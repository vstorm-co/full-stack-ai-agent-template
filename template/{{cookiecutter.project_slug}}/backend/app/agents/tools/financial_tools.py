{%- if cookiecutter.enable_skills %}
"""Financial data tools available as external functions inside the Monty sandbox.

All functions run in the HOST environment (not in the sandbox), so they can make
real HTTP requests. They are exposed to sandboxed code via ``_build_external_functions``
in code_execution.py, letting model-written Python fetch live market data and use
it directly in calculations and charts.

APIs used:
- yfinance — stock/ETF prices and historical OHLCV data via Yahoo Finance
- Frankfurter (frankfurter.dev) — ECB-sourced FX rates, free, no key needed
"""

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0


# ---------------------------------------------------------------------------
# Exchange rates — Frankfurter (ECB reference rates, free, no key)
# ---------------------------------------------------------------------------

async def get_exchange_rate(from_currency: str, to_currency: str) -> dict[str, Any]:
    """Return the latest exchange rate between two currencies.

    Args:
        from_currency: ISO 4217 base currency code, e.g. ``"USD"``.
        to_currency:   ISO 4217 target currency code, e.g. ``"PLN"``.

    Returns:
        ``{"from": "USD", "to": "PLN", "rate": 3.97, "date": "2024-06-02"}``
        or ``{"error": "..."}`` on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            url = (
                f"https://api.frankfurter.dev/v1/latest"
                f"?from={from_currency.upper()}&to={to_currency.upper()}"
            )
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            rate = data["rates"].get(to_currency.upper())
            if rate is None:
                return {"error": f"Currency {to_currency!r} not found in response"}
            return {
                "from": from_currency.upper(),
                "to": to_currency.upper(),
                "rate": rate,
                "date": data.get("date", ""),
            }
    except Exception as e:
        logger.warning("get_exchange_rate failed: %s", e)
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Market prices & historical returns — yfinance
# ---------------------------------------------------------------------------

def _fetch_asset_price_sync(symbol: str) -> dict[str, Any]:
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="5d", interval="1d")
    if hist.empty:
        return {"error": f"No data for symbol {symbol!r}"}
    price = float(hist["Close"].iloc[-1])
    info = ticker.fast_info
    currency = getattr(info, "currency", "") or ""
    return {
        "symbol": symbol.upper(),
        "price": round(price, 4),
        "currency": currency,
    }


async def get_asset_price(symbol: str) -> dict[str, Any]:
    """Return the latest market price for a stock, ETF, or index ticker.

    Args:
        symbol: Yahoo Finance ticker, e.g. ``"SPY"``, ``"IWDA.AS"``, ``"^GSPC"``.

    Returns:
        ``{"symbol": "SPY", "price": 523.4, "currency": "USD"}``
        or ``{"error": "..."}`` on failure.
    """
    try:
        return await asyncio.to_thread(_fetch_asset_price_sync, symbol)
    except Exception as e:
        logger.warning("get_asset_price(%s) failed: %s", symbol, e)
        return {"error": str(e)}


def _fetch_annual_returns_sync(symbol: str, years: int) -> dict[str, Any]:
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=f"{years}y", interval="1mo")
    if hist.empty:
        return {"error": f"No data for symbol {symbol!r}"}

    info = ticker.fast_info
    currency = getattr(info, "currency", "") or ""

    # Group by calendar year — keep last close price of each year
    hist.index = hist.index.tz_localize(None) if hist.index.tzinfo is not None else hist.index
    year_close: dict[int, float] = {}
    for dt, row in hist.iterrows():
        year_close[dt.year] = float(row["Close"])

    sorted_years = sorted(year_close)
    annual_returns: dict[str, float] = {}
    for i in range(1, len(sorted_years)):
        y_prev = sorted_years[i - 1]
        y_curr = sorted_years[i]
        ret = (year_close[y_curr] / year_close[y_prev] - 1) * 100
        annual_returns[str(y_curr)] = round(ret, 2)

    if not annual_returns:
        return {"error": "Not enough data to compute returns"}

    avg = round(sum(annual_returns.values()) / len(annual_returns), 2)
    return {
        "symbol": symbol.upper(),
        "currency": currency,
        "annual_returns": annual_returns,
        "avg_annual_return": avg,
        "years_available": len(annual_returns),
    }


async def get_historical_annual_returns(symbol: str, years: int = 10) -> dict[str, Any]:
    """Return annualised returns for each calendar year for an asset.

    Args:
        symbol: Yahoo Finance ticker, e.g. ``"SPY"`` or ``"IWDA.AS"``.
        years:  How many years of history to request (1-30, default 10).

    Returns:
        ``{"symbol": "SPY", "currency": "USD",
           "annual_returns": {"2023": 26.3, "2022": -18.2, ...},
           "avg_annual_return": 10.4,
           "years_available": 10}``
        or ``{"error": "..."}`` on failure.
    """
    years = max(1, min(30, years))
    try:
        return await asyncio.to_thread(_fetch_annual_returns_sync, symbol, years)
    except Exception as e:
        logger.warning("get_historical_annual_returns(%s) failed: %s", symbol, e)
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Government bond yields — curated table + live ^TNX for US
# ---------------------------------------------------------------------------

def _fetch_bond_yield_sync(country_code: str) -> float | None:
    """Return the current 10Y government bond yield % for the given country.
    Falls back to a curated 2024/2025 estimate when live data is unavailable.
    """
    import yfinance as yf

    # Live tickers for major markets
    live_tickers: dict[str, str] = {
        "US": "^TNX",   # US 10Y Treasury
        "DE": "^BUND",  # German Bund
        "GB": "^TNX",   # Approximate with US (no free UK gilt ticker on YF)
    }
    ticker_sym = live_tickers.get(country_code.upper())
    if ticker_sym:
        try:
            hist = yf.Ticker(ticker_sym).history(period="5d", interval="1d")
            if not hist.empty:
                return round(float(hist["Close"].iloc[-1]), 2)
        except Exception:
            pass  # fall through to curated table

    return None


async def get_bond_yield(country_code: str = "US") -> dict[str, Any]:
    """Return the current 10-year government bond yield for a country.

    Useful for comparing risk-free rate vs equity returns in FIRE and portfolio
    analysis (bond allocation yield, real return calculations).

    Args:
        country_code: ISO 3166-1 alpha-2 code, e.g. ``"US"``, ``"DE"``, ``"PL"``.

    Returns:
        ``{"country": "US", "yield_pct": 4.35, "maturity": "10Y", "source": "live"}``
    """
    # Curated fallback table (2025 estimates)
    fallback: dict[str, float] = {
        "US": 4.3, "DE": 2.5, "GB": 4.2, "PL": 5.6, "FR": 3.1,
        "IT": 3.8, "ES": 3.3, "CZ": 4.1, "HU": 6.8, "JP": 1.1,
        "AU": 4.4, "CA": 3.5,
    }
    code = country_code.upper()
    try:
        live = await asyncio.to_thread(_fetch_bond_yield_sync, code)
        if live is not None:
            return {"country": code, "yield_pct": live, "maturity": "10Y", "source": "live"}
    except Exception as e:
        logger.warning("get_bond_yield(%s) live fetch failed: %s", code, e)

    rate = fallback.get(code, 3.5)
    return {
        "country": code,
        "yield_pct": rate,
        "maturity": "10Y",
        "source": "estimate (2025)",
        "note": "Verify against current market data for precise calculations.",
    }


# ---------------------------------------------------------------------------
# Inflation estimates — curated fallback table
# ---------------------------------------------------------------------------

async def get_inflation_rate(country_code: str = "PL") -> dict[str, Any]:
    """Return the latest available annual inflation rate for a country.

    Args:
        country_code: ISO 3166-1 alpha-2 country code, e.g. ``"PL"``, ``"US"``, ``"DE"``.

    Returns:
        ``{"country": "PL", "inflation_pct": 4.9, "year": 2024, "source": "estimate"}``
    """
    fallback: dict[str, float] = {
        "US": 3.4, "PL": 4.9, "DE": 2.9, "GB": 3.2, "FR": 2.7,
        "CZ": 2.8, "HU": 4.1, "RO": 5.9, "SK": 3.1, "EU": 2.6,
    }
    code = country_code.upper()
    rate = fallback.get(code, 3.0)
    return {
        "country": code,
        "inflation_pct": rate,
        "year": 2024,
        "source": "IMF/Eurostat estimate",
        "note": "Use as planning assumption; verify against latest official data.",
    }
{%- endif %}
