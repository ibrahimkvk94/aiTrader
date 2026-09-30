"""Offline experiments only. Does not change the running scanner's rules.

Short *signals* reuse the long rules under an affine price reflection, chosen
using only the first candle. Reflected account values are discarded. All fills,
fees, funding and portfolio accounting use ORIGINAL futures prices below.
"""
from dataclasses import dataclass
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .engine import replay
from .model import ROOT, Bar, aggregate, validate_bars, symbol_name

FUTURES_URL = "https://fapi.binance.com"


def get(path, params=None):
    request = Request(FUTURES_URL + path + ("?" + urlencode(params) if params else ""),
                      headers={"User-Agent": "aiTraderResearch/0.1"})
    with urlopen(request, timeout=25) as response:
        return json.load(response)


def futures_data(symbol, start, end):
    symbol = symbol_name(symbol)
    server_end = int(get("/fapi/v1/time")["serverTime"]) // 1000
    end = min(end, server_end // 900 * 900)
    directory = ROOT / "data" / "experiments"
    directory.mkdir(parents=True, exist_ok=True)
    cache = directory / f"{symbol}-{start}-{end}.json"
    if cache.exists():
        saved = json.loads(cache.read_text(encoding="utf-8"))
        return validate_bars([Bar(**b) for b in saved["bars"]], continuous=True), saved["funding"]
    cursor, bars = start * 1000, []
    while cursor < end * 1000:
        rows = get("/fapi/v1/klines", {"symbol": symbol, "interval": "15m", "startTime": cursor,
                   "endTime": end * 1000 - 1, "limit": 1000})
        if not rows:
            break
        for row in rows:
            bar_end = (int(row[6]) + 1) // 1000
            if bar_end <= end:
                bars.append(Bar(int(row[0])//1000, bar_end, *(float(row[i]) for i in (1,2,3,4,5))))
        advanced = int(rows[-1][6]) + 1
        if advanced <= cursor:
            raise ValueError("Futures pagination did not advance")
        cursor = advanced
        time.sleep(.12)
    validate_bars(bars, continuous=True)
    if not bars or bars[0].start != start or bars[-1].end != end:
        raise ValueError("Requested futures coverage is incomplete")
    cursor, funding = start * 1000, []
    while cursor < end * 1000:
        rows = get("/fapi/v1/fundingRate", {"symbol": symbol, "startTime": cursor,
                   "endTime": end * 1000 - 1, "limit": 1000})
        if not rows:
            break
        for row in rows:
            mark = float(row.get("markPrice", 0))
            if mark <= 0:
                raise ValueError("Funding record missing mark price")
            funding.append({"time": int(row["fundingTime"]) / 1000,
                            "rate": float(row["fundingRate"]), "mark": mark})
        advanced = int(rows[-1]["fundingTime"]) + 1
        if advanced <= cursor:
            raise ValueError("Funding pagination did not advance")
        cursor = advanced
        if len(rows) < 1000:
            break
    if not funding:
        raise ValueError("No funding history: refusing zero-funding assumption")
    funding.sort(key=lambda f: f["time"])
    # This research universe is BTC/ETH USD-M. Refuse large unexplained funding gaps.
    if (funding[0]["time"] - start > 12*3600 or end - funding[-1]["time"] > 12*3600
            or any(b["time"] - a["time"] > 12*3600 for a,b in zip(funding,funding[1:]))):
        raise ValueError("Funding coverage has an unexplained gap >12h")
    cache.write_text(json.dumps({"bars": [b.json() for b in bars], "funding": funding}), encoding="utf-8")
    return bars, funding


def mtf_filter(engine, bar, zone):
    """Predeclared candidate: HTF zone overlap + room to nearest HTF supply.

    No learned thresholds: >=1 structural risk-distance of headroom. This is an
    entry filter; it does not insert a fixed price stop or a take-profit order.
    """
    higher = [z for z in engine.context.zones if z.active and z.known_at <= bar.start]
    supported = any(z.kind in {"demand", "breaker"} and max(z.low, zone.low) <= min(z.high, zone.high)
                    for z in higher)
    if not supported:
        return False
    risk_distance = bar.close - zone.low
    # Supply that contains current price is an immediate obstacle, not skipped.
    obstacles = [max(0.0, z.low - bar.close) for z in higher if z.kind == "supply" and z.high >= bar.close]
    return risk_distance > 0 and (not obstacles or min(obstacles) >= risk_distance)


def reflect(bars, anchor):
    return [Bar(b.start, b.end, anchor-b.open, anchor-b.low, anchor-b.high, anchor-b.close, b.volume)
            for b in bars]


def direction_signals(cfg, bars, side, use_mtf=False):
    if side not in (1, -1):
        raise ValueError("Side must be 1 or -1")
    # Anchor uses first observed price, never full-sample min/max.
    signal_bars = bars if side == 1 else reflect(bars, bars[0].open * 100)
    signal_cfg = {**cfg, "fee_bps": 0, "slippage_bps": 0}
    engine = replay(signal_cfg, signal_bars, aggregate(signal_bars, 3600), aggregate(signal_bars, 14400),
                    entry_filter=mtf_filter if use_mtf else None)
    orders = [{"time": e["time"], "action": e["action"], "side": side, "reason": e["reason"]}
              for e in engine.events if e["action"] in {"BUY", "SELL"}]
    return orders


def account(cfg, bars, orders, funding):
    """One collateralized position at a time; never borrow cash or reuse margin.

    Funding at a boundary applies to the existing position before open-price
    exits/entries. Entries use 10% of available equity as fully funded notional.
    This is not an exchange liquidation/margin-tier simulator.
    """
    scheduled = {}
    for order in orders:
        scheduled.setdefault(order["time"], []).append(order)
    cash, position, trades, curve = float(cfg["initial_cash"]), None, [], []
    funding_index = 0
    fee, slip = cfg["fee_bps"]/10000, cfg["slippage_bps"]/10000
    funding_total = 0.0
    skipped_conflicts = 0
    for bar in bars:
        while funding_index < len(funding) and funding[funding_index]["time"] <= bar.start:
            f = funding[funding_index]
            if position and f["time"] > position["entry_time"]:
                payment = -position["side"] * position["qty"] * f["mark"] * f["rate"]
                cash += payment
                position["funding"] += payment
                funding_total += payment
            funding_index += 1
        actions = sorted(scheduled.get(bar.start, []), key=lambda o: o["action"] == "BUY")
        for order in actions:
            side = order["side"]
            if order["action"] == "SELL":
                if not position or position["side"] != side:
                    continue
                p = position
                price = bar.open * (1-side*slip)
                exit_fee = p["qty"] * price * fee
                gross = side * p["qty"] * (price-p["entry_price"])
                cash += p["margin"] + gross - exit_fee
                trades.append({**p, "exit_time": bar.start, "exit_price": price, "exit_fee": exit_fee,
                               "pnl": gross-p["entry_fee"]-exit_fee+p["funding"], "exit_reason": order["reason"]})
                position = None
            elif position:
                skipped_conflicts += 1
            elif cash > 0:
                price = bar.open*(1+side*slip)
                budget = cash * cfg["allocation_fraction"]
                margin = budget/(1+fee)
                entry_fee = margin*fee
                qty = margin/price
                cash -= margin+entry_fee
                position = {"side": side, "entry_time": bar.start, "entry_price": price, "qty": qty,
                            "margin": margin, "entry_fee": entry_fee, "funding": 0.0}
        value = cash
        if position:
            value += position["margin"] + position["side"]*position["qty"]*(bar.close-position["entry_price"])
        curve.append({"time":bar.end,"value":value})
    # Apply any funding after the final open through the final closed candle.
    while funding_index < len(funding) and funding[funding_index]["time"] < bars[-1].end:
        f = funding[funding_index]
        if position and f["time"] > position["entry_time"]:
            payment = -position["side"]*position["qty"]*f["mark"]*f["rate"]
            cash += payment
            position["funding"] += payment
            funding_total += payment
            curve[-1]["value"] += payment
        funding_index += 1
    peak, dd = cfg["initial_cash"], 0.0
    for point in curve:
        peak = max(peak, point["value"])
        dd = max(dd, (peak-point["value"])/peak*100)
    gains = sum(t["pnl"] for t in trades if t["pnl"]>0)
    losses = -sum(t["pnl"] for t in trades if t["pnl"]<0)
    ending = curve[-1]["value"]
    return {"closed_trades":len(trades),"long_trades":sum(t["side"]==1 for t in trades),
            "short_trades":sum(t["side"]==-1 for t in trades),
            "win_rate_pct":100*sum(t["pnl"]>0 for t in trades)/len(trades) if trades else None,
            "net_return_pct":100*(ending/cfg["initial_cash"]-1),"closed_pnl":sum(t["pnl"] for t in trades),
            "max_drawdown_pct":dd,"profit_factor":gains/losses if losses else None,
            "funding_pnl":funding_total,"skipped_conflicts":skipped_conflicts,
            "open_position":position,"trades":trades,"equity":curve}


def compare(cfg, bars, funding):
    variants = []
    for mtf in (False, True):
        longs = direction_signals(cfg, bars, 1, mtf)
        shorts = direction_signals(cfg, bars, -1, mtf)
        for both in (False, True):
            orders = longs + (shorts if both else [])
            normal = account(cfg, bars, orders, funding)
            stress = account({**cfg,"fee_bps":2*cfg["fee_bps"],"slippage_bps":2*cfg["slippage_bps"]}, bars, orders, funding)
            windows = []
            # Descriptive time blocks only; not called unseen/OOS because recent data was already inspected.
            for i in range(3):
                a,b = len(bars)*i//3, len(bars)*(i+1)//3
                curve = normal["equity"]
                first = cfg["initial_cash"] if a==0 else curve[a-1]["value"]
                windows.append({"start":bars[a].start,"end":bars[b-1].end,
                    "return_pct":100*(curve[b-1]["value"]/first-1),
                    "closed_trades":sum(bars[a].start<=t["exit_time"]<bars[b-1].end for t in normal["trades"])})
            variants.append({"variant": ("long_short" if both else "long_only")+("_mtf" if mtf else "_baseline"),
                **{k:v for k,v in normal.items() if k not in {"equity","trades","open_position"}},
                "open_position":normal["open_position"], "double_cost_return_pct":stress["net_return_pct"],
                "time_blocks":windows,"trades":normal["trades"]})
    return variants
