"""
Фасад.
Точка входа для остальных модулей.

Генератор ничего не строит сам: он задает порядок сборки мира и раздает
работу тем, кто умеет ее делать - разметке карты, сборщику держав, набору
стартовых армий и наполнению Ничьей земли. Своего состояния он не держит,
поэтому один и тот же экземпляр годится на любое число новых партий.

За ним остаются только шаги, которые никому не отдать: гарнизоны земель
(их поднимает тот же сервис, что следит за ними каждый такт), дипломатия
нулевого такта, первичный расчет тумана войны и объявление на шине.

Вся случайность идет через один экземпляр random.Random, засеянный сидом из
настроек: одинаковые настройки дают одинаковую карту.
"""

from random import Random
from typing import Optional

from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.protocols.gamedata import GameDataRepositoryProtocol
from src.back.l01_domain.world.models.setup import NewGameConfig
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.vision.facade import VisionFacade
from src.back.l02_services.turns.strategic.garrison import GarrisonService
from src.back.l02_services.world.armies import StartingArmyBuilder
from src.back.l02_services.world.factions import FactionBuilder
from src.back.l02_services.world.layout import plan_placements
from src.back.l02_services.world.no_mans_land import NoMansLandPopulator
from src.back.utils.event.registry import GameEvents
from src.back.utils.logger import main_logger


class WorldGenerator:
    """
    Собирает мир новой партии из настроек лобби.
    """

    def __init__(
        self,
        gamedata: GameDataRepositoryProtocol,
        vision_facade: Optional[VisionFacade] = None,
        garrison_service: Optional[GarrisonService] = None,
        faction_builder: Optional[FactionBuilder] = None,
        army_builder: Optional[StartingArmyBuilder] = None,
        no_mans_land: Optional[NoMansLandPopulator] = None,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._vision_facade = vision_facade
        self._garrison_service = garrison_service or GarrisonService(gamedata=gamedata)
        self._factions = faction_builder or FactionBuilder(gamedata=gamedata)
        self._armies = army_builder or StartingArmyBuilder(gamedata=gamedata)
        self._no_mans_land = no_mans_land or NoMansLandPopulator(gamedata=gamedata)
        self._event_bus = event_bus

    # ==================================================================
    # СБОРКА МИРА
    # ==================================================================

    async def generate(self, config: NewGameConfig) -> WorldState:
        """
        Создает мир партии по настройкам лобби.

        Порядок шагов не случаен: туман войны считается последним, потому что
        смотрят на карту уже поставленные цитадели, ратуши и армии.
        """
        rng = Random(config.seed)
        world = WorldState(victory_config=config.victory_config)

        # 1. Разметка: кто где встанет на карте
        placements = plan_placements(config, rng)

        # 2. Державы: правители, цитадели, союзные земли, застройка и армии
        for setup, placement in zip(config.starting_sides, placements):
            faction = self._factions.build(setup, placement, config.difficulty)
            world.add_faction(faction)
            world.add_army(self._armies.build(faction, placement.capital_hex))

        # 3. Гарнизоны земель и городское ополчение нулевого такта
        await self._raise_garrisons(world)

        # 4. Ничья земля: свободные гексы, лорные ориентиры и процедурные места
        self._no_mans_land.populate(world, rng)

        # 5. Нулевой такт дипломатии и первичный расчет тумана войны
        self._establish_peace(world)
        await self._refresh_vision(world)

        await self._publish_generated(world, config)
        main_logger.info(
            f"Сгенерирован мир '{world.id}': {len(world.factions)} держав, "
            f"сид '{config.seed}', сложность '{config.difficulty.value}'."
        )
        return world

    # ==================================================================
    # ГАРНИЗОНЫ ЗЕМЕЛЬ
    # ==================================================================

    async def _raise_garrisons(self, world: WorldState) -> None:
        """
        Поднимает гарнизоны земель и городское ополчение нулевого такта.

        Отдельного приказа "построить гарнизон" в игре нет: гарнизон - это
        свойство самой земли, поэтому его ставит тот же сервис, который потом
        следит за ним каждый такт.
        """
        await self._garrison_service.process_garrisons(world)

    # ==================================================================
    # ДИПЛОМАТИЯ И ТУМАН ВОЙНЫ
    # ==================================================================

    @staticmethod
    def _establish_peace(world: WorldState) -> None:
        """
        Заводит нейтральные мирные отношения между всеми парами держав:
        стороны начинают партию с чистого листа, без пактов и претензий.
        """
        faction_ids = sorted(world.factions)

        for index, faction_id in enumerate(faction_ids):
            for counterpart_id in faction_ids[index + 1 :]:
                world.get_or_create_relation(faction_id, counterpart_id)

    async def _refresh_vision(self, world: WorldState) -> None:
        """
        Считает первичные маски тумана: стартовые зоны обзора цитаделей,
        ратуш и стоящих на базах армий.
        """
        if self._vision_facade is None:
            return
        await self._vision_facade.refresh_world_vision(world)

    # ==================================================================
    # ОБЪЯВЛЕНИЕ НА ШИНЕ
    # ==================================================================

    async def _publish_generated(
        self, world: WorldState, config: NewGameConfig
    ) -> None:
        """
        Сообщает миру о начатой партии: интерфейсу пора рисовать карту.
        """
        if self._event_bus is None:
            return

        await self._event_bus.publish(
            GameEvents.GameFlow.GAME_STARTED,
            world_state_id=world.id,
            seed=str(config.seed),
            difficulty=config.difficulty.value,
            faction_ids=sorted(world.factions),
        )
