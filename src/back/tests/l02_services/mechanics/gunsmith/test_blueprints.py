"""
Тесты сборки чертежа: превращение свободного ответа нейросети
в валидный доменный Equipment.

Модель отвечает строками ("sword", "plate"), а домен работает с Enum-ами -
разбор этих строк и подстановка заглушек вместо пропусков живут здесь.
"""

import pytest
from pydantic import ValidationError

from src.back.l01_domain.army.constants import (
    AccessoryCategory,
    ArmorCategory,
    EquipmentSlot,
    EquipmentTag,
    WeaponCategory,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.l01_domain.exceptions.army import InvalidEquipmentSlotError
from src.back.l02_services.mechanics.gunsmith.blueprints import BlueprintRegistry
from src.back.l02_services.mechanics.gunsmith.crafting import LLMGunsmithResponse

STATS = EquipmentStats(damage=12.0, armor_piercing=3.0)


def make_response(**overrides) -> LLMGunsmithResponse:
    """Одобренный ответ мастера с разумными значениями по умолчанию."""
    data = {
        "is_approved": True,
        "master_reply": "Сделаю, мой лорд.",
        "name": "Алебарда с аркебузой",
        "lore": "Древко, к которому прикручен однозарядный ствол.",
        "tier": 3,
        "slot": EquipmentSlot.WEAPON,
        "category_name": "polearm",
        "tags": [EquipmentTag.TWO_HANDED, EquipmentTag.BLACKPOWDER],
    }
    data.update(overrides)
    return LLMGunsmithResponse(**data)


def construct(response: LLMGunsmithResponse, stats: EquipmentStats = STATS):
    return BlueprintRegistry.construct_draft(response, stats, cost_gold=31.2, cost_material=73.1)


# ====================================================
# Перенос полей ответа в предмет
# ====================================================


class TestDraftAssembly:
    def test_response_fields_reach_the_item(self):
        draft = construct(make_response())

        assert draft.name == "Алебарда с аркебузой"
        assert draft.lore == "Древко, к которому прикручен однозарядный ствол."
        assert draft.tier == 3
        assert draft.slot == EquipmentSlot.WEAPON
        assert draft.stats == STATS
        assert draft.cost_gold == 31.2
        assert draft.cost_material == 73.1

    def test_draft_is_marked_as_custom(self):
        """Предметы мастерской должны отличаться от серийной геймдаты."""
        assert construct(make_response()).is_custom is True

    def test_id_is_prefixed_and_unique(self):
        first = construct(make_response())
        second = construct(make_response())

        assert first.id.startswith("eq_custom_")
        assert first.id != second.id

    def test_tags_become_a_set(self):
        draft = construct(make_response())

        assert draft.tags == {EquipmentTag.TWO_HANDED, EquipmentTag.BLACKPOWDER}
        assert draft.is_two_handed is True
        assert draft.is_firearm is True

    def test_special_rules_are_carried_over(self):
        draft = construct(
            make_response(special_rules="Развертывание: 50 проникающего урона в гекс.")
        )

        assert draft.special_rules == "Развертывание: 50 проникающего урона в гекс."


# ====================================================
# Разбор категории
# ====================================================


class TestCategoryResolution:
    @pytest.mark.parametrize(
        "slot, category_name, expected",
        [
            (EquipmentSlot.WEAPON, "sword", WeaponCategory.SWORD),
            (EquipmentSlot.WEAPON, "firearm", WeaponCategory.FIREARM),
            (EquipmentSlot.ARMOR, "plate", ArmorCategory.PLATE),
            (EquipmentSlot.ARMOR, "brigandine", ArmorCategory.BRIGANDINE),
            (EquipmentSlot.ACCESSORY, "shield", AccessoryCategory.SHIELD),
            (EquipmentSlot.ACCESSORY, "trap", AccessoryCategory.TRAP),
        ],
    )
    def test_known_category_names_map_to_enums(self, slot, category_name, expected):
        draft = construct(make_response(slot=slot, category_name=category_name, tags=[]))

        assert draft.category == expected

    def test_category_name_is_case_insensitive(self):
        """Модель вольна кричать капслоком - разбору это мешать не должно."""
        draft = construct(make_response(category_name="POLEARM"))

        assert draft.category == WeaponCategory.POLEARM

    def test_unknown_category_leaves_the_item_uncategorized(self):
        """
        Мастер может выдумать категорию, которой в домене нет. Это не повод
        ронять чертеж: предмет просто остается без подтипа.
        """
        draft = construct(make_response(category_name="halberd_gun"))

        assert draft.category is None

    def test_missing_category_is_allowed(self):
        draft = construct(make_response(category_name=None))

        assert draft.category is None

    def test_category_from_a_foreign_slot_is_rejected_by_the_domain(self):
        """
        Модель назвала слот броней, а категорию - мечом. Домен такую карточку
        не принимает, и чертеж не собирается.
        """
        response = make_response(
            slot=EquipmentSlot.ARMOR, category_name="sword", tags=[]
        )

        with pytest.raises(InvalidEquipmentSlotError):
            construct(response)


# ====================================================
# Пропуски в ответе модели
# ====================================================


class TestFallbacks:
    def test_missing_name_gets_a_placeholder(self):
        assert construct(make_response(name=None)).name == "Безымянный прототип"

    def test_missing_lore_gets_a_placeholder(self):
        draft = construct(make_response(lore=None))

        assert draft.lore == "Собрано в мастерской по индивидуальному заказу."

    def test_blank_name_gets_a_placeholder(self):
        """Пустая строка для домена так же непригодна, как и None."""
        assert construct(make_response(name="")).name == "Безымянный прототип"

    def test_missing_tier_falls_back_to_the_first(self):
        assert construct(make_response(tier=None)).tier == 1

    def test_slot_is_mandatory(self):
        """
        Слот подставить нечем: без него непонятно, куда предмет надевать.
        Ответ модели без слота до карточки не доходит.
        """
        with pytest.raises(ValidationError):
            construct(make_response(slot=None))
