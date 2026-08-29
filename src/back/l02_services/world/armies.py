"""
Стартовая армия державы: два отряда рабочих и два отряда линейной пехоты на
гексе цитадели.

Полководца у нее нет намеренно - без лидера армия не марширует и стоит на
базе, пока игрок или ИИ не назначит ей командующего.
"""

from typing import Optional

from src.back.l01_domain.army.models.card.equipment import Equipment
from src.back.l01_domain.army.models.card.roster import RosterEntry
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.protocols.gamedata import GameDataRepositoryProtocol
from src.back.l01_domain.world.constants import (
    STARTING_ARMY_INFANTRY_SQUADS,
    STARTING_ARMY_NAME,
    STARTING_ARMY_WORKER_SQUADS,
    STARTING_INFANTRY_UNIT_TIER,
    WORKER_UNIT_TIER,
)
from src.back.utils.logger import main_logger


class StartingArmyBuilder:
    """
    Набирает армию нулевого такта из расового ростера.
    """

    def __init__(self, gamedata: GameDataRepositoryProtocol) -> None:
        self._gamedata = gamedata

    # ==================================================================
    # АРМИЯ ЦЕЛИКОМ
    # ==================================================================

    def build(self, faction: Faction, capital_hex: HexCoordinates) -> StrategicArmy:
        """
        Собирает армию нулевого такта на гексе цитадели: два отряда рабочих и
        два отряда регулярной пехоты, без полководца.
        """
        squads = [
            *self._recruit_squads(
                faction.race, WORKER_UNIT_TIER, STARTING_ARMY_WORKER_SQUADS
            ),
            *self._recruit_squads(
                faction.race, STARTING_INFANTRY_UNIT_TIER, STARTING_ARMY_INFANTRY_SQUADS
            ),
        ]

        return StrategicArmy(
            faction_id=faction.id,
            name=STARTING_ARMY_NAME,
            commander=None,
            squads=squads,
            current_hex=capital_hex,
        )

    # ==================================================================
    # НАБОР ОТРЯДОВ
    # ==================================================================

    def _recruit_squads(self, race: FactionRace, tier: int, count: int) -> list[Squad]:
        """
        Набирает нужное число одинаковых отрядов заданного тира.

        Отряды намеренно одинаковые: на нулевом такте держава выставляет
        простейшее, что у нее есть, - рабочую артель и линейную пехоту, а не
        сборную солянку из всего ростера.
        """
        entry = self._cheapest_roster_entry(race, tier)
        if entry is None:
            main_logger.warning(
                f"В ростере расы '{race.value}' нет отрядов тира {tier}: "
                "стартовая армия выйдет неполной."
            )
            return []

        return [self._build_squad(entry) for _ in range(count)]

    def _cheapest_roster_entry(
        self, race: FactionRace, tier: int
    ) -> Optional[RosterEntry]:
        """
        Самый дешевый рецепт найма нужного тира в расовом ростере.

        Дешевле всего расе обходятся именно ее рабочие и ее линейная пехота,
        поэтому цена и служит отбором. Ничью добивает идентификатор: состав
        стартовой армии должен быть воспроизводим при одинаковой геймдате.
        """
        candidates = [
            entry
            for entry in self._gamedata.list_faction_roster(race.value)
            if self._archetype_tier(entry) == tier
        ]
        if not candidates:
            return None

        return min(candidates, key=lambda e: (e.cost_gold + e.cost_material, e.id))

    def _archetype_tier(self, entry: RosterEntry) -> Optional[int]:
        """Тир юнита, которого поднимает этот рецепт найма."""
        archetype = self._gamedata.get_unit_archetype(entry.unit_archetype_id)
        return None if archetype is None else archetype.tier

    def _build_squad(self, entry: RosterEntry) -> Squad:
        """
        Собирает отряд по рецепту найма вместе с положенным снаряжением.
        """
        return Squad.create_new(
            archetype=self._gamedata.get_unit_archetype(entry.unit_archetype_id),
            weapon=self._get_equipment(entry.weapon_id),
            armor=self._get_equipment(entry.armor_id),
            accessory=self._get_equipment(entry.accessory_id),
        )

    def _get_equipment(self, equipment_id: Optional[str]) -> Optional[Equipment]:
        """Достает снаряжение из каталога, если рецепт его называет."""
        if equipment_id is None:
            return None
        return self._gamedata.get_equipment(equipment_id)
