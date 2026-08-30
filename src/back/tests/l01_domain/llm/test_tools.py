"""
Тесты схем параметров инструментов по всем направлениям.
"""

from src.back.l01_domain.llm.tools.definitions import (
    advisor as adv_tools,
    chronicler as chr_tools,
    diplomacy as dip_tools,
    game_master as gm_tools,
    general as gen_tools,
    gunsmith as gun_tools,
    strategic as str_tools,
)
from src.back.l01_domain.army.constants import EquipmentSlot, EquipmentTag
from src.back.l01_domain.combat.constants import ReactionType, TacticalMovementPace
from src.back.l01_domain.factions.constants import (
    BorderTownResolutionType,
    NegotiationMode,
    ResourceType,
)
from src.back.l01_domain.llm.models.tools import ToolDefinition
from src.back.l01_domain.llm.tools.definitions import (
    tactical as tac_tools,
)
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.maps.models.tactical import CellCoordinates
from src.back.l01_domain.world.constants import GlobalEventCategory, GlobalEventScope


class TestGeneralTools:
    def test_reply_and_stay_silent_definitions(self):
        assert isinstance(gen_tools.REPLY, ToolDefinition)
        assert isinstance(gen_tools.STAY_SILENT, ToolDefinition)

        reply_params = gen_tools.ReplyParams(text="Слушаюсь.")
        assert reply_params.text == "Слушаюсь."

        silent_params = gen_tools.StaySilentParams(reason="Нет повода отвечать.")
        assert silent_params.reason == "Нет повода отвечать."


class TestStrategicTools:
    def test_march_params_to_hex_coordinates(self):
        params = str_tools.OrderArmyMarchParams(army_id="army_1", target_q=3, target_r=-2)
        coord = params.to_target_hex()

        assert isinstance(coord, HexCoordinates)
        assert coord.to_axial() == (3, -2)

    def test_expedition_params_to_hex_coordinates(self):
        params = str_tools.DispatchExpeditionParams(
            squad_id="sq_1", target_q=4, target_r=-1, home_q=0, home_r=0
        )
        assert params.to_target_hex() == HexCoordinates.from_axial(4, -1)
        assert params.to_home_hex() == HexCoordinates.from_axial(0, 0)

    def test_found_town_and_claim_land_params(self):
        found = str_tools.FoundBorderTownParams(name="Острог", target_q=2, target_r=1)
        assert found.to_target_hex() == HexCoordinates.from_axial(2, 1)

        claim = str_tools.ClaimBorderLandParams(town_id="t1", target_q=1, target_r=1)
        assert claim.to_target_hex() == HexCoordinates.from_axial(1, 1)

    def test_resolve_town_params(self):
        params = str_tools.ResolveBorderTownParams(
            town_id="town_1",
            army_id="army_1",
            resolution_type=BorderTownResolutionType.PILLAGE,
        )
        assert params.resolution_type == BorderTownResolutionType.PILLAGE


class TestTacticalTools:
    def test_order_squad_move_and_hold_params(self):
        move = tac_tools.OrderSquadMoveParams(
            squad_id="sq_1", target_x=5, target_y=3, pace=TacticalMovementPace.CHARGE
        )
        assert move.to_target_cell() == CellCoordinates(x=5, y=3)
        assert move.pace == TacticalMovementPace.CHARGE

        hold = tac_tools.OrderSquadHoldParams(squad_id="sq_2")
        assert hold.squad_id == "sq_2"

    def test_order_squad_reaction_params(self):
        reaction_with_target = tac_tools.OrderSquadReactionParams(
            squad_id="sq_1", reaction=ReactionType.ACCEPT_CHARGE, target_x=2, target_y=1
        )
        assert reaction_with_target.to_target_cell() == CellCoordinates(x=2, y=1)

        reaction_inplace = tac_tools.OrderSquadReactionParams(
            squad_id="sq_1", reaction=ReactionType.FLEE
        )
        assert reaction_inplace.to_target_cell() is None


class TestDiplomacyTools:
    def test_propose_trade_and_rights_of_passage_params(self):
        trade = dip_tools.ProposeTradeParams(
            give_resource=ResourceType.FOOD,
            give_amount=50.0,
            get_resource=ResourceType.GOLD,
            get_amount=25.0,
            duration_turns=3,
        )
        assert trade.give_amount == 50.0

        passage = dip_tools.EstablishRightOfPassageParams(
            toll_gold_per_crossing=15.0, allowed_hex_ids=["0,0", "1,-1"]
        )
        assert passage.toll_gold_per_crossing == 15.0

    def test_send_ambassador_params(self):
        amb = dip_tools.SendAmbassadorParams(
            name="Валленштейн",
            target_faction_id="elfs",
            negotiation_mode=NegotiationMode.AUTOMATIC,
            directive="Добиться союза.",
        )
        assert amb.name == "Валленштейн"
        assert amb.negotiation_mode == NegotiationMode.AUTOMATIC


class TestGunsmithTools:
    def test_draft_blueprint_params(self):
        draft = gun_tools.DraftBlueprintParams(
            name="Пороховой мушкет с штыком",
            slot=EquipmentSlot.WEAPON,
            tier=2,
            tags=[EquipmentTag.TWO_HANDED, EquipmentTag.BLACKPOWDER],
            damage_priority=7,
            heavy_weight_tradeoff=3,
            master_reply="Выкую за два такта.",
        )
        assert draft.slot == EquipmentSlot.WEAPON
        assert draft.damage_priority == 7

    def test_reject_blueprint_params(self):
        reject = gun_tools.RejectBlueprintParams(
            reason="Ересь", master_reply="Инквизиция не одобрит."
        )
        assert reject.reason == "Ересь"


class TestAdvisorTools:
    def test_propose_advisor_action_params(self):
        proposal = adv_tools.ProposeAdvisorActionParams(
            title="Казна пустеет",
            message="Пора повысить налог.",
            options=["Да", "Нет"],
            action_tool_name="set_tax_rate",
            action_arguments={"rate": 1.2},
        )
        assert len(proposal.options) == 2
        assert proposal.action_tool_name == "set_tax_rate"


class TestChroniclerTools:
    def test_chronicler_params(self):
        chronicle = chr_tools.RecordChronicleParams(
            title="Битва при Низине", body="Строй сомкнулся."
        )
        assert chronicle.title == "Битва при Низине"

        epitaph = chr_tools.RecordEpitaphParams(
            title="Павшие стражи", epitaph="Они пали у ворот."
        )
        assert epitaph.title == "Павшие стражи"

        rumor = chr_tools.SpeakRumorParams(text="Говорят, в топях зашевелились мертвецы.")
        assert "топях" in rumor.text


class TestGameMasterTools:
    def test_create_commander_and_hero_params(self):
        cmd = gm_tools.CreateCommanderParams(
            name="Ольгерд",
            role_title="Капитан",
            distilled_personality="Стойкий ветеран.",
            master_reply="Полководец готов.",
        )
        assert cmd.name == "Ольгерд"

        hero = gm_tools.CreateHeroParams(
            name="Илай",
            special_rule="Видение линий смерти",
            max_hp=150.0,
            distilled_personality="Мрачный хирург.",
            master_reply="Герой примкнул к ставке.",
        )
        assert hero.max_hp == 150.0

    def test_trigger_world_event_params(self):
        event = gm_tools.TriggerWorldEventParams(
            name="Пепельная буря",
            description="Небо заволокло пеплом.",
            category=GlobalEventCategory.WEATHER,
            scope=GlobalEventScope.GLOBAL,
        )
        assert event.category == GlobalEventCategory.WEATHER
        assert event.scope == GlobalEventScope.GLOBAL
