-- ============================================================
-- BA Technical Assessment - Set C
-- Section 3: Normalized Schema Design
-- ============================================================
-- Denormalized source: hotel_bookings.csv (12,000 rows, 28 columns)
-- Normalized into 4 tables: customers, properties, bookings, reviews
-- ============================================================

-- ===========================================================
-- CUSTOMERS
-- ===========================================================
CREATE TABLE customers (
    customer_id             INTEGER        PRIMARY KEY,
    customer_name           VARCHAR(100)   NOT NULL,
    customer_segment        VARCHAR(20)    NOT NULL,   -- Individual / Corporate / Group
    customer_signup_date    DATE           NOT NULL,
    customer_home_city      VARCHAR(50)    NOT NULL,
    customer_loyalty_tier   VARCHAR(10)    NOT NULL    -- 'None' / Silver / Gold / Platinum
);

-- ===========================================================
-- PROPERTIES
-- ===========================================================
CREATE TABLE properties (
    property_id             INTEGER        PRIMARY KEY,
    property_name           VARCHAR(100)   NOT NULL,
    property_city           VARCHAR(50)    NOT NULL,
    property_star_rating    SMALLINT       NOT NULL CHECK (property_star_rating BETWEEN 1 AND 5),
    property_type           VARCHAR(30)    NOT NULL,
    property_total_rooms    INTEGER        NOT NULL CHECK (property_total_rooms > 0),

    -- Footnote 5: property_name repeats across cities with DIFFERENT property_ids.
    -- This constraint guarantees one (name, city) pair never maps to two
    -- different property rows, without ever grouping on property_name alone.
    UNIQUE (property_name, property_city)
);

-- ===========================================================
-- BOOKINGS
-- ===========================================================
CREATE TABLE bookings (
    booking_id           INTEGER         PRIMARY KEY,
    customer_id          INTEGER         NOT NULL REFERENCES customers(customer_id),
    property_id          INTEGER         NOT NULL REFERENCES properties(property_id),
    booking_date         DATE            NOT NULL,
    checkin_date         DATE            NOT NULL,
    checkout_date        DATE            NOT NULL,
    room_type            VARCHAR(20)     NOT NULL,     -- Standard / Deluxe / Suite
    num_rooms            SMALLINT        NOT NULL CHECK (num_rooms > 0),    -- Footnote 3
    nights               SMALLINT        NOT NULL CHECK (nights > 0),
    booking_channel      VARCHAR(20)     NOT NULL,     -- Direct Website / OTA / Travel Agent / Corporate Portal
    adr                  DECIMAL(10,2)   NOT NULL CHECK (adr > 0),
    discount_amount      DECIMAL(10,2)   NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    coupon_code          VARCHAR(20),                   -- NULL = no coupon (Footnote 4 normalized at load time)
    total_amount         DECIMAL(12,2)   NOT NULL CHECK (total_amount >= 0),
    payment_method       VARCHAR(20)     NOT NULL,
    booking_status       VARCHAR(15)     NOT NULL,      -- Completed / Cancelled / No-Show

    -- Footnote 1: checkout on or before checkin is a data error.
    CHECK (checkout_date > checkin_date)
);

-- ===========================================================
-- REVIEWS  (1:1 with bookings - a booking has at most one review)
-- ===========================================================
CREATE TABLE reviews (
    review_id       INTEGER         PRIMARY KEY,
    booking_id      INTEGER         NOT NULL UNIQUE REFERENCES bookings(booking_id),
    review_rating   DECIMAL(3,1)    NOT NULL,   -- raw scale: 1-5 (Individual/Group) or 1-10 (Corporate) - Footnote 7
    review_date     DATE            NOT NULL
);

-- ===========================================================
-- INDEX
-- ===========================================================
-- Justification: C-Q1 partitions and orders by (customer_id, checkin_date) for
-- every completed booking. Without an index, ROW_NUMBER() OVER
-- (PARTITION BY customer_id ORDER BY checkin_date) forces a full-table sort on
-- every run. This composite index lets the engine read each customer's
-- bookings pre-sorted, turning that sort into a fast index scan.
CREATE INDEX idx_bookings_customer_checkin ON bookings (customer_id, checkin_date);

-- ===========================================================
-- DESIGN NOTES
-- ===========================================================
-- 1. booking_status / customer_segment kept as VARCHAR with app-level
--    validation rather than a DB-level CHECK IN (...) list, since new
--    statuses/segments are a plausible business change that shouldn't
--    require a schema migration.
-- 2. Reviews are a separate table (not a nullable column on bookings) so
--    that Footnote 6 (a review on a Cancelled booking) is an explicit,
--    checkable business-rule violation rather than a silently blank column.
-- 3. All money columns use DECIMAL, never FLOAT/REAL, to avoid rounding
--    drift on aggregates like total_amount.
