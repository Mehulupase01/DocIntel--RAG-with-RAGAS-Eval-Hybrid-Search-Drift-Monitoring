from __future__ import annotations

import os
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
TEST_POSTGRES_ADMIN_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
TEST_POSTGRES_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/docintel_test"
TEST_ARTIFACT_STORAGE_PATH = str((Path(__file__).parent / ".artifacts").resolve())
TEST_MODEL_CACHE_DIR = str((Path(__file__).parent / ".model_cache").resolve())
os.environ.setdefault("DATABASE_URL", TEST_DB_URL)
os.environ.setdefault("API_KEYS", "dev-key-change-me")
os.environ.setdefault("ARTIFACT_STORAGE_PATH", TEST_ARTIFACT_STORAGE_PATH)
os.environ.setdefault("MODEL_CACHE_DIR", TEST_MODEL_CACHE_DIR)
Path(TEST_ARTIFACT_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
Path(TEST_MODEL_CACHE_DIR).mkdir(parents=True, exist_ok=True)

from docintel.database import get_db  # noqa: E402
from docintel.main import app  # noqa: E402
from docintel.models.base import Base  # noqa: E402


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def postgres_engine():
    admin_engine = create_async_engine(TEST_POSTGRES_ADMIN_URL, isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = 'docintel_test'")
            )
            if not exists:
                await conn.execute(text("CREATE DATABASE docintel_test"))
    except Exception as exc:
        await admin_engine.dispose()
        pytest.skip(f"Postgres test database unavailable: {exc}")

    await admin_engine.dispose()

    import docintel.models  # noqa: F401

    engine = create_async_engine(TEST_POSTGRES_DB_URL, poolclass=NullPool, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def postgres_db_session(postgres_engine):
    async with postgres_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP TYPE IF EXISTS document_status CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS drift_status CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS retrieval_strategy CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS eval_run_status CASCADE"))
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(postgres_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with postgres_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP TYPE IF EXISTS document_status CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS drift_status CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS retrieval_strategy CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS eval_run_status CASCADE"))


@pytest_asyncio.fixture
async def postgres_client(postgres_db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: postgres_db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def tiny_pdf_path() -> Path:
    return Path(__file__).parent / "fixtures" / "tiny_pdf.pdf"


@pytest.fixture
def tiny_pdf_bytes(tiny_pdf_path: Path) -> bytes:
    return tiny_pdf_path.read_bytes()
