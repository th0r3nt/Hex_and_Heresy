"""
Обработчики навыков мастера игры.
"""

from typing import Any, Optional

from src.back.l01_domain.army.constants import StrategicMovementPace, UnitSizeCategory
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.army.models.characters.commanders import (
    Commander,
    CommanderCharacteristics,
)
from src.back.l01_domain.army.models.characters.heroes import Hero
from src.back.l01_domain.army.models.characters.traits import Trait, get_trait
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.common import CharacterGenerationType, FactionRace
from src.back.l01_domain.factions.models.lord import Lord, LordStrategicBias
from src.back.l01_domain.llm.tools.definitions.game_master import (
    CREATE_ADVISOR,
    CREATE_COMMANDER,
    CREATE_HERO,
    CREATE_LORD,
    REJECT_CREATION,
    TRIGGER_WORLD_EVENT,
)
from src.back.l01_domain.llm.tools.schemas.game_master import (
    CreateAdvisorParams,
    CreateCommanderParams,
    CreateHeroParams,
    CreateLordParams,
    RejectCreationParams,
    TriggerWorldEventParams,
)
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.events import GlobalEvent
from src.back.l02_services.mechanics.game_master.custom.advisers import CustomAdvisor
from src.back.l02_services.mechanics.game_master.facade import GameMasterFacade
from src.back.l02_services.mechanics.tools.context import ToolExecutionContext
from src.back.l02_services.mechanics.tools.executor import ToolExecutor
from src.back.utils.event.registry import GameEvents


class GameMasterToolHandlers:
    """
    Мастер игры лепит персонажей по заказу игрока и запускает события мира.
    """

    def __init__(self, game_master_facade: GameMasterFacade) -> None:
        self._game_master = game_master_facade

    def register(self, executor: ToolExecutor) -> None:
        """
        Подключает навыки мастера игры к исполнителю.
        """
        executor.register_handler(CREATE_COMMANDER, self.create_commander)
        executor.register_handler(CREATE_HERO, self.create_hero)
        executor.register_handler(CREATE_LORD, self.create_lord)
        executor.register_handler(CREATE_ADVISOR, self.create_advisor)
        executor.register_handler(TRIGGER_WORLD_EVENT, self.trigger_world_event)
        executor.register_handler(REJECT_CREATION, self.reject_creation)

    # ====================================================
    # Создание персонажей
    # ====================================================

    async def create_commander(
        self, params: CreateCommanderParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Ставит в ставку найма кастомного полководца.
        """
        faction_id = ctx.require_caller_faction_id("create_commander")

        characteristics = CommanderCharacteristics(
            authority=params.authority,
            tactical_acumen=params.tactical_acumen,
            resilience=params.resilience,
            cunning=params.cunning,
        )

        commander = Commander(
            name=params.name,
            role_title=params.role_title,
            faction_id=faction_id,
            generation_type=CharacterGenerationType.CUSTOM,
            traits=self._collect_traits(params.trait_ids),
            characteristics=characteristics,
            personality_prompt_override=params.distilled_personality,
        )

        ctx.world_state.add_available_commander(commander)

        await self._publish_character_created(commander.id, "commander", commander.name, faction_id)

        return (
            f"Полководец {commander.name} создан и добавлен в ставку найма. {params.master_reply}",
            {"commander_id": commander.id, "name": commander.name},
        )

    async def create_hero(
        self, params: CreateHeroParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Ставит в ставку найма кастомного героя.
        """
        faction_id = ctx.require_caller_faction_id("create_hero")

        hero = Hero.create_new(
            name=params.name,
            faction_id=faction_id,
            special_rule=params.special_rule,
            max_hp=params.max_hp,
            traits=self._collect_traits(params.trait_ids),
            generation_type=CharacterGenerationType.CUSTOM,
            personality_prompt_override=params.distilled_personality,
        )

        ctx.world_state.add_available_hero(hero)

        await self._publish_character_created(hero.id, "hero", hero.name, faction_id)

        return (
            f"Герой {hero.name} создан и готов к найму. {params.master_reply}",
            {"hero_id": hero.id, "name": hero.name},
        )

    async def create_lord(
        self, params: CreateLordParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Сажает на престол фракции кастомного правителя.
        """
        faction_id = ctx.require_caller_faction_id("create_lord")
        faction = ctx.world_state.get_faction(faction_id)

        lord = Lord(
            faction_id=faction_id,
            name=params.name,
            title=params.title,
            generation_type=CharacterGenerationType.CUSTOM,
            traits=self._collect_traits(params.trait_ids),
            personality_prompt_override=params.distilled_personality,
            lore_description=params.archetype_name,
            bias=LordStrategicBias(
                tax_rate_bias=params.tax_rate_bias,
                military_building_priority=params.military_building_priority,
                diplomatic_aggression=params.diplomatic_aggression,
                bribery_susceptibility=params.bribery_susceptibility,
            ),
        )

        if faction is not None:
            faction.lord = lord

        await self._publish_character_created(lord.id, "lord", lord.name, faction_id)

        return (
            f"Правитель {lord.display_name} возглавил фракцию. {params.master_reply}",
            {"lord_id": lord.id, "name": lord.name},
        )

    async def create_advisor(
        self, params: CreateAdvisorParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Назначает державе кастомного советника.
        """
        faction_id = ctx.require_caller_faction_id("create_advisor")
        faction = ctx.world_state.get_faction(faction_id)
        race = faction.race if faction is not None else FactionRace.HUMANS

        advisor = CustomAdvisor(
            id=f"adv_{params.name.lower()}",
            faction_id=faction_id,
            race=race,
            name=params.name,
            title=params.title,
            personality_prompt=params.distilled_personality,
            biography="",
            traits=self._collect_traits(params.trait_ids),
        )

        await self._publish_character_created(advisor.id, "advisor", advisor.name, faction_id)

        return (
            f"Советник {advisor.title} {advisor.name} вступил в должность. {params.master_reply}",
            {"advisor_id": advisor.id, "name": advisor.name},
        )

    # ====================================================
    # События и кризисы мира
    # ====================================================

    async def trigger_world_event(
        self, params: TriggerWorldEventParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Запускает глобальное событие и, если нужно, ставит на карту враждебную армию.
        """
        target_coords: list[HexCoordinates] = []
        spawn_hex: Optional[HexCoordinates] = None

        if params.target_hex_q is not None and params.target_hex_r is not None:
            coord = HexCoordinates.from_axial(params.target_hex_q, params.target_hex_r)
            target_coords.append(coord)
            spawn_hex = coord

        spawned_army_id: Optional[str] = None
        if params.spawn_hostile_army:
            army = self._spawn_neutral_army(
                name=params.neutral_army_name,
                host_hex=spawn_hex or HexCoordinates.from_axial(0, 0),
            )
            ctx.world_state.add_army(army)
            spawned_army_id = army.id

        event = GlobalEvent(
            name=params.name,
            description=params.description,
            category=params.category,
            scope=params.scope,
            target_faction_ids=params.target_faction_ids,
            target_hex_coords=target_coords,
            spawned_army_id=spawned_army_id,
            spawn_hex=spawn_hex,
            duration_ticks_remaining=params.duration_ticks,
            modifiers=params.modifiers,
        )
        ctx.world_state.add_event(event)

        if self._game_master._event_bus is not None:
            await self._game_master._event_bus.publish(
                GameEvents.GameMaster.GLOBAL_EVENT_SPAWNED,
                event_id=event.id,
                name=event.name,
                category=event.category.value,
                scope=event.scope.value,
                spawned_army_id=spawned_army_id,
            )

        return (
            f"Запущено событие мира «{event.name}» (категория: {event.category.value}).",
            {"event_id": event.id, "name": event.name},
        )

    async def reject_creation(
        self, params: RejectCreationParams, _ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Отклоняет заказ игрока на создание сущности.
        """
        return (
            f"Создание сущности отклонено: {params.master_reply}",
            {"is_approved": False, "reason": params.reason},
        )

    # ====================================================
    # Служебное
    # ====================================================

    @staticmethod
    def _collect_traits(trait_ids: list[str]) -> list[Trait]:
        """
        Отбирает известные каталогу черты: выдуманных моделью в персонаже не будет.
        """
        traits = (get_trait(trait_id) for trait_id in trait_ids)
        return [trait for trait in traits if trait is not None]

    @staticmethod
    def _spawn_neutral_army(name: str, host_hex: HexCoordinates) -> StrategicArmy:
        """
        Собирает нейтральный отряд мятежников под событие мира.
        """
        army = StrategicArmy(
            faction_id="neutrals",
            name=name,
            current_hex=host_hex,
            pace=StrategicMovementPace.MARCH,
        )
        army.add_squad(
            Squad.create_new(
                archetype=UnitArchetype(
                    id="unit_neu_event_mob",
                    race=FactionRace.NEUTRALS,
                    faction_id="neutrals",
                    name="Отряд мятежников",
                    tier=1,
                    default_unit_count=80,
                    base_stats=BaseUnitStats(
                        max_hp=15.0, size_category=UnitSizeCategory.MEDIUM
                    ),
                )
            )
        )
        return army

    async def _publish_character_created(
        self, character_id: str, character_type: str, name: str, faction_id: str
    ) -> None:
        """
        Рассказывает миру о новом персонаже, если шина событий вообще собрана.
        """
        if self._game_master._event_bus is None:
            return
        await self._game_master._event_bus.publish(
            GameEvents.GameMaster.CHARACTER_CREATED,
            character_id=character_id,
            character_type=character_type,
            name=name,
            faction_id=faction_id,
        )
