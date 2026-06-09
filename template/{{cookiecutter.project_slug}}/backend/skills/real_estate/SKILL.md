---
name: real_estate
description: >
  Rent vs Buy analysis and mortgage calculator. Computes true cost of ownership
  (mortgage + tax + maintenance) plus the renter's opportunity cost — the down payment
  invested at the live S&P 500 return — for an honest net-worth break-even. Uses live
  inflation + market data and shows equity accumulation over the full mortgage term.
tags: [finance, real_estate, mortgage, rent, property]
---

# Real Estate Skill

## When to use
User mentions: buy vs rent, mortgage, house price, down payment, can I afford a house,
monthly mortgage payment, break-even for buying, property investment.

## Execution plan

### STEP 1 — ask_user
Collect: property price, down payment amount or %, mortgage interest rate,
mortgage term (years), current rent / comparable rent, country.

### STEP 2 — run_python (mortgage + rent vs buy + 3 charts)

```python
import asyncio, json as _json

# Fill from ask_user answers
property_price  = ...
down_payment    = ...
mortgage_rate   = ...   # annual %, e.g. 6.5
mortgage_years  = 30
monthly_rent    = ...
country         = "..."

# Live data: local inflation (drives property appreciation + rent growth) and the S&P 500
# long-run return (what the renter earns by investing the down payment instead of buying).
spy, inflation = await asyncio.gather(
    get_historical_annual_returns("SPY", years=20),
    get_inflation_rate(country),
)
inflation_rate     = inflation["inflation_pct"] / 100
market_return      = spy["avg_annual_return"] / 100   # renter's opportunity-cost return
appreciation_rate  = inflation_rate + 0.015   # property appreciates at inflation + 1.5%

loan = property_price - down_payment

def monthly_mortgage(principal, annual_rate, years):
    r = annual_rate / 100 / 12
    n = years * 12
    if r == 0:
        return principal / n
    return principal * r * (1+r)**n / ((1+r)**n - 1)

monthly_payment = monthly_mortgage(loan, mortgage_rate, mortgage_years)
total_paid      = monthly_payment * mortgage_years * 12
total_interest  = total_paid - loan

print("Monthly mortgage: $" + str(int(monthly_payment)))
print("Total interest: $" + str(int(total_interest)))
print("Total paid: $" + str(int(total_paid)))

# Amortisation schedule
schedule = []
balance = float(loan)
cumulative_interest = 0.0
r = mortgage_rate / 100 / 12
payment = monthly_payment
for month in range(1, mortgage_years*12+1):
    interest = balance * r
    principal_paid = payment - interest
    balance = max(balance - principal_paid, 0)
    cumulative_interest += interest
    if month % 12 == 0:
        year = month // 12
        prop_value = property_price * ((1+appreciation_rate)**year)
        equity = prop_value - balance
        schedule.append({
            "year": year, "balance": int(balance), "equity": int(equity),
            "property_value": int(prop_value), "cumulative_interest": int(cumulative_interest),
        })

# Honest buy-vs-rent: compare NET WORTH, not just cash spent.
#   • Buyer's wealth  = home equity (property value − mortgage balance) + any side investments.
#   • Renter's wealth = the down payment (which the buyer locks into the house) invested at the
#     live market return, PLUS whatever they save in months where renting is cheaper than owning.
# Whoever has the lower monthly outlay invests the difference — THAT is the opportunity cost.
monthly_market = (1 + market_return) ** (1/12) - 1
renter_invest  = float(down_payment)   # capital the buyer ties up; the renter keeps it invested
buyer_invest   = 0.0                    # buyer invests only in months where owning is cheaper
rent_m         = float(monthly_rent)
bal2           = float(loan)
r_m            = mortgage_rate / 100 / 12
wealth_vs_year = []
for month in range(1, mortgage_years*12 + 1):
    prop_v_now = property_price * ((1+appreciation_rate)**(month/12))
    own_outlay = monthly_payment + prop_v_now*0.005/12 + prop_v_now*0.01/12   # P&I + tax + maint
    if own_outlay >= rent_m:
        renter_invest += (own_outlay - rent_m)     # renting cheaper → renter invests the gap
    else:
        buyer_invest  += (rent_m - own_outlay)     # owning cheaper → buyer invests the gap
    renter_invest *= (1 + monthly_market)
    buyer_invest  *= (1 + monthly_market)
    interest = bal2 * r_m
    bal2 = max(bal2 - (monthly_payment - interest), 0)
    rent_m *= (1 + inflation_rate) ** (1/12)
    if month % 12 == 0:
        y = month // 12
        prop_v        = property_price * ((1+appreciation_rate)**y)
        buyer_wealth  = (prop_v - bal2) + buyer_invest   # equity + side investments
        renter_wealth = renter_invest                    # invested portfolio
        wealth_vs_year.append({"year": y,
                               "Buying":  int(buyer_wealth/1000),
                               "Renting": int(renter_wealth/1000)})

# Decide the verdict by NET WORTH at the END of the term, and find where the lead changes hands.
# Leverage usually flatters the buyer early (appreciation hits the whole property, not just the
# down payment); the renter's invested capital then compounds and often overtakes — so report the
# DECISIVE crossover, not the first year one side nudges ahead.
buyer_final  = wealth_vs_year[-1]["Buying"]
renter_final = wealth_vs_year[-1]["Renting"]
crossover_year = None
for i in range(1, len(wealth_vs_year)):
    prev_buyer_ahead = wealth_vs_year[i-1]["Buying"] >= wealth_vs_year[i-1]["Renting"]
    cur_buyer_ahead  = wealth_vs_year[i]["Buying"]   >= wealth_vs_year[i]["Renting"]
    if cur_buyer_ahead != prev_buyer_ahead:
        crossover_year = wealth_vs_year[i]["year"]
be_label = str(crossover_year) if crossover_year else "—"

print("Renter invests the $" + str(int(down_payment)) + " down payment + monthly savings at the live market return (" + str(round(market_return*100,1)) + "%/yr)")
if buyer_final >= renter_final:
    print("BUYING wins by year " + str(mortgage_years) + ": owner net worth $" + str(buyer_final) + "K vs renter $" + str(renter_final) + "K")
else:
    print("RENTING + investing wins by year " + str(mortgage_years) + ": renter net worth $" + str(renter_final) + "K vs owner $" + str(buyer_final) + "K")
if crossover_year:
    print("Lead changes hands around year " + str(crossover_year))

# Chart 1 — buyer vs renter NET WORTH over time (wealth_vs_year, built above)
# Chart 2 — equity & property value area
equity_data = [{"year": s["year"], "Property Value": int(s["property_value"]/1000),
                "Mortgage Balance": int(s["balance"]/1000)} for s in schedule]
# Chart 3 — mortgage breakdown pie
pie_data = [
    {"x": "Principal", "value": int(loan)},
    {"x": "Interest",  "value": int(total_interest)},
    {"x": "Down Payment","value": int(down_payment)},
]

# AntV — waterfall: home equity buildup
wf = [{"category": "Down Payment", "value": int(down_payment)}]
prev_eq = float(down_payment)
for cp in [5, 10, 15, 20, 25, mortgage_years]:
    if cp > mortgage_years:
        break
    yr = None
    for s in schedule:
        if s["year"] == cp:
            yr = s
            break
    if yr:
        wf.append({"category": "Year " + str(cp), "value": int(yr["equity"] - prev_eq)})
        prev_eq = yr["equity"]
wf.append({"category": "Full Ownership", "isTotal": True})

# AntV — sankey: monthly cost breakdown
avg_principal = int(loan / (mortgage_years * 12))
avg_interest  = int(monthly_payment - avg_principal)
sankey = [
    {"source": "Monthly Payment", "target": "Principal",    "value": avg_principal},
    {"source": "Monthly Payment", "target": "Interest",     "value": avg_interest},
    {"source": "Monthly Costs",   "target": "Property Tax", "value": int(property_price*0.005/12)},
    {"source": "Monthly Costs",   "target": "Maintenance",  "value": int(property_price*0.01/12)},
    {"source": "Principal",       "target": "Home Equity",  "value": avg_principal},
]

# Render ALL FIVE charts here. The generate_* AntV functions are callable
# right inside run_python — DO NOT defer them to a separate tool call.
await asyncio.gather(
    create_chart("line", "Buyer vs Renter — Net Worth (crossover yr " + be_label + ")",
                 wealth_vs_year, series=[{"key":"Buying","color":"#3b82f6"},{"key":"Renting","color":"#f97316"}],
                 x_key="year", style={"x_label":"Year","y_label":"Net Worth ($K)","legend":True,"grid":True}),
    create_chart("area", "Property Value vs Mortgage Balance", equity_data,
                 series=[{"key":"Property Value"},{"key":"Mortgage Balance"}], x_key="year",
                 style={"y_label":"$K","legend":True}),
    create_chart("pie", "Total Mortgage Cost Breakdown", pie_data),
    generate_waterfall_chart("Home Equity Buildup", wf,
                             axisXTitle="Period", axisYTitle="Equity ($)"),
    generate_sankey_chart("Monthly Housing Cost Breakdown", sankey),
)
print("Rendered 5 charts: 3 standard + 2 AntV (waterfall, sankey)")
```

### STEP 3 — text summary

- Mortgage snapshot: monthly $X, total interest $Y over Z years
- **Honest verdict by net worth (not just cash spent):** lead with who's richer at the end of the
  term and where the lead flips. e.g. "Buying leads early thanks to leverage, but the renter's
  invested down payment overtakes around **year {crossover_year}** — by year 30 the renter is worth
  ${renter_final}K vs the owner's ${buyer_final}K." This already credits the renter with investing
  your down payment at the live {market_return}% market return plus any month renting is cheaper —
  the opportunity cost most calculators ignore. If the buyer wins at the end, say so instead. The
  takeaway: buying tends to win if you sell before the crossover; renting + investing wins if you'd
  hold past it.
- Affordability: "Mortgage is Nx your annual income (recommended max: 4x)."
- Sensitivity: "If rates rise to X%, monthly payment increases by $Y. A higher market return widens
  the renter's lead, since the freed-up down payment compounds faster."
