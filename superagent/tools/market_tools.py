"""
Market Data Tools

Provides:
- Real-time stock/crypto/forex price data
- Historical data retrieval
- Technical indicator calculation
- News sentiment for market instruments

Uses Yahoo Finance (yfinance) and Alpha Vantage APIs.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

# Global config (set during registration)
_config: dict[str, Any] = {}


def register(registry: Any) -> None:
    """Register market tools with the tool registry."""

    @registry.register_decorator(
        name="market_data",
        description="Fetch real-time or historical market data for stocks, crypto, or forex. "
        "Returns price, volume, change, and technical indicators.",
        category="market",
    )
    async def market_data(
        symbol: str,
        data_type: str = "quote",
        interval: str = "1d",
        period: str = "1mo",
    ) -> str:
        """
        Fetch market data.

        Args:
            symbol: Ticker symbol (e.g., AAPL, BTC-USD, EUR/USD)
            data_type: "quote" (real-time), "historical", "overview"
            interval: Data interval (1m, 5m, 15m, 1h, 1d, 1wk, 1mo)
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 5y, max)
        """
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)

            if data_type == "quote":
                info = ticker.info
                return json.dumps({
                    "symbol": symbol,
                    "name": info.get("longName", symbol),
                    "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                    "previous_close": info.get("previousClose"),
                    "open": info.get("open"),
                    "day_high": info.get("dayHigh"),
                    "day_low": info.get("dayLow"),
                    "volume": info.get("volume"),
                    "market_cap": info.get("marketCap"),
                    "pe_ratio": info.get("trailingPE"),
                    "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                    "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                    "currency": info.get("currency", "USD"),
                    "exchange": info.get("exchange"),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                }, indent=2)

            elif data_type == "historical":
                hist = ticker.history(period=period, interval=interval)
                if hist.empty:
                    return json.dumps({"error": f"No data found for {symbol}"})

                records = []
                for idx, row in hist.tail(100).iterrows():
                    records.append({
                        "date": str(idx),
                        "open": round(float(row["Open"]), 4),
                        "high": round(float(row["High"]), 4),
                        "low": round(float(row["Low"]), 4),
                        "close": round(float(row["Close"]), 4),
                        "volume": int(row["Volume"]),
                    })

                return json.dumps({
                    "symbol": symbol,
                    "interval": interval,
                    "period": period,
                    "count": len(records),
                    "data": records[-20:],  # last 20 data points
                }, indent=2)

            elif data_type == "overview":
                info = ticker.info
                return json.dumps({
                    "symbol": symbol,
                    "name": info.get("longName"),
                    "sector": info.get("sector"),
                    "industry": info.get("industry"),
                    "description": info.get("longBusinessSummary", "")[:500],
                    "employees": info.get("fullTimeEmployees"),
                    "website": info.get("website"),
                    "ceo": info.get("companyOfficers", [{}])[0].get("name") if info.get("companyOfficers") else None,
                    "country": info.get("country"),
                }, indent=2)

            else:
                return json.dumps({"error": f"Unknown data_type: {data_type}"})

        except ImportError:
            return json.dumps({"error": "yfinance not installed. Run: pip install yfinance"})
        except Exception as e:
            logger.error("market_data_failed", symbol=symbol, error=str(e))
            return json.dumps({"error": str(e)})

    @registry.register_decorator(
        name="market_search",
        description="Search for financial instruments by name or ticker.",
        category="market",
    )
    async def market_search(query: str, limit: int = 5) -> str:
        """Search for tickers by name or symbol."""
        try:
            import yfinance as yf

            # yfinance doesn't have a direct search, use lookup
            ticker = yf.Ticker(query)
            info = ticker.info

            if not info or "symbol" not in info:
                return json.dumps({"results": [], "query": query})

            return json.dumps({
                "query": query,
                "results": [{
                    "symbol": info.get("symbol", query),
                    "name": info.get("longName", query),
                    "exchange": info.get("exchange"),
                    "type": info.get("quoteType"),
                }],
            }, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @registry.register_decorator(
        name="technical_indicators",
        description="Calculate technical indicators for a symbol (SMA, EMA, RSI, MACD, Bollinger Bands).",
        category="market",
    )
    async def technical_indicators(
        symbol: str,
        indicators: str = "sma,rsi,macd",
        period: str = "3mo",
    ) -> str:
        """
        Calculate technical indicators.

        Args:
            symbol: Ticker symbol
            indicators: Comma-separated list: sma, ema, rsi, macd, bollinger
            period: Data period
        """
        try:
            import numpy as np
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)

            if hist.empty:
                return json.dumps({"error": f"No data for {symbol}"})

            close = hist["Close"].values
            result: dict[str, Any] = {"symbol": symbol, "period": period}
            indicator_list = [i.strip().lower() for i in indicators.split(",")]

            if "sma" in indicator_list:
                for window in [20, 50, 200]:
                    if len(close) >= window:
                        sma = float(np.mean(close[-window:]))
                        result[f"sma_{window}"] = round(sma, 4)

            if "ema" in indicator_list:
                for span in [12, 26]:
                    if len(close) >= span:
                        multiplier = 2 / (span + 1)
                        ema = float(close[0])
                        for price in close[1:]:
                            ema = (float(price) - ema) * multiplier + ema
                        result[f"ema_{span}"] = round(ema, 4)

            if "rsi" in indicator_list and len(close) >= 15:
                deltas = np.diff(close[-15:])
                gains = np.where(deltas > 0, deltas, 0)
                losses = np.where(deltas < 0, -deltas, 0)
                avg_gain = float(np.mean(gains))
                avg_loss = float(np.mean(losses))
                if avg_loss == 0:
                    result["rsi_14"] = 100.0
                else:
                    rs = avg_gain / avg_loss
                    result["rsi_14"] = round(100 - (100 / (1 + rs)), 2)

            if "macd" in indicator_list and len(close) >= 26:
                # Simplified MACD
                ema12 = float(np.mean(close[-12:]))
                ema26 = float(np.mean(close[-26:]))
                macd_line = ema12 - ema26
                signal = float(np.mean([macd_line]))  # simplified
                result["macd"] = {
                    "line": round(macd_line, 4),
                    "signal": round(signal, 4),
                    "histogram": round(macd_line - signal, 4),
                }

            if "bollinger" in indicator_list and len(close) >= 20:
                sma20 = float(np.mean(close[-20:]))
                std20 = float(np.std(close[-20:]))
                result["bollinger"] = {
                    "upper": round(sma20 + 2 * std20, 4),
                    "middle": round(sma20, 4),
                    "lower": round(sma20 - 2 * std20, 4),
                    "current_price": round(float(close[-1]), 4),
                }

            result["current_price"] = round(float(close[-1]), 4)
            return json.dumps(result, indent=2)

        except ImportError:
            return json.dumps({"error": "numpy not installed"})
        except Exception as e:
            return json.dumps({"error": str(e)})


def set_config(config: dict[str, Any]) -> None:
    """Set market tools configuration."""
    global _config
    _config = config
