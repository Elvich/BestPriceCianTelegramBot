import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_session():
    """Mock for SQLAlchemy async session"""
    session = AsyncMock()
    # Mocking basic context manager behavior
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    
    # Synchronous methods in AsyncSession
    session.add = MagicMock()
    session.merge = AsyncMock() # merge is actually async in AsyncSession! 
    # Wait, let me check SQLAlchemy docs for AsyncSession.merge.
    # AsyncSession.merge() is awaitable.
    # AsyncSession.add() is NOT awaitable.
    return session

@pytest.fixture
def mock_session_factory(mock_session):
    """Mock for SQLAlchemy sessionmaker"""
    factory = MagicMock()
    factory.return_value = mock_session
    return factory
