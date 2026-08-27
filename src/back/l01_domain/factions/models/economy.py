from typing import Optional

from pydantic import BaseModel, Field

from src.back.l01_domain.factions.constants import BASE_TAX_RATE


class FactionEconomyReport(BaseModel):
    """
    Экономический отчет фракции за прошедший такт.
    """

    faction_id: str = Field(...)
    income_gold: float = Field(default=0.0)
    tax_income_gold: float = Field(
        default=0.0, description="Часть дохода золотом, собранная налогами"
    )
    income_material: float = Field(default=0.0)
    income_food: float = Field(default=0.0)

    upkeep_gold_required: float = Field(default=0.0)
    upkeep_food_required: float = Field(default=0.0)

    gold_deficit: float = Field(default=0.0)
    food_deficit: float = Field(default=0.0)

    deserted_squad_names: list[str] = Field(default_factory=list)
    completed_building_names: list[str] = Field(default_factory=list)
    unavailable_worker_squad_ids: list[str] = Field(
        default_factory=list,
        description="Отряды тира 00, пропущенные из добычи - в бою или в Ничьей земле",
    )

    # ====================================================
    # Настроения подданных под текущей налоговой ставкой
    # ====================================================

    tax_rate: float = Field(
        default=BASE_TAX_RATE, description="Ставка, по которой собран налог этого такта"
    )
    tax_morale_delta: float = Field(
        default=0.0, description="Изменение морали гарнизонов от налоговой политики"
    )
    striking_worker_squad_ids: list[str] = Field(
        default_factory=list,
        description="Отряды рабочих, бросившие добычу из-за повышенных сборов",
    )
    riot_army_id: Optional[str] = Field(
        default=None, description="ID нейтральной армии, поднявшей бунт против налогов"
    )
