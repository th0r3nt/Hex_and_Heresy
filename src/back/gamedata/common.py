"""
Общие константы каталога геймдаты: версия схемы и списки поддерживаемых рас.

DTO-модели ростеров живут в домене:
`src.back.l01_domain.army.models.card.roster.RosterEntry`.
"""

from typing import Final

from src.back.l01_domain.common import FactionRace

CATALOG_SCHEMA_VERSION: Final[str] = "1.0.0"

RACES: Final[list[FactionRace]] = [
    FactionRace.HUMANS,
    FactionRace.GREENSKINS,
    FactionRace.ELFS,
    FactionRace.BARONIAL_TROOPS,
    FactionRace.CONGREGATION_OF_THE_METEORITE,
    FactionRace.MERCENARIES,
    FactionRace.NEUTRALS,
]