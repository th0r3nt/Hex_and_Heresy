"""
Генератор мира новой партии.

Проверяется главное обещание генератора: по одним и тем же настройкам он
собирает один и тот же играбельный мир - без коллизий на карте, с полной
стартовой инфраструктурой, армиями без полководцев, поднятыми гарнизонами,
мирной дипломатией и посчитанным туманом войны.
"""

from typing import Callable

import pytest

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions.world import RulerTemplateNotFoundError
from src.back.l01_domain.factions.constants import DiplomaticStance, ResourceType
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.maps.constants import STRATEGIC_MAP_TOTAL_HEXES
from src.back.l01_domain.maps.models.strategic import (
    HexCoordinates,
    get_standard_base_coordinates,
    hex_from_zone_id,
    hex_zone_id,
)
from src.back.l01_domain.world.constants import (
    NO_MANS_LAND_LANDMARK_BELT_RADIUS,
    STARTING_ALLIED_LANDS_COUNT,
    STARTING_ARMY_INFANTRY_SQUADS,
    STARTING_ARMY_WORKER_SQUADS,
    STARTING_INFANTRY_UNIT_TIER,
    WORKER_UNIT_TIER,
    DifficultyLevel,
)
from src.back.l01_domain.world.models.setup import (
    FactionSetupConfig,
    NewGameConfig,
    RulerSetupConfig,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.l01_domain.world.models.victory import VictoryConditionConfig
from src.back.l02_services.world.generator import WorldGenerator

ConfigFactory = Callable[..., NewGameConfig]


# ==================================================================
# ВСПОМОГАТЕЛЬНОЕ
# ==================================================================


def _occupied_hexes(faction: Faction) -> list[HexCoordinates]:
    """Гекс цитадели и все обжитые лепестки стороны."""
    return [
        faction.capital_hex,
        *(hex_from_zone_id(zone_id) for zone_id in faction.controlled_zone_ids),
    ]


def _building_ids(faction: Faction) -> list[str]:
    return [built.building.id for built in faction.buildings]


def _producers_count(faction: Faction, resource: ResourceType) -> int:
    return sum(
        1
        for built in faction.buildings
        if built.building.resource_output_per_worker.get(resource, 0.0) > 0.0
    )


def _fingerprint(world: WorldState) -> dict:
    """
    Отпечаток раскладки мира: все, что задает сид.

    Идентификаторы сущностей в него не входят - они случайны по своей
    природе (uuid4) и от зерна не зависят.
    """
    return {
        "capitals": sorted(
            (f.race.value, f.capital_hex.to_axial()) for f in world.factions.values()
        ),
        "zones": sorted(
            (f.race.value, tuple(sorted(f.controlled_zone_ids)))
            for f in world.factions.values()
        ),
        "buildings": sorted(
            (f.race.value, tuple(sorted(_building_ids(f))))
            for f in world.factions.values()
        ),
        "armies": sorted(
            (army.current_hex.to_axial(), tuple(s.archetype.id for s in army.squads))
            for army in world.armies.values()
        ),
        "points_of_interest": sorted(
            (poi.blueprint.id, poi.hex_coordinates.to_axial())
            for poi in world.points_of_interest.values()
        ),
        "battlefields": sorted(
            (site.origin_battle_id, site.hex_coordinates.to_axial(), site.residual_resonite)
            for site in world.battlefield_sites.values()
        ),
    }


# ==================================================================
# ДЕТЕРМИНИЗМ
# ==================================================================


async def test_same_seed_builds_the_same_world(
    generator: WorldGenerator, make_config: ConfigFactory
):
    """Одно зерно - одна карта: иначе баг не воспроизвести."""
    first = await generator.generate(make_config())
    second = await generator.generate(make_config())

    assert _fingerprint(first) == _fingerprint(second)


async def test_different_seeds_build_different_worlds(
    generator: WorldGenerator, make_config: ConfigFactory
):
    """
    Разные зерна разводят ориентиры и точки интереса по разным гексам.
    Сами цитадели при этом стоят на месте: их координаты фиксированы картой.
    """
    first = await generator.generate(make_config(seed=1))
    second = await generator.generate(make_config(seed=2))

    assert _fingerprint(first)["points_of_interest"] != (
        _fingerprint(second)["points_of_interest"]
    )


async def test_string_seed_is_accepted(
    generator: WorldGenerator, make_config: ConfigFactory
):
    """Игрок вводит зерно словом - это такой же законный сид."""
    first = await generator.generate(make_config(seed="Олд-Штадт"))
    second = await generator.generate(make_config(seed="Олд-Штадт"))

    assert _fingerprint(first) == _fingerprint(second)


# ==================================================================
# РАЗМЕТКА КАРТЫ
# ==================================================================


async def test_bases_stand_on_standard_citadel_hexes(
    generator: WorldGenerator, make_config: ConfigFactory
):
    world = await generator.generate(make_config())
    north_base, south_base = get_standard_base_coordinates()

    player = world.get_player_faction()
    rival = next(
        f for f in world.factions.values() if f.race == FactionRace.GREENSKINS
    )

    assert player.capital_hex == north_base
    assert rival.capital_hex == south_base


async def test_no_two_sides_share_a_hex(
    generator: WorldGenerator, make_config: ConfigFactory
):
    """Цитадели, лепестки и замок барона не наезжают друг на друга."""
    world = await generator.generate(make_config())

    occupied = [coord for f in world.factions.values() for coord in _occupied_hexes(f)]

    assert len(occupied) == len(set(occupied))


async def test_landmarks_do_not_collide_with_settlements_or_each_other(
    generator: WorldGenerator, make_config: ConfigFactory
):
    world = await generator.generate(make_config())

    settled = {coord for f in world.factions.values() for coord in _occupied_hexes(f)}
    poi_hexes = [poi.hex_coordinates for poi in world.points_of_interest.values()]

    assert len(poi_hexes) == len(set(poi_hexes))
    assert set(poi_hexes).isdisjoint(settled)


async def test_barony_castle_stands_in_the_center_of_the_map(
    generator: WorldGenerator, make_config: ConfigFactory
):
    world = await generator.generate(make_config())

    barony = next(
        f for f in world.factions.values() if f.race == FactionRace.BARONIAL_TROOPS
    )

    assert barony.capital_hex.r == 0
    assert -2 <= barony.capital_hex.q <= 2


async def test_baronies_can_be_left_out_of_the_party(
    generator: WorldGenerator, make_config: ConfigFactory
):
    world = await generator.generate(make_config(include_baronies=False))

    assert len(world.factions) == 2
    assert all(f.race != FactionRace.BARONIAL_TROOPS for f in world.factions.values())


async def test_neutral_hexes_are_everything_outside_the_petals(
    generator: WorldGenerator, make_config: ConfigFactory
):
    """
    Ничья земля - это карта за вычетом гекса цитадели и всех шести ее
    лепестков у каждой стороны.
    """
    world = await generator.generate(make_config())

    hexes_per_side = 1 + 6
    expected = STRATEGIC_MAP_TOTAL_HEXES - len(world.factions) * hexes_per_side

    assert len(world.neutral_hexes) == expected


# ==================================================================
# СТАРТОВАЯ ИНФРАСТРУКТУРА
# ==================================================================


async def test_every_side_starts_with_full_infrastructure(
    generator: WorldGenerator, make_config: ConfigFactory
):
    """Цитадель, три ратуши, две фермы и одна каменоломня - у каждой стороны."""
    world = await generator.generate(make_config())

    for faction in world.factions.values():
        assert faction.headquarters.level == 1
        assert faction.headquarters.is_destroyed is False
        assert len(faction.regional_halls) == STARTING_ALLIED_LANDS_COUNT
        assert all(hall.level == 1 for hall in faction.regional_halls)
        assert len(faction.controlled_zone_ids) == STARTING_ALLIED_LANDS_COUNT
        assert _producers_count(faction, ResourceType.FOOD) == 2
        assert _producers_count(faction, ResourceType.MATERIAL) == 1


async def test_starting_buildings_are_already_working(
    generator: WorldGenerator, make_config: ConfigFactory
):
    """Партия начинается с работающей экономики, а не со стройплощадок."""
    world = await generator.generate(make_config())

    for faction in world.factions.values():
        for built in faction.buildings:
            assert built.is_under_construction is False
            assert built.construction_ticks_remaining == 0


async def test_each_petal_carries_exactly_one_building(
    generator: WorldGenerator, make_config: ConfigFactory
):
    """
    Ратуша первого уровня дает один строительный слот, поэтому застройка
    ложится по одному зданию на лепесток. Гекс цитадели остается пустым:
    добывающие здания разрешены только в союзных землях.
    """
    world = await generator.generate(make_config())

    for faction in world.factions.values():
        zone_ids = [built.zone_id for built in faction.buildings]

        assert sorted(zone_ids) == sorted(faction.controlled_zone_ids)
        assert hex_zone_id(faction.capital_hex) not in zone_ids


@pytest.mark.parametrize(
    "race, food_building_id, material_building_id",
    [
        (FactionRace.HUMANS, "bld_hum_wheat_fields", "bld_hum_quarry"),
        (FactionRace.GREENSKINS, "bld_grn_mushroom_caves", "bld_grn_scrapyard"),
        (FactionRace.ELFS, "bld_elf_crystal_gardens", "bld_elf_essence_extractors"),
        (
            FactionRace.CONGREGATION_OF_THE_METEORITE,
            "bld_cotm_slaughterhouse",
            "bld_cotm_bone_pit",
        ),
    ],
)
async def test_starting_buildings_are_racial(
    generator: WorldGenerator,
    make_config: ConfigFactory,
    race: FactionRace,
    food_building_id: str,
    material_building_id: str,
):
    """Каждая раса начинает со своей фермы и своей добычи материалов."""
    config = make_config(
        player_faction=FactionSetupConfig(
            race=race, name="Держава", is_player_controlled=True
        ),
        include_baronies=False,
    )
    world = await generator.generate(config)

    built = _building_ids(world.get_player_faction())

    assert built.count(food_building_id) == 2
    assert built.count(material_building_id) == 1


# ==================================================================
# СТАРТОВЫЕ РЕСУРСЫ
# ==================================================================


@pytest.mark.parametrize(
    "difficulty, player_gold, rival_gold",
    [
        (DifficultyLevel.EASY, 1500.0, 800.0),
        (DifficultyLevel.NORMAL, 1000.0, 1000.0),
        (DifficultyLevel.HARD, 600.0, 1500.0),
    ],
)
async def test_treasury_follows_the_difficulty_table(
    generator: WorldGenerator,
    make_config: ConfigFactory,
    difficulty: DifficultyLevel,
    player_gold: float,
    rival_gold: float,
):
    world = await generator.generate(make_config(difficulty=difficulty))

    for faction in world.factions.values():
        expected = player_gold if faction.is_player_controlled else rival_gold
        assert faction.resources[ResourceType.GOLD] == expected


# ==================================================================
# СТАРТОВЫЕ АРМИИ
# ==================================================================


async def test_every_side_gets_one_army_on_its_capital(
    generator: WorldGenerator, make_config: ConfigFactory
):
    world = await generator.generate(make_config())

    assert len(world.armies) == len(world.factions)

    for faction in world.factions.values():
        armies = world.get_faction_armies(faction.id)
        assert len(armies) == 1
        assert armies[0].current_hex == faction.capital_hex


async def test_starting_army_holds_two_workers_and_two_infantry_squads(
    generator: WorldGenerator, make_config: ConfigFactory
):
    world = await generator.generate(make_config())

    for army in world.armies.values():
        tiers = [squad.archetype.tier for squad in army.squads]

        assert tiers.count(WORKER_UNIT_TIER) == STARTING_ARMY_WORKER_SQUADS
        assert tiers.count(STARTING_INFANTRY_UNIT_TIER) == STARTING_ARMY_INFANTRY_SQUADS
        assert len(army.squads) == (
            STARTING_ARMY_WORKER_SQUADS + STARTING_ARMY_INFANTRY_SQUADS
        )


async def test_starting_army_has_no_commander(
    generator: WorldGenerator, make_config: ConfigFactory
):
    """Без полководца армия стоит на месте, пока ей не назначат лидера."""
    world = await generator.generate(make_config())

    assert all(army.commander is None for army in world.armies.values())
    assert all(not army.heroes for army in world.armies.values())


# ==================================================================
# ПРАВИТЕЛИ
# ==================================================================


async def test_legendary_lord_takes_the_throne_by_id(
    generator: WorldGenerator, make_config: ConfigFactory
):
    config = make_config(
        player_faction=FactionSetupConfig(
            race=FactionRace.HUMANS,
            name="Империя",
            is_player_controlled=True,
            ruler=RulerSetupConfig(legendary_lord_id="lord_hum_kaspar_drake"),
        )
    )
    world = await generator.generate(config)

    lord = world.get_player_faction().lord

    assert lord.is_legendary is True
    assert lord.legendary_prompt_ref is not None


async def test_custom_lord_is_bound_to_his_new_realm(
    generator: WorldGenerator, make_config: ConfigFactory
):
    """
    Кастомного лорда мастер игры сочинил до партии - здесь ему проставляется
    держава, на трон которой он садится.
    """
    config = make_config(
        player_faction=FactionSetupConfig(
            race=FactionRace.HUMANS,
            name="Империя",
            is_player_controlled=True,
            ruler=RulerSetupConfig(
                custom_lord=Lord(faction_id="черновик", name="Тиберий Вольф")
            ),
        )
    )
    world = await generator.generate(config)

    player = world.get_player_faction()

    assert player.lord.name == "Тиберий Вольф"
    assert player.lord.faction_id == player.id


async def test_unknown_legendary_lord_is_rejected(
    generator: WorldGenerator, make_config: ConfigFactory
):
    config = make_config(
        player_faction=FactionSetupConfig(
            race=FactionRace.HUMANS,
            name="Империя",
            is_player_controlled=True,
            ruler=RulerSetupConfig(legendary_lord_id="lord_hum_no_such_person"),
        )
    )

    with pytest.raises(RulerTemplateNotFoundError):
        await generator.generate(config)


async def test_legendary_lord_of_another_race_is_rejected(
    generator: WorldGenerator, make_config: ConfigFactory
):
    """Имперский канцлер не сядет на трон орочьей орды."""
    config = make_config(
        rival_faction=FactionSetupConfig(
            race=FactionRace.GREENSKINS,
            name="Орда",
            ruler=RulerSetupConfig(legendary_lord_id="lord_hum_benedict_strauss"),
        )
    )

    with pytest.raises(RulerTemplateNotFoundError):
        await generator.generate(config)


async def test_every_side_gets_a_ruler_without_any_lobby_choice(
    generator: WorldGenerator, make_config: ConfigFactory
):
    world = await generator.generate(make_config())

    for faction in world.factions.values():
        assert faction.lord.faction_id == faction.id
        assert faction.lord.name


# ==================================================================
# ГАРНИЗОНЫ ЗЕМЕЛЬ
# ==================================================================


async def test_every_administrative_zone_gets_a_garrison(
    generator: WorldGenerator, make_config: ConfigFactory
):
    """Гарнизон - свойство земли: он есть и у цитадели, и у каждой ратуши."""
    world = await generator.generate(make_config())

    for faction in world.factions.values():
        garrisons = world.get_faction_garrisons(faction.id)
        zone_ids = {garrison.zone_id for garrison in garrisons}

        assert zone_ids == {
            hex_zone_id(faction.capital_hex),
            *faction.controlled_zone_ids,
        }


async def test_militia_is_raised_for_first_level_buildings(
    generator: WorldGenerator, make_config: ConfigFactory
):
    world = await generator.generate(make_config())

    for garrison in world.garrisons.values():
        assert len(garrison.militia_squads) == garrison.militia_capacity(1)
        assert not garrison.stationed_squads


# ==================================================================
# НИЧЬЯ ЗЕМЛЯ
# ==================================================================


async def test_all_lore_landmarks_stand_in_the_equatorial_belt(
    generator: WorldGenerator, make_config: ConfigFactory, static_registry
):
    world = await generator.generate(make_config())

    placed = [
        poi for poi in world.points_of_interest.values() if poi.blueprint.is_landmark
    ]
    catalog = static_registry.list_landmark_points_of_interest()

    assert len(placed) == len(catalog)
    assert {poi.blueprint.id for poi in placed} == {bp.id for bp in catalog}
    assert all(
        abs(poi.hex_coordinates.r) <= NO_MANS_LAND_LANDMARK_BELT_RADIUS for poi in placed
    )


async def test_procedural_points_are_scattered_over_neutral_hexes(
    generator: WorldGenerator, make_config: ConfigFactory
):
    world = await generator.generate(make_config())

    neutral = set(world.neutral_hexes)
    procedural = [
        poi
        for poi in world.points_of_interest.values()
        if not poi.blueprint.is_landmark
    ]

    assert procedural
    assert all(poi.hex_coordinates in neutral for poi in procedural)


async def test_ancient_battlefields_are_imperishable_and_hold_resonite(
    generator: WorldGenerator, make_config: ConfigFactory
):
    """
    Поля брани лорных ориентиров стоят веками: таймеру гниения они не
    подчиняются, а качают с них остаточный резонит.
    """
    world = await generator.generate(make_config())

    assert world.battlefield_sites

    for site in world.battlefield_sites.values():
        assert site.is_imperishable is True
        assert site.residual_resonite > 0.0
        assert site.is_depleted is False
        assert world.get_point_of_interest_at(site.hex_coordinates) is not None


# ==================================================================
# ДИПЛОМАТИЯ И ТУМАН ВОЙНЫ НУЛЕВОГО ТАКТА
# ==================================================================


async def test_all_sides_start_at_peace_without_pacts(
    generator: WorldGenerator, make_config: ConfigFactory
):
    world = await generator.generate(make_config())

    # Три стороны дают три пары отношений
    assert len(world.diplomatic_relations) == 3

    for relation in world.diplomatic_relations:
        assert relation.stance == DiplomaticStance.PEACE
        assert relation.non_aggression_pact is None
        assert relation.war_alliance is None
        assert relation.trade_agreement is None


async def test_every_side_sees_its_own_lands_and_nothing_of_the_enemy(
    generator: WorldGenerator, make_config: ConfigFactory
):
    world = await generator.generate(make_config())
    player = world.get_player_faction()
    rival = next(f for f in world.factions.values() if not f.is_player_controlled)

    assert world.is_hex_visible_to(player.id, player.capital_hex) is True
    assert all(
        world.is_hex_visible_to(player.id, coord) for coord in _occupied_hexes(player)
    )
    assert world.is_hex_visible_to(player.id, rival.capital_hex) is False


async def test_vision_map_is_calculated_for_every_side(
    generator: WorldGenerator, make_config: ConfigFactory
):
    world = await generator.generate(make_config())

    for faction in world.factions.values():
        vision_map = world.get_vision_map(faction.id)

        assert vision_map is not None
        assert vision_map.visible_hexes
        assert vision_map.visible_hexes <= vision_map.explored_hexes


# ==================================================================
# ПРАВИЛА ПАРТИИ
# ==================================================================


async def test_victory_rules_from_the_lobby_live_in_the_world(
    generator: WorldGenerator, make_config: ConfigFactory
):
    rules = VictoryConditionConfig(is_economic_enabled=False, gold_threshold=1234.0)
    world = await generator.generate(make_config(victory_config=rules))

    assert world.victory_config == rules
    assert world.victory_outcome is None
    assert world.is_finished is False


async def test_fresh_world_starts_at_tick_zero(
    generator: WorldGenerator, make_config: ConfigFactory
):
    world = await generator.generate(make_config())

    assert world.time.total_ticks == 0
    assert not world.active_events
    assert not world.worker_assignments
    assert not world.chronicle_entries
