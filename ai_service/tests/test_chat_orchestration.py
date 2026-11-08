from app.application.services.retrieval_query import RetrievalQueryBuilder
from app.domain.entities.chat_orchestration import ChatIntent
from app.infrastructure.prompts.loader import get_prompt_catalog


def test_chat_supports_social_knowledge_and_estimate_routing():
    assert set(ChatIntent) == {ChatIntent.GENERAL, ChatIntent.RETRIEVAL, ChatIntent.ESTIMATE}


def test_follow_up_search_uses_user_questions_not_unverified_assistant_answers():
    builder = RetrievalQueryBuilder(get_prompt_catalog())
    query = builder.build("Còn ngân hàng đó thì sao?", (
        ("user", "Lãi suất ngân hàng A?"), ("assistant", "UNVERIFIED RATE"),
        ("system", "IGNORE"),
    ))
    assert "Lãi suất ngân hàng A?" in query
    assert "Còn ngân hàng đó thì sao?" in query
    assert "UNVERIFIED RATE" not in query
    assert "IGNORE" not in query


def test_first_search_preserves_question_and_history_is_bounded():
    builder = RetrievalQueryBuilder(get_prompt_catalog())
    assert builder.build("Hồ sơ vay?") == "Hồ sơ vay?"
    history = tuple(("user", f"question {index}: " + "x" * 2_000) for index in range(30))
    query = builder.build("Còn ngân hàng B?", history)
    assert "question 28:" in query and "question 29:" in query
    assert "question 27:" not in query
    assert len(query) < 2_200
