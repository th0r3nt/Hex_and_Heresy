"""
Тесты доменного каталога логических ключей промптов.

Соответствие ключей реальным файлам проверяется уже в инфраструктуре
(tests/l03_infrastructure/llm/test_prompt_catalog_integrity.py).
"""

import pytest

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.llm.prompts import (
    PromptCatalog,
    get_chronicler_writing_key,
    get_faction_prompt_key,
)


class TestFactionKeys:
    def test_every_race_has_its_own_key(self):
        keys = [get_faction_prompt_key(race) for race in FactionRace]

        assert len(set(keys)) == len(list(FactionRace))

    @pytest.mark.parametrize(
        "race, expected",
        [
            (FactionRace.HUMANS, PromptCatalog.FACTIONS.HUMANS),
            (FactionRace.ELFS, PromptCatalog.FACTIONS.ELFS),
            (FactionRace.GREENSKINS, PromptCatalog.FACTIONS.GREENSKINS),
            (FactionRace.BARONIAL_TROOPS, PromptCatalog.FACTIONS.BARONIAL_TROOPS),
            (
                FactionRace.CONGREGATION_OF_THE_METEORITE,
                PromptCatalog.FACTIONS.CONGREGATION_OF_THE_METEORITE,
            ),
            (FactionRace.MERCENARIES, PromptCatalog.FACTIONS.MERCENARIES),
            (FactionRace.NEUTRALS, PromptCatalog.FACTIONS.NEUTRALS),
        ],
    )
    def test_race_maps_to_its_description(self, race: FactionRace, expected: str):
        assert get_faction_prompt_key(race) == expected


class TestChroniclerWritingKeys:
    def test_faction_style_is_taken_from_the_race(self):
        assert (
            get_chronicler_writing_key(FactionRace.GREENSKINS)
            == PromptCatalog.ROLES.CHRONICLER.WRITING.GREENSKINS
        )

    @pytest.mark.parametrize("race", [None, FactionRace.NEUTRALS])
    def test_battle_without_a_scribe_gets_the_neutral_style(self, race):
        assert (
            get_chronicler_writing_key(race)
            == PromptCatalog.ROLES.CHRONICLER.WRITING.NEUTRAL
        )
