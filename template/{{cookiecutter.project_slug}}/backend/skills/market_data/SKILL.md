---
name: market_data
description: >
  Fetch live financial market data: stock/ETF prices, historical returns,
  and index performance. Data is retrieved via Yahoo Finance (no API key needed).
  Use these functions inside run_python code blocks.
tags: [finance, stocks, etf, markets]
---

# Market Data Skill

## Available functions (call inside run_python)

### `get_asset_price(symbol)`
Returns current price for any stock, ETF, or index.
```python
spy = await get_asset_price("SPY")        # S&P 500 ETF
iwda = await get_asset_price("IWDA.AS")   # MSCI World (Euronext)
wig20 = await get_asset_price("^WIG20")   # Warsaw Stock Exchange WIG20
btc = await get_asset_price("BTC-USD")    # Bitcoin

print(spy["price"], spy["currency"])  # 523.4 USD
```

### `get_historical_annual_returns(symbol, years=10)`
Returns year-by-year returns and the long-term average.
```python
data = await get_historical_annual_returns("SPY", years=20)
avg = data["avg_annual_return"]  # e.g. 10.4 (percent)
annual = data["annual_returns"]  # {"2023": 26.3, "2022": -18.2, ...}
```

**Useful tickers for FIRE planning:**
| Asset | Ticker | Description |
|-------|--------|-------------|
| S&P 500 | `SPY` | US large-cap benchmark |
| MSCI World | `IWDA.AS` | Global developed markets |
| MSCI EM | `EIMI.AS` | Emerging markets |
| WIG20 | `^WIG20` | Polish blue-chip index |
| Gold | `GC=F` | Gold futures |
| BTC | `BTC-USD` | Bitcoin |
| Bonds (US 10y) | `^TNX` | 10-year Treasury yield |

## Usage pattern
Always fetch data first, then compute:
```python
# 1. Fetch real data
spy_data = await get_historical_annual_returns("SPY", years=20)
base_return = spy_data["avg_annual_return"] / 100  # convert to decimal

# 2. Use in calculations
portfolio = 85000
for year in range(30):
    portfolio = portfolio * (1 + base_return) + 3800 * 12

print(f"Portfolio after 30 years: {portfolio:.0f}")
```

### `get_bond_yield(country_code)`
Returns the current 10-year government bond yield for a country.
Useful for comparing risk-free rate vs equity return premium.
```python
us_bond = await get_bond_yield("US")   # {"yield_pct": 4.3, "maturity": "10Y"}
pl_bond = await get_bond_yield("PL")   # {"yield_pct": 5.6}
de_bond = await get_bond_yield("DE")   # {"yield_pct": 2.5}

equity_premium = spy["avg_annual_return"] - us_bond["yield_pct"]
print(f"Equity risk premium: {equity_premium:.1f}%")
```

Supported countries: US, DE, GB, PL, FR, IT, ES, CZ, HU, JP, AU, CA.

## Error handling
All functions return `{"error": "..."}` on failure. Always check:
```python
data = await get_asset_price("SPY")
if "error" in data:
    # Fall back to historical assumption
    price = 520.0
else:
    price = data["price"]
```

## AntV Visualizations for market data

`generate_histogram_chart` and `generate_boxplot_chart` are callable **directly inside
run_python** — call them in the same block right after fetching the data. DO NOT defer
them to a separate tool call (the model tends to skip those).

### Annual Returns Histogram
Shows how often a market had positive vs negative years:
```python
import asyncio

data = await get_historical_annual_returns("SPY", years=20)
returns_list = list(data["annual_returns"].values())  # e.g. [26.3, -18.2, 28.7, ...]

await generate_histogram_chart(
    "SPY Annual Return Distribution (20 Years)",
    returns_list,
    binNumber=8,
)
```

### Multi-Asset Comparison Boxplot
Compares the volatility (median/quartiles/outliers) of several assets side by side:
```python
import asyncio

symbols = ["SPY", "IWDA.AS", "EIMI.AS"]
results = await asyncio.gather(*[get_historical_annual_returns(s, years=10) for s in symbols])

box_data = []
for symbol, d in zip(symbols, results):
    for ret in d["annual_returns"].values():
        box_data.append({"category": symbol, "value": ret})

await generate_boxplot_chart("Return Volatility Comparison", box_data,
                             axisYTitle="Annual Return (%)")
```

You can also render both in one go with `await asyncio.gather(generate_histogram_chart(...), generate_boxplot_chart(...))`.
