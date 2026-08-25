"""
Тесты для src/back/l01_domain/world/models/state.py
"""

from src.back.l01_domain.army.models.characters.commanders import (
    Commander,
    CommanderArchetype,
    CommanderTrait,
)
from src.back.l01_domain.army.models.characters.heroes import Hero, HeroArchetype
from src.back.l01_domain.common import CharacterGenerationType, FactionRace
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.diplomacy.relation import DiplomaticRelation
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord, LordArchetype, LordTrait
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.constants import GlobalEventCategory
from src.back.l01_domain.world.models.battleground import BattlefieldLootSite
from src.back.l01_domain.world.models.events import GlobalEvent
from src.back.l01_domain.world.models.state import WorldState


def _make_dummy_faction(faction_id: str, name: str, is_player: bool = False) -> Faction:
    lord = Lord(
        faction_id=faction_id,
        name="Правитель",
        title="Барон",
        archetype=LordArchetype(id="arch_tyrant", name="Тиран", description="..."),
        trait=LordTrait(id="trait_harsh", name="Суровый", text_fragment="..."),
    )
    hq = Headquarters(faction_id=faction_id, name="Замок")
    return Faction(
        id=faction_id,
        race=FactionRace.HUMANS,
        name=name,
        is_player_controlled=is_player,
        lord=lord,
        headquarters=hq,
    )


class TestWorldState:
    def test_faction_management(self):
        world = WorldState()
        f_player = _make_dummy_faction("f_human", "Империя", is_player=True)
        f_enemy = _make_dummy_faction("f_orcs", "Орда", is_player=False)

        world.add_faction(f_player)
        world.add_faction(f_enemy)

        assert world.get_faction("f_human") == f_player
        assert world.get_player_faction() == f_player
        assert len(world.factions) == 2

    def test_available_commanders_and_heroes_pools(self):
        world = WorldState()

        commander = Commander(
            id="cmd_custom_hans",
            name="Сержант Ганс",
            faction_id="humans",
            generation_type=CharacterGenerationType.CUSTOM,
            archetype=CommanderArchetype(id="arch_vet", name="Ветеран", description="..."),
            trait=CommanderTrait(id="trait_cynic", name="Циник", text_fragment="..."),
            custom_biography="Потерял глаз в резне с гоблинами.",
            personality_prompt_override="Грубый и подозрительный ветеран.",
        )

        hero = Hero.create_new(
            name="Илай",
            faction_id="congregation_of_the_meteorite",
            archetype=HeroArchetype(
                id="arch_seer", name="Видящий", description="...", special_rule="..."
            ),
            max_hp=80.0,
            generation_type=CharacterGenerationType.CUSTOM,
            custom_biography="Бывший хирург Империи.",
        )

        # Добавление в пул доступных
        world.add_available_commander(commander)
        world.add_available_hero(hero)

        assert len(world.available_commanders) == 1
        assert world.available_commanders["cmd_custom_hans"].name == "Сержант Ганс"
        assert len(world.available_heroes) == 1
        assert world.available_heroes[hero.id].name == "Илай"

        # Извлечение из пула (например, при найме)
        removed_cmd = world.remove_available_commander("cmd_custom_hans")
        assert removed_cmd is commander
        assert len(world.available_commanders) == 0

        removed_hero = world.remove_available_hero(hero.id)
        assert removed_hero is hero
        assert len(world.available_heroes) == 0

    def test_diplomatic_relation_bidirectional_lookup(self):
        world = WorldState()
        rel = DiplomaticRelation(faction_a_id="f_1", faction_b_id="f_2")
        world.diplomatic_relations.append(rel)

        assert world.get_relation("f_1", "f_2") == rel
        assert world.get_relation("f_2", "f_1") == rel
        assert world.get_relation("f_1", "f_3") is None

    def test_events_cleanup(self):
        world = WorldState()
        active_event = GlobalEvent(
            name="Активное",
            description="...",
            category=GlobalEventCategory.ECONOMIC,
            is_active=True,
        )
        expired_event = GlobalEvent(
            name="Истекшее",
            description="...",
            category=GlobalEventCategory.WEATHER,
            is_active=False,
        )

        world.add_event(active_event)
        world.add_event(expired_event)
        world.cleanup_expired_events()

        assert world.active_events == [active_event]

    def test_battlefields_cleanup(self):
        world = WorldState()
        coord = HexCoordinates.from_axial(1, 1)
        fresh_site = BattlefieldLootSite(
            id="site_1",
            hex_coordinates=coord,
            origin_battle_id="b_1",
            salvageable_equipment={"sword": 5},
            ticks_remaining=3,
        )
        depleted_site = BattlefieldLootSite(
            id="site_2",
            hex_coordinates=HexCoordinates.from_axial(2, 2),
            origin_battle_id="b_2",
            ticks_remaining=0,
        )

        world.add_battlefield_site(fresh_site)
        world.add_battlefield_site(depleted_site)

        assert world.get_battlefield_at(coord) == fresh_site

        world.cleanup_depleted_battlefields()
        assert "site_1" in world.battlefield_sites
        assert "site_2" not in world.battlefield_sites
