"""
Маскирование мира под фракцию.

Проверяется то, ради чего туман и вводился: игрок не должен получать в
срезе карты ни чужих армий за горизонтом, ни чужих писем, ни земель,
которых его разведка не открывала. При этом свое он видит всегда.
"""

import pytest

from src.back.l01_domain.factions.models.border_town import BorderTown
from src.back.l01_domain.factions.models.diplomacy.messengers import (
    Ambassador,
    Dispatch,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.garrison import Garrison
from src.back.l01_domain.factions.models.workers import WorkerAssignment
from src.back.l01_domain.maps.models.strategic import hex_zone_id
from src.back.l01_domain.world.constants import (
    GlobalEventCategory,
    GlobalEventScope,
)
from src.back.l01_domain.world.models.events import GlobalEvent
from src.back.l01_domain.world.models.points_of_interest import (
    PointOfInterest,
    PointOfInterestBlueprint,
    PointOfInterestCategory,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.vision.calculator import VisionCalculator
from src.back.l02_services.mechanics.vision.filter import VisionFilter
from src.back.tests.l02_services.mechanics.vision.conftest import (
    PLAYER_CAPITAL,
    RIVAL_CAPITAL,
    add_army,
    add_regional_hall,
    hex_at,
)


@pytest.fixture
def vision_filter() -> VisionFilter:
    return VisionFilter()


def light_up(world_state: WorldState, faction_id: str = "humans") -> None:
    """
    Считает обзор фракции и кладет его в мир - то же, что делает такт.

    Без этого шага маска пуста, и фильтр честно прячет вообще все: тестам
    нужно именно рабочее поле зрения.
    """
    visible = VisionCalculator().calculate_visible_hexes(world_state, faction_id)
    world_state.get_or_create_vision_map(faction_id).reveal(visible)


# ==================================================================
# ЧУЖИЕ АРМИИ
# ==================================================================


class TestForeignArmies:
    def test_distant_enemy_army_is_cut_from_the_view(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        """Вражеская колонна в трех гексах от базы в срез игрока не попадает."""
        far_away = add_army(world, "greenskins", hex_at(3))
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert far_away.id not in view.armies

    def test_enemy_inside_the_watch_ring_is_revealed(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        """Тот же враг, подошедший на два гекса, разведкой вскрыт."""
        approaching = add_army(world, "greenskins", hex_at(2))
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert approaching.id in view.armies

    def test_own_armies_are_never_hidden(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        """Свою армию фракция видит и на другом конце карты."""
        expedition = add_army(world, "humans", hex_at(9))
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert expedition.id in view.armies

    def test_hidden_army_leaves_no_trace_in_battle_locks(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        """
        По списку залоченных боем армий невидимого врага тоже не вычислить:
        иначе туман обходился бы одним запросом.
        """
        hidden = add_army(world, "greenskins", hex_at(9))
        world.lock_armies_for_battle("battle-1", [hidden.id])
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert view.active_battle_armies["battle-1"] == []

    def test_view_is_an_independent_copy(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        """Срез уезжает клиенту, поэтому правки в нем не должны бить по миру."""
        add_army(world, "greenskins", hex_at(9))
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")
        view.factions.clear()

        assert len(world.factions) == 2


    def test_foreign_worker_assignments_are_always_cut(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        """
        Наряд рабочих соперника не отдается никогда, даже если сам караван
        стоит на виду: по наряду читаются и его маршрут, и срок добычи.
        """
        world.add_worker_assignment(
            WorkerAssignment.create_expedition(
                squad_id="orc-diggers",
                faction_id="greenskins",
                target_hex=hex_at(2),
                home_hex=hex_at(12),
                mining_duration_ticks=3,
                expedition_army_id="caravan",
            )
        )
        add_army(world, "greenskins", hex_at(2))
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert view.worker_assignments == {}


# ==================================================================
# ЧУЖАЯ ПЕРЕПИСКА
# ==================================================================


class TestForeignMessengers:
    def test_foreign_dispatch_out_of_sight_is_hidden(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        world.dispatches.append(
            Dispatch(
                sender_faction_id="greenskins",
                recipient_faction_id="elfs",
                message_text="Выступаем на рассвете",
                route=[hex_at(9)],
            )
        )
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert view.dispatches == []

    def test_own_correspondence_always_stays(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        world.dispatches.append(
            Dispatch(
                sender_faction_id="humans",
                recipient_faction_id="greenskins",
                message_text="Предлагаем мир",
                route=[hex_at(9)],
            )
        )
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert len(view.dispatches) == 1

    def test_foreign_ambassador_out_of_sight_is_hidden(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        world.ambassadors.append(
            Ambassador(
                faction_id="greenskins",
                name="Гнилозуб",
                target_faction_id="elfs",
                current_hex=hex_at(9),
            )
        )
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert view.ambassadors == []

    def test_ambassador_heading_to_us_is_visible(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        """О после, идущем к нам, известно и без разведки: его ждут."""
        world.ambassadors.append(
            Ambassador(
                faction_id="greenskins",
                name="Гнилозуб",
                target_faction_id="humans",
                current_hex=hex_at(9),
            )
        )
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert len(view.ambassadors) == 1


# ==================================================================
# НЕРАЗВЕДАННЫЕ ЗЕМЛИ
# ==================================================================


class TestUnexploredLands:
    def test_unknown_point_of_interest_is_hidden(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        world.add_point_of_interest(
            PointOfInterest(
                blueprint=PointOfInterestBlueprint(
                    id="poi_crater",
                    name="Кратер сияния",
                    category=PointOfInterestCategory.GEO_ANOMALY,
                ),
                hex_coordinates=hex_at(9),
            )
        )
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert view.points_of_interest == {}

    def test_once_explored_place_stays_on_the_map(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        """
        Разведка ушла, но воронка с резонитом с карты не пропадает: места
        видны с момента первого открытия, а не только в прямом обзоре.
        """
        world.add_point_of_interest(
            PointOfInterest(
                blueprint=PointOfInterestBlueprint(
                    id="poi_crater",
                    name="Кратер сияния",
                    category=PointOfInterestCategory.GEO_ANOMALY,
                ),
                hex_coordinates=hex_at(9),
            )
        )
        scouts = add_army(world, "humans", hex_at(9))
        light_up(world)

        # Разъезд возвращается домой, прямой обзор гекса теряется
        world.remove_army(scouts.id)
        world.get_or_create_vision_map("humans").clear_direct_vision()
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert len(view.points_of_interest) == 1

    def test_foreign_capital_is_masked_until_found(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert view.factions["greenskins"].capital_hex is None

    def test_found_foreign_capital_shows_up(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        add_army(world, "humans", RIVAL_CAPITAL)
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert view.factions["greenskins"].capital_hex == RIVAL_CAPITAL

    def test_foreign_border_town_is_hidden_until_found(
        self, vision_filter: VisionFilter, world: WorldState, rival: Faction
    ):
        rival.add_border_town(
            BorderTown(faction_id=rival.id, name="Клык", center_hex=hex_at(8))
        )
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert view.factions["greenskins"].border_towns == []

    def test_foreign_regional_hall_is_hidden_until_found(
        self, vision_filter: VisionFilter, world: WorldState, rival: Faction
    ):
        add_regional_hall(rival, hex_at(11))
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert view.factions["greenskins"].regional_halls == []

    def test_own_territory_is_never_trimmed(
        self, vision_filter: VisionFilter, world: WorldState, player: Faction
    ):
        """Собственную ратушу фракция видит всегда, где бы та ни стояла."""
        add_regional_hall(player, hex_at(9))
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert len(view.factions["humans"].regional_halls) == 1

    def test_foreign_garrison_out_of_sight_is_hidden(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        world.add_garrison(
            Garrison(
                faction_id="greenskins",
                zone_id=hex_zone_id(hex_at(9)),
                hex_coordinates=hex_at(9),
            )
        )
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert view.garrisons == {}


# ==================================================================
# СОБЫТИЯ В НЕВИДИМЫХ СЕКТОРАХ
# ==================================================================


class TestEvents:
    def _zone_event(self, world_state: WorldState, target) -> GlobalEvent:
        event = GlobalEvent(
            name="Прорыв мутантов",
            description="Из руин полезли твари",
            category=GlobalEventCategory.MILITARY,
            scope=GlobalEventScope.ZONE,
            target_hex_coords=[target],
        )
        world_state.add_event(event)
        return event

    def test_local_event_in_the_dark_is_hidden(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        self._zone_event(world, hex_at(9))
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert view.active_events == []

    def test_local_event_at_home_is_reported(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        self._zone_event(world, PLAYER_CAPITAL)
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert len(view.active_events) == 1

    def test_global_event_reaches_everyone(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        """Мор и неурожай туманом не закрываются: они бьют по всей карте."""
        world.add_event(
            GlobalEvent(
                name="Пепельная зима",
                description="Небо закрыло пеплом",
                category=GlobalEventCategory.MILITARY,
                scope=GlobalEventScope.GLOBAL,
            )
        )
        light_up(world)

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert len(view.active_events) == 1


# ==================================================================
# ЧУЖАЯ РАЗВЕДКА
# ==================================================================


class TestForeignVisionMaps:
    def test_view_keeps_only_own_mask(
        self, vision_filter: VisionFilter, world: WorldState
    ):
        """
        Чужая маска тумана - это вся чужая разведка разом, и в срез игрока
        она попадать не должна.
        """
        light_up(world, "humans")
        light_up(world, "greenskins")

        view = vision_filter.filter_world_for_faction(world, "humans")

        assert set(view.vision_maps) == {"humans"}
