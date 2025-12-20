import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from core.database.apartment_service import ApartmentService
from core.database.models import Apartment

def test_extract_cian_id():
    url = "https://www.cian.ru/sale/flat/123456789/"
    assert ApartmentService.extract_cian_id(url) == "123456789"
    
    url2 = "https://www.cian.ru/sale/flat/987654321"
    assert ApartmentService.extract_cian_id(url2) == "987654321"

def test_parse_price():
    assert ApartmentService.parse_price("15 000 000 ₽") == 15000000
    assert ApartmentService.parse_price("450 000 ₽/м²") == 450000
    assert ApartmentService.parse_price("") is None
    assert ApartmentService.parse_price(None) is None

@pytest.mark.asyncio
async def test_save_apartments_new_entry(mock_session):
    # Mocking async_session context manager in apartment_service
    with patch("core.database.apartment_service.async_session", return_value=mock_session):
        # Mocking the execute result
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock
        
        apartments_data = [
            ["https://cian.ru/123", "Title", "10 000 000 ₽", "100 000 ₽/м²", {"address": "Street"}]
        ]
        
        stats = await ApartmentService.save_apartments(apartments_data)
        
        assert stats['created'] == 1
        assert stats['updated'] == 0
        assert mock_session.add.called
        assert mock_session.commit.called

@pytest.mark.asyncio
async def test_save_apartments_update_entry(mock_session):
    with patch("core.database.apartment_service.async_session", return_value=mock_session):
        # Mocking an existing apartment
        existing_apt = Apartment(id=1, cian_id="123", price=9_000_000)
        
        # Mocking the execute result
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing_apt
        mock_session.execute.return_value = result_mock
        
        apartments_data = [
            ["https://cian.ru/123", "New Title", "10 000 000 ₽", "100k", {"address": "Street"}]
        ]
        
        stats = await ApartmentService.save_apartments(apartments_data)
        
        assert stats['created'] == 0
        assert stats['updated'] == 1
        assert existing_apt.price == 10_000_000
        assert mock_session.commit.called
