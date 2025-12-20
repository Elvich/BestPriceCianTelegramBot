import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, CallbackQuery, User, Chat
from services.bot.handlers import base, browser, stats, export

@pytest.fixture(autouse=True)
def mock_common_user_service():
    """Mock UserService in handlers.common for all tests (used in decorators)"""
    with patch('services.bot.handlers.common.UserService') as mock:
        mock.get_or_create_user = AsyncMock()
        yield mock

@pytest.fixture
def bot_user():
    return User(id=123456789, is_bot=False, first_name="Test", last_name="User", username="testuser")

@pytest.fixture
def bot_chat():
    return Chat(id=123456789, type="private")

@pytest.fixture
def mock_message(bot_user, bot_chat):
    message = MagicMock(spec=Message)
    message.from_user = bot_user
    message.chat = bot_chat
    message.text = "/start"
    message.answer = AsyncMock()
    return message

@pytest.fixture
def mock_callback(bot_user, mock_message):
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = bot_user
    callback.message = mock_message
    callback.data = "test_data"
    callback.answer = AsyncMock()
    return callback

@pytest.mark.asyncio
@patch('services.bot.handlers.base.NotificationService')
async def test_start_command(mock_notification_service, mock_message, bot_user):
    """Test /start command"""
    mock_notification_service.get_new_apartments_for_user = AsyncMock(return_value=[])
    mock_notification_service.mark_notifications_read = AsyncMock()
    
    state = AsyncMock()
    await base.command_start_handler(mock_message, state)
    
    mock_notification_service.mark_notifications_read.assert_called_with(bot_user.id)
    mock_message.answer.assert_called_once()
    _, kwargs = mock_message.answer.call_args
    assert "Привет, Test User!" in kwargs['text']
    assert kwargs['reply_markup']

@pytest.mark.asyncio
async def test_help_callback(mock_callback):
    """Test help button callback"""
    mock_callback.data = "help"
    mock_callback.message.text = "Old text"
    mock_callback.message.edit_text = AsyncMock()
    
    await base.help_callback_handler(mock_callback)
    
    mock_callback.message.edit_text.assert_called_once()

@pytest.mark.asyncio
@patch('services.bot.handlers.stats.ApartmentService')
async def test_stats_command(mock_apt_service, mock_message):
    """Test /stats command"""
    mock_apt_service.get_statistics = AsyncMock(return_value={
        'total_apartments': 100,
        'active_apartments': 80,
        'inactive_apartments': 20,
        'average_price': 5000000
    })
    
    await stats.stats_handler(mock_message)
    
    mock_message.answer.assert_called_once()
    args, _ = mock_message.answer.call_args
    assert "100" in args[0]
    assert "80" in args[0]

@pytest.mark.asyncio
@patch('services.bot.handlers.browser.ApartmentService')
@patch('services.bot.handlers.browser.ReactionService')
async def test_browse_all_handler(mock_reaction_service, mock_apt_service, mock_callback):
    """Test browse all handler"""
    mock_apt = MagicMock()
    mock_apt.id = 1
    mock_apt.price = 10000000
    mock_apt.title = "Test Apartment"
    mock_apt.url = "http://cian.ru/1"
    mock_apt.price_per_sqm = 200000
    mock_apt.address = "Test St"
    mock_apt.metro_stations = []
    
    mock_apt_service.get_apartments = AsyncMock(return_value=[mock_apt])
    mock_reaction_service.get_user_reaction = AsyncMock(return_value=None)
    
    mock_callback.data = "browse_all"
    mock_callback.message.edit_text = AsyncMock()
    
    await browser.browse_all_handler(mock_callback)
    
    mock_callback.message.edit_text.assert_called_once()
    args, _ = mock_callback.message.edit_text.call_args
    assert "Test Apartment" in args[0]

@pytest.mark.asyncio
@patch('services.bot.handlers.browser.ApartmentService')
@patch('services.bot.handlers.browser.ReactionService')
async def test_browse_next_views_100(mock_reaction_service, mock_apt_service, mock_callback):
    """Test browsing next with complex context views_100 (Bug Fix Verification)"""
    mock_apt = MagicMock()
    mock_apt.id = 2
    mock_apt.price = 12000000
    mock_apt.title = "Views Apartment"
    mock_apt.url = "http://cian.ru/2" 
    mock_apt.price_per_sqm = 220000
    mock_apt.address = "Views St"
    mock_apt.metro_stations = []
    
    mock_apt_service.get_apartments = AsyncMock(return_value=[MagicMock(), mock_apt]) 
    mock_reaction_service.get_user_reaction = AsyncMock(return_value=None)
    
    mock_callback.data = "browse_next_0_views_100"
    mock_callback.message.edit_text = AsyncMock()
    
    await browser.browse_next_handler(mock_callback)
    
    mock_apt_service.get_apartments.assert_called_once()
    kwargs = mock_apt_service.get_apartments.call_args[1]
    assert kwargs.get('min_views') == 100
    
    mock_callback.message.edit_text.assert_called_once()
    args, _ = mock_callback.message.edit_text.call_args
    assert "Views Apartment" in args[0]
