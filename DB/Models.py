from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy import String, Integer, BigInteger, Text, DateTime, Float, Boolean, ForeignKey, JSON, Index
from datetime import datetime
import sys
import os

# Добавляем путь к родительской директории для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import config

engine = create_async_engine(config.DATABASE_URL)
async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class Apartment(Base):
    """Модель для хранения объявлений о квартирах"""
    __tablename__ = "apartments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cian_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # ID из URL Cian
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=True)  # Цена в рублях
    price_per_sqm: Mapped[int] = mapped_column(Integer, nullable=True)  # Цена за м² в рублях
    
    # Источник данных
    source_url: Mapped[str] = mapped_column(Text, nullable=True, index=True)  # URL поиска, по которому была найдена квартира
    
    # Детальная информация (из глубокого парсинга)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    floor: Mapped[int] = mapped_column(Integer, nullable=True)
    floors_total: Mapped[int] = mapped_column(Integer, nullable=True)
    area: Mapped[float] = mapped_column(Float, nullable=True)
    rooms: Mapped[int] = mapped_column(Integer, nullable=True)
    
    # Метаданные
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_staging: Mapped[bool] = mapped_column(Boolean, default=False)  # Флаг для staging записей
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Поля для фильтрации (только для staging записей)
    filter_status: Mapped[str] = mapped_column(String(20), nullable=True, default='pending')  # 'pending', 'approved', 'rejected'
    filter_reason: Mapped[str] = mapped_column(Text, nullable=True)  # Причина отклонения
    price_segment: Mapped[int] = mapped_column(Integer, nullable=True)  # 1: <15M, 2: 15-20M, 3: 20-30M
    processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)  # Время обработки фильтрами
    
    # Поля для системы уведомлений
    is_new: Mapped[bool] = mapped_column(Boolean, default=True)  # Новая квартира (для уведомлений)
    approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)  # Время одобрения (перехода в production)
    
    # Связи
    metro_stations: Mapped[list["MetroStation"]] = relationship("MetroStation", back_populates="apartment", cascade="all, delete-orphan")
    price_history: Mapped[list["PriceHistory"]] = relationship("PriceHistory", back_populates="apartment", cascade="all, delete-orphan")
    user_reads: Mapped[list["UserApartmentRead"]] = relationship("UserApartmentRead", back_populates="apartment", cascade="all, delete-orphan")
    user_reactions: Mapped[list["UserApartmentReaction"]] = relationship("UserApartmentReaction", back_populates="apartment", cascade="all, delete-orphan")

class MetroStation(Base):
    """Модель для хранения информации о станциях метро"""
    __tablename__ = "metro_stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    apartment_id: Mapped[int] = mapped_column(Integer, ForeignKey("apartments.id"), nullable=False)
    station_name: Mapped[str] = mapped_column(String(100), nullable=False)
    travel_time: Mapped[str] = mapped_column(String(50), nullable=True)  # "8 мин пешком"
    
    # Связи
    apartment: Mapped["Apartment"] = relationship("Apartment", back_populates="metro_stations")

class PriceHistory(Base):
    """Модель для отслеживания истории изменения цен"""
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    apartment_id: Mapped[int] = mapped_column(Integer, ForeignKey("apartments.id"), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_sqm: Mapped[int] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связи
    apartment: Mapped["Apartment"] = relationship("Apartment", back_populates="price_history")

class User(Base):
    """Модель для пользователей бота"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Настройки пользователя
    max_price: Mapped[int] = mapped_column(Integer, nullable=True)
    min_price: Mapped[int] = mapped_column(Integer, nullable=True)
    preferred_metro: Mapped[str] = mapped_column(JSON, nullable=True)  # Список станций метро
    
    # Метаданные
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class FilterLog(Base):
    """Лог работы фильтра для отслеживания процесса"""
    __tablename__ = "filter_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    apartment_cian_id: Mapped[str] = mapped_column(String(50), nullable=False)
    filter_name: Mapped[str] = mapped_column(String(100), nullable=False)
    result: Mapped[str] = mapped_column(String(20), nullable=False)  # 'pass', 'fail'
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class UserNotification(Base):
    """Уведомления для пользователей о новых квартирах"""
    __tablename__ = "user_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    apartment_count: Mapped[int] = mapped_column(Integer, nullable=False)  # Количество новых квартир
    message: Mapped[str] = mapped_column(Text, nullable=False)  # Текст уведомления
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)  # Отправлено ли уведомление
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)  # Прочитано ли пользователем
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)  # Время отправки
    read_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)  # Время прочтения

class UserApartmentRead(Base):
    """Отслеживание просмотренных пользователем квартир"""
    __tablename__ = "user_apartment_reads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    apartment_id: Mapped[int] = mapped_column(Integer, ForeignKey("apartments.id"), nullable=False)
    read_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связи
    apartment: Mapped["Apartment"] = relationship("Apartment", back_populates="user_reads")

class UserApartmentReaction(Base):
    """Реакции пользователей на квартиры (лайки/дизлайки)"""
    __tablename__ = "user_apartment_reactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    apartment_id: Mapped[int] = mapped_column(Integer, ForeignKey("apartments.id"), nullable=False)
    reaction: Mapped[str] = mapped_column(String(10), nullable=False)  # 'like', 'dislike'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Составной индекс для быстрого поиска и уникальности (один пользователь - одна реакция на квартиру)
    __table_args__ = (
        Index('ix_user_apartment_unique', 'telegram_id', 'apartment_id', unique=True),
    )
    
    # Связи
    apartment: Mapped["Apartment"] = relationship("Apartment", back_populates="user_reactions")

# Устаревшая модель - оставляем для совместимости
class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    section: Mapped[str] = mapped_column(String)
    answer: Mapped[str] = mapped_column(String)
