"""
Схемы переходов конечного автомата, старта новой партии и экрана окончания.
"""

from typing import Optional, Union

from pydantic import BaseModel, Field

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.world.constants import DifficultyLevel, VictoryType
from src.back.l01_domain.world.models.setup import (
    FactionSetupConfig,
    NewGameConfig,
    RulerSetupConfig,
    new_random_seed,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.l01_domain.world.models.victory import VictoryConditionConfig
from src.back.l02_services.gameflow.states import GameState


class GameStateResponse(BaseModel):
    """
    Текущий режим игры для интерфейса.
    """

    state: GameState = Field(..., description="Активное состояние конечного автомата")
    is_party_active: bool = Field(
        default=False, description="Привязан ли к игре мир активной партии"
    )


# ====================================================
# Старт новой партии
# ====================================================


class RulerSetupRequest(BaseModel):
    """
    Выбор правителя стороны в лобби.

    Либо легендарный правитель из каталога по идентификатору, либо готовый
    кастомный лорд, которого мастер игры уже сочинил по биографии игрока.
    Пустой запрос тоже допустим: тогда трон займет первый правитель расы.
    """

    legendary_lord_id: Optional[str] = Field(
        default=None, description="напр. lord_hum_benedict_strauss"
    )
    custom_lord: Optional[Lord] = Field(
        default=None, description="Готовый лорд из ответа POST /api/game-master/lords"
    )

    def to_config(self) -> RulerSetupConfig:
        return RulerSetupConfig(
            legendary_lord_id=self.legendary_lord_id,
            custom_lord=self.custom_lord,
        )


class FactionSetupRequest(BaseModel):
    """
    Настройки одной стороны партии.
    """

    race: FactionRace = Field(...)
    name: str = Field(..., min_length=1, description="Название державы в этой партии")
    ruler: RulerSetupRequest = Field(default_factory=RulerSetupRequest)

    def to_config(self, is_player_controlled: bool) -> FactionSetupConfig:
        """
        Кто из сторон играет за человека, решает не сама сторона, а состав
        партии, поэтому флаг проставляется снаружи.
        """
        return FactionSetupConfig(
            race=self.race,
            name=self.name,
            is_player_controlled=is_player_controlled,
            ruler=self.ruler.to_config(),
        )


class NewGameRequest(BaseModel):
    """
    Настройки создаваемой партии.

    Все поля имеют значения по умолчанию, поэтому пустой запрос запускает
    быструю партию: люди против зеленокожих на нормальной сложности со
    случайным сидом и баронствами в центре карты.
    """

    seed: Union[int, str] = Field(
        default_factory=new_random_seed,
        description="Зерно генератора: одинаковое зерно дает одинаковую карту",
    )
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.NORMAL)

    player_faction: FactionSetupRequest = Field(
        default_factory=lambda: FactionSetupRequest(
            race=FactionRace.HUMANS, name="Империя"
        )
    )
    rival_faction: FactionSetupRequest = Field(
        default_factory=lambda: FactionSetupRequest(
            race=FactionRace.GREENSKINS, name="Орда"
        )
    )

    include_baronies: bool = Field(
        default=True,
        description="Ставить ли на карту независимые баронства третьей силой",
    )
    baronies_name: str = Field(default="Независимые баронства", min_length=1)
    baronies_ruler: RulerSetupRequest = Field(default_factory=RulerSetupRequest)

    victory_config: VictoryConditionConfig = Field(
        default_factory=VictoryConditionConfig,
        description="Правила победы партии: пороги ресурсов, города и активные ветки",
    )

    def to_config(self) -> NewGameConfig:
        """
        Переводит запрос клиента в доменные настройки партии.
        """
        return NewGameConfig(
            seed=self.seed,
            difficulty=self.difficulty,
            player_faction=self.player_faction.to_config(is_player_controlled=True),
            rival_faction=self.rival_faction.to_config(is_player_controlled=False),
            include_baronies=self.include_baronies,
            baronies_name=self.baronies_name,
            baronies_ruler=self.baronies_ruler.to_config(),
            victory_config=self.victory_config,
        )


class NewGameResponse(BaseModel):
    """
    Стартовый срез созданной партии для отрисовки глобальной карты.

    Мир приезжает уже профильтрованным туманом войны: на нулевом такте игрок
    видит только окрестности своей цитадели, а не всю раскладку соперников.
    """

    state: GameState = Field(..., description="Активное состояние конечного автомата")
    is_party_active: bool = Field(default=True)

    session_id: str = Field(..., description="Идентификатор мира начатой партии")
    seed: str = Field(
        ...,
        description="Зерно этой партии - его же игрок вводит, чтобы повторить карту",
    )
    player_faction_id: str = Field(..., description="Держава, за которую играет человек")
    world: WorldState = Field(..., description="Срез мира глазами игрока")


# ====================================================
# Финал партии и служебные экраны
# ====================================================


class GameOverRequest(BaseModel):
    """
    Фиксация финала партии.
    """

    is_player_victorious: bool = Field(...)
    reason: str = Field(..., min_length=1, description="Причина окончания партии")
    total_ticks: int = Field(default=0, ge=0)
    victory_type: Optional[VictoryType] = Field(
        default=None,
        description=(
            "Ветка глобальной цели, если финал объявляется по ней. Сами условия "
            "проверяет такт: этот эндпоинт нужен ручному завершению партии"
        ),
    )


class GlobalEventScreenRequest(BaseModel):
    """
    Открытие модального окна кризиса по уже существующему событию мира.
    """

    event_id: str = Field(..., min_length=1)


class DiplomaticSessionRequest(BaseModel):
    """
    Открытие окна дипломатической аудиенции.
    """

    initiator_faction_id: str = Field(..., min_length=1)
    target_faction_id: str = Field(..., min_length=1)
    ambassador_id: Optional[str] = Field(default=None)
