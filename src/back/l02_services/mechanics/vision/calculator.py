"""
Расчет прямого обзора фракции на глобальной карте.

Сервис чисто вычислительный: собирает источники обзора, разворачивает от
каждого спираль его радиуса и складывает результат в одно множество гексов.
Мир он при этом не трогает - записать посчитанное в маску тумана и обновить
историю открытых гексов это забота фасада.
"""

from dataclasses import dataclass

from src.back.l01_domain.factions.constants import DiplomaticStance
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.maps.constants import (
    VISION_RADIUS_AMBASSADOR,
    VISION_RADIUS_BASE,
    VISION_RADIUS_BORDER_TOWN,
    VISION_RADIUS_REGIONAL_HALL,
)
from src.back.l01_domain.maps.models.strategic import (
    HexCoordinates,
    hex_from_zone_id,
    hex_spiral,
)
from src.back.l01_domain.world.models.state import WorldState


@dataclass(frozen=True)
class VisionSource:
    """
    Одна "пара глаз" фракции: гекс, с которого смотрят, и дальность обзора.

    Отдельный тип нужен, чтобы отладка и тесты видели, кто именно вскрыл
    сектор карты - цитадель, вышка или ушедший в рейд разъезд.
    """

    origin: HexCoordinates
    radius: int
    kind: str


class VisionCalculator:
    """
    Считает, какие гексы фракция просматривает прямо сейчас.
    """

    # ==================================================================
    # ИТОГОВЫЙ ОБЗОР
    # ==================================================================

    def calculate_visible_hexes(
        self, world_state: WorldState, faction_id: str
    ) -> set[HexCoordinates]:
        """
        Множество гексов под прямым обзором фракции на текущий такт.

        Обзор союзника по пакту об обмене разведданными вливается сюда же:
        для игрока разницы нет, чьи именно глаза вскрыли сектор.
        """
        visible: set[HexCoordinates] = set()

        for source in self.collect_sources(world_state, faction_id):
            visible.update(hex_spiral(source.origin, source.radius))

        visible.update(self._collect_shared_intelligence(world_state, faction_id))

        return visible

    # ==================================================================
    # ИСТОЧНИКИ ОБЗОРА
    # ==================================================================

    def collect_sources(
        self, world_state: WorldState, faction_id: str
    ) -> list[VisionSource]:
        """
        Все собственные источники обзора фракции: застройка и все, что ходит
        по карте под ее флагом.
        """
        faction = world_state.get_faction(faction_id)
        if faction is None:
            return []

        sources: list[VisionSource] = []
        sources.extend(self._collect_settlement_sources(faction))
        sources.extend(self._collect_building_sources(faction))
        sources.extend(self._collect_mobile_sources(world_state, faction_id))
        return sources

    @staticmethod
    def _collect_settlement_sources(faction: Faction) -> list[VisionSource]:
        """
        Обзор с застройки: цитадель, пограничные города и ратуши союзных земель.

        Земли города уже лежат в regional_halls общим списком, поэтому
        отдельно по claimed_hexes проходить не нужно - иначе один и тот же
        гекс попал бы в источники дважды.
        """
        sources: list[VisionSource] = []

        if faction.capital_hex is not None and not faction.headquarters.is_destroyed:
            sources.append(
                VisionSource(
                    origin=faction.capital_hex,
                    radius=VISION_RADIUS_BASE,
                    kind="headquarters",
                )
            )

        for town in faction.border_towns:
            sources.append(
                VisionSource(
                    origin=town.center_hex,
                    radius=VISION_RADIUS_BORDER_TOWN,
                    kind="border_town",
                )
            )

        for hall in faction.regional_halls:
            sources.append(
                VisionSource(
                    origin=hex_from_zone_id(hall.zone_id),
                    radius=VISION_RADIUS_REGIONAL_HALL,
                    kind="regional_hall",
                )
            )

        return sources

    @staticmethod
    def _collect_building_sources(faction: Faction) -> list[VisionSource]:
        """
        Обзор с наблюдательной застройки: сторожевых вышек и обсерваторий.

        Здание само объявляет свой радиус в геймданных, поэтому список
        "смотрящих" построек нигде не захардкожен: достаточно проставить
        vision_radius_hexes новому зданию в каталоге.
        """
        sources: list[VisionSource] = []

        for constructed in faction.buildings:
            radius = constructed.vision_radius_hexes
            if radius <= 0:
                continue
            sources.append(
                VisionSource(
                    origin=hex_from_zone_id(constructed.zone_id),
                    radius=radius,
                    kind="watchtower",
                )
            )

        return sources

    @staticmethod
    def _collect_mobile_sources(
        world_state: WorldState, faction_id: str
    ) -> list[VisionSource]:
        """
        Обзор с того, что движется: армий, караванов рабочих и послов в пути.

        Караван - это обычная армия на карте (см. WorkerAssignment), поэтому
        отдельной ветки для него не нужно.
        """
        sources: list[VisionSource] = []

        for army in world_state.get_faction_armies(faction_id):
            sources.append(
                VisionSource(
                    origin=army.current_hex,
                    radius=army.vision_radius_hexes,
                    kind="army",
                )
            )

        for ambassador in world_state.ambassadors:
            if ambassador.faction_id != faction_id or ambassador.current_hex is None:
                continue
            sources.append(
                VisionSource(
                    origin=ambassador.current_hex,
                    radius=VISION_RADIUS_AMBASSADOR,
                    kind="ambassador",
                )
            )

        return sources

    # ==================================================================
    # ОБМЕН РАЗВЕДДАННЫМИ
    # ==================================================================

    def _collect_shared_intelligence(
        self, world_state: WorldState, faction_id: str
    ) -> set[HexCoordinates]:
        """
        Гексы, которые фракция видит чужими глазами по пакту об обмене
        разведданными.

        Союзник делится не всем полем зрения, а только той его частью, что
        лежит в согласованном радиусе от его собственных источников: договор
        на обмен постами наблюдения не отдает всю карту разом.
        """
        shared: set[HexCoordinates] = set()

        for relation in world_state.diplomatic_relations:
            pact = relation.intelligence_sharing
            if pact is None or relation.stance == DiplomaticStance.WAR:
                continue

            if relation.faction_a_id == faction_id:
                partner_id = relation.faction_b_id
            elif relation.faction_b_id == faction_id:
                partner_id = relation.faction_a_id
            else:
                continue

            for source in self.collect_sources(world_state, partner_id):
                radius = min(source.radius, pact.vision_sharing_radius_hexes)
                shared.update(hex_spiral(source.origin, radius))

        return shared
