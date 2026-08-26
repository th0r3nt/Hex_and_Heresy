"""
Каталог логических ключей промптов.

Домен знает, какой текст нужен роли ("персона", "роль лорда", "лор эльфов"),
но не знает, где этот текст лежит: разрешением ключа в файл на диске
занимается инфраструктура (l03_infrastructure/llm/prompt/).

Ключ - точечный идентификатор вида "roles.chronicler.rumors". Ни расширений,
ни разделителей пути в нем нет: слой сценариев не должен догадываться,
что за ключом стоит markdown-файл.
"""

from typing import Optional

from src.back.l01_domain.common import FactionRace


# ====================================================
# Каталог ключей
# ====================================================


class PromptCatalog:
    """Логические идентификаторы статических промптов ядра системы."""

    class BASE:
        PERSONA = "base.persona"

        class MECHANICS:
            ECONOMY = "base.mechanics.economy"
            STRATEGIC = "base.mechanics.strategic"
            TACTICAL = "base.mechanics.tactical"

    class FACTIONS:
        BARONIAL_TROOPS = "factions.baronial_troops"
        CONGREGATION_OF_THE_METEORITE = "factions.congregation_of_the_meteorite"
        ELFS = "factions.elfs"
        GREENSKINS = "factions.greenskins"
        HUMANS = "factions.humans"
        MERCENARIES = "factions.mercenaries"
        NEUTRALS = "factions.neutrals"

    class LORE:
        class BASIC:
            LOW = "lore.basic.low"
            MEDIUM = "lore.basic.medium"
            HIGH = "lore.basic.high"
            MAX = "lore.basic.max"

        class MAGIC:
            LOW = "lore.magic.low"
            MEDIUM = "lore.magic.medium"
            HIGH = "lore.magic.high"
            MAX = "lore.magic.max"

        class FACTIONS:
            class BARONIAL_TROOPS:
                LOW = "lore.factions.baronial_troops.low"
                MEDIUM = "lore.factions.baronial_troops.medium"
                HIGH = "lore.factions.baronial_troops.high"
                MAX = "lore.factions.baronial_troops.max"

            class CONGREGATION_OF_THE_METEORITE:
                LOW = "lore.factions.congregation_of_the_meteorite.low"
                MEDIUM = "lore.factions.congregation_of_the_meteorite.medium"
                HIGH = "lore.factions.congregation_of_the_meteorite.high"
                MAX = "lore.factions.congregation_of_the_meteorite.max"

            class ELFS:
                LOW = "lore.factions.elfs.low"
                MEDIUM = "lore.factions.elfs.medium"
                HIGH = "lore.factions.elfs.high"
                MAX = "lore.factions.elfs.max"

            class GREENSKINS:
                LOW = "lore.factions.greenskins.low"
                MEDIUM = "lore.factions.greenskins.medium"
                HIGH = "lore.factions.greenskins.high"
                MAX = "lore.factions.greenskins.max"

            class HUMANS:
                LOW = "lore.factions.humans.low"
                MEDIUM = "lore.factions.humans.medium"
                HIGH = "lore.factions.humans.high"
                MAX = "lore.factions.humans.max"

            class MERCENARIES:
                LOW = "lore.factions.mercenaries.low"
                MEDIUM = "lore.factions.mercenaries.medium"
                HIGH = "lore.factions.mercenaries.high"
                MAX = "lore.factions.mercenaries.max"

    class ROLES:
        ADVISOR = "roles.advisor.prompt"
        COMMANDER = "roles.commander.prompt"
        DIPLOMAT = "roles.diplomat.prompt"
        GAME_MASTER = "roles.game_master.prompt"
        GUNSMITH = "roles.gunsmith.prompt"
        HERO = "roles.hero.prompt"
        LORD = "roles.lord.prompt"
        VETERAN = "roles.veteran.prompt"

        class CHRONICLER:
            PROMPT = "roles.chronicler.prompt"
            RUMORS = "roles.chronicler.rumors"

            class WRITING:
                NEUTRAL = "roles.chronicler.neutral.writing"
                BARONIAL_TROOPS = "roles.chronicler.baronial_troops.writing"
                CONGREGATION_OF_THE_METEORITE = (
                    "roles.chronicler.congregation_of_the_meteorite.writing"
                )
                ELFS = "roles.chronicler.elfs.writing"
                GREENSKINS = "roles.chronicler.greenskins.writing"
                HUMANS = "roles.chronicler.humans.writing"
                MERCENARIES = "roles.chronicler.mercenaries.writing"


# ====================================================
# Выбор ключа по расе
# ====================================================


def get_faction_prompt_key(race: FactionRace) -> str:
    """Сопоставляет расу фракции с ключом ее описания."""
    mapping = {
        FactionRace.HUMANS: PromptCatalog.FACTIONS.HUMANS,
        FactionRace.GREENSKINS: PromptCatalog.FACTIONS.GREENSKINS,
        FactionRace.ELFS: PromptCatalog.FACTIONS.ELFS,
        FactionRace.BARONIAL_TROOPS: PromptCatalog.FACTIONS.BARONIAL_TROOPS,
        FactionRace.CONGREGATION_OF_THE_METEORITE: (
            PromptCatalog.FACTIONS.CONGREGATION_OF_THE_METEORITE
        ),
        FactionRace.MERCENARIES: PromptCatalog.FACTIONS.MERCENARIES,
        FactionRace.NEUTRALS: PromptCatalog.FACTIONS.NEUTRALS,
    }
    return mapping[race]


def get_chronicler_writing_key(race: Optional[FactionRace]) -> str:
    """
    Ключ стиля записи летописца. Без расы (или у нейтралов) стиль нейтральный:
    у боя не было своего писаря.
    """
    if race is None or race == FactionRace.NEUTRALS:
        return PromptCatalog.ROLES.CHRONICLER.WRITING.NEUTRAL

    mapping = {
        FactionRace.HUMANS: PromptCatalog.ROLES.CHRONICLER.WRITING.HUMANS,
        FactionRace.GREENSKINS: PromptCatalog.ROLES.CHRONICLER.WRITING.GREENSKINS,
        FactionRace.ELFS: PromptCatalog.ROLES.CHRONICLER.WRITING.ELFS,
        FactionRace.BARONIAL_TROOPS: PromptCatalog.ROLES.CHRONICLER.WRITING.BARONIAL_TROOPS,
        FactionRace.CONGREGATION_OF_THE_METEORITE: (
            PromptCatalog.ROLES.CHRONICLER.WRITING.CONGREGATION_OF_THE_METEORITE
        ),
        FactionRace.MERCENARIES: PromptCatalog.ROLES.CHRONICLER.WRITING.MERCENARIES,
    }
    return mapping.get(race, PromptCatalog.ROLES.CHRONICLER.WRITING.NEUTRAL)
