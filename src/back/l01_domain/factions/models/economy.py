from pydantic import BaseModel, Field


class FactionEconomyReport(BaseModel):
    """
    Экономический отчет фракции за прошедший такт.
    """

    faction_id: str = Field(...)
    income_gold: float = Field(default=0.0)
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
