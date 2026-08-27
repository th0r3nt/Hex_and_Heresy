"""
Тесты моделей советника: подрезка разговорившейся модели под окно интерфейса,
смысл кнопок выбора и фиксация решения игрока.

Домен здесь стоит на страже контракта интерфейса: окно советника - это угол
экрана, и ни длина текста, ни число кнопок не должны его распирать.
"""

import pytest

from src.back.l01_domain.exceptions.advisor import AdvisorOptionNotFoundError
from src.back.l01_domain.factions.models.advisor import (
    ADVISOR_MAX_OPTIONS,
    ADVISOR_MESSAGE_MAX_LENGTH,
    ADVISOR_OPTION_LABEL_MAX_LENGTH,
    ADVISOR_TITLE_MAX_LENGTH,
    AdvisorAction,
    AdvisorActionOutcome,
    AdvisorActionStatus,
    AdvisorDecision,
    AdvisorOption,
    AdvisorOptionKind,
    AdvisorProposal,
)


def make_proposal(**overrides) -> AdvisorProposal:
    """Предложение поднять налоги - канонический пример из advisor.md."""
    data = {
        "faction_id": "humans",
        "title": "Казна пуста",
        "message": "Мой лорд, налоги в графстве занижены. Предлагаю поднять сбор на 10%.",
        "options": [
            AdvisorOption(label="Принять", kind=AdvisorOptionKind.ACCEPT),
            AdvisorOption(label="Поднять на 5%", kind=AdvisorOptionKind.ADJUST),
            AdvisorOption(label="Отклонить", kind=AdvisorOptionKind.DECLINE),
        ],
    }
    data.update(overrides)
    return AdvisorProposal(**data)


# ==================================================================
# ВАРИАНТЫ ВЫБОРА
# ==================================================================


class TestAdvisorOption:
    def test_option_gets_its_own_id(self):
        """Интерфейс отвечает идентификатором кнопки, а не ее подписью."""
        first = AdvisorOption(label="Принять")
        second = AdvisorOption(label="Принять")

        assert first.id != second.id

    def test_freeform_option_asks_the_player_for_text(self):
        option = AdvisorOption(label="Дать свой ответ", kind=AdvisorOptionKind.FREEFORM)

        assert option.requires_player_text is True
        assert option.is_refusal is False

    def test_decline_option_is_a_refusal(self):
        option = AdvisorOption(label="Отклонить", kind=AdvisorOptionKind.DECLINE)

        assert option.is_refusal is True
        assert option.requires_player_text is False

    def test_accept_is_the_default_kind(self):
        """Модель вправе не указывать вид кнопки: по умолчанию это согласие."""
        assert AdvisorOption(label="Принять").kind == AdvisorOptionKind.ACCEPT

    def test_long_label_is_trimmed_to_fit_the_button(self):
        option = AdvisorOption(label="П" * (ADVISOR_OPTION_LABEL_MAX_LENGTH + 50))

        assert len(option.label) == ADVISOR_OPTION_LABEL_MAX_LENGTH


# ==================================================================
# ПРЕДЛОЖЕНИЕ
# ==================================================================


class TestAdvisorProposal:
    def test_fresh_proposal_is_not_answered(self):
        proposal = make_proposal()

        assert proposal.is_answered is False
        assert proposal.chosen_option_id is None

    def test_choice_is_remembered_and_returns_the_option(self):
        proposal = make_proposal()
        target = proposal.options[1]

        chosen = proposal.choose(target.id)

        assert chosen is target
        assert proposal.chosen_option_id == target.id
        assert proposal.is_answered is True

    def test_unknown_option_is_rejected(self):
        """Кнопки, которой советник не предлагал, для домена не существует."""
        proposal = make_proposal()

        with pytest.raises(AdvisorOptionNotFoundError):
            proposal.choose("opt_never_offered")

        assert proposal.is_answered is False

    def test_get_option_returns_none_for_unknown_id(self):
        assert make_proposal().get_option("opt_missing") is None

    def test_proposal_without_options_is_invalid(self):
        """Окно без кнопок игрок закрыть не сможет."""
        with pytest.raises(ValueError):
            make_proposal(options=[])

    def test_extra_options_do_not_fit_the_window(self):
        """Модель насыпала кнопок сверх контракта - лишние отбрасываются."""
        proposal = make_proposal(
            options=[
                AdvisorOption(label=f"Вариант {index}")
                for index in range(ADVISOR_MAX_OPTIONS + 3)
            ]
        )

        assert len(proposal.options) == ADVISOR_MAX_OPTIONS

    def test_long_message_and_title_are_trimmed(self):
        proposal = make_proposal(
            title="Т" * (ADVISOR_TITLE_MAX_LENGTH + 100),
            message="М" * (ADVISOR_MESSAGE_MAX_LENGTH + 500),
        )

        assert len(proposal.title) == ADVISOR_TITLE_MAX_LENGTH
        assert len(proposal.message) == ADVISOR_MESSAGE_MAX_LENGTH


# ==================================================================
# ДЕЙСТВИЯ И ИТОГ ВЫБОРА
# ==================================================================


class TestAdvisorDecision:
    def _outcome(self, status: AdvisorActionStatus) -> AdvisorActionOutcome:
        return AdvisorActionOutcome(
            action=AdvisorAction(tool_name="change_taxes", arguments={"percent": 10}),
            status=status,
        )

    def test_action_arguments_default_to_empty(self):
        """Схем навыков еще нет: советник вправе позвать навык без параметров."""
        assert AdvisorAction(tool_name="collect_taxes").arguments == {}

    def test_executed_actions_are_separated_from_the_rest(self):
        decision = AdvisorDecision(
            proposal_id="advp_1",
            option_id="opt_1",
            outcomes=[
                self._outcome(AdvisorActionStatus.EXECUTED),
                self._outcome(AdvisorActionStatus.FAILED),
            ],
        )

        assert len(decision.executed_actions) == 1
        assert decision.has_unsupported_actions is False

    def test_unsupported_action_is_visible_to_the_interface(self):
        """
        Навык еще не подключен - игрок должен увидеть совет непримененным,
        а не решить, что налоги уже подняты.
        """
        decision = AdvisorDecision(
            proposal_id="advp_1",
            option_id="opt_1",
            outcomes=[self._outcome(AdvisorActionStatus.NOT_SUPPORTED)],
        )

        assert decision.has_unsupported_actions is True
        assert decision.executed_actions == []

    def test_refusal_leaves_the_decision_empty(self):
        """Отказ игрока не порождает ни реплики, ни действий."""
        decision = AdvisorDecision(proposal_id="advp_1", option_id="opt_1")

        assert decision.advisor_reply == ""
        assert decision.outcomes == []
        assert decision.has_unsupported_actions is False
