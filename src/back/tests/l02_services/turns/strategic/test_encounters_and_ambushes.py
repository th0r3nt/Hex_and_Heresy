"""
Тесты сложных боевых столкновений нескольких армий на одном гексе,
асимметрии засад при форсированном марше.
"""

import pytest

from src.back.l01_domain.army.constants import StrategicMovementPace
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord, LordArchetype, LordTrait
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.movement import StrategicMovementService


@pytest.fixture
def elf_faction() -> Faction:
    lord = Lord(
        faction_id="elfs",
        name="Лиандрис",
        title="Стеклянный демиург",
        archetype=LordArchetype(id="arch_elf", name="Изоляционист", description="..."),
        trait=LordTrait(id="trait_elf", name="Холодный", text_fragment="..."),
    )
    hq = Headquarters(faction_id="elfs", name="Цитадель Эфирного Зенита")
    return Faction(
        id="elfs",
        race=FactionRace.ELFS,
        name="Эльфы Чистого Скола",
        is_player_controlled=False,
        lord=lord,
        headquarters=hq,
    )


class TestStrategicEncountersAndAmbushes:
    @pytest.mark.asyncio
    async def test_three_hostile_factions_on_same_hex_create_pairwise_encounters(
        self, human_faction, orc_faction, elf_faction, fake_bus
    ):
        neutral_hex = HexCoordinates.from_axial(3, 3)

        army_human = StrategicArmy(
            faction_id=human_faction.id,
            current_hex=neutral_hex,
            pace=StrategicMovementPace.MARCH,
        )
        army_orc = StrategicArmy(
            faction_id=orc_faction.id,
            current_hex=neutral_hex,
            pace=StrategicMovementPace.MARCH,
        )
        army_elf = StrategicArmy(
            faction_id=elf_faction.id,
            current_hex=neutral_hex,
            pace=StrategicMovementPace.MARCH,
        )

        world = WorldState()
        world.neutral_hexes.append(neutral_hex)
        world.add_faction(human_faction)
        world.add_faction(orc_faction)
        world.add_faction(elf_faction)
        world.add_army(army_human)
        world.add_army(army_orc)
        world.add_army(army_elf)

        service = StrategicMovementService(event_bus=fake_bus)
        report = await service.process_movements_and_encounters(world)

        # 3 разные фракции создают ровно 3 попарных столкновения: (Human, Orc), (Human, Elf), (Orc, Elf)
        assert len(report.encounters) == 3
        pairs = {
            (min(e.faction_a_id, e.faction_b_id), max(e.faction_a_id, e.faction_b_id))
            for e in report.encounters
        }
        assert ("greenskins", "humans") in pairs
        assert ("elfs", "humans") in pairs
        assert ("elfs", "greenskins") in pairs

    @pytest.mark.asyncio
    async def test_same_faction_armies_do_not_fight(self, human_faction, fake_bus):
        neutral_hex = HexCoordinates.from_axial(1, 1)

        army_1 = StrategicArmy(faction_id=human_faction.id, current_hex=neutral_hex)
        army_2 = StrategicArmy(faction_id=human_faction.id, current_hex=neutral_hex)

        world = WorldState()
        world.neutral_hexes.append(neutral_hex)
        world.add_faction(human_faction)
        world.add_army(army_1)
        world.add_army(army_2)

        service = StrategicMovementService(event_bus=fake_bus)
        report = await service.process_movements_and_encounters(world)

        assert len(report.encounters) == 0

    @pytest.mark.asyncio
    async def test_ambush_triggered_when_one_army_uses_forced_march(
        self, human_faction, orc_faction, fake_bus
    ):
        neutral_hex = HexCoordinates.from_axial(4, 4)

        # Человеческая армия бежит на форсированном марше (уязвимость к засаде)
        army_human = StrategicArmy(
            faction_id=human_faction.id,
            current_hex=neutral_hex,
            pace=StrategicMovementPace.FORCED,
        )
        # Орки двигаются осторожным шагом в режиме разведки
        army_orc = StrategicArmy(
            faction_id=orc_faction.id,
            current_hex=neutral_hex,
            pace=StrategicMovementPace.CAUTIOUS,
        )

        world = WorldState()
        world.neutral_hexes.append(neutral_hex)
        world.add_faction(human_faction)
        world.add_faction(orc_faction)
        world.add_army(army_human)
        world.add_army(army_orc)

        service = StrategicMovementService(event_bus=fake_bus)
        report = await service.process_movements_and_encounters(world)

        assert len(report.encounters) == 1
        encounter = report.encounters[0]
        assert encounter.is_ambush is True
        assert encounter.ambusher_army_id == army_orc.id
