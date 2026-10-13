"""
Multi-Currency Revenue Reporter
Section 4 Mini-Project — Set C (BA Technical Assessment)

Converts realized (Completed) hotel revenue into USD/EUR/GBP using the free,
keyless Frankfurter FX API, and quantifies how much of the apparent monthly
revenue trend (in USD) is really just the rupee moving, vs. genuine business
growth — by comparing "today's spot rate applied to every month" (the naive,
common mistake) against "each month's own historical rate" (the correct way).

Run:  python fx_revenue_reporter.py
Needs: pandas, requests, hotel_bookings.csv in the same folder.
"""

import sys
import time
import requests
import pandas as pd

FRANKFURTER_LATEST = "https://api.frankfurter.app/latest"
FRANKFURTER_HISTORICAL = "https://api.frankfurter.app/{date}"
BASE_CURRENCY = "INR"
TARGET_CURRENCIES = ["USD", "EUR", "GBP"]
REQUEST_TIMEOUT = 8  # seconds
MAX_RETRIES = 2


# ---------------------------------------------------------------------------
# API layer — every call is wrapped so a timeout, a non-200 response, or a
# malformed body degrades gracefully instead of crashing the run.
# ---------------------------------------------------------------------------

def _get_json(url, params, what):
    """Fetch a URL and return parsed JSON, or None on any failure."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            print(f"[warn] {what}: timed out (attempt {attempt}/{MAX_RETRIES})")
        except requests.exceptions.RequestException as e:
            print(f"[warn] {what}: request failed ({e}) (attempt {attempt}/{MAX_RETRIES})")
        except ValueError:
            print(f"[warn] {what}: response was not valid JSON")
            return None
        time.sleep(0.5)
    print(f"[warn] {what}: giving up after {MAX_RETRIES} attempts — continuing without this data")
    return None


def get_latest_rates(base=BASE_CURRENCY, symbols=TARGET_CURRENCIES):
    """GET /latest — today's spot rate. Returns a dict {symbol: rate} or None."""
    data = _get_json(FRANKFURTER_LATEST, {"base": base, "symbols": ",".join(symbols)},
                      "latest rates")
    if data is None or "rates" not in data:
        return None
    return data["rates"]


def get_historical_rate(date_str, base=BASE_CURRENCY, symbol="USD"):
    """GET /{date} — the ECB reference rate for that specific date (or the
    prior business day if it fell on a weekend/holiday). Returns a float or None."""
    url = FRANKFURTER_HISTORICAL.format(date=date_str)
    data = _get_json(url, {"base": base, "symbols": symbol}, f"historical rate for {date_str}")
    if data is None or "rates" not in data or symbol not in data["rates"]:
        return None
    return data["rates"][symbol]


# ---------------------------------------------------------------------------
# Data prep — realized (Completed) revenue by check-in month, from the CSV.
# ---------------------------------------------------------------------------

def load_monthly_revenue(csv_path="hotel_bookings.csv"):
    df = pd.read_csv(csv_path, keep_default_na=False)
    df["checkin_date"] = pd.to_datetime(df["checkin_date"])
    completed = df[df["booking_status"] == "Completed"].copy()
    completed["checkin_month"] = completed["checkin_date"].dt.to_period("M")
    monthly = completed.groupby("checkin_month")["total_amount"].sum().sort_index()
    return monthly  # Series indexed by Period('M'), values in INR


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def build_report(monthly_inr_revenue, currency="USD"):
    """
    For each month, compute:
      - nominal_usd   = INR revenue * TODAY's spot rate (the naive approach)
      - fx_adjusted   = INR revenue * THAT MONTH's own historical rate (correct)
    Missing historical rates fall back to the nearest earlier month's rate that
    *was* successfully fetched, so one bad API call never blanks out a whole
    report — it just reuses the last known-good rate and is flagged as such.
    """
    today_rates = get_latest_rates()
    if today_rates is None:
        print("[warn] Could not reach the FX API for a current rate — "
              "reporting revenue in INR only.")
        report = monthly_inr_revenue.to_frame("revenue_inr")
        report["fx_data_available"] = False
        return report

    today_rate = today_rates[currency]

    rows = []
    last_known_rate = None
    any_historical_fetched = False

    for period, revenue_inr in monthly_inr_revenue.items():
        # Use the first business day of the month as the representative date
        month_date = period.to_timestamp().strftime("%Y-%m-%d")
        rate = get_historical_rate(month_date, symbol=currency)

        if rate is not None:
            last_known_rate = rate
            any_historical_fetched = True
            rate_source = "live"
        elif last_known_rate is not None:
            rate = last_known_rate
            rate_source = "carried-forward (API miss)"
        else:
            rate = today_rate
            rate_source = "today's rate (no historical data yet)"

        rows.append({
            "month": str(period),
            "revenue_inr": revenue_inr,
            "nominal_usd_today_rate": revenue_inr * today_rate,
            "fx_adjusted_usd": revenue_inr * rate,
            "historical_rate_used": rate,
            "rate_source": rate_source,
        })

    report = pd.DataFrame(rows).set_index("month")
    report.attrs["fx_data_available"] = any_historical_fetched
    report.attrs["today_rate"] = today_rate
    return report


def quantify_trend_difference(report, currency="USD"):
    """
    Compare the month-over-month % trend under the naive (today's-rate)
    method vs. the FX-adjusted (each month's own rate) method, and state how
    much of the apparent trend is really just currency movement.
    """
    if "fx_adjusted_usd" not in report.columns:
        print("No FX-adjusted figures available (API was unreachable) — "
              "trend comparison skipped.")
        return

    nominal = report["nominal_usd_today_rate"]
    adjusted = report["fx_adjusted_usd"]

    nominal_growth = (nominal.iloc[-1] / nominal.iloc[0] - 1) * 100
    adjusted_growth = (adjusted.iloc[-1] / adjusted.iloc[0] - 1) * 100

    # Because "nominal" applies ONE constant rate to every month, its
    # month-to-month % SHAPE is identical to the raw INR series — any
    # difference from "adjusted" growth is purely the FX effect.
    fx_contribution = nominal_growth - adjusted_growth

    print(f"\n--- Quantified insight ({currency}) ---")
    print(f"First-to-last month revenue growth, using TODAY'S rate for every month: {nominal_growth:+.1f}%")
    print(f"First-to-last month revenue growth, using EACH month's OWN rate:        {adjusted_growth:+.1f}%")
    print(f"Difference attributable to FX movement between the two methods:         {fx_contribution:+.1f} points")
    if abs(fx_contribution) < 1:
        print("Interpretation: the rupee barely moved WITHIN the analysis window, so "
              "the naive method mainly mis-states the absolute dollar level (via "
              "today's much-later spot rate), not the shape of the trend.")
    else:
        print("Interpretation: a meaningful share of the apparent USD trend is FX "
              "noise, not real revenue change — the FX-adjusted number is the one "
              "an international stakeholder should actually look at.")


def main():
    print("Fetching FX data from Frankfurter (api.frankfurter.app)...")
    monthly_revenue = load_monthly_revenue()
    print(f"Loaded {len(monthly_revenue)} months of realized (Completed) revenue.\n")

    report = build_report(monthly_revenue, currency="USD")

    # Format each column at the precision it actually needs — a blanket 2-decimal
    # format would round every INR/USD rate (~0.011-0.012) down to "0.01" and hide
    # the real month-to-month variation.
    display_report = report.copy()
    for col in ["revenue_inr", "nominal_usd_today_rate", "fx_adjusted_usd"]:
        if col in display_report.columns:
            display_report[col] = display_report[col].map(lambda x: f"{x:,.2f}")
    if "historical_rate_used" in display_report.columns:
        display_report["historical_rate_used"] = display_report["historical_rate_used"].map(lambda x: f"{x:.6f}")
    print(display_report)

    quantify_trend_difference(report, currency="USD")


if __name__ == "__main__":
    main()