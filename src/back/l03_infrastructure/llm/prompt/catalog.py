"""
Статический реестр путей к файлам промптов.
Обеспечивает строгую типизацию и защиту от опечаток при сборке контекста для LLM.
"""

from typing import Optional

from src.back.l01_domain.common import FactionRace


class PromptCatalog:
    """Корневой каталог всех markdown-файлов промптов."""

    class BASE:
        PERSONA = "base/persona.md"

        class MECHANICS:
            ECONOMY = "base/mechanics/economy.md"
            STRATEGIC = "base/mechanics/strategic.md"
            TACTICAL = "base/mechanics/tactical.md"

    class FACTIONS:
        BARONIAL_TROOPS = "factions/baronial_troops.md"
        BARONIES = "factions/baronies.md"
        CONGREGATION_OF_THE_METEORITE = "factions/congregation_of_the_meteorite.md"
        ELFS = "factions/elfs.md"
        GREENSKINS = "factions/greenskins.md"
        HUMANS = "factions/humans.md"
        MERCENARIES = "factions/mercenaries.md"

    class LORE:
        class BASIC:
            LOW = "lore/basic/low.md"
            MEDIUM = "lore/basic/medium.md"
            HIGH = "lore/basic/high.md"
            MAX = "lore/basic/max.md"

        class MAGIC:
            LOW = "lore/magic/low.md"
            MEDIUM = "lore/magic/medium.md"
            HIGH = "lore/magic/high.md"
            MAX = "lore/magic/max.md"

        class FACTIONS:
            class BARONIAL_TROOPS:
                LOW = "lore/factions/baronial_troops/low.md"
                MEDIUM = "lore/factions/baronial_troops/medium.md"
                HIGH = "lore/factions/baronial_troops/high.md"
                MAX = "lore/factions/baronial_troops/max.md"

            class CONGREGATION_OF_THE_METEORITE:
                LOW = "lore/factions/congregation_of_the_meteorite/low.md"
                MEDIUM = "lore/factions/congregation_of_the_meteorite/medium.md"
                HIGH = "lore/factions/congregation_of_the_meteorite/high.md"
                MAX = "lore/factions/congregation_of_the_meteorite/max.md"

            class ELFS:
                LOW = "lore/factions/elfs/low.md"
                MEDIUM = "lore/factions/elfs/medium.md"
                HIGH = "lore/factions/elfs/high.md"
                MAX = "lore/factions/elfs/max.md"

            class GREENSKINS:
                LOW = "lore/factions/greenskins/low.md"
                MEDIUM = "lore/factions/greenskins/medium.md"
                HIGH = "lore/factions/greenskins/high.md"
                MAX = "lore/factions/greenskins/max.md"

            class HUMANS:
                LOW = "lore/factions/humans/low.md"
                MEDIUM = "lore/factions/humans/medium.md"
                HIGH = "lore/factions/humans/high.md"
                MAX = "lore/factions/humans/max.md"

            class MERCENARIES:
                LOW = "lore/factions/mercenaries/low.md"
                MEDIUM = "lore/factions/mercenaries/medium.md"
                HIGH = "lore/factions/mercenaries/high.md"
                MAX = "lore/factions/mercenaries/max.md"

    class ROLES:
        ADVISOR = "roles/advisor/prompt.md"
        COMMANDER = "roles/commander/prompt.md"
        DIPLOMAT = "roles/diplomat/prompt.md"
        GAME_MASTER = "roles/game_master/prompt.md"
        GUNSMITH = "roles/gunsmith/prompt.md"
        HERO = "roles/hero/prompt.md"
        LORD = "roles/lord/prompt.md"
        VETERAN = "roles/veteran/prompt.md"

        class CHRONICLER:
            PROMPT = "roles/chronicler/prompt.md"
            RUMORS = "roles/chronicler/rumors.md"

            class WRITING:
                """Стиль записи летописца: у каждой расы свой носитель, почерк и тон."""

                NEUTRAL = "roles/chronicler/neutral/writing.md"
                BARONIAL_TROOPS = "roles/chronicler/baronial_troops/writing.md"
                CONGREGATION_OF_THE_METEORITE = (
                    "roles/chronicler/congregation_of_the_meteorite/writing.md"
                )
                ELFS = "roles/chronicler/elfs/writing.md"
                GREENSKINS = "roles/chronicler/greenskins/writing.md"
                HUMANS = "roles/chronicler/humans/writing.md"
                MERCENARIES = "roles/chronicler/mercenaries/writing.md"

    class TRAITS:
        class PSYCHOLOGICAL:
            CRAVEN = "traits/psychological/craven.md"
            CYNIC = "traits/psychological/cynic.md"
            FATALIST = "traits/psychological/fatalist.md"
            GREEDY = "traits/psychological/greedy.md"
            HEDONIST = "traits/psychological/hedonist.md"
            MEGALOMANIAC = "traits/psychological/megalomaniac.md"
            PARANOID = "traits/psychological/paranoid.md"
            PERFECTIONIST = "traits/psychological/perfectionist.md"
            PRAGMATIST = "traits/psychological/pragmatist.md"
            SADIST = "traits/psychological/sadist.md"
            VENGEFUL = "traits/psychological/vengeful.md"

        class STRATEGIC:
            AMBUSHER = "traits/strategic/ambusher.md"
            DEFENDER = "traits/strategic/defender.md"
            STRATEGIST = "traits/strategic/strategist.md"
            WARMONGER = "traits/strategic/warmonger.md"

        class TACTICAL:
            BUTCHER = "traits/tactical/butcher.md"
            DEFENDER = "traits/tactical/defender.md"

        class UNIQUE:
            class BACKGROUNDS:
                ARISTOCRAT = "traits/unique/backgrounds/aristocrat.md"
                BUREAUCRAT = "traits/unique/backgrounds/bureaucrat.md"
                DESERTER = "traits/unique/backgrounds/deserter.md"
                GLADIATOR = "traits/unique/backgrounds/gladiator.md"
                INQUISITOR = "traits/unique/backgrounds/inquisitor.md"

            class CURSED_GENES:
                CHAOS = "traits/unique/cursed_genes/chaos.md"
                DECAY = "traits/unique/cursed_genes/decay.md"
                DESICCATION = "traits/unique/cursed_genes/desiccation.md"
                HYPERPLASIA = "traits/unique/cursed_genes/hyperplasia.md"
                LYCANTHROPY = "traits/unique/cursed_genes/lycanthropy.md"
                MONOLITH = "traits/unique/cursed_genes/monolith.md"
                NECROSIS = "traits/unique/cursed_genes/necrosis.md"
                RESONANCE = "traits/unique/cursed_genes/resonance.md"

    class UNIQUE_PERSONALITIES:
        # Для простоты обращаемся к папкам, но можно детализировать до конкретных файлов
        class BARONIES:
            COMMANDERS = "unique_personalities/baronies/commanders/"
            HEROES = "unique_personalities/baronies/heroes/"
            LORDS = "unique_personalities/baronies/lords/"

        class CONGREGATION_OF_THE_METEORITE:
            COMMANDERS = "unique_personalities/congregation_of_the_meteorite/commanders/"
            HEROES = "unique_personalities/congregation_of_the_meteorite/heroes/"
            LORDS = "unique_personalities/congregation_of_the_meteorite/lords/"

        class ELFS:
            COMMANDERS = "unique_personalities/elfs/commanders/"
            HEROES = "unique_personalities/elfs/heroes/"
            LORDS = "unique_personalities/elfs/lords/"

        class GREENSKINS:
            COMMANDERS = "unique_personalities/greenskins/commanders/"
            HEROES = "unique_personalities/greenskins/heroes/"
            LORDS = "unique_personalities/greenskins/lords/"

        class HUMANS:
            COMMANDERS = "unique_personalities/humans/commanders/"
            HEROES = "unique_personalities/humans/heroes/"
            LORDS = "unique_personalities/humans/lords/"

        class MERCENARIES:
            HEROES = "unique_personalities/mercenaries/heroes/"


def get_faction_prompt_path(race: FactionRace) -> str:
    """Удобный маппинг расы фракции на её лорный файл-описание."""
    mapping = {
        FactionRace.HUMANS: PromptCatalog.FACTIONS.HUMANS,
        FactionRace.GREENSKINS: PromptCatalog.FACTIONS.GREENSKINS,
        FactionRace.ELFS: PromptCatalog.FACTIONS.ELFS,
        FactionRace.BARONIAL_TROOPS: PromptCatalog.FACTIONS.BARONIAL_TROOPS,
        FactionRace.CONGREGATION_OF_THE_METEORITE: PromptCatalog.FACTIONS.CONGREGATION_OF_THE_METEORITE,
        FactionRace.MERCENARIES: PromptCatalog.FACTIONS.MERCENARIES,
    }
    return mapping[race]


def get_chronicler_writing_path(race: Optional[FactionRace]) -> str:
    """
    Стилистический файл летописца для расы фракции.
    Без фракции летопись пишется нейтрально: так бывает для боев наемников
    и стычек на ничьей земле, где нет своего писаря.
    """
    if race is None:
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
