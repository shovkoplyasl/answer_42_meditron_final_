import os
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/sm_clinic_test"

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/sm_clinic_test"

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        await session.execute(text("TRUNCATE findings, triggers, route_triggers, route_events, routes, protocols, patients, routing_rules RESTART IDENTITY CASCADE"))
        await session.commit()
        yield session
    await engine.dispose()