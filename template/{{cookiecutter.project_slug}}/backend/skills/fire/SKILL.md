---
name: fire
description: >
  FIRE (Financial Independence, Retire Early) calculator. Computes FIRE number,
  retirement timeline, 3 market scenarios, investment strategy (ETFs, tax wrappers).
  Fetches live market data. Produces 3 standard charts + 2 AntV advanced charts.
tags: [finance, retirement, planning, investing]
---

# FIRE Planning Skill

## When to use
User asks about: retiring early, financial independence, FIRE number, when can I retire,
how much do I need, investment strategy, what ETFs to buy.

## Execution plan

### STEP 1 — ask_user (one call)
Ask everything in ONE call. Because every question is asked at once, you do NOT yet know the
user's currency — so **never assume one (don't write "PLN", "$", etc.)**. Each money question
says **"in your local currency"** and a dedicated currency question resolves it. **Every money
question MUST also state the period (per month)** — keep ALL cash flows on the SAME monthly
basis; STEP 2 converts them to annual. DO NOT mix monthly and annual across questions.

Use this exact wording:

- "What is your current age?"
- "What is your current invested portfolio balance? (total, in your local currency)"
- "What is your take-home income **per month**? (in your local currency)"
- "What are your living expenses **per month**? (in your local currency)"
- "How much do you save/invest **per month**? (in your local currency)"
- "Which country / currency do you use? (sets the inflation assumption)"
- "Risk appetite — conservative, balanced, or aggressive?"

Use the currency from the answer for all chart labels and the text summary.

### STEP 2 — run_python

```python
import asyncio, json as _json

current_age       = ...   # from ask_user
current_portfolio = ...   # current portfolio total (not monthly)
monthly_income    = ...   # take-home income per month
monthly_expenses  = ...   # living expenses per month
monthly_savings   = ...   # saved/invested per month
risk_profile      = "..."   # conservative / balanced / aggressive
country           = "..."

# All money inputs are PER MONTH — convert to annual figures used below
annual_income     = monthly_income * 12
annual_expenses   = monthly_expenses * 12
annual_savings    = monthly_savings * 12

spy, inflation, bonds = await asyncio.gather(
    get_historical_annual_returns("SPY", years=20),
    get_inflation_rate(country),
    get_bond_yield("US"),
)
base_nominal   = spy["avg_annual_return"] / 100      # live SPY 20y nominal
inflation_rate = inflation["inflation_pct"] / 100    # live CPI for the country
bond_nominal   = bonds.get("yield_pct", 4.0) / 100   # live 10y govt bond yield (fallback 4%)

# Data-driven REAL returns: deflate the live nominal figures by inflation, then
# blend by risk profile. Risk profile = equity weight; the rest sits in bonds at
# the live 10y yield. So SPY, the bond yield AND inflation all move the result.
spy_real  = (1 + base_nominal) / (1 + inflation_rate) - 1
bond_real = (1 + bond_nominal) / (1 + inflation_rate) - 1
eq_weights = {"aggressive": 0.95, "balanced": 0.70, "conservative": 0.45}
eq_weight  = eq_weights.get(risk_profile, 0.70)
port_return = eq_weight * spy_real + (1 - eq_weight) * bond_real
fire_number = annual_expenses / 0.04

def yrs(start, contrib, ret, target):
    p, y = float(start), 0
    while p < target and y < 60:
        p = p * (1 + ret) + contrib
        y += 1
    return y

base_years = yrs(current_portfolio, annual_savings, port_return, fire_number)
fire_age   = current_age + base_years
pess_years = yrs(current_portfolio, annual_savings, port_return - 0.02, fire_number)
opti_years = yrs(current_portfolio, annual_savings, port_return + 0.02, fire_number)

print("FIRE number: " + str(int(fire_number)))
print("Retire age: " + str(fire_age) + " (pess " + str(current_age+pess_years) + " / opti " + str(current_age+opti_years) + ")")
print("Portfolio real return: " + str(round(port_return*100,1)) + "% (" + str(int(eq_weight*100)) + "% equity @ SPY real " + str(round(spy_real*100,1)) + "%, rest bonds real " + str(round(bond_real*100,1)) + "%, inflation " + str(round(inflation_rate*100,1)) + "%)")

# Chart 1 — 3 scenario line
plot_n = min(max(pess_years, base_years, opti_years) + 3, 50)
line_data = []
p_b = p_p = p_o = float(current_portfolio)
for y in range(plot_n + 1):
    line_data.append({"year": y, "Base": round(p_b/1000,1),
                       "Pessimistic": round(p_p/1000,1), "Optimistic": round(p_o/1000,1)})
    p_b = p_b*(1+port_return)+annual_savings
    p_p = p_p*(1+port_return-0.02)+annual_savings
    p_o = p_o*(1+port_return+0.02)+annual_savings

# Chart 2 — allocation pie
alloc = {
    "aggressive":   [("Global Equities (IWDA)", 80), ("Emerging Mkts (EIMI)", 10), ("Cash Buffer", 10)],
    "balanced":     [("Global Equities (IWDA)", 60), ("US Equities (SPY)", 20), ("Bonds (AGGH)", 20)],
    "conservative": [("Global Equities (IWDA)", 40), ("Bonds (AGGH)", 40), ("Cash", 20)],
}
pie_data = [{"x": n, "value": v} for n, v in alloc.get(risk_profile, alloc["balanced"])]

# Chart 3 — savings sensitivity bar
impact_data = []
for extra in [-500, -250, 0, 250, 500, 1000]:
    label = "Current" if extra == 0 else ("+" if extra > 0 else "") + str(extra) + "/mo"
    impact_data.append({"x": label, "years": yrs(current_portfolio, annual_savings+extra*12, port_return, fire_number)})

# Chart 4 (AntV) — waterfall: portfolio growth milestones
wf = [{"category": "Start", "value": int(current_portfolio)}]
p2, prev2, y2 = float(current_portfolio), float(current_portfolio), 0
for cp in sorted(set([y for y in [5,10,15,20] if y < base_years] + [base_years])):
    while y2 < cp:
        p2 = p2*(1+port_return)+annual_savings
        y2 += 1
    wf.append({"category": ("FIRE! yr "+str(cp)) if cp==base_years else ("Year "+str(cp)), "value": int(p2-prev2)})
    prev2 = p2
wf.append({"category": "FIRE Target", "isTotal": True})

# Chart 5 (AntV) — sankey: monthly income flow
m_income = annual_income / 12
m_exp    = annual_expenses / 12
m_taxes  = max(0, m_income - m_exp - monthly_savings)
sankey = [
    {"source":"Monthly Income","target":"Living Expenses","value":int(m_exp)},
    {"source":"Monthly Income","target":"Investments",    "value":int(monthly_savings)},
    {"source":"Monthly Income","target":"Taxes & Other",  "value":int(m_taxes)},
    {"source":"Investments",   "target":"ETF Portfolio",  "value":int(monthly_savings*0.9)},
    {"source":"Investments",   "target":"Cash Buffer",    "value":int(monthly_savings*0.1)},
]

# Render ALL FIVE charts in one go. The generate_* AntV functions are callable
# right here inside run_python — DO NOT defer them to a separate tool call.
await asyncio.gather(
    create_chart("line", "Portfolio Growth to FIRE — 3 Scenarios", line_data,
                 series=[{"key":"Pessimistic","color":"#ef4444"},{"key":"Base","color":"#3b82f6"},{"key":"Optimistic","color":"#22c55e"}],
                 x_key="year", style={"x_label":"Years","y_label":"Portfolio ($K)","legend":True,"grid":True}),
    create_chart("pie", "Portfolio Allocation — " + risk_profile.title(), pie_data),
    create_chart("bar", "How Extra Monthly Savings Moves FIRE Date", impact_data,
                 x_key="x", series=[{"key":"years","label":"Years to FIRE"}], style={"grid":True}),
    generate_waterfall_chart("Portfolio Growth Milestones to FIRE", wf,
                             axisXTitle="Milestone", axisYTitle="Contribution to Portfolio ($)"),
    generate_sankey_chart("Where Your Money Goes Each Month", sankey),
)
print("Rendered 5 charts: 3 standard + 2 AntV (waterfall, sankey)")
```

### STEP 3 — text summary
- Lead: "You need **$X** to retire. At your current pace: **age Y**."
- Investment strategy: specific ETFs with tickers + TERs
- Tax wrappers: 401k/Roth IRA (US) | IKE/IKZE (PL) | ISA (UK)
- Key levers: "Save $500/mo more → retire 2 years earlier"
- Data: SPY 20Y avg X%, inflation Y%, bond yield Z% — live from Yahoo Finance

## Investment strategy reference

### Aggressive (age < 40)
80% IWDA.AS (TER 0.20%) or VWCE.AS (TER 0.22%) · 10% EIMI.AS (TER 0.18%) · 10% cash

### Balanced
60% IWDA.AS · 20% SPY or CSPX.AS · 20% AGGH.AS (TER 0.10%)

### Conservative
40% IWDA.AS · 40% AGGH.AS + local govt bonds · 20% cash / money market
