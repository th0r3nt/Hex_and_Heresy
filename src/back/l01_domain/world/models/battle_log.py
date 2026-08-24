"""
Числовое досье боя - сухая математика сражения, которую летописец превращает
в художественный текст.

Отчеты тактических раундов (combat/models/reports.py) живут ровно один раунд
и говорят на языке идентификаторов. Досье копится от первого раунда до
последнего и говорит на языке имен, потерь и переломных моментов: именно его
летописец рендерит в контекст для языковой модели.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.back.l01_domain.combat.constants import TimeOfDay, WeatherCondition
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.world.constants import CHRONICLE_MASSACRE_LOSS_RATIO


class BattleSide(str, Enum):
    """Сторона боя, к которой приписан отряд."""

    ATTACKER = "attacker"
    DEFENDER = "defender"


class TurningPointKind(str, Enum):
    """
    Тип переломного момента сражения.

    Это не игровая механика, а подсказка летописцу: на чем строить рассказ,
    чтобы бой не свелся к перечислению потерь.
    """

    CHARGE_BROKE_LINE = "charge_broke_line"  # натиск смял строй защитников
    CHAIN_PANIC = "chain_panic"  # паника перекинулась на соседей
    MISFIRE = "misfire"  # осечка и залп по своим
    FLANK_SLAUGHTER = "flank_slaughter"  # удар во фланг или тыл
    SQUAD_WIPED_OUT = "squad_wiped_out"  # отряд выбит подчистую
    CORPSE_PILE = "corpse_pile"  # на клетке выросла гора трупов
    HERO_SLAIN = "hero_slain"  # погиб герой


class SquadBattleLog(BaseModel):
    """
    Итог одного отряда в конкретном бою.

    Снимок имени и численности берется на старте боя: к финалу отряд может
    быть выбит целиком, и восстановить, кем он был, будет уже не по чему.
    """

    squad_id: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1, description="Имя отряда на момент начала боя")
    archetype_name: str = Field(default="", description="Название базового юнита")
    is_named: bool = Field(default=False, description="Именной отряд (ветеран) или безымянное мясо")
    commander_name: Optional[str] = Field(default=None, description="Имя командира именного отряда")

    faction_id: Optional[str] = Field(default=None)
    race: FactionRace = Field(...)
    side: BattleSide = Field(...)

    initial_count: int = Field(..., ge=0, description="Численность на момент начала боя")
    deaths: int = Field(default=0, ge=0, description="Потери за весь бой")
    kills: int = Field(default=0, ge=0, description="Убито врагов за весь бой")

    panicked: bool = Field(default=False, description="Отряд хотя бы раз обращался в бегство")
    wiped_out: bool = Field(default=False, description="Отряд полег полностью")

    @property
    def survivors(self) -> int:
        """Сколько бойцов пережило бой."""
        return max(0, self.initial_count - self.deaths)

    @property
    def loss_ratio(self) -> float:
        """Доля потерь от исходной численности (0.0 - 1.0)."""
        if self.initial_count <= 0:
            return 0.0
        return min(1.0, self.deaths / self.initial_count)


class BattleTurningPoint(BaseModel):
    """
    Переломный момент боя, замеченный летописцем в отчете раунда.
    """

    model_config = ConfigDict(frozen=True)

    tick: int = Field(..., ge=0, description="Раунд боя, в котором это случилось")
    kind: TurningPointKind = Field(...)

    actor_name: Optional[str] = Field(default=None, description="Кто это сделал")
    target_name: Optional[str] = Field(default=None, description="С кем это случилось")
    value: float = Field(default=0.0, description="Числовая мера события: погибшие, сила удара")
    details: str = Field(default="", description="Уточнение для промпта, если числа мало")


class BattleDossier(BaseModel):
    """
    Досье сражения: обстановка, состав сторон, потери и переломные моменты.

    Агрегат копится по мере боя (см. BattleLogCollector) и остается в истории
    партии после того, как летопись написана: по нему можно перегенерировать
    текст, не переигрывая бой.
    """

    battle_id: str = Field(..., min_length=1)
    started_tick: int = Field(default=0, ge=0, description="Глобальный такт начала боя")
    finished_tick: Optional[int] = Field(default=None, ge=0, description="Раунд, оборвавший бой")
    last_absorbed_tick: int = Field(
        default=0,
        ge=0,
        description="Последний учтенный раунд: защита от повторного счета одного отчета",
    )

    location_name: str = Field(default="", description="Место сражения для заголовка свитка")
    weather: WeatherCondition = Field(default=WeatherCondition.CLEAR)
    time_of_day: TimeOfDay = Field(default=TimeOfDay.GREY_HOURS)
    is_siege: bool = Field(default=False, description="Штурм цитадели: в летопись идет всегда")

    attacker_faction_id: Optional[str] = Field(default=None)
    defender_faction_id: Optional[str] = Field(default=None)

    squads: dict[str, SquadBattleLog] = Field(
        default_factory=dict, description="Досье отрядов обеих сторон: squad_id -> итог"
    )
    turning_points: list[BattleTurningPoint] = Field(default_factory=list)
    heroes_slain: list[str] = Field(
        default_factory=list, description="Имена героев, павших в этом бою"
    )

    victor_faction_id: Optional[str] = Field(default=None)

    # ==================================================================
    # НАПОЛНЕНИЕ ДОСЬЕ
    # ==================================================================

    def register_squad(self, log: SquadBattleLog) -> None:
        """
        Заводит отряд в досье. Повторная регистрация игнорируется: исходная
        численность берется на старте боя и не переписывается по ходу.
        """
        self.squads.setdefault(log.squad_id, log)

    def get_squad(self, squad_id: str) -> Optional[SquadBattleLog]:
        return self.squads.get(squad_id)

    def add_deaths(self, squad_id: str, count: int) -> None:
        """
        Прибавляет потери отряду. Отряд, которого нет в досье (например,
        подкрепление, пришедшее в бой позже), молча игнорируется.
        """
        if count <= 0:
            return
        log = self.squads.get(squad_id)
        if log is None:
            return
        log.deaths += count
        if log.deaths >= log.initial_count:
            log.wiped_out = True

    def add_kills(self, squad_id: str, count: int) -> None:
        """Прибавляет отряду счет убитых врагов."""
        if count <= 0:
            return
        log = self.squads.get(squad_id)
        if log is None:
            return
        log.kills += count

    def mark_panic(self, squad_id: str) -> None:
        """Отмечает, что отряд обратился в бегство."""
        log = self.squads.get(squad_id)
        if log is not None:
            log.panicked = True

    def add_turning_point(self, turning_point: BattleTurningPoint) -> None:
        self.turning_points.append(turning_point)

    def add_slain_hero(self, hero_name: str) -> None:
        """Записывает павшего героя, не допуская дублей от повторных событий."""
        if hero_name and hero_name not in self.heroes_slain:
            self.heroes_slain.append(hero_name)

    # ==================================================================
    # ИТОГИ БОЯ
    # ==================================================================

    @property
    def is_finished(self) -> bool:
        return self.finished_tick is not None

    def side_squads(self, side: BattleSide) -> list[SquadBattleLog]:
        return [log for log in self.squads.values() if log.side == side]

    def side_initial_count(self, side: BattleSide) -> int:
        return sum(log.initial_count for log in self.side_squads(side))

    def side_deaths(self, side: BattleSide) -> int:
        return sum(log.deaths for log in self.side_squads(side))

    def side_loss_ratio(self, side: BattleSide) -> float:
        """Доля погибших от исходной численности стороны."""
        initial = self.side_initial_count(side)
        if initial <= 0:
            return 0.0
        return min(1.0, self.side_deaths(side) / initial)

    @property
    def total_deaths(self) -> int:
        return sum(log.deaths for log in self.squads.values())

    @property
    def min_squads_per_side(self) -> int:
        """
        Размер меньшей из сторон в карточках - мера масштаба сражения.
        """
        return min(
            len(self.side_squads(BattleSide.ATTACKER)),
            len(self.side_squads(BattleSide.DEFENDER)),
        )

    @property
    def named_squads_lost(self) -> list[SquadBattleLog]:
        """Именные отряды, полегшие в этом бою, - кандидаты в Зал павших."""
        return [log for log in self.squads.values() if log.is_named and log.wiped_out]

    @property
    def is_massacre(self) -> bool:
        """
        Резня: хотя бы одна сторона потеряла подавляющую часть своих бойцов.
        """
        return any(
            self.side_loss_ratio(side) >= CHRONICLE_MASSACRE_LOSS_RATIO
            for side in (BattleSide.ATTACKER, BattleSide.DEFENDER)
        )
