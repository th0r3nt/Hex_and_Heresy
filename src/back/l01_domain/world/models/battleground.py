"""
Модель поля брани на глобальной карте: сбор трофеев, остатки тел и резонит.
"""

from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict

from src.back.l01_domain.army.constants import UnitSizeCategory
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.constants import DEFAULT_BATTLEFIELD_DECAY_TICKS


class BattlefieldCorpsePile(BaseModel):
    """
    Группа погибших тел определенной расы и габарита на поле боя.
    """

    model_config = ConfigDict(frozen=True)

    race: FactionRace = Field(..., description="Раса погибших юнитов")
    size_category: UnitSizeCategory = Field(default=UnitSizeCategory.MEDIUM)
    count: int = Field(..., gt=0, description="Количество тел")

    @property
    def race_id(self) -> str:
        return self.race.value


class BattlefieldLootSite(BaseModel):
    """
    Поле брани на глобальной карте.
    Возникает после окончания тактического боя и содержит трофеи.
    """

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    hex_coordinates: HexCoordinates = Field(..., description="Гекс расположения поля боя")
    origin_battle_id: str = Field(..., description="ID тактического боя, породившего это поле")

    # Трофейная экипировка в формате: {equipment_id: количество}
    salvageable_equipment: dict[str, int] = Field(
        default_factory=dict, description="Уцелевшая экипировка, готовая к сбору"
    )

    # Ресурс резонита для откачки жрецами эльфов
    residual_resonite: float = Field(
        default=0.0, ge=0.0, description="Концентрация остаточного резонита в крови"
    )

    # Тела для воскрешения нежити Паствой метеорита
    corpses: list[BattlefieldCorpsePile] = Field(default_factory=list)

    ticks_remaining: int = Field(
        default=DEFAULT_BATTLEFIELD_DECAY_TICKS,
        ge=0,
        description="Количество тактов до полного разложения и исчезновения лута",
    )
    is_scavenged: bool = Field(
        default=False, description="Было ли поле полностью зачищено мародерами"
    )

    @property
    def is_depleted(self) -> bool:
        """
        Проверяет, истощено ли поле боя (нет лута или истекло время).
        """
        has_items = sum(self.salvageable_equipment.values()) > 0
        has_corpses = len(self.corpses) > 0
        has_resonite = self.residual_resonite > 0.0

        return (
            self.ticks_remaining == 0
            or self.is_scavenged
            or (not has_items and not has_corpses and not has_resonite)
        )

    def decay_tick(self) -> None:
        """
        Уменьшает таймер существования поля брани.
        """
        if self.ticks_remaining > 0:
            self.ticks_remaining -= 1

    def siphon_resonite(self) -> float:
        """
        Сбор всего доступного резонита (для эльфов).
        """
        extracted = self.residual_resonite
        self.residual_resonite = 0.0
        return extracted

    def claim_equipment(self, equipment_id: str, amount: int) -> int:
        """
        Забирает указанное количество единиц экипировки из трофеев.
        Возвращает фактически забранное количество.
        """
        if amount <= 0 or equipment_id not in self.salvageable_equipment:
            return 0

        available = self.salvageable_equipment[equipment_id]
        taken = min(available, amount)
        self.salvageable_equipment[equipment_id] -= taken

        if self.salvageable_equipment[equipment_id] == 0:
            del self.salvageable_equipment[equipment_id]

        return taken
