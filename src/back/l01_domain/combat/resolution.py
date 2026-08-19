"""
Чистая боевая математика: разрешение натиска и реакций на него,
распространение цепной паники.

Не знает о WorldState, БД или LLM - только домен и числа.

Применение результата к состоянию отряда,
поиск соседей на сетке и порядок обработки за такт - забота l02_services.
"""

from dataclasses import dataclass

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.constants import UnitSizeCategory
from src.back.l01_domain.combat.constants import (
    ACCEPT_CHARGE_DEFENDER_DAMAGE_RATIO,
    CHAIN_PANIC_MORALE_SHOCK,
    CHARGE_DAMAGE_BONUS,
    DOWNHILL_CHARGE_DAMAGE_MULTIPLIER,
    FLEE_CATCH_DAMAGE_MULTIPLIER,
    MORALE_THRESHOLD_ACCEPT_CHARGE,
    UPHILL_CHARGE_DAMAGE_PENALTY,
    UNIT_SIZE_CORPSE_WEIGHT,
    ReactionType,
    SurfaceIncline,
)
from src.back.l01_domain.combat.models.effects import TerrainProfile


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
    Базовый урон натиска одной стороны, до применения брони цели.

    Зависит от: атакующего урона бойца, численности отряда, бонуса натиска,
    относительной скорости атакующего к защищающемуся, рельефа и местности цели.
    """

    speed_ratio = charging_squad.total_effective_speed / max(
        opposing_squad.total_effective_speed, 0.01
    )
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
    (см. fighting.md, "Механика реакций")
    """

    charge_damage = calculate_charge_damage(attacker, defender, defender_terrain, elevation)

    # Убежать от врага
    if reaction == ReactionType.FLEE:
        # Побег не удаётся: атакующий догоняет и вырезает бегущих почти без потерь.
        return ChargeResolution(
            damage_to_attacker=0.0,
            damage_to_defender=charge_damage * FLEE_CATCH_DAMAGE_MULTIPLIER,
        )

    # Побежать вперед
    if reaction == ReactionType.COUNTER_CHARGE:
        # Обе стороны бегут навстречу - урон физики столкновения колоссален с обеих сторон.
        counter_damage = calculate_charge_damage(
            defender, attacker, attacker_terrain, elevation
        )
        return ChargeResolution(
            damage_to_attacker=counter_damage,
            damage_to_defender=charge_damage,
        )

    # Принять натиск
    if defender.state.morale >= MORALE_THRESHOLD_ACCEPT_CHARGE:
        # Копья упёрты в землю - урон натиска оборачивается против атакующего,
        # защитник получает лишь часть урона (передний ряд).
        return ChargeResolution(
            damage_to_attacker=charge_damage,
            damage_to_defender=charge_damage * ACCEPT_CHARGE_DEFENDER_DAMAGE_RATIO,
        )

    # Духа не хватило держать строй - отряд ломается перед самым ударом
    # и получает урон как небронированная толпа, плюс удар по морали.
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
    Возвращает удар по морали для соседних (в радиусе CHAIN_PANIC_RADIUS_CELLS)
    союзных отрядов, когда panicking_squad_id проваливает проверку морали.
    (см. fighting.md, "Моральный шок и цепная паника")

    Поиск соседей в радиусе на сетке - забота вызывающего кода
    (TacticalBattleState уже знает геометрию клеток), здесь только формула шока.
    """

    return {
        squad_id: CHAIN_PANIC_MORALE_SHOCK
        for squad_id in neighbor_squad_ids
        if squad_id != panicking_squad_id
    }


def calculate_effective_corpse_weight(deaths: int, size_category: UnitSizeCategory) -> float:
    """
    Переводит число погибших бойцов конкретного размера в эффективный вес
    для сравнения с CORPSE_PILE_UNIT_THRESHOLD (см. fighting.md, "Горы трупов").
    """

    return deaths * UNIT_SIZE_CORPSE_WEIGHT.get(size_category, 1.0)
