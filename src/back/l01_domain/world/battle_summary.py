"""
Текстовая проекция досье боя.

Досье (battle_log.py) хранит числа, а языковая модель читает прозу. Перевод
одного в другое живет в домене, потому что нужен сразу двоим: летописцу
(l02_services/mechanics/chronicler) и сборщику контекста для промптов
(l03_infrastructure/llm/context) - и расходиться между ними эти тексты не должны.
"""

from src.back.l01_domain.world.models.battle_log import BattleDossier, BattleSide


def render_battle_summary(dossier: BattleDossier) -> str:
    """
    Разворачивает досье в сводку сражения для промпта.

    Проза с числами, а не JSON: модель пересказывает бой, а не разбирает
    структуру, и на связном тексте держит нить рассказа заметно лучше.
    """
    sections = [
        _render_setting(dossier),
        _render_side(dossier, BattleSide.ATTACKER, "Нападавшие"),
        _render_side(dossier, BattleSide.DEFENDER, "Оборонявшиеся"),
        _render_turning_points(dossier),
        _render_outcome(dossier),
    ]
    return "\n\n".join(section for section in sections if section)


def _render_setting(dossier: BattleDossier) -> str:
    lines = [
        f"Место: {dossier.location_name}.",
        f"Погода: {dossier.weather.value}, время суток: {dossier.time_of_day.value}.",
        f"Такт мира: {dossier.started_tick}, раундов боя: {dossier.finished_tick or 0}.",
    ]
    if dossier.is_siege:
        lines.append("Это был штурм цитадели.")
    return "Обстановка:\n" + "\n".join(f"- {line}" for line in lines)


def _render_side(dossier: BattleDossier, side: BattleSide, title: str) -> str:
    logs = dossier.side_squads(side)
    if not logs:
        return ""

    header = (
        f"{title} ({len(logs)} карточек, всего {dossier.side_initial_count(side)} бойцов, "
        f"потеряно {dossier.side_deaths(side)}):"
    )
    lines = []
    for log in logs:
        marks = []
        if log.is_named:
            marks.append("именной отряд")
        if log.panicked:
            marks.append("бежал с поля")
        if log.wiped_out:
            marks.append("уничтожен полностью")
        suffix = f" [{', '.join(marks)}]" if marks else ""
        lines.append(
            f"- {log.display_name} ({log.archetype_name or log.race.value}): "
            f"было {log.initial_count}, погибло {log.deaths}, убил {log.kills}{suffix}"
        )
    return header + "\n" + "\n".join(lines)


def _render_turning_points(dossier: BattleDossier) -> str:
    if not dossier.turning_points:
        return ""

    lines = []
    for point in dossier.turning_points:
        actors = " -> ".join(name for name in (point.actor_name, point.target_name) if name)
        prefix = f"- Раунд {point.tick}"
        if actors:
            prefix += f", {actors}"
        lines.append(f"{prefix}: {point.details or point.kind.value}")
    return "Переломные моменты:\n" + "\n".join(lines)


def _render_outcome(dossier: BattleDossier) -> str:
    lines = [f"Всего погибло: {dossier.total_deaths}."]

    if dossier.victor_faction_id:
        lines.append(f"Поле осталось за фракцией '{dossier.victor_faction_id}'.")
    else:
        lines.append("Победителя нет: бой не дал перевеса ни одной стороне.")

    if dossier.is_massacre:
        lines.append("Одна из сторон была вырезана почти полностью.")

    named_lost = dossier.named_squads_lost
    if named_lost:
        names = ", ".join(log.display_name for log in named_lost)
        lines.append(f"Полегли именные отряды: {names}.")

    if dossier.heroes_slain:
        lines.append(f"Погибли герои: {', '.join(dossier.heroes_slain)}.")

    return "Итог:\n" + "\n".join(f"- {line}" for line in lines)
