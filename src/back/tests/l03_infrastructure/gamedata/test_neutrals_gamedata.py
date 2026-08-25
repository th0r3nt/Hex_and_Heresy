"""
Интеграционные тесты статической геймдаты нейтральных сил:
проверка регистрации юнитов, врожденной экипировки и корректности сборки отрядов по ростеру.
"""

from src.back.gamedata.neutrals.common import (
    NeutralsArmorId,
    NeutralsRosterId,
    NeutralsUnitId,
    NeutralsWeaponId,
)
from src.back.gamedata.neutrals.roster.roster import ROSTER_LIST
from src.back.l01_domain.army.constants import (
    ArmorCategory,
    EquipmentSlot,
    WeaponCategory,
)
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.common import FactionRace
from src.back.l03_infrastructure.gamedata.loader import build_static_registry


class TestNeutralsGameData:
    def test_static_registry_loads_all_neutral_archetypes(self):
        """Проверяет, что все 4 базовых архетипа нейтралов присутствуют в общем реестре."""
        registry = build_static_registry()

        rebels = registry.get_unit_archetype(NeutralsUnitId.REBELS_MOB_00.value)
        assert rebels is not None
        assert rebels.name == "Толпа бунтовщиков"
        assert rebels.race == FactionRace.NEUTRALS
        assert rebels.tier == 0
        assert rebels.default_unit_count == 120

        marauders = registry.get_unit_archetype(NeutralsUnitId.MARAUDERS_01.value)
        assert marauders is not None
        assert marauders.name == "Бродячие мародеры"
        assert marauders.tier == 1

        beasts = registry.get_unit_archetype(NeutralsUnitId.WILD_BEASTS_01.value)
        assert beasts is not None
        assert beasts.name == "Одичавшие звери"
        assert beasts.base_stats.base_speed == 3.5

        deserters = registry.get_unit_archetype(NeutralsUnitId.DESERTER_GANG_02.value)
        assert deserters is not None
        assert deserters.name == "Шайка дезертиров"
        assert deserters.tier == 2

    def test_neutral_innate_equipment_registered(self):
        """Проверяет корректность характеристик и слотов естественного оружия и брони зверей."""
        registry = build_static_registry()

        fangs = registry.get_equipment(NeutralsWeaponId.BEAST_FANGS_01.value)
        assert fangs is not None
        assert fangs.slot == EquipmentSlot.WEAPON
        assert fangs.category == WeaponCategory.NATURAL
        assert fangs.stats.damage == 8.0

        hide = registry.get_equipment(NeutralsArmorId.BEAST_HIDE_01.value)
        assert hide is not None
        assert hide.slot == EquipmentSlot.ARMOR
        assert hide.category == ArmorCategory.LEATHER
        assert hide.stats.armor_bonus == 2.0

    def test_all_neutral_rosters_assemble_valid_squads(self):
        """
        Проверяет, что каждый рецепт найма нейтралов успешно находит свои компоненты
        (включая кросс-фракционную экипировку) и собирает валидный боевой отряд Squad.
        """
        registry = build_static_registry()

        for roster_id, entry_data in ROSTER_LIST.items():
            archetype = registry.get_unit_archetype(entry_data["unit_archetype_id"])
            assert (
                archetype is not None
            ), f"Архетип {entry_data['unit_archetype_id']} не найден"

            weapon = (
                registry.get_equipment(entry_data["weapon_id"])
                if entry_data.get("weapon_id")
                else None
            )
            if entry_data.get("weapon_id"):
                assert weapon is not None, f"Оружие {entry_data['weapon_id']} не найдено"

            armor = (
                registry.get_equipment(entry_data["armor_id"])
                if entry_data.get("armor_id")
                else None
            )
            if entry_data.get("armor_id"):
                assert armor is not None, f"Броня {entry_data['armor_id']} не найдена"

            accessory = (
                registry.get_equipment(entry_data["accessory_id"])
                if entry_data.get("accessory_id")
                else None
            )
            if entry_data.get("accessory_id"):
                assert (
                    accessory is not None
                ), f"Аксессуар {entry_data['accessory_id']} не найден"

            squad = Squad.create_new(
                archetype=archetype,
                weapon=weapon,
                armor=armor,
                accessory=accessory,
            )

            assert squad.state.unit_count == archetype.default_unit_count
            assert squad.total_attack_damage > 0.0
            assert squad.total_effective_speed > 0.0

    def test_deserter_gang_cross_faction_equipment(self):
        """Проверяет корректность переиспользования имперской стали шайкой дезертиров."""
        registry = build_static_registry()
        deserter_roster = ROSTER_LIST[NeutralsRosterId.ROSTER_DESERTERS.value]

        archetype = registry.get_unit_archetype(deserter_roster["unit_archetype_id"])
        weapon = registry.get_equipment(deserter_roster["weapon_id"])
        armor = registry.get_equipment(deserter_roster["armor_id"])

        squad = Squad.create_new(archetype=archetype, weapon=weapon, armor=armor)

        # Алебарда (12) + базовая броня (1) + кираса (6)
        assert squad.total_attack_damage == 12.0
        assert squad.total_effective_armor == 7.0
        assert squad.display_name == "Шайка дезертиров"
