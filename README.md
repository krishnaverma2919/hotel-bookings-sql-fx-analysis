
# Multi-Currency Revenue Reporter

Converts realized hotel revenue into USD using exchange rates from the free
[Frankfurter FX API](https://api.frankfurter.app), and shows how much of the apparent
month-to-month revenue trend is real business change versus just the rupee moving.

---

## What it does

For every month of **Completed** bookings, the script computes realized revenue in INR,
then converts it to USD two different ways:

1. **Naive method:** applies *today's* exchange rate to every month (a common mistake
   in quick dashboards).
2. **FX-adjusted method:** applies *that month's own* historical exchange rate (the
   correct way to compare revenue across time in another currency).

It then quantifies the gap between the two, so a stakeholder can see how much of a
month-over-month revenue "trend" is genuine growth or decline versus pure currency noise.

---

## Files in this folder

| File                       | Purpose                                                    |
| -------------------------- | ---------------------------------------------------------- |
| `fx_revenue_reporter.py` | The script. Run this                                       |
| `README.md`              | This file                                                  |
| `hotel_bookings.csv`     | The dataset the script reads (must be in this same folder) |

---

## Requirements

- Python 3.8+
- `pandas` and `requests`
- An internet connection (the script calls `api.frankfurter.app` directly; no API key needed)

Install the two packages if you don't already have them:

```
pip install pandas requests
```

---

## How to run

1. Make sure `hotel_bookings.csv` is in the **same folder** as `fx_revenue_reporter.py`.
2. Open a terminal / PowerShell inside this folder (the `project` folder).
3. Run:

   ```
   python fx_revenue_reporter.py
   ```

   If `python` is not recognized on Windows, try `py fx_revenue_reporter.py`.

No arguments, config file, or API key needed.

---

## Expected output

```
Fetching FX data from Frankfurter (api.frankfurter.app)...
Loaded 12 months of realized (Completed) revenue.

            revenue_inr nominal_usd_today_rate fx_adjusted_usd historical_rate_used rate_source
month
2024-01   25,228,707.26             263,387.70      303,249.06             0.012020        live
2024-02   20,555,513.88             214,599.56      247,693.94             0.012050        live
2024-03   22,746,596.73             237,474.47      274,551.42             0.012070        live
2024-04   22,841,635.43             238,466.67      273,871.21             0.011990        live
2024-05   25,818,068.83             269,540.64      309,558.65             0.011990        live
2024-06   21,742,373.41             226,990.38      260,691.06             0.011990        live
2024-07   22,256,093.21             232,353.61      266,628.00             0.011980        live
2024-08   21,085,086.66             220,128.30      251,755.93             0.011940        live
2024-09   22,949,334.54             239,591.05      273,785.56             0.011930        live
2024-10   25,033,636.65             261,351.17      298,651.29             0.011930        live
2024-11   23,867,426.74             249,175.94      284,022.38             0.011900        live
2024-12   22,401,233.77             233,868.88      264,782.58             0.011820        live

--- Quantified insight (USD) ---
First-to-last month revenue growth, using TODAY'S rate for every month: -11.2%
First-to-last month revenue growth, using EACH month's OWN rate:        -12.7%
Difference attributable to FX movement between the two methods:         +1.5 points
Interpretation: a meaningful share of the apparent USD trend is FX noise, not real
revenue change; the FX-adjusted number is the one an international stakeholder
should actually look at.
```

**What to check in your own run:**

- **`rate_source` should say `live` on every row.** That means each month's rate was
  fetched from the API, not guessed or reused.
- **`historical_rate_used` should vary slightly month to month** (about `0.0118` to
  `0.0121`). If every row shows the same number, the API calls likely failed and the
  script fell back (see Troubleshooting).
- **`nominal_usd_today_rate` can differ slightly from the numbers above.** It uses the
  current day's spot rate, which changes daily. The `revenue_inr`, `fx_adjusted_usd`, and
  `historical_rate_used` columns are based on fixed historical rates and stay the same.

Result of the verified live run: **-11.2% (naive) vs. -12.7% (FX-adjusted)**, a
**+1.5 point** difference caused purely by the rupee's movement during 2024. The rate
moved from `0.012020` in January to `0.011820` in December.

---

## How to verify the rates are real

Pick any month from the output, for example `2024-05` with rate `0.011990`, and open this
URL in a browser:

```
https://api.frankfurter.app/2024-05-01?base=INR&symbols=USD
```

The `rates.USD` value in the JSON response should match the script's `2024-05` row. If it
does, the script is pulling genuine ECB reference rates, not hardcoded or simulated numbers.

---

## Troubleshooting

| Problem                                                                                                      | Likely cause                                                        | Fix                                                                                                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `cd : Cannot find path ...\project`                                                                        | Terminal is opened in the wrong folder                              | Use`cd` to reach the folder that directly contains `fx_revenue_reporter.py` (check with `dir` on Windows or `ls` on Mac/Linux)                                                                        |
| `ModuleNotFoundError: No module named 'requests'` (or `pandas`)                                          | Package not installed for this Python interpreter                   | `pip install pandas requests`, or `python -m pip install pandas requests` if multiple Pythons are installed                                                                                               |
| `FileNotFoundError: hotel_bookings.csv`                                                                    | CSV is not in the same folder as the script                         | Copy`hotel_bookings.csv` into this folder                                                                                                                                                                   |
| `[warn] ... request failed` on one or two months, but the run still finishes                               | A single API call timed out or the connection reset                 | The script retries once, then carries forward the last known rate. Check`rate_source`: it says `live` if the retry worked, or `carried-forward (API miss)` if not. The script does **not** crash. |
| Every row shows`today's rate (no historical data yet)`, or the report says "reporting revenue in INR only" | The API was unreachable for every call (firewall, no internet, VPN) | Check your connection, or try another network (for example a mobile hotspot) if a college or office firewall blocks`api.frankfurter.app`                                                                    |
| All rates show as`0.01` with no variation                                                                  | Display rounded to 2 decimal places                                 | Rates display with 6 decimal places in the current script. Make sure you are running the latest`fx_revenue_reporter.py`                                                                                     |

---

## Design decision

If a historical rate call for one month fails, the script **carries forward the last
successfully fetched rate** instead of failing that month or crashing the whole run. A
single flaky API call degrades the report slightly (one month reuses a nearby rate) rather
than losing the month entirely. Carried-forward rows are labeled in the `rate_source` column.

## Limitation

If the API is unreachable for the **current** rate too (not just one historical month), the
script has no rate to fall back on and reports revenue in **INR only**, clearly flagged,
rather than guessing a number. When run from a network that blocks `api.frankfurter.app`
entirely, the script prints a clear warning and completes without crashing, instead of
producing incorrect currency figures.
