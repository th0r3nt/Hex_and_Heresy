"""
Три исхода операции над побежденным городом: сожжение, разграбление и
захват.

Здесь собраны только последствия, наступающие в тот такт, когда отсчет
операции дошел до нуля. Кто, когда и вправе ли вообще их запускать - дело
BorderTownResolutionService: этот модуль уже ничего не проверяет и просто
делает то, что решено.
"""

from random import Random
from typing import Optional

from src.back.l01_domain.factions.constants import (
    OCCUPY_LEVEL_DOWNGRADE,
    PILLAGE_BUILDINGS_DESTROY_MAX,
    PILLAGE_BUILDINGS_DESTROY_MIN,
    PILLAGE_LEVEL_DOWNGRADE,
    ResourceType,
)
from src.back.l01_domain.factions.models.border_town import (
    BorderTown,
    BorderTownOperation,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.settlements.border_towns.common import release_hex
from src.back.utils.event.registry import GameEvents


class BorderTownOutcomes:
    """
    Применяет последствия отработавшей операции над городом.
    """

    def __init__(
        self,
        event_bus: Optional[EventBusProtocol] = None,
        rng: Optional[Random] = None,
    ) -> None:
        self._event_bus = event_bus
        # Свой генератор нужен разграблению: какие именно постройки сгорят,
        # решает жребий, а тесту этот жребий надо уметь задать
        self._rng = rng or Random()

    # ==================================================================
    # РАЗРУШЕНИЕ
    # ==================================================================

    async def raze(
        self,
        world_state: WorldState,
        owner: Faction,
        town: BorderTown,
        conqueror: Optional[Faction],
        operation: BorderTownOperation,
    ) -> None:
        """
        Разрушение: города больше нет.

        Постройки сносятся, гарнизоны снимаются, а все гексы поселения -
        и центральный, и выкупленные им земли - возвращаются в Ничью землю.
        Захватчик уносит половину всего, что было в город вложено.
        """
        razed_zone_ids = [town.zone_id, *town.claimed_zone_ids]
        razed_hexes = [town.center_hex, *town.claimed_hexes]

        loot = self._award_loot(conqueror, operation)

        self._demolish_buildings(owner, razed_zone_ids)
        for zone_id in razed_zone_ids:
            world_state.remove_garrison(zone_id)

        # lose_zone стирает город целиком: и его земли, и их ратуши
        owner.lose_zone(town.zone_id)

        for coord in razed_hexes:
            release_hex(world_state, coord)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Economy.BORDER_TOWN_RAZED,
                town_id=town.id,
                town_name=town.name,
                original_faction_id=owner.id,
                conqueror_faction_id=operation.conqueror_faction_id,
                released_zone_ids=razed_zone_ids,
                loot=self._loot_payload(loot),
            )

    # ==================================================================
    # РАЗГРАБЛЕНИЕ
    # ==================================================================

    async def pillage(
        self,
        owner: Faction,
        town: BorderTown,
        conqueror: Optional[Faction],
        operation: BorderTownOperation,
    ) -> None:
        """
        Разграбление: город остается прежнему хозяину, но обескровлен.

        Уровень падает на два, несколько построек внутри стен сгорают, а
        гарнизон восстанавливается сам - со следующего такта и с нуля.
        Добыча самая крупная: победитель ничего не бережет для себя.
        """
        loot = self._award_loot(conqueror, operation)

        levels_lost = town.downgrade(PILLAGE_LEVEL_DOWNGRADE)
        burned_ids = self._demolish_random_buildings(
            faction=owner,
            zone_id=town.zone_id,
            minimum=PILLAGE_BUILDINGS_DESTROY_MIN,
            maximum=PILLAGE_BUILDINGS_DESTROY_MAX,
        )

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Economy.BORDER_TOWN_PILLAGED,
                town_id=town.id,
                town_name=town.name,
                original_faction_id=owner.id,
                conqueror_faction_id=operation.conqueror_faction_id,
                level=town.level,
                levels_lost=levels_lost,
                destroyed_building_ids=burned_ids,
                loot=self._loot_payload(loot),
            )

    # ==================================================================
    # ЗАХВАТ
    # ==================================================================

    async def occupy(
        self,
        world_state: WorldState,
        owner: Faction,
        town: BorderTown,
        conqueror: Optional[Faction],
        operation: BorderTownOperation,
    ) -> None:
        """
        Захват: город и все его земли меняют флаг.

        Внутри стен не остается ни одной постройки - победителю достаются
        голые стены и уровень на единицу ниже, - зато вместе с городом к
        нему переходят выкупленные земли с их ратушами. Добыча за это
        самая скудная: город грабили с оглядкой, он теперь свой.
        """
        if conqueror is None:
            # Победитель успел выбыть из партии, пока шла операция - тогда
            # передавать город некому, и он остается у прежнего хозяина
            return

        loot = self._award_loot(conqueror, operation)

        self._demolish_buildings(owner, [town.zone_id])
        levels_lost = town.downgrade(OCCUPY_LEVEL_DOWNGRADE)

        claimed_zone_ids = town.claimed_zone_ids
        transferred_zone_ids = [town.zone_id, *claimed_zone_ids]

        # Ратуши переезжают к новому хозяину теми же объектами: земля и ее
        # административный центр неразделимы, меняется только флаг над ними
        halls = [
            hall
            for hall in (owner.get_regional_hall(zid) for zid in claimed_zone_ids)
            if hall is not None
        ]

        owner.remove_border_town_at(town.zone_id)
        if town.zone_id in owner.controlled_zone_ids:
            owner.controlled_zone_ids.remove(town.zone_id)

        town.transfer_ownership(conqueror.id)
        conqueror.add_border_town(town)
        for zone_id in transferred_zone_ids:
            conqueror.gain_zone(zone_id)
        for hall in halls:
            hall.faction_id = conqueror.id
            conqueror.add_regional_hall(hall)

        for zone_id in transferred_zone_ids:
            self._rebind_garrison(world_state, zone_id, conqueror.id)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Economy.BORDER_TOWN_OCCUPIED,
                town_id=town.id,
                town_name=town.name,
                original_faction_id=owner.id,
                conqueror_faction_id=conqueror.id,
                level=town.level,
                levels_lost=levels_lost,
                transferred_zone_ids=transferred_zone_ids,
                loot=self._loot_payload(loot),
            )

    # ==================================================================
    # ДОБЫЧА
    # ==================================================================

    @staticmethod
    def _award_loot(
        conqueror: Optional[Faction], operation: BorderTownOperation
    ) -> dict[ResourceType, float]:
        """
        Начисляет победителю его долю от вложений города.

        Доля считается от снимка, снятого в начале операции: то, что фракция
        успела достроить, пока горел ее город, добычи уже не увеличивает.
        """
        loot = operation.loot
        if conqueror is None:
            return loot

        for resource, amount in loot.items():
            conqueror.earn(resource, amount)

        return loot

    @staticmethod
    def _loot_payload(loot: dict[ResourceType, float]) -> dict[str, float]:
        """Добыча в виде, пригодном для сокета: ключи-строки вместо перечисления."""
        return {resource.value: amount for resource, amount in loot.items()}

    # ==================================================================
    # УРОН ИНФРАСТРУКТУРЕ
    # ==================================================================

    @staticmethod
    def _demolish_buildings(faction: Faction, zone_ids: list[str]) -> list[str]:
        """
        Сносит все постройки фракции в перечисленных землях.

        Возвращает id снесенного: событию нужно назвать, что именно сгорело.
        """
        doomed = [b for b in faction.buildings if b.zone_id in zone_ids]
        for building in doomed:
            faction.remove_building(building.id)
        return [building.id for building in doomed]

    def _demolish_random_buildings(
        self, faction: Faction, zone_id: str, minimum: int, maximum: int
    ) -> list[str]:
        """
        Сносит от minimum до maximum случайных построек одной земли.

        Если построек в городе меньше, сгорает все, что было: грабители не
        уходят, не дожрав. Что именно сгорит, решает жребий - у сервиса он
        свой и подменяемый, иначе тест на разграбление был бы невоспроизводим.
        """
        standing = [b for b in faction.buildings if b.zone_id == zone_id]
        if not standing:
            return []

        count = min(len(standing), self._rng.randint(minimum, maximum))
        doomed = self._rng.sample(standing, count)

        for building in doomed:
            faction.remove_building(building.id)

        return [building.id for building in doomed]

    @staticmethod
    def _rebind_garrison(
        world_state: WorldState, zone_id: str, new_faction_id: str
    ) -> None:
        """
        Передает гарнизон земли новому хозяину.

        Прежние защитники в нем не остаются: ополчение - это местные жители
        побежденной фракции, а расквартированные ей войска под чужим флагом
        служить не станут. Свой гарнизон новый владелец поднимет на
        ближайшем такте (см. GarrisonService.process_garrisons).
        """
        garrison = world_state.get_garrison(zone_id)
        if garrison is None:
            return

        garrison.faction_id = new_faction_id
        garrison.militia_squads.clear()
        garrison.stationed_squads.clear()
