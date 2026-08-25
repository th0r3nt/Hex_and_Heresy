"""
Статический каталог базовых промптов и модуль динамического обнаружения файлов.
"""

from pathlib import Path
from typing import Optional

from src.back.l01_domain.common import FactionRace


class PromptCatalog:
    """Корневой каталог статических markdown-файлов ядра системы промптов."""

    class BASE:
        PERSONA = "base/persona.md"

        class MECHANICS:
            ECONOMY = "base/mechanics/economy.md"
            STRATEGIC = "base/mechanics/strategic.md"
            TACTICAL = "base/mechanics/tactical.md"

    class FACTIONS:
        BARONIAL_TROOPS = "factions/baronial_troops.md"
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
                NEUTRAL = "roles/chronicler/neutral/writing.md"
                BARONIAL_TROOPS = "roles/chronicler/baronial_troops/writing.md"
                CONGREGATION_OF_THE_METEORITE = (
                    "roles/chronicler/congregation_of_the_meteorite/writing.md"
                )
                ELFS = "roles/chronicler/elfs/writing.md"
                GREENSKINS = "roles/chronicler/greenskins/writing.md"
                HUMANS = "roles/chronicler/humans/writing.md"
                MERCENARIES = "roles/chronicler/mercenaries/writing.md"


class PromptDiscovery:
    """
    Инструмент динамического обнаружения файлов промптов на диске.
    Обеспечивает сбор коллекций трейтов, личностей и лора для мастера игры.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = base_dir or Path(__file__).parent

    def get_traits(self, category: Optional[str] = None) -> list[str]:
        """
        Возвращает относительные пути ко всем markdown-файлам черт характера.
        Если указана категория (например, 'psychological', 'unique/backgrounds',
        'unique/cursed_genes'), поиск ограничивается ею.
        """

        target_dir = self._base_dir / "traits"
        if category:
            target_dir = target_dir / category

        return self._collect_relative_md_files(target_dir)

    def get_unique_personalities(
        self,
        race: Optional[FactionRace] = None,
        role: Optional[str] = None,
    ) -> list[str]:
        """
        Возвращает относительные пути к файлам уникальных личностей.
        Поддерживает фильтрацию по расе и роли (commanders, heroes, lords).
        """

        target_dir = self._base_dir / "unique_personalities"
        if race:
            target_dir = target_dir / race.value
        if role:
            target_dir = target_dir / role

        return self._collect_relative_md_files(target_dir)

    def get_all_md_files(self, sub_dir: str = "") -> list[str]:
        """
        Рекурсивно возвращает относительные пути ко всем markdown-файлам
        в заданной поддиректории.
        """

        target_dir = self._base_dir / sub_dir if sub_dir else self._base_dir
        return self._collect_relative_md_files(target_dir)

    def _collect_relative_md_files(self, directory: Path) -> list[str]:
        if not directory.exists() or not directory.is_dir():
            return []

        results: list[str] = []
        for file_path in sorted(directory.rglob("*.md")):
            if file_path.is_file():
                rel_path = file_path.relative_to(self._base_dir).as_posix()
                results.append(rel_path)
        return results


def get_faction_prompt_path(race: FactionRace) -> str:
    """Сопоставляет расу фракции с ее файлом описания."""
    mapping = {
        FactionRace.HUMANS: PromptCatalog.FACTIONS.HUMANS,
        FactionRace.GREENSKINS: PromptCatalog.FACTIONS.GREENSKINS,
        FactionRace.ELFS: PromptCatalog.FACTIONS.ELFS,
        FactionRace.BARONIAL_TROOPS: PromptCatalog.FACTIONS.BARONIAL_TROOPS,
        FactionRace.CONGREGATION_OF_THE_METEORITE: (
            PromptCatalog.FACTIONS.CONGREGATION_OF_THE_METEORITE
        ),
        FactionRace.MERCENARIES: PromptCatalog.FACTIONS.MERCENARIES,
    }
    return mapping[race]


def get_chronicler_writing_path(race: Optional[FactionRace]) -> str:
    """
    Возвращает путь к файлу стиля записи летописца для конкретной расы.
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
