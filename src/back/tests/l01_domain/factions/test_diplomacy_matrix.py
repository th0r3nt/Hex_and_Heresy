"""
Тесты матрицы дипломатических отношений: объявление войн, аннуляция пактов,
запрет мирных соглашений во время войны и восстановление отношений.
"""

import pytest

from src.back.l01_domain.exceptions import (
    PactForbiddenDuringWarError,
    WarAllianceWithEnemyForbiddenError,
)
from src.back.l01_domain.factions.constants import DiplomaticStance, ResourceType
from src.back.l01_domain.factions.models.diplomacy.pacts import (
    HostageExchangePact,
    IntelligenceSharingPact,
    NonAggressionPact,
    RightOfPassagePact,
    TradeAgreement,
    VassalPact,
    WarAlliancePact,
)
from src.back.l01_domain.factions.models.diplomacy.relation import DiplomaticRelation


@pytest.fixture
def active_relation() -> DiplomaticRelation:
    rel = DiplomaticRelation(faction_a_id="humans", faction_b_id="elfs")
    rel.trade_agreement = TradeAgreement(
        give_resource=ResourceType.FOOD,
        give_amount=50.0,
        get_resource=ResourceType.GOLD,
        get_amount=30.0,
        duration_turns=5,
        remaining_turns=5,
    )
    rel.non_aggression_pact = NonAggressionPact(allowed_hex_ids=["hex_1"])
    rel.right_of_passage = RightOfPassagePact(
        beneficiary_faction_id="humans",
        duration_turns=3,
        remaining_turns=3,
    )
    rel.vassal_pact = VassalPact(
        overlord_faction_id="humans",
        vassal_faction_id="elfs",
        tribute_gold_per_turn=20.0,
    )
    rel.intelligence_sharing = IntelligenceSharingPact(
        shared_target_faction_ids=["greenskins"]
    )
    rel.hostage_exchange = HostageExchangePact(faction_a_hostage_id="hero_1")
    rel.war_alliance = WarAlliancePact(
        common_enemy_faction_id="greenskins",
        loot_split_ratio_a=0.5,
        duration_turns=4,
        remaining_turns=4,
    )
    return rel


class TestDiplomaticMatrixInvariants:
    def test_declare_war_nullifies_all_active_pacts(self, active_relation):
        assert active_relation.stance == DiplomaticStance.PEACE
        assert active_relation.trade_agreement is not None
        assert active_relation.war_alliance is not None

        active_relation.declare_war()

        assert active_relation.stance == DiplomaticStance.WAR
        assert active_relation.trade_agreement is None
        assert active_relation.non_aggression_pact is None
        assert active_relation.right_of_passage is None
        assert active_relation.vassal_pact is None
        assert active_relation.intelligence_sharing is None
        assert active_relation.hostage_exchange is None
        assert active_relation.war_alliance is None

    def test_proposing_pacts_during_war_raises_error(self, active_relation):
        active_relation.declare_war()

        trade = TradeAgreement(
            give_resource=ResourceType.GOLD,
            give_amount=10.0,
            get_resource=ResourceType.FOOD,
            get_amount=10.0,
            duration_turns=1,
            remaining_turns=1,
        )
        with pytest.raises(PactForbiddenDuringWarError):
            active_relation.propose_trade(trade)

        with pytest.raises(PactForbiddenDuringWarError):
            active_relation.establish_right_of_passage(
                RightOfPassagePact(
                    beneficiary_faction_id="humans", duration_turns=1, remaining_turns=1
                )
            )

        with pytest.raises(PactForbiddenDuringWarError):
            active_relation.form_vassalage(
                VassalPact(
                    overlord_faction_id="humans",
                    vassal_faction_id="elfs",
                    tribute_gold_per_turn=5.0,
                )
            )

        with pytest.raises(WarAllianceWithEnemyForbiddenError):
            active_relation.form_war_alliance(
                WarAlliancePact(
                    common_enemy_faction_id="greenskins",
                    loot_split_ratio_a=0.5,
                    duration_turns=1,
                    remaining_turns=1,
                )
            )

    def test_make_peace_restores_ability_to_sign_pacts(self, active_relation):
        active_relation.declare_war()
        assert active_relation.stance == DiplomaticStance.WAR

        active_relation.make_peace()
        assert active_relation.stance == DiplomaticStance.PEACE

        trade = TradeAgreement(
            give_resource=ResourceType.GOLD,
            give_amount=10.0,
            get_resource=ResourceType.FOOD,
            get_amount=10.0,
            duration_turns=2,
            remaining_turns=2,
        )
        active_relation.propose_trade(trade)
        assert active_relation.trade_agreement == trade
