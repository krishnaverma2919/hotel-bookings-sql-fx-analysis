# Multi-Currency Revenue Reporter (Set C)

Converts realized hotel revenue into USD using live exchange rates from the free
[Frankfurter FX API](https://api.frankfurter.app), and shows how much of the apparent
month-to-month revenue trend is real business change vs. just the rupee moving.

---

## What it does

For every month of **Completed** bookings, the script computes realized revenue in INR,
then converts it to USD two different ways:

1. **Naive method** — applies *today's* exchange rate to every month (the common mistake
   most quick dashboards make).
2. **FX-adjusted method** — applies *that month's own* historical exchange rate (the
   correct way to compare revenue across time in another currency).

It then quantifies the gap between the two, so a stakeholder can see how much of a
month-over-month revenue "trend" is genuine growth/decline versus pure currency noise.

---

## Files in this folder

| File | Purpose |
|---|---|
| `fx_revenue_reporter.py` | The script — run this |
| `README.md` | This file |
| `hotel_bookings.csv` | The dataset the script reads (must be in this same folder) |

---

## Requirements

- Python 3.8+
- `pandas` and `requests`
- A normal internet connection (the script calls `api.frankfurter.app` directly — no
  API key needed, it's a free/keyless public API)

Install the two packages if you don't already have them:

```
pip install pandas requests
```

---

## How to run

1. Make sure `hotel_bookings.csv` is in the **same folder** as `fx_revenue_reporter.py`
   (check with `dir` on Windows or `ls` on Mac/Linux — both files should show up together).
2. Open a terminal / PowerShell in that folder.
3. Run:

   ```
   python fx_revenue_reporter.py
   ```

That's it — no arguments, no config file, no API key to set up.

---

## What you should see (expected output)

```
Fetching FX data from Frankfurter (api.frankfurter.app)...
Loaded 12 months of realized (Completed) revenue.

           revenue_inr nominal_usd_today_rate fx_adjusted_usd historical_rate_used rate_source
month
2024-01  25,228,707.26             263,639.99      303,249.06             0.012020        live
2024-02  20,555,513.88             214,805.12      247,693.94             0.012050        live
...
2024-12  22,401,233.77             234,092.89      264,782.58             0.011820        live

--- Quantified insight (USD) ---
First-to-last month revenue growth, using TODAY'S rate for every month: -11.2%
First-to-last month revenue growth, using EACH month's OWN rate:        -12.7%
Difference attributable to FX movement between the two methods:         +1.5 points
Interpretation: a meaningful share of the apparent USD trend is FX noise, not real
revenue change — the FX-adjusted number is the one an international stakeholder
should actually look at.
```

- **`rate_source` should say `live` for every row.** That means each month's rate was
  genuinely fetched from the API, not guessed or reused.
- **`historical_rate_used` should be a small, slightly different number each month**
  (something like `0.0118`–`0.0121`) — if every row shows the exact same number, the
  API calls likely failed and it silently fell back (see Troubleshooting below).

This exact output was verified with a real, live run — Jan's rate was `0.012020`,
December's was `0.011820`, and the final insight was **-11.2% (naive) vs. -12.7%
(FX-adjusted)**, a **+1.5 point** difference caused purely by the rupee's movement
within 2024.

---

## How to verify it's really live (not faked)

Pick any month from the output — say `2024-05`, rate `0.011990` — and open this URL
directly in a browser:

```
https://api.frankfurter.app/2024-05-01?base=INR&symbols=USD
```

The `rates.USD` value in that JSON response should match the script's `2024-05` row.
If it does, the script is pulling genuine, live ECB reference rates — not hardcoded or
simulated numbers.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'requests'` (or `pandas`) | Package not installed for the Python interpreter you're running | `pip install pandas requests`, or `python -m pip install pandas requests` if multiple Pythons are installed |
| `FileNotFoundError: hotel_bookings.csv` | CSV isn't in the same folder as the script | Copy `hotel_bookings.csv` into this `project/` folder |
| `[warn] ... request failed` on one or two months, but the run still finishes | A single API call timed out or the connection was briefly reset — normal on some networks | The script automatically retries once, then carries forward the last known rate. Check `rate_source` — it'll say `live` if the retry succeeded, or `carried-forward (API miss)` if not. Either way the script does **not** crash. |
| Every row shows `rate_source = today's rate (no historical data yet)` or the report says `"reporting revenue in INR only"` | The API was unreachable for *every* call (firewall, no internet, VPN blocking it) | Check your internet connection; try a different network (e.g. mobile hotspot) if a college/office firewall is blocking `api.frankfurter.app` |
| All rates show as `0.01` with no variation | Display was rounded to 2 decimal places, hiding the real difference between months | Fixed in the current version of the script — rates now display with 6 decimal places. If you still see this, make sure you're running the latest version of `fx_revenue_reporter.py`. |

---

## Design decision

If a historical rate call for one month fails, the script **carries forward the last
successfully-fetched rate** instead of failing that month or crashing the whole run.
This means a single flaky API call degrades the report slightly (one month reuses a
nearby rate) rather than losing the month entirely.

## Limitation

If the API is unreachable for the **current** rate too (not just one historical month),
the script has no rate to fall back on and reports revenue in **INR only**, clearly
flagged, rather than guessing a number. This was tested directly: when run from a
network that blocks `api.frankfurter.app` entirely, the script printed a clear warning
and completed without crashing, instead of producing incorrect currency figures.