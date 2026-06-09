---
name: savings_goals
description: >
  Goal-based savings planner for multiple simultaneous goals (house, emergency fund,
  car, vacation, education). Allocates monthly savings by priority, shows which goals
  are on track, and projects completion dates.
tags: [finance, savings, goals, planning]
---

# Savings Goals Skill

## When to use
User mentions: saving for a house, car, vacation, emergency fund, wedding, education,
multiple savings goals, can I afford X by Y date, how long to save.

## Execution plan

### STEP 1 — ask_user
Collect: each goal (name + target amount + deadline or "ASAP"), monthly savings available
(per month, in the user's local currency), existing savings per goal (or total),
whether to invest vs keep in cash, country/currency (the country sets the inflation assumption).

### STEP 2 — run_python (allocate + simulate + 3 charts)

```python
import asyncio, json as _json

# Fill from ask_user answers
goals = [
    {"name": "Emergency Fund",    "target": 20000, "months_left": 6,  "saved": 5000,  "priority": 1},
    {"name": "House Down Payment","target": 80000, "months_left": 48, "saved": 12000, "priority": 2},
    {"name": "New Car",           "target": 25000, "months_left": 24, "saved": 3000,  "priority": 3},
    {"name": "Japan Holiday",     "target": 5000,  "months_left": 10, "saved": 800,   "priority": 4},
]
monthly_savings = 2500
investing = True
country = "..."   # sets the inflation assumption

# Live data: SPY long-run return (for the investing case) + local inflation
spy, inflation = await asyncio.gather(
    get_historical_annual_returns("SPY", years=20),
    get_inflation_rate(country),
)
inflation_rate = inflation["inflation_pct"] / 100
market_return  = spy["avg_annual_return"] / 100

# Investing → live market return; cash → roughly tracks inflation (no real growth)
annual_return  = market_return if investing else inflation_rate
monthly_return = (1 + annual_return) ** (1/12) - 1
print("Return assumption: " + str(round(annual_return*100,1)) + "%/yr (" + ("invested @ live SPY" if investing else "cash ~ inflation") + "), inflation " + str(round(inflation_rate*100,1)) + "%")

def required_monthly(target, saved, months, rate):
    if months <= 0:
        return 0
    fv_saved = saved * ((1+rate)**months)
    if rate > 0:
        return max(0, (target - fv_saved) * rate / ((1+rate)**months - 1))
    return max(0, (target - fv_saved) / months)

# Allocate by priority
required = {g["name"]: required_monthly(g["target"], g["saved"], g["months_left"], monthly_return)
            for g in goals}
total_req = sum(required.values())
shortfall = max(0, total_req - monthly_savings)

# Scale down proportionally if shortfall
scale = monthly_savings / total_req if total_req > monthly_savings else 1.0
allocations = {g["name"]: round(required[g["name"]] * scale, 2) for g in goals}

for g in goals:
    name = g["name"]
    status = "on track" if required[name] <= allocations[name] + 1 else "at risk"
    print(name + ": need $" + str(int(required[name])) + "/mo, getting $" + str(int(allocations[name])) + "/mo — " + status)
if shortfall > 0:
    print("Shortfall: $" + str(int(shortfall)) + "/mo to hit all goals on time")

# Month-by-month simulation (60 months)
balances = {g["name"]: float(g["saved"]) for g in goals}
history  = []
for m in range(1, 61):
    for g in goals:
        name = g["name"]
        if balances[name] >= g["target"]:
            balances[name] = g["target"]
            continue
        balances[name] = min(balances[name] * (1+monthly_return) + allocations[name], g["target"])
    history.append({"month": m, **{g["name"]: int(balances[g["name"]]) for g in goals}})

# Chart 1 — stacked area progress
step = max(1, len(history) // 40)
area_data = history[::step]

# Chart 2 — months until each goal is reached
months_chart = []
for g in goals:
    months_to_reach = 0
    b = float(g["saved"])
    while b < g["target"] and months_to_reach < 120:
        b = b * (1+monthly_return) + allocations[g["name"]]
        months_to_reach += 1
    months_chart.append({"x": g["name"], "months": months_to_reach})

# Chart 3 — monthly allocation pie
alloc_pie = [{"x": g["name"], "value": int(allocations[g["name"]])} for g in goals]

goal_names = [g["name"] for g in goals]

# AntV — sankey: how monthly savings is split across goals
# (sankey instead of funnel — the funnel chart injects hardcoded Chinese
#  "转化率" conversion-rate labels that cannot be disabled via the MCP tool)
sankey = [{"source": "Monthly Savings", "target": g["name"], "value": int(allocations[g["name"]])}
          for g in goals if allocations[g["name"]] > 0]

# AntV — treemap: saved vs remaining per goal
treemap = [{"name": g["name"], "value": int(g["target"]),
             "children": [{"name": "Saved", "value": int(g["saved"])},
                          {"name": "Remaining", "value": int(max(0, g["target"]-g["saved"]))}]}
           for g in goals]

# Render ALL FIVE charts here. The generate_* AntV functions are callable
# right inside run_python — DO NOT defer them to a separate tool call.
await asyncio.gather(
    create_chart("area", "Savings Progress Per Goal", area_data,
                 series=[{"key": name} for name in goal_names], x_key="month",
                 style={"stacked":True,"y_label":"Total Saved ($)","legend":True}),
    create_chart("bar", "Months Until Each Goal Is Reached", months_chart,
                 x_key="x", series=[{"key":"months","label":"Months to Goal"}]),
    create_chart("pie", "Monthly Savings Allocation", alloc_pie),
    generate_sankey_chart("Monthly Savings Allocation Flow", sankey),
    generate_treemap_chart("Savings Goals — Progress Overview", treemap),
)
print("Rendered 5 charts: 3 standard + 2 AntV (sankey, treemap)")
```

### STEP 3 — text summary

- Status per goal: ✅ on track | ⚠ tight | ❌ not reachable at current rate
- If shortfall: "You need $X/mo more to hit all goals on time. Prioritise:"
- Suggestions: "Pushing car purchase 6 months later frees $Y/mo for the house."
- Inflation note (uses the live rate): "A goal worth $X in N years is only ~$Y in today's
  money at {inflation}% inflation — bump long-dated targets so they keep their real value."
- Return note: state the assumption used — "invested at the S&P 500's live 20-yr average of
  {market_return}%, vs cash tracking inflation."
