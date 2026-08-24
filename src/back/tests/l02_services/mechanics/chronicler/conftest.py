"""
Общие фикстуры тестов летописца: мир с двумя фракциями, армии на карте,
фейковые шина событий, языковая модель и хранилище летописи.
"""

from typing import Any, Optional

import pytest
from pydantic import BaseModel

from src.back.l01_domain.army.constants import UnitSizeCategory
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.combat.constants import BattlePhase
from src.back.l01_domain.combat.models.reports import (
    MoraleAndEnvironmentReport,
    TacticalTurnReport,
)
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord, LordArchetype, LordTrait
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.chronicle import (
    LLMChronicleResponse,
    LLMEpitaphResponse,
)
from src.back.l01_domain.world.models.state import WorldState


# ==================================================================
# ФЕЙКОВАЯ ИНФРАСТРУКТУРА
# ==================================================================


class FakeEventBus:
    """Шина событий, запоминающая опубликованное."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_name: str, *args: Any, **kwargs: Any) -> None:
        self.events.append((event_name, kwargs))

    def names(self) -> list[str]:
        return [name for name, _ in self.events]

    def payload_of(self, event_name: str) -> dict:
        for name, payload in self.events:
            if name == event_name:
                return payload
        return {}


class FakeLLMClient:
    """
    Детерминированная языковая модель.

    Считает вызовы и отдает заранее заданные ответы, чтобы тесты проверяли
    логику летописца, а не фантазию нейросети.
    """

    def __init__(
        self,
        chronicle: Optional[LLMChronicleResponse] = None,
        epitaph: Optional[LLMEpitaphResponse] = None,
        rumor: str = "Торговцы говорят, что барон опять поднял налоги.",
    ) -> None:
        self.chronicle = chronicle or LLMChronicleResponse(
            title="Резня в Долине ржавых мечей",
            quote="Они умерли за Империю.",
            body="Строй сошелся со строем, и поле стало красным.",
        )
        self.epitaph = epitaph or LLMEpitaphResponse(
            title="Грязные стрелки Маркуса",
            epitaph="Они держали фланг до последнего болта.",
        )
        self.rumor = rumor

        self.structured_calls: list[dict[str, Any]] = []
        self.text_calls: list[dict[str, Any]] = []

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
    ) -> str:
        self.text_calls.append(
            {"system_prompt": system_prompt, "user_prompt": user_prompt, "max_tokens": max_tokens}
        )
        return self.rumor

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        temperature: float = 0.6,
    ) -> BaseModel:
        self.structured_calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_model": response_model,
            }
        )
        if response_model is LLMEpitaphResponse:
            return self.epitaph
        return self.chronicle


class FakeChroniclerRepository:
    """Хранилище летописи в памяти вместо SQL."""

    def __init__(self) -> None:
        self.history: list[dict[str, Any]] = []
        self.fallen: list[dict[str, Any]] = []

    async def record_battle_history(
        self,
        battle_id: str,
        title: str,
        quote: str,
        body: str,
        tick: int,
        location_name: str,
    ) -> None:
        self.history.append(
            {
                "battle_id": battle_id,
                "title": title,
                "quote": quote,
                "body": body,
                "tick": tick,
                "location_name": location_name,
            }
        )

    async def record_fallen_squad(
        self,
        squad_name: str,
        commander_name: str,
        race_id: str,
        biography: str,
        death_tick: int,
        killer_name: str,
    ) -> None:
        self.fallen.append(
            {
                "squad_name": squad_name,
                "commander_name": commander_name,
                "race_id": race_id,
                "biography": biography,
                "death_tick": death_tick,
                "killer_name": killer_name,
            }
        )

    async def get_history_entries(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.history[:limit]

    async def get_fallen_records(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.fallen[:limit]


@pytest.fixture
def fake_bus() -> FakeEventBus:
    return FakeEventBus()


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture
def fake_repository() -> FakeChroniclerRepository:
    return FakeChroniclerRepository()


# ==================================================================
# ИГРОВОЙ МИР
# ==================================================================


def _make_faction(faction_id: str, race: FactionRace, name: str, hex_q: int) -> Faction:
    lord = Lord(
        faction_id=faction_id,
        name=f"Лорд {name}",
        title="Правитель",
        archetype=LordArchetype(id=f"arch_{faction_id}", name="Прагматик", description="..."),
        trait=LordTrait(id=f"trait_{faction_id}", name="Расчетливый", text_fragment="..."),
    )
    return Faction(
        id=faction_id,
        race=race,
        name=name,
        lord=lord,
        headquarters=Headquarters(faction_id=faction_id, name="Цитадель"),
        capital_hex=HexCoordinates.from_axial(hex_q, 0),
        is_player_controlled=faction_id == "humans",
    )


def build_squad(
    squad_id: str,
    faction_id: str,
    race: FactionRace = FactionRace.HUMANS,
    unit_count: int = 100,
    name: str = "Мечники",
    is_named: bool = False,
) -> Squad:
    """Собирает отряд с предсказуемой численностью для проверок арифметики."""
    archetype = UnitArchetype(
        id=f"unit_{faction_id}_{squad_id}",
        race=race,
        faction_id=faction_id,
        name=name,
        tier=1,
        default_unit_count=unit_count,
        base_stats=BaseUnitStats(
            max_hp=20.0,
            base_armor=0.0,
            base_speed=2.0,
            base_morale=50.0,
            base_stamina=100.0,
            base_initiative=10,
            size_category=UnitSizeCategory.MEDIUM,
        ),
    )
    squad = Squad.create_new(archetype=archetype, custom_unit_count=unit_count)
    squad.id = squad_id

    if is_named:
        squad.veterancy.promote(
            commander_name="Маркус",
            squad_nickname="Грязные стрелки Маркуса",
            trait_name="Злопамятные",
            lore="Выжили под Черными топями.",
        )

    return squad


@pytest.fixture
def humans() -> Faction:
    return _make_faction("humans", FactionRace.HUMANS, "Священная Империя", 0)


@pytest.fixture
def greenskins() -> Faction:
    return _make_faction("greenskins", FactionRace.GREENSKINS, "Орда Ржавых Клыков", 8)


@pytest.fixture
def battle_hex() -> HexCoordinates:
    """Ничья земля между цитаделями."""
    return HexCoordinates.from_axial(4, 0)


@pytest.fixture
def battle_squads(battle_hex) -> dict[str, Squad]:
    """
    Шесть карточек с каждой стороны - масштаб, который летописец считает
    достойным пера (CHRONICLE_MIN_SQUADS_PER_SIDE).
    """
    squads: dict[str, Squad] = {}
    for i in range(6):
        squad = build_squad(f"atk_{i}", "humans", FactionRace.HUMANS)
        squads[squad.id] = squad
    for i in range(6):
        squad = build_squad(f"def_{i}", "greenskins", FactionRace.GREENSKINS, name="Гоблины")
        squads[squad.id] = squad
    return squads


@pytest.fixture
def world(humans, greenskins, battle_squads, battle_hex) -> WorldState:
    """
    Мир с двумя армиями, сошедшимися на ничьей земле.
    """
    state = WorldState()
    state.add_faction(humans)
    state.add_faction(greenskins)

    attacker_army = StrategicArmy(
        id="army_humans",
        faction_id="humans",
        name="Первый легион",
        current_hex=battle_hex,
        squads=[squad for sid, squad in battle_squads.items() if sid.startswith("atk_")],
    )
    defender_army = StrategicArmy(
        id="army_greenskins",
        faction_id="greenskins",
        name="Орава",
        current_hex=battle_hex,
        squads=[squad for sid, squad in battle_squads.items() if sid.startswith("def_")],
    )
    state.add_army(attacker_army)
    state.add_army(defender_army)
    return state


@pytest.fixture
def battle_state(battle_squads) -> TacticalBattleState:
    return TacticalBattleState(
        id="battle_1",
        attacker_squad_ids=[sid for sid in battle_squads if sid.startswith("atk_")],
        defender_squad_ids=[sid for sid in battle_squads if sid.startswith("def_")],
    )


def build_report(
    tick: int = 1,
    battle_id: str = "battle_1",
    charge_reports=None,
    ranged_reports=None,
    melee_reports=None,
    morale_report: Optional[MoraleAndEnvironmentReport] = None,
    is_battle_finished: bool = False,
    victor_faction_id: Optional[str] = None,
) -> TacticalTurnReport:
    """Собирает отчет раунда, не заставляя тест перечислять пустые поля."""
    return TacticalTurnReport(
        battle_id=battle_id,
        tick=tick,
        phase=BattlePhase.AFTERMATH,
        charge_reports=charge_reports or [],
        ranged_reports=ranged_reports or [],
        melee_reports=melee_reports or [],
        morale_report=morale_report or MoraleAndEnvironmentReport(),
        is_battle_finished=is_battle_finished,
        victor_faction_id=victor_faction_id,
    )


@pytest.fixture
def make_squad():
    """
    Фабрика отрядов как фикстура: тестовые модули лежат вне пакета и не могут
    импортировать хелперы conftest напрямую.
    """
    return build_squad


@pytest.fixture
def make_report():
    """Фабрика отчетов раунда (см. make_squad о том, почему это фикстура)."""
    return build_report
