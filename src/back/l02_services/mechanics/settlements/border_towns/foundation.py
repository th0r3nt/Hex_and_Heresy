"""
Рост пограничного города: основание поселения на свободном гексе, подъем
его уровня и выкуп смежных земель.

Разделение ответственности здесь такое же, как у гарнизонов: все, что
касается самого города (потолок уровня, смежность и лимит земель), проверяет
агрегат BorderTown, а сервис отвечает за карту и казну - свободен ли гекс,
хватает ли ресурсов и что после этого меняется в мире.

Порядок операций в каждом приказе один и тот же: сначала все проверки,
потом списание казны и только затем изменение мира. Иначе отказ на середине
оставил бы фракцию без денег и без города.
"""

from typing import Optional

from src.back.l01_domain.factions.constants import (
    BORDER_TOWN_FOUNDATION_COST,
    BORDER_TOWN_LAND_CLAIM_COST,
    border_town_upgrade_cost,
)
from src.back.l01_domain.factions.models.border_town import BorderTown
from src.back.l01_domain.factions.models.buildings import RegionalHall
from src.back.l01_domain.maps.models.strategic import HexCoordinates, hex_zone_id
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.settlements.border_towns.common import (
    assert_hex_is_free,
    occupy_hex,
    require_faction,
    require_town,
)
from src.back.utils.event.registry import GameEvents


class BorderTownFoundationService:
    """
    Исполняет приказы игрока по развитию пограничных городов.
    """

    def __init__(self, event_bus: Optional[EventBusProtocol] = None) -> None:
        self._event_bus = event_bus

    # ==================================================================
    # ОСНОВАНИЕ ГОРОДА
    # ==================================================================

    async def found_border_town(
        self,
        world_state: WorldState,
        faction_id: str,
        target_hex: HexCoordinates,
        name: str,
    ) -> BorderTown:
        """
        Ставит новое поселение на свободный гекс карты.

        Город встает сразу на первом уровне с двумя строительными слотами и
        без единой союзной земли: их предстоит выкупать отдельно.
        """
        faction = require_faction(world_state, faction_id)
        assert_hex_is_free(world_state, faction_id, target_hex)

        faction.spend_all(BORDER_TOWN_FOUNDATION_COST)

        town = BorderTown(
            faction_id=faction.id,
            name=name,
            center_hex=target_hex,
        )
        town.register_investment(BORDER_TOWN_FOUNDATION_COST)

        faction.add_border_town(town)
        faction.gain_zone(town.zone_id)
        occupy_hex(world_state, target_hex)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Economy.BORDER_TOWN_FOUNDED,
                faction_id=faction.id,
                town_id=town.id,
                town_name=town.name,
                zone_id=town.zone_id,
                hex=target_hex.model_dump(),
            )

        return town

    # ==================================================================
    # РОСТ ГОРОДА
    # ==================================================================

    async def upgrade_border_town(
        self,
        world_state: WorldState,
        faction_id: str,
        town_id: str,
    ) -> BorderTown:
        """
        Поднимает город на уровень выше: +1 строительный слот внутри стен
        и больше ополчения в его гарнизоне со следующего такта.
        """
        faction = require_faction(world_state, faction_id)
        town = require_town(faction, town_id)

        town.assert_can_upgrade()
        cost = border_town_upgrade_cost(town.level + 1)

        faction.spend_all(cost)
        town.upgrade()
        town.register_investment(cost)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Economy.BORDER_TOWN_UPGRADED,
                faction_id=faction.id,
                town_id=town.id,
                town_name=town.name,
                level=town.level,
                building_slots=town.building_slots,
            )

        return town

    # ==================================================================
    # ЗАСЕЛЕНИЕ СМЕЖНЫХ ЗЕМЕЛЬ
    # ==================================================================

    async def claim_border_land(
        self,
        world_state: WorldState,
        faction_id: str,
        town_id: str,
        target_hex: HexCoordinates,
    ) -> BorderTown:
        """
        Выкупает смежный с городом гекс в союзные земли фракции.

        На купленной земле сразу встает ратуша: с этого такта земля дает
        строительный слот, платит подушный сбор и поднимает свое ополчение.
        """
        faction = require_faction(world_state, faction_id)
        town = require_town(faction, town_id)

        assert_hex_is_free(world_state, faction_id, target_hex)
        town.assert_can_claim_land(target_hex)

        faction.spend_all(BORDER_TOWN_LAND_CLAIM_COST)

        town.claim_land(target_hex)
        town.register_investment(BORDER_TOWN_LAND_CLAIM_COST)

        zone_id = hex_zone_id(target_hex)
        faction.gain_zone(zone_id)
        faction.add_regional_hall(
            RegionalHall(
                faction_id=faction.id,
                zone_id=zone_id,
                name=f"Ратуша поселения {town.name}",
            )
        )
        occupy_hex(world_state, target_hex)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Economy.BORDER_TOWN_LAND_CLAIMED,
                faction_id=faction.id,
                town_id=town.id,
                town_name=town.name,
                zone_id=zone_id,
                hex=target_hex.model_dump(),
                free_land_slots=town.free_land_slots,
            )

        return town

    # ==================================================================
    # ЧТЕНИЕ
    # ==================================================================

    @staticmethod
    def list_border_towns(
        world_state: WorldState, faction_id: str
    ) -> list[BorderTown]:
        """Все пограничные города фракции для окна управления державой."""
        return list(require_faction(world_state, faction_id).border_towns)
