"""Streaming structural decisions, executed at NEXT available candle open.

Experimental long-only models: demand continuation, demand+sweep, bullish breaker.
No fixed percent stop or take profit. No live orders and no online rule mutation.
"""
from dataclasses import dataclass, asdict
from statistics import mean
from .model import validate_bars


@dataclass
class Zone:
    id: str
    low: float
    high: float
    kind: str
    source_time: int
    known_at: int
    expires_at_index: int
    active: bool = True
    used: bool = False
    touched_at: int = -1


class Structure:
    def __init__(self, cfg, name):
        self.cfg, self.name = cfg, name
        self.bars, self.tr, self.zones = [], [], []
        self.high_pivot = self.low_pivot = None
        self.broken = set()
        self.trend = 0
        self.atr = None
        self.new_low = None
        self.bull = self.bear = False

    def push(self, bar):
        cfg = self.cfg
        previous = self.bars[-1] if self.bars else None
        self.atr = mean(self.tr[-cfg["atr_period"]:]) if len(self.tr) >= cfg["atr_period"] else None
        self.bull = self.bear = False
        self.new_low = None
        # Only pivots already known before this candle can be crossed or swept.
        swept_low = self.low_pivot is not None and bar.low < self.low_pivot[1] < bar.close
        for side, pivot in ((1, self.high_pivot), (-1, self.low_pivot)):
            if previous and pivot and (side, pivot[0]) not in self.broken:
                crossed = (previous.close <= pivot[1] < bar.close) if side == 1 else (previous.close >= pivot[1] > bar.close)
                if crossed:
                    self.broken.add((side, pivot[0]))
                    self.trend = side
                    self.bull, self.bear = side == 1, side == -1
        index = len(self.bars)
        strong = self.atr is not None and abs(bar.close - bar.open) >= cfg["displacement_atr"] * self.atr
        additions = []
        for zone in self.zones:
            if not zone.active:
                continue
            if index > zone.expires_at_index:
                zone.active = False
                continue
            invalid = bar.close < zone.low if zone.kind in {"demand", "breaker"} else bar.close > zone.high
            if invalid:
                zone.active = False
                if zone.kind == "supply" and self.bull and strong:
                    additions.append(Zone(f"{self.name}-breaker-{bar.end}", zone.low, zone.high,
                        "breaker", zone.source_time, bar.end, index + cfg["zone_lifetime"]))
        if strong and (self.bull or self.bear):
            side = 1 if self.bull else -1
            source = next((b for b in reversed(self.bars[-cfg["zone_lookback"]:])
                           if (b.close < b.open if side == 1 else b.close > b.open)), None)
            if source:
                kind = "demand" if side == 1 else "supply"
                additions.append(Zone(f"{self.name}-{kind}-{bar.end}", source.low, source.high,
                                      kind, source.start, bar.end, index + cfg["zone_lifetime"]))
        # A breaker takes precedence over a new demand zone at the same confirmation.
        self.zones.extend(additions)
        self.tr.append(max(bar.high - bar.low, abs(bar.high - previous.close),
                           abs(bar.low - previous.close)) if previous else bar.high - bar.low)
        self.bars.append(bar)
        left, right = cfg["pivot_left"], cfg["pivot_right"]
        if len(self.bars) >= left + right + 1:
            p = len(self.bars) - 1 - right
            candidate = self.bars[p]
            window = self.bars[p-left:p] + self.bars[p+1:p+right+1]
            if all(candidate.high > b.high for b in window):
                self.high_pivot = (candidate.start, candidate.high, bar.end)
            if all(candidate.low < b.low for b in window):
                self.low_pivot = (candidate.start, candidate.low, bar.end)
                self.new_low = self.low_pivot
        return {"bull": self.bull, "bear": self.bear, "sweep": swept_low}


class Engine:
    def __init__(self, cfg):
        self.cfg = cfg
        self.base = Structure(cfg, "base")
        self.setup = Structure(cfg, "setup")
        self.context = Structure(cfg, "context")
        self.cash = float(cfg["initial_cash"])
        self.position = self.pending = None
        self.events, self.trades, self.equity = [], [], []
        self.last_sweep = -100000

    def event(self, bar, action, reason, **extra):
        self.events.append({"time": bar.end, "action": action, "reason": reason,
                            "price": bar.close, **extra})

    def fill(self, bar):
        if not self.pending:
            return
        order, self.pending = self.pending, None
        fee = self.cfg["fee_bps"] / 10000
        slip = self.cfg["slippage_bps"] / 10000
        if order["side"] == "buy":
            if bar.open <= order["zone_low"] or abs(bar.open - order["signal_price"]) > order["atr"] * self.cfg["max_entry_gap_atr"]:
                self.events.append({"time": bar.start, "action": "CANCEL", "price": bar.open,
                                    "reason": "Açılışta bölge geçersiz veya giriş boşluğu fazla"})
                return
            price = bar.open * (1 + slip)
            budget = self.cash * self.cfg["allocation_fraction"]
            qty = budget / (price * (1 + fee))
            entry_fee = qty * price * fee
            self.cash -= qty * price + entry_fee
            self.position = {"entry_time": bar.start, "entry_signal_time": order["signal_time"],
                "entry_price": price, "qty": qty, "entry_fee": entry_fee, "model": order["model"],
                "zone_low": order["zone_low"], "protected_low": order["zone_low"],
                "zone_id": order["zone_id"], "mfe_pct": 0.0, "mae_pct": 0.0}
            self.events.append({"time": bar.start, "action": "BUY", "price": price,
                                "reason": "Önceki kapanış sinyali; sonraki açılış simülasyonu", "model": order["model"]})
        elif self.position:
            p = self.position
            price = bar.open * (1 - slip)
            exit_fee = p["qty"] * price * fee
            proceeds = p["qty"] * price - exit_fee
            cost = p["qty"] * p["entry_price"] + p["entry_fee"]
            self.cash += proceeds
            trade = {**p, "exit_time": bar.start, "exit_signal_time": order["signal_time"],
                     "exit_price": price, "exit_fee": exit_fee, "pnl": proceeds - cost,
                     "return_pct": (proceeds / cost - 1) * 100, "exit_reason": order["reason"]}
            # Include the executable exit price, but not the subsequent candle's range.
            trade["mfe_pct"] = max(p["mfe_pct"], (price / p["entry_price"] - 1) * 100)
            trade["mae_pct"] = min(p["mae_pct"], (price / p["entry_price"] - 1) * 100)
            self.trades.append(trade)
            self.events.append({"time": bar.start, "action": "SELL", "price": price, "reason": order["reason"], "pnl": trade["pnl"]})
            self.position = None

    def step(self, bar, setup_bars=(), context_bars=()):
        self.fill(bar)
        for higher in context_bars:
            if higher.end > bar.end:
                raise ValueError("Unclosed context candle")
            self.context.push(higher)
        for higher in setup_bars:
            if higher.end > bar.end:
                raise ValueError("Unclosed setup candle")
            self.setup.push(higher)
        signal = self.base.push(bar)
        index = len(self.base.bars) - 1
        if signal["sweep"]:
            self.last_sweep = index
        snapshot = {"context_trend": self.context.trend, "setup_trend": self.setup.trend,
                    "base_trend": self.base.trend, "sweep": signal["sweep"]}
        if self.position:
            p = self.position
            p["mfe_pct"] = max(p["mfe_pct"], (bar.high / p["entry_price"] - 1) * 100)
            p["mae_pct"] = min(p["mae_pct"], (bar.low / p["entry_price"] - 1) * 100)
            reason = None
            if setup_bars and self.setup.bars[-1].close < p["zone_low"]:
                reason = "Kurulum mumu talep/breaker bölgesi altında kapandı"
            elif self.context.trend == -1:
                reason = "Üst zaman diliminde düşüş yapısı onaylandı"
            elif bar.close < p["protected_low"]:
                reason = "Giriş zaman dilimi korunan dip altında kapandı"
            if reason:
                self.pending = {"side": "sell", "signal_time": bar.end, "reason": reason}
                self.event(bar, "EXIT_SIGNAL", reason, **snapshot, protected_low=p["protected_low"])
            else:
                low = self.base.new_low
                if low and low[0] >= p["entry_time"] and p["protected_low"] < low[1] < bar.close:
                    p["protected_low"] = low[1]
                self.event(bar, "HOLD", "Kapanışta yapısal geçersizleşme yok", **snapshot, protected_low=p["protected_low"])
        else:
            zones = [z for z in self.setup.zones if z.active and not z.used
                     and z.kind in {"demand", "breaker"} and z.known_at <= bar.start]
            for zone in zones:
                if bar.low <= zone.high and bar.high >= zone.low and bar.close >= zone.low:
                    zone.touched_at = index
            candidates = [z for z in zones if z.touched_at >= 0 and index - z.touched_at <= self.cfg["entry_window"]
                          and bar.close > z.high]
            if (self.context.trend == 1 and self.setup.trend == 1 and signal["bull"]
                    and self.base.atr and candidates):
                zone = sorted(candidates, key=lambda z: (z.kind == "breaker", z.known_at), reverse=True)[0]
                model = "breaker" if zone.kind == "breaker" else (
                    "demand_sweep" if index - self.last_sweep <= self.cfg["entry_window"] else "demand_continuation")
                zone.used = True
                self.pending = {"side": "buy", "signal_time": bar.end, "signal_price": bar.close,
                    "zone_low": zone.low, "zone_id": zone.id, "model": model, "atr": self.base.atr}
                self.event(bar, "ENTRY_SIGNAL", "Üst yapı yukarı; bölge dönüşü ve giriş yapısı teyitli", **snapshot,
                           model=model, zone_id=zone.id, zone_low=zone.low)
            else:
                reason = ("Üst zaman dilimi yükseliş teyidi bekleniyor" if self.context.trend != 1
                          else "Kurulum yapısı yükseliş teyidi bekleniyor" if self.setup.trend != 1
                          else "Bölge dönüşü sonrası giriş yapısı kırılması bekleniyor")
                self.event(bar, "WATCH", reason, **snapshot)
        value = self.cash + (self.position["qty"] * bar.close if self.position else 0)
        self.equity.append({"time": bar.end, "value": value})

    def summary(self):
        initial = self.cfg["initial_cash"]
        ending = self.equity[-1]["value"] if self.equity else initial
        peak, drawdown = initial, 0
        for point in self.equity:
            peak = max(peak, point["value"])
            drawdown = max(drawdown, (peak - point["value"]) / peak * 100)
        wins = [t for t in self.trades if t["pnl"] > 0]
        gains = sum(t["pnl"] for t in wins)
        losses = -sum(t["pnl"] for t in self.trades if t["pnl"] < 0)
        return {"initial_cash": initial, "equity": ending, "net_return_pct": (ending / initial - 1) * 100,
                "max_drawdown_pct": drawdown, "closed_trades": len(self.trades),
                "win_rate_pct": len(wins) / len(self.trades) * 100 if self.trades else None,
                "profit_factor": gains / losses if losses else None,
                "closed_pnl": sum(t["pnl"] for t in self.trades),
                "open_position": self.position, "pending": self.pending}


def replay(cfg, bars, setups, contexts):
    validate_bars(bars, continuous=cfg["market"] == "crypto")
    validate_bars(setups)
    validate_bars(contexts)
    engine = Engine(cfg)
    si = ci = 0
    for bar in bars:
        new_s, new_c = [], []
        while si < len(setups) and setups[si].end <= bar.end:
            new_s.append(setups[si])
            si += 1
        while ci < len(contexts) and contexts[ci].end <= bar.end:
            new_c.append(contexts[ci])
            ci += 1
        engine.step(bar, new_s, new_c)
    return engine
