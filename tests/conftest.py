# *Claude Generated*
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from spivmova.config import settings

# A dedicated NullPool engine for tests, separate from the app's pooled engine
# in db/session.py. pytest-asyncio gives each test its own event loop, and an
# async connection pool holds onto connections tied to the loop they were
# opened in -- reusing the app's shared engine across tests crashes as soon as
# a second test tries to check out a connection opened under a prior loop.
# NullPool sidesteps this by never pooling: every checkout is a fresh
# connection. (alembic/env.py uses the same fix for the same reason.)
test_engine = create_async_engine(settings.database_url, poolclass=NullPool)


@pytest_asyncio.fixture
async def db_session():
    """An AsyncSession bound to a SAVEPOINT that's always rolled back.

    Code under test can call session.commit() freely (e.g. persist_track does) --
    commit only releases the SAVEPOINT, it doesn't touch the outer transaction.
    Rolling that back at the end undoes everything, so tests never leave rows
    behind in the real dev database.
    """
    async with test_engine.connect() as connection:
        trans = await connection.begin()
        session = AsyncSession(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
