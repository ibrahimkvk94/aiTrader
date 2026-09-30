from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import csv
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
DURATIONS = {"15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}


@dataclass(frozen=True)
class Bar:
    start: int
    end: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self):
        values = (self.open, self.high, self.low, self.close, self.volume)
        if not all(math.isfinite(v) for v in values):
            raise ValueError("Non-finite OHLCV")
        if self.start >= self.end or min(values[:4]) <= 0 or self.volume < 0:
            raise ValueError("Invalid time, price or volume")
        if not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("Invalid OHLC range")

    def json(self):
        return asdict(self)


def symbol_name(value):
    value = value.upper()
    if not re.fullmatch(r"[A-Z0-9._-]{2,24}", value):
        raise ValueError("Invalid symbol")
    return value


def config(market):
    if market not in {"crypto", "bist"}:
        raise ValueError("Unknown market")
    cfg = json.loads((ROOT / "configs" / f"{market}.json").read_text(encoding="utf-8"))
    expected = ("15m", "1h", "4h") if market == "crypto" else ("1d", "1w", "1mo")
    if tuple(cfg[k] for k in ("base", "setup", "context")) != expected:
        raise ValueError("This v0.1 adapter only supports frames " + str(expected))
    if cfg["initial_cash"] <= 0 or cfg["slippage_bps"] >= 10000:
        raise ValueError("Invalid cash or slippage")
    if not 0 < cfg["allocation_fraction"] <= 1:
        raise ValueError("Invalid allocation")
    if any(cfg[k] < 0 for k in ("fee_bps", "slippage_bps")):
        raise ValueError("Invalid costs")
    if any(cfg[k] < 1 for k in ("pivot_left", "pivot_right", "atr_period", "zone_lifetime", "entry_window")):
        raise ValueError("Invalid lookback")
    return cfg


def fingerprint(cfg):
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:16]


def validate_bars(bars, continuous=False):
    for previous, current in zip(bars, bars[1:]):
        if current.start < previous.end:
            raise ValueError("Duplicate, overlapping or unsorted candles")
        if continuous and current.start != previous.end:
            raise ValueError(f"Missing crypto candle after {previous.end}")
    return bars


def aggregate(bars, seconds):
    """UTC crypto buckets only. Incomplete or gapped buckets never become HTF bars."""
    grouped = {}
    for bar in bars:
        key = bar.start // seconds * seconds
        grouped.setdefault(key, []).append(bar)
    result = []
    for start, group in sorted(grouped.items()):
        if group[0].start != start or group[-1].end != start + seconds:
            continue
        if any(a.end != b.start for a, b in zip(group, group[1:])):
            continue
        result.append(Bar(start, start + seconds, group[0].open,
                          max(b.high for b in group), min(b.low for b in group),
                          group[-1].close, sum(b.volume for b in group)))
    return result


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("CSV timestamps need an explicit UTC offset")
    return int(parsed.timestamp())


def read_csv(path):
    """Explicit close timestamps prevent assumptions about BIST auction/holiday sessions."""
    result = []
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            result.append(Bar(timestamp(row["timestamp"]), timestamp(row["close_timestamp"]),
                              *(float(row[k]) for k in ("open", "high", "low", "close", "volume"))))
    if not result:
        raise ValueError("CSV is empty")
    return validate_bars(result)


def iso(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()
