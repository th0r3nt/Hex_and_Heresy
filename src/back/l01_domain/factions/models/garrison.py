"""
Garrison - несносимая оборона земли (цитадели, города или союзного гекса).

Гарнизон не занимает строительный слот и не может быть уничтожен как
здание: он прикреплен к самой земле и восстанавливается вместе с ней.
Состоит из двух разных по природе половин:

* городское ополчение - местные жители 1-2 тира, которых поднимает сама
  земля. Их численность задается уровнем цитадели/ратуши, они бесплатно
  добираются после штурма и распускаются при падении уровня здания;
* расквартированные войска - карточки регулярной армии, которые игрок
  осознанно оставил за стенами (не больше MAX_STATIONED_GARRISON_SQUADS).

Любой отряд за стенами ест меньше провизии: гарнизон кормится из
городских амбаров, а не с обоза.
"""

from typing import Callable, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.exceptions.factions import (
    GarrisonCapacityExceededError,
    GarrisonLockedInBattleError,
    MilitiaTierNotAllowedError,
    SquadNotInGarrisonError,
)
from src.back.l01_domain.factions.constants import (
    GARRISON_FOOD_UPKEEP_DISCOUNT_RATIO,
    MAX_STATIONED_GARRISON_SQUADS,
    MILITIA_ALLOWED_TIERS,
    MILITIA_REPLENISHMENT_RATE_PER_TICK,
    militia_capacity_for_level,
)
from src.back.l01_domain.maps.models.strategic import HexCoordinates


class Garrison(BaseModel):
    """
    Агрегат гарнизона одной земли.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    zone_id: str = Field(
        ..., min_length=1, description="Ключ гекса земли в формате 'q,r'"
    )
    faction_id: str = Field(..., min_length=1, description="Владелец земли")
    hex_coordinates: HexCoordinates = Field(...)

    militia_squads: list[Squad] = Field(
        default_factory=list,
        description="Городское ополчение: поднимается землей, восстанавливается само",
    )
    stationed_squads: list[Squad] = Field(
        default_factory=list,
        description="Регулярные войска, оставленные игроком за стенами",
    )

    is_locked_in_battle: bool = Field(
        default=False,
        description="За землю идет тактический бой: состав гарнизона заморожен",
    )

    is_locked_in_resolution: bool = Field(
        default=False,
        description=(
            "Землю разоряет победитель: пока идет операция над городом, "
            "ополчение не набирается и потери не восполняются"
        ),
    )

    # ==================================================================
    # РАСЧЕТНЫЕ СВОЙСТВА
    # ==================================================================

    @property
    def all_squads(self) -> list[Squad]:
        """
        Полный список защитников земли - именно он уходит в тактический бой.
        Ополчение идет первым: оно встречает штурм у стен.
        """
        return [*self.militia_squads, *self.stationed_squads]

    @property
    def total_units_count(self) -> int:
        """Сколько живых бойцов держит землю прямо сейчас."""
        return sum(squad.state.unit_count for squad in self.all_squads)

    @property
    def total_upkeep_gold(self) -> float:
        """
        Жалование гарнизона за такт. Скидки нет: за стенами платят столько же,
        сколько в поле - экономия касается только провизии.
        """
        return sum(squad.upkeep_gold for squad in self.all_squads)

    @property
    def total_upkeep_food(self) -> float:
        """
        Расход провизии за такт со скидкой за жизнь на городских запасах.
        """
        raw_food = sum(squad.upkeep_food for squad in self.all_squads)
        return raw_food * (1.0 - GARRISON_FOOD_UPKEEP_DISCOUNT_RATIO)

    @property
    def free_stationed_slots(self) -> int:
        """Сколько карточек регулярных войск земля еще примет."""
        return max(0, MAX_STATIONED_GARRISON_SQUADS - len(self.stationed_squads))

    # ==================================================================
    # РОТАЦИЯ РЕГУЛЯРНЫХ ВОЙСК
    # ==================================================================

    def station_squad(self, squad: Squad) -> None:
        """
        Расквартировывает отряд за стенами.

        Лимит в MAX_STATIONED_GARRISON_SQUADS карточек - жесткий: земля
        физически не прокормит и не разместит больше.
        """
        self._assert_not_locked()

        if len(self.stationed_squads) >= MAX_STATIONED_GARRISON_SQUADS:
            raise GarrisonCapacityExceededError(
                zone_id=self.zone_id, max_squads=MAX_STATIONED_GARRISON_SQUADS
            )

        self.stationed_squads.append(squad)

    def unstation_squad(self, squad_id: str) -> Squad:
        """
        Выводит расквартированный отряд обратно в мобильную армию.

        Ополчение вывести нельзя: горожане не покидают свою землю, поэтому
        поиск идет только по регулярным войскам.
        """
        self._assert_not_locked()

        for i, squad in enumerate(self.stationed_squads):
            if squad.id == squad_id:
                return self.stationed_squads.pop(i)

        raise SquadNotInGarrisonError(zone_id=self.zone_id, squad_id=squad_id)

    def get_squad(self, squad_id: str) -> Optional[Squad]:
        """Находит любого защитника земли - ополченца или расквартированного."""
        return next((s for s in self.all_squads if s.id == squad_id), None)

    def _assert_not_locked(self) -> None:
        """Роняет доменную ошибку, если за землю прямо сейчас идет бой."""
        if self.is_locked_in_battle:
            raise GarrisonLockedInBattleError(self.zone_id)

    # ==================================================================
    # ГОРОДСКОЕ ОПОЛЧЕНИЕ
    # ==================================================================

    def militia_capacity(self, level: int) -> int:
        """Сколько отрядов ополчения положено земле при таком уровне здания."""
        return militia_capacity_for_level(level)

    def sync_militia_capacity(
        self, level: int, recruit: Callable[[], Squad]
    ) -> tuple[list[Squad], list[Squad]]:
        """
        Приводит численность ополчения к уровню цитадели/ратуши.

        Апгрейд здания открывает слот - земля тут же поднимает новый отряд
        фабрикой recruit (ее дает сервис: доменная модель не знает, из какого
        каталога берутся расовые ополченцы). Падение уровня, наоборот,
        распускает лишних по домам.

        Возвращает пару (набранные, распущенные).
        """
        capacity = self.militia_capacity(level)

        raised: list[Squad] = []
        while len(self.militia_squads) < capacity:
            squad = recruit()
            self._assert_militia_tier(squad)
            self.militia_squads.append(squad)
            raised.append(squad)

        disbanded: list[Squad] = []
        while len(self.militia_squads) > capacity:
            disbanded.append(self.militia_squads.pop())

        return raised, disbanded

    def replenish_militia_losses(self) -> list[str]:
        """
        Восполняет потери ополчения за такт: земля доучивает горожан взамен
        павших. За такт отряд добирает MILITIA_REPLENISHMENT_RATE_PER_TICK
        от полного состава, но не больше недостачи.

        Отряд, выбитый штурмом под ноль, не удаляется, а отстраивается с нуля:
        гарнизон земли уничтожить нельзя, его можно только временно обескровить.

        Возвращает id отрядов, которые получили пополнение.
        """
        replenished_ids: list[str] = []

        for squad in self.militia_squads:
            full_count = squad.archetype.default_unit_count
            deficit = full_count - squad.state.unit_count
            if deficit <= 0:
                continue

            # Минимум один боец за такт: иначе крошечные отряды не лечатся вовсе
            per_tick = max(1, int(full_count * MILITIA_REPLENISHMENT_RATE_PER_TICK))
            was_wiped = squad.state.unit_count == 0

            squad.state.unit_count += min(deficit, per_tick)
            if was_wiped:
                squad.state.hp_first_unit = squad.archetype.base_stats.max_hp

            replenished_ids.append(squad.id)

        return replenished_ids

    @staticmethod
    def _assert_militia_tier(squad: Squad) -> None:
        """
        Не пускает в ополчение элитные отряды: горожане - это 1-2 тир.
        """
        if squad.archetype.tier not in MILITIA_ALLOWED_TIERS:
            raise MilitiaTierNotAllowedError(
                squad_name=squad.display_name,
                tier=squad.archetype.tier,
                allowed_tiers=MILITIA_ALLOWED_TIERS,
            )
