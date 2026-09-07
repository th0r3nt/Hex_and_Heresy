"""
Формат сообщений вебсокета.

Канал односторонний по смыслу: сервер рассказывает клиенту о жизни мира,
а команды игрока идут обычным HTTP. Поэтому наружу едет один конверт
ServerMessage, а внутрь принимается только служебный пинг.
"""

from typing import Any

from pydantic import BaseModel, Field

# Служебные события самого канала - в отличие от игровых, они не приходят
# с шины, а рождаются здесь же.
CONNECTION_ESTABLISHED = "connection.established"
CONNECTION_PONG = "connection.pong"


class ServerMessage(BaseModel):
    """
    Конверт исходящего сообщения.

    event - строковый ключ события с шины (напр. "tactical.turn_completed"),
    data - его полезная нагрузка в том виде, в каком ее опубликовал сервис.
    """

    event: str = Field(..., min_length=1)
    data: dict[str, Any] = Field(default_factory=dict)


class ClientMessage(BaseModel):
    """
    Входящее сообщение от клиента.

    Игровых команд здесь не бывает: единственное, что умеет клиент, -
    напомнить о себе пингом, чтобы соединение не сочли мертвым.
    """

    action: str = Field(..., min_length=1)
