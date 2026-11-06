import asyncio
import logging
import signal
from uuid import UUID

from sqlalchemy import text

from app.infrastructure.db.session import get_async_session_factory
from app.presentation.api.knowledge_dependencies import get_document_processor

logger = logging.getLogger(__name__)


async def claim_job():
    sessions = get_async_session_factory()
    async with sessions() as session, session.begin():
        row = (await session.execute(text("""
            WITH candidate AS (
              SELECT id FROM background_jobs
              WHERE status = 'pending' AND kind = 'knowledge_ingestion' AND run_after <= now()
                AND attempts < max_attempts
              ORDER BY run_after, id FOR UPDATE SKIP LOCKED LIMIT 1
            )
            UPDATE background_jobs j
            SET status = 'running', lease_until = now() + interval '120 seconds',
                lease_token = gen_random_uuid(), attempts = attempts + 1
            FROM candidate c WHERE j.id = c.id
            RETURNING j.id, j.payload, j.lease_token, j.attempts, j.max_attempts
        """))).mappings().first()
        if row is None:
            return None
        return dict(row)


async def finish_job(job_id: UUID, lease_token, *, error: str | None = None) -> None:
    sessions = get_async_session_factory()
    async with sessions() as session, session.begin():
        if error is None:
            await session.execute(text("""
                UPDATE background_jobs SET status='done', lease_token=NULL, lease_until=NULL
                WHERE id=:id AND status='running' AND lease_token=:token
            """), {"id": job_id, "token": lease_token})
        else:
            await session.execute(text("""
                UPDATE background_jobs
                SET status = CASE WHEN attempts >= max_attempts THEN 'dead' ELSE 'pending' END,
                    run_after = now() + make_interval(secs => LEAST(300, (2 ^ LEAST(attempts, 8))::int)),
                    lease_token=NULL, lease_until=NULL, last_error_code=:error
                WHERE id=:id AND status='running' AND lease_token=:token
            """), {"id": job_id, "token": lease_token, "error": error})


async def reap_expired_jobs() -> None:
    sessions = get_async_session_factory()
    async with sessions() as session, session.begin():
        await session.execute(text("""
            UPDATE background_jobs
            SET status = CASE WHEN attempts >= max_attempts THEN 'dead' ELSE 'pending' END,
                run_after = now() + make_interval(secs => LEAST(300, (2 ^ LEAST(attempts, 8))::int)),
                lease_token=NULL, lease_until=NULL, last_error_code='JOB_LEASE_EXPIRED'
            WHERE kind='knowledge_ingestion' AND status='running' AND lease_until < now()
        """))


async def run_worker(stop: asyncio.Event) -> None:
    processor = get_document_processor()
    while not stop.is_set():
        try:
            await reap_expired_jobs()
            claimed = await claim_job()
            if claimed is None:
                try:
                    await asyncio.wait_for(stop.wait(), timeout=1.0)
                except TimeoutError:
                    pass
                continue
            payload = claimed["payload"]
            document_id = UUID(payload["document_id"])
            try:
                await processor.execute(document_id)
                await finish_job(claimed["id"], claimed["lease_token"])
            except Exception:
                logger.exception("Knowledge job failed", extra={"job_id": str(claimed["id"])})
                await finish_job(claimed["id"], claimed["lease_token"], error="JOB_FAILED")
        except Exception:
            logger.exception("Worker poll failed")
            try:
                await asyncio.wait_for(stop.wait(), timeout=2.0)
            except TimeoutError:
                pass


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logger.info("Knowledge worker starting; polling PostgreSQL for ingestion jobs")
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            signal.signal(sig, lambda *_: stop.set())
    try:
        await run_worker(stop)
    finally:
        from app.infrastructure.db.session import dispose_database

        await dispose_database()


if __name__ == "__main__":
    asyncio.run(main())
