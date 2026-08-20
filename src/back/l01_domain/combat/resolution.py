"""
Чистая боевая математика: разрешение натиска и реакций на него,
распространение цепной паники.
"""

from dataclasses import dataclass
from typing import Final

from src.back.l01_domain.army.constants import UnitSizeCategory
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import (
    ACCEPT_CHARGE_DEFENDER_DAMAGE_RATIO,
    CHAIN_PANIC_MORALE_SHOCK,
    CHARGE_DAMAGE_BONUS,
    DOWNHILL_CHARGE_DAMAGE_MULTIPLIER,
    FLEE_CATCH_DAMAGE_MULTIPLIER,
    MORALE_THRESHOLD_ACCEPT_CHARGE,
    UNIT_SIZE_CORPSE_WEIGHT,
    UPHILL_CHARGE_DAMAGE_PENALTY,
    ReactionType,
    SurfaceIncline,
)
from src.back.l01_domain.combat.models.effects import TerrainProfile

# Максимальный множитель превосходства в скорости при таране
MAX_CHARGE_SPEED_RATIO: Final[float] = 3.0
MIN_OPPOSING_SPEED_DENOMINATOR: Final[float] = 0.5


@dataclass(frozen=True)
class ChargeResolution:
    """Результат столкновения атакующего с защищающимся в фазу натиска."""

    damage_to_attacker: float
    damage_to_defender: float
    defender_morale_shock: float = 0.0


def calculate_charge_damage(
    charging_squad: Squad,
    opposing_squad: Squad,
    target_terrain: TerrainProfile,
    elevation: SurfaceIncline = SurfaceIncline.FLAT,
) -> float:
    """
    Базовый урон натиска одной стороны до применения брони цели.
    """
    if (
        charging_squad.total_effective_speed <= 0.0
        or charging_squad.state.unit_count <= 0
        or charging_squad.total_attack_damage <= 0.0
    ):
        return 0.0

    raw_speed_ratio = charging_squad.total_effective_speed / max(
        opposing_squad.total_effective_speed, MIN_OPPOSING_SPEED_DENOMINATOR
    )
    speed_ratio = min(raw_speed_ratio, MAX_CHARGE_SPEED_RATIO)

    damage = (
        charging_squad.total_attack_damage
        * charging_squad.state.unit_count
        * CHARGE_DAMAGE_BONUS
        * speed_ratio
    )
    damage *= max(0.0, 1.0 - target_terrain.charge_penalty)

    if elevation == SurfaceIncline.DESCENT:
        damage *= DOWNHILL_CHARGE_DAMAGE_MULTIPLIER
    elif elevation == SurfaceIncline.ASCENT:
        damage *= UPHILL_CHARGE_DAMAGE_PENALTY

    return max(0.0, damage)


def resolve_charge_reaction(
    attacker: Squad,
    defender: Squad,
    reaction: ReactionType,
    attacker_terrain: TerrainProfile,
    defender_terrain: TerrainProfile,
    elevation: SurfaceIncline = SurfaceIncline.FLAT,
) -> ChargeResolution:
    """
    Разрешает один такт столкновения "Натиск" -> реакция защищающегося.
    """
    charge_damage = calculate_charge_damage(attacker, defender, defender_terrain, elevation)

    # Побег защищающегося
    if reaction == ReactionType.FLEE:
        return ChargeResolution(
            damage_to_attacker=0.0,
            damage_to_defender=charge_damage * FLEE_CATCH_DAMAGE_MULTIPLIER,
        )

    # Встречный натиск
    if reaction == ReactionType.COUNTER_CHARGE:
        # Инвертируем рельеф для встречного удара защитника
        defender_elevation = SurfaceIncline.FLAT
        if elevation == SurfaceIncline.DESCENT:
            defender_elevation = SurfaceIncline.ASCENT
        elif elevation == SurfaceIncline.ASCENT:
            defender_elevation = SurfaceIncline.DESCENT

        counter_damage = calculate_charge_damage(
            defender, attacker, attacker_terrain, defender_elevation
        )
        return ChargeResolution(
            damage_to_attacker=counter_damage,
            damage_to_defender=charge_damage,
        )

    # Принятие удара в строй (упор копий)
    if defender.state.morale >= MORALE_THRESHOLD_ACCEPT_CHARGE:
        return ChargeResolution(
            damage_to_attacker=charge_damage,
            damage_to_defender=charge_damage * ACCEPT_CHARGE_DEFENDER_DAMAGE_RATIO,
        )

    # Не хватило морали удержать строй
    return ChargeResolution(
        damage_to_attacker=0.0,
        damage_to_defender=charge_damage,
        defender_morale_shock=CHAIN_PANIC_MORALE_SHOCK,
    )


def propagate_chain_panic(
    panicking_squad_id: str,
    neighbor_squad_ids: list[str],
) -> dict[str, float]:
    """
    Возвращает удар по морали для соседних союзных отрядов.
    """
    return {
        squad_id: CHAIN_PANIC_MORALE_SHOCK
        for squad_id in neighbor_squad_ids
        if squad_id != panicking_squad_id
    }


def calculate_effective_corpse_weight(deaths: int, size_category: UnitSizeCategory) -> float:
    """
    Переводит число погибших бойцов конкретного размера в эффективный вес трупов.
    """
    return deaths * UNIT_SIZE_CORPSE_WEIGHT.get(size_category, 1.0)
