"""
Гейт тумана войны для ленты событий.

Мост "шина -> сокет" вещает все подряд, а окно клиента принадлежит игроку:
без фильтра лента выдала бы марши врага, которых на карте не видно. Гейт
стоит перед рассылкой и отвечает на один вопрос - имеет ли игрок право
узнать об этом событии.

Правил ровно два:
* событие с гексом уезжает клиенту, только если гекс просматривается игроком;
* адресное событие (в нем указан наблюдатель) уезжает, только если наблюдатель -
  сам игрок.

Все прочее пропускается как есть: экономика собственной державы, фазы боя и
смена экранов туманом не закрываются.
"""

from typing import Any, Optional

from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l02_services.gameflow.facade import GameFlowFacade
from src.back.l02_services.mechanics.vision.facade import VisionFacade

# Поля нагрузки, которыми сервисы называют место происшествия.
# Именно место, а не цель приказа: гекс, куда игрок только собирается идти,
# туманом закрывать нельзя - это его собственный приказ.
HEX_PAYLOAD_KEYS: tuple[str, ...] = ("hex_coords", "hex_coordinates")

# Поле, которым событие называет своего адресата
OBSERVER_PAYLOAD_KEY = "observer_faction_id"


class PlayerVisionGate:
    """
    Пропускает в сокет только то, что фракция игрока действительно видит.
    """

    def __init__(
        self,
        gameflow_facade: GameFlowFacade,
        vision_facade: Optional[VisionFacade] = None,
    ) -> None:
        self._gameflow = gameflow_facade
        self._vision = vision_facade or VisionFacade()

    def __call__(self, event_key: str, payload: dict[str, Any]) -> bool:
        """
        Решает судьбу одного события. True - вещать, False - промолчать.

        Пока партия не начата, гейт не мешает ничему: событий мира в этот
        момент все равно нет, а служебные сообщения канала нужны клиенту.
        """
        world_state = self._gameflow.world_state
        if world_state is None:
            return True

        player = world_state.get_player_faction()
        if player is None:
            return True

        observer_id = payload.get(OBSERVER_PAYLOAD_KEY)
        if isinstance(observer_id, str) and observer_id != player.id:
            return False

        coord = self._extract_hex(payload)
        if coord is None:
            return True

        return self._vision.is_hex_visible(
            world_state=world_state, faction_id=player.id, coord=coord
        )

    @staticmethod
    def _extract_hex(payload: dict[str, Any]) -> Optional[HexCoordinates]:
        """
        Достает из нагрузки координаты гекса, если событие вообще привязано
        к месту на карте.

        Нагрузка приходит и живыми моделями (событие опубликовано сервисом),
        и словарями (событие пересобрано из сохранения), поэтому разбираются
        оба вида.
        """
        for key in HEX_PAYLOAD_KEYS:
            value = payload.get(key)
            if isinstance(value, HexCoordinates):
                return value
            if isinstance(value, dict) and {"q", "r"} <= value.keys():
                return HexCoordinates.from_axial(int(value["q"]), int(value["r"]))
        return None
