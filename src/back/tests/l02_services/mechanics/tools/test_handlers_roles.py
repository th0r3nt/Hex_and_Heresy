"""
Интеграционные тесты навыков ролей-рассказчиков: оружейника, советника,
летописца и мастера игры.

Эти роли не двигают армии - они добавляют в мир сущности и тексты. Проверяем
то же самое: вызов доехал до фасада, мир изменился, событие ушло в шину.
"""

from src.back.l01_domain.army.constants import EquipmentSlot, EquipmentTag
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.world.constants import GlobalEventCategory, GlobalEventScope
from src.back.tests.l02_services.fakes import tool_call
from src.back.utils.event.registry import GameEvents


def draft_call(**overrides):
    """Заказ на тяжелую алебарду с пороховым стволом."""
    arguments = {
        "name": "Алебарда с аркебузой",
        "lore": "Древко, к которому прикручен однозарядный ствол.",
        "slot": EquipmentSlot.WEAPON.value,
        "tier": 3,
        "tags": [EquipmentTag.TWO_HANDED.value, EquipmentTag.HEAVY.value],
        "damage_priority": 8,
        "heavy_weight_tradeoff": 5,
        "master_reply": "Тяжелая выйдет, но я такое уже ковал.",
    }
    arguments.update(overrides)
    return tool_call("draft_blueprint", **arguments)


# ==================================================================
# ОРУЖЕЙНАЯ МАСТЕРСКАЯ
# ==================================================================


class TestGunsmithHandlers:
    async def test_blueprint_reaches_the_arsenal(self, executor, world, context):
        result = await executor.execute(draft_call(), context())

        assert result.success is True
        assert len(world.custom_equipment) == 1
        item = next(iter(world.custom_equipment.values()))
        assert item.name == "Алебарда с аркебузой"
        assert item.is_custom is True
        assert result.data["equipment_id"] == item.id

    async def test_blueprint_is_paid_for_from_the_treasury(self, executor, world, context):
        """Чертеж, попавший в арсенал, уже оплачен разработкой."""
        gold_before = world.get_faction("humans").resources[ResourceType.GOLD]

        await executor.execute(draft_call(), context())

        item = next(iter(world.custom_equipment.values()))
        assert item.cost_gold > 0
        assert world.get_faction("humans").resources[ResourceType.GOLD] == (
            gold_before - item.cost_gold
        )

    async def test_blueprint_beyond_the_treasury_is_refused(self, executor, world, context):
        """Пустая казна - причина отказа, а не повод падать."""
        world.get_faction("humans").resources[ResourceType.GOLD] = 1.0

        result = await executor.execute(draft_call(tier=6), context())

        assert result.success is False
        assert world.custom_equipment == {}

    async def test_rejection_leaves_the_arsenal_untouched(self, executor, world, context):
        result = await executor.execute(
            tool_call(
                "reject_blueprint",
                reason="Заказ противоречит лору",
                master_reply="В Империи за такое жгут.",
            ),
            context(),
        )

        assert result.success is True
        assert result.data["is_approved"] is False
        assert world.custom_equipment == {}


# ==================================================================
# СОВЕТНИК
# ==================================================================


class TestAdvisorHandlers:
    async def test_proposal_waits_for_the_player_in_the_facade(
        self, executor, advisor_facade, world, fake_bus, context
    ):
        world.time.total_ticks = 7

        result = await executor.execute(
            tool_call(
                "propose_advisor_action",
                title="Казна пуста",
                message="Налоги занижены. Предлагаю поднять сбор на 10%.",
                options=["Принять", "Поднять на 5%"],
            ),
            context(),
        )

        pending = advisor_facade.pending_proposals("humans")
        assert result.success is True
        assert len(pending) == 1
        assert pending[0].title == "Казна пуста"
        assert pending[0].tick == 7
        assert GameEvents.Advisor.PROPOSAL_OFFERED in fake_bus.names()

    async def test_player_always_gets_a_way_to_refuse(
        self, executor, advisor_facade, context
    ):
        """Модель предложила только согласия - отказ дорисует сам обработчик."""
        await executor.execute(
            tool_call(
                "propose_advisor_action",
                title="Казна пуста",
                message="Пора поднять налог.",
                options=["Принять", "Поднять на 5%"],
            ),
            context(),
        )

        proposal = advisor_facade.pending_proposals("humans")[0]
        assert any(option.is_refusal for option in proposal.options)


# ==================================================================
# ЛЕТОПИСЕЦ
# ==================================================================


class TestChroniclerHandlers:
    async def test_chronicle_page_is_archived(self, executor, world, context):
        result = await executor.execute(
            tool_call(
                "record_chronicle",
                title="Битва при Низине",
                body="Строй сомкнулся и выстоял.",
                quote="Мы стояли, пока стояли ноги.",
            ),
            context(actor_id="battle_17"),
        )

        assert result.success is True
        assert [entry.title for entry in world.chronicle_entries] == ["Битва при Низине"]
        assert world.chronicle_entries[0].battle_id == "battle_17"

    async def test_the_same_battle_is_not_written_twice(self, executor, world, context):
        """Перегенерация текста не должна плодить свитки об одном сражении."""
        call_context = context(actor_id="battle_17")
        await executor.execute(
            tool_call("record_chronicle", title="Битва при Низине", body="Первый вариант."),
            call_context,
        )

        await executor.execute(
            tool_call("record_chronicle", title="Битва при Низине", body="Второй вариант."),
            call_context,
        )

        assert len(world.chronicle_entries) == 1

    async def test_rumor_goes_out_to_the_world(self, executor, world, context):
        result = await executor.execute(
            tool_call("speak_rumor", text="Говорят, в топях зашевелились мертвецы."),
            context(),
        )

        assert result.success is True
        assert [rumor.text for rumor in world.rumors] == [
            "Говорят, в топях зашевелились мертвецы."
        ]

    async def test_finale_closes_the_party(self, executor, world, context):
        await executor.execute(
            tool_call(
                "record_finale",
                title="Империя выстояла",
                body="Знамена подняты над последней крепостью.",
            ),
            context(),
        )

        assert world.finale is not None
        assert world.finale.title == "Империя выстояла"


# ==================================================================
# МАСТЕР ИГРЫ
# ==================================================================


class TestGameMasterHandlers:
    async def test_commander_joins_the_hiring_pool(
        self, executor, world, fake_bus, context
    ):
        result = await executor.execute(
            tool_call(
                "create_commander",
                name="Ольгерд",
                role_title="Капитан",
                distilled_personality="Стойкий ветеран, говорит скупо.",
                authority=40,
                master_reply="Полководец готов.",
            ),
            context(),
        )

        assert result.success is True
        commanders = list(world.available_commanders.values())
        assert [c.name for c in commanders] == ["Ольгерд"]
        assert commanders[0].characteristics.authority == 40
        assert fake_bus.payload_of(GameEvents.GameMaster.CHARACTER_CREATED)["name"] == (
            "Ольгерд"
        )

    async def test_hero_joins_the_hiring_pool(self, executor, world, context):
        result = await executor.execute(
            tool_call(
                "create_hero",
                name="Илай",
                special_rule="Видение линий смерти",
                max_hp=150.0,
                distilled_personality="Мрачный хирург.",
                master_reply="Герой примкнул к ставке.",
            ),
            context(),
        )

        assert result.success is True
        assert [h.name for h in world.available_heroes.values()] == ["Илай"]

    async def test_invented_traits_do_not_reach_the_character(
        self, executor, world, context
    ):
        """Черта берется из каталога: выдуманную моделью нужно отбросить."""
        await executor.execute(
            tool_call(
                "create_commander",
                name="Ольгерд",
                role_title="Капитан",
                distilled_personality="Стойкий ветеран.",
                trait_ids=["trait_never_existed"],
                master_reply="Готов.",
            ),
            context(),
        )

        assert next(iter(world.available_commanders.values())).traits == []

    async def test_lord_takes_the_throne(self, executor, world, context):
        await executor.execute(
            tool_call(
                "create_lord",
                name="Отто",
                title="Барон",
                archetype_name="Осторожный скопидом",
                distilled_personality="Говорит цифрами.",
                tax_rate_bias=0.5,
                master_reply="Правитель коронован.",
            ),
            context(),
        )

        lord = world.get_faction("humans").lord
        assert lord.name == "Отто"
        assert lord.bias.tax_rate_bias == 0.5

    async def test_world_event_starts_and_spawns_an_army(
        self, executor, world, fake_bus, context
    ):
        armies_before = len(world.armies)

        result = await executor.execute(
            tool_call(
                "trigger_world_event",
                name="Пепельная буря",
                description="Небо заволокло пеплом.",
                category=GlobalEventCategory.WEATHER.value,
                scope=GlobalEventScope.GLOBAL.value,
                duration_ticks=3,
                target_hex_q=2,
                target_hex_r=-1,
                spawn_hostile_army=True,
                neutral_army_name="Шайка пепельных",
            ),
            context(),
        )

        assert result.success is True
        assert [event.name for event in world.active_events] == ["Пепельная буря"]
        assert len(world.armies) == armies_before + 1
        assert result.data["event_id"] == world.active_events[0].id
        assert GameEvents.GameMaster.GLOBAL_EVENT_SPAWNED in fake_bus.names()

    async def test_quiet_event_does_not_spawn_anyone(self, executor, world, context):
        armies_before = len(world.armies)

        await executor.execute(
            tool_call(
                "trigger_world_event",
                name="Неурожай",
                description="Поля выгорели.",
                category=GlobalEventCategory.ECONOMIC.value,
            ),
            context(),
        )

        assert len(world.armies) == armies_before

    async def test_rejected_concept_changes_nothing(self, executor, world, context):
        result = await executor.execute(
            tool_call(
                "reject_creation",
                reason="Концепт противоречит лору",
                master_reply="Таких в этом мире не бывает.",
            ),
            context(),
        )

        assert result.success is True
        assert result.data["is_approved"] is False
        assert world.available_commanders == {}
        assert world.available_heroes == {}
