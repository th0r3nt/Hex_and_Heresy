"""
Сквозной End-to-End интеграционный тест полного жизненного цикла тактического боя:
расстановка -> стрельба -> таран и встречные удары -> рукопашная схватка ->
моральный шок -> горы трупов -> определение победителя и создание трофеев.
"""

import pytest

from src.back.l01_domain.army.constants import (
    EquipmentSlot,
    EquipmentTag,
    UnitSizeCategory,
    WeaponCategory,
)
from src.back.l01_domain.army.models.card.equipment import Equipment, EquipmentStats
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.combat.constants import (
    BattleMapSize,
    BattlePhase,
    ReactionType,
    SPEED_CHARGE_PACE,
    SPEED_MARCH_PACE,
)
from src.back.l01_domain.combat.models.state import (
    SquadOrder,
    TacticalBattleState,
    TacticalCellState,
)
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.maps.models.tactical import CellCoordinates
from src.back.l02_services.turns.tactical.orchestrator import TacticalTurnOrchestrator
from src.back.utils.event.registry import GameEvents


class FakeEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, event_name: str, *args, **kwargs) -> None:
        self.published.append((event_name, kwargs))


def _build_14x14_battle_state() -> TacticalBattleState:
    state = TacticalBattleState(map_size=BattleMapSize.SMALL)
    for x in range(14):
        for y in range(14):
            state.cells.append(TacticalCellState(coordinates=CellCoordinates(x=x, y=y)))
    return state


def _place(battle_state: TacticalBattleState, squad_id: str, x: int, y: int) -> None:
    for cell in battle_state.cells:
        if cell.coordinates.x == x and cell.coordinates.y == y:
            cell.occupant_squad_id = squad_id
            break


class TestTacticalBattleLifecycleE2E:
    @pytest.mark.asyncio
    async def test_full_multiturn_battle_simulation(self):
        fake_bus = FakeEventBus()
        orchestrator = TacticalTurnOrchestrator(event_bus=fake_bus)
        battle_hex = HexCoordinates.from_axial(3, -1)

        # 1. Формирование войск атакующей стороны (Люди)
        human_infantry_arch = UnitArchetype(
            id="unit_human_swords",
            race=FactionRace.HUMANS,
            faction_id="humans",
            name="Имперские мечники",
            tier=1,
            default_unit_count=100,
            base_stats=BaseUnitStats(
                max_hp=20.0,
                base_speed=2.0,
                base_morale=60.0,
                size_category=UnitSizeCategory.MEDIUM,
            ),
        )
        human_archers_arch = UnitArchetype(
            id="unit_human_bowmen",
            race=FactionRace.HUMANS,
            faction_id="humans",
            name="Имперские лучники",
            tier=1,
            default_unit_count=80,
            base_stats=BaseUnitStats(
                max_hp=15.0,
                base_speed=2.0,
                base_morale=50.0,
                size_category=UnitSizeCategory.MEDIUM,
            ),
        )

        sword = Equipment(
            id="wpn_sword_01",
            name="Меч",
            lore="...",
            slot=EquipmentSlot.WEAPON,
            category=WeaponCategory.SWORD,
            tags={EquipmentTag.ONE_HANDED},
            tier=1,
            stats=EquipmentStats(damage=6.0, armor_piercing=1.0),
        )
        longbow = Equipment(
            id="wpn_bow_01",
            name="Длинный лук",
            lore="...",
            slot=EquipmentSlot.WEAPON,
            category=WeaponCategory.BOW,
            tags={EquipmentTag.STRING_BASED, EquipmentTag.TWO_HANDED},
            tier=1,
            stats=EquipmentStats(damage=8.0, range_hexes=6),
        )

        squad_swords = Squad.create_new(archetype=human_infantry_arch, weapon=sword)
        squad_swords.id = "squad_swords"
        squad_archers = Squad.create_new(archetype=human_archers_arch, weapon=longbow)
        squad_archers.id = "squad_archers"

        # 2. Формирование войск защищающейся стороны (Зеленокожие)
        orc_choppas_arch = UnitArchetype(
            id="unit_orc_boyz",
            race=FactionRace.GREENSKINS,
            faction_id="greenskins",
            name="Орки-рубилы",
            tier=1,
            default_unit_count=100,
            base_stats=BaseUnitStats(
                max_hp=25.0,
                base_speed=2.0,
                base_morale=45.0,
                size_category=UnitSizeCategory.MEDIUM,
            ),
        )
        choppa = Equipment(
            id="wpn_choppa",
            name="Тесак",
            lore="...",
            slot=EquipmentSlot.WEAPON,
            category=WeaponCategory.AXE,
            tags={EquipmentTag.ONE_HANDED},
            tier=1,
            stats=EquipmentStats(damage=7.0),
        )
        squad_orcs = Squad.create_new(archetype=orc_choppas_arch, weapon=choppa)
        squad_orcs.id = "squad_orcs"

        squads = {
            "squad_swords": squad_swords,
            "squad_archers": squad_archers,
            "squad_orcs": squad_orcs,
        }

        # 3. Инициализация поля боя с разделением на коридоры (мечники на y=1, лучники и орки на y=2)
        battle_state = _build_14x14_battle_state()
        battle_state.attacker_squad_ids = ["squad_swords", "squad_archers"]
        battle_state.defender_squad_ids = ["squad_orcs"]

        _place(battle_state, "squad_swords", 1, 1)  # Мечники на коридоре y=1
        _place(battle_state, "squad_archers", 0, 2)  # Лучники на коридоре y=2
        _place(battle_state, "squad_orcs", 5, 2)  # Орки на коридоре y=2

        # =========================================================================
        # РАУНД 1: Прямой залп лучников по свободной линии y=2 и сближение мечников по y=1
        # =========================================================================

        # Лучники стреляют по оркам (линия огня y=2 свободна от союзников)
        battle_state.queue_order(
            SquadOrder(squad_id="squad_archers", target_cell=CellCoordinates(x=5, y=2))
        )
        # Мечники наступают по коридору y=1: (1, 1) -> (3, 1)
        battle_state.queue_order(
            SquadOrder(
                squad_id="squad_swords",
                target_cell=CellCoordinates(x=3, y=1),
                pace=SPEED_MARCH_PACE,
            )
        )
        # Орки двигаются навстречу по коридору y=2: (5, 2) -> (4, 2)
        battle_state.queue_order(
            SquadOrder(
                squad_id="squad_orcs",
                target_cell=CellCoordinates(x=4, y=2),
                pace=SPEED_MARCH_PACE,
            )
        )

        report_round_1 = await orchestrator.execute_turn(
            battle_state=battle_state,
            squads=squads,
            strategic_hex=battle_hex,
        )

        assert report_round_1.tick == 1
        assert report_round_1.phase == BattlePhase.AFTERMATH
        assert len(report_round_1.ranged_reports) == 1
        assert report_round_1.ranged_reports[0].kills > 0
        assert squad_orcs.state.unit_count < 100
        assert report_round_1.is_battle_finished is False

        # =========================================================================
        # РАУНД 2: Орки с (4, 2) идут на таран мечников на (3, 1), мечники принимают удар
        # =========================================================================

        battle_state.queue_order(
            SquadOrder(
                squad_id="squad_orcs",
                target_cell=CellCoordinates(x=3, y=1),
                pace=SPEED_CHARGE_PACE,
            )
        )
        battle_state.queue_order(
            SquadOrder(
                squad_id="squad_swords",
                target_cell=CellCoordinates(x=3, y=1),
                reaction=ReactionType.ACCEPT_CHARGE,
            )
        )

        report_round_2 = await orchestrator.execute_turn(
            battle_state=battle_state,
            squads=squads,
            strategic_hex=battle_hex,
        )

        assert report_round_2.tick == 2
        assert len(report_round_2.charge_reports) == 1
        charge_rep = report_round_2.charge_reports[0]
        assert charge_rep.reaction == ReactionType.ACCEPT_CHARGE
        assert charge_rep.attacker_deaths > 0  # Орки понесли потери от приема на щиты
        assert charge_rep.defender_deaths > 0  # Мечники также понесли потери

        # =========================================================================
        # РАУНД 3: Добивание орков в рукопашной и фиксация победы
        # =========================================================================

        # Ослабляем орков до критического уровня без бегства
        squad_orcs.state.unit_count = 5
        squad_orcs.state.hp_first_unit = 5.0
        squad_orcs.state.morale = 25.0
        squad_orcs.state.is_in_panic = False

        battle_state.queue_order(
            SquadOrder(squad_id="squad_swords", target_cell=CellCoordinates(x=4, y=2))
        )

        report_round_3 = await orchestrator.execute_turn(
            battle_state=battle_state,
            squads=squads,
            strategic_hex=battle_hex,
        )

        assert report_round_3.tick == 3
        assert report_round_3.is_battle_finished is True
        assert report_round_3.victor_faction_id == "humans"

        # 4. Проверка создания поля брани и трофеев со всех раундов боя
        loot = report_round_3.loot_site
        assert loot is not None
        assert loot.hex_coordinates == battle_hex
        assert loot.origin_battle_id == battle_state.id
        assert loot.residual_resonite > 0.0
        assert len(loot.corpses) > 0
        assert (
            "wpn_choppa" in loot.salvageable_equipment
            or "wpn_sword_01" in loot.salvageable_equipment
        )

        # 5. Проверка событий шины
        event_names = [name for name, _ in fake_bus.published]
        assert GameEvents.Tactical.TURN_STARTED in event_names
        assert GameEvents.Tactical.BATTLE_COMPLETED in event_names
