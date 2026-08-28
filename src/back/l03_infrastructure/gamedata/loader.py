"""
Загрузчик статической геймдаты.
Считывает словари из пакета src.back.gamedata, валидирует их через Pydantic
и предоставляет in-memory реестр, реализующий GameDataRepositoryProtocol.
"""

import importlib
from typing import Callable, Optional

from src.back.gamedata.common import RACES
from src.back.l01_domain.army.models.card.equipment import Equipment
from src.back.l01_domain.army.models.card.roster import RosterEntry
from src.back.l01_domain.army.models.card.unit import UnitArchetype
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.models.buildings import Building
from src.back.l01_domain.factions.models.legendary import (
    LegendaryCommanderTemplate,
    LegendaryHeroTemplate,
    LegendaryLordTemplate,
)
from src.back.l01_domain.protocols.gamedata import GameDataRepositoryProtocol
from src.back.l01_domain.world.models.points_of_interest import PointOfInterestBlueprint
from src.back.utils.logger import main_logger

# Модуль с местами Ничьей земли: он один на весь мир, а не свой у каждой расы
POINTS_OF_INTEREST_MODULE = "src.back.gamedata.world.points_of_interest"


class StaticGameDataRegistry(GameDataRepositoryProtocol):
    """Read-only реестр статических данных игры."""

    def __init__(self) -> None:
        self._units: dict[str, UnitArchetype] = {}
        self._equipment: dict[str, Equipment] = {}
        self._buildings: dict[str, Building] = {}
        self._roster: dict[str, RosterEntry] = {}

        self._legendary_lords: dict[str, LegendaryLordTemplate] = {}
        self._legendary_commanders: dict[str, LegendaryCommanderTemplate] = {}
        self._legendary_heroes: dict[str, LegendaryHeroTemplate] = {}

        self._points_of_interest: dict[str, PointOfInterestBlueprint] = {}

        self._faction_units_index: dict[str, list[UnitArchetype]] = {}
        self._faction_equipment_index: dict[str, list[Equipment]] = {}
        self._faction_buildings_index: dict[str, list[Building]] = {}
        self._faction_roster_index: dict[str, list[RosterEntry]] = {}

        self._faction_lords_index: dict[str, list[LegendaryLordTemplate]] = {}
        self._faction_commanders_index: dict[str, list[LegendaryCommanderTemplate]] = {}
        self._faction_heroes_index: dict[str, list[LegendaryHeroTemplate]] = {}

    # ==================================================================
    # КАРТОЧКИ: ЮНИТЫ, СНАРЯЖЕНИЕ, ЗДАНИЯ
    # ==================================================================

    def get_unit_archetype(self, unit_id: str) -> Optional[UnitArchetype]:
        return self._units.get(unit_id)

    def get_equipment(self, equipment_id: str) -> Optional[Equipment]:
        return self._equipment.get(equipment_id)

    def get_building(self, building_id: str) -> Optional[Building]:
        return self._buildings.get(building_id)

    def list_faction_units(self, faction_id: str) -> list[UnitArchetype]:
        return self._faction_units_index.get(faction_id, [])

    def list_faction_equipment(self, faction_id: str) -> list[Equipment]:
        return self._faction_equipment_index.get(faction_id, [])

    def list_faction_buildings(self, faction_id: str) -> list[Building]:
        return self._faction_buildings_index.get(faction_id, [])

    # ==================================================================
    # РОСТЕР НАЙМА
    # ==================================================================

    def get_roster_entry(self, roster_id: str) -> Optional[RosterEntry]:
        return self._roster.get(roster_id)

    def list_faction_roster(self, faction_id: str) -> list[RosterEntry]:
        return self._faction_roster_index.get(faction_id, [])

    # ==================================================================
    # ЛЕГЕНДАРНЫЕ ЛИЧНОСТИ
    # ==================================================================

    def get_legendary_lord(self, lord_id: str) -> Optional[LegendaryLordTemplate]:
        return self._legendary_lords.get(lord_id)

    def get_legendary_commander(
        self, commander_id: str
    ) -> Optional[LegendaryCommanderTemplate]:
        return self._legendary_commanders.get(commander_id)

    def get_legendary_hero(self, hero_id: str) -> Optional[LegendaryHeroTemplate]:
        return self._legendary_heroes.get(hero_id)

    def list_faction_legendary_lords(self, faction_id: str) -> list[LegendaryLordTemplate]:
        return self._faction_lords_index.get(faction_id, [])

    def list_faction_legendary_commanders(
        self, faction_id: str
    ) -> list[LegendaryCommanderTemplate]:
        return self._faction_commanders_index.get(faction_id, [])

    def list_faction_legendary_heroes(
        self, faction_id: str
    ) -> list[LegendaryHeroTemplate]:
        return self._faction_heroes_index.get(faction_id, [])

    # ==================================================================
    # ТОЧКИ ИНТЕРЕСА
    # ==================================================================

    def get_point_of_interest(self, poi_id: str) -> Optional[PointOfInterestBlueprint]:
        return self._points_of_interest.get(poi_id)

    def list_landmark_points_of_interest(self) -> list[PointOfInterestBlueprint]:
        return [poi for poi in self._points_of_interest.values() if poi.is_landmark]

    def list_procedural_points_of_interest(self) -> list[PointOfInterestBlueprint]:
        return [poi for poi in self._points_of_interest.values() if not poi.is_landmark]

    # ==================================================================
    # НАПОЛНЕНИЕ РЕЕСТРА (вызывается только загрузчиком)
    # ==================================================================

    def _add_unit(self, unit: UnitArchetype) -> None:
        self._units[unit.id] = unit
        if unit.faction_id:
            self._faction_units_index.setdefault(unit.faction_id, []).append(unit)

    def _add_equipment(self, eq: Equipment, faction_id: str) -> None:
        self._equipment[eq.id] = eq
        self._faction_equipment_index.setdefault(faction_id, []).append(eq)

    def _add_building(self, building: Building) -> None:
        self._buildings[building.id] = building
        self._faction_buildings_index.setdefault(building.faction_id, []).append(building)

    def _add_roster_entry(self, entry: RosterEntry) -> None:
        self._roster[entry.id] = entry
        self._faction_roster_index.setdefault(entry.faction_id, []).append(entry)

    def _add_legendary_lord(self, lord: LegendaryLordTemplate) -> None:
        self._legendary_lords[lord.id] = lord
        self._faction_lords_index.setdefault(lord.faction_id, []).append(lord)

    def _add_legendary_commander(self, commander: LegendaryCommanderTemplate) -> None:
        self._legendary_commanders[commander.id] = commander
        self._faction_commanders_index.setdefault(commander.faction_id, []).append(commander)

    def _add_legendary_hero(self, hero: LegendaryHeroTemplate) -> None:
        self._legendary_heroes[hero.id] = hero
        self._faction_heroes_index.setdefault(hero.faction_id, []).append(hero)

    def _add_point_of_interest(self, poi: PointOfInterestBlueprint) -> None:
        self._points_of_interest[poi.id] = poi


class SessionGameDataRepository(GameDataRepositoryProtocol):
    """Репозиторий, объединяющий статику и кастомную сессионную экипировку."""

    def __init__(
        self, static_registry: StaticGameDataRegistry, custom_equipment: list[Equipment]
    ) -> None:
        self._static = static_registry
        self._custom_equipment = {eq.id: eq for eq in custom_equipment}

    def get_unit_archetype(self, unit_id: str) -> Optional[UnitArchetype]:
        return self._static.get_unit_archetype(unit_id)

    def get_equipment(self, equipment_id: str) -> Optional[Equipment]:
        if equipment_id in self._custom_equipment:
            return self._custom_equipment[equipment_id]
        return self._static.get_equipment(equipment_id)

    def get_building(self, building_id: str) -> Optional[Building]:
        return self._static.get_building(building_id)

    def list_faction_units(self, faction_id: str) -> list[UnitArchetype]:
        return self._static.list_faction_units(faction_id)

    def list_faction_equipment(self, faction_id: str) -> list[Equipment]:
        static_eq = self._static.list_faction_equipment(faction_id)
        custom_eq = [eq for eq in self._custom_equipment.values() if eq.is_custom]
        return static_eq + custom_eq

    def list_faction_buildings(self, faction_id: str) -> list[Building]:
        return self._static.list_faction_buildings(faction_id)

    # Ростер, легендарные личности и места Ничьей земли партия не меняет,
    # поэтому они целиком делегируются статическому реестру.

    def get_roster_entry(self, roster_id: str) -> Optional[RosterEntry]:
        return self._static.get_roster_entry(roster_id)

    def list_faction_roster(self, faction_id: str) -> list[RosterEntry]:
        return self._static.list_faction_roster(faction_id)

    def get_legendary_lord(self, lord_id: str) -> Optional[LegendaryLordTemplate]:
        return self._static.get_legendary_lord(lord_id)

    def get_legendary_commander(
        self, commander_id: str
    ) -> Optional[LegendaryCommanderTemplate]:
        return self._static.get_legendary_commander(commander_id)

    def get_legendary_hero(self, hero_id: str) -> Optional[LegendaryHeroTemplate]:
        return self._static.get_legendary_hero(hero_id)

    def list_faction_legendary_lords(self, faction_id: str) -> list[LegendaryLordTemplate]:
        return self._static.list_faction_legendary_lords(faction_id)

    def list_faction_legendary_commanders(
        self, faction_id: str
    ) -> list[LegendaryCommanderTemplate]:
        return self._static.list_faction_legendary_commanders(faction_id)

    def list_faction_legendary_heroes(
        self, faction_id: str
    ) -> list[LegendaryHeroTemplate]:
        return self._static.list_faction_legendary_heroes(faction_id)

    def get_point_of_interest(self, poi_id: str) -> Optional[PointOfInterestBlueprint]:
        return self._static.get_point_of_interest(poi_id)

    def list_landmark_points_of_interest(self) -> list[PointOfInterestBlueprint]:
        return self._static.list_landmark_points_of_interest()

    def list_procedural_points_of_interest(self) -> list[PointOfInterestBlueprint]:
        return self._static.list_procedural_points_of_interest()


# ==================================================================
# СБОРКА СТАТИЧЕСКОГО РЕЕСТРА
# ==================================================================


def build_static_registry() -> StaticGameDataRegistry:
    """Сканирует пакеты геймдаты и строит статический реестр."""
    registry = StaticGameDataRegistry()

    for race in RACES:
        _load_faction_module(registry, race, "units.units_list", "UNITS_LIST", _loader_unit)
        _load_faction_module(registry, race, "armor.armor_list", "ARMOR_LIST", _loader_eq)
        _load_faction_module(
            registry, race, "accessories.accessories_list", "ACCESSORIES_LIST", _loader_eq
        )
        _load_faction_module(registry, race, "weapon.melee_list", "MELEE_WEAPONS", _loader_eq)
        _load_faction_module(
            registry, race, "weapon.ranged_list", "RANGED_WEAPONS", _loader_eq
        )
        _load_faction_module(
            registry, race, "buildings.buildings_list", "BUILDINGS_LIST", _loader_bld
        )
        _load_faction_module(registry, race, "roster", "ROSTER_LIST", _loader_roster)

        # Легендарные личности есть не у всех: у наемников нет ни лордов,
        # ни полководцев, а у нейтралов - вообще никого
        # Отсутствующий модуль загрузчик пропускает молча
        _load_faction_module(
            registry, race, "characters.lords_list", "LORDS_LIST", _loader_lord
        )
        _load_faction_module(
            registry, race, "characters.commanders_list", "COMMANDERS_LIST", _loader_commander
        )
        _load_faction_module(
            registry, race, "characters.heroes_list", "HEROES_LIST", _loader_hero
        )

    _load_points_of_interest(registry)

    main_logger.info("Статическая геймдата успешно загружена и провалидирована.")
    return registry


def _load_faction_module(
    registry: StaticGameDataRegistry,
    race: FactionRace,
    module_suffix: str,
    dict_name: str,
    loader_func: Callable[[StaticGameDataRegistry, FactionRace, dict], None],
) -> None:
    module_path = f"src.back.gamedata.{race.value}.{module_suffix}"
    try:
        mod = importlib.import_module(module_path)
        data_dict = getattr(mod, dict_name, {})
        for raw_data in data_dict.values():
            loader_func(registry, race, raw_data)
    except ModuleNotFoundError as e:
        if e.name and module_path.startswith(e.name):
            return
        main_logger.error(f"Ошибка импорта зависимостей внутри {module_path}: {e}")
        raise
    except Exception as e:
        main_logger.error(f"Ошибка при загрузке {module_path}: {e}")
        raise


def _load_points_of_interest(registry: StaticGameDataRegistry) -> None:
    """
    Загружает каталог мест Ничьей земли: он общий для всех рас.
    """
    try:
        mod = importlib.import_module(POINTS_OF_INTEREST_MODULE)
        for raw_data in getattr(mod, "POINTS_OF_INTEREST_LIST", {}).values():
            registry._add_point_of_interest(PointOfInterestBlueprint(**raw_data))
    except ModuleNotFoundError as e:
        if e.name and POINTS_OF_INTEREST_MODULE.startswith(e.name):
            return
        main_logger.error(f"Ошибка импорта зависимостей внутри {POINTS_OF_INTEREST_MODULE}: {e}")
        raise
    except Exception as e:
        main_logger.error(f"Ошибка при загрузке {POINTS_OF_INTEREST_MODULE}: {e}")
        raise


def _loader_unit(registry: StaticGameDataRegistry, race: FactionRace, raw: dict) -> None:
    registry._add_unit(UnitArchetype(**raw))


def _loader_eq(registry: StaticGameDataRegistry, race: FactionRace, raw: dict) -> None:
    registry._add_equipment(Equipment(**raw), faction_id=race.value)


def _loader_bld(registry: StaticGameDataRegistry, race: FactionRace, raw: dict) -> None:
    registry._add_building(Building(**raw))


def _loader_roster(registry: StaticGameDataRegistry, race: FactionRace, raw: dict) -> None:
    registry._add_roster_entry(RosterEntry(**raw))


def _loader_lord(registry: StaticGameDataRegistry, race: FactionRace, raw: dict) -> None:
    registry._add_legendary_lord(LegendaryLordTemplate(**raw))


def _loader_commander(
    registry: StaticGameDataRegistry, race: FactionRace, raw: dict
) -> None:
    registry._add_legendary_commander(LegendaryCommanderTemplate(**raw))


def _loader_hero(registry: StaticGameDataRegistry, race: FactionRace, raw: dict) -> None:
    registry._add_legendary_hero(LegendaryHeroTemplate(**raw))
