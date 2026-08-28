"""
Реестр легендарных полководцев фракции эльфов.

Лор личностей - docs/factions/elfs/commanders.md, их системные промпты -
l03_infrastructure/llm/prompt/unique_personalities/elfs/commanders/.
"""

from typing import Any

from src.back.gamedata.elfs.common import ElfsCommanderId
from src.back.l01_domain.army.models.characters.commanders import CommanderCharacteristics
from src.back.l01_domain.common import FactionRace

_RACE = FactionRace.ELFS
_PROMPTS = "unique_personalities.elfs.commanders"

COMMANDERS_LIST: dict[str, dict[str, Any]] = {
    ElfsCommanderId.IRIEL.value: {
        "id": ElfsCommanderId.IRIEL.value,
        "race": _RACE,
        "name": "Ириэль",
        "role_title": "Командир штурмовых когорт",
        "archetype": "Танцор бури",
        "prompt_ref": f"{_PROMPTS}.Iriel",
        "trait_ids": ["hedonist", "resonance", "gladiator"],
        "characteristics": CommanderCharacteristics(
            authority=60,
            tactical_acumen=70,
            resilience=35,  # В зажатом строю ее когорты несут страшные потери
            cunning=65,
        ),
        "lore_description": (
            "Ведет Танцующих-с-клинками, охраняющих подступы к Парящим храмам. Использует "
            "антигравитационные стабилизаторы и резонитовые глефы, двигаясь по полю боя с "
            "недостижимой для людей скоростью - но только пока у нее есть простор для маневра."
        ),
    },
    ElfsCommanderId.SILVIAN.value: {
        "id": ElfsCommanderId.SILVIAN.value,
        "race": _RACE,
        "name": "Сильвиан",
        "role_title": "Верховный жрец резонита",
        "archetype": "Иллюзионист",
        "prompt_ref": f"{_PROMPTS}.Silvian",
        "trait_ids": ["paranoid", "perfectionist", "resonance"],
        "characteristics": CommanderCharacteristics(
            authority=45,
            tactical_acumen=75,
            resilience=30,
            cunning=90,  # Ложные маркеры на карте и фантомные отряды в бою
        ),
        "lore_description": (
            "Специалист по преломлению световых волн и пространственным голограммам. "
            "Побеждает врага до того, как тот обнажит клинки: на карте генерирует ложные "
            "маркеры, в бою - фантомные копии отрядов. Уязвим к пороховому смогу."
        ),
    },
    ElfsCommanderId.KAELIN.value: {
        "id": ElfsCommanderId.KAELIN.value,
        "race": _RACE,
        "name": "Каэлин",
        "role_title": "Страж переправ",
        "archetype": "Непоколебимый часовой",
        "prompt_ref": f"{_PROMPTS}.Kaelin",
        "trait_ids": ["monolith", "fatalist", "perfectionist"],
        "characteristics": CommanderCharacteristics(
            authority=65,
            tactical_acumen=55,
            resilience=95,
            cunning=20,
        ),
        "lore_description": (
            "Древнейший эльфийский полководец: Изъян монолита перевел более восьмидесяти "
            "процентов его тела в светящийся изумрудный минерал. Говорит медленным скрипучим "
            "эхом и ведет в бой Кристальных часовых - единственную глухую оборону эльфов."
        ),
    },
}
