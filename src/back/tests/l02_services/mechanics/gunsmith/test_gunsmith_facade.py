"""
Тесты фасада мастерской: сборка промпта мастеру, разбор его вердикта,
оплата разработки чертежа и публикация событий.

Мастер - это витрина механики для интерфейса: он оркестрирует балансировщик,
экономиста и реестр, но сам ничего не считает.
"""

import pytest

from src.back.l01_domain.army.constants import EquipmentSlot, EquipmentTag
from src.back.l01_domain.army.models.card.equipment import Equipment, EquipmentStats
from src.back.l01_domain.exceptions.factions import InsufficientResourcesError
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l02_services.mechanics.gunsmith.crafting import StatPriorities
from src.back.l02_services.mechanics.gunsmith.facade import INCOMPLETE_ANSWER_REPLY
from src.back.l02_services.mechanics.gunsmith.validation.balance import EquipmentBalancer
from src.back.l02_services.mechanics.gunsmith.validation.economy import EquipmentEconomist
from src.back.tests.l02_services.fakes import reply
from src.back.utils.event.registry import GameEvents

ORDER = "Тяжелая двуручная алебарда с аркебузой на древке."


def make_draft(
    equipment_id: str = "eq_custom_test",
    cost_gold: float = 100.0,
    cost_material: float = 200.0,
) -> Equipment:
    """Готовый чертеж - как если бы его уже собрал BlueprintRegistry."""
    return Equipment(
        id=equipment_id,
        name="Алебарда с аркебузой",
        lore="Древко, к которому прикручен однозарядный ствол.",
        slot=EquipmentSlot.WEAPON,
        tags={EquipmentTag.TWO_HANDED},
        tier=3,
        stats=EquipmentStats(damage=20.0),
        cost_gold=cost_gold,
        cost_material=cost_material,
        is_custom=True,
    )


# ==================================================================
# СИСТЕМНЫЙ ПРОМПТ МАСТЕРА
# ==================================================================


class TestSystemPrompt:
    @pytest.mark.asyncio
    async def test_prompt_carries_role_economy_and_race(
        self, facade, world, llm, draft_call
    ):
        """
        У каждой расы свой мастер: в промпт уходят его роль, правила экономики
        и лор фракции заказчика (см. docs/game_mechanics/gunsmith.md).
        """
        llm.script(reply("", draft_call()))

        await facade.draft_blueprint(world, "humans", ORDER)

        system_prompt = llm.calls[0]["system_prompt"]
        assert "[base.persona]" in system_prompt
        assert "[base.mechanics.economy]" in system_prompt
        assert "[roles.gunsmith.prompt]" in system_prompt
        assert "[factions.humans]" in system_prompt
        assert "[lore.basic.medium]" in system_prompt

    @pytest.mark.asyncio
    async def test_prompt_carries_the_current_state_of_the_faction(
        self, facade, world, llm, draft_call
    ):
        """Мастер должен видеть казну заказчика, а не выставлять цену вслепую."""
        llm.script(reply("", draft_call()))

        await facade.draft_blueprint(world, "humans", ORDER)

        assert "[gunsmith]" in llm.calls[0]["system_prompt"]

    @pytest.mark.asyncio
    async def test_player_order_reaches_the_user_prompt(
        self, facade, world, llm, draft_call
    ):
        llm.script(reply("", draft_call()))

        await facade.draft_blueprint(world, "humans", ORDER)

        assert ORDER in llm.calls[0]["user_prompt"]

    @pytest.mark.asyncio
    async def test_unknown_faction_is_rejected_before_the_model(
        self, facade, world, llm
    ):
        """Заказ от несуществующей фракции модель даже не увидит."""
        with pytest.raises(ValueError):
            await facade.draft_blueprint(world, "elfs", ORDER)

        assert llm.calls == []


# ==================================================================
# ЧЕРТЕЖ ОДОБРЕН
# ==================================================================


class TestDraftApproved:
    @pytest.mark.asyncio
    async def test_draft_carries_the_masters_reply(
        self, facade, world, llm, draft_call
    ):
        call = draft_call()
        llm.script(reply("", call))

        draft, master_reply = await facade.draft_blueprint(world, "humans", ORDER)

        assert draft is not None
        assert master_reply == call.arguments["master_reply"]

    @pytest.mark.asyncio
    async def test_stats_and_price_come_from_the_math_modules(
        self, facade, world, llm, draft_call
    ):
        """
        Фасад не считает сам: статы приходят от балансировщика,
        цена - от экономиста.
        """
        call = draft_call()
        llm.script(reply("", call))

        draft, _ = await facade.draft_blueprint(world, "humans", ORDER)

        priorities = StatPriorities(
            damage=call.arguments["damage_priority"],
            armor_piercing=call.arguments["armor_piercing_priority"],
            heavy_weight_tradeoff=call.arguments["heavy_weight_tradeoff"],
            clunkiness_tradeoff=call.arguments["clunkiness_tradeoff"],
        )
        expected_stats = EquipmentBalancer.normalize_stats(
            call.arguments["tier"], priorities
        )
        expected_gold, expected_material = EquipmentEconomist.calculate_cost(
            call.arguments["tier"],
            [EquipmentTag(tag) for tag in call.arguments["tags"]],
        )

        assert draft.stats == expected_stats
        assert draft.cost_gold == expected_gold
        assert draft.cost_material == expected_material

    @pytest.mark.asyncio
    async def test_tradeoffs_from_the_order_land_in_the_card(
        self, facade, world, llm, draft_call
    ):
        """Заказ тяжелой алебарды - это заявленные штрафы к скорости и инициативе."""
        llm.script(reply("", draft_call()))

        draft, _ = await facade.draft_blueprint(world, "humans", ORDER)

        assert draft.stats.speed_modifier == -0.1
        assert draft.stats.initiative_modifier == -2
        assert draft.stats.damage > 0

    @pytest.mark.asyncio
    async def test_draft_is_not_registered_until_approved(
        self, facade, world, llm, draft_call
    ):
        """Чертеж - это предложение мастера, а не покупка: казна не тронута."""
        llm.script(reply("", draft_call()))

        await facade.draft_blueprint(world, "humans", ORDER)

        assert world.custom_equipment == {}
        assert world.get_faction("humans").resources[ResourceType.GOLD] == 1000.0

    @pytest.mark.asyncio
    async def test_drafted_event_names_the_item(
        self, facade, world, llm, fake_bus, draft_call
    ):
        llm.script(reply("", draft_call()))

        draft, _ = await facade.draft_blueprint(world, "humans", ORDER)

        assert GameEvents.Gunsmith.BLUEPRINT_DRAFTED in fake_bus.names()
        payload = fake_bus.payload_of(GameEvents.Gunsmith.BLUEPRINT_DRAFTED)
        assert payload["faction_id"] == "humans"
        assert payload["equipment_id"] == draft.id
        assert payload["equipment_name"] == draft.name


# ==================================================================
# МАСТЕР ОТКАЗАЛ
# ==================================================================


class TestDraftRejected:
    @pytest.mark.asyncio
    async def test_rejection_returns_the_reply_without_an_item(
        self, facade, world, llm, reject_call
    ):
        """Заказ против лора расы уходит в отказ - грубый, но без чертежа."""
        call = reject_call()
        llm.script(reply("", call))

        draft, master_reply = await facade.draft_blueprint(
            world, "humans", "Магический посох."
        )

        assert draft is None
        assert master_reply == call.arguments["master_reply"]

    @pytest.mark.asyncio
    async def test_rejected_event_carries_the_reason(
        self, facade, world, llm, fake_bus, reject_call
    ):
        call = reject_call()
        llm.script(reply("", call))

        await facade.draft_blueprint(world, "humans", "Магический посох.")

        assert GameEvents.Gunsmith.BLUEPRINT_REJECTED in fake_bus.names()
        payload = fake_bus.payload_of(GameEvents.Gunsmith.BLUEPRINT_REJECTED)
        assert payload["faction_id"] == "humans"
        assert payload["reason"] == call.arguments["master_reply"]
        assert GameEvents.Gunsmith.BLUEPRINT_DRAFTED not in fake_bus.names()

    @pytest.mark.asyncio
    async def test_priorities_beyond_the_scale_are_treated_as_refusal(
        self, facade, world, llm, draft_call
    ):
        """
        Мастер выставил акценты вне шкалы навыка: считать по такому вызову
        нечего, и чертежа не будет.
        """
        llm.script(reply("", draft_call(damage_priority=99)))

        draft, _ = await facade.draft_blueprint(world, "humans", ORDER)

        assert draft is None

    @pytest.mark.asyncio
    async def test_approval_without_tier_is_treated_as_refusal(
        self, facade, world, llm, draft_call
    ):
        """Без тира неоткуда взять ни бюджет статов, ни цену."""
        llm.script(reply("", draft_call(tier=None)))

        draft, _ = await facade.draft_blueprint(world, "humans", ORDER)

        assert draft is None

    @pytest.mark.asyncio
    async def test_approval_without_slot_is_treated_as_refusal(
        self, facade, world, llm, fake_bus, draft_call
    ):
        """
        Без слота непонятно, куда предмет надевать, и домен такую карточку
        не примет. Игрок должен получить отказ мастера, а не ошибку валидации.
        """
        llm.script(reply("", draft_call(slot=None)))

        draft, master_reply = await facade.draft_blueprint(world, "humans", ORDER)

        assert draft is None
        assert master_reply == INCOMPLETE_ANSWER_REPLY
        assert GameEvents.Gunsmith.BLUEPRINT_REJECTED in fake_bus.names()

    @pytest.mark.asyncio
    async def test_incomplete_answer_never_reaches_the_arsenal(
        self, facade, world, llm, draft_call
    ):
        """Любой недозаполненный вызов мастера оставляет арсенал пустым."""
        for broken in (
            draft_call(damage_priority=99),
            draft_call(tier=None),
            draft_call(slot=None),
            draft_call(name=""),
        ):
            llm.script(reply("", broken))
            draft, _ = await facade.draft_blueprint(world, "humans", ORDER)
            assert draft is None

        assert world.custom_equipment == {}

    @pytest.mark.asyncio
    async def test_master_without_any_tool_call_only_speaks(self, facade, world, llm):
        """Мастер ограничился словами - заказ закрыт без чертежа."""
        llm.script(reply("Такое я не кую."))

        draft, master_reply = await facade.draft_blueprint(world, "humans", ORDER)

        assert draft is None
        assert master_reply == "Такое я не кую."


# ==================================================================
# ОДОБРЕНИЕ ЧЕРТЕЖА ИГРОКОМ
# ==================================================================


class TestApproveBlueprint:
    @pytest.mark.asyncio
    async def test_approval_charges_research_and_registers_the_item(
        self, facade, world, humans
    ):
        """
        Игрок платит за разработку разовую стоимость крафта одной штуки,
        после чего чертеж попадает в арсенал партии.
        """
        draft = make_draft(cost_gold=100.0, cost_material=200.0)

        await facade.approve_blueprint(world, "humans", draft)

        assert humans.resources[ResourceType.GOLD] == 900.0
        assert humans.resources[ResourceType.MATERIAL] == 800.0
        assert world.custom_equipment == {draft.id: draft}

    @pytest.mark.asyncio
    async def test_approved_event_carries_the_price(self, facade, world, fake_bus):
        draft = make_draft(cost_gold=100.0, cost_material=200.0)

        await facade.approve_blueprint(world, "humans", draft)

        payload = fake_bus.payload_of(GameEvents.Gunsmith.BLUEPRINT_APPROVED)
        assert payload["faction_id"] == "humans"
        assert payload["equipment_id"] == draft.id
        assert payload["equipment_name"] == draft.name
        assert payload["cost_gold"] == 100.0
        assert payload["cost_material"] == 200.0

    @pytest.mark.asyncio
    async def test_unknown_faction_cannot_approve(self, facade, world):
        with pytest.raises(ValueError):
            await facade.approve_blueprint(world, "elfs", make_draft())

        assert world.custom_equipment == {}

    @pytest.mark.asyncio
    async def test_empty_treasury_blocks_approval(self, facade, world, humans):
        """Нечем платить - чертеж в арсенал не попадает, склад не тронут."""
        humans.resources[ResourceType.GOLD] = 10.0

        with pytest.raises(InsufficientResourcesError):
            await facade.approve_blueprint(
                world, "humans", make_draft(cost_gold=100.0, cost_material=200.0)
            )

        assert humans.resources[ResourceType.GOLD] == 10.0
        assert humans.resources[ResourceType.MATERIAL] == 1000.0
        assert world.custom_equipment == {}

    @pytest.mark.asyncio
    async def test_empty_warehouse_blocks_approval(self, facade, world, humans, fake_bus):
        """
        Материалов не хватило: предмет не регистрируется и событие не уходит.

        Золото при этом остается в казне целиком - платить за чертеж,
        который так и не собрали, игрок не должен.
        """
        humans.resources[ResourceType.MATERIAL] = 10.0

        with pytest.raises(InsufficientResourcesError):
            await facade.approve_blueprint(
                world, "humans", make_draft(cost_gold=100.0, cost_material=200.0)
            )

        assert humans.resources[ResourceType.GOLD] == 1000.0
        assert humans.resources[ResourceType.MATERIAL] == 10.0
        assert world.custom_equipment == {}
        assert GameEvents.Gunsmith.BLUEPRINT_APPROVED not in fake_bus.names()


# ==================================================================
# СКВОЗНОЙ СЦЕНАРИЙ
# ==================================================================


class TestWorkshopEndToEnd:
    @pytest.mark.asyncio
    async def test_order_becomes_an_item_in_the_arsenal(
        self, facade, world, humans, llm, fake_bus, draft_call
    ):
        """Путь заказа целиком: текст игрока -> чертеж -> оплата -> арсенал."""
        llm.script(reply("", draft_call()))

        draft, _ = await facade.draft_blueprint(world, "humans", ORDER)
        await facade.approve_blueprint(world, "humans", draft)

        assert world.custom_equipment[draft.id] is draft
        assert draft.is_custom is True
        assert humans.resources[ResourceType.GOLD] == 1000.0 - draft.cost_gold
        assert humans.resources[ResourceType.MATERIAL] == 1000.0 - draft.cost_material
        assert fake_bus.names() == [
            GameEvents.Gunsmith.BLUEPRINT_DRAFTED,
            GameEvents.Gunsmith.BLUEPRINT_APPROVED,
        ]

    @pytest.mark.asyncio
    async def test_second_order_does_not_overwrite_the_first(
        self, facade, world, llm, draft_call
    ):
        """У каждого чертежа свой идентификатор - арсенал копится."""
        llm.script(reply("", draft_call()))
        first, _ = await facade.draft_blueprint(world, "humans", ORDER)
        await facade.approve_blueprint(world, "humans", first)

        llm.script(reply("", draft_call(name="Крепостной гвоздомет", tier=1)))
        second, _ = await facade.draft_blueprint(world, "humans", "Что-нибудь попроще.")
        await facade.approve_blueprint(world, "humans", second)

        assert len(world.custom_equipment) == 2
        assert {item.name for item in world.custom_equipment.values()} == {
            "Алебарда с аркебузой",
            "Крепостной гвоздомет",
        }
