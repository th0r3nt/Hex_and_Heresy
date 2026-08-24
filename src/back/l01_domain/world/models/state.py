"""
WorldState - корневой агрегат состояния глобальной партии.
"""

from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field

from src.back.l01_domain.army.models.card.equipment import Equipment
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.factions.models.diplomacy.messengers import (
    Ambassador,
    Dispatch,
)
from src.back.l01_domain.factions.models.diplomacy.relation import DiplomaticRelation
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.workers import WorkerAssignment
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.battleground import BattlefieldLootSite
from src.back.l01_domain.world.models.chronicle import (
    ChronicleEntry,
    FallenRecord,
    RumorEntry,
)
from src.back.l01_domain.world.models.events import GlobalEvent
from src.back.l01_domain.world.models.timekeeping import GameTime


class WorldState(BaseModel):
    """
    Полный снимок состояния игрового мира в текущей партии.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    time: GameTime = Field(default_factory=GameTime)

    factions: dict[str, Faction] = Field(default_factory=dict)
    armies: dict[str, StrategicArmy] = Field(default_factory=dict)

    diplomatic_relations: list[DiplomaticRelation] = Field(default_factory=list)
    dispatches: list[Dispatch] = Field(default_factory=list)
    ambassadors: list[Ambassador] = Field(default_factory=list)

    intercepted_dispatches: dict[str, list[Dispatch]] = Field(
        default_factory=dict,
        description=(
            "Чужие депеши, перехваченные фракцией: faction_id -> список писем. "
            "Ложатся в контекст LLM перехватившего лорда"
        ),
    )

    active_events: list[GlobalEvent] = Field(default_factory=list)
    battlefield_sites: dict[str, BattlefieldLootSite] = Field(default_factory=dict)
    neutral_hexes: list[HexCoordinates] = Field(default_factory=list)

    active_battle_armies: dict[str, list[str]] = Field(
        default_factory=dict,
        description="battle_id -> army_id[], армии, залоченные текущим тактическим боем",
    )

    worker_assignments: dict[str, WorkerAssignment] = Field(
        default_factory=dict,
        description="Реестр активных назначений рабочих: assignment_id -> WorkerAssignment",
    )

    # Реестр уникальных предметов, созданных Оружейником в этой сессии
    custom_equipment: dict[str, Equipment] = Field(
        default_factory=dict,
        description="Уникальные чертежи экипировки текущей партии (equipment_id -> Equipment)",
    )

    # ==================================================================
    # ЛЕТОПИСЬ ПАРТИИ
    # ==================================================================

    chronicle_entries: list[ChronicleEntry] = Field(
        default_factory=list, description="Страницы летописи о сражениях этой партии"
    )
    fallen_records: list[FallenRecord] = Field(
        default_factory=list, description="Надгробия Зала павших"
    )
    rumors: list[RumorEntry] = Field(
        default_factory=list, description="Фоновые слухи для окна логов"
    )
    ticks_since_last_battle: int = Field(
        default=0,
        ge=0,
        description="Сколько тактов не было ни одного боя: порог болтливости летописца",
    )

    def get_faction(self, faction_id: str) -> Optional[Faction]:
        return self.factions.get(faction_id)

    def get_player_faction(self) -> Optional[Faction]:
        return next((f for f in self.factions.values() if f.is_player_controlled), None)

    def add_faction(self, faction: Faction) -> None:
        self.factions[faction.id] = faction

    def add_army(self, army: StrategicArmy) -> None:
        self.armies[army.id] = army

    def get_army(self, army_id: str) -> Optional[StrategicArmy]:
        return self.armies.get(army_id)

    def remove_army(self, army_id: str) -> Optional[StrategicArmy]:
        return self.armies.pop(army_id, None)

    def get_armies_at_hex(self, coord: HexCoordinates) -> list[StrategicArmy]:
        return [army for army in self.armies.values() if army.current_hex == coord]

    def get_faction_armies(self, faction_id: str) -> list[StrategicArmy]:
        return [army for army in self.armies.values() if army.faction_id == faction_id]

    def get_relation(
        self, faction_a_id: str, faction_b_id: str
    ) -> Optional[DiplomaticRelation]:
        for rel in self.diplomatic_relations:
            is_direct = rel.faction_a_id == faction_a_id and rel.faction_b_id == faction_b_id
            is_reverse = rel.faction_a_id == faction_b_id and rel.faction_b_id == faction_a_id
            if is_direct or is_reverse:
                return rel
        return None

    def get_or_create_relation(
        self, faction_a_id: str, faction_b_id: str
    ) -> DiplomaticRelation:
        """
        Возвращает отношения пары фракций, создавая мирные при первом контакте.
        """
        relation = self.get_relation(faction_a_id, faction_b_id)
        if relation is None:
            relation = DiplomaticRelation(
                faction_a_id=faction_a_id, faction_b_id=faction_b_id
            )
            self.diplomatic_relations.append(relation)
        return relation

    def add_intercepted_dispatch(self, faction_id: str, dispatch: Dispatch) -> None:
        """
        Кладет перехваченное письмо в разведывательные трофеи фракции.
        """
        self.intercepted_dispatches.setdefault(faction_id, []).append(dispatch)

    def add_event(self, event: GlobalEvent) -> None:
        self.active_events.append(event)

    def cleanup_expired_events(self) -> None:
        self.active_events = [e for e in self.active_events if e.is_active]

    def add_battlefield_site(self, site: BattlefieldLootSite) -> None:
        self.battlefield_sites[site.id] = site

    def get_battlefield_at(self, coord: HexCoordinates) -> Optional[BattlefieldLootSite]:
        for site in self.battlefield_sites.values():
            if site.hex_coordinates == coord and not site.is_depleted:
                return site
        return None

    def cleanup_depleted_battlefields(self) -> None:
        self.battlefield_sites = {
            site_id: site
            for site_id, site in self.battlefield_sites.items()
            if not site.is_depleted
        }

    def lock_armies_for_battle(self, battle_id: str, army_ids: list[str]) -> None:
        """
        Помечает армии как связанные тактическим боем: они не могут добывать
        ресурсы или маршировать, пока бой не завершён.
        """
        self.active_battle_armies[battle_id] = list(army_ids)
        for army_id in army_ids:
            army = self.get_army(army_id)
            if army is not None:
                army.lock_in_tactical_battle()

    def release_armies_from_battle(self, battle_id: str) -> list[str]:
        """
        Снимает лок с армий по завершении боя. Возвращает id освобождённых армий.
        """
        army_ids = self.active_battle_armies.pop(battle_id, [])
        for army_id in army_ids:
            army = self.get_army(army_id)
            if army is not None:
                army.release_from_tactical_battle()
        return army_ids

    # ==================================================================
    # МЕТОДЫ УПРАВЛЕНИЯ НАЗНАЧЕНИЯМИ РАБОЧИХ
    # ==================================================================

    def add_worker_assignment(self, assignment: WorkerAssignment) -> None:
        """Регистрирует новое назначение рабочих."""
        self.worker_assignments[assignment.id] = assignment

    def get_worker_assignment(self, assignment_id: str) -> Optional[WorkerAssignment]:
        """Возвращает назначение по его уникальному ID."""
        return self.worker_assignments.get(assignment_id)

    def get_squad_assignment(self, squad_id: str) -> Optional[WorkerAssignment]:
        """Возвращает активное назначение для конкретного отряда рабочих."""
        for assignment in self.worker_assignments.values():
            if assignment.squad_id == squad_id and assignment.is_active:
                return assignment
        return None

    def get_building_assignments(self, building_id: str) -> list[WorkerAssignment]:
        """Возвращает список активных назначений рабочих для конкретного здания."""
        return [
            a
            for a in self.worker_assignments.values()
            if a.target_building_id == building_id and a.is_active
        ]

    def get_faction_worker_assignments(self, faction_id: str) -> list[WorkerAssignment]:
        """Возвращает все активные назначения рабочих конкретной фракции."""
        return [
            a
            for a in self.worker_assignments.values()
            if a.faction_id == faction_id and a.is_active
        ]

    def cleanup_completed_assignments(self) -> list[WorkerAssignment]:
        """Удаляет завершенные и прерванные назначения из активного реестра."""
        active: dict[str, WorkerAssignment] = {}
        cleaned: list[WorkerAssignment] = []
        for aid, a in self.worker_assignments.items():
            if a.is_active:
                active[aid] = a
            else:
                cleaned.append(a)
        self.worker_assignments = active
        return cleaned

    # Метод для работы с кастомными предметами
    def add_custom_equipment(self, equipment: Equipment) -> None:
        self.custom_equipment[equipment.id] = equipment

    # ==================================================================
    # МЕТОДЫ ЛЕТОПИСИ
    # ==================================================================

    def add_chronicle_entry(self, entry: ChronicleEntry) -> None:
        """
        Дописывает страницу летописи. Повторная запись о том же бое
        игнорируется: перегенерация текста не должна плодить свитки.
        """
        if any(existing.battle_id == entry.battle_id for existing in self.chronicle_entries):
            return
        self.chronicle_entries.append(entry)

    def add_fallen_record(self, record: FallenRecord) -> None:
        """
        Ставит надгробие в Зале павших. Один отряд хоронят единожды.
        """
        if any(existing.squad_id == record.squad_id for existing in self.fallen_records):
            return
        self.fallen_records.append(record)

    def add_rumor(self, rumor: RumorEntry) -> None:
        self.rumors.append(rumor)

    def register_battle_happened(self) -> None:
        """
        Сбрасывает счетчик тишины: пока идут бои, летописцу не до слухов.
        """
        self.ticks_since_last_battle = 0
