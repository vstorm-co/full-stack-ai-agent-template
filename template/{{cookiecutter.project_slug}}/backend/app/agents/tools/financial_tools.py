{%- if cookiecutter.enable_skills %}
"""Financial data tools available as external functions inside the Monty sandbox.

All functions run in the HOST environment (not in the sandbox), so they can make
real HTTP requests. They are exposed to sandboxed code via ``_build_external_functions``
in code_execution.py, letting model-written Python fetch live market data and use
it directly in calculations and charts.

APIs used:
- yfinance — stock/ETF prices, historical OHLCV, and 10Y government bond yields
- Frankfurter (frankfurter.dev) — ECB-sourced FX rates, free, no key needed
- World Bank (api.worldbank.org) — annual CPI inflation, free, no key needed
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0


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


_BOND_TICKERS: dict[str, str] = {
    "US": "^TNX",
    "DE": "^BUND",
    "GB": "^TNX",
}


def _fetch_bond_yield_sync(ticker_sym: str) -> float | None:
    import yfinance as yf

    hist = yf.Ticker(ticker_sym).history(period="5d", interval="1d")
    if hist.empty:
        return None
    return round(float(hist["Close"].iloc[-1]), 2)


async def get_bond_yield(country_code: str = "US") -> dict[str, Any]:
    """Return the current 10-year government bond yield for a country.

    Live data via yfinance.

    Args:
        country_code: ISO 3166-1 alpha-2 code, e.g. ``"US"``, ``"DE"``, ``"GB"``.

    Returns:
        ``{"country": "US", "yield_pct": 4.35, "maturity": "10Y", "source": "live"}``
        or ``{"error": "..."}`` when no live series is available.
    """
    code = country_code.upper()
    ticker_sym = _BOND_TICKERS.get(code)
    if ticker_sym is None:
        return {"error": f"No live 10Y bond yield series available for {code!r}"}
    try:
        live = await asyncio.to_thread(_fetch_bond_yield_sync, ticker_sym)
    except Exception as e:
        logger.warning("get_bond_yield(%s) failed: %s", code, e)
        return {"error": str(e)}
    if live is None:
        return {"error": f"No live 10Y bond yield data for {code!r}"}
    return {"country": code, "yield_pct": live, "maturity": "10Y", "source": "live"}


async def get_inflation_rate(country_code: str = "PL") -> dict[str, Any]:
    """Return the latest available annual CPI inflation rate for a country.

    Live data via the World Bank indicator ``FP.CPI.TOTL.ZG`` (annual % change of
    consumer prices). Returns the most recent year that has a value.

    Args:
        country_code: ISO 3166-1 alpha-2 country code, e.g. ``"PL"``, ``"US"``, ``"DE"``.

    Returns:
        ``{"country": "PL", "inflation_pct": 4.9, "year": 2024, "source": "World Bank"}``
        or ``{"error": "..."}`` on failure.
    """
    code = country_code.upper()
    current_year = datetime.now(UTC).year
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            url = (
                f"https://api.worldbank.org/v2/country/{code}/indicator/FP.CPI.TOTL.ZG"
                f"?format=json&per_page=100&date={current_year - 6}:{current_year}"
            )
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list) or len(data) < 2 or not data[1]:
                return {"error": f"No inflation data for {code!r}"}
            latest: tuple[int, float] | None = None
            for obs in data[1]:
                value = obs.get("value")
                if value is None:
                    continue
                year = int(obs["date"])
                if latest is None or year > latest[0]:
                    latest = (year, float(value))
            if latest is None:
                return {"error": f"No inflation data for {code!r}"}
            return {
                "country": code,
                "inflation_pct": round(latest[1], 2),
                "year": latest[0],
                "source": "World Bank",
            }
    except Exception as e:
        logger.warning("get_inflation_rate(%s) failed: %s", code, e)
        return {"error": str(e)}
{%- endif %}
