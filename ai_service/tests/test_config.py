import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("value", [0, -1, 8193])
def test_chat_max_tokens_rejects_out_of_range_values(value):
    with pytest.raises(ValidationError):
        Settings(chat_max_tokens=value)


@pytest.mark.parametrize("value", [1, 2000, 8192])
def test_chat_max_tokens_accepts_values_within_range(value):
    assert Settings(chat_max_tokens=value).chat_max_tokens == value
