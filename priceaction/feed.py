"""Public market-data requests only. This module cannot submit orders."""
import json
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .model import Bar, validate_bars, symbol_name

BASE = "https://data-api.binance.vision"
# Verified null-row exceptions, not a complete exchange calendar.
# https://www.borsaistanbul.com/resmi-tatil-gunleri (checked 2026-09-30)
VERIFIED_BIST_CLOSED = {"2026-04-23", "2026-05-01", "2026-05-19", "2026-07-15"}


def public_get(path, params=None):
    url = BASE + path + ("?" + urlencode(params) if params else "")
    request = Request(url, headers={"User-Agent": "PriceActionResearch/0.1"})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def download(symbol, start, end=None):
    symbol = symbol_name(symbol)
    server_now = public_get("/api/v3/time")["serverTime"] // 1000
    end = min(end or server_now, server_now)
    cursor = start * 1000
    result = []
    while cursor < end * 1000:
        rows = public_get("/api/v3/klines", {"symbol": symbol, "interval": "15m",
                           "startTime": cursor, "endTime": end * 1000 - 1, "limit": 1000})
        if not rows:
            break
        for row in rows:
            close_time = (int(row[6]) + 1) // 1000
            if close_time <= end:
                result.append(Bar(int(row[0]) // 1000, close_time,
                                  *(float(row[i]) for i in (1, 2, 3, 4, 5))))
        next_cursor = int(rows[-1][6]) + 1
        if next_cursor <= cursor:
            raise ValueError("Provider pagination did not advance")
        cursor = next_cursor
        if len(rows) < 1000:
            break
        time.sleep(0.12)
    return validate_bars(result, continuous=True)


def download_bist_daily(symbol):
    """Experimental personal-use Yahoo feed; exclude the entire current UTC day.

    Raw vendor OHLC; NOT certified point-in-time/corporate-action data.
    Daily candles become usable at the FOLLOWING UTC midnight, conservatively.
    """
    symbol = symbol_name(symbol)
    if not symbol.endswith(".IS"):
        raise ValueError("Yahoo BIST symbols must end in .IS")
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + symbol + "?" + urlencode(
        {"interval": "1d", "range": "5y", "events": "div,splits"})
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 PriceActionResearch/0.1"})
    with urlopen(req, timeout=20) as response:
        chart = json.load(response)["chart"]
    if chart.get("error") or not chart.get("result"):
        raise ValueError("Yahoo returned no chart")
    payload = chart["result"][0]
    if payload["meta"].get("exchangeName") != "IST":
        raise ValueError("Not a BIST instrument")
    quote = payload["indicators"]["quote"][0]
    cutoff = int(time.time()) // 86400 * 86400
    bars, missing_dates, closed_dates = [], [], []
    split_dates = [int(v["date"]) for v in payload.get("events", {}).get("splits", {}).values()]
    after_split = max(split_dates, default=0)
    for i, stamp in enumerate(payload["timestamp"]):
        day = stamp // 86400 * 86400
        if day + 86400 > cutoff or stamp <= after_split:
            continue
        values = [quote[k][i] for k in ("open", "high", "low", "close", "volume")]
        if any(v is None for v in values):
            date = datetime.fromtimestamp(stamp, timezone.utc).date().isoformat()
            if all(v is None for v in values) and date in VERIFIED_BIST_CLOSED:
                closed_dates.append(date)
            else:
                # Restart history after an unknown gap instead of carrying structure across it.
                bars = []
                missing_dates.append(date)
            continue
        bars.append(Bar(stamp, day + 86400, *(float(v) for v in values)))
    if len(bars) < 120:
        raise ValueError("Not enough daily history after missing-data/split boundary (minimum 120 bars)")
    return validate_bars(bars), {"source": "Yahoo Finance / günlük, deneysel", "delay": "Bugünkü mum hariç",
        "corporate_actions_verified": False, "history_after_split": after_split or None,
        "history_reset_after_missing": missing_dates[-1] if missing_dates else None,
        "verified_closed_dates": closed_dates}


def calendar_aggregate(bars, period, now=None):
    """BIST daily -> calendar week/month; publish only after full calendar period.

    No invented weekend candles. This is not an exchange-calendar validation.
    """
    now = int(time.time()) if now is None else now
    groups = {}
    for bar in bars:
        date = datetime.fromtimestamp(bar.start, timezone.utc)
        if period == "1w":
            begin = (date - timedelta(days=date.weekday())).replace(hour=0, minute=0, second=0)
            end = begin + timedelta(days=7)
        elif period == "1mo":
            begin = date.replace(day=1, hour=0, minute=0, second=0)
            end = begin.replace(year=begin.year + 1, month=1) if begin.month == 12 else begin.replace(month=begin.month + 1)
        else:
            raise ValueError("Unsupported calendar period")
        groups.setdefault((int(begin.timestamp()), int(end.timestamp())), []).append(bar)
    result = []
    for (start, end), group in sorted(groups.items()):
        # Drop initial partial calendar bucket even when data starts midweek/month.
        if start < bars[0].start // 86400 * 86400 or end > now:
            continue
        result.append(Bar(start, end, group[0].open, max(b.high for b in group), min(b.low for b in group),
                          group[-1].close, sum(b.volume for b in group)))
    return result
