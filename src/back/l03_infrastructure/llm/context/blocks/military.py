from src.back.l01_domain.army.constants import StrategicMovementPace
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.combat.constants import TerrainType
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.llm.models.context import ContextBlock
from src.back.l01_domain.world.battle_summary import render_battle_summary
from src.back.l01_domain.world.models.battle_log import BattleDossier


def build_army_block(army: StrategicArmy) -> ContextBlock:
    squads_count = len(army.squads)
    total_units = army.total_units_count

    pace_label = {
        StrategicMovementPace.CAUTIOUS: "Осторожный шаг",
        StrategicMovementPace.MARCH: "Марш",
        StrategicMovementPace.FORCED: "Форсированный марш",
        StrategicMovementPace.MOUNTED: "Конный марш",
    }.get(army.pace, "Стоит на месте")

    lines = [
        f"Армия: {army.name}.",
        f"Позиция на карте: гекс ({army.current_hex.q}, {army.current_hex.r}).",
        f"Темп перемещения: {pace_label}.",
        f"Состав: {squads_count} отрядов, всего {total_units} бойцов.",
    ]

    panicking = sum(1 for s in army.squads if s.state.is_in_panic)
    exhausted = sum(1 for s in army.squads if s.state.is_exhausted)

    if panicking > 0:
        lines.append(f"Внимание: {panicking} отрядов находятся в панике и бегут!")
    if exhausted > 0:
        lines.append(f"Внимание: {exhausted} отрядов физически истощены.")

    return ContextBlock(title="Состояние армии", body="\n".join(f"- {line}" for line in lines))


def build_battle_block(battle_state: TacticalBattleState) -> ContextBlock:
    lines = [
        f"Текущий раунд (такт) боя: {battle_state.current_tick}.",
        f"Фаза: {battle_state.phase.value}.",
        f"Погода: {battle_state.weather.value}, Время суток: {battle_state.time_of_day.value}.",
    ]

    corpses = sum(1 for c in battle_state.cells if c.terrain_type == TerrainType.CORPSE_PILE)
    if corpses > 0:
        lines.append(f"На поле брани образовалось гор трупов: {corpses}.")

    return ContextBlock(
        title="Тактическая обстановка", body="\n".join(f"- {line}" for line in lines)
    )


def build_battle_summary_block(dossier: BattleDossier) -> ContextBlock:
    # Используем готовый доменный метод (который применялся в старом летописце)
    return ContextBlock(title="Итоги сражения", body=render_battle_summary(dossier))
