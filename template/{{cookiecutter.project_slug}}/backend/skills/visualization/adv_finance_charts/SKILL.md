---
name: adv_finance_charts
description: >
  Advanced AntV chart patterns for financial data. Covers waterfall (milestones, debt cascade,
  equity buildup), sankey (income/cashflow), radar (portfolio health score), treemap
  (holdings breakdown, FIRE variants, goal priority), dual-axes (portfolio + contributions),
  histogram + boxplot (return distributions). Avoid the funnel chart — it injects hardcoded
  Chinese labels; use treemap/sankey instead. Load this skill whenever you need advanced
  visualizations after computing financial data. Each section shows the exact tool name,
  schema, and a ready-to-use example.
tags: [finance, charts, visualization, antv]
---

# Finance Charts Skill

Load this skill after any financial calculation to produce advanced AntV visualizations.
Each tool below is an MCP tool — call it directly (not inside run_python).

---

## generate_waterfall_chart

**Best for:** Portfolio milestone journey, debt elimination cascade, equity buildup, P&L breakdown.

Schema:
```json
data: [
  { "category": "string", "value": number },          // regular bar (positive = up, negative = down)
  { "category": "string", "isIntermediateTotal": true }, // subtotal bar
  { "category": "string", "isTotal": true }            // final total bar
]
```

### Example — FIRE milestones
```
generate_waterfall_chart(
  title="Portfolio Growth Milestones to FIRE",
  data=[
    {"category": "Starting Portfolio", "value": 100000},
    {"category": "Year 5 gains",       "value": 187000},
    {"category": "Year 10 gains",      "value": 310000},
    {"category": "Year 15 gains",      "value": 278000},
    {"category": "FIRE Target",        "isTotal": true}
  ]
)
```

### Example — Debt elimination cascade
```
generate_waterfall_chart(
  title="Debt Elimination (Avalanche Order)",
  data=[
    {"category": "Total Debt",       "value": 45000},
    {"category": "Credit Card 24%",  "value": -8000},
    {"category": "Personal Loan 12%","value": -12000},
    {"category": "Car Loan 6%",      "value": -15000},
    {"category": "Debt Free",        "isTotal": true}
  ]
)
```

### Example — Equity buildup (real estate)
```
generate_waterfall_chart(
  title="Home Equity Buildup",
  data=[
    {"category": "Down Payment",  "value": 60000},
    {"category": "Yr 1-5 equity", "value": 28000},
    {"category": "Yr 6-10 equity","value": 42000},
    {"category": "Yr 11-20 equity","value": 95000},
    {"category": "Full Ownership","isTotal": true}
  ]
)
```

---

## generate_sankey_chart

**Best for:** Income/cashflow breakdown, money flow (income → expenses → savings), debt payment routing.

Schema:
```json
data: [
  { "source": "string", "target": "string", "value": number }
]
```
Each row is a directed flow from source to target with a numeric value.
Nodes are created automatically from unique source/target strings.

### Example — Monthly income flow
```
generate_sankey_chart(
  title="Where Your Money Goes Each Month",
  data=[
    {"source": "Monthly Income",  "target": "Living Expenses", "value": 2917},
    {"source": "Monthly Income",  "target": "Investments",     "value": 2000},
    {"source": "Monthly Income",  "target": "Taxes & Other",   "value": 3416},
    {"source": "Investments",     "target": "ETF Portfolio",   "value": 1800},
    {"source": "Investments",     "target": "Cash Buffer",     "value": 200}
  ]
)
```

### Example — Debt payment routing
```
generate_sankey_chart(
  title="Monthly Cash Flow — Debt Payments",
  data=[
    {"source": "Monthly Income",   "target": "Living Expenses",    "value": 2500},
    {"source": "Monthly Income",   "target": "Credit Card (min)",  "value": 150},
    {"source": "Monthly Income",   "target": "Car Loan (min)",     "value": 300},
    {"source": "Monthly Income",   "target": "Extra Payment",      "value": 500},
    {"source": "Extra Payment",    "target": "Credit Card (extra)","value": 500}
  ]
)
```

### Example — Mortgage cost breakdown
```
generate_sankey_chart(
  title="Monthly Mortgage Cost Breakdown",
  data=[
    {"source": "Monthly Payment", "target": "Principal",    "value": 800},
    {"source": "Monthly Payment", "target": "Interest",     "value": 950},
    {"source": "Monthly Costs",   "target": "Property Tax", "value": 210},
    {"source": "Monthly Costs",   "target": "Maintenance",  "value": 250},
    {"source": "Principal",       "target": "Home Equity",  "value": 800}
  ]
)
```

---

## generate_radar_chart

**Best for:** Portfolio health score, multi-dimensional comparison, risk profile assessment.

Schema:
```json
data: [
  { "name": "dimension", "value": number_0_to_100 }
]
// For grouped comparison add "group" field:
  { "name": "dimension", "value": number, "group": "Portfolio A" }
```

### Example — Portfolio health score
```
generate_radar_chart(
  title="Portfolio Health Score",
  data=[
    {"name": "Diversification",   "value": 78},
    {"name": "Return Potential",  "value": 85},
    {"name": "Geographic Spread", "value": 70},
    {"name": "Target Alignment",  "value": 62},
    {"name": "Risk Balance",      "value": 74}
  ]
)
```

### Example — Two portfolios compared
```
generate_radar_chart(
  title="Current vs Target Portfolio",
  data=[
    {"name": "US Stocks",  "value": 65, "group": "Current"},
    {"name": "Intl",       "value": 15, "group": "Current"},
    {"name": "Bonds",      "value": 10, "group": "Current"},
    {"name": "US Stocks",  "value": 50, "group": "Target"},
    {"name": "Intl",       "value": 30, "group": "Target"},
    {"name": "Bonds",      "value": 20, "group": "Target"}
  ]
)
```

---

## generate_treemap_chart

**Best for:** Portfolio breakdown by asset class/holding, goal progress overview, hierarchical allocation.

Schema:
```json
data: [
  {
    "name": "Category",
    "value": number,
    "children": [                     // optional nested breakdown
      { "name": "Sub-item", "value": number }
    ]
  }
]
```

### Example — Portfolio by asset class → holdings
```
generate_treemap_chart(
  title="Portfolio Breakdown by Asset Class",
  data=[
    {"name": "US Equities", "value": 45000, "children": [
      {"name": "VTI",  "value": 30000},
      {"name": "AAPL", "value": 15000}
    ]},
    {"name": "International", "value": 25000, "children": [
      {"name": "IWDA.AS", "value": 25000}
    ]},
    {"name": "Bonds",   "value": 15000, "children": [
      {"name": "BND", "value": 15000}
    ]},
    {"name": "Cash",    "value": 10000}
  ]
)
```

### Example — Savings goal progress
```
generate_treemap_chart(
  title="Savings Goals — Progress Overview",
  data=[
    {"name": "House Down Payment", "value": 80000, "children": [
      {"name": "Saved",     "value": 22000},
      {"name": "Remaining", "value": 58000}
    ]},
    {"name": "Emergency Fund", "value": 20000, "children": [
      {"name": "Saved",     "value": 14000},
      {"name": "Remaining", "value": 6000}
    ]},
    {"name": "Car", "value": 25000, "children": [
      {"name": "Saved",     "value": 3000},
      {"name": "Remaining", "value": 22000}
    ]}
  ]
)
```

---

## generate_funnel_chart

> ⚠️ **AVOID for these finance demos.** The AntV funnel chart injects hardcoded Chinese
> "转化率" (conversion-rate) labels via its SSR renderer, and there is **no parameter to disable
> them**. For "stages sized by value" use **`generate_treemap_chart`** (FIRE variants, goal
> targets) or **`generate_sankey_chart`** (priority/flow) instead — both render clean. The schema
> below is kept for reference only.

**Best for (in theory):** FIRE variants (Fat → Lean → Coast), savings goals by priority, debt stages.

Schema:
```json
data: [
  { "category": "Stage label", "value": number }
]
```
Ordered from largest value (top/widest) to smallest (bottom/narrowest).

### Example — FIRE variants
```
generate_funnel_chart(
  title="FIRE Variants — Required Portfolio (Hardest → Easiest)",
  data=[
    {"category": "Fat FIRE — retire age 48",     "value": 3500000},
    {"category": "Full FIRE — retire age 42",    "value": 1750000},
    {"category": "Barista FIRE — retire age 38", "value": 875000},
    {"category": "Lean FIRE — retire age 36",    "value": 625000},
    {"category": "Coast Number — save to age 32","value": 280000}
  ]
)
```

### Example — Savings goals by urgency (most urgent = largest bar at top)
```
generate_funnel_chart(
  title="Savings Goals — Priority & Target",
  data=[
    {"category": "Emergency Fund (6 mo)",  "value": 20000},
    {"category": "House Down Payment (4y)","value": 80000},
    {"category": "New Car (2y)",           "value": 25000},
    {"category": "Japan Holiday (10mo)",   "value": 5000}
  ]
)
```

---

## generate_dual_axes_chart

**Best for:** Portfolio value (columns, left axis) + annual contribution (line, right axis), price + volume.

Schema:
```json
categories: ["2025", "2026", ...]    // x-axis labels
series: [
  { "type": "column", "data": [number, ...], "axisYTitle": "Left axis label" },
  { "type": "line",   "data": [number, ...], "axisYTitle": "Right axis label" }
]
// Note: line data values should be ≤ 1 (ratios) OR a different scale than columns.
// If both are dollar amounts, normalise the line to a ratio of max value.
```

### Example — Portfolio growth + contribution timeline (Coast FIRE)
```
generate_dual_axes_chart(
  title="Portfolio Growth & Savings Contributions by Age",
  categories=["25","26","27","28","29","30","31","32","33","34","35"],
  series=[
    {
      "type": "column",
      "data": [100, 134, 171, 213, 259, 311, 368, 432, 502, 579, 664],
      "axisYTitle": "Portfolio ($K)"
    },
    {
      "type": "line",
      "data": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
      "axisYTitle": "Contributing (1=yes, 0=coasted)"
    }
  ]
)
```

---

## generate_histogram_chart

**Best for:** Distribution of annual returns, showing how often a portfolio had positive/negative years.

Schema:
```json
data: [number, number, ...]   // raw values — AntV bins them automatically
binNumber: 8                   // optional: number of bins
```

### Example — SPY annual return distribution
```
generate_histogram_chart(
  title="SPY Annual Return Distribution (20 Years)",
  data=[26.3, -18.2, 28.7, 4.2, 31.5, -4.4, 21.8, 13.7, 1.4, 32.4,
        16.0, -9.1, 11.8, 30.0, -37.0, 5.5, 15.8, 4.9, -22.1, 28.6],
  binNumber=8
)
```

---

## generate_boxplot_chart

**Best for:** Comparing return volatility across assets, showing median/quartiles/outliers.

Schema:
```json
data: [
  { "category": "Asset name", "value": number }   // one row per data point
]
// AntV automatically computes min/Q1/median/Q3/max per category
```

### Example — Multi-asset volatility comparison
```
generate_boxplot_chart(
  title="Return Volatility by Asset (10 Years)",
  data=[
    {"category": "SPY",     "value": 26.3},
    {"category": "SPY",     "value": -18.2},
    {"category": "IWDA.AS", "value": 22.1},
    {"category": "IWDA.AS", "value": -14.5},
    ...
  ]
)
```
