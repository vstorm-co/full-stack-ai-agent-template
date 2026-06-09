---
name: base_finance_charts
description: >
  Standard create_chart patterns for financial data. Covers all common finance chart
  combinations: FIRE scenarios (line + pie + bar), debt payoff (line + bar + area),
  portfolio allocation (pie + grouped bar), coast FIRE variants (bar + area),
  rent vs buy (line + area + pie), savings goals (area + bar + pie).
  Load this skill after a domain skill prints its __CHART_*__ data, then call
  create_chart with the printed data.
tags: [finance, charts, visualization]
---

# Base Finance Charts Skill

Load after a domain skill has printed structured chart data. Use `create_chart` with
the printed data. Run all charts in a single `await asyncio.gather(...)` inside run_python.

---

## FIRE Charts

Domain skill prints: `__LINE__`, `__PIE__`, `__BAR__`

```python
# Inside run_python — paste the printed data then call charts
import asyncio, json as _json

line_data   = _json.loads("""<paste __LINE__ value>""")
pie_data    = _json.loads("""<paste __PIE__ value>""")
bar_data    = _json.loads("""<paste __BAR__ value>""")

await asyncio.gather(
    create_chart(
        "line",
        "Portfolio Growth to FIRE — 3 Scenarios",
        line_data,
        series=[
            {"key": "Pessimistic", "color": "#ef4444"},
            {"key": "Base",        "color": "#3b82f6"},
            {"key": "Optimistic",  "color": "#22c55e"},
        ],
        x_key="year",
        style={"x_label": "Years", "y_label": "Portfolio ($K)", "legend": True, "grid": True},
    ),
    create_chart(
        "pie",
        "Portfolio Allocation",
        pie_data,
    ),
    create_chart(
        "bar",
        "How Extra Monthly Savings Moves Your FIRE Date",
        bar_data,
        x_key="x",
        series=[{"key": "years", "label": "Years to FIRE"}],
        style={"y_label": "Years to FIRE", "grid": True},
    ),
)
```

---

## Debt Optimizer Charts

Domain skill prints: `__LINE__` (strategies), `__BAR__` (interest), `__AREA__` (stacked debt)

```python
line_data = _json.loads("""<paste __LINE__ value>""")
bar_data  = _json.loads("""<paste __BAR__ value>""")
area_data = _json.loads("""<paste __AREA__ value>""")
debt_names = [...]  # from __DEBT_NAMES__

await asyncio.gather(
    create_chart(
        "line",
        "Total Debt Balance Over Time",
        line_data,
        series=[{"key": "Avalanche", "color": "#22c55e"}, {"key": "Snowball", "color": "#3b82f6"}],
        x_key="month",
        style={"y_label": "Balance ($K)", "legend": True, "grid": True},
    ),
    create_chart(
        "bar",
        "Total Interest Paid — Avalanche vs Snowball",
        bar_data,
        x_key="x",
        series=[{"key": "interest", "label": "Total Interest ($)"}],
    ),
    create_chart(
        "area",
        "Debt Breakdown Over Time (Avalanche)",
        area_data,
        series=[{"key": name} for name in debt_names],
        x_key="month",
        style={"y_label": "Balance ($K)", "stacked": True, "legend": True},
    ),
)
```

---

## Portfolio Health Charts

Domain skill prints: `__PIE__`, `__REBAL__`, `__CVT__`

```python
pie_data   = _json.loads("""<paste __PIE__ value>""")
rebal_data = _json.loads("""<paste __REBAL__ value>""")
cvt_data   = _json.loads("""<paste __CVT__ value>""")

await asyncio.gather(
    create_chart("pie", "Current Portfolio Allocation", pie_data),
    create_chart(
        "bar",
        "Rebalancing Actions (+ buy  /  − sell)",
        rebal_data,
        x_key="x",
        series=[{"key": "amount", "label": "Amount ($)"}],
    ),
    create_chart(
        "bar",
        "Current vs Target Allocation (%)",
        cvt_data,
        x_key="x",
        series=[{"key": "current", "label": "Current %"}, {"key": "target", "label": "Target %"}],
    ),
)
```

---

## Coast FIRE Charts

Domain skill prints: `__BAR_VARIANTS__`, `__AREA_COAST__`, `__BAR_YEARS__`

```python
bar_variants = _json.loads("""<paste __BAR_VARIANTS__ value>""")
area_coast   = _json.loads("""<paste __AREA_COAST__ value>""")
bar_years    = _json.loads("""<paste __BAR_YEARS__ value>""")

await asyncio.gather(
    create_chart(
        "bar",
        "Required Portfolio by FIRE Variant",
        bar_variants,
        x_key="x",
        series=[{"key": "target", "label": "Required Portfolio ($)"}],
    ),
    create_chart(
        "area",
        "Coast FIRE Journey",
        area_coast,
        series=[{"key": "With Investing"}, {"key": "After Coasting"}],
        x_key="age",
        style={"x_label": "Age", "y_label": "Portfolio ($K)", "legend": True},
    ),
    create_chart(
        "bar",
        "Years Until Each FIRE Variant",
        bar_years,
        x_key="x",
        series=[{"key": "years", "label": "Years to Reach"}],
    ),
)
```

---

## Real Estate Charts

Domain skill prints: `__LINE_RVB__`, `__AREA_EQ__`, `__PIE__`

```python
line_rvb  = _json.loads("""<paste __LINE_RVB__ value>""")
area_eq   = _json.loads("""<paste __AREA_EQ__ value>""")
pie_data  = _json.loads("""<paste __PIE__ value>""")
breakeven = ...  # from __BREAKEVEN__

await asyncio.gather(
    create_chart(
        "line",
        "Buyer vs Renter — Net Worth (crossover yr " + str(breakeven) + ")",
        line_rvb,
        series=[{"key": "Buying", "color": "#3b82f6"}, {"key": "Renting", "color": "#f97316"}],
        x_key="year",
        style={"x_label": "Year", "y_label": "Net Worth ($K)", "legend": True, "grid": True},
    ),
    create_chart(
        "area",
        "Property Value vs Mortgage Balance",
        area_eq,
        series=[{"key": "Property Value"}, {"key": "Mortgage Balance"}],
        x_key="year",
        style={"y_label": "$K", "legend": True},
    ),
    create_chart("pie", "Total Mortgage Cost Breakdown", pie_data),
)
```

---

## Savings Goals Charts

Domain skill prints: `__AREA__`, `__BAR_MONTHS__`, `__PIE__`

```python
area_data  = _json.loads("""<paste __AREA__ value>""")
bar_months = _json.loads("""<paste __BAR_MONTHS__ value>""")
pie_data   = _json.loads("""<paste __PIE__ value>""")
goal_names = [...]  # from __GOAL_NAMES__

await asyncio.gather(
    create_chart(
        "area",
        "Savings Progress Per Goal",
        area_data,
        series=[{"key": name} for name in goal_names],
        x_key="month",
        style={"stacked": True, "y_label": "Total Saved ($)", "legend": True},
    ),
    create_chart(
        "bar",
        "Months Until Each Goal Is Reached",
        bar_months,
        x_key="x",
        series=[{"key": "months", "label": "Months to Goal"}],
    ),
    create_chart("pie", "Monthly Savings Allocation", pie_data),
)
```
