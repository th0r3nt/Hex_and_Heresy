"""
WorldState - корневой агрегат состояния глобальной партии.
Объединяет карту, фракции, дипломатию, арсеналы, поля брани и временную шкалу.
"""

from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field

from src.back.l01_domain.factions.models.diplomacy.relation import DiplomaticRelation
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.maps.models.global_map import HexCoordinates
from src.back.l01_domain.world.models.battleground import BattlefieldLootSite
from src.back.l01_domain.world.models.events import GlobalEvent
from src.back.l01_domain.world.models.timekeeping import GameTime


class WorldState(BaseModel):
    """
    Полный снимок состояния игрового мира в текущей партии.
    Мутируется на глобальной фазе расчетом ходов в слое l02_services.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    time: GameTime = Field(default_factory=GameTime)

    # Все политические фракции, участвующие в партии: {faction_id: Faction}
    factions: dict[str, Faction] = Field(default_factory=dict)

    # Двусторонние дипломатические отношения
    diplomatic_relations: list[DiplomaticRelation] = Field(default_factory=list)

    # Активные глобальные и региональные события
    active_events: list[GlobalEvent] = Field(default_factory=list)

    # Поля брани с трофеями на глобальной карте: {site_id: BattlefieldLootSite}
    battlefield_sites: dict[str, BattlefieldLootSite] = Field(default_factory=dict)

    # Нейтральные гексы, формирующие Ничью землю
    neutral_hexes: list[HexCoordinates] = Field(default_factory=list)

    def get_faction(self, faction_id: str) -> Optional[Faction]:
        """Возвращает фракцию по ее уникальному идентификатору."""
        return self.factions.get(faction_id)

    def get_player_faction(self) -> Optional[Faction]:
        """Возвращает фракцию под управлением игрока-человека."""
        return next((f for f in self.factions.values() if f.is_player_controlled), None)

    def add_faction(self, faction: Faction) -> None:
        """Регистрирует новую фракцию в партии."""
        self.factions[faction.id] = faction

    def get_relation(
        self, faction_a_id: str, faction_b_id: str
    ) -> Optional[DiplomaticRelation]:
        """
        Находит объект дипломатических отношений между двумя фракциями независимо от порядка аргументов.
        """
        
        for rel in self.diplomatic_relations:
            is_direct = rel.faction_a_id == faction_a_id and rel.faction_b_id == faction_b_id
            is_reverse = rel.faction_a_id == faction_b_id and rel.faction_b_id == faction_a_id
            if is_direct or is_reverse:
                return rel
        return None

    def add_event(self, event: GlobalEvent) -> None:
        """Добавляет новое событие в активный пул."""
        self.active_events.append(event)

    def cleanup_expired_events(self) -> None:
        """Удаляет завершенные события из активного списка."""
        self.active_events = [e for e in self.active_events if e.is_active]

    def add_battlefield_site(self, site: BattlefieldLootSite) -> None:
        """Регистрирует новое поле брани на карте."""
        self.battlefield_sites[site.id] = site

    def get_battlefield_at(self, coord: HexCoordinates) -> Optional[BattlefieldLootSite]:
        """Ищет активное поле брани на заданном гексе."""
        for site in self.battlefield_sites.values():
            if site.hex_coordinates == coord and not site.is_depleted:
                return site
        return None

    def cleanup_depleted_battlefields(self) -> None:
        """Удаляет истощенные и истлевшие поля брани."""
        self.battlefield_sites = {
            site_id: site
            for site_id, site in self.battlefield_sites.items()
            if not site.is_depleted
        }
