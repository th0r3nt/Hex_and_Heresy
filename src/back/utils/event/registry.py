"""
Централизованный реестр типизированных событий игры (Pub/Sub).
Содержит типизированные перечисления событий по доменным областям.
"""

from enum import Enum

# ==================================================================
# ИГРОВОЙ ПОТОК (GAMEFLOW)
# ==================================================================


class GameFlowEvents(str, Enum):
    """События смены высокоуровневых экранов и режимов конечного автомата."""

    STATE_CHANGED = "gameflow.state_changed"
    GAME_STARTED = "gameflow.game_started"
    GAME_LOADED = "gameflow.game_loaded"
    GAME_SAVED = "gameflow.game_saved"
    GAME_OVER = "gameflow.game_over"


# ==================================================================
# СТРАТЕГИЧЕСКАЯ КАРТА И ВРЕМЯ (STRATEGIC)
# ==================================================================


class StrategicEvents(str, Enum):
    """События макро-уровня: такты, суточные циклы, перемещения, засады и депеши."""

    TURN_STARTED = "strategic.turn_started"
    TURN_COMPLETED = "strategic.turn_completed"
    GREY_HOURS_STARTED = "strategic.grey_hours_started"
    NEON_HOURS_STARTED = "strategic.neon_hours_started"
    ENCOUNTER_DETECTED = "strategic.encounter_detected"
    DISPATCH_DELIVERED = "strategic.dispatch_delivered"
    DISPATCH_INTERCEPTED = "strategic.dispatch_intercepted"
    AMBASSADOR_ARRIVED = "strategic.ambassador_arrived"
    HERO_RECOVERED = "strategic.hero_recovered"
    EVENT_EXPIRED = "strategic.event_expired"

    # Гарнизоны земель: ротация войск и городское ополчение
    SQUAD_STATIONED = "strategic.squad_stationed"
    SQUAD_UNSTATIONED = "strategic.squad_unstationed"
    GARRISON_RAISED = "strategic.garrison_raised"
    MILITIA_CAPACITY_SYNCED = "strategic.militia_capacity_synced"
    MILITIA_REPLENISHED = "strategic.militia_replenished"


# ==================================================================
# ЭКОНОМИКА, СТРОИТЕЛЬСТВО И РАБОЧИЕ (ECONOMY)
# ==================================================================


class EconomyEvents(str, Enum):
    """События производства, возведения зданий, стационарных рабочих, экспедиций и снабжения."""

    # Строительство
    BUILDING_STARTED = "economy.building_started"
    BUILDING_COMPLETED = "economy.building_completed"
    BUILDING_UPGRADED = "economy.building_upgraded"
    BUILDING_DEMOLISHED = "economy.building_demolished"

    # Стационарные рабочие
    WORKER_ASSIGNED = "economy.worker_assigned"
    WORKER_WARMUP_COMPLETED = "economy.worker_warmup_completed"
    WORKER_UNASSIGNED = "economy.worker_unassigned"

    # Экспедиции караванов
    EXPEDITION_DISPATCHED = "economy.expedition_dispatched"
    EXPEDITION_MINING_STARTED = "economy.expedition_mining_started"
    EXPEDITION_RETURNING = "economy.expedition_returning"
    EXPEDITION_RETURNED = "economy.expedition_returned"
    EXPEDITION_LOST = "economy.expedition_lost"

    # Кризисы снабжения
    FAMINE_OCCURRED = "economy.famine_occurred"
    SQUAD_DESERTED = "economy.squad_deserted"

    # Налоги и настроения подданных
    TAXES_COLLECTED = "economy.taxes_collected"
    TAX_RATE_CHANGED = "economy.tax_rate_changed"
    WORKERS_ON_STRIKE = "economy.workers_on_strike"
    TAX_RIOT_ERUPTED = "economy.tax_riot_erupted"


# ==================================================================
# 4. ТАКТИЧЕСКИЙ БОЙ
# ==================================================================


class TacticalEvents(str, Enum):
    """События на тактической сетке: фазы раундов, паника, кучи трупов и ранения героев."""

    BATTLE_STARTED = "tactical.battle_started"
    TURN_STARTED = "tactical.turn_started"
    TURN_COMPLETED = "tactical.turn_completed"
    PHASE_ADVANCED = "tactical.phase_advanced"
    SQUAD_PANICKED = "tactical.squad_panicked"
    CHAIN_PANIC_TRIGGERED = "tactical.chain_panic_triggered"
    CORPSE_PILE_FORMED = "tactical.corpse_pile_formed"
    HERO_WOUNDED = "tactical.hero_wounded"
    HERO_SLAIN = "tactical.hero_slain"
    BATTLE_COMPLETED = "tactical.battle_completed"


# ==================================================================
# 5. ДИПЛОМАТИЯ (DIPLOMACY)
# ==================================================================


class DiplomacyEvents(str, Enum):
    """События дипломатических отношений, пактов, дани и переговоров."""

    WAR_DECLARED = "diplomacy.war_declared"
    PEACE_SIGNED = "diplomacy.peace_signed"
    TRADE_AGREED = "diplomacy.trade_agreed"
    PACT_FORMED = "diplomacy.pact_formed"
    PACT_BROKEN = "diplomacy.pact_broken"
    TRIBUTE_DEMANDED = "diplomacy.tribute_demanded"
    TRIBUTE_PAID = "diplomacy.tribute_paid"
    AMBASSADOR_EXECUTED = "diplomacy.ambassador_executed"
    DISPATCH_SENT = "diplomacy.dispatch_sent"
    AMBASSADOR_SENT = "diplomacy.ambassador_sent"


# ==================================================================
# 6. ЛЕТОПИСЕЦ И ВЕТЕРАНСТВО (CHRONICLER)
# ==================================================================


class ChroniclerEvents(str, Enum):
    """События генерации хроник, некрологов, слухов и повышения ветеранов."""

    BATTLE_RECORDED = "chronicler.battle_recorded"
    FALLEN_RECORDED = "chronicler.fallen_recorded"
    RUMOR_GENERATED = "chronicler.rumor_generated"
    SQUAD_PROMOTED = "chronicler.squad_promoted"


# ==================================================================
# 7. ОРУЖЕЙНИК (GUNSMITH)
# ==================================================================


class GunsmithEvents(str, Enum):
    """События крафта кастомного снаряжения и чертежей."""

    BLUEPRINT_DRAFTED = "gunsmith.blueprint_drafted"
    BLUEPRINT_APPROVED = "gunsmith.blueprint_approved"
    BLUEPRINT_REJECTED = "gunsmith.blueprint_rejected"


# ==================================================================
# 8. МАСТЕР ИГРЫ (GAME MASTER)
# ==================================================================


class GameMasterEvents(str, Enum):
    """События случайных глобальных кризисов и создания кастомных персонажей."""

    GLOBAL_EVENT_SPAWNED = "game_master.global_event_spawned"
    GLOBAL_EVENT_RESOLVED = "game_master.global_event_resolved"
    CHARACTER_CREATED = "game_master.character_created"


# ==================================================================
# 9. СОВЕТНИК (ADVISOR)
# ==================================================================


class AdvisorEvents(str, Enum):
    """События окна советника: непрошеные предложения и их последствия."""

    PROPOSAL_OFFERED = "advisor.proposal_offered"
    PROPOSAL_ANSWERED = "advisor.proposal_answered"
    ACTION_EXECUTED = "advisor.action_executed"


# ==================================================================
# ЕДИНЫЙ КОНТЕЙНЕР СОБЫТИЙ
# ==================================================================


class GameEvents:
    """Единое пространство имен для доступа ко всем событиям игры."""

    GameFlow = GameFlowEvents
    Strategic = StrategicEvents
    Economy = EconomyEvents
    Tactical = TacticalEvents
    Diplomacy = DiplomacyEvents
    Chronicler = ChroniclerEvents
    Gunsmith = GunsmithEvents
    GameMaster = GameMasterEvents
    Advisor = AdvisorEvents
