import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import User, Chat, Message, CallbackQuery

@pytest.fixture
def mock_user():
    return User(id=123456789, is_bot=False, first_name="Test", last_name="User", username="testuser")

@pytest.fixture
def mock_chat():
    return Chat(id=123456789, type="private")

@pytest.fixture
def mock_message(mock_user, mock_chat):
    message = MagicMock(spec=Message)
    message.from_user = mock_user
    message.chat = mock_chat
    message.text = "/start"
    message.answer = AsyncMock()
    message.edit_text = AsyncMock()
    return message

@pytest.fixture
def mock_callback(mock_user, mock_message):
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = mock_user
    callback.message = mock_message
    callback.data = "test_data"
    callback.answer = AsyncMock()
    return callback

@pytest.fixture(autouse=True)
def mock_db_session(mocker):
    """Global mock for DB sessions to prevent actual DB connections during unit tests"""
    mock_session = AsyncMock()
    mocker.patch('core.database.models.async_session', return_value=mock_session)
    return mock_session
