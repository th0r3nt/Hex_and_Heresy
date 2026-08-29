"""
Переводчик доменных ошибок на язык HTTP.

Контроллеры не ловят исключения руками: любая DomainError, вылетевшая из
фасада, доезжает сюда и превращается в честный статус с текстом ошибки.
Неизвестная доменная ошибка - это 500: значит, ей забыли назначить статус.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.back.l01_domain.exceptions.advisor import (
    AdvisorDisabledError,
    AdvisorGenerationFailedError,
    AdvisorOptionNotFoundError,
    AdvisorProposalNotFoundError,
)
from src.back.l01_domain.exceptions.base import DomainError
from src.back.l01_domain.exceptions.chronicler import (
    BattleDossierNotFoundError,
    ChronicleGenerationFailedError,
)
from src.back.l01_domain.exceptions.combat import (
    CellOccupiedError,
    CellOutOfBoundsError,
    InvalidBattlePhaseError,
    OrderNotAllowedError,
)
from src.back.l01_domain.exceptions.diplomacy import (
    AmbassadorUnavailableError,
    DiplomaticRelationNotFoundError,
    FactionCapitalUnknownError,
    PactForbiddenDuringWarError,
    SelfDiplomacyForbiddenError,
    WarAllianceWithEnemyForbiddenError,
)
from src.back.l01_domain.exceptions.factions import (
    BorderTownMaxLandsReachedError,
    BorderTownMaxLevelReachedError,
    BorderTownNotFoundError,
    BorderTownOperationInProgressError,
    BorderTownResolutionInvalidError,
    BuildingMaxLevelReachedError,
    BuildingSlotsExhaustedError,
    FactionNotFoundError,
    GarrisonCapacityExceededError,
    GarrisonLockedInBattleError,
    GarrisonNotFoundError,
    GarrisonRotationForbiddenError,
    HexNotAdjacentToTownError,
    InsufficientResourcesError,
    InvalidSettlementPlacementError,
    InvalidTaxRateError,
    MilitiaTierNotAllowedError,
    NegativeResourceAmountError,
    SquadNotInGarrisonError,
    ZoneNotControlledError,
)
from src.back.l01_domain.exceptions.llm import (
    LLMAuthorizationError,
    LLMKeyMissingError,
    LLMProviderNotConfiguredError,
    LLMRateLimitError,
    LLMRequestFailedError,
    LLMResponseFormatError,
)
from src.back.l01_domain.exceptions.maps import (
    HexOutOfBoundsError,
    InvalidCubeCoordinatesError,
    InvalidRadiusError,
    InvalidZoneIdError,
)
from src.back.l01_domain.exceptions.saves import (
    EmptySaveNameError,
    SaveDataCorruptedError,
    SaveDuringBattleForbiddenError,
    SaveNotFoundError,
)
from src.back.l01_domain.exceptions.workers import (
    BuildingWorkerCapacityExceededError,
    ExpeditionRecallForbiddenError,
    InvalidAssignmentTargetError,
    WorkerNotAvailableError,
)
from src.back.l01_domain.exceptions.world import (
    BattlefieldDepletedError,
    NoArmiesLockedForBattleError,
)
from src.back.l02_services.gameflow.guards import (
    ActionForbiddenInCurrentStateError,
    GuardConditionFailedError,
    InvalidStateTransitionError,
    WorldStateNotBoundError,
)
from src.back.l04_api.http.schemas.common import ErrorResponse
from src.back.utils.logger import main_logger

# ====================================================
# Таблица соответствия доменных ошибок статусам HTTP
# ====================================================

# Порядок важен: подклассы стоят выше своих родителей, иначе родитель
# перехватит их первым (LLMAuthorizationError наследует LLMRequestFailedError).
ERROR_STATUS_MAP: tuple[tuple[type[DomainError], int], ...] = (
    # 404 - запрошенного объекта не существует
    (SaveNotFoundError, status.HTTP_404_NOT_FOUND),
    (BattleDossierNotFoundError, status.HTTP_404_NOT_FOUND),
    (DiplomaticRelationNotFoundError, status.HTTP_404_NOT_FOUND),
    (FactionNotFoundError, status.HTTP_404_NOT_FOUND),
    (AdvisorProposalNotFoundError, status.HTTP_404_NOT_FOUND),
    (GarrisonNotFoundError, status.HTTP_404_NOT_FOUND),
    (BorderTownNotFoundError, status.HTTP_404_NOT_FOUND),
    # 401 / 502 - провайдер языковой модели
    (LLMAuthorizationError, status.HTTP_401_UNAUTHORIZED),
    (LLMKeyMissingError, status.HTTP_401_UNAUTHORIZED),
    (LLMProviderNotConfiguredError, status.HTTP_400_BAD_REQUEST),
    (LLMRateLimitError, status.HTTP_429_TOO_MANY_REQUESTS),
    (LLMResponseFormatError, status.HTTP_502_BAD_GATEWAY),
    (LLMRequestFailedError, status.HTTP_502_BAD_GATEWAY),
    (ChronicleGenerationFailedError, status.HTTP_502_BAD_GATEWAY),
    (AdvisorGenerationFailedError, status.HTTP_502_BAD_GATEWAY),
    # 409 - действие противоречит текущему состоянию игры
    (SaveDuringBattleForbiddenError, status.HTTP_409_CONFLICT),
    (ActionForbiddenInCurrentStateError, status.HTTP_409_CONFLICT),
    (InvalidStateTransitionError, status.HTTP_409_CONFLICT),
    (GuardConditionFailedError, status.HTTP_409_CONFLICT),
    (WorldStateNotBoundError, status.HTTP_409_CONFLICT),
    (PactForbiddenDuringWarError, status.HTTP_409_CONFLICT),
    (WarAllianceWithEnemyForbiddenError, status.HTTP_409_CONFLICT),
    (AmbassadorUnavailableError, status.HTTP_409_CONFLICT),
    (NoArmiesLockedForBattleError, status.HTTP_409_CONFLICT),
    (BattlefieldDepletedError, status.HTTP_409_CONFLICT),
    (InvalidBattlePhaseError, status.HTTP_409_CONFLICT),
    (CellOccupiedError, status.HTTP_409_CONFLICT),
    (OrderNotAllowedError, status.HTTP_409_CONFLICT),
    (WorkerNotAvailableError, status.HTTP_409_CONFLICT),
    (ExpeditionRecallForbiddenError, status.HTTP_409_CONFLICT),
    (BuildingMaxLevelReachedError, status.HTTP_409_CONFLICT),
    (BuildingSlotsExhaustedError, status.HTTP_409_CONFLICT),
    (BuildingWorkerCapacityExceededError, status.HTTP_409_CONFLICT),
    (ZoneNotControlledError, status.HTTP_409_CONFLICT),
    (GarrisonLockedInBattleError, status.HTTP_409_CONFLICT),
    (GarrisonCapacityExceededError, status.HTTP_409_CONFLICT),
    (GarrisonRotationForbiddenError, status.HTTP_409_CONFLICT),
    (BorderTownMaxLevelReachedError, status.HTTP_409_CONFLICT),
    (BorderTownMaxLandsReachedError, status.HTTP_409_CONFLICT),
    (BorderTownResolutionInvalidError, status.HTTP_409_CONFLICT),
    (BorderTownOperationInProgressError, status.HTTP_409_CONFLICT),
    (InvalidSettlementPlacementError, status.HTTP_409_CONFLICT),
    (SaveDataCorruptedError, status.HTTP_409_CONFLICT),
    (AdvisorDisabledError, status.HTTP_409_CONFLICT),
    # 400 - игрок просит невозможного
    (InsufficientResourcesError, status.HTTP_400_BAD_REQUEST),
    (NegativeResourceAmountError, status.HTTP_400_BAD_REQUEST),
    (InvalidTaxRateError, status.HTTP_400_BAD_REQUEST),
    (SquadNotInGarrisonError, status.HTTP_400_BAD_REQUEST),
    (MilitiaTierNotAllowedError, status.HTTP_400_BAD_REQUEST),
    (HexNotAdjacentToTownError, status.HTTP_400_BAD_REQUEST),
    (SelfDiplomacyForbiddenError, status.HTTP_400_BAD_REQUEST),
    (FactionCapitalUnknownError, status.HTTP_400_BAD_REQUEST),
    (InvalidAssignmentTargetError, status.HTTP_400_BAD_REQUEST),
    (EmptySaveNameError, status.HTTP_400_BAD_REQUEST),
    (AdvisorOptionNotFoundError, status.HTTP_400_BAD_REQUEST),
    (CellOutOfBoundsError, status.HTTP_400_BAD_REQUEST),
    (HexOutOfBoundsError, status.HTTP_400_BAD_REQUEST),
    (InvalidCubeCoordinatesError, status.HTTP_400_BAD_REQUEST),
    (InvalidRadiusError, status.HTTP_400_BAD_REQUEST),
    (InvalidZoneIdError, status.HTTP_400_BAD_REQUEST),
)


def resolve_status_code(error: DomainError) -> int:
    """
    Подбирает статус ответа по типу доменной ошибки.
    """
    for error_type, status_code in ERROR_STATUS_MAP:
        if isinstance(error, error_type):
            return status_code
    return status.HTTP_500_INTERNAL_SERVER_ERROR


# ====================================================
# Регистрация обработчиков в приложении
# ====================================================


async def domain_error_handler(_: Request, error: Exception) -> JSONResponse:
    """
    Единый обработчик доменных ошибок.
    """
    status_code = resolve_status_code(error)

    if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        main_logger.error(f"[API] Необработанная доменная ошибка: {error}")

    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=type(error).__name__,
            detail=getattr(error, "message", str(error)),
        ).model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Подключает перевод доменных ошибок к приложению. Вызывается корнем
    компоновки один раз при сборке FastAPI.
    """
    app.add_exception_handler(DomainError, domain_error_handler)
