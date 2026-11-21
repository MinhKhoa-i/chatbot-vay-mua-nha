from decimal import Decimal

import pytest

from app.domain.entities.conversation_memory import ConversationMemory
from app.infrastructure.db.conversation_memory_codec import (
    decode_conversation_memory,
    encode_conversation_memory,
)
from app.infrastructure.security.payload_cipher import PayloadCipherError


def test_empty_legacy_profile_decodes_to_empty_memory():
    assert decode_conversation_memory({"schema_version": 1, "slots": {}}) == ConversationMemory()


def test_memory_round_trips_decimal_values_and_provenance():
    memory = ConversationMemory(
        amount=1_000_000_000,
        years=20,
        user_provided_rate=Decimal("8.50"),
        promo_rate=Decimal("5.9"),
        promo_duration_months=12,
        repayment_method="reducing_balance",
        verified_rate=Decimal("8.25"),
        property_value=2_000_000_000,
        prepay_month=60,
        grace_period_months=6,
        base_rate=Decimal("7.5"),
        assumed_floating_rate=Decimal("10"),
        source_seq=3,
    )

    assert decode_conversation_memory({"conversation_memory": encode_conversation_memory(memory)}) == memory


def test_memory_codec_migrates_schema_v1_memory_with_empty_new_fields():
    legacy = {
        "schema_version": 1,
        "amount": 1_000_000_000,
        "years": 20,
        "user_provided_rate": "8.5",
        "promo_rate": None,
        "promo_duration_months": None,
        "repayment_method": "annuity",
        "verified_rate": None,
        "source_seq": 3,
    }

    decoded = decode_conversation_memory({"conversation_memory": legacy})

    assert decoded.amount == 1_000_000_000
    assert decoded.user_provided_rate == Decimal("8.5")
    assert decoded.property_value is None
    assert decoded.assumed_floating_rate is None
    assert encode_conversation_memory(decoded)["schema_version"] == 2


def test_memory_codec_rejects_unknown_keys_and_non_string_decimal():
    encoded = encode_conversation_memory(ConversationMemory(user_provided_rate=Decimal("8.5")))

    with pytest.raises(PayloadCipherError):
        decode_conversation_memory({"conversation_memory": {**encoded, "unexpected": True}})
    with pytest.raises(PayloadCipherError):
        decode_conversation_memory({"conversation_memory": {**encoded, "user_provided_rate": 8.5}})


def test_memory_merges_estimate_values_without_erasing_unknown_facts():
    previous = ConversationMemory(
        amount=1_000_000_000,
        years=20,
        user_provided_rate=Decimal("8.5"),
        verified_rate=Decimal("8.25"),
    )
    updated = previous.merge_estimate(
        amount=1_200_000_000,
        years=25,
        user_provided_rate=Decimal("9"),
        promo_rate=None,
        promo_duration_months=0,
        repayment_method="annuity",
        source_seq=5,
    )

    assert updated.amount == 1_200_000_000
    assert updated.years == 25
    assert updated.user_provided_rate == Decimal("9")
    assert updated.verified_rate == Decimal("8.25")
    assert updated.promo_duration_months == 0
    assert updated.promo_rate is None
    assert updated.source_seq == 5


def test_estimate_term_change_clears_bank_months_that_no_longer_fit():
    previous = ConversationMemory(
        years=20,
        prepay_month=180,
        grace_period_months=120,
    )

    updated = previous.merge_estimate(
        amount=None,
        years=10,
        user_provided_rate=None,
        promo_rate=None,
        promo_duration_months=None,
        repayment_method=None,
        source_seq=2,
    )

    assert updated.years == 10
    assert updated.prepay_month is None
    assert updated.grace_period_months is None


def test_bank_comparison_term_change_clears_months_that_no_longer_fit():
    previous = ConversationMemory(
        years=20,
        prepay_month=180,
        grace_period_months=120,
    )

    updated = previous.merge_bank_comparison(
        amount=None,
        years=10,
        repayment_method=None,
        source_seq=2,
    )

    assert updated.years == 10
    assert updated.prepay_month is None
    assert updated.grace_period_months == 0


def test_partial_promo_facts_are_retained_as_unverified_context():
    rate_context = ConversationMemory(promo_rate=Decimal("5.9")).to_prompt_context()
    duration_context = ConversationMemory(promo_duration_months=12).to_prompt_context()

    assert "5,9%/năm" in rate_context
    assert "chưa rõ thời gian áp dụng" in rate_context
    assert "12 tháng" in duration_context
    assert "chưa rõ mức lãi suất" in duration_context


def test_memory_merges_shared_bank_comparison_facts_without_erasing_estimate_facts():
    previous = ConversationMemory(
        amount=1_000_000_000,
        years=20,
        user_provided_rate=Decimal("8.5"),
        repayment_method="annuity",
    )

    updated = previous.merge_bank_comparison(
        amount=1_200_000_000,
        years=25,
        repayment_method="reducing_balance",
        source_seq=8,
    )

    assert updated.amount == 1_200_000_000
    assert updated.years == 25
    assert updated.repayment_method == "reducing_balance"
    assert updated.user_provided_rate == Decimal("8.5")
    assert updated.source_seq == 8


def test_bank_comparison_scenario_facts_are_saved_and_prompted():
    memory = ConversationMemory().merge_bank_comparison(
        amount=1_000_000_000,
        years=20,
        repayment_method="annuity",
        property_value=2_000_000_000,
        prepay_month=60,
        grace_period_months=6,
        base_rate=Decimal("7.5"),
        assumed_floating_rate=Decimal("10"),
        source_seq=4,
    )

    context = memory.to_prompt_context()

    assert memory.property_value == 2_000_000_000
    assert memory.prepay_month == 60
    assert memory.grace_period_months == 6
    assert memory.base_rate == Decimal("7.5")
    assert memory.assumed_floating_rate == Decimal("10")
    assert "2,000,000,000 VND" in context
    assert "tháng 60" in context
    assert "6 tháng" in context
    assert "7,5%/năm" in context
    assert "10%/năm" in context
    assert "Lãi suất cơ sở giả định" in context
    assert "Lãi suất thả nổi giả định" in context


def test_new_bank_comparison_scenario_does_not_inherit_scenario_specific_facts():
    previous = ConversationMemory(
        amount=1_000_000_000,
        years=20,
        repayment_method="reducing_balance",
        property_value=2_000_000_000,
        prepay_month=60,
        grace_period_months=6,
        base_rate=Decimal("7.5"),
        assumed_floating_rate=Decimal("10"),
    )

    bank_compare = previous.to_bank_compare_session()
    updated = previous.merge_bank_comparison(
        amount=1_500_000_000,
        years=25,
        repayment_method=None,
        source_seq=9,
    )

    assert bank_compare.amount == 1_000_000_000
    assert bank_compare.years == 20
    assert bank_compare.property_value is None
    assert bank_compare.prepay_month is None
    assert bank_compare.grace_period_months == 0
    assert bank_compare.base_rate is None
    assert bank_compare.assumed_floating_rate is None
    assert updated.amount == 1_500_000_000
    assert updated.years == 25
    assert updated.repayment_method == "reducing_balance"
    assert updated.property_value is None
    assert updated.prepay_month is None
    assert updated.grace_period_months == 0
    assert updated.base_rate is None
    assert updated.assumed_floating_rate is None
    assert updated.user_provided_rate is None
    assert updated.to_bank_compare_session().property_value is None
    assert updated.to_bank_compare_session().assumed_floating_rate is None
    assert updated.to_bank_compare_session().method == "reducing_balance"
    assert updated.to_bank_compare_session().method_explicit is True


def test_memory_does_not_turn_bank_comparison_default_method_into_user_fact():
    bank_compare = ConversationMemory().to_bank_compare_session()

    assert bank_compare.method == "annuity"
    assert bank_compare.method_explicit is False

    updated = ConversationMemory().merge_bank_comparison(
        amount=1_000_000_000,
        years=20,
        repayment_method=None,
        source_seq=1,
    )

    assert updated.repayment_method is None
    assert updated.to_estimate_session().method is None


def test_explicit_bank_comparison_method_can_be_saved_as_shared_fact():
    bank_compare = ConversationMemory().to_bank_compare_session().updated({"method": "annuity"})

    assert bank_compare.method_explicit is True
    updated = ConversationMemory().merge_bank_comparison(
        amount=1_000_000_000,
        years=20,
        repayment_method=(bank_compare.method if bank_compare.method_explicit else None),
        source_seq=1,
    )
    assert updated.repayment_method == "annuity"


def test_memory_creates_estimate_and_bank_compare_sessions_from_saved_facts():
    memory = ConversationMemory(
        amount=1_000_000_000,
        years=20,
        user_provided_rate=Decimal("8.5"),
        repayment_method="reducing_balance",
        property_value=2_000_000_000,
        prepay_month=60,
        grace_period_months=6,
        base_rate=Decimal("7.5"),
        assumed_floating_rate=Decimal("10"),
    )

    estimate = memory.to_estimate_session()
    bank_compare = memory.to_bank_compare_session()

    assert (estimate.amount, estimate.years, estimate.rate, estimate.method) == (
        1_000_000_000, 20, Decimal("8.5"), "reducing_balance",
    )
    assert (bank_compare.amount, bank_compare.years, bank_compare.method) == (
        1_000_000_000, 20, "reducing_balance",
    )
    assert bank_compare.property_value is None
    assert bank_compare.prepay_month is None
    assert bank_compare.grace_period_months == 0
    assert bank_compare.base_rate is None
    assert bank_compare.assumed_floating_rate is None


def test_memory_rejects_bank_comparison_fields_outside_saved_loan_term():
    with pytest.raises(ValueError):
        ConversationMemory(years=1, prepay_month=12)
    with pytest.raises(ValueError):
        ConversationMemory(years=1, grace_period_months=12)


def test_memory_context_labels_user_rate_as_unverified():
    memory = ConversationMemory(user_provided_rate=Decimal("8.5"), verified_rate=Decimal("8.25"))

    context = memory.to_prompt_context()

    assert "8,5%/năm" in context
    assert "người dùng cung cấp" in context
    assert "chưa xác minh" in context
    assert "8,25%/năm" in context
    assert "đã được truy xuất" in context
