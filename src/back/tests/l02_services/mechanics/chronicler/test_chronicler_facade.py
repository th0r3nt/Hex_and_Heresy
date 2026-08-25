"""
Тесты фасада летописца: порог значимости боя, запись летописи и некрологов,
поведение без языковой модели и устойчивость к ее отказам.
"""

import pytest

from src.back.l01_domain.combat.models.reports import MeleeCombatReport
from src.back.l01_domain.exceptions.llm import LLMRequestFailedError
from src.back.l01_domain.world.models.chronicle import LLMChronicleResponse
from src.back.l02_services.mechanics.chronicler.facade import ChroniclerFacade
from src.back.utils.event.registry import GameEvents


@pytest.fixture
def facade(fake_llm, fake_repository, fake_bus, fake_prompt_builder) -> ChroniclerFacade:
    return ChroniclerFacade(
        llm_client=fake_llm, 
        repository=fake_repository, 
        event_bus=fake_bus,
        prompt_builder=fake_prompt_builder
    )


def wipe_defenders(make_report, tick: int = 1, victor: str = "humans"):
    """Финальный раунд, в котором обороняющиеся выбиты подчистую."""
    return make_report(
        tick=tick,
        melee_reports=[
            MeleeCombatReport(
                attacker_squad_id="atk_0", defender_squad_id=f"def_{i}", kills=100
            )
            for i in range(6)
        ],
        is_battle_finished=True,
        victor_faction_id=victor,
    )


class TestChronicleWorthiness:
    def test_large_battle_is_worthy(self, facade, world, battle_state, battle_squads, battle_hex):
        dossier = facade.on_battle_started(world, battle_state, battle_squads, battle_hex)

        assert facade.is_chronicle_worthy(dossier) is True

    def test_small_skirmish_is_not_worthy(
        self, facade, world, battle_state, battle_squads, battle_hex
    ):
        battle_state.attacker_squad_ids = ["atk_0", "atk_1"]
        battle_state.defender_squad_ids = ["def_0", "def_1"]

        dossier = facade.on_battle_started(world, battle_state, battle_squads, battle_hex)

        assert facade.is_chronicle_worthy(dossier) is False

    def test_siege_is_always_worthy(
        self, facade, world, battle_state, battle_squads, humans
    ):
        battle_state.attacker_squad_ids = ["atk_0"]
        battle_state.defender_squad_ids = ["def_0"]

        dossier = facade.on_battle_started(
            world, battle_state, battle_squads, humans.capital_hex
        )

        assert facade.is_chronicle_worthy(dossier) is True

    def test_dead_veteran_makes_skirmish_worthy(
        self, facade, world, battle_state, battle_squads, battle_hex
    ):
        battle_state.attacker_squad_ids = ["atk_0"]
        battle_state.defender_squad_ids = ["def_0"]
        battle_squads["def_0"].veterancy.promote(
            commander_name="Гразнык",
            squad_nickname="Клыки Гразныка",
            trait_name="Упрямые",
            lore="...",
        )

        dossier = facade.on_battle_started(world, battle_state, battle_squads, battle_hex)
        dossier.add_deaths("def_0", 100)

        assert facade.is_chronicle_worthy(dossier) is True

    def test_slain_hero_makes_skirmish_worthy(
        self, facade, world, battle_state, battle_squads, battle_hex
    ):
        battle_state.attacker_squad_ids = ["atk_0"]
        battle_state.defender_squad_ids = ["def_0"]
        dossier = facade.on_battle_started(world, battle_state, battle_squads, battle_hex)

        facade.note_hero_slain(dossier.battle_id, "Гром Железное брюхо")

        assert dossier.heroes_slain == ["Гром Железное брюхо"]
        assert facade.is_chronicle_worthy(dossier) is True


class TestChronicleBattle:
    @pytest.mark.asyncio
    async def test_writes_entry_and_publishes_event(
        self, facade, world, battle_state, battle_squads, battle_hex,
        make_report, fake_llm, fake_bus, fake_repository,
    ):
        facade.on_battle_started(world, battle_state, battle_squads, battle_hex)

        entry = await facade.chronicle_battle(world, wipe_defenders(make_report))

        assert entry is not None
        assert entry.title == "Резня в Долине ржавых мечей"
        assert entry.location_name == "Ничья земля (4, 0)"
        assert world.chronicle_entries == [entry]
        assert len(fake_llm.structured_calls) == 1
        assert GameEvents.Chronicler.BATTLE_RECORDED in fake_bus.names()
        assert fake_repository.history[0]["battle_id"] == "battle_1"

    @pytest.mark.asyncio
    async def test_context_reaches_the_model(
        self, facade, world, battle_state, battle_squads, battle_hex, make_report, fake_llm
    ):
        facade.on_battle_started(world, battle_state, battle_squads, battle_hex)

        await facade.chronicle_battle(world, wipe_defenders(make_report))

        user_prompt = fake_llm.structured_calls[0]["user_prompt"]
        assert "Оборонявшиеся (6 карточек" in user_prompt
        assert "уничтожен полностью" in user_prompt

    @pytest.mark.asyncio
    async def test_player_faction_sets_the_style(
        self, facade, world, battle_state, battle_squads, battle_hex, make_report, fake_llm
    ):
        """Свиток читает игрок, поэтому пишется он в культуре его фракции."""
        facade.on_battle_started(world, battle_state, battle_squads, battle_hex)

        entry = await facade.chronicle_battle(world, wipe_defenders(make_report, victor="greenskins"))

        assert entry is not None
        assert entry.faction_id == "humans"
        # Проверяем, что в промпт ушел лорный файл людей, а не зеленокожих
        assert "[factions/humans.md]" in fake_llm.structured_calls[0]["system_prompt"]

    @pytest.mark.asyncio
    async def test_skirmish_is_not_written(
        self, facade, world, battle_state, battle_squads, battle_hex, make_report, fake_llm
    ):
        battle_state.attacker_squad_ids = ["atk_0"]
        battle_state.defender_squad_ids = ["def_0"]
        facade.on_battle_started(world, battle_state, battle_squads, battle_hex)

        entry = await facade.chronicle_battle(
            world,
            make_report(tick=1, is_battle_finished=True, victor_faction_id="humans"),
        )

        assert entry is None
        assert world.chronicle_entries == []
        assert fake_llm.structured_calls == []

    @pytest.mark.asyncio
    async def test_battle_resets_the_silence_counter(
        self, facade, world, battle_state, battle_squads, battle_hex, make_report
    ):
        world.ticks_since_last_battle = 7
        facade.on_battle_started(world, battle_state, battle_squads, battle_hex)

        await facade.chronicle_battle(world, wipe_defenders(make_report))

        assert world.ticks_since_last_battle == 0

    @pytest.mark.asyncio
    async def test_unknown_battle_does_not_break_the_turn(self, facade, world, make_report):
        """Бой, начало которого летописец пропустил, просто не попадет в летопись."""
        entry = await facade.chronicle_battle(
            world, make_report(battle_id="battle_unseen", is_battle_finished=True)
        )

        assert entry is None

    @pytest.mark.asyncio
    async def test_dossier_is_forgotten_after_the_chronicle(
        self, facade, world, battle_state, battle_squads, battle_hex, make_report
    ):
        facade.on_battle_started(world, battle_state, battle_squads, battle_hex)
        await facade.chronicle_battle(world, wipe_defenders(make_report))

        assert facade.on_battle_turn(make_report(tick=2)) is None

    @pytest.mark.asyncio
    async def test_second_chronicle_of_one_battle_is_ignored(
        self, facade, world, battle_state, battle_squads, battle_hex, make_report, fake_llm
    ):
        facade.on_battle_started(world, battle_state, battle_squads, battle_hex)
        await facade.chronicle_battle(world, wipe_defenders(make_report))

        facade.on_battle_started(world, battle_state, battle_squads, battle_hex)
        await facade.chronicle_battle(world, wipe_defenders(make_report, tick=2))

        assert len(world.chronicle_entries) == 1
        assert len(fake_llm.structured_calls) == 1


class TestTurnAccumulation:
    @pytest.mark.asyncio
    async def test_losses_of_all_rounds_reach_the_model(
        self, facade, world, battle_state, battle_squads, battle_hex, make_report, fake_llm
    ):
        facade.on_battle_started(world, battle_state, battle_squads, battle_hex)

        facade.on_battle_turn(
            make_report(
                tick=1,
                melee_reports=[
                    MeleeCombatReport(
                        attacker_squad_id="atk_0", defender_squad_id="def_0", kills=40
                    )
                ],
            )
        )
        await facade.chronicle_battle(
            world,
            make_report(
                tick=2,
                melee_reports=[
                    MeleeCombatReport(
                        attacker_squad_id="atk_0", defender_squad_id="def_0", kills=60
                    )
                ],
                is_battle_finished=True,
                victor_faction_id="humans",
            ),
        )

        user_prompt = fake_llm.structured_calls[0]["user_prompt"]
        assert "погибло 100" in user_prompt


class TestHallOfFallen:
    @pytest.fixture
    def facade_with_veteran(self, facade, world, battle_state, battle_squads, battle_hex):
        battle_squads["def_0"].veterancy.promote(
            commander_name="Гразнык",
            squad_nickname="Клыки Гразныка",
            trait_name="Упрямые",
            lore="...",
        )
        facade.on_battle_started(world, battle_state, battle_squads, battle_hex)
        return facade

    @pytest.mark.asyncio
    async def test_named_squad_gets_an_epitaph(
        self, facade_with_veteran, world, make_report, fake_bus, fake_repository
    ):
        await facade_with_veteran.chronicle_battle(world, wipe_defenders(make_report))

        assert len(world.fallen_records) == 1
        record = world.fallen_records[0]
        assert record.squad_name == "Клыки Гразныка"
        assert record.commander_name == "Гразнык"
        assert record.killer_name == "humans"
        assert GameEvents.Chronicler.FALLEN_RECORDED in fake_bus.names()
        assert fake_repository.fallen[0]["squad_name"] == "Клыки Гразныка"

    @pytest.mark.asyncio
    async def test_nameless_militia_is_not_buried_personally(
        self, facade, world, battle_state, battle_squads, battle_hex, make_report
    ):
        facade.on_battle_started(world, battle_state, battle_squads, battle_hex)

        await facade.chronicle_battle(world, wipe_defenders(make_report))

        assert world.fallen_records == []

    @pytest.mark.asyncio
    async def test_surviving_veteran_is_not_buried(
        self, facade, world, battle_state, battle_squads, battle_hex, make_report
    ):
        battle_squads["def_1"].veterancy.promote(
            commander_name="Гразнык",
            squad_nickname="Клыки Гразныка",
            trait_name="Упрямые",
            lore="...",
        )
        facade.on_battle_started(world, battle_state, battle_squads, battle_hex)

        await facade.chronicle_battle(
            world,
            make_report(
                tick=1,
                melee_reports=[
                    MeleeCombatReport(
                        attacker_squad_id="atk_0", defender_squad_id="def_1", kills=30
                    )
                ],
                is_battle_finished=True,
                victor_faction_id="humans",
            ),
        )

        assert world.fallen_records == []

    @pytest.mark.asyncio
    async def test_veteran_is_buried_once(
        self, facade_with_veteran, world, battle_state, battle_squads, battle_hex, make_report
    ):
        await facade_with_veteran.chronicle_battle(world, wipe_defenders(make_report))

        facade_with_veteran.on_battle_started(world, battle_state, battle_squads, battle_hex)
        await facade_with_veteran.chronicle_battle(world, wipe_defenders(make_report, tick=2))

        assert len(world.fallen_records) == 1


class TestWithoutLLM:
    @pytest.fixture
    def silent_facade(self, fake_bus) -> ChroniclerFacade:
        return ChroniclerFacade(event_bus=fake_bus)

    @pytest.mark.asyncio
    async def test_battle_is_counted_but_not_written(
        self, silent_facade, world, battle_state, battle_squads, battle_hex, make_report
    ):
        world.ticks_since_last_battle = 5
        silent_facade.on_battle_started(world, battle_state, battle_squads, battle_hex)

        entry = await silent_facade.chronicle_battle(world, wipe_defenders(make_report))

        assert entry is None
        assert world.chronicle_entries == []
        assert world.ticks_since_last_battle == 0

    @pytest.mark.asyncio
    async def test_rumors_are_silent(self, silent_facade, world):
        world.ticks_since_last_battle = 10

        assert await silent_facade.speak_rumor(world) is None


class TestLLMFailures:
    @pytest.mark.asyncio
    async def test_model_failure_does_not_break_the_battle(
        self, world, battle_state, battle_squads, battle_hex, make_report, fake_bus
    ):
        class BrokenLLM:
            async def generate_text(self, *args, **kwargs):
                raise LLMRequestFailedError("local", "model", "нет сети")

            async def generate_structured(self, *args, **kwargs):
                raise LLMRequestFailedError("local", "model", "нет сети")

        facade = ChroniclerFacade(llm_client=BrokenLLM(), event_bus=fake_bus)
        facade.on_battle_started(world, battle_state, battle_squads, battle_hex)

        entry = await facade.chronicle_battle(world, wipe_defenders(make_report))

        assert entry is None
        assert world.chronicle_entries == []
        assert GameEvents.Chronicler.BATTLE_RECORDED not in fake_bus.names()

    @pytest.mark.asyncio
    async def test_blank_body_is_rejected(
        self, world, battle_state, battle_squads, battle_hex, make_report, fake_llm
    ):
        fake_llm.chronicle = LLMChronicleResponse(title="Заголовок", quote="", body="   ")
        facade = ChroniclerFacade(llm_client=fake_llm)
        facade.on_battle_started(world, battle_state, battle_squads, battle_hex)

        entry = await facade.chronicle_battle(world, wipe_defenders(make_report))

        assert entry is None
        assert world.chronicle_entries == []
