"""
Фасад.
Точка входа для остальных модулей.

Пограничный город живет две жизни, и обе идут через этот фасад: сначала
фракция основывает поселение, растит его и выкупает ему земли, а потом
чужая армия берет его штурмом и решает, сжечь, разграбить, занять или
пройти мимо.

Состояния фасад не держит: и города, и начатые над ними операции лежат в
самом WorldState. Поэтому один и тот же фасад одинаково годится и для
приказов игрока, и для шага глобального такта.
"""

from random import Random
from typing import Optional

from src.back.l01_domain.factions.constants import BorderTownResolutionType
from src.back.l01_domain.factions.models.border_town import (
    BorderTown,
    BorderTownOperation,
)
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.reports import BorderTownResolutionStepReport
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.settlements.border_towns.foundation import (
    BorderTownFoundationService,
)
from src.back.l02_services.mechanics.settlements.border_towns.resolution import (
    BorderTownResolutionService,
)


class SettlementsFacade:
    """
    Оркестрирует рост пограничных городов и операции над взятыми штурмом.
    """

    def __init__(
        self,
        event_bus: Optional[EventBusProtocol] = None,
        rng: Optional[Random] = None,
        foundation_service: Optional[BorderTownFoundationService] = None,
        resolution_service: Optional[BorderTownResolutionService] = None,
    ) -> None:
        self._foundation = foundation_service or BorderTownFoundationService(
            event_bus=event_bus
        )
        # Жребий нужен только разграблению - какие постройки в нем сгорят
        self._resolution = resolution_service or BorderTownResolutionService(
            event_bus=event_bus, rng=rng
        )

    # ==================================================================
    # РОСТ ГОРОДА
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
        """
        return await self._foundation.found_border_town(
            world_state=world_state,
            faction_id=faction_id,
            target_hex=target_hex,
            name=name,
        )

    async def upgrade_border_town(
        self,
        world_state: WorldState,
        faction_id: str,
        town_id: str,
    ) -> BorderTown:
        """
        Поднимает город на уровень выше: +1 строительный слот внутри стен.
        """
        return await self._foundation.upgrade_border_town(
            world_state=world_state,
            faction_id=faction_id,
            town_id=town_id,
        )

    async def claim_border_land(
        self,
        world_state: WorldState,
        faction_id: str,
        town_id: str,
        target_hex: HexCoordinates,
    ) -> BorderTown:
        """
        Выкупает смежный с городом гекс в союзные земли фракции.
        """
        return await self._foundation.claim_border_land(
            world_state=world_state,
            faction_id=faction_id,
            town_id=town_id,
            target_hex=target_hex,
        )

    def list_border_towns(
        self, world_state: WorldState, faction_id: str
    ) -> list[BorderTown]:
        """Все пограничные города фракции для окна управления державой."""
        return self._foundation.list_border_towns(
            world_state=world_state, faction_id=faction_id
        )

    # ==================================================================
    # СУДЬБА ПОБЕЖДЕННОГО ГОРОДА
    # ==================================================================

    async def initiate_town_resolution(
        self,
        world_state: WorldState,
        town_id: str,
        army_id: str,
        resolution_type: BorderTownResolutionType,
    ) -> Optional[BorderTownOperation]:
        """
        Начинает то, что победитель решил сделать с побежденным городом.

        Возвращает заведенную операцию либо None, если победитель прошел
        мимо: за пропуском ждать нечего.
        """
        return await self._resolution.initiate_town_resolution(
            world_state=world_state,
            town_id=town_id,
            army_id=army_id,
            resolution_type=resolution_type,
        )

    async def process_town_resolutions(
        self, world_state: WorldState
    ) -> BorderTownResolutionStepReport:
        """
        Шаг глобального такта: прожигает по такту у начатых операций и
        доводит до конца те, у которых отсчет дошел до нуля.
        """
        return await self._resolution.process_town_resolutions(world_state)

    def get_town_operation(
        self, world_state: WorldState, town_id: str
    ) -> Optional[BorderTownOperation]:
        """
        Прогресс операции над городом для окна осады. None - город не разоряют.
        """
        return self._resolution.get_town_operation(
            world_state=world_state, town_id=town_id
        )
