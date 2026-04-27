-- StayEase Database Schema
-- Run this in pgAdmin or psql before testing the API.

CREATE TABLE IF NOT EXISTS listings (
    id              VARCHAR(20)     PRIMARY KEY,
    title           VARCHAR(255)    NOT NULL,
    description     TEXT,
    location        VARCHAR(100)    NOT NULL,
    price_per_night DECIMAL(10,2)   NOT NULL,
    max_guests      INTEGER         NOT NULL,
    bedrooms        INTEGER         DEFAULT 1,
    bathrooms       INTEGER         DEFAULT 1,
    amenities       TEXT[],
    rating          DECIMAL(2,1)    DEFAULT 0.0,
    total_reviews   INTEGER         DEFAULT 0,
    host_name       VARCHAR(100),
    cancellation_policy VARCHAR(255),
    is_active       BOOLEAN         DEFAULT TRUE,
    created_at      TIMESTAMPTZ     DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
    id              VARCHAR(36)     PRIMARY KEY,
    messages        JSONB           DEFAULT '[]',
    current_intent  VARCHAR(20),
    needs_escalation BOOLEAN        DEFAULT FALSE,
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bookings (
    id              VARCHAR(30)     PRIMARY KEY,
    listing_id      VARCHAR(20)     NOT NULL REFERENCES listings(id),
    guest_name      VARCHAR(100)    NOT NULL,
    check_in        DATE            NOT NULL,
    check_out       DATE            NOT NULL CHECK (check_out > check_in),
    guests          INTEGER         NOT NULL CHECK (guests >= 1),
    total_price     DECIMAL(12,2)   NOT NULL,
    status          VARCHAR(20)     DEFAULT 'confirmed',
    conversation_id VARCHAR(36)     REFERENCES conversations(id),
    created_at      TIMESTAMPTZ     DEFAULT NOW()
);

-- Indexes for faster search, details and availability queries
CREATE INDEX IF NOT EXISTS idx_listings_location ON listings(location);
CREATE INDEX IF NOT EXISTS idx_listings_location_active_guests
ON listings (lower(location), is_active, max_guests);

CREATE INDEX IF NOT EXISTS idx_listings_id_active
ON listings (id, is_active);

CREATE INDEX IF NOT EXISTS idx_bookings_listing_dates_status
ON bookings (listing_id, check_in, check_out, status);

-- Sample data for testing
INSERT INTO listings (id, title, description, location, price_per_night, max_guests, bedrooms, bathrooms, amenities, rating, total_reviews, host_name, cancellation_policy)
VALUES
    ('LST-001', 'Sea Breeze Villa', 'Beachfront villa in Cox''s Bazar with sea views and modern amenities.', 'Cox''s Bazar', 4500.00, 4, 2, 1, ARRAY['Wi-Fi', 'AC', 'Kitchen', 'Beach Access', 'Parking'], 4.8, 124, 'Rahim Uddin', 'Free cancellation up to 48 hours before check-in'),
    ('LST-002', 'Ocean View Resort', 'Modern resort with pool access and stunning ocean views.', 'Cox''s Bazar', 6200.00, 6, 3, 2, ARRAY['Wi-Fi', 'AC', 'Pool', 'Restaurant', 'Parking'], 4.5, 89, 'Kamal Ahmed', 'Free cancellation up to 24 hours before check-in'),
    ('LST-003', 'Sylhet Tea Garden Cottage', 'Cozy cottage surrounded by lush tea gardens in Sylhet.', 'Sylhet', 3200.00, 3, 1, 1, ARRAY['Wi-Fi', 'AC', 'Garden View', 'Breakfast'], 4.9, 56, 'Fatima Begum', 'Non-refundable'),
    ('LST-004', 'Sundarbans Eco Lodge', 'Eco-friendly lodge near the Sundarbans mangrove forest.', 'Khulna', 5500.00, 5, 2, 2, ARRAY['Wi-Fi', 'Fan', 'Boat Tour', 'Meals Included'], 4.7, 42, 'Jamal Hossain', 'Free cancellation up to 72 hours before check-in'),
    ('LST-005', 'Bandarban Hill Retreat', 'Mountain retreat with panoramic views of the Chittagong Hill Tracts.', 'Bandarban', 3800.00, 4, 2, 1, ARRAY['Wi-Fi', 'Hiking Trails', 'Fireplace', 'Parking'], 4.6, 67, 'Aung Marma', 'Free cancellation up to 48 hours before check-in')
ON CONFLICT (id) DO NOTHING;

-- SQL test case 1: Search available listings in Cox's Bazar for 2 guests
SELECT
    l.id AS listing_id,
    l.title,
    l.location,
    l.price_per_night,
    'BDT' AS currency,
    l.max_guests,
    l.rating
FROM listings AS l
WHERE lower(l.location) = lower('Cox''s Bazar')
  AND l.max_guests >= 2
  AND l.is_active = true
  AND NOT EXISTS (
      SELECT 1
      FROM bookings AS b
      WHERE b.listing_id = l.id
        AND b.status IN ('confirmed', 'pending')
        AND b.check_in < DATE '2026-05-12'
        AND b.check_out > DATE '2026-05-10'
  )
ORDER BY l.price_per_night ASC, l.rating DESC NULLS LAST;

-- SQL test case 2: Get details of one listing
SELECT
    id AS listing_id,
    title,
    description,
    location,
    price_per_night,
    'BDT' AS currency,
    max_guests,
    bedrooms,
    bathrooms,
    amenities,
    rating,
    total_reviews,
    host_name,
    cancellation_policy
FROM listings
WHERE id = 'LST-003'
  AND is_active = true;

-- SQL test case 3: Create one booking if the listing is available
WITH selected_listing AS (
    SELECT id, price_per_night
    FROM listings
    WHERE id = 'LST-003'
      AND is_active = true
      AND max_guests >= 2
      AND NOT EXISTS (
          SELECT 1
          FROM bookings AS b
          WHERE b.listing_id = listings.id
            AND b.status IN ('confirmed', 'pending')
            AND b.check_in < DATE '2026-06-12'
            AND b.check_out > DATE '2026-06-10'
      )
    LIMIT 1
)
INSERT INTO bookings (
    id,
    listing_id,
    guest_name,
    check_in,
    check_out,
    guests,
    total_price,
    status
)
SELECT
    'BKG-SQL-TEST-001',
    id,
    'Nusrat Jahan',
    DATE '2026-06-10',
    DATE '2026-06-12',
    2,
    price_per_night * 2,
    'confirmed'
FROM selected_listing
ON CONFLICT (id) DO NOTHING
RETURNING id, listing_id, guest_name, total_price, status;

-- SQL test case 4: Check that the booked listing is blocked for overlapping dates
SELECT
    l.id AS listing_id,
    l.title
FROM listings AS l
WHERE l.id = 'LST-003'
  AND NOT EXISTS (
      SELECT 1
      FROM bookings AS b
      WHERE b.listing_id = l.id
        AND b.status IN ('confirmed', 'pending')
        AND b.check_in < DATE '2026-06-11'
        AND b.check_out > DATE '2026-06-09'
  );
