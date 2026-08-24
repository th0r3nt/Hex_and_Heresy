"""
Тесты для src/back/l01_domain/world/models/chronicle.py

Проверяем подрезку разговорившейся модели и сборку записей летописи,
а также то, что WorldState не плодит дубли свитков и надгробий.
"""

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.world.constants import (
    CHRONICLE_BODY_MAX_LENGTH,
    CHRONICLE_TITLE_MAX_LENGTH,
    RUMOR_TEXT_MAX_LENGTH,
)
from src.back.l01_domain.world.models.chronicle import (
    ChronicleEntry,
    FallenRecord,
    LLMChronicleResponse,
    LLMEpitaphResponse,
    RumorEntry,
)
from src.back.l01_domain.world.models.state import WorldState


class TestLLMResponseClamping:
    def test_long_text_is_trimmed_instead_of_rejected(self):
        response = LLMChronicleResponse(
            title="Т" * (CHRONICLE_TITLE_MAX_LENGTH + 50),
            quote="Цитата",
            body="Б" * (CHRONICLE_BODY_MAX_LENGTH + 500),
        )

        assert len(response.title) == CHRONICLE_TITLE_MAX_LENGTH
        assert len(response.body) == CHRONICLE_BODY_MAX_LENGTH
        assert response.title.endswith("…")

    def test_short_text_survives_untouched(self):
        response = LLMChronicleResponse(
            title="Резня в Долине ржавых мечей",
            quote="Они умерли за Империю.",
            body="Текст истории.",
        )

        assert response.title == "Резня в Долине ржавых мечей"
        assert response.body == "Текст истории."

    def test_whitespace_is_stripped(self):
        response = LLMEpitaphResponse(title="  Маркус  ", epitaph="\n Полег у ворот. \n")

        assert response.title == "Маркус"
        assert response.epitaph == "Полег у ворот."

    def test_rumor_text_is_clamped(self):
        rumor = RumorEntry(text="С" * (RUMOR_TEXT_MAX_LENGTH + 10), tick=4)

        assert len(rumor.text) == RUMOR_TEXT_MAX_LENGTH


class TestChronicleEntry:
    def test_built_from_llm_response(self):
        response = LLMChronicleResponse(
            title="Резня в Долине ржавых мечей",
            quote="И за пару сапог.",
            body="Текст истории.",
        )

        entry = ChronicleEntry.from_response(
            response,
            battle_id="battle_1",
            tick=12,
            location_name="Долина ржавых мечей",
            faction_id="humans",
        )

        assert entry.battle_id == "battle_1"
        assert entry.title == "Резня в Долине ржавых мечей"
        assert entry.tick == 12
        assert entry.location_name == "Долина ржавых мечей"
        assert entry.faction_id == "humans"


class TestWorldStateChronicle:
    def _entry(self, battle_id: str = "battle_1") -> ChronicleEntry:
        return ChronicleEntry(battle_id=battle_id, title="Заголовок", body="Текст")

    def _record(self, squad_id: str = "squad_1") -> FallenRecord:
        return FallenRecord(
            squad_id=squad_id,
            squad_name="Грязные стрелки Маркуса",
            race=FactionRace.HUMANS,
            epitaph="Полегли у ворот.",
        )

    def test_chronicle_entry_is_written_once_per_battle(self):
        world = WorldState()

        world.add_chronicle_entry(self._entry())
        world.add_chronicle_entry(self._entry())
        world.add_chronicle_entry(self._entry("battle_2"))

        assert [e.battle_id for e in world.chronicle_entries] == ["battle_1", "battle_2"]

    def test_squad_is_buried_once(self):
        world = WorldState()

        world.add_fallen_record(self._record())
        world.add_fallen_record(self._record())

        assert len(world.fallen_records) == 1

    def test_rumors_are_appended_as_is(self):
        world = WorldState()

        world.add_rumor(RumorEntry(text="Барон опять поднял налоги.", tick=3))
        world.add_rumor(RumorEntry(text="Снег сегодня серый, как сталь.", tick=4))

        assert len(world.rumors) == 2

    def test_battle_resets_silence_counter(self):
        world = WorldState()
        world.ticks_since_last_battle = 5

        world.register_battle_happened()

        assert world.ticks_since_last_battle == 0

    def test_chronicle_survives_save_round_trip(self):
        """Летопись должна уезжать в сейв вместе с остальным миром."""
        world = WorldState()
        world.add_chronicle_entry(self._entry())
        world.add_fallen_record(self._record())
        world.add_rumor(RumorEntry(text="В Черных топях неспокойно.", tick=2))

        restored = WorldState.model_validate_json(world.model_dump_json())

        assert restored.chronicle_entries[0].title == "Заголовок"
        assert restored.fallen_records[0].squad_name == "Грязные стрелки Маркуса"
        assert restored.rumors[0].text == "В Черных топях неспокойно."
