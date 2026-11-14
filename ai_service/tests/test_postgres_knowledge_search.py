"""Repository SQL regressions; opt in with TEST_KNOWLEDGE_DATABASE_URL.

Only temporary tables are written; all changes are rolled back after each test.
The database must already have the vector extension installed.
"""

import os
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.domain.entities.knowledge_evidence import KnowledgeSearchQuery
from app.infrastructure.knowledge.postgres_knowledge_repository import PostgresKnowledgeRepository


@pytest.fixture
async def search_session():
    url = os.environ.get("TEST_KNOWLEDGE_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_KNOWLEDGE_DATABASE_URL to run PostgreSQL search regressions")
    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                await connection.execute(text("""
                    CREATE TEMP TABLE knowledge_documents (
                        id uuid PRIMARY KEY, logical_document_id uuid NOT NULL,
                        version_no integer NOT NULL, title text DEFAULT 'FAQ', source_url text,
                        bank_code text, product_type text, effective_from date, effective_to date,
                        review_status text DEFAULT 'approved',
                        ingestion_status text DEFAULT 'published', is_active boolean DEFAULT true
                    ) ON COMMIT DROP
                """))
                await connection.execute(text("""
                    CREATE TEMP TABLE knowledge_chunks (
                        id uuid PRIMARY KEY, document_id uuid NOT NULL, body text NOT NULL,
                        embedding vector(2), textsearch tsvector
                    ) ON COMMIT DROP
                """))
                async with AsyncSession(bind=connection) as session:
                    yield session
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


async def add_version(session, logical_id, version, *, chunks=1, embedding="[1,0]", **overrides):
    document_id = uuid4()
    values = {
        "id": document_id, "logical_id": logical_id, "version": version,
        "review": "approved", "status": "published", "active": True,
        "start": None, "end": None, **overrides,
    }
    await session.execute(text("""
        INSERT INTO pg_temp.knowledge_documents (
            id, logical_document_id, version_no, review_status,
            ingestion_status, is_active, effective_from, effective_to
        ) VALUES (:id, :logical_id, :version, :review, :status, :active, :start, :end)
    """), values)
    for ordinal in range(chunks):
        await session.execute(text("""
            INSERT INTO pg_temp.knowledge_chunks (id, document_id, body, embedding, textsearch)
            VALUES (:id, :document_id, :body, CAST(:embedding AS vector),
                    to_tsvector('simple', :body))
        """), {
            "id": uuid4(), "document_id": document_id,
            "body": f"version {version} chunk {ordinal}", "embedding": embedding,
        })
    return document_id


async def search(session, *, limit=10):
    # Repository owns this session context; the outer connection owns the rollback.
    repository = PostgresKnowledgeRepository(lambda: session)
    return await repository.search_approved(KnowledgeSearchQuery(
        text="mortgage", embedding=(1.0, 0.0), limit=limit,
    ))


async def test_latest_version_is_selected_before_scoring_and_preserves_all_its_chunks(search_session):
    logical_id = uuid4()
    await add_version(search_session, logical_id, 1, embedding="[1,0]")
    latest = await add_version(search_session, logical_id, 2, chunks=2, embedding="[1,1]")
    other = await add_version(search_session, uuid4(), 1, embedding="[1,1]")

    evidence = await search(search_session)

    assert {item.document_id for item in evidence} == {latest, other}
    assert sum(item.document_id == latest for item in evidence) == 2
    assert all(item.score > 0 for item in evidence)


@pytest.mark.parametrize("overrides", [
    {"status": "queued"},
    {"status": "failed"},
    {"review": "pending"},
    {"active": False},
    {"start": "future"},
    {"end": "today"},
])
async def test_newer_ineligible_version_does_not_hide_older_eligible_version(search_session, overrides):
    today = (await search_session.execute(text("SELECT CURRENT_DATE"))).scalar_one()
    overrides = {
        key: today + timedelta(days=1) if value == "future" else today if value == "today" else value
        for key, value in overrides.items()
    }
    logical_id = uuid4()
    older = await add_version(search_session, logical_id, 1)
    await add_version(search_session, logical_id, 2, **overrides)

    evidence = await search(search_session)

    assert [item.document_id for item in evidence] == [older]


async def test_old_matching_chunks_are_not_used_when_latest_version_does_not_match(search_session):
    logical_id = uuid4()
    await add_version(search_session, logical_id, 1)
    await add_version(search_session, logical_id, 2, embedding="[-1,0]")

    assert await search(search_session) == ()


async def test_latest_version_with_no_chunks_does_not_resurrect_old_content(search_session):
    logical_id = uuid4()
    await add_version(search_session, logical_id, 1)
    await add_version(search_session, logical_id, 2, chunks=0)

    assert await search(search_session) == ()


async def test_effective_from_today_is_eligible_and_limit_applies_after_version_selection(search_session):
    today = (await search_session.execute(text("SELECT CURRENT_DATE"))).scalar_one()
    logical_id = uuid4()
    await add_version(search_session, logical_id, 1)
    latest = await add_version(search_session, logical_id, 2, chunks=2, start=today)

    evidence = await search(search_session, limit=1)

    assert len(evidence) == 1
    assert evidence[0].document_id == latest
