"""
Сервис расчета тактической инициативы и определения очередности ходов отрядов.
"""

from typing import Optional

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.characters.commanders import Commander
from src.back.l01_domain.army.models.characters.heroes import Hero
from src.back.l01_domain.combat.models.state import TacticalBattleState


class TacticalInitiativeService:
    """
    Рассчитывает динамическую инициативу боевых единиц на сетке
    с учетом базовых статов, экипировки, полководцев, героев,
    состояния отряда (паника, истощение) и эффектов местности.
    """

    def calculate_squad_initiative(
        self,
        squad: Squad,
        commander: Optional[Commander] = None,
        hero: Optional[Hero] = None,
    ) -> int:
        """
        Вычисляет итоговое значение инициативы для конкретного отряда.
        """

        # Базовая инициатива расового шаблона
        total_initiative = squad.archetype.base_stats.base_initiative

        # Модификаторы экипировки
        if squad.weapon is not None:
            total_initiative += squad.weapon.stats.initiative_modifier
        if squad.armor is not None:
            total_initiative += squad.armor.stats.initiative_modifier
        if squad.accessory is not None:
            total_initiative += squad.accessory.stats.initiative_modifier

        # Влияние полководца (архетип и тактическое чутье)
        if commander is not None:
            total_initiative += commander.archetype.stats.initiative_modifier
            total_initiative += commander.characteristics.tactical_acumen // 10

        # Влияние прикрепленного героя
        if hero is not None and hero.state.attached_squad_id == squad.id:
            for modifier in hero.get_active_modifiers():
                if modifier.stat_name == "initiative": # TODO: сделать статы героев типизированными
                    total_initiative += int(modifier.value)

        # Штрафы за истощение и панику
        if squad.state.is_exhausted:
            total_initiative -= 5
        if squad.state.is_in_panic:
            total_initiative -= 10

        return total_initiative

    def get_turn_order(
        self,
        squads: dict[str, Squad],
        battle_state: TacticalBattleState,
        commanders: Optional[dict[str, Commander]] = None,
        heroes: Optional[dict[str, Hero]] = None,
    ) -> list[str]:
        """
        Формирует детерминированный список идентификаторов отрядов,
        отсортированный по убыванию инициативы.

        Тай-брейкер при равенстве инициатив:
        1. Сторона защиты ходит раньше стороны нападения при равной инициативе (оборонительное преимущество).
        2. Лексикографический порядок squad_id для полной воспроизводимости симуляции.
        """
        
        commander_map = commanders or {}
        hero_map = heroes or {}

        scored_squads: list[tuple[int, int, str]] = []

        for squad_id, squad in squads.items():
            if squad.state.unit_count <= 0:
                continue

            # Определяем сторону отряда для тай-брейкера
            is_defender = squad_id in battle_state.defender_squad_ids
            side_priority = 1 if is_defender else 0

            # Ищем полководца и героя соответствующей стороны
            commander = None
            for cmd in commander_map.values():
                if cmd.faction_id == squad.archetype.faction_id:
                    commander = cmd
                    break

            hero = None
            for h in hero_map.values():
                if h.state.attached_squad_id == squad_id:
                    hero = h
                    break

            initiative = self.calculate_squad_initiative(
                squad=squad,
                commander=commander,
                hero=hero,
            )

            # Сортировка кортежа: (-initiative, -side_priority, squad_id)
            scored_squads.append((initiative, side_priority, squad_id))

        # Сортируем: сначала наибольшая инициатива, затем защитники, затем по ID
        scored_squads.sort(key=lambda item: (-item[0], -item[1], item[2]))

        return [item[2] for item in scored_squads]
