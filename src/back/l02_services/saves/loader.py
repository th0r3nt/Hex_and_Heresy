"""
Загружает сохранение из базы данных и восстанавливает состояние игры и фракций.

Обертка над SaveGameRepositoryProtocol: достает снимок, чинит инварианты,
пережившие запись, и поднимает поверх него сессионный реестр геймдаты.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from pydantic import ValidationError

from src.back.l01_domain.army.models.card.equipment import Equipment
from src.back.l01_domain.exceptions.saves import SaveDataCorruptedError, SaveNotFoundError
from src.back.l01_domain.protocols.gamedata import GameDataRepositoryProtocol
from src.back.l01_domain.protocols.saves import SaveGameRepositoryProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.utils.logger import main_logger

# Фабрика сессионного репозитория геймдаты.
# Слой сервисов не имеет права знать про SessionGameDataRepository из l03,
# поэтому composition root подсовывает сюда замыкание вида
# `lambda custom: SessionGameDataRepository(static_registry, custom)`.
GameDataRepositoryFactory = Callable[[list[Equipment]], GameDataRepositoryProtocol]


@dataclass(frozen=True)
class LoadedSession:
    """
    Результат подъема партии: восстановленный мир и собранный под него
    репозиторий геймдаты (статика плюс кастомные чертежи этой партии).
    """

    world_state: WorldState
    gamedata: GameDataRepositoryProtocol


class WorldStateLoader:
    """
    Восстанавливает игровую сессию из сохранения.

    Отвечает за то, чтобы поднятый WorldState был пригоден к игре сразу:
    без залоченных призрачным боем армий и с доступной кастомной экипировкой.
    """

    def __init__(
        self,
        repository: SaveGameRepositoryProtocol,
        gamedata_factory: GameDataRepositoryFactory,
    ) -> None:
        self._repository = repository
        self._gamedata_factory = gamedata_factory

    async def load(self, save_id: str) -> LoadedSession:
        """
        Поднимает партию по идентификатору сохранения.

        Бросает SaveNotFoundError, если записи нет, и SaveDataCorruptedError,
        если снимок не проходит валидацию текущими доменными моделями
        (например, сейв остался от предыдущей версии схемы).
        """
        try:
            world_state = await self._repository.load_world_state(save_id)
        except ValidationError as e:
            raise SaveDataCorruptedError(save_id, str(e)) from e

        if world_state is None:
            raise SaveNotFoundError(save_id)

        return self.restore_session(world_state)

    def restore_session(self, world_state: WorldState) -> LoadedSession:
        """
        Приводит уже полученный WorldState в играбельное состояние и собирает
        под него репозиторий геймдаты.

        Вызывается и при загрузке сейва, и при старте новой партии - во втором
        случае мир приходит от генератора мира, а не из базы.
        """
        self._repair(world_state)
        return LoadedSession(
            world_state=world_state,
            gamedata=self.build_gamedata(world_state),
        )

    def build_gamedata(self, world_state: WorldState) -> GameDataRepositoryProtocol:
        """
        Собирает сессионный репозиторий: статические каталоги плюс уникальные
        чертежи Оружейника, лежащие в самом снимке партии.
        """
        return self._gamedata_factory(list(world_state.custom_equipment.values()))

    async def peek_metadata(self, save_id: str) -> Optional[dict]:
        """
        Возвращает метаданные конкретного сохранения без подъема партии.
        Нужен экрану загрузки для превью выбранной строки списка.
        """
        for record in await self._repository.list_saves():
            if record.get("id") == save_id:
                return record
        return None

    def _repair(self, world_state: WorldState) -> None:
        """
        Чинит инварианты, которые не переживают запись на диск.

        Сохранение посреди тактического боя запрещено дампером, но сейв мог
        приехать из аварийно завершенной сессии или из старой версии игры,
        поэтому призрачные локи снимаются принудительно: иначе армии навсегда
        останутся неподвижными.
        """
        for battle_id in list(world_state.active_battle_armies.keys()):
            world_state.release_armies_from_battle(battle_id)
            main_logger.warning(
                f"В сохранении обнаружен незавершенный бой '{battle_id}': армии освобождены."
            )

        for army in world_state.armies.values():
            if army.is_in_tactical_battle:
                army.release_from_tactical_battle()
                main_logger.warning(
                    f"Армия '{army.id}' была залочена несуществующим боем: лок снят."
                )

        for battle_id in list(world_state.active_battle_garrisons.keys()):
            world_state.release_garrisons_from_battle(battle_id)

        for garrison in world_state.garrisons.values():
            if garrison.is_locked_in_battle:
                garrison.is_locked_in_battle = False
                main_logger.warning(
                    f"Гарнизон земли '{garrison.zone_id}' был заморожен "
                    "несуществующим боем: лок снят."
                )

        world_state.cleanup_expired_events()
        world_state.cleanup_depleted_battlefields()
        world_state.cleanup_completed_assignments()
