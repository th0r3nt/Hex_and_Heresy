"""
Загрузчик статической геймдаты.
Считывает словари из пакета src.back.gamedata, валидирует их через Pydantic
и предоставляет in-memory реестр, реализующий GameDataRepositoryProtocol.
Также содержит SessionGameDataRepository для объединения статики и кастомных предметов сессии.
"""

import importlib
from typing import Callable, Optional

from src.back.gamedata.common import RACES
from src.back.l01_domain.army.models.card.equipment import Equipment
from src.back.l01_domain.army.models.card.unit import UnitArchetype
from src.back.l01_domain.army.models.characters.commanders import (
    CommanderArchetype,
    CommanderTrait,
)
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.models.buildings import Building
from src.back.l01_domain.protocols.gamedata import GameDataRepositoryProtocol
from src.back.utils.logger import main_logger


class StaticGameDataRegistry(GameDataRepositoryProtocol):
    """
    Read-only реестр статических данных игры.
    Инициализируется один раз при старте сервера.
    """

    def __init__(self) -> None:
        self._units: dict[str, UnitArchetype] = {}
        self._equipment: dict[str, Equipment] = {}
        self._buildings: dict[str, Building] = {}
        self._commander_archetypes: dict[str, CommanderArchetype] = {}
        self._commander_traits: dict[str, CommanderTrait] = {}

        self._faction_units_index: dict[str, list[UnitArchetype]] = {}
        self._faction_equipment_index: dict[str, list[Equipment]] = {}
        self._faction_buildings_index: dict[str, list[Building]] = {}

    def get_unit_archetype(self, unit_id: str) -> Optional[UnitArchetype]:
        return self._units.get(unit_id)

    def get_equipment(self, equipment_id: str) -> Optional[Equipment]:
        return self._equipment.get(equipment_id)

    def get_building(self, building_id: str) -> Optional[Building]:
        return self._buildings.get(building_id)

    def get_commander_archetype(self, archetype_id: str) -> Optional[CommanderArchetype]:
        return self._commander_archetypes.get(archetype_id)

    def get_commander_trait(self, trait_id: str) -> Optional[CommanderTrait]:
        return self._commander_traits.get(trait_id)

    def list_faction_units(self, faction_id: str) -> list[UnitArchetype]:
        return self._faction_units_index.get(faction_id, [])

    def list_faction_equipment(self, faction_id: str) -> list[Equipment]:
        return self._faction_equipment_index.get(faction_id, [])

    def list_faction_buildings(self, faction_id: str) -> list[Building]:
        return self._faction_buildings_index.get(faction_id, [])

    # Методы для заполнения реестра при загрузке
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


class SessionGameDataRepository(GameDataRepositoryProtocol):
    """
    Репозиторий, объединяющий статические данные и кастомные предметы
    (созданные Оружейником), которые принадлежат конкретной игровой сессии.
    Именно этот класс будет инжектироваться в сервисы при активной игре.
    """

    def __init__(
        self, static_registry: StaticGameDataRegistry, custom_equipment: list[Equipment]
    ) -> None:
        self._static = static_registry
        self._custom_equipment = {eq.id: eq for eq in custom_equipment}

    def get_unit_archetype(self, unit_id: str) -> Optional[UnitArchetype]:
        return self._static.get_unit_archetype(unit_id)

    def get_equipment(self, equipment_id: str) -> Optional[Equipment]:
        # Сначала проверяем сессионные кастомные чертежи, затем статику
        if equipment_id in self._custom_equipment:
            return self._custom_equipment[equipment_id]
        return self._static.get_equipment(equipment_id)

    def get_building(self, building_id: str) -> Optional[Building]:
        return self._static.get_building(building_id)

    def get_commander_archetype(self, archetype_id: str) -> Optional[CommanderArchetype]:
        return self._static.get_commander_archetype(archetype_id)

    def get_commander_trait(self, trait_id: str) -> Optional[CommanderTrait]:
        return self._static.get_commander_trait(trait_id)

    def list_faction_units(self, faction_id: str) -> list[UnitArchetype]:
        return self._static.list_faction_units(faction_id)

    def list_faction_equipment(self, faction_id: str) -> list[Equipment]:
        # Смешиваем статическую экипировку фракции с кастомной сессионной
        static_eq = self._static.list_faction_equipment(faction_id)
        custom_eq = [eq for eq in self._custom_equipment.values() if eq.is_custom]
        return static_eq + custom_eq

    def list_faction_buildings(self, faction_id: str) -> list[Building]:
        return self._static.list_faction_buildings(faction_id)


def build_static_registry() -> StaticGameDataRegistry:
    """
    Сканирует пакеты геймдаты, собирает все словари, валидирует их
    и формирует итоговый статический реестр. Вызывается при запуске приложения.
    """
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

    main_logger.info("Статическая геймдата успешно загружена и провалидирована.")
    return registry


def _load_faction_module(
    registry: StaticGameDataRegistry,
    race: FactionRace,
    module_suffix: str,
    dict_name: str,
    loader_func: Callable[[StaticGameDataRegistry, FactionRace, dict], None],
) -> None:
    """
    Безопасно импортирует модуль геймдаты и передает его парсеру.
    Имя пакета в каталоге gamedata совпадает со значением FactionRace.
    """

    module_path = f"src.back.gamedata.{race.value}.{module_suffix}"
    try:
        mod = importlib.import_module(module_path)
        data_dict = getattr(mod, dict_name, {})
        for raw_data in data_dict.values():
            loader_func(registry, race, raw_data)
    except ModuleNotFoundError as e:
        # Если отсутствует сам файл или любая из его родительских папок
        # (например, у наемников или нейтралов нет папки buildings), безопасно пропускаем
        if e.name and module_path.startswith(e.name):
            return
        main_logger.error(f"Ошибка импорта зависимостей внутри {module_path}: {e}")
        raise
    except Exception as e:
        main_logger.error(f"Ошибка при загрузке {module_path}: {e}")
        raise


def _loader_unit(registry: StaticGameDataRegistry, race: FactionRace, raw: dict) -> None:
    registry._add_unit(UnitArchetype(**raw))


def _loader_eq(registry: StaticGameDataRegistry, race: FactionRace, raw: dict) -> None:
    registry._add_equipment(Equipment(**raw), faction_id=race.value)


def _loader_bld(registry: StaticGameDataRegistry, race: FactionRace, raw: dict) -> None:
    registry._add_building(Building(**raw))
