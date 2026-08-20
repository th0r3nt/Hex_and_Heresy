"""
Сервис обновления мирового времени, погодных условий, активных событий,
деградации полей брани и реабилитации героев.
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.combat.constants import TimeOfDay
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.utils.event.registry import GameEvents


class EventsStepReport(BaseModel):
    """
    Отчет о результатах шага обновления времени и условий мира.
    """

    ticks_elapsed: int = Field(default=1)
    current_timestamp: str = Field(...)
    time_of_day: TimeOfDay = Field(...)
    is_neon_hours: bool = Field(default=False)
    phase_changed: bool = Field(default=False)

    expired_event_ids: list[str] = Field(default_factory=list)
    decayed_battlefield_ids: list[str] = Field(default_factory=list)
    recovered_hero_ids: list[str] = Field(default_factory=list)


class StrategicEventsService:
    """
    Выполняет первый этап глобального такта: продвижение времени,
    таймеров кризисов, деградации трофеев и выздоровления героев.
    """

    def __init__(self, event_bus: Optional[EventBusProtocol] = None) -> None:
        self._event_bus = event_bus

    async def process_world_events(self, world_state: WorldState) -> EventsStepReport:
        """
        Продвигает состояние мира на 1 глобальный такт (4 часа).
        """
        previous_phase = world_state.time.time_of_day

        # =========================================================
        # Продвижение времени
        # =========================================================

        world_state.time.advance_ticks(1)
        current_phase = world_state.time.time_of_day
        phase_changed = previous_phase != current_phase

        if phase_changed and self._event_bus is not None:
            event_name = (
                GameEvents.Strategic.NEON_HOURS_STARTED
                if world_state.time.is_neon_hours
                else GameEvents.Strategic.GREY_HOURS_STARTED
            )
            await self._event_bus.publish(
                event_name,
                timestamp=world_state.time.format_timestamp(),
                hour=world_state.time.current_hour,
            )

        # =========================================================
        # Обработка активных глобальных событий
        # =========================================================

        expired_event_ids = []
        for event in world_state.active_events:
            event.tick()
            if not event.is_active:
                expired_event_ids.append(event.id)
                if self._event_bus is not None:
                    await self._event_bus.publish(
                        GameEvents.Strategic.EVENT_EXPIRED,
                        event_id=event.id,
                        name=event.name,
                    )

        world_state.cleanup_expired_events()

        # =========================================================
        # Деградация полей брани
        # =========================================================

        decayed_battlefield_ids = []
        for site_id, site in list(world_state.battlefield_sites.items()):
            site.decay_tick()
            if site.is_depleted:
                decayed_battlefield_ids.append(site_id)
        world_state.cleanup_depleted_battlefields()

        # =========================================================
        # Реабилитация героев после тяжелых ранений
        # =========================================================

        recovered_hero_ids = []
        for army in world_state.armies.values():
            for hero in army.heroes:
                if hero.state.is_heavily_wounded:
                    if hero.state.wounded_ticks_remaining > 0:
                        hero.state.wounded_ticks_remaining -= 1

                    if hero.state.wounded_ticks_remaining == 0:
                        hero.state.is_heavily_wounded = False
                        hero.state.current_hp = hero.max_hp
                        recovered_hero_ids.append(hero.id)
                        if self._event_bus is not None:
                            await self._event_bus.publish(
                                GameEvents.Strategic.HERO_RECOVERED,
                                hero_id=hero.id,
                                hero_name=hero.name,
                                faction_id=hero.faction_id,
                            )

        return EventsStepReport(
            ticks_elapsed=1,
            current_timestamp=world_state.time.format_timestamp(),
            time_of_day=current_phase,
            is_neon_hours=world_state.time.is_neon_hours,
            phase_changed=phase_changed,
            expired_event_ids=expired_event_ids,
            decayed_battlefield_ids=decayed_battlefield_ids,
            recovered_hero_ids=recovered_hero_ids,
        )
