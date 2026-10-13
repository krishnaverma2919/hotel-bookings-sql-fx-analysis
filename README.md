# Hotel Bookings: SQL Modeling & FX-Adjusted Revenue Analysis

Analysis of a 12,000-row hotel bookings dataset covering relational schema design, SQL queries with window functions, and a Python tool that separates real revenue trends from INR→USD currency movement.

**Tech stack:** SQL · Python · pandas · Jupyter · REST API (Frankfurter)

---

## Project Overview

The project has three parts:

1. **Schema design:** normalize a flat 28-column CSV into a 4-table relational schema with constraints and an index.
2. **SQL analysis:** window functions and rating-scale normalization to answer business questions.
3. **FX revenue reporter:** a Python script that pulls historical exchange rates and shows how much of the apparent USD revenue trend is just rupee movement.

---

## Repository Structure

```
hotel-bookings-sql-fx-analysis/
├── README.md
├── LICENSE
├── code/
│   ├── schema.sql
│   ├── queries.sql
│   ├── analysis_notebook.ipynb
│   └── hotel_bookings.csv
└── project/
    ├── fx_revenue_reporter.py
    ├── hotel_bookings.csv
    └── README.md
```

---

## 1. Schema Design (`code/schema.sql`)

The flat CSV is split into four tables:

| Table          | Purpose                                                         |
| -------------- | --------------------------------------------------------------- |
| `customers`  | Customer profile, segment, loyalty tier                         |
| `properties` | Property details, with`UNIQUE (property_name, property_city)` |
| `bookings`   | Stay details, pricing, channel, status                          |
| `reviews`    | One review per booking (1:1)                                    |

Design decisions:

- **Data-quality rules as constraints:** `CHECK (checkout_date > checkin_date)`, positive room counts and nights, non-negative amounts.
- **Duplicate property names:** the same name appears in different cities with different IDs, so queries group on `property_id`, never on name alone.
- **Reviews in their own table:** a review on a cancelled booking becomes an explicit, checkable rule violation instead of a silent blank column.
- **`DECIMAL` for all money columns** to avoid floating-point drift in aggregates.
- **Composite index** on `bookings (customer_id, checkin_date)` to speed up the per-customer window function in Query 1.

---

## 2. SQL Queries (`code/queries.sql`)

### Q1: Average booking value by booking sequence

Uses `ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY checkin_date)` on completed bookings.

| Sequence     | Avg total amount | Bookings |
| ------------ | ---------------- | -------- |
| First        | 29,765.24        | 4,719    |
| Second       | 29,328.32        | 1,884    |
| 3rd or later | 30,197.68        | 2,676    |

Repeat customers do not spend noticeably more or less per booking than first-time customers.

### Q2: Top 5 properties by normalized rating (min. 20 reviews)

Reviews use a 1-5 scale for Individual/Group customers but 1-10 for Corporate customers. Corporate ratings are divided by 2 **before** averaging so all properties are compared on one scale.

| Property          | City    | Reviews | Normalized avg rating |
| ----------------- | ------- | ------- | --------------------- |
| Tusker Lodge      | Mumbai  | 91      | 3.95                  |
| Banyan Heights    | Mumbai  | 78      | 3.92                  |
| Crimson Residency | Chennai | 97      | 3.92                  |
| Mango Manor       | Jaipur  | 91      | 3.91                  |
| Pearl Retreat     | Mumbai  | 76      | 3.89                  |

---

## 3. Exploratory Analysis (`code/analysis_notebook.ipynb`)

Jupyter notebook with data cleaning and exploratory analysis of the bookings data.

<!-- Add 2-3 key findings from your notebook here, e.g.:
- Finding 1
- Finding 2
-->

---

## 4. FX Revenue Reporter (`project/`)

Converts realized (Completed) monthly revenue from INR to USD two ways:

- **Naive:** applies today's exchange rate to every month.
- **FX-adjusted:** applies each month's own historical rate (ECB reference rates via the free [Frankfurter API](https://api.frankfurter.app)).

**Result:** first-to-last month revenue growth was **-11.2%** with the naive method and **-12.7%** with the FX-adjusted method, a **1.5 point** gap caused purely by the rupee's movement within the year.

**Takeaway:** converting historical revenue at today's rate quietly distorts trends. Use each period's own rate when comparing across time.

Error handling: API calls use timeouts and retries. If a historical rate is missing, the last known rate is carried forward and flagged in the output. If the API is fully unreachable, the report falls back to INR only instead of guessing numbers.

See [`project/README.md`](project/README.md) for full details.

---

## How to Run

```bash
pip install pandas requests
cd project
python fx_revenue_reporter.py
```

The script reads `hotel_bookings.csv` from the same folder (`project/`), so it runs as-is.

For the SQL files in `code/`, load `hotel_bookings.csv` into your database of choice (PostgreSQL, SQLite, etc.) and run `schema.sql`, then `queries.sql`.

---

## Skills Demonstrated

- Relational data modeling and normalization
- Constraints, indexing, and query optimization
- Window functions and CTEs
- Data cleaning and handling inconsistent scales
- API integration with error handling and graceful degradation
- Translating analysis into business insight
