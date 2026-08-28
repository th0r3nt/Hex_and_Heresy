"""
Сервис гарнизонов земель: подъем ополчения, его восстановление после
штурмов и ротация регулярных войск между полем и стенами.

Гарнизон - не постройка, а свойство самой земли, поэтому сервис на каждом
такте сам следит за тем, чтобы у каждой подконтрольной фракции земли с
цитаделью или ратушей был гарнизон нужного размера. Отдельного приказа
"построить гарнизон" в игре нет и быть не должно.
"""

from typing import Optional

from src.back.l01_domain.army.models.card.equipment import Equipment
from src.back.l01_domain.army.models.card.roster import RosterEntry
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.exceptions.factions import (
    GarrisonNotFoundError,
    GarrisonRotationForbiddenError,
    ZoneNotControlledError,
)
from src.back.l01_domain.exceptions.workers import InvalidAssignmentTargetError
from src.back.l01_domain.factions.constants import MILITIA_ALLOWED_TIERS
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.garrison import Garrison
from src.back.l01_domain.maps.constants import ALLIED_LANDS_RING_RADIUS
from src.back.l01_domain.maps.models.strategic import (
    HexCoordinates,
    hex_ring,
    hex_zone_id,
)
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.protocols.gamedata import GameDataRepositoryProtocol
from src.back.l01_domain.world.models.reports import GarrisonStepReport
from src.back.l01_domain.world.models.state import WorldState
from src.back.utils.event.registry import GameEvents

# Резервное ополчение на случай пустого каталога: безымянные горожане с вилами
FALLBACK_MILITIA_UNIT_ID = "unit_neu_town_militia_01"
FALLBACK_MILITIA_NAME = "Городское ополчение"
FALLBACK_MILITIA_UNIT_COUNT = 80


class GarrisonService:
    """
    Обслуживает гарнизоны всех земель мира на глобальном такте и исполняет
    приказы игрока на расквартирование войск.
    """

    def __init__(
        self,
        gamedata: Optional[GameDataRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._gamedata = gamedata
        self._event_bus = event_bus

    # ==================================================================
    # ШАГ ГЛОБАЛЬНОГО ТАКТА
    # ==================================================================

    async def process_garrisons(self, world_state: WorldState) -> GarrisonStepReport:
        """
        Приводит гарнизоны мира в соответствие с картой за один такт:
        снимает гарнизоны потерянных земель, поднимает недостающие,
        подгоняет ополчение под уровень здания и лечит его потери.
        """
        report = GarrisonStepReport()

        report.disbanded_garrison_zone_ids = self._drop_lost_garrisons(world_state)

        for faction in world_state.factions.values():
            await self._sync_faction_garrisons(
                faction=faction, world_state=world_state, report=report
            )

        report.replenished_militia_squad_ids = await self._replenish_all_militia(world_state)

        return report

    def _drop_lost_garrisons(self, world_state: WorldState) -> list[str]:
        """
        Убирает гарнизоны земель, которые фракция больше не контролирует
        (гекс отбит врагом либо фракция выбыла из партии).
        """
        dropped: list[str] = []

        for zone_id, garrison in list(world_state.garrisons.items()):
            faction = world_state.get_faction(garrison.faction_id)
            if faction is not None and self._owns_zone(faction, zone_id):
                continue

            world_state.remove_garrison(zone_id)
            dropped.append(zone_id)

        return dropped

    async def _sync_faction_garrisons(
        self,
        faction: Faction,
        world_state: WorldState,
        report: GarrisonStepReport,
    ) -> None:
        """
        Проверяет каждую административную землю фракции: цитадель и союзные
        ратуши. Где гарнизона нет - поднимает, где есть - сверяет ополчение
        с текущим уровнем здания.
        """
        for zone_id, coord, level in self._administrative_zones(faction):
            garrison = world_state.get_garrison(zone_id)

            if garrison is None:
                garrison = Garrison(
                    zone_id=zone_id,
                    faction_id=faction.id,
                    hex_coordinates=coord,
                )
                world_state.add_garrison(garrison)
                report.raised_garrison_zone_ids.append(zone_id)

                if self._event_bus is not None:
                    await self._event_bus.publish(
                        GameEvents.Strategic.GARRISON_RAISED,
                        faction_id=faction.id,
                        zone_id=zone_id,
                        hex=coord.model_dump(),
                    )

            await self._sync_militia(
                garrison=garrison, faction=faction, level=level, report=report
            )

    def _administrative_zones(
        self, faction: Faction
    ) -> list[tuple[str, HexCoordinates, int]]:
        """
        Земли фракции, у которых есть свой административный центр, вместе с
        его уровнем: гекс цитадели, ее лепестки с ратушами, а также каждый
        пограничный город и выкупленные им земли.

        Именно уровень центра задает вместимость городского ополчения, поэтому
        город четвертого уровня держит гарнизон крупнее, чем любая ратуша.
        """
        zones: list[tuple[str, HexCoordinates, int]] = []

        if faction.capital_hex is not None:
            zones.append(
                (
                    hex_zone_id(faction.capital_hex),
                    faction.capital_hex,
                    faction.headquarters.level,
                )
            )
            for coord in hex_ring(faction.capital_hex, ALLIED_LANDS_RING_RADIUS):
                zones.extend(self._regional_hall_zone(faction, coord))

        # Пограничные города - такие же административные центры, только
        # стоят они где угодно на карте, а их земли покупались поштучно
        for town in faction.border_towns:
            zones.append((town.zone_id, town.center_hex, town.level))
            for coord in town.claimed_hexes:
                zones.extend(self._regional_hall_zone(faction, coord))

        return zones

    def _regional_hall_zone(
        self, faction: Faction, coord: HexCoordinates
    ) -> list[tuple[str, HexCoordinates, int]]:
        """
        Земля с ратушей в виде готовой строки для _administrative_zones -
        либо пустой список, если земля потеряна или ратуши на ней нет.

        Список, а не Optional: вызывающей стороне так удобнее собирать
        зоны обоих видов в один плоский перечень.
        """
        zone_id = hex_zone_id(coord)
        if not self._owns_zone(faction, zone_id):
            return []

        hall = faction.get_regional_hall(zone_id)
        if hall is None:
            return []

        return [(zone_id, coord, hall.level)]

    @staticmethod
    def _owns_zone(faction: Faction, zone_id: str) -> bool:
        """
        Контролирует ли фракция землю. Гекс цитадели в список союзных зон не
        входит, но принадлежит фракции по определению.
        """
        if faction.capital_hex is not None and hex_zone_id(faction.capital_hex) == zone_id:
            return True
        return zone_id in faction.controlled_zone_ids

    async def _sync_militia(
        self,
        garrison: Garrison,
        faction: Faction,
        level: int,
        report: GarrisonStepReport,
    ) -> None:
        """
        Подгоняет число ополченцев под уровень цитадели/ратуши: апгрейд
        открывает слот и земля тут же поднимает новый отряд.
        """
        raised, disbanded = garrison.sync_militia_capacity(
            level=level, recruit=lambda: self._build_militia_squad(faction)
        )
        if not raised and not disbanded:
            return

        report.raised_militia_squad_ids.extend(squad.id for squad in raised)
        report.disbanded_militia_squad_ids.extend(squad.id for squad in disbanded)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Strategic.MILITIA_CAPACITY_SYNCED,
                faction_id=faction.id,
                zone_id=garrison.zone_id,
                level=level,
                raised_count=len(raised),
                disbanded_count=len(disbanded),
            )

    async def _replenish_all_militia(self, world_state: WorldState) -> list[str]:
        """
        Дает всем гарнизонам мира добрать потери ополчения за такт.
        Гарнизон, застрявший в бою, не лечится: горожан некогда обучать
        посреди штурма.
        """
        replenished_ids: list[str] = []

        for garrison in world_state.garrisons.values():
            if garrison.is_locked_in_battle:
                continue

            healed = garrison.replenish_militia_losses()
            if not healed:
                continue

            replenished_ids.extend(healed)

            if self._event_bus is not None:
                await self._event_bus.publish(
                    GameEvents.Strategic.MILITIA_REPLENISHED,
                    faction_id=garrison.faction_id,
                    zone_id=garrison.zone_id,
                    squad_ids=healed,
                )

        return replenished_ids

    # ==================================================================
    # ПРИКАЗЫ ИГРОКА: РОТАЦИЯ ВОЙСК
    # ==================================================================

    async def station_squad(
        self,
        world_state: WorldState,
        army_id: str,
        squad_id: str,
        zone_id: str,
    ) -> Garrison:
        """
        Переводит отряд из мобильной армии за стены земли.

        Армия должна стоять на самом гексе гарнизона: отряд нельзя оставить
        в крепости, находясь от нее в трех днях марша.
        """
        garrison = self._require_garrison(world_state, zone_id)
        army = self._require_army(world_state, army_id)

        if army.faction_id != garrison.faction_id:
            raise ZoneNotControlledError(faction_id=army.faction_id, zone_id=zone_id)
        if army.is_in_tactical_battle:
            raise GarrisonRotationForbiddenError(zone_id, "армия связана тактическим боем")
        if army.current_hex != garrison.hex_coordinates:
            raise GarrisonRotationForbiddenError(
                zone_id, "армия находится не на гексе гарнизона"
            )

        squad = next((s for s in army.squads if s.id == squad_id), None)
        if squad is None:
            raise GarrisonRotationForbiddenError(
                zone_id, f"отряда '{squad_id}' нет в этой армии"
            )

        # Сначала проверка лимита самим гарнизоном, и только потом изъятие
        # отряда из армии: иначе отказ оставил бы отряд вообще нигде.
        garrison.station_squad(squad)
        army.remove_squad(squad_id)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Strategic.SQUAD_STATIONED,
                faction_id=garrison.faction_id,
                zone_id=zone_id,
                army_id=army_id,
                squad_id=squad_id,
                squad_name=squad.display_name,
            )

        return garrison

    async def unstation_squad(
        self,
        world_state: WorldState,
        army_id: str,
        squad_id: str,
        zone_id: str,
    ) -> Squad:
        """
        Забирает расквартированный отряд обратно в мобильную армию.
        Городское ополчение так вывести нельзя - оно привязано к своей земле.
        """
        garrison = self._require_garrison(world_state, zone_id)
        army = self._require_army(world_state, army_id)

        if army.faction_id != garrison.faction_id:
            raise ZoneNotControlledError(faction_id=army.faction_id, zone_id=zone_id)
        if army.is_in_tactical_battle:
            raise GarrisonRotationForbiddenError(zone_id, "армия связана тактическим боем")
        if army.current_hex != garrison.hex_coordinates:
            raise GarrisonRotationForbiddenError(
                zone_id, "армия находится не на гексе гарнизона"
            )

        squad = garrison.unstation_squad(squad_id)
        army.add_squad(squad)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Strategic.SQUAD_UNSTATIONED,
                faction_id=garrison.faction_id,
                zone_id=zone_id,
                army_id=army_id,
                squad_id=squad_id,
                squad_name=squad.display_name,
            )

        return squad

    # ==================================================================
    # ОБОРОНА ЗЕМЛИ
    # ==================================================================

    @staticmethod
    def collect_defenders(world_state: WorldState, coord: HexCoordinates) -> list[Squad]:
        """
        Защитники, которых земля выставляет в тактический бой на своем гексе:
        все ополчение плюс все расквартированные войска.

        Мобильные армии на гексе сюда не входят - их собирает бой по своим
        локам (см. TurnsFacade.execute_tactical_turn).
        """
        garrison = world_state.get_garrison_at(coord)
        return list(garrison.all_squads) if garrison is not None else []

    # ==================================================================
    # ВСПОМОГАТЕЛЬНОЕ
    # ==================================================================

    @staticmethod
    def _require_garrison(world_state: WorldState, zone_id: str) -> Garrison:
        garrison = world_state.get_garrison(zone_id)
        if garrison is None:
            raise GarrisonNotFoundError(zone_id)
        return garrison

    @staticmethod
    def _require_army(world_state: WorldState, army_id: str) -> StrategicArmy:
        army = world_state.get_army(army_id)
        if army is None:
            raise InvalidAssignmentTargetError(army_id, "армия не найдена")
        return army

    def _build_militia_squad(self, faction: Faction) -> Squad:
        """
        Поднимает один отряд городского ополчения из расового каталога.

        Ополчение - это вооруженные горожане, поэтому берется самый дешевый
        рецепт найма разрешенных тиров. Без каталога поднимается резервная
        толпа с вилами: партия не должна падать из-за неполной геймдаты.
        """
        entry = self._pick_militia_roster_entry(faction)
        if entry is None:
            return Squad.create_new(archetype=self._fallback_militia_archetype(faction))

        archetype = self._gamedata.get_unit_archetype(entry.unit_archetype_id)
        if archetype is None:
            return Squad.create_new(archetype=self._fallback_militia_archetype(faction))

        return Squad.create_new(
            archetype=archetype,
            weapon=self._get_equipment(entry.weapon_id),
            armor=self._get_equipment(entry.armor_id),
            accessory=self._get_equipment(entry.accessory_id),
        )

    def _pick_militia_roster_entry(self, faction: Faction) -> Optional[RosterEntry]:
        """
        Выбирает рецепт ополчения: самый дешевый отряд разрешенного тира.

        Сортировка добивается id, чтобы состав гарнизона был воспроизводим
        при одинаковой геймдате - от этого зависят тесты и сохранения.
        """
        if self._gamedata is None:
            return None

        candidates = [
            entry
            for entry in self._gamedata.list_faction_roster(faction.race_id)
            if self._is_militia_grade(entry)
        ]
        if not candidates:
            return None

        return min(candidates, key=lambda e: (e.cost_gold + e.cost_material, e.id))

    def _is_militia_grade(self, entry: RosterEntry) -> bool:
        """Годится ли рецепт найма в городское ополчение по тиру юнита."""
        archetype = self._gamedata.get_unit_archetype(entry.unit_archetype_id)
        return archetype is not None and archetype.tier in MILITIA_ALLOWED_TIERS

    def _get_equipment(self, equipment_id: Optional[str]) -> Optional[Equipment]:
        """Достает снаряжение из каталога, если рецепт его называет."""
        if equipment_id is None or self._gamedata is None:
            return None
        return self._gamedata.get_equipment(equipment_id)

    @staticmethod
    def _fallback_militia_archetype(faction: Faction) -> UnitArchetype:
        """
        Резервный архетип ополчения на случай, если в каталоге расы не нашлось
        ни одного подходящего рецепта.
        """
        return UnitArchetype(
            id=FALLBACK_MILITIA_UNIT_ID,
            race=faction.race,
            faction_id=faction.race_id,
            name=FALLBACK_MILITIA_NAME,
            tier=MILITIA_ALLOWED_TIERS[0],
            default_unit_count=FALLBACK_MILITIA_UNIT_COUNT,
            base_stats=BaseUnitStats(max_hp=12.0, base_morale=40.0),
            base_upkeep_food=1.0,
            base_upkeep_gold=0.1,
        )
