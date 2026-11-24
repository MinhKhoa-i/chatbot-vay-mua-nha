import re
import unicodedata
from decimal import Decimal, InvalidOperation

from app.domain.entities.bank_compare_session import BankCompareSession
from app.domain.entities.bank_rank import BankRankResult

_NUMBER_PATTERN = re.compile(r"([+-]?\d+(?:[.,]\d+)*)(?:\s*(tỷ|tỉ|triệu|nghìn|ngàn)\b)?", re.IGNORECASE)
_DATE_PATTERN = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_MONEY_UNITS = {"tỷ": 1_000_000_000, "tỉ": 1_000_000_000, "triệu": 1_000_000, "nghìn": 1_000, "ngàn": 1_000}


def _numbers(text: str) -> set[Decimal]:
    text = "".join(char for char in text if unicodedata.category(char) != "Cf").replace("−", "-")
    # ISO date separators must not turn month/day into negative numbers.
    text = _DATE_PATTERN.sub(r"\1/\2/\3", text)
    values = set()
    for token, unit in _NUMBER_PATTERN.findall(text):
        multiplier = _MONEY_UNITS.get(unit.lower(), 1)
        # Grouped VND amounts use thousands separators; rates and scaled amounts use decimals.
        if not unit and re.fullmatch(r"[+-]?\d{1,3}([.,]\d{3}){2,}", token):
            token = token.replace(".", "").replace(",", "")
        else:
            token = token.replace(",", ".")
        try:
            values.add(Decimal(token) * multiplier)
        except InvalidOperation:
            values.add(Decimal("Infinity"))
    return values


def bank_compare_numbers_match(
    answer: str, session: BankCompareSession, result: BankRankResult,
) -> bool:
    """shortcut: checks numeric values, not bank/field associations; render facts for that guarantee."""
    amounts = (
        session.amount, session.years, session.property_value,
        session.prepay_month, session.grace_period_months,
        *(value for bank in result.ranked for value in (
            bank.total_cost, bank.total_interest, bank.prepay_fee, bank.first_payment,
        )),
    )
    rates = (
        session.base_rate, session.assumed_floating_rate,
        *result.assumptions.values(), *(bank.floating_rate for bank in result.ranked),
    )
    labels = (
        result.updated_at,
        *(label for bank in result.ranked for label in (bank.short_name, bank.package_name)),
        *(label for bank in result.excluded for label in (bank.short_name, bank.reason)),
    )
    allowed = {
        *(Decimal(str(value)) for value in (*amounts, *rates) if value is not None),
        *(Decimal(index) for index in range(1, len(result.ranked) + 1)),
        *(number for label in labels for number in _numbers(label)),
    }
    return _numbers(answer) <= allowed
