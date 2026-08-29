"""
Маскирование состояния мира под конкретную фракцию.

Игрок не имеет права видеть весь WorldState: в нем лежат и чужие армии, и
чужие гонцы, и вся Ничья земля до последнего гекса. Фильтр снимает с мира
копию и вычеркивает из нее все, чего фракция своими глазами не видит.

Правило одно и простое:
* прямая видимость - гекс отдается как есть, вместе с тем, что по нему ходит;
* туман войны - остаются ландшафт, застройка и места, но не движение;
* черный туман - гекс не отдается вообще.

Своя сторона под фильтр не попадает никогда: собственные армии и письма
фракция видит независимо от того, куда они забрели.
"""

from typing import Optional

from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.maps.models.strategic import (
    HexCoordinates,
    hex_from_zone_id,
)
from src.back.l01_domain.world.constants import GlobalEventScope
from src.back.l01_domain.world.models.state import WorldState
from src.back.l01_domain.world.models.visibility import FactionVisionMap


class VisionFilter:
    """
    Отдает срез мира, очищенный от чужих секретов.
    """

    def filter_world_for_faction(
        self, world_state: WorldState, faction_id: str
    ) -> WorldState:
        """
        Возвращает независимую копию мира, урезанную до знаний фракции.

        Копия обязательна: срез уезжает клиенту и не должен быть тем же
        объектом, по которому дальше считается такт.
        """
        view = world_state.model_copy(deep=True)
        vision_map = view.get_or_create_vision_map(faction_id)

        self._hide_foreign_armies(view, faction_id, vision_map)
        self._hide_foreign_worker_assignments(view, faction_id)
        self._hide_foreign_ambassadors(view, faction_id, vision_map)
        self._hide_foreign_dispatches(view, faction_id, vision_map)
        self._hide_unexplored_places(view, vision_map)
        self._hide_unexplored_events(view, faction_id, vision_map)
        self._hide_foreign_territory(view, faction_id, vision_map)
        self._keep_own_vision_map_only(view, faction_id)

        return view

    # ==================================================================
    # ТО, ЧТО ДВИЖЕТСЯ: ВИДНО ТОЛЬКО В ПРЯМОМ ОБЗОРЕ
    # ==================================================================

    @staticmethod
    def _hide_foreign_armies(
        view: WorldState, faction_id: str, vision_map: FactionVisionMap
    ) -> None:
        """
        Убирает чужие армии и караваны, стоящие вне поля зрения.

        Вместе с армией уходят и следы ее участия в бою: иначе по замку
        активных боев можно было бы вычислить невидимого противника.
        """
        hidden_army_ids = {
            army_id
            for army_id, army in view.armies.items()
            if army.faction_id != faction_id and not vision_map.is_visible(army.current_hex)
        }
        if not hidden_army_ids:
            return

        for army_id in hidden_army_ids:
            view.armies.pop(army_id, None)

        view.active_battle_armies = {
            battle_id: [aid for aid in army_ids if aid not in hidden_army_ids]
            for battle_id, army_ids in view.active_battle_armies.items()
        }

    @staticmethod
    def _hide_foreign_worker_assignments(view: WorldState, faction_id: str) -> None:
        """
        Убирает чужие наряды рабочих целиком.

        Наряд - это внутренняя бухгалтерия державы, а не объект на карте: по
        нему читаются и маршрут каравана, и срок его добычи, даже когда сам
        караван скрыт туманом.
        """
        view.worker_assignments = {
            assignment_id: assignment
            for assignment_id, assignment in view.worker_assignments.items()
            if assignment.faction_id == faction_id
        }

    @staticmethod
    def _hide_foreign_ambassadors(
        view: WorldState, faction_id: str, vision_map: FactionVisionMap
    ) -> None:
        """
        Убирает чужих послов в пути, если их не видно с наблюдательных постов.

        Посол, уже дошедший до цитадели фракции, остается: он стоит на
        пороге и о его прибытии известно и без разведки.
        """
        view.ambassadors = [
            ambassador
            for ambassador in view.ambassadors
            if ambassador.faction_id == faction_id
            or ambassador.target_faction_id == faction_id
            or ambassador.current_hex is None
            or vision_map.is_visible(ambassador.current_hex)
        ]

    @staticmethod
    def _hide_foreign_dispatches(
        view: WorldState, faction_id: str, vision_map: FactionVisionMap
    ) -> None:
        """
        Убирает чужих гонцов, чей текущий гекс вне поля зрения.

        Текущее положение гонца - первый гекс непройденного остатка пути.
        Депеши, адресованные самой фракции или ею отправленные, остаются
        всегда: это ее собственная переписка.
        """

        def is_hidden(dispatch) -> bool:
            if faction_id in (dispatch.sender_faction_id, dispatch.recipient_faction_id):
                return False
            if not dispatch.route:
                return True
            return not vision_map.is_visible(dispatch.route[0])

        view.dispatches = [d for d in view.dispatches if not is_hidden(d)]

    # ==================================================================
    # ТО, ЧТО СТОИТ НА МЕСТЕ: ВИДНО С МОМЕНТА ПЕРВОГО ОТКРЫТИЯ
    # ==================================================================

    @staticmethod
    def _hide_unexplored_places(view: WorldState, vision_map: FactionVisionMap) -> None:
        """
        Убирает места и поля брани с гексов, которых фракция не открывала.

        Однажды найденная воронка с резонитом с карты уже не пропадает -
        поэтому здесь достаточно факта разведки, а не прямого обзора.
        """
        view.points_of_interest = {
            poi_id: poi
            for poi_id, poi in view.points_of_interest.items()
            if vision_map.is_explored(poi.hex_coordinates)
        }
        view.battlefield_sites = {
            site_id: site
            for site_id, site in view.battlefield_sites.items()
            if vision_map.is_explored(site.hex_coordinates)
        }
        view.neutral_hexes = [
            coord for coord in view.neutral_hexes if vision_map.is_explored(coord)
        ]

    @staticmethod
    def _hide_unexplored_events(
        view: WorldState, faction_id: str, vision_map: FactionVisionMap
    ) -> None:
        """
        Убирает локальные события, разыгравшиеся в неразведанных секторах.

        Глобальные события и события, направленные на саму фракцию, остаются:
        мор и неурожай на своей земле замечают без разведки.
        """

        def is_known(event) -> bool:
            if event.scope != GlobalEventScope.ZONE:
                return True
            if faction_id in event.target_faction_ids:
                return True

            epicenters: list[HexCoordinates] = list(event.target_hex_coords)
            if event.spawn_hex is not None:
                epicenters.append(event.spawn_hex)
            if not epicenters:
                return True

            return any(vision_map.is_explored(coord) for coord in epicenters)

        view.active_events = [e for e in view.active_events if is_known(e)]

    @staticmethod
    def _hide_foreign_territory(
        view: WorldState, faction_id: str, vision_map: FactionVisionMap
    ) -> None:
        """
        Прячет чужую державу до той ее части, которую фракция разведала.

        Из фракции-соседа вычеркиваются города, ратуши, здания и земли на
        неоткрытых гексах, а вместе с ними уходят их гарнизоны и операции
        над их поселениями. Казна,
        налоги и лорд соседа не трогаются: это предмет дипломатии и
        разведданных, а не тумана войны.
        """
        for other_id, other in view.factions.items():
            if other_id == faction_id:
                continue
            VisionFilter._trim_faction_territory(other, vision_map)

        view.garrisons = {
            zone_id: garrison
            for zone_id, garrison in view.garrisons.items()
            if garrison.faction_id == faction_id
            or vision_map.is_explored(hex_from_zone_id(zone_id))
        }

        known_town_ids = {
            town.id for faction in view.factions.values() for town in faction.border_towns
        }
        view.border_town_operations = {
            town_id: operation
            for town_id, operation in view.border_town_operations.items()
            if town_id in known_town_ids
        }

    @staticmethod
    def _trim_faction_territory(
        faction: Faction, vision_map: FactionVisionMap
    ) -> None:
        """
        Оставляет чужой фракции только ту застройку, что стоит на разведанных гексах.
        """
        faction.border_towns = [
            town
            for town in faction.border_towns
            if vision_map.is_explored(town.center_hex)
        ]
        faction.regional_halls = [
            hall
            for hall in faction.regional_halls
            if vision_map.is_explored(hex_from_zone_id(hall.zone_id))
        ]
        faction.buildings = [
            constructed
            for constructed in faction.buildings
            if vision_map.is_explored(hex_from_zone_id(constructed.zone_id))
        ]
        faction.controlled_zone_ids = [
            zone_id
            for zone_id in faction.controlled_zone_ids
            if vision_map.is_explored(hex_from_zone_id(zone_id))
        ]

        capital: Optional[HexCoordinates] = faction.capital_hex
        if capital is not None and not vision_map.is_explored(capital):
            faction.capital_hex = None

    # ==================================================================
    # ЧУЖИЕ МАСКИ ТУМАНА
    # ==================================================================

    @staticmethod
    def _keep_own_vision_map_only(view: WorldState, faction_id: str) -> None:
        """
        Оставляет в срезе только собственную маску тумана.

        По чужой маске читается вся чужая разведка разом - это ровно та
        информация, ради сокрытия которой туман и вводился.
        """
        own = view.vision_maps.get(faction_id)
        view.vision_maps = {} if own is None else {faction_id: own}
