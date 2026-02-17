-- CIAN Parser - Complete Database Schema
-- Provides a clean setup for the entire database structure in one execution.

-- 1. Search URLs (Sources)
CREATE TABLE IF NOT EXISTS search_urls (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    name VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    last_parsed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Main Offers Table
CREATE TABLE IF NOT EXISTS offers (
    id SERIAL PRIMARY KEY,
    cian_id BIGINT UNIQUE NOT NULL,
    url TEXT NOT NULL,
    search_url_id INTEGER REFERENCES search_urls(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_seen_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Offer Details (Deep properties)
CREATE TABLE IF NOT EXISTS offer_details (
    offer_id INTEGER PRIMARY KEY REFERENCES offers(id) ON DELETE CASCADE,
    description TEXT,
    total_area FLOAT,
    living_area FLOAT,
    kitchen_area FLOAT,
    floor INTEGER,
    floors_count INTEGER,
    build_year INTEGER,
    material_type VARCHAR(50),
    metro_name VARCHAR(100),
    metro_time INTEGER,
    metro_transport VARCHAR(20),
    
    -- Extra fields added during development
    rooms_count INTEGER,
    property_type VARCHAR(50),
    balcony_count INTEGER,
    loggia_count INTEGER,
    is_auction BOOLEAN DEFAULT FALSE,
    deposit_paid BOOLEAN,
    
    extra_attributes JSONB
);

-- 4. Offer Prices (History)
CREATE TABLE IF NOT EXISTS offer_prices (
    id SERIAL PRIMARY KEY,
    offer_id INTEGER REFERENCES offers(id) ON DELETE CASCADE,
    price BIGINT NOT NULL,
    price_per_m2 FLOAT,
    currency VARCHAR(5) DEFAULT 'RUB',
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Offer Stats (Views History)
CREATE TABLE IF NOT EXISTS offer_stats (
    id SERIAL PRIMARY KEY,
    offer_id INTEGER REFERENCES offers(id) ON DELETE CASCADE,
    views_total INTEGER,
    views_today INTEGER,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Offer Scores (Analytics)
CREATE TABLE IF NOT EXISTS offer_scores (
    offer_id INTEGER PRIMARY KEY REFERENCES offers(id) ON DELETE CASCADE,
    price_score INTEGER DEFAULT 0,
    metro_score INTEGER DEFAULT 0,
    floor_score INTEGER DEFAULT 0,
    area_score INTEGER DEFAULT 0,
    views_score INTEGER DEFAULT 0,
    quality_score INTEGER DEFAULT 0,
    market_interest_score INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    discount_pct FLOAT,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_scores CHECK (
        price_score >= 0 AND price_score <= 45 AND
        metro_score >= 0 AND metro_score <= 30 AND
        floor_score >= 0 AND floor_score <= 15 AND
        area_score >= 0 AND area_score <= 10 AND
        views_score >= 0 AND views_score <= 100 AND
        total_score >= 0 AND total_score <= 200
    )
);

-- 7. Performance Indexes
CREATE INDEX IF NOT EXISTS idx_offers_cian_id ON offers(cian_id);
CREATE INDEX IF NOT EXISTS idx_offers_search_url_id ON offers(search_url_id);
CREATE INDEX IF NOT EXISTS idx_prices_offer_id ON offer_prices(offer_id);
CREATE INDEX IF NOT EXISTS idx_stats_offer_id ON offer_stats(offer_id);
CREATE INDEX IF NOT EXISTS idx_offer_scores_total ON offer_scores(total_score DESC);
CREATE INDEX IF NOT EXISTS idx_offer_scores_quality ON offer_scores(quality_score DESC);

-- 8. Bot Users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(100),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_developer BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- user_interactions: Likes/Dislikes
CREATE TABLE IF NOT EXISTS user_interactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    offer_id INTEGER REFERENCES offers(id) ON DELETE CASCADE,
    interaction_type VARCHAR(20) CHECK (interaction_type IN ('like', 'dislike')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, offer_id)
);

CREATE INDEX IF NOT EXISTS idx_user_interactions_user_id ON user_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_interactions_offer_id ON user_interactions(offer_id);

CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);

-- 9. Metro Ban List
CREATE TABLE IF NOT EXISTS banned_metros (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_banned_metros_name ON banned_metros(name);
