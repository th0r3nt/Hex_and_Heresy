"""
Расчет прямого обзора фракции на глобальной карте.

Каждый источник проверяется поодиночке и на границе своего радиуса: обзор
обязан кончаться ровно там, где сказано в константах, а не гексом дальше.
"""

import pytest

from src.back.l01_domain.army.models.characters.commanders import Commander
from src.back.l01_domain.army.models.characters.traits import Trait, TraitCategory
from src.back.l01_domain.common import MechanicalModifier, StatName
from src.back.l01_domain.factions.constants import DiplomaticStance
from src.back.l01_domain.factions.models.diplomacy.messengers import Ambassador
from src.back.l01_domain.factions.models.diplomacy.pacts import IntelligenceSharingPact
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.maps.constants import (
    VISION_RADIUS_ARMY,
    VISION_RADIUS_BASE,
    VISION_RADIUS_REGIONAL_HALL,
    VISION_RADIUS_WATCHTOWER,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.vision.calculator import VisionCalculator
from src.back.tests.l02_services.mechanics.vision.conftest import (
    PLAYER_CAPITAL,
    add_army,
    add_regional_hall,
    add_watchtower,
    build_lenses,
    build_squad,
    hex_at,
)


@pytest.fixture
def calculator() -> VisionCalculator:
    return VisionCalculator()


# ==================================================================
# ЗАСТРОЙКА КАК ИСТОЧНИК ОБЗОРА
# ==================================================================


class TestSettlementVision:
    def test_citadel_lights_up_two_hexes_around(
        self, calculator: VisionCalculator, world: WorldState
    ):
        visible = calculator.calculate_visible_hexes(world, "humans")

        assert PLAYER_CAPITAL in visible
        assert hex_at(VISION_RADIUS_BASE) in visible
        assert hex_at(VISION_RADIUS_BASE + 1) not in visible

    def test_razed_citadel_stops_watching(
        self, calculator: VisionCalculator, world: WorldState, player: Faction
    ):
        """С сожженной цитадели смотреть некому."""
        player.headquarters.destroy()

        visible = calculator.calculate_visible_hexes(world, "humans")

        assert PLAYER_CAPITAL not in visible

    def test_regional_hall_adds_its_own_ring(
        self, calculator: VisionCalculator, world: WorldState, player: Faction
    ):
        hall_hex = hex_at(6)
        add_regional_hall(player, hall_hex)

        visible = calculator.calculate_visible_hexes(world, "humans")

        assert hall_hex in visible
        assert hex_at(6 + VISION_RADIUS_REGIONAL_HALL) in visible
        assert hex_at(6 + VISION_RADIUS_REGIONAL_HALL + 1) not in visible

    def test_watchtower_reaches_further_than_a_hall(
        self, calculator: VisionCalculator, world: WorldState, player: Faction
    ):
        tower_hex = hex_at(6)
        add_watchtower(player, tower_hex)

        visible = calculator.calculate_visible_hexes(world, "humans")

        assert hex_at(6 + VISION_RADIUS_WATCHTOWER) in visible
        assert hex_at(6 + VISION_RADIUS_WATCHTOWER + 1) not in visible

    def test_unfinished_watchtower_sees_nothing(
        self, calculator: VisionCalculator, world: WorldState, player: Faction
    ):
        """На недостроенную вышку подниматься некому."""
        tower_hex = hex_at(6)
        add_watchtower(player, tower_hex, is_under_construction=True)

        visible = calculator.calculate_visible_hexes(world, "humans")

        assert tower_hex not in visible

    def test_unknown_faction_sees_nothing(self, calculator: VisionCalculator, world: WorldState):
        assert calculator.calculate_visible_hexes(world, "мертвые души") == set()


# ==================================================================
# МОБИЛЬНЫЕ ИСТОЧНИКИ
# ==================================================================


class TestMobileVision:
    def test_army_opens_its_near_circle(
        self, calculator: VisionCalculator, world: WorldState
    ):
        add_army(world, "humans", hex_at(6))

        visible = calculator.calculate_visible_hexes(world, "humans")

        assert hex_at(6) in visible
        assert hex_at(6 + VISION_RADIUS_ARMY) in visible
        assert hex_at(6 + VISION_RADIUS_ARMY + 1) not in visible

    def test_lenses_widen_the_army_view(
        self, calculator: VisionCalculator, world: WorldState
    ):
        """Оптика в отряде отодвигает границу обзора армии на гекс."""
        add_army(world, "humans", hex_at(6), squads=[build_squad(build_lenses(1))])

        visible = calculator.calculate_visible_hexes(world, "humans")

        assert hex_at(6 + VISION_RADIUS_ARMY + 1) in visible

    def test_scouting_commander_widens_the_army_view(
        self, calculator: VisionCalculator, world: WorldState
    ):
        """Перк разведки полководца работает так же, как оптика отряда."""
        scout = Commander(
            name="Следопыт",
            faction_id="humans",
            traits=[
                Trait(
                    id="trait_pathfinder",
                    name="Следопыт",
                    category=TraitCategory.BACKGROUND,
                    prompt_text="Ты вырос в дозорах и читаешь горизонт лучше карты.",
                    modifiers=[
                        MechanicalModifier(
                            stat_name=StatName.VISION_RANGE_HEXES, value=2.0
                        )
                    ],
                )
            ],
        )
        add_army(world, "humans", hex_at(6), commander=scout)

        visible = calculator.calculate_visible_hexes(world, "humans")

        assert hex_at(6 + VISION_RADIUS_ARMY + 2) in visible
        assert hex_at(6 + VISION_RADIUS_ARMY + 3) not in visible

    def test_ambassador_on_the_road_scouts_around_himself(
        self, calculator: VisionCalculator, world: WorldState
    ):
        world.ambassadors.append(
            Ambassador(faction_id="humans", name="Посланник", current_hex=hex_at(6))
        )

        visible = calculator.calculate_visible_hexes(world, "humans")

        assert hex_at(6) in visible

    def test_foreign_army_gives_no_vision(
        self, calculator: VisionCalculator, world: WorldState
    ):
        """Чужая колонна на Ничьей земле обзора игроку не дает."""
        add_army(world, "greenskins", hex_at(6))

        visible = calculator.calculate_visible_hexes(world, "humans")

        assert hex_at(6) not in visible


# ==================================================================
# ОБМЕН РАЗВЕДДАННЫМИ
# ==================================================================


class TestIntelligenceSharing:
    def test_pact_extends_vision_to_allied_sectors(
        self, calculator: VisionCalculator, world: WorldState
    ):
        """
        Союзник по пакту делится своими постами: сектор вокруг его цитадели
        становится виден игроку.
        """
        relation = world.get_or_create_relation("humans", "greenskins")
        relation.share_intelligence(IntelligenceSharingPact(vision_sharing_radius_hexes=2))

        visible = calculator.calculate_visible_hexes(world, "humans")

        assert hex_at(12) in visible
        assert hex_at(10) in visible

    def test_pact_radius_caps_what_is_shared(
        self, calculator: VisionCalculator, world: WorldState
    ):
        """
        Договор на радиус 1 отдает только ближний круг союзника, даже если
        сам он видит на два гекса.
        """
        relation = world.get_or_create_relation("humans", "greenskins")
        relation.share_intelligence(IntelligenceSharingPact(vision_sharing_radius_hexes=1))

        visible = calculator.calculate_visible_hexes(world, "humans")

        assert hex_at(11) in visible
        assert hex_at(10) not in visible

    def test_war_cancels_shared_vision(
        self, calculator: VisionCalculator, world: WorldState
    ):
        """Объявленная война обнуляет обмен разведданными."""
        relation = world.get_or_create_relation("humans", "greenskins")
        relation.share_intelligence(IntelligenceSharingPact(vision_sharing_radius_hexes=2))
        relation.stance = DiplomaticStance.WAR

        visible = calculator.calculate_visible_hexes(world, "humans")

        assert hex_at(12) not in visible

    def test_pact_between_others_gives_nothing(
        self, calculator: VisionCalculator, world: WorldState, player: Faction
    ):
        """Чужой договор игрока не касается."""
        third = world.get_or_create_relation("greenskins", "elfs")
        third.share_intelligence(IntelligenceSharingPact(vision_sharing_radius_hexes=3))

        visible = calculator.calculate_visible_hexes(world, "humans")

        assert hex_at(12) not in visible


# ==================================================================
# ИСТОЧНИКИ КАК СПИСОК
# ==================================================================


class TestVisionSources:
    def test_sources_name_their_kind(
        self, calculator: VisionCalculator, world: WorldState, player: Faction
    ):
        """
        По списку источников видно, чем именно вскрыт сектор: это нужно и
        отладке, и подсказкам интерфейса.
        """
        add_regional_hall(player, hex_at(2))
        add_watchtower(player, hex_at(6))
        add_army(world, "humans", hex_at(8))

        kinds = {source.kind for source in calculator.collect_sources(world, "humans")}

        assert kinds == {"headquarters", "regional_hall", "watchtower", "army"}
