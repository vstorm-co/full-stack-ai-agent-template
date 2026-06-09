---
name: debt_optimizer
description: >
  Debt payoff optimizer. Compares avalanche (highest-interest-first) vs snowball
  (smallest-balance-first) strategies. Shows exact payoff timeline, total interest
  paid, and month-by-month balance for each debt. Includes extra-payment sensitivity.
tags: [finance, debt, planning]
---

# Debt Optimizer Skill

## When to use
User mentions: credit cards, loans, mortgage, debt, repayment plan,
how long to pay off, how much interest, debt-free date.

## Execution plan

### STEP 1 — ask_user
Collect: list of debts (name, balance, APR%, minimum monthly payment),
extra monthly amount available, currency/country.

### STEP 2 — run_python (simulate both strategies + 3 charts)

```python
import asyncio, json as _json

# Fill from ask_user answers
debts = [
    {"name": "Credit Card", "balance": 8000, "rate_annual": 24.0, "min_payment": 160},
    {"name": "Car Loan",    "balance": 12000,"rate_annual": 7.5,  "min_payment": 280},
    # ... add all debts
]
extra_monthly = 400   # extra to throw at debt

# Live expected market return — the bar that decides "pay down debt" vs "invest the extra".
# A debt's APR is a GUARANTEED, risk-free return from paying it off; compare it to what the
# same money could earn in the market (live S&P 500 20-year average).
spy = await get_historical_annual_returns("SPY", years=20)
market_return = spy["avg_annual_return"] / 100

def simulate(debts_sorted, extra_monthly):
    balances = {d["name"]: float(d["balance"]) for d in debts_sorted}
    monthly_history = []
    total_interest = 0.0
    month = 0
    while any(b > 0.01 for b in balances.values()) and month < 600:
        month += 1
        snapshot = {"month": month}
        available_extra = extra_monthly
        for debt in debts_sorted:
            name = debt["name"]
            if balances[name] <= 0:
                snapshot[name] = 0
                continue
            rate = debt["rate_annual"] / 100 / 12
            interest = balances[name] * rate
            total_interest += interest
            balances[name] += interest
            payment = min(debt["min_payment"], balances[name])
            balances[name] -= payment
            if balances[name] > 0 and available_extra > 0:
                extra = min(available_extra, balances[name])
                balances[name] -= extra
                available_extra -= extra
            snapshot[name] = round(max(balances[name], 0), 2)
        monthly_history.append(snapshot)
        if all(b <= 0.01 for b in balances.values()):
            break
    return monthly_history, round(total_interest, 2)

avalanche = sorted(debts, key=lambda d: d["rate_annual"], reverse=True)
snowball   = sorted(debts, key=lambda d: d["balance"])

hist_av, interest_av = simulate(avalanche, extra_monthly)
hist_sb, interest_sb = simulate(snowball,  extra_monthly)

months_av = len(hist_av)
months_sb = len(hist_sb)

print("Avalanche: " + str(months_av) + " months, interest $" + str(int(interest_av)))
print("Snowball:  " + str(months_sb) + " months, interest $" + str(int(interest_sb)))
print("Interest saved: $" + str(int(interest_sb - interest_av)))

# Prepay vs invest the extra — decided per debt by APR vs the live market return.
# APR is a guaranteed return; the market is an expected (not guaranteed) one.
print("Expected market return (live SPY 20y): " + str(round(market_return*100,1)) + "%/yr")
invest_candidates = []
for d in sorted(debts, key=lambda x: x["rate_annual"], reverse=True):
    apr = d["rate_annual"] / 100
    if apr > market_return:
        print(d["name"] + " @ " + str(d["rate_annual"]) + "% — PREPAY (guaranteed " + str(d["rate_annual"]) + "% beats the ~" + str(round(market_return*100,1)) + "% market)")
    else:
        invest_candidates.append(d["name"])
        print(d["name"] + " @ " + str(d["rate_annual"]) + "% — could INVEST the extra instead (market ~" + str(round(market_return*100,1)) + "% may beat this low rate)")

# Chart 1 — total balance over time (both strategies)
step = max(1, months_av // 40)
balance_chart = []
for i in range(0, months_av, step):
    row = {"month": i+1}
    if i < len(hist_av):
        row["Avalanche"] = round(sum(v for k, v in hist_av[i].items() if k != "month") / 1000, 1)
    if i < len(hist_sb):
        row["Snowball"]  = round(sum(v for k, v in hist_sb[i].items() if k != "month") / 1000, 1)
    balance_chart.append(row)

# Chart 2 — interest comparison bar
interest_chart = [
    {"x": "Avalanche", "interest": int(interest_av)},
    {"x": "Snowball",  "interest": int(interest_sb)},
]

# Chart 3 — individual debt stacked area (avalanche order)
debt_names = [d["name"] for d in avalanche]
area_data = []
for i in range(0, months_av, step):
    if i < len(hist_av):
        row = {"month": i+1}
        row.update({k: round(hist_av[i].get(k, 0)/1000, 1) for k in debt_names})
        area_data.append(row)

# AntV — waterfall: debt elimination cascade
total_debt = sum(d["balance"] for d in debts)
wf = [{"category": "Total Debt", "value": int(total_debt)}]
for d in avalanche:
    wf.append({"category": d["name"], "value": -int(d["balance"])})
wf.append({"category": "Debt Free", "isTotal": True})

# AntV — sankey: monthly cash flow toward debt
sankey = [{"source": "Monthly Income", "target": "Living Expenses", "value": 2500}]  # adjust
for d in debts:
    sankey.append({"source": "Monthly Income", "target": d["name"] + " (min)", "value": int(d["min_payment"])})
sankey.append({"source": "Monthly Income", "target": "Extra Payment", "value": int(extra_monthly)})

# Render ALL FIVE charts here. The generate_* AntV functions are callable
# right inside run_python — DO NOT defer them to a separate tool call.
await asyncio.gather(
    create_chart("line", "Total Debt Balance Over Time", balance_chart,
                 series=[{"key":"Avalanche","color":"#22c55e"},{"key":"Snowball","color":"#3b82f6"}],
                 x_key="month", style={"y_label":"Balance ($K)","legend":True,"grid":True}),
    create_chart("bar", "Total Interest Paid — Avalanche vs Snowball", interest_chart,
                 x_key="x", series=[{"key":"interest","label":"Total Interest ($)"}]),
    create_chart("area", "Debt Breakdown Over Time (Avalanche)", area_data,
                 series=[{"key": name} for name in debt_names], x_key="month",
                 style={"y_label":"Balance ($K)","stacked":True,"legend":True}),
    generate_waterfall_chart("Debt Elimination (Avalanche Order)", wf,
                             axisXTitle="Debt", axisYTitle="Balance ($)"),
    generate_sankey_chart("Monthly Cash Flow — Debt Payments", sankey),
)
print("Rendered 5 charts: 3 standard + 2 AntV (waterfall, sankey)")
```

### STEP 3 — text summary

- "Avalanche saves you **$X** in interest and clears debt **Y months** earlier."
- Summary table: debt | balance | rate | avalanche payoff month | snowball payoff month
- Key levers: "Adding $100/month cuts timeline by Z months."
- **Prepay vs invest** (uses the live SPY return): "Every debt above the ~{market_return}% expected
  market return — like your 24% card — is a *guaranteed* win to clear first. For anything below it
  (e.g. a 4% mortgage), investing the extra has a higher *expected* return than prepaying — though
  prepaying is risk-free. Your {invest_candidates} sit below the market line." Only raise the
  invest-instead angle when at least one debt's APR is below the live market return.
