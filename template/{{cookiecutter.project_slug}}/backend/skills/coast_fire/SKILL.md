---
name: coast_fire
description: >
  All FIRE variants: Coast FIRE (save now, stop investing), Barista FIRE (part-time
  work covers living costs), Lean FIRE (minimal budget), Fat FIRE (luxury retirement).
  Uses real market data. Compares all four variants side by side.
tags: [finance, retirement, fire, planning]
---

# Coast FIRE & FIRE Variants Skill

## When to use
User asks about: coast FIRE, barista FIRE, lean FIRE, fat FIRE, semi-retirement,
"how much do I need if I invest now and stop", different retirement styles.

## Execution plan

### STEP 1 — ask_user
Ask all questions in ONE `ask_user` call (a list). Because every question is asked at once,
you do NOT yet know the user's currency — so **never assume one (don't write "PLN", "$", etc.)**.
Instead each money question says **"in your local currency"** and includes a dedicated
currency question. **Every money question MUST also state the period (per month)** — keep all
cash flows on the SAME monthly basis. DO NOT mix monthly and annual across questions.

Use this exact wording:

- "What is your current age?"
- "At what age do you want to retire (traditional FIRE target)?"
- "What is your current invested portfolio balance? (total, in your local currency)"
- "How much do you save/invest **per month**? (in your local currency)"
- "What are your **monthly** living expenses? (in your local currency)"
- "Which country / currency do you use? (sets the inflation assumption)"
- "For Barista FIRE — how much could you realistically earn from part-time work **per month**?
  (in your local currency, enter 0 to skip)"

All money inputs are collected **per month**; STEP 2 converts them to annual figures.
Use the currency from the answer for all chart labels and the text summary.

### STEP 2 — run_python (real-data scenarios + drawdown + 5 charts)

```python
import asyncio, json as _json

# Fill from ask_user answers — ALL cash flows are collected PER MONTH
current_age       = ...
retirement_age    = ...
current_savings   = ...            # current portfolio total (not monthly)
monthly_savings   = ...            # saved/invested per month
monthly_expenses  = ...            # living expenses per month
barista_monthly   = ...            # part-time income per month (0 if skipping)
country           = "..."

# Convert monthly inputs to annual figures used below
annual_savings    = monthly_savings * 12
annual_expenses   = monthly_expenses * 12
barista_income    = barista_monthly * 12

# Fetch data
spy, inflation = await asyncio.gather(
    get_historical_annual_returns("SPY", years=20),
    get_inflation_rate(country),
)
inflation_rate = inflation["inflation_pct"] / 100

# Mean AND volatility from the REAL 20-year SPY return series (nominal %)
rets     = list(spy["annual_returns"].values())
n_rets   = len(rets)
mean_nom = sum(rets) / n_rets / 100
std_nom  = (sum((r/100 - mean_nom) ** 2 for r in rets) / n_rets) ** 0.5
band     = 0.5 * std_nom   # half-sigma: single-year vol overstates a 30-yr average

def to_real(nom):
    return (1 + nom) / (1 + inflation_rate) - 1

bull_r = to_real(mean_nom + band)   # optimistic market path
base_r = to_real(mean_nom)          # expected (real) return
bear_r = to_real(mean_nom - band)   # pessimistic market path
real_return = base_r

years_to_retire = retirement_age - current_age

# FIRE variants
swr = 0.04
fire_number    = annual_expenses / swr
lean_number    = (annual_expenses * 0.70) / swr
fat_number     = (annual_expenses * 2.0)  / swr
barista_gap    = max(0, annual_expenses - barista_income)
barista_number = barista_gap / swr
coast_number   = fire_number / ((1 + real_return) ** years_to_retire)

def years_to_reach(start, contrib, ret, target):
    p, y = float(start), 0
    while p < target and y < 60:
        p = p * (1 + ret) + contrib
        y += 1
    return y

fire_years    = years_to_reach(current_savings, annual_savings, real_return, fire_number)
lean_years    = years_to_reach(current_savings, annual_savings, real_return, lean_number)
fat_years     = years_to_reach(current_savings, annual_savings, real_return, fat_number)
barista_years = years_to_reach(current_savings, annual_savings, real_return, barista_number)
coast_years   = years_to_reach(current_savings, annual_savings, real_return, coast_number)
coast_age     = current_age + coast_years

# Coast age RANGE across market scenarios (the coast number itself shifts with returns)
def coast_age_for(ret):
    cn = fire_number / ((1 + ret) ** years_to_retire)
    return current_age + years_to_reach(current_savings, annual_savings, ret, cn)

coast_bull = coast_age_for(bull_r)   # earliest (good markets)
coast_base = coast_age
coast_bear = coast_age_for(bear_r)   # latest (poor markets)

print("Expected real return " + str(round(base_r*100, 1)) + "% | SPY 20y volatility " + str(round(std_nom*100, 1)) + "%")
print("Full FIRE:    $" + str(int(fire_number))    + " — age " + str(current_age + fire_years))
print("Lean FIRE:    $" + str(int(lean_number))    + " — age " + str(current_age + lean_years))
print("Fat FIRE:     $" + str(int(fat_number))     + " — age " + str(current_age + fat_years))
print("Barista FIRE: $" + str(int(barista_number)) + " — age " + str(current_age + barista_years))
print("Coast number: $" + str(int(coast_number))   + " — hit age " + str(coast_base) + " (range " + str(coast_bull) + "-" + str(coast_bear) + ")")

# Chart 1 — all FIRE numbers horizontal bar
fire_variants = [
    {"x": "Fat FIRE",    "target": int(fat_number)},
    {"x": "Full FIRE",   "target": int(fire_number)},
    {"x": "Barista FIRE","target": int(barista_number)},
    {"x": "Lean FIRE",   "target": int(lean_number)},
    {"x": "Coast Number","target": int(coast_number)},
]

# Chart 2 — MARKET SCENARIO FAN: portfolio to retirement under bear / expected / bull
scenario_data = []
pb = pm = pl = float(current_savings)
for y in range(years_to_retire + 1):
    age = current_age + y
    scenario_data.append({
        "age": age,
        "Bull":     round(pl/1000),
        "Expected": round(pm/1000),
        "Bear":     round(pb/1000),
    })
    pb = pb * (1+bear_r) + annual_savings
    pm = pm * (1+base_r) + annual_savings
    pl = pl * (1+bull_r) + annual_savings

# Chart 3 — RETIREMENT DRAWDOWN: project to retirement (invest, then coast), then spend.
# Does the money survive a normal market vs a prolonged bear market?
p_ret = float(current_savings)
for y in range(years_to_retire):
    age = current_age + y
    if age < coast_age:
        p_ret = p_ret * (1+base_r) + annual_savings
    else:
        p_ret = p_ret * (1+base_r)   # coasting: no more contributions
retire_portfolio = p_ret

draw_data    = []
bal_base     = retire_portfolio
bal_bear     = retire_portfolio
deplete_base = None
deplete_bear = None
for age in range(retirement_age, 96):
    draw_data.append({
        "age": age,
        "Expected Market": round(max(bal_base, 0)/1000),
        "Bear Market":     round(max(bal_bear, 0)/1000),
    })
    bal_base = bal_base * (1+base_r) - annual_expenses
    bal_bear = bal_bear * (1+bear_r) - annual_expenses
    if bal_base <= 0 and deplete_base is None:
        deplete_base = age
    if bal_bear <= 0 and deplete_bear is None:
        deplete_bear = age

last_base = "95+" if deplete_base is None else str(deplete_base)
last_bear = "95+" if deplete_bear is None else str(deplete_bear)
print("At retirement (age " + str(retirement_age) + "): $" + str(int(retire_portfolio)))
print("Money lasts to — expected market: " + last_base + ", bear market: " + last_bear)

# AntV — treemap: FIRE variants sized by required portfolio
# (treemap instead of funnel — the funnel chart injects hardcoded Chinese
#  "转化率" conversion-rate labels that cannot be disabled via the MCP tool)
treemap = [
    {"name": "Fat FIRE (age " + str(current_age+fat_years) + ")",    "value": int(fat_number)},
    {"name": "Full FIRE (age " + str(current_age+fire_years) + ")",  "value": int(fire_number)},
    {"name": "Barista (age " + str(current_age+barista_years) + ")", "value": int(barista_number)},
    {"name": "Lean FIRE (age " + str(current_age+lean_years) + ")",  "value": int(lean_number)},
    {"name": "Coast (age " + str(coast_base) + ")",                  "value": int(coast_number)},
]

# AntV — dual-axes: portfolio ($K columns) + annual contribution (line, right axis)
dual_ages  = [str(current_age + y) for y in range(min(fire_years+5, 35))]
dual_port  = []
dual_c     = []
p3 = float(current_savings)
max_c = annual_savings / 1000
for y in range(len(dual_ages)):
    dual_port.append(round(p3/1000))
    dual_c.append(round(max_c, 2) if (current_age + y) < coast_age else 0.0)
    p3 = p3 * (1+real_return) + annual_savings
dual_series = [
    {"type": "column", "data": dual_port, "axisYTitle": "Portfolio ($K)"},
    {"type": "line",   "data": dual_c,    "axisYTitle": "Annual Contribution ($K)"},
]

# Render ALL FIVE charts here. The generate_* AntV functions are callable
# right inside run_python — DO NOT defer them to a separate tool call.
await asyncio.gather(
    create_chart("bar", "Required Portfolio by FIRE Variant", fire_variants,
                 x_key="x", series=[{"key":"target","label":"Required Portfolio ($)"}]),
    create_chart("line", "Market Scenario Fan — Portfolio to Retirement", scenario_data,
                 series=[{"key":"Bull","color":"#22c55e"},{"key":"Expected","color":"#3b82f6"},{"key":"Bear","color":"#ef4444"}],
                 x_key="age", style={"x_label":"Age","y_label":"Portfolio ($K)","legend":True,"grid":True}),
    create_chart("line", "Retirement Drawdown — Will Your Money Last?", draw_data,
                 series=[{"key":"Expected Market","color":"#3b82f6"},{"key":"Bear Market","color":"#ef4444"}],
                 x_key="age", style={"x_label":"Age","y_label":"Portfolio ($K)","legend":True,"grid":True}),
    generate_treemap_chart("FIRE Variants — Required Portfolio", treemap),
    generate_dual_axes_chart("Portfolio Growth & Contributions by Age", dual_ages, dual_series,
                             axisXTitle="Age"),
)
print("Rendered 5 charts: 3 standard (bar + scenario fan + drawdown) + 2 AntV (treemap, dual-axes)")
```

### STEP 3 — text summary

Lead with the most interesting insight:
"You'll hit your **Coast FIRE number of $X around age Z** (range Z_bull–Z_bear depending
on markets). After that, you can stop investing entirely and still retire at 60 with $1.2M."

- **Coast age as a range**, not one number: "In strong markets you coast by {coast_bull};
  in a poor market it slips to {coast_bear}. Expected: {coast_base}." Anchor it in real data:
  "based on the S&P 500's actual 20-year volatility of {std}%."
- **Longevity check (the part most calculators skip):** "At retirement you'd have ~$X. In a
  normal market that lasts to 95+; in a prolonged bear market it runs dry at age {deplete_bear}.
  To be safe, {raise savings / trim expenses / delay retirement 2 yrs}."
- Side-by-side table: variant | target | years away | retire age
- Key levers: "Barista FIRE with $1,000/mo part-time cuts target by $300k, 6 years earlier"
