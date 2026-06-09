---
name: currency
description: >
  Real-time currency exchange rates via the European Central Bank (Frankfurter API).
  Supports 30+ currencies. No API key required. Use inside run_python blocks.
tags: [finance, currency, forex]
---

# Currency Skill

## Available function

### `get_exchange_rate(from_currency, to_currency)`
```python
rate = await get_exchange_rate("USD", "PLN")
print(rate["rate"])   # e.g. 3.97
print(rate["date"])   # e.g. "2024-06-02"

# Convert an amount (NOTE: the sandbox has NO comma format — use int(), not {x:,})
usd_amount = 85000
pln_amount = usd_amount * rate["rate"]
print(f"${int(usd_amount)} = {int(pln_amount)} PLN")
```

## Supported currencies
USD, EUR, PLN, GBP, CHF, JPY, CZK, HUF, SEK, NOK, DKK, CAD, AUD, NZD, and 20+ more.
Source: European Central Bank reference rates, updated daily.

## FIRE planning use case
Always convert financial projections to the user's local currency:
```python
fx = await get_exchange_rate("USD", "PLN")
fire_number_usd = 1200000
fire_number_pln = fire_number_usd * fx["rate"]
print(f"FIRE number: ${int(fire_number_usd)} / {int(fire_number_pln)} PLN")
```
