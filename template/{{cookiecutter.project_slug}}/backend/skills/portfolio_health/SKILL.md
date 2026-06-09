---
name: portfolio_health
description: >
  Portfolio allocation analysis. Fetches live market data (10y return history per holding),
  computes value-weighted expected return & volatility, compares current vs target allocation,
  scores diversification (HHI), and generates exact rebalancing trades.
tags: [finance, portfolio, investing, allocation]
---

# Portfolio Health Skill

## When to use
User mentions: portfolio, asset allocation, rebalance, diversification, how is my portfolio,
what should I buy/sell, portfolio drift, stocks vs bonds allocation.

## Execution plan

### STEP 1 — ask_user
Collect: holdings (ticker or name + current value), target allocation % per asset class,
cash available to invest, currency.

### STEP 2 — run_python (fetch prices + calculate + 3 charts)

```python
import asyncio, json as _json

# Fill from ask_user answers
holdings = [
    {"name": "S&P 500 ETF", "ticker": "SPY",     "value": 45000, "asset_class": "US Stocks"},
    {"name": "MSCI World",  "ticker": "IWDA.AS",  "value": 25000, "asset_class": "International"},
    {"name": "Bond ETF",    "ticker": "BND",       "value": 15000, "asset_class": "Bonds"},
    {"name": "Cash",        "ticker": None,         "value": 10000, "asset_class": "Cash"},
]
target_allocation = {"US Stocks": 50, "International": 30, "Bonds": 15, "Cash": 5}
cash_to_invest = 5000

# Fetch live market data (10y return history) for every holding with a ticker
tickers = [h["ticker"] for h in holdings if h["ticker"]]
hist = await asyncio.gather(*[get_historical_annual_returns(t, years=10) for t in tickers]) if tickers else []

# Per-ticker expected return + volatility, straight from the REAL return series
exp_ret_by_ticker = {}
vol_by_ticker = {}
for t, d in zip(tickers, hist):
    rs = list(d.get("annual_returns", {}).values())
    if rs:
        m = sum(rs) / len(rs) / 100
        exp_ret_by_ticker[t] = m
        vol_by_ticker[t] = (sum((r/100 - m) ** 2 for r in rs) / len(rs)) ** 0.5
    else:
        exp_ret_by_ticker[t] = 0.0
        vol_by_ticker[t] = 0.0

# Value-weighted portfolio expected return + volatility (invested holdings only)
invested_value = sum(h["value"] for h in holdings if h["ticker"])
exp_return = sum(h["value"]/invested_value * exp_ret_by_ticker.get(h["ticker"], 0) for h in holdings if h["ticker"]) if invested_value > 0 else 0.0
port_vol   = sum(h["value"]/invested_value * vol_by_ticker.get(h["ticker"], 0)  for h in holdings if h["ticker"]) if invested_value > 0 else 0.0

# Current weights
total_value = sum(h["value"] for h in holdings) + cash_to_invest
for h in holdings:
    h["weight_pct"] = round(h["value"] / total_value * 100, 1)

# Group by asset class
current_alloc = {}
current_values = {}
for h in holdings:
    cls = h["asset_class"]
    current_alloc[cls]  = round(current_alloc.get(cls, 0) + h["weight_pct"], 1)
    current_values[cls] = current_values.get(cls, 0) + h["value"]

# Drift from target
drift = {cls: round(current_alloc.get(cls, 0) - tgt, 1) for cls, tgt in target_allocation.items()}

# Rebalancing trades
new_total = total_value
trades = {cls: round(new_total * tgt/100 - current_values.get(cls, 0), 0)
          for cls, tgt in target_allocation.items()}

# Diversification score — HHI computed on ASSET CLASS weights (current_alloc),
# not on individual tickers. Asset-class HHI measures allocation spread across
# categories (US Stocks, Bonds, etc.); per-ticker HHI only counts positions and
# ignores that several tickers in the same class add no real diversification.
weights = list(current_alloc.values())
hhi = sum((w/100)**2 for w in weights)
diversity_score = round((1 - hhi) * 100)

print("Total portfolio: $" + str(int(total_value)))
print("Diversification score: " + str(diversity_score) + "/100")
print("Expected return: " + str(round(exp_return*100,1)) + "%/yr, volatility " + str(round(port_vol*100,1)) + "% (live 10y history)")
for cls, d in drift.items():
    flag = "OVERWEIGHT" if d > 5 else ("UNDERWEIGHT" if d < -5 else "ok")
    print(cls + ": " + str(current_alloc.get(cls,0)) + "% (target " + str(target_allocation[cls]) + "%) — " + flag)

# Chart 1 — current allocation pie
pie_data = [{"x": cls, "value": pct} for cls, pct in current_alloc.items()]

# Chart 2 — rebalancing bar (buy/sell amounts)
rebal_data = [{"x": cls, "amount": int(amt)} for cls, amt in trades.items()]

# Chart 3 — current vs target grouped bar
cvt_data = [{"x": cls,
              "current": current_alloc.get(cls, 0),
              "target": target_allocation.get(cls, 0)}
             for cls in target_allocation]

# AntV — radar: portfolio health score (0–100 per dimension)
drift_score   = max(0, 100 - int(sum(abs(d) for d in drift.values()) * 3))
geo_score     = 75 if len([h for h in holdings if h["asset_class"] == "International"]) > 0 else 35
risk_score    = max(0, min(100, round(100 - port_vol * 280)))   # lower live volatility → higher
return_score  = max(0, min(100, round(exp_return * 1000)))       # ~10%/yr expected return → 100
radar = [
    {"name": "Diversification",   "value": diversity_score},
    {"name": "Return Potential",  "value": return_score},
    {"name": "Geographic Spread", "value": geo_score},
    {"name": "Target Alignment",  "value": drift_score},
    {"name": "Risk Balance",      "value": risk_score},
]

# AntV — treemap: holdings grouped by asset class
class_groups = {}
for h in holdings:
    class_groups.setdefault(h["asset_class"], []).append({"name": h["name"], "value": int(h["value"])})
treemap = [{"name": cls, "value": int(sum(c["value"] for c in ch)), "children": ch}
           for cls, ch in class_groups.items()]

# Render ALL FIVE charts here. The generate_* AntV functions are callable
# right inside run_python — DO NOT defer them to a separate tool call.
await asyncio.gather(
    create_chart("pie", "Current Portfolio Allocation", pie_data),
    create_chart("bar", "Rebalancing Actions (+ buy  /  − sell)", rebal_data,
                 x_key="x", series=[{"key":"amount","label":"Amount ($)"}]),
    create_chart("bar", "Current vs Target Allocation (%)", cvt_data, x_key="x",
                 series=[{"key":"current","label":"Current %"},{"key":"target","label":"Target %"}]),
    generate_radar_chart("Portfolio Health Score", radar),
    generate_treemap_chart("Portfolio Breakdown by Asset Class", treemap),
)
print("Rendered 5 charts: 3 standard + 2 AntV (radar, treemap)")
```

### STEP 3 — text summary

- Portfolio snapshot: total value, positions count, diversification score X/100
- Expected return & risk: "Your mix targets ~X%/yr at Y% volatility, computed from each
  holding's live 10-year return history."
- Risk flags: "⚠ You are 15% overweight in US Stocks vs your 50% target"
- Rebalancing table: asset class | current % | target % | action (buy/sell $X)
- "With $5,000 cash you can rebalance without selling any positions."
