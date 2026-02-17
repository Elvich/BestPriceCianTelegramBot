import datetime
import os
from dotenv import load_dotenv

Base = declarative_base()

class SearchUrl(Base):
    __tablename__ = 'search_urls'

    id = Column(Integer, primary_key=True)
    url = Column(Text, nullable=False)
    name = Column(String(200))  # Human-readable description
    is_active = Column(Boolean, default=True)
    last_parsed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    offers = relationship("Offer", back_populates="search_url")


class Offer(Base):
    __tablename__ = 'offers'

    id = Column(Integer, primary_key=True)
    cian_id = Column(BigInteger, unique=True, nullable=False)
    url = Column(Text, nullable=False)
    search_url_id = Column(Integer, ForeignKey('search_urls.id'))  # Link to search source
    is_active = Column(Boolean, default=True)
    last_seen_at = Column(DateTime(timezone=True))  # When last seen in listing results
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    search_url = relationship("SearchUrl", back_populates="offers")
    details = relationship("OfferDetail", uselist=False, back_populates="offer", cascade="all, delete-orphan")
    prices = relationship("OfferPrice", back_populates="offer", cascade="all, delete-orphan")
    stats = relationship("OfferStat", back_populates="offer", cascade="all, delete-orphan")

class OfferDetail(Base):
    __tablename__ = 'offer_details'

    offer_id = Column(Integer, ForeignKey('offers.id'), primary_key=True)
    description = Column(Text)
    total_area = Column(Float)
    living_area = Column(Float)
    kitchen_area = Column(Float)
    floor = Column(Integer)
    floors_count = Column(Integer)
    build_year = Column(Integer)
    material_type = Column(String(50))
    metro_name = Column(String(100))
    metro_time = Column(Integer)
    metro_transport = Column(String(20))
    # NEW FIELDS
    rooms_count = Column(Integer)              # Количество комнат
    property_type = Column(String(50))         # flat, apartments, etc.
    balcony_count = Column(Integer)            # Количество балконов
    loggia_count = Column(Integer)             # Количество лоджий  
    is_auction = Column(Boolean, default=False) # Аукционная квартира
    deposit_paid = Column(Boolean)             # Залог внесен
    extra_attributes = Column(JSON)

    offer = relationship("Offer", back_populates="details")

class OfferPrice(Base):
    __tablename__ = 'offer_prices'

    id = Column(Integer, primary_key=True)
    offer_id = Column(Integer, ForeignKey('offers.id'))
    price = Column(BigInteger)
    price_per_m2 = Column(Float)
    currency = Column(String(5), default='RUB')
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())

    offer = relationship("Offer", back_populates="prices")

class OfferStat(Base):
    __tablename__ = 'offer_stats'

    id = Column(Integer, primary_key=True)
    offer_id = Column(Integer, ForeignKey('offers.id'))
    views_total = Column(Integer)
    views_today = Column(Integer)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())

    offer = relationship("Offer", back_populates="stats")

class OfferScore(Base):
    __tablename__ = 'offer_scores'

    offer_id = Column(Integer, ForeignKey('offers.id'), primary_key=True)
    price_score = Column(Integer, default=0)
    metro_score = Column(Integer, default=0)
    floor_score = Column(Integer, default=0)
    area_score = Column(Integer, default=0)
    views_score = Column(Integer, default=0)
    quality_score = Column(Integer, default=0)
    market_interest_score = Column(Integer, default=0)
    total_score = Column(Integer, default=0)
    discount_pct = Column(Float)
    calculated_at = Column(DateTime(timezone=True), default=func.now())

    offer = relationship("Offer", backref="score")

class UserInteraction(Base):
    __tablename__ = 'user_interactions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    offer_id = Column(Integer, ForeignKey('offers.id', ondelete='CASCADE'))
    interaction_type = Column(String(20)) # 'like', 'dislike'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="interactions")
    offer = relationship("Offer", backref="interactions")

class BannedMetro(Base):
    __tablename__ = 'banned_metros'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_developer = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# Configuration
# Load environment variables
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
load_dotenv(os.path.join(project_root, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/cian_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    Base.metadata.create_all(engine)

if __name__ == "__main__":
    # Test creation
    # Note: You must ensure the database 'cian_db' exists in Postgres first!
    try:
        create_tables()
        print("Tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {e}")
        print("Make sure you have installed PostgreSQL and created the database 'cian_db'.")
