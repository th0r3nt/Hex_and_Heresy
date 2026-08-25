"""
Модель назначения отряда рабочих (стационарная работа или экспедиция в нейтральные земли).
"""

from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field

from src.back.l01_domain.exceptions.workers import ExpeditionRecallForbiddenError
from src.back.l01_domain.factions.constants import (
    STATIONARY_WARMUP_TICKS,
    ResourceType,
    WorkerAssignmentStatus,
    WorkerAssignmentType,
)
from src.back.l01_domain.maps.models.strategic import HexCoordinates


class WorkerAssignment(BaseModel):
    """
    Агрегат назначения отряда рабочих.
    Управляет жизненным циклом стационарной добычи или экспедиции.
    """

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    squad_id: str = Field(
        ..., min_length=1, description="Идентификатор отряда рабочих (тир 00)"
    )
    faction_id: str = Field(..., min_length=1, description="Идентификатор фракции-владельца")
    assignment_type: WorkerAssignmentType = Field(...)
    status: WorkerAssignmentStatus = Field(...)

    # Параметры стационарной работы
    target_building_id: Optional[str] = Field(
        default=None, description="ID здания при стационарной работе"
    )
    warmup_ticks_remaining: int = Field(
        default=0, ge=0, description="Оставшиеся такты смены зоны до начала добычи"
    )

    # Параметры экспедиции
    target_hex: Optional[HexCoordinates] = Field(
        default=None, description="Целевой нейтральный гекс для экспедиции"
    )
    home_hex: Optional[HexCoordinates] = Field(
        default=None, description="Гекс базы или города, куда караван вернется с грузом"
    )
    mining_duration_ticks: Optional[int] = Field(
        default=None, ge=1, description="Запланированная длительность добычи на гексе"
    )
    mining_ticks_remaining: Optional[int] = Field(
        default=None, ge=0, description="Оставшееся время добычи"
    )
    accumulated_cargo: dict[ResourceType, float] = Field(
        default_factory=lambda: {res: 0.0 for res in ResourceType},
        description="Накопленные экспедицией ресурсы, зачисляемые по возвращении",
    )
    expedition_army_id: Optional[str] = Field(
        default=None, description="ID физической армии-каравана на глобальной карте"
    )

    @classmethod
    def create_stationary(
        cls,
        squad_id: str,
        faction_id: str,
        building_id: str,
        needs_warmup: bool = False,
    ) -> "WorkerAssignment":
        """
        Фабричный метод создания стационарного назначения на здание.
        Если рабочий уже находится в нужной зоне - статус сразу working,
        иначе - warming_up с задержкой в один такт.
        """

        warmup = STATIONARY_WARMUP_TICKS if needs_warmup else 0
        status = (
            WorkerAssignmentStatus.WARMING_UP
            if needs_warmup
            else WorkerAssignmentStatus.WORKING
        )

        return cls(
            squad_id=squad_id,
            faction_id=faction_id,
            assignment_type=WorkerAssignmentType.STATIONARY,
            status=status,
            target_building_id=building_id,
            warmup_ticks_remaining=warmup,
        )

    @classmethod
    def create_expedition(
        cls,
        squad_id: str,
        faction_id: str,
        target_hex: HexCoordinates,
        home_hex: HexCoordinates,
        mining_duration_ticks: int,
        expedition_army_id: str,
    ) -> "WorkerAssignment":
        """
        Фабричный метод отправки каравана в экспедицию в нейтральные земли.
        """
        return cls(
            squad_id=squad_id,
            faction_id=faction_id,
            assignment_type=WorkerAssignmentType.EXPEDITION,
            status=WorkerAssignmentStatus.TRAVELING_OUT,
            target_hex=target_hex,
            home_hex=home_hex,
            mining_duration_ticks=mining_duration_ticks,
            mining_ticks_remaining=mining_duration_ticks,
            expedition_army_id=expedition_army_id,
        )

    @property
    def is_active(self) -> bool:
        """
        Проверяет, активно ли назначение (не завершено и не отменено).
        """
        return self.status not in (
            WorkerAssignmentStatus.COMPLETED,
            WorkerAssignmentStatus.ABORTED,
        )

    # ==================================================================
    # ПЕРЕХОДЫ СОСТОЯНИЙ
    # ==================================================================

    def advance_warmup(self) -> bool:
        """
        Продвигает таймер разогрева на один такт.
        Возвращает True, если разогрев завершился и рабочий начал добычу.
        """
        if self.status != WorkerAssignmentStatus.WARMING_UP:
            return False

        if self.warmup_ticks_remaining > 0:
            self.warmup_ticks_remaining -= 1

        if self.warmup_ticks_remaining == 0:
            self.status = WorkerAssignmentStatus.WORKING
            return True
        return False

    def start_mining(self) -> None:
        """
        Переводит прибывший на нейтральный гекс караван в режим активной добычи.
        """
        if self.status == WorkerAssignmentStatus.TRAVELING_OUT:
            self.status = WorkerAssignmentStatus.MINING

    def tick_mining(self, mined_resources: dict[ResourceType, float]) -> bool:
        """
        Выполняет один такт добычи на нейтральном гексе и накапливает груз.
        Возвращает True, если лимит времени добычи исчерпан и пора отправляться назад.
        """
        if self.status != WorkerAssignmentStatus.MINING:
            return False

        for res_type, amount in mined_resources.items():
            self.accumulated_cargo[res_type] = (
                self.accumulated_cargo.get(res_type, 0.0) + amount
            )

        if self.mining_ticks_remaining is not None and self.mining_ticks_remaining > 0:
            self.mining_ticks_remaining -= 1

        if self.mining_ticks_remaining == 0:
            self.status = WorkerAssignmentStatus.TRAVELING_BACK
            return True
        return False

    def arrive_home(self) -> dict[ResourceType, float]:
        """
        Фиксирует успешное возвращение каравана на базу.
        Переводит статус в completed и возвращает накопленный груз для зачисления в казну.
        """
        self.status = WorkerAssignmentStatus.COMPLETED
        cargo = dict(self.accumulated_cargo)
        self.accumulated_cargo = {res: 0.0 for res in ResourceType}
        return cargo

    def abort(self) -> None:
        """
        Прерывает назначение при гибели отряда или сносе здания.
        """
        self.status = WorkerAssignmentStatus.ABORTED

    def assert_can_unassign_manually(self) -> None:
        """
        Проверяет, разрешен ли ручной отзыв игроком.
        Стационарных рабочих можно отозвать всегда; экспедиции отзывать досрочно запрещено.
        """
        if self.assignment_type == WorkerAssignmentType.EXPEDITION:
            raise ExpeditionRecallForbiddenError(self.id, self.status.value)
