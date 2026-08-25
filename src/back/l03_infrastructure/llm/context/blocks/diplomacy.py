from typing import Optional

from src.back.l01_domain.factions.constants import DiplomaticStance
from src.back.l01_domain.llm.models.context import ContextBlock
from src.back.l01_domain.world.models.state import WorldState


def build_diplomacy_block(
    world_state: WorldState, faction_id: str, counterpart_id: Optional[str] = None
) -> ContextBlock:
    """
    Если counterpart_id передан — собираем детальную сводку отношений между
    двумя фракциями (для прямых переговоров и дипломатов).
    Если не передан — собираем глобальную сводку войн для полководцев и советников.
    """
    if counterpart_id:
        relation = world_state.get_relation(faction_id, counterpart_id)
        if relation is None:
            return ContextBlock(
                title="Дипломатическая обстановка",
                body="- Между вами нет ни договоров, ни объявленной войны.",
            )

        active_pacts = []
        if relation.trade_agreement:
            active_pacts.append("торговое соглашение")
        if relation.non_aggression_pact:
            active_pacts.append("договор о ненападении")
        if relation.right_of_passage:
            active_pacts.append("право прохода")
        if relation.vassal_pact:
            active_pacts.append("вассалитет")
        if relation.intelligence_sharing:
            active_pacts.append("обмен разведданными")
        if relation.hostage_exchange:
            active_pacts.append("обмен заложниками")
        if relation.war_alliance:
            active_pacts.append("военный союз")

        lines = [f"Текущее состояние отношений: {relation.stance.value}."]
        if active_pacts:
            lines.append("Действующие соглашения: " + ", ".join(active_pacts) + ".")
        if relation.tribute_demanded_gold:
            lines.append(
                f"Не закрыто требование дани: {relation.tribute_demanded_gold} золота."
            )

        return ContextBlock(
            title="Дипломатическая обстановка", body="\n".join(f"- {line}" for line in lines)
        )
    else:
        wars = []
        for relation in world_state.diplomatic_relations:
            if relation.stance == DiplomaticStance.WAR:
                if relation.faction_a_id == faction_id:
                    enemy = world_state.get_faction(relation.faction_b_id)
                    wars.append(enemy.name if enemy else relation.faction_b_id)
                elif relation.faction_b_id == faction_id:
                    enemy = world_state.get_faction(relation.faction_a_id)
                    wars.append(enemy.name if enemy else relation.faction_a_id)

        body = (
            f"- В состоянии войны с: {', '.join(wars)}."
            if wars
            else "- Фракция живет в мире, открытых войн нет."
        )
        return ContextBlock(title="Внешние угрозы", body=body)


def build_world_wars_block(world_state: WorldState) -> ContextBlock:
    """
    Все воюющие пары карты для того, кто смотрит на мир со стороны (летописец).
    """
    wars = []
    for relation in world_state.diplomatic_relations:
        if relation.stance != DiplomaticStance.WAR:
            continue
        first = world_state.get_faction(relation.faction_a_id)
        second = world_state.get_faction(relation.faction_b_id)
        wars.append(
            f"{first.name if first else relation.faction_a_id} против "
            f"{second.name if second else relation.faction_b_id}"
        )

    body = f"- Войны: {'; '.join(wars)}." if wars else "- Открытых войн на карте нет."
    return ContextBlock(title="Войны на карте", body=body)
