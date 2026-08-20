"""
Тесты расчета веса трупов по габаритам и логики распространения цепной паники.
"""

from src.back.l01_domain.army.constants import UnitSizeCategory
from src.back.l01_domain.combat.constants import (
    CHAIN_PANIC_MORALE_SHOCK,
    CORPSE_PILE_UNIT_THRESHOLD,
)
from src.back.l01_domain.combat.resolution import (
    calculate_effective_corpse_weight,
    propagate_chain_panic,
)


class TestCorpseWeightCalculations:
    def test_size_category_weights(self):
        # 100 мелких существ (гоблины, крысы) = 50 веса (недостаточно для кучи трупов 150)
        assert calculate_effective_corpse_weight(100, UnitSizeCategory.SMALL) == 50.0

        # 100 бойцов среднего размера (люди, эльфы) = 100 веса
        assert calculate_effective_corpse_weight(100, UnitSizeCategory.MEDIUM) == 100.0

        # 30 крупных кавалеристов (кони, волки) = 150 веса (ровно порог кучи трупов)
        large_weight = calculate_effective_corpse_weight(30, UnitSizeCategory.LARGE)
        assert large_weight == 150.0
        assert large_weight >= CORPSE_PILE_UNIT_THRESHOLD

        # 8 гигантских монстров (огры, тролли) = 160 веса (превышает порог 150)
        huge_weight = calculate_effective_corpse_weight(8, UnitSizeCategory.HUGE)
        assert huge_weight == 160.0
        assert huge_weight >= CORPSE_PILE_UNIT_THRESHOLD


class TestChainPanicPropagation:
    def test_empty_neighbors_returns_empty_shock_dict(self):
        result = propagate_chain_panic(
            panicking_squad_id="squad_origin", neighbor_squad_ids=[]
        )
        assert result == {}

    def test_origin_squad_excluded_from_panic_shock(self):
        neighbors = ["squad_origin", "squad_ally_1", "squad_ally_2"]
        result = propagate_chain_panic(
            panicking_squad_id="squad_origin", neighbor_squad_ids=neighbors
        )

        assert "squad_origin" not in result
        assert result["squad_ally_1"] == CHAIN_PANIC_MORALE_SHOCK
        assert result["squad_ally_2"] == CHAIN_PANIC_MORALE_SHOCK
        assert len(result) == 2
