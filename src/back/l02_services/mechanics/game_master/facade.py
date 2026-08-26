"""
Главный фасад мастера игры (Game Master).
Единая точка входа для генерации кастомных персонажей и динамических событий мира.
"""

from typing import Optional

from src.back.l01_domain.army.models.characters.commanders import Commander
from src.back.l01_domain.army.models.characters.heroes import Hero
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.protocols.gamedata import GameDataRepositoryProtocol
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l01_domain.world.models.events import GlobalEvent
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.game_master.custom.advisers import (
    CustomAdvisor,
    CustomAdvisorFactory,
)
from src.back.l02_services.mechanics.game_master.custom.commanders import (
    CustomCommanderFactory,
)
from src.back.l02_services.mechanics.game_master.custom.heroes import (
    CustomHeroFactory,
)
from src.back.l02_services.mechanics.game_master.custom.lords import (
    CustomLordFactory,
)
from src.back.l02_services.mechanics.game_master.events import (
    DEFAULT_TICKS_BETWEEN_EVENTS,
    DynamicEventService,
)
from src.back.l03_infrastructure.llm.context.builder import ContextBuilder
from src.back.l03_infrastructure.llm.prompt.builder import PromptBuilder
from src.back.utils.event.registry import GameEvents
from src.back.utils.logger import main_logger


class GameMasterFacade:
    """
    Фасад оркестрации мастера игры:
    - генерация и регистрация кастомных личностей по тексту игрока;
    - мониторинг состояния партии и создание случайных кризисов.
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        prompt_builder: Optional[PromptBuilder] = None,
        context_builder: Optional[ContextBuilder] = None,
        gamedata_repository: Optional[GameDataRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        event_evaluation_interval: int = DEFAULT_TICKS_BETWEEN_EVENTS,
    ) -> None:
        self._llm = llm_client
        self._event_bus = event_bus

        pb = prompt_builder or PromptBuilder()
        cb = context_builder or ContextBuilder()

        self._commander_factory = CustomCommanderFactory(
            llm_client=llm_client,
            prompt_builder=pb,
        )
        self._hero_factory = CustomHeroFactory(
            llm_client=llm_client,
            prompt_builder=pb,
        )
        self._lord_factory = CustomLordFactory(
            llm_client=llm_client,
            prompt_builder=pb,
        )
        self._advisor_factory = CustomAdvisorFactory(
            llm_client=llm_client,
            prompt_builder=pb,
        )
        self._event_service = DynamicEventService(
            llm_client=llm_client,
            prompt_builder=pb,
            context_builder=cb,
            gamedata_repository=gamedata_repository,
            event_bus=event_bus,
            evaluation_interval=event_evaluation_interval,
        )

    # ==================================================================
    # СОЗДАНИЕ КАСТОМНЫХ ПЕРСОНАЖЕЙ
    # ==================================================================

    async def create_custom_commander(
        self,
        world_state: WorldState,
        faction_id: str,
        biography_text: str,
    ) -> tuple[Optional[Commander], str]:
        """
        Создает полководца по биографии игрока и регистрирует его в пуле найма.
        """
        faction = world_state.get_faction(faction_id)
        if faction is None:
            raise ValueError(f"Фракция '{faction_id}' не найдена в мире.")

        commander, message = await self._commander_factory.create_commander(
            faction_id=faction_id,
            race=faction.race,
            biography_text=biography_text,
        )

        if commander is not None:
            world_state.add_available_commander(commander)
            main_logger.info(
                f"[GameMaster] Полководец '{commander.name}' добавлен в пул найма фракции '{faction.name}'."
            )
            await self._publish_character_created(
                character_id=commander.id,
                character_type="commander",
                name=commander.name,
                faction_id=faction_id,
            )

        return commander, message

    async def create_custom_hero(
        self,
        world_state: WorldState,
        faction_id: str,
        biography_text: str,
    ) -> tuple[Optional[Hero], str]:
        """
        Создает героя по биографии игрока и регистрирует его в пуле найма.
        """
        faction = world_state.get_faction(faction_id)
        if faction is None:
            raise ValueError(f"Фракция '{faction_id}' не найдена в мире.")

        hero, message = await self._hero_factory.create_hero(
            faction_id=faction_id,
            race=faction.race,
            biography_text=biography_text,
        )

        if hero is not None:
            world_state.add_available_hero(hero)
            main_logger.info(
                f"[GameMaster] Герой '{hero.name}' добавлен в пул найма фракции '{faction.name}'."
            )
            await self._publish_character_created(
                character_id=hero.id,
                character_type="hero",
                name=hero.name,
                faction_id=faction_id,
            )

        return hero, message

    async def create_custom_lord(
        self,
        world_state: WorldState,
        faction_id: str,
        biography_text: str,
        assign_as_ruler: bool = True,
    ) -> tuple[Optional[Lord], str]:
        """
        Создает лорда по биографии игрока. При assign_as_ruler=True назначает его правителем фракции.
        """
        faction = world_state.get_faction(faction_id)
        if faction is None:
            raise ValueError(f"Фракция '{faction_id}' не найдена в мире.")

        lord, message = await self._lord_factory.create_lord(
            faction_id=faction_id,
            race=faction.race,
            biography_text=biography_text,
        )

        if lord is not None and assign_as_ruler:
            faction.lord = lord
            main_logger.info(
                f"[GameMaster] Лорд '{lord.display_name}' назначен верховным правителем фракции '{faction.name}'."
            )
            await self._publish_character_created(
                character_id=lord.id,
                character_type="lord",
                name=lord.name,
                faction_id=faction_id,
            )

        return lord, message

    async def create_custom_advisor(
        self,
        world_state: WorldState,
        faction_id: str,
        biography_text: str,
    ) -> tuple[Optional[CustomAdvisor], str]:
        """
        Создает персонализированный профиль советника для UI и рекомендаций.
        """
        faction = world_state.get_faction(faction_id)
        if faction is None:
            raise ValueError(f"Фракция '{faction_id}' не найдена в мире.")

        advisor, message = await self._advisor_factory.create_advisor(
            faction_id=faction_id,
            race=faction.race,
            biography_text=biography_text,
        )

        if advisor is not None:
            main_logger.info(
                f"[GameMaster] Советник '{advisor.title} {advisor.name}' создан для фракции '{faction.name}'."
            )
            await self._publish_character_created(
                character_id=advisor.id,
                character_type="advisor",
                name=advisor.name,
                faction_id=faction_id,
            )

        return advisor, message

    # ==================================================================
    # ДИНАМИЧЕСКИЕ СОБЫТИЯ МИРА
    # ==================================================================

    async def evaluate_world_events(
        self,
        world_state: WorldState,
        force: bool = False,
    ) -> Optional[GlobalEvent]:
        """
        Оценивает состояние партии и генерирует случайный кризис или аномалию.
        """
        return await self._event_service.evaluate_and_spawn_event(
            world_state=world_state,
            force=force,
        )

    # ==================================================================
    # СЛУЖЕБНОЕ
    # ==================================================================

    async def _publish_character_created(
        self,
        character_id: str,
        character_type: str,
        name: str,
        faction_id: str,
    ) -> None:
        if self._event_bus is None:
            return
        await self._event_bus.publish(
            GameEvents.GameMaster.CHARACTER_CREATED,
            character_id=character_id,
            character_type=character_type,
            name=name,
            faction_id=faction_id,
        )
