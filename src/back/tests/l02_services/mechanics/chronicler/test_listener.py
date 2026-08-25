"""
Тесты подписчика летописца: подписки на живой шине событий, фоновая
генерация и связка с тактическим оркестратором.
"""

import pytest

from src.back.l01_domain.combat.models.reports import MeleeCombatReport
from src.back.l01_domain.exceptions.llm import LLMRequestFailedError
from src.back.l02_services.mechanics.chronicler.facade import ChroniclerFacade
from src.back.l02_services.mechanics.chronicler.listener import ChroniclerListener
from src.back.l02_services.turns.tactical.orchestrator import TacticalTurnOrchestrator
from src.back.utils.event.bus import EventBus
from src.back.utils.event.registry import GameEvents


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
def facade(fake_llm, fake_repository) -> ChroniclerFacade:
    return ChroniclerFacade(llm_client=fake_llm, repository=fake_repository)


@pytest.fixture
def listener(facade, world) -> ChroniclerListener:
    """
    Синхронный режим: тесту нужен детерминированный порядок, а не гонка с
    фоновой задачей.
    """
    listener = ChroniclerListener(facade, run_in_background=False)
    listener.bind_world_state(world)
    return listener


class TestSubscriptions:
    def test_register_and_unregister(self, listener, bus):
        listener.register(bus)

        assert bus.listener_count(GameEvents.Tactical.BATTLE_STARTED) == 1
        assert bus.listener_count(GameEvents.Tactical.TURN_COMPLETED) == 1
        assert bus.listener_count(GameEvents.Tactical.BATTLE_COMPLETED) == 1
        assert bus.listener_count(GameEvents.Strategic.TURN_COMPLETED) == 1

        listener.unregister(bus)

        assert bus.listener_count(GameEvents.Tactical.BATTLE_COMPLETED) == 0

    @pytest.mark.asyncio
    async def test_events_before_binding_do_not_crash(self, facade, bus, make_report):
        unbound = ChroniclerListener(facade, run_in_background=False)
        unbound.register(bus)

        await bus.publish(
            GameEvents.Tactical.BATTLE_COMPLETED,
            battle_id="battle_1",
            report=make_report(is_battle_finished=True),
        )
        await bus.publish(GameEvents.Strategic.TURN_COMPLETED)


class TestBattleFlowOverTheBus:
    @pytest.mark.asyncio
    async def test_full_battle_produces_a_chronicle(
        self, listener, bus, world, battle_state, battle_squads, battle_hex, make_report
    ):
        listener.register(bus)

        await bus.publish(
            GameEvents.Tactical.BATTLE_STARTED,
            battle_id=battle_state.id,
            battle_state=battle_state,
            squads=battle_squads,
            strategic_hex=battle_hex,
        )
        await bus.publish(
            GameEvents.Tactical.TURN_COMPLETED,
            battle_id=battle_state.id,
            tick=1,
            report=make_report(
                tick=1,
                melee_reports=[
                    MeleeCombatReport(
                        attacker_squad_id="atk_0", defender_squad_id="def_0", kills=40
                    )
                ],
            ),
        )

        final = make_report(
            tick=2,
            melee_reports=[
                MeleeCombatReport(
                    attacker_squad_id="atk_0", defender_squad_id=f"def_{i}", kills=100
                )
                for i in range(6)
            ],
            is_battle_finished=True,
            victor_faction_id="humans",
        )
        await bus.publish(
            GameEvents.Tactical.TURN_COMPLETED,
            battle_id=battle_state.id,
            tick=2,
            report=final,
        )
        await bus.publish(
            GameEvents.Tactical.BATTLE_COMPLETED,
            battle_id=battle_state.id,
            victor_faction_id="humans",
            report=final,
        )

        assert len(world.chronicle_entries) == 1
        assert world.chronicle_entries[0].battle_id == battle_state.id

    @pytest.mark.asyncio
    async def test_final_report_is_counted_once(
        self, listener, bus, world, battle_state, battle_squads, battle_hex,
        make_report, fake_llm,
    ):
        """
        Последний раунд приезжает дважды - раундом и концом боя. Числа от
        этого удваиваться не должны.
        """
        listener.register(bus)
        await bus.publish(
            GameEvents.Tactical.BATTLE_STARTED,
            battle_id=battle_state.id,
            battle_state=battle_state,
            squads=battle_squads,
            strategic_hex=battle_hex,
        )

        final = make_report(
            tick=1,
            melee_reports=[
                MeleeCombatReport(
                    attacker_squad_id="atk_0", defender_squad_id="def_0", kills=50
                )
            ],
            is_battle_finished=True,
            victor_faction_id="humans",
        )
        await bus.publish(
            GameEvents.Tactical.TURN_COMPLETED, battle_id=battle_state.id, tick=1, report=final
        )
        await bus.publish(
            GameEvents.Tactical.BATTLE_COMPLETED, battle_id=battle_state.id, report=final
        )

        user_prompt = fake_llm.structured_calls[0]["user_prompt"]
        assert "погибло 50" in user_prompt

    @pytest.mark.asyncio
    async def test_hero_death_reaches_the_dossier(
        self, listener, bus, world, battle_state, battle_squads, battle_hex,
        make_report, fake_llm,
    ):
        listener.register(bus)
        await bus.publish(
            GameEvents.Tactical.BATTLE_STARTED,
            battle_id=battle_state.id,
            battle_state=battle_state,
            squads=battle_squads,
            strategic_hex=battle_hex,
        )

        await bus.publish(
            GameEvents.Tactical.HERO_SLAIN,
            battle_id=battle_state.id,
            hero_name="Гром Железное брюхо",
        )

        await bus.publish(
            GameEvents.Tactical.BATTLE_COMPLETED,
            battle_id=battle_state.id,
            report=make_report(tick=1, is_battle_finished=True, victor_faction_id="humans"),
        )

        # Гибель героя делает достойной летописи даже мелкую стычку,
        # а его имя обязано доехать до модели вместе со сводкой боя
        assert len(world.chronicle_entries) == 1
        assert "Гром Железное брюхо" in fake_llm.structured_calls[0]["user_prompt"]


class TestStrategicSilence:
    @pytest.mark.asyncio
    async def test_ticks_of_silence_are_counted(self, listener, bus, world):
        listener.register(bus)

        await bus.publish(GameEvents.Strategic.TURN_COMPLETED)
        await bus.publish(GameEvents.Strategic.TURN_COMPLETED)

        assert world.ticks_since_last_battle == 2

    @pytest.mark.asyncio
    async def test_rumor_appears_after_the_threshold(self, listener, bus, world):
        listener.register(bus)

        for _ in range(3):
            await bus.publish(GameEvents.Strategic.TURN_COMPLETED)

        assert len(world.rumors) == 1


class TestBackgroundMode:
    @pytest.mark.asyncio
    async def test_chronicle_is_written_in_background(
        self, facade, world, bus, battle_state, battle_squads, battle_hex, make_report
    ):
        listener = ChroniclerListener(facade, run_in_background=True)
        listener.bind_world_state(world)
        listener.register(bus)

        await bus.publish(
            GameEvents.Tactical.BATTLE_STARTED,
            battle_id=battle_state.id,
            battle_state=battle_state,
            squads=battle_squads,
            strategic_hex=battle_hex,
        )
        await bus.publish(
            GameEvents.Tactical.BATTLE_COMPLETED,
            battle_id=battle_state.id,
            report=make_report(tick=1, is_battle_finished=True, victor_faction_id="humans"),
        )

        await listener.wait_for_pending()

        assert len(world.chronicle_entries) == 1

    @pytest.mark.asyncio
    async def test_broken_model_does_not_kill_the_task(
        self, world, bus, battle_state, battle_squads, battle_hex, make_report
    ):
        class BrokenLLM:
            async def generate_text(self, *args, **kwargs):
                raise LLMRequestFailedError("local", "model", "нет сети")

            async def generate_structured(self, *args, **kwargs):
                raise LLMRequestFailedError("local", "model", "нет сети")

        listener = ChroniclerListener(
            ChroniclerFacade(llm_client=BrokenLLM()), run_in_background=True
        )
        listener.bind_world_state(world)
        listener.register(bus)

        await bus.publish(
            GameEvents.Tactical.BATTLE_STARTED,
            battle_id=battle_state.id,
            battle_state=battle_state,
            squads=battle_squads,
            strategic_hex=battle_hex,
        )
        await bus.publish(
            GameEvents.Tactical.BATTLE_COMPLETED,
            battle_id=battle_state.id,
            report=make_report(tick=1, is_battle_finished=True),
        )
        await listener.wait_for_pending()

        assert world.chronicle_entries == []


class TestWithTacticalOrchestrator:
    @pytest.mark.asyncio
    async def test_orchestrator_feeds_the_chronicler(
        self, listener, bus, world, battle_state, battle_squads, battle_hex
    ):
        """
        Настоящий оркестратор боя должен сам сообщить летописцу и о начале
        сражения, и о каждом раунде.
        """
        listener.register(bus)
        orchestrator = TacticalTurnOrchestrator(event_bus=bus)

        # Обороняющиеся уже мертвы: бой закончится первым же раундом
        for squad_id in battle_state.defender_squad_ids:
            battle_squads[squad_id].state.unit_count = 0

        report = await orchestrator.execute_turn(
            battle_state=battle_state,
            squads=battle_squads,
            strategic_hex=battle_hex,
        )

        assert report.is_battle_finished is True
        assert len(world.chronicle_entries) == 1
        assert world.ticks_since_last_battle == 0
