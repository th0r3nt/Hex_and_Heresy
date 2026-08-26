"""
Сервис генерации и разрешения динамических событий мира через мастера игры.
"""

from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field

from src.back.l01_domain.army.constants import StrategicMovementPace, UnitSizeCategory
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.common import FactionRace, MechanicalModifier
from src.back.l01_domain.exceptions.llm import LLMError
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.protocols.gamedata import GameDataRepositoryProtocol
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l01_domain.world.constants import GlobalEventCategory, GlobalEventScope
from src.back.l01_domain.world.models.events import GlobalEvent
from src.back.l01_domain.world.models.state import WorldState
from src.back.l03_infrastructure.llm.context.builder import ContextBuilder
from src.back.l03_infrastructure.llm.prompt.builder import PromptBuilder
from src.back.l03_infrastructure.llm.prompt.catalog import PromptCatalog
from src.back.utils.event.registry import GameEvents
from src.back.utils.logger import main_logger

# Минимальный интервал между проверками событий в глобальных тактах
DEFAULT_TICKS_BETWEEN_EVENTS = 5


class DynamicGlobalEventResponse(BaseModel):
    """Схема ответа мастера игры при оценке событий мира."""

    should_trigger: bool = Field(
        ..., description="Следует ли запустить новое событие на основе текущего состояния мира"
    )
    name: str = Field(default="Событие", description="Название кризиса или аномалии")
    description: str = Field(
        default="", description="Художественное описание события для игрока"
    )
    category: GlobalEventCategory = Field(
        default=GlobalEventCategory.WEATHER, description="Категория события"
    )
    scope: GlobalEventScope = Field(
        default=GlobalEventScope.GLOBAL, description="Масштаб распространения"
    )
    duration_ticks: Optional[int] = Field(
        default=4, ge=1, le=20, description="Длительность действия в глобальных тактах"
    )
    target_faction_ids: list[str] = Field(
        default_factory=list, description="ID фракций, если область действия ограничена"
    )

    # Координаты эпицентра (осевые q, r)
    target_hex_q: Optional[int] = Field(default=None, description="Осевая координата Q")
    target_hex_r: Optional[int] = Field(default=None, description="Осевая координата R")

    # Физический спавн сил
    spawn_hostile_army: bool = Field(
        default=False, description="Требуется ли создать враждебную армию на карте"
    )
    neutral_army_name: str = Field(
        default="Шайка разбойников", description="Название создаваемой нейтральной армии"
    )
    neutral_unit_type: str = Field(
        default="marauders",
        description="Тип нейтрального отряда: 'rebels', 'marauders', 'beasts', 'deserters'",
    )

    modifiers: list[MechanicalModifier] = Field(
        default_factory=list, description="Механические эффекты события"
    )


class DynamicEventService:
    """Генерирует и применяет динамические события мира."""

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        prompt_builder: Optional[PromptBuilder] = None,
        context_builder: Optional[ContextBuilder] = None,
        gamedata_repository: Optional[GameDataRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        evaluation_interval: int = DEFAULT_TICKS_BETWEEN_EVENTS,
    ) -> None:
        self._llm = llm_client
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._context_builder = context_builder or ContextBuilder()
        self._gamedata = gamedata_repository
        self._event_bus = event_bus
        self._evaluation_interval = evaluation_interval
        self._last_evaluation_tick = 0

    def should_evaluate(self, world_state: WorldState) -> bool:
        """Проверяет, наступил ли срок плановой оценки событий."""
        current_tick = world_state.time.total_ticks
        return (current_tick - self._last_evaluation_tick) >= self._evaluation_interval

    async def evaluate_and_spawn_event(
        self,
        world_state: WorldState,
        force: bool = False,
    ) -> Optional[GlobalEvent]:
        """Оценивает срез мира и при необходимости создает новое глобальное событие."""
        if not force and not self.should_evaluate(world_state):
            return None

        self._last_evaluation_tick = world_state.time.total_ticks

        system_prompt = self._build_system_prompt()
        world_summary = self._context_builder.render(
            self._context_builder.build_rumor_context(world_state)
        )
        user_prompt = f"Текущая сводка состояния мира:\n{world_summary}"

        try:
            draft = await self._llm.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=DynamicGlobalEventResponse,
                temperature=0.7,
            )
        except LLMError as e:
            main_logger.warning(f"[GameMaster] Ошибка генерации события: {e.message}")
            return None

        if not draft.should_trigger or not draft.name.strip():
            return None

        # Разрешаем координаты эпицентра
        target_coords: list[HexCoordinates] = []
        spawn_hex: Optional[HexCoordinates] = None
        if draft.target_hex_q is not None and draft.target_hex_r is not None:
            try:
                coord = HexCoordinates.from_axial(draft.target_hex_q, draft.target_hex_r)
                target_coords.append(coord)
                spawn_hex = coord
            except Exception as err:
                main_logger.debug(f"[GameMaster] Некорректные координаты эпицентра: {err}")

        # Создаем физическую армию на карте, если событие военное
        spawned_army_id: Optional[str] = None
        if draft.spawn_hostile_army:
            spawned_army = self._spawn_neutral_army(
                world_state=world_state,
                army_name=draft.neutral_army_name,
                unit_type=draft.neutral_unit_type,
                spawn_hex=spawn_hex,
            )
            if spawned_army is not None:
                spawned_army_id = spawned_army.id
                spawn_hex = spawned_army.current_hex

        # Формируем непустое описание для валидации GlobalEvent
        description_text = (
            draft.description.strip()
            if draft.description and draft.description.strip()
            else f"Событие мира: {draft.name}"
        )

        event = GlobalEvent(
            id=f"event_dynamic_{uuid4().hex[:8]}",
            name=draft.name,
            description=description_text,
            category=draft.category,
            scope=draft.scope,
            target_faction_ids=draft.target_faction_ids,
            target_hex_coords=target_coords,
            spawned_army_id=spawned_army_id,
            spawn_hex=spawn_hex,
            duration_ticks_remaining=draft.duration_ticks,
            modifiers=draft.modifiers,
        )

        world_state.add_event(event)
        main_logger.info(
            f"[GameMaster] Создано динамическое событие: «{event.name}» ({event.category.value})."
        )

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.GameMaster.GLOBAL_EVENT_SPAWNED,
                event_id=event.id,
                name=event.name,
                category=event.category.value,
                scope=event.scope.value,
                spawned_army_id=spawned_army_id,
            )

        return event

    def _spawn_neutral_army(
        self,
        world_state: WorldState,
        army_name: str,
        unit_type: str,
        spawn_hex: Optional[HexCoordinates],
    ) -> Optional[StrategicArmy]:
        """Создает нейтральную армию на глобальной карте."""
        target_hex = spawn_hex
        if target_hex is None:
            if world_state.neutral_hexes:
                target_hex = world_state.neutral_hexes[0]
            else:
                target_hex = HexCoordinates.from_axial(0, 0)

        # Подбираем или генерируем базовый отряд нейтралов
        squad = self._build_neutral_squad(unit_type)

        army = StrategicArmy(
            id=f"army_neutral_{uuid4().hex[:8]}",
            faction_id="neutrals",
            name=army_name,
            current_hex=target_hex,
            pace=StrategicMovementPace.MARCH,
        )
        army.add_squad(squad)
        world_state.add_army(army)

        return army

    def _build_neutral_squad(self, unit_type: str) -> Squad:
        """Собирает отряд нейтралов заданного типа."""
        unit_id_map = {
            "rebels": "unit_neu_rebels_mob_00",
            "marauders": "unit_neu_marauders_01",
            "beasts": "unit_neu_wild_beasts_01",
            "deserters": "unit_neu_deserter_gang_02",
        }
        archetype_id = unit_id_map.get(unit_type.lower(), "unit_neu_marauders_01")

        archetype = None
        if self._gamedata is not None:
            archetype = self._gamedata.get_unit_archetype(archetype_id)

        if archetype is None:
            # Резервный шаблон на случай отсутствия каталога
            archetype = UnitArchetype(
                id=archetype_id,
                race=FactionRace.NEUTRALS,
                faction_id="neutrals",
                name="Шайка мародеров",
                tier=1,
                default_unit_count=80,
                base_stats=BaseUnitStats(max_hp=16.0, size_category=UnitSizeCategory.MEDIUM),
            )

        return Squad.create_new(archetype=archetype)

    def _build_system_prompt(self) -> str:
        blocks = [
            PromptCatalog.BASE.PERSONA,
            PromptCatalog.ROLES.GAME_MASTER,
            PromptCatalog.LORE.BASIC.MEDIUM,
        ]
        base_prompt = self._prompt_builder.build(blocks)

        # TODO: засунуть в промпты
        instructions = (
            "## Задача мастера игры\n"
            "Оцени текущее состояние мира и реши, должно ли произойти локальное или глобальное событие.\n"
            "Правила генерации:\n"
            "1. Реагируй на контекст: при дефиците еды логичен бунт крестьян; при скоплении полей брани — нашествие "
            "диких мутантов; в неоновые часы — погодные аномалии или выброс резонита.\n"
            "2. Не спамь: если обстановка стабильна, выстави should_trigger: false.\n"
            "3. При создании военных угроз (бунт, набег) выстави spawn_hostile_army: true и укажи neutral_unit_type "
            "('rebels', 'marauders', 'beasts', 'deserters')."
        )
        return f"{base_prompt}\n\n{instructions}"
