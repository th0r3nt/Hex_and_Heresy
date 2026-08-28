"""
Интеграционные тесты каталога легендарных личностей, ростеров найма и
точек интереса Ничьей земли.

Главное, что здесь проверяется, - каталог не разъезжается с остальным
проектом: у каждой личности есть реальный файл промпта на диске и только
существующие черты из TRAITS_CATALOG.
"""

from pathlib import Path

import pytest

from src.back.gamedata.baronial_troops.common import BaronialLordId
from src.back.gamedata.congregation_of_the_meteorite.common import CongregationHeroId
from src.back.gamedata.elfs.common import ElfsCommanderId
from src.back.gamedata.greenskins.common import GreenskinsLordId
from src.back.gamedata.humans.common import HumanLordId, HumanRosterId
from src.back.gamedata.mercenaries.common import MercenaryHeroId
from src.back.gamedata.world.common import PointOfInterestId
from src.back.l01_domain.army.models.characters.traits import TRAITS_CATALOG
from src.back.l01_domain.common import CharacterGenerationType, FactionRace
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l03_infrastructure.gamedata.loader import build_static_registry
from src.back.l03_infrastructure.llm.prompt.catalog import resolve_prompt_key

# Расы, у которых каталог легендарных личностей обязан быть непустым
PLAYABLE_RACES = [
    FactionRace.HUMANS,
    FactionRace.GREENSKINS,
    FactionRace.ELFS,
    FactionRace.BARONIAL_TROOPS,
    FactionRace.CONGREGATION_OF_THE_METEORITE,
]

PROMPTS_DIR = Path(__file__).resolve().parents[3] / "l03_infrastructure" / "llm" / "prompt"


@pytest.fixture(scope="module")
def registry():
    return build_static_registry()


# ==================================================================
# ЛЕГЕНДАРНЫЕ ЛИЧНОСТИ
# ==================================================================


class TestLegendaryCatalog:
    @pytest.mark.parametrize("race", PLAYABLE_RACES)
    def test_every_playable_race_has_lords_commanders_and_heroes(self, registry, race):
        assert registry.list_faction_legendary_lords(race.value)
        assert registry.list_faction_legendary_commanders(race.value)
        assert registry.list_faction_legendary_heroes(race.value)

    def test_mercenaries_have_only_captains(self, registry):
        """Наемники - нейтральная сила без цитадели: ни лордов, ни полководцев."""
        assert registry.list_faction_legendary_lords(FactionRace.MERCENARIES.value) == []
        assert registry.list_faction_legendary_commanders(FactionRace.MERCENARIES.value) == []
        assert len(registry.list_faction_legendary_heroes(FactionRace.MERCENARIES.value)) == 3

    def test_neutrals_have_no_personalities(self, registry):
        assert registry.list_faction_legendary_lords(FactionRace.NEUTRALS.value) == []
        assert registry.list_faction_legendary_heroes(FactionRace.NEUTRALS.value) == []

    def test_known_personalities_are_registered_by_id(self, registry):
        strauss = registry.get_legendary_lord(HumanLordId.BENEDICT_STRAUSS.value)
        assert strauss is not None
        assert strauss.name == "Бенедикт Штраусс"
        assert strauss.title == "Верховный канцлер"

        khmyr = registry.get_legendary_lord(GreenskinsLordId.BARON_KHMYR.value)
        assert khmyr is not None
        assert khmyr.bias.bribery_susceptibility > 0.5  # Его покупают, и он не скрывает

        kaelin = registry.get_legendary_commander(ElfsCommanderId.KAELIN.value)
        assert kaelin is not None
        assert kaelin.characteristics.resilience > kaelin.characteristics.cunning

        malakai = registry.get_legendary_hero(CongregationHeroId.MALAKAI.value)
        assert malakai is not None
        assert malakai.max_hp > 0

        hector = registry.get_legendary_hero(MercenaryHeroId.HECTOR.value)
        assert hector is not None
        assert hector.race == FactionRace.MERCENARIES

    def test_every_personality_points_to_existing_prompt_file(self, registry):
        """Ссылка на файл личности не должна вести в пустоту."""
        broken = []
        for race in list(PLAYABLE_RACES) + [FactionRace.MERCENARIES]:
            for template in _all_templates(registry, race):
                prompt_file = PROMPTS_DIR / resolve_prompt_key(template.prompt_ref)
                if not prompt_file.is_file():
                    broken.append((template.id, template.prompt_ref))

        assert broken == []

    def test_every_personality_uses_known_traits(self, registry):
        """Черты берутся только из общего каталога, опечаток в геймдате нет."""
        unknown = []
        for race in list(PLAYABLE_RACES) + [FactionRace.MERCENARIES]:
            for template in _all_templates(registry, race):
                for trait_id in template.trait_ids:
                    if trait_id not in TRAITS_CATALOG:
                        unknown.append((template.id, trait_id))
                    assert len(template.resolve_traits()) == len(template.trait_ids)

        assert unknown == []

    def test_ids_are_unique_across_the_whole_catalog(self, registry):
        seen: list[str] = []
        for race in list(PLAYABLE_RACES) + [FactionRace.MERCENARIES]:
            seen.extend(t.id for t in _all_templates(registry, race))

        assert len(seen) == len(set(seen))

    def test_template_builds_playable_aggregate(self, registry):
        template = registry.get_legendary_lord(BaronialLordId.LADY_ISOLDE.value)

        lord = template.build(faction_id="faction-under-test")

        assert lord.faction_id == "faction-under-test"
        assert lord.is_legendary
        assert lord.generation_type == CharacterGenerationType.LEGENDARY
        assert lord.legendary_prompt_ref == template.prompt_ref
        assert lord.traits


def _all_templates(registry, race: FactionRace) -> list:
    """Все легендарные личности расы одним списком."""
    return [
        *registry.list_faction_legendary_lords(race.value),
        *registry.list_faction_legendary_commanders(race.value),
        *registry.list_faction_legendary_heroes(race.value),
    ]


# ==================================================================
# РОСТЕР НАЙМА
# ==================================================================


class TestRosterCatalog:
    def test_registry_loads_recruitment_recipes(self, registry):
        builders = registry.get_roster_entry(HumanRosterId.ROSTER_BUILDERS.value)

        assert builders is not None
        assert builders.faction_id == FactionRace.HUMANS.value
        assert builders.unit_archetype_id

    @pytest.mark.parametrize("race", PLAYABLE_RACES)
    def test_every_playable_race_has_roster(self, registry, race):
        assert registry.list_faction_roster(race.value)

    def test_roster_recipes_reference_existing_cards(self, registry):
        """Рецепт найма не должен ссылаться на несуществующий юнит или предмет."""
        dangling = []
        for race in list(FactionRace):
            for entry in registry.list_faction_roster(race.value):
                if registry.get_unit_archetype(entry.unit_archetype_id) is None:
                    dangling.append((entry.id, entry.unit_archetype_id))
                for equipment_id in (entry.weapon_id, entry.armor_id, entry.accessory_id):
                    if equipment_id is not None and registry.get_equipment(equipment_id) is None:
                        dangling.append((entry.id, equipment_id))

        assert dangling == []


# ==================================================================
# ТОЧКИ ИНТЕРЕСА
# ==================================================================


class TestPointsOfInterestCatalog:
    def test_all_five_landmarks_are_loaded(self, registry):
        landmark_ids = {poi.id for poi in registry.list_landmark_points_of_interest()}

        assert landmark_ids == {
            PointOfInterestId.RUSTY_SWORDS_VALLEY.value,
            PointOfInterestId.RADIANCE_CRATER.value,
            PointOfInterestId.OLD_STADT.value,
            PointOfInterestId.SORROW_LOWLAND.value,
            PointOfInterestId.SIEGE_COLOSSI_GRAVEYARD.value,
        }

    def test_procedural_pool_is_not_empty_and_holds_no_landmarks(self, registry):
        procedural = registry.list_procedural_points_of_interest()

        assert procedural
        assert all(not poi.is_landmark for poi in procedural)

    def test_resonite_places_are_useless_for_humans(self, registry):
        """Люди резонит не используют: Кратер сияния не дает им ничего."""
        crater = registry.get_point_of_interest(PointOfInterestId.RADIANCE_CRATER.value)
        placed = crater.build(_any_hex())

        assert placed.yield_multiplier_for(ResourceType.MATERIAL, FactionRace.ELFS) > 1.0
        assert placed.yield_multiplier_for(ResourceType.MATERIAL, FactionRace.HUMANS) == 0.0
        assert placed.has_morale_penalty_for(FactionRace.HUMANS)

    def test_mycelium_lowland_feeds_greenskins_and_scares_humans(self, registry):
        lowland = registry.get_point_of_interest(PointOfInterestId.SORROW_LOWLAND.value)
        placed = lowland.build(_any_hex())

        assert placed.yield_multiplier_for(ResourceType.FOOD, FactionRace.GREENSKINS) > 2.0
        assert placed.has_morale_penalty_for(FactionRace.HUMANS)
        assert not placed.has_morale_penalty_for(FactionRace.GREENSKINS)


def _any_hex():
    from src.back.l01_domain.maps.models.strategic import HexCoordinates

    return HexCoordinates.from_axial(0, 0)
