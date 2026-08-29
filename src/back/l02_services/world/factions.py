"""
Сборка одной державы нулевого такта: правитель на троне, цитадель первого
уровня, казна по уровню сложности, обжитые лепестки с ратушами и работающая
стартовая застройка.

Все, что выбирается из каталогов геймдаты - правитель и здания, - берется
детерминированно: ничью между кандидатами всегда добивает идентификатор,
иначе одинаковый сид давал бы разные державы.
"""

from typing import Final, Optional
from uuid import uuid4

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions.world import RulerTemplateNotFoundError
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.buildings import (
    Building,
    ConstructedBuilding,
    Headquarters,
    RegionalHall,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.legendary import LegendaryLordTemplate
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.maps.constants import TerritoryZoneType
from src.back.l01_domain.maps.models.strategic import hex_zone_id
from src.back.l01_domain.protocols.gamedata import GameDataRepositoryProtocol
from src.back.l01_domain.world.constants import (
    DEFAULT_HEADQUARTERS_NAME,
    DEFAULT_REGIONAL_HALL_NAME,
    HEADQUARTERS_NAME_BY_RACE,
    REGIONAL_HALL_NAME_BY_RACE,
    DifficultyLevel,
    starting_resources,
)
from src.back.l01_domain.world.models.setup import FactionSetupConfig, RulerSetupConfig
from src.back.l02_services.world.layout import FactionPlacement
from src.back.utils.logger import main_logger

# Стартовая застройка стороны: по одному зданию на каждый обжитый лепесток,
# в порядке разметки земель. Гекс цитадели остается пустым - все добывающие
# здания расовых каталогов разрешены только в союзных землях
STARTING_BUILDING_PLAN: Final[tuple[ResourceType, ...]] = (
    ResourceType.FOOD,
    ResourceType.FOOD,
    ResourceType.MATERIAL,
)


class FactionBuilder:
    """
    Собирает державу партии из настроек ее стороны и отведенного ей места.
    """

    def __init__(self, gamedata: GameDataRepositoryProtocol) -> None:
        self._gamedata = gamedata

    # ==================================================================
    # ДЕРЖАВА ЦЕЛИКОМ
    # ==================================================================

    def build(
        self,
        setup: FactionSetupConfig,
        placement: FactionPlacement,
        difficulty: DifficultyLevel,
    ) -> Faction:
        """
        Собирает одну сторону партии целиком: правитель, цитадель, казна,
        союзные земли с ратушами и стартовая застройка.
        """
        # Идентификатор нужен раньше самой фракции: на него ссылаются и
        # правитель, и цитадель, и ратуши
        faction_id = str(uuid4())
        race = setup.race

        faction = Faction(
            id=faction_id,
            race=race,
            name=setup.name,
            is_player_controlled=setup.is_player_controlled,
            lord=self._enthrone_lord(setup, faction_id),
            headquarters=Headquarters(
                faction_id=faction_id,
                name=HEADQUARTERS_NAME_BY_RACE.get(race, DEFAULT_HEADQUARTERS_NAME),
                level=1,
            ),
            resources=starting_resources(difficulty, setup.is_player_controlled),
            capital_hex=placement.capital_hex,
        )

        self._settle_allied_lands(faction, placement)
        self._erect_starting_buildings(faction, placement)
        return faction

    # ==================================================================
    # ПРАВИТЕЛЬ
    # ==================================================================

    def _enthrone_lord(self, setup: FactionSetupConfig, faction_id: str) -> Lord:
        """
        Сажает на трон стороны выбранного игроком правителя.

        Кастомного лорда мастер игры сочинил заранее и без привязки к партии,
        поэтому здесь ему проставляется его новая держава.
        """
        ruler = setup.ruler
        if ruler.custom_lord is not None:
            return ruler.custom_lord.model_copy(update={"faction_id": faction_id})

        return self._require_lord_template(setup.race, ruler).build(faction_id)

    def _require_lord_template(
        self, race: FactionRace, ruler: RulerSetupConfig
    ) -> LegendaryLordTemplate:
        """
        Достает из каталога шаблон легендарного правителя.

        Пустая настройка - законный выбор: партию можно начать и без похода в
        лобби, тогда трон занимает первый правитель расового каталога.
        """
        if ruler.legendary_lord_id is None:
            candidates = sorted(
                self._gamedata.list_faction_legendary_lords(race.value),
                key=lambda template: template.id,
            )
            if not candidates:
                raise RulerTemplateNotFoundError("<любой>", race.value)
            return candidates[0]

        template = self._gamedata.get_legendary_lord(ruler.legendary_lord_id)
        if template is None or template.race != race:
            raise RulerTemplateNotFoundError(ruler.legendary_lord_id, race.value)
        return template

    # ==================================================================
    # ЗЕМЛИ И ЗАСТРОЙКА
    # ==================================================================

    @staticmethod
    def _settle_allied_lands(faction: Faction, placement: FactionPlacement) -> None:
        """
        Берет под контроль лепестки цитадели и ставит на каждом ратушу
        первого уровня.
        """
        hall_name = REGIONAL_HALL_NAME_BY_RACE.get(
            faction.race, DEFAULT_REGIONAL_HALL_NAME
        )

        for coord in placement.allied_hexes:
            zone_id = hex_zone_id(coord)
            faction.gain_zone(zone_id)
            faction.add_regional_hall(
                RegionalHall(
                    faction_id=faction.id,
                    zone_id=zone_id,
                    name=hall_name,
                    level=1,
                )
            )

    def _erect_starting_buildings(
        self, faction: Faction, placement: FactionPlacement
    ) -> None:
        """
        Ставит экономику нулевого такта: два пищевых здания и одну добычу
        материалов, по одному зданию на лепесток (см. STARTING_BUILDING_PLAN).

        Здания встают уже достроенными: партия начинается с работающей
        экономики, а не со стройплощадок.
        """
        zone_ids = [hex_zone_id(coord) for coord in placement.allied_hexes]

        for zone_id, resource in zip(zone_ids, STARTING_BUILDING_PLAN):
            template = self._pick_producer(faction.race, resource)
            if template is None:
                main_logger.warning(
                    f"В каталоге расы '{faction.race_id}' нет здания, добывающего "
                    f"'{resource.value}': земля '{zone_id}' осталась незастроенной."
                )
                continue

            faction.add_building(
                ConstructedBuilding(
                    building=template,
                    zone_id=zone_id,
                    is_under_construction=False,
                    construction_ticks_remaining=0,
                )
            )

    def _pick_producer(
        self, race: FactionRace, resource: ResourceType
    ) -> Optional[Building]:
        """
        Подбирает расовое здание, добывающее нужный ресурс в союзных землях.

        Берется самое доходное; ничью добивает идентификатор, чтобы стартовая
        застройка была воспроизводима при одинаковой геймдате.
        """
        producers = [
            building
            for building in self._gamedata.list_faction_buildings(race.value)
            if building.allowed_zone == TerritoryZoneType.ALLIED_LANDS
            and building.resource_output_per_worker.get(resource, 0.0) > 0.0
        ]
        if not producers:
            return None

        return min(
            producers,
            key=lambda b: (-b.resource_output_per_worker[resource], b.id),
        )
