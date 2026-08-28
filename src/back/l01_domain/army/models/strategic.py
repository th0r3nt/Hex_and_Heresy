"""
Модель армии на глобальной стратегической карте.
"""

from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field

from src.back.l01_domain.army.constants import (
    STRATEGIC_PACE_SPEED_HEXES,
    StrategicMovementPace,
)
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.characters.commanders import Commander
from src.back.l01_domain.army.models.characters.heroes import Hero
from src.back.l01_domain.maps.models.strategic import HexCoordinates


class StrategicArmy(BaseModel):
    """
    Агрегат армии на глобальной карте.
    Объединяет отряды, героев, полководца и управляет передвижением по гексам.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    faction_id: str = Field(..., min_length=1)
    name: str = Field(default="Армия", min_length=1)

    commander: Optional[Commander] = Field(default=None)
    squads: list[Squad] = Field(default_factory=list)
    heroes: list[Hero] = Field(default_factory=list)

    current_hex: HexCoordinates = Field(...)
    target_hex: Optional[HexCoordinates] = Field(default=None)
    planned_path: list[HexCoordinates] = Field(default_factory=list)

    pace: StrategicMovementPace = Field(default=StrategicMovementPace.MARCH)
    is_in_ambush: bool = Field(default=False)
    is_in_tactical_battle: bool = Field(
        default=False,
        description=(
            "Армия связана тактическим боем на текущий такт: не может работать, "
            "маршировать или собирать ресурсы (см. turns/strategic/economy.py)"
        ),
    )

    active_operation_id: Optional[str] = Field(
        default=None,
        description=(
            "Армия занята операцией над побежденным пограничным городом "
            "(сожжение, разграбление, захват) и стоит на его гексе, пока та "
            "не завершится - см. factions/models/border_town.py"
        ),
    )

    @property
    def total_units_count(self) -> int:
        """
        Суммарное число живых бойцов и героев в армии.
        """
        return sum(squad.state.unit_count for squad in self.squads) + len(self.heroes)

    @property
    def is_busy_with_operation(self) -> bool:
        """
        Занята ли армия операцией над городом: такая армия не марширует и
        не получает новых приказов, пока не догорит последний такт.
        """
        return self.active_operation_id is not None

    @property
    def is_wiped_out(self) -> bool:
        """
        Проверяет, уничтожена ли армия полностью.
        """
        return self.total_units_count == 0

    @property
    def total_upkeep_gold(self) -> float:
        """
        Итоговое содержание армии в золоте за такт с учетом множителя полководца.
        """
        base_gold = sum(squad.upkeep_gold for squad in self.squads)
        if self.commander is not None:
            base_gold *= self.commander.upkeep_gold_multiplier
        return base_gold

    @property
    def total_upkeep_food(self) -> float:
        """
        Итоговое содержание армии в провизии за такт.
        """
        return sum(squad.upkeep_food for squad in self.squads)

    @property
    def max_movement_range(self) -> int:
        """
        Максимальная дальность марша в гексах за текущий такт с учетом бонуса полководца.
        """
        base_speed = STRATEGIC_PACE_SPEED_HEXES[self.pace]
        if self.commander is not None:
            base_speed += self.commander.strategic_movement_bonus
        return max(1, base_speed)

    def add_squad(self, squad: Squad) -> None:
        """
        Добавляет боевой отряд в армию.
        """
        self.squads.append(squad)

    def remove_squad(self, squad_id: str) -> Optional[Squad]:
        """
        Удаляет и возвращает отряд по его идентификатору.
        """
        for i, squad in enumerate(self.squads):
            if squad.id == squad_id:
                return self.squads.pop(i)
        return None

    def add_hero(self, hero: Hero) -> None:
        """
        Добавляет героя в армию.
        """
        self.heroes.append(hero)

    def remove_hero(self, hero_id: str) -> Optional[Hero]:
        """
        Удаляет и возвращает героя по его идентификатору.
        """
        for i, hero in enumerate(self.heroes):
            if hero.id == hero_id:
                return self.heroes.pop(i)
        return None

    def cleanup_wiped_squads(self) -> list[Squad]:
        """
        Удаляет полностью уничтоженные отряды и возвращает их список.
        """
        alive_squads = []
        wiped_squads = []
        for squad in self.squads:
            if squad.state.unit_count > 0:
                alive_squads.append(squad)
            else:
                wiped_squads.append(squad)
        self.squads = alive_squads
        return wiped_squads

    def lock_in_tactical_battle(self) -> None:
        """
        Помечает армию как связанную боем - вызывается при входе в тактический бой.
        """
        self.is_in_tactical_battle = True

    def release_from_tactical_battle(self) -> None:
        """
        Снимает пометку боя - вызывается при завершении тактического боя.
        """
        self.is_in_tactical_battle = False

    def lock_in_operation(self, operation_id: str) -> None:
        """
        Привязывает армию к операции над городом: она встает лагерем на его
        гексе и до конца работ ничем другим не занимается.
        """
        self.active_operation_id = operation_id

    def release_from_operation(self) -> None:
        """
        Отпускает армию, когда операция над городом завершена.
        """
        self.active_operation_id = None
