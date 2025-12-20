import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from aiogram.types import Message, CallbackQuery, User, Chat
from services.bot.handlers import base, browser, stats, export

class TestBotHandlers(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Set up global patch for UserService used in decorator
        self.user_service_patcher = patch('services.bot.handlers.common.UserService')
        self.mock_user_service = self.user_service_patcher.start()
        self.mock_user_service.get_or_create_user = AsyncMock()

        # Create mock objects
        self.user = User(id=123456789, is_bot=False, first_name="Test", last_name="User", username="testuser")
        self.chat = Chat(id=123456789, type="private")
        
        self.message = MagicMock(spec=Message)
        self.message.from_user = self.user
        self.message.chat = self.chat
        self.message.text = "/start"
        self.message.answer = AsyncMock()
        
        self.callback = MagicMock(spec=CallbackQuery)
        self.callback.from_user = self.user
        self.callback.message = self.message
        self.callback.data = "test_data"
        self.callback.answer = AsyncMock()
        
        # State mock
        self.state = AsyncMock()

    async def asyncTearDown(self):
        self.user_service_patcher.stop()

    @patch('services.bot.handlers.base.NotificationService')
    async def test_start_command(self, mock_notification_service):
        """Test /start command"""
        # Setup mocks
        mock_notification_service.get_new_apartments_for_user = AsyncMock(return_value=[])
        mock_notification_service.mark_notifications_read = AsyncMock()
        
        # Call handler
        await base.command_start_handler(self.message, self.state)
        
        # Verify interactions
        mock_notification_service.mark_notifications_read.assert_called_with(self.user.id)
        self.message.answer.assert_called_once()
        args, kwargs = self.message.answer.call_args
        self.assertIn("Привет, Test User!", kwargs['text'])
        self.assertTrue(kwargs['reply_markup']) # Keyboard check

    @patch('services.bot.handlers.base.NotificationService')
    async def test_help_callback(self, mock_notif):
        """Test help button callback"""
        self.callback.data = "help"
        self.callback.message.text = "Old text" # Simulate existing message
        self.callback.message.edit_text = AsyncMock()
        
        await base.help_callback_handler(self.callback)
        
        # Should edit text
        self.callback.message.edit_text.assert_called_once()
        
    @patch('services.bot.handlers.stats.ApartmentService')
    async def test_stats_command(self, mock_apt_service):
        """Test /stats command"""
        # Fix import path for patch
        mock_apt_service.get_statistics = AsyncMock(return_value={
            'total_apartments': 100,
            'active_apartments': 80,
            'inactive_apartments': 20,
            'average_price': 5000000
        })
        
        await stats.stats_handler(self.message)
        
        self.message.answer.assert_called_once()
        args, kwargs = self.message.answer.call_args
        self.assertIn("100", args[0])
        self.assertIn("80", args[0])

    @patch('services.bot.handlers.browser.ApartmentService')
    @patch('services.bot.handlers.browser.ReactionService')
    async def test_browse_all_handler(self, mock_reaction_service, mock_apt_service):
        """Test browse all handler"""
        # Mock apartment
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
        
        self.callback.data = "browse_all"
        self.callback.message.edit_text = AsyncMock()
        
        await browser.browse_all_handler(self.callback)
        
        self.callback.message.edit_text.assert_called_once()
        args, kwargs = self.callback.message.edit_text.call_args
        self.assertIn("Test Apartment", args[0])

    @patch('services.bot.handlers.browser.ApartmentService')
    @patch('services.bot.handlers.browser.ReactionService')
    async def test_browse_next_views_100(self, mock_reaction_service, mock_apt_service):
        """Test browsing next with complex context views_100 (Bug Fix Verification)"""
        # Mock apartment
        mock_apt = MagicMock()
        mock_apt.id = 2
        mock_apt.price = 12000000
        mock_apt.title = "Views Apartment"
        mock_apt.url = "http://cian.ru/2" 
        mock_apt.price_per_sqm = 220000
        mock_apt.address = "Views St"
        mock_apt.metro_stations = []
        
        # Mocks
        # We need get_apartments to return a list with at least 2 items if index is 1
        mock_apt_service.get_apartments = AsyncMock(return_value=[MagicMock(), mock_apt]) 
        mock_reaction_service.get_user_reaction = AsyncMock(return_value=None)
        
        # Simulate callback data for "Next" button in "views_100" context
        # Format: browse_next_{current_index}_{list_context}
        # Current index 0 -> Next index 1
        self.callback.data = "browse_next_0_views_100"
        self.callback.message.edit_text = AsyncMock()
        
        await browser.browse_next_handler(self.callback)
        
        # Check that get_apartments was called with min_views=100
        # args/kwargs check
        mock_apt_service.get_apartments.assert_called_once()
        kwargs = mock_apt_service.get_apartments.call_args[1]
        self.assertEqual(kwargs.get('min_views'), 100)
        
        # Check that message was edited with correct apartment
        self.callback.message.edit_text.assert_called_once()
        args, _ = self.callback.message.edit_text.call_args
        self.assertIn("Views Apartment", args[0])

if __name__ == '__main__':
    unittest.main()
