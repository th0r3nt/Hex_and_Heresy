from pydantic import BaseModel
from typing import Dict, List, Optional, Literal
from enum import Enum


class Race(str, Enum):
    HUMAN = "human"
    GREENSKIN = "greenskin"
    ELF = "elf"
    ROBBER = "robber"
    BARON = "baron"
    MERCENARIES = "mercenaries"


class Resources(BaseModel):
    gold: int = 0
    material: int = 0
    provision: int = 0


class Unit(BaseModel):
    id: str
    name: str
    tier: Literal[1, 2, 3, 4, 5, 6]
    quantity: int  # Количество бойцов в карточке

    # Характеристики
    max_hp: int
    current_hp: int
    damage: int
    armor: int = 0

    # Потребление
    upkeep_gold: int = 0
    upkeep_provision: int = 0

    # Для механики ветеранства
    is_veteran: bool = False
    commander_name: Optional[str] = None
    commander_lore: Optional[str] = None


class Building(BaseModel):
    id: str
    name: str
    level: Literal[1, 2, 3, 4, 5, 6] = 1
    upgrades: List[str] = []


class HexZone(BaseModel):
    zone_id: str
    zone_type: Literal["base", "ally", "neutral"]
    owner: Literal["player", "enemy", "neutral"]
    buildings: List[Building] = []

    # Находящиеся карточки юнитов в этой зоне
    units: List[Unit] = []

    # Модификаторы (напр. от местности или локальных событий)
    modifiers: List[str] = []


class PlayerState(BaseModel):
    race: Race
    resources: Resources
    # и т.д.


class WorldState(BaseModel):
    turn: int = 1
    max_turns: int = 100
    map_zones: Dict[str, HexZone] = {}
    player: PlayerState
    enemy: PlayerState