import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from core.database.filter_service import FilterConfig, PriceFilter, MetroFilter, Apartment
from core.database.models import MetroStation

@pytest.fixture
def filter_config():
    return FilterConfig(
        min_price=10_000_000,
        max_price=25_000_000,
        blocked_metro_stations=["Зябликово"],
        required_metro_distance=15
    )

@pytest.mark.asyncio
async def test_price_filter_segmentation(filter_config):
    filter_inst = PriceFilter(filter_config)
    
    # Segment 1 (< 15M)
    apt1 = Apartment(price=14_000_000)
    result = await filter_inst.check(apt1)
    assert result['passed'] is True
    assert apt1.price_segment == 1
    
    # Segment 2 (15M - 20M)
    apt2 = Apartment(price=16_000_000)
    result = await filter_inst.check(apt2)
    assert result['passed'] is True
    assert apt2.price_segment == 2
    
    # Segment 3 (20M - 30M)
    apt3 = Apartment(price=22_000_000)
    result = await filter_inst.check(apt3)
    assert result['passed'] is True
    assert apt3.price_segment == 3

@pytest.mark.asyncio
async def test_price_filter_limits(filter_config):
    filter_inst = PriceFilter(filter_config)
    
    # Below min
    apt_low = Apartment(price=9_000_000)
    result = await filter_inst.check(apt_low)
    assert result['passed'] is False
    assert "слишком низкая" in result['reason']
    
    # Above max
    apt_high = Apartment(price=26_000_000)
    result = await filter_inst.check(apt_high)
    assert result['passed'] is False
    assert "слишком высокая" in result['reason']
    
    # Hard cap 30M
    apt_hard_cap = Apartment(price=31_000_000)
    result = await filter_inst.check(apt_hard_cap)
    assert result['passed'] is False
    assert "выше 30 млн" in result['reason']

@pytest.mark.asyncio
async def test_metro_filter_blocking(filter_config):
    # Mocking the import of metro_config to avoid external dependency issues in unit test
    with patch('core.database.filter_service.MetroFilter.__init__', return_value=None):
        filter_inst = MetroFilter(filter_config)
        filter_inst.config = filter_config
        filter_inst.blocked_stations = filter_config.blocked_metro_stations
        filter_inst.preferred_stations = []
        filter_inst.default_max_distance = 15
        
        # Blocked station
        apt = Apartment()
        apt.metro_stations = [MetroStation(station_name="Зябликово", travel_time="5 мин")]
        result = await filter_inst.check(apt)
        assert result['passed'] is False
        assert "Зябликово" in result['reason']
        
        # Valid station within distance
        apt.metro_stations = [MetroStation(station_name="Марьино", travel_time="10 мин")]
        result = await filter_inst.check(apt)
        assert result['passed'] is True
        assert "Марьино" in result['reason']
        
        # Valid station but too far
        apt.metro_stations = [MetroStation(station_name="Марьино", travel_time="20 мин")]
        result = await filter_inst.check(apt)
        assert result['passed'] is False
        assert "20 мин" in result['reason']
