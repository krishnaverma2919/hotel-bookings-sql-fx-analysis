
-- BA Technical Assessment - Set C
-- Section 3: SQL Queries
-- ============================================================
-- Note: these queries are written against the normalized schema in
-- schema.sql, and were verified by executing them against the flat
-- hotel_bookings.csv (loaded as one table) - join logic is identical
-- either way, since customers/properties/bookings/reviews map 1:1
-- onto the flat CSV's columns.
-- ============================================================


-- ============================================================
-- C-Q1: Average total_amount by booking sequence (1st, 2nd, 3rd+)
-- ============================================================
-- Verified result:
--   sequence_label | avg_total  |  n
--   first          | 29765.24   | 4719
--   second         | 29328.32   | 1884
--   3-or-later     | 30197.68   | 2676
-- ------------------------------------------------------------

WITH numbered AS (
    SELECT
        customer_id,
        total_amount,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY checkin_date) AS seq
    FROM bookings
    WHERE booking_status = 'Completed'
),
labeled AS (
    SELECT
        CASE
            WHEN seq = 1 THEN 'first'
            WHEN seq = 2 THEN 'second'
            ELSE '3-or-later'
        END AS sequence_label,
        total_amount
    FROM numbered
)
SELECT
    sequence_label,
    ROUND(AVG(total_amount), 2) AS avg_total,
    COUNT(*) AS n
FROM labeled
GROUP BY sequence_label
ORDER BY CASE sequence_label
    WHEN 'first' THEN 1 WHEN 'second' THEN 2 ELSE 3 END;


-- ============================================================
-- C-Q2: Top 5 properties by normalized average review_rating (>=20 reviews)
-- ============================================================
-- Footnote 7: review_rating is on a 1-5 scale for Individual/Group customers,
-- but on a 1-10 scale for Corporate customers. Corporate ratings are divided
-- by 2 BEFORE averaging so every property's average is on a consistent 1-5 scale.
--
-- Verified result:
--   property_name      | property_city | num_reviews | normalized_avg_rating
--   Tusker Lodge        | Mumbai        | 91          | 3.95
--   Banyan Heights       | Mumbai        | 78          | 3.92
--   Crimson Residency    | Chennai       | 97          | 3.92
--   Mango Manor          | Jaipur        | 91          | 3.91
--   Pearl Retreat        | Mumbai        | 76          | 3.89
-- ------------------------------------------------------------

WITH normalized_reviews AS (
    SELECT
        b.property_id,
        CASE
            WHEN c.customer_segment = 'Corporate' THEN r.review_rating / 2.0
            ELSE r.review_rating
        END AS normalized_rating
    FROM reviews r
    JOIN bookings  b ON b.booking_id  = r.booking_id
    JOIN customers c ON c.customer_id = b.customer_id
)
SELECT
    p.property_name,
    p.property_city,
    COUNT(*) AS num_reviews,
    ROUND(AVG(nr.normalized_rating), 2) AS normalized_avg_rating
FROM normalized_reviews nr
JOIN properties p ON p.property_id = nr.property_id
GROUP BY p.property_id, p.property_name, p.property_city
HAVING COUNT(*) >= 20
ORDER BY normalized_avg_rating DESC
LIMIT 5;
