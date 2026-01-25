import pytest
from bs4 import BeautifulSoup
from services.parser.logic.cian_parser import CianParser

@pytest.fixture
def parser():
    return CianParser()

def test_extract_metro_info(parser):
    html = """
    <ul>
        <li data-name="UndergroundItem">
            <a class="--underground-link--">Мякинино</a>
            <span class="--underground-time--">10 мин</span>
        </li>
        <li data-name="UndergroundItem">
            <a class="--underground-link--">Строгино</a>
            <span class="--underground-time--">15 мин</span>
        </li>
    </ul>
    """
    soup = BeautifulSoup(html, 'lxml')
    info = parser._extract_metro_info(soup)
    
    assert len(info) == 2
    assert info[0]['station'] == "Мякинино"
    assert info[0]['time'] == "10 мин"
    assert info[1]['station'] == "Строгино"
    assert info[1]['time'] == "15 мин"

def test_extract_floor_info(parser):
    # Strategy 1: "Этаж" text
    html1 = """
    <div>Этаж</div>
    <div>5 из 12</div>
    """
    soup1 = BeautifulSoup(html1, 'lxml')
    floor, total = parser._extract_floor_info(soup1)
    assert floor == 5
    assert total == 12
    
    # Strategy 2: OfferFactItem
    html2 = """
    <div data-name="OfferFactItem">
        <div class="--title--">Этаж</div>
        <div class="--value--">3 из 9</div>
    </div>
    """
    soup2 = BeautifulSoup(html2, 'lxml')
    floor, total = parser._extract_floor_info(soup2)
    assert floor == 3
    assert total == 9

def test_extract_views(parser):
    html = """
    <div>123 просмотра, 5 за сегодня</div>
    """
    soup = BeautifulSoup(html, 'lxml')
    views = parser._extract_views(soup)
    assert views == 5
    
    html_no_today = """
    <div>123 просмотра</div>
    """
    soup_no_today = BeautifulSoup(html_no_today, 'lxml')
    views_no_today = parser._extract_views(soup_no_today)
    assert views_no_today == 0

def test_extract_rooms(parser):
    # From title
    title = "2-комн. квартира, 54,2 м²"
    soup = BeautifulSoup("", 'lxml')
    assert parser._extract_rooms(title, soup) == 2
    
    # From title (studio)
    title_studio = "Студия, 20 м²"
    assert parser._extract_rooms(title_studio, soup) == 0
    
    # From characteristics
    html = """
    <div data-name="OfferFactItem">
        <div class="--title--">Количество комнат</div>
        <div class="--value--">3-комнатная</div>
    </div>
    """
    soup_char = BeautifulSoup(html, 'lxml')
    assert parser._extract_rooms("", soup_char) == 3

def test_extract_area(parser):
    # From title
    title = "2-комн. квартира, 54.2 м²"
    soup = BeautifulSoup("", 'lxml')
    assert parser._extract_area(title, soup) == 54.2
    
    # From title with comma
    title_comma = "2-комн. квартира, 54,2 м²"
    assert parser._extract_area(title_comma, soup) == 54.2
    
    # From characteristics
    html = """
    <div data-name="OfferFactItem">
        <div class="--title--">Общая площадь</div>
        <div class="--value--">60.5 м²</div>
    </div>
    """
    soup_char = BeautifulSoup(html, 'lxml')
    assert parser._extract_area("", soup_char) == 60.5
