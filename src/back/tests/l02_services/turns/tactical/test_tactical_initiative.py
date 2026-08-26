"""
Тесты расчета тактической инициативы и очередности.
"""

from src.back.l01_domain.army.models.characters.traits import get_trait
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.characters.commanders import (
    Commander,
    CommanderCharacteristics,
    CommanderGenerationType,
)
from src.back.l02_services.turns.tactical.initiative import TacticalInitiativeService


class TestTacticalInitiativeService:
    def test_calculate_squad_initiative_base(self, archetype_human_sword):
        squad = Squad.create_new(archetype=archetype_human_sword)
        service = TacticalInitiativeService()

        # Базовая = 10
        init = service.calculate_squad_initiative(squad)
        assert init == 10

    def test_calculate_squad_initiative_with_equipment(
        self, archetype_human_sword, weapon_sword
    ):
        heavy_weapon = weapon_sword.model_copy(
            update={"stats": weapon_sword.stats.model_copy(update={"initiative_modifier": -2})}
        )
        squad = Squad.create_new(archetype=archetype_human_sword, weapon=heavy_weapon)
        service = TacticalInitiativeService()

        init = service.calculate_squad_initiative(squad)
        assert init == 8

    def test_calculate_squad_initiative_with_commander(self, archetype_human_sword):
        squad = Squad.create_new(archetype=archetype_human_sword)

        commander = Commander(
            name="Лорд",
            faction_id="humans",
            generation_type=CommanderGenerationType.PROCEDURAL,
            characteristics=CommanderCharacteristics(tactical_acumen=20),
            traits=[get_trait("cynic")],  # дает +2 к инициативе
        )

        service = TacticalInitiativeService()
        init = service.calculate_squad_initiative(squad, commander=commander)

        # 10 (база) + 2 (acumen 20 // 10) + 2 (черта cynic) = 14
        assert init == 14
        
    def test_exhaustion_and_panic_penalties(self, archetype_human_sword):
        squad = Squad.create_new(archetype=archetype_human_sword)
        squad.state.is_exhausted = True
        squad.state.is_in_panic = True

        service = TacticalInitiativeService()
        init = service.calculate_squad_initiative(squad)

        # 10 - 5 (exhaustion) - 10 (panic) = -5
        assert init == -5

    def test_get_turn_order_sorting_and_tie_breakers(
        self, archetype_human_sword, empty_battle_state
    ):
        sq1 = Squad.create_new(archetype=archetype_human_sword)
        sq1.id = "squad_a"  # Инициатива 10
        sq2 = Squad.create_new(archetype=archetype_human_sword)
        sq2.id = "squad_b"  # Инициатива 10

        # squad_b - защитник (приоритет при равной инициативе)
        empty_battle_state.attacker_squad_ids = ["squad_a"]
        empty_battle_state.defender_squad_ids = ["squad_b"]

        service = TacticalInitiativeService()
        order = service.get_turn_order(
            squads={"squad_a": sq1, "squad_b": sq2}, battle_state=empty_battle_state
        )

        # squad_b выигрывает тай-брейк из-за того, что защитник
        assert order == ["squad_b", "squad_a"]
