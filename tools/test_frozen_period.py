"""Frozen historical transfer test; not a chronological walk-forward test."""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from priceaction.experiments import account, compare, direction_signals, futures_data
from priceaction.model import ROOT, Bar, iso, timestamp, validate_bars

START = timestamp("2025-10-01T00:00:00Z")
END = timestamp("2026-04-01T00:00:00Z")
WARMUP = 14 * 86400
SYMBOLS = ("BTCUSDT", "ETHUSDT")
VARIANTS = (
    ("long_only_baseline", False, False, False),
    ("long_short_baseline", True, False, False),
    ("long_only_mtf", False, True, False),
    ("long_short_mtf", True, True, False),
    ("long_short_mtf_sweep", True, True, True),
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new_or_identical(path, value):
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != value:
            raise ValueError(f"Refusing to overwrite different evidence: {path}")
        return
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)


def loss_groups(trades):
    result = {}
    for key in ("side", "model", "exit_reason"):
        groups = defaultdict(list)
        for trade in trades:
            groups[str(trade.get(key, "unknown"))].append(trade)
        result[key] = [{"group": name, "count": len(items),
                        "losses": sum(t["pnl"] < 0 for t in items),
                        "net_pnl": sum(t["pnl"] for t in items),
                        "fees": sum(t["entry_fee"] + t["exit_fee"] for t in items),
                        "funding": sum(t["funding"] for t in items),
                        "mean_holding_hours": sum(t["exit_time"]-t["entry_time"] for t in items)/len(items)/3600}
                       for name, items in sorted(groups.items())]
    return result


def gates(result, cfg):
    return {
        "at_least_30_closed": result["closed_trades"] >= 30,
        "positive_net": result["net_return_pct"] > 0,
        "positive_double_cost": result["double_cost_return_pct"] > 0,
        "two_positive_blocks": sum(b["return_pct"] > 0 for b in result["time_blocks"]) >= 2,
        "positive_without_best_closed_trade": result["pnl_without_best_closed_trade"] > 0,
    }


def evaluate(cfg, bars, funding):
    scored = [b for b in bars if b.start >= START]
    if bars[0].start != START-WARMUP or bars[-1].end != END:
        raise ValueError("Frozen test data coverage mismatch")
    validate_bars(bars, continuous=True)
    results, streams, checks = [], {}, []
    for name, both, mtf, sweep in VARIANTS:
        orders = []
        for side in ((1, -1) if both else (1,)):
            key = (side, mtf, sweep)
            if key not in streams:
                streams[key] = direction_signals(cfg, bars, side, mtf, sweep, START)
                if any(o["time"] < START for o in streams[key]):
                    raise AssertionError("Warmup order leaked into test")
                if sweep:
                    for cut in (len(bars)//2, len(bars)*3//4):
                        prefix = direction_signals(cfg, bars[:cut], side, mtf, sweep, START)
                        assert prefix == [o for o in streams[key] if o["time"] < bars[cut-1].end]
                        checks.append({"side": side, "cut": iso(bars[cut-1].end), "result": "PASS"})
            orders += streams[key]
        normal = account(cfg, scored, orders, funding)
        stress = account({**cfg, "fee_bps": 2*cfg["fee_bps"], "slippage_bps": 2*cfg["slippage_bps"]},
                         scored, orders, funding)
        blocks = []
        for i in range(3):
            a, b = len(scored)*i//3, len(scored)*(i+1)//3
            beginning = cfg["initial_cash"] if a == 0 else normal["equity"][a-1]["value"]
            blocks.append({"start": iso(scored[a].start), "end": iso(scored[b-1].end),
                           "return_pct": 100*(normal["equity"][b-1]["value"]/beginning-1)})
        best = max([0.0] + [t["pnl"] for t in normal["trades"]])
        item = {"variant": name, **{k: v for k, v in normal.items() if k != "equity"},
                "double_cost_return_pct": stress["net_return_pct"], "time_blocks": blocks,
                "pnl_without_best_closed_trade": normal["equity"][-1]["value"]-cfg["initial_cash"]-best,
                "diagnostics": loss_groups(normal["trades"])}
        item["gates"] = gates(item, cfg)
        item["passes_research_screen"] = all(item["gates"].values())
        results.append(item)
        print(json.dumps({k: item[k] for k in ("variant", "closed_trades", "win_rate_pct", "net_return_pct",
                          "double_cost_return_pct", "passes_research_screen")}), flush=True)
    return results, checks


def main():
    directory = ROOT / "reports" / "experiments" / "experiment-002"
    directory.mkdir(parents=True, exist_ok=True)
    original = ROOT / "reports" / "experiments" / "comparison.json"
    development = json.loads(original.read_text(encoding="utf-8"))
    cfg = development["config"]
    if json.loads((ROOT/"configs"/"crypto.json").read_text(encoding="utf-8")) != cfg:
        raise ValueError("Current configuration differs from experiment 001")
    files = ("priceaction/engine.py", "priceaction/model.py", "priceaction/experiments.py",
             "tools/test_frozen_period.py", "configs/crypto.json", "docs/experiment-002-protocol.md")
    spec = {"start": iso(START), "end": iso(END), "warmup_days": 14, "symbols": SYMBOLS,
            "variants": VARIANTS, "config": cfg, "development_report_sha256": digest(original),
            "source_sha256": {p: digest(ROOT/p) for p in files}}
    # Normalize tuples for stable equality after JSON roundtrips.
    spec = json.loads(json.dumps(spec))
    manifest_path = directory / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["spec"] != spec:
            raise ValueError("Frozen sources or configuration changed; create a new experiment instead")
    else:
        manifest = {"frozen_at": iso(int(time.time())), "spec": spec}
        save_new_or_identical(manifest_path, manifest)
    print(f"Protocol frozen: {manifest['frozen_at']}; verifying development parity first", flush=True)
    dev_start, dev_end = timestamp(development["start"]), timestamp(development["end"])
    if END > dev_start:
        raise AssertionError("Periods overlap")
    diagnoses = []
    for previous in development["results"]:
        symbol = previous["symbol"]
        path = ROOT / "data" / "experiments" / f"{symbol}-{dev_start}-{dev_end}.json"
        saved = json.loads(path.read_text(encoding="utf-8"))
        actual = compare(cfg, [Bar(**b) for b in saved["bars"]], saved["funding"])
        for old, new in zip(previous["variants"], actual):
            for key in ("variant", "closed_trades", "net_return_pct", "double_cost_return_pct"):
                assert old[key] == new[key], (symbol, key, old[key], new[key])
        diagnoses.append({"symbol": symbol, "parity": "PASS", "variants": [
            {"variant": v["variant"], "diagnostics": loss_groups(v["trades"]),
             "worst_three": sorted(v["trades"], key=lambda t: t["pnl"])[:3]} for v in actual]})
        print(f"{symbol}: development parity PASS; diagnostics saved", flush=True)
    save_new_or_identical(directory / "development-diagnostics.json", diagnoses)
    output = {"experiment": "002", "manifest_sha256": digest(manifest_path),
              "validation": "previously uninspected EARLIER historical period; NOT forward test",
              "results": [], "causality_checks": []}
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = {s: pool.submit(futures_data, s, START-WARMUP, END) for s in SYMBOLS}
        for symbol, job in jobs.items():
            bars, funding = job.result()
            print(f"{symbol}: {len(bars)} candles including warmup; {len(funding)} funding records", flush=True)
            variants, checks = evaluate(cfg, bars, funding)
            cache = ROOT/"data"/"experiments"/f"{symbol}-{START-WARMUP}-{END}.json"
            output["results"].append({"symbol": symbol, "data_sha256": digest(cache),
                "test_candles": sum(b.start >= START for b in bars), "variants": variants})
            output["causality_checks"].append({"symbol": symbol, "checks": checks})
    output["screen_survivors_both_symbols"] = [name for name, *_ in VARIANTS if all(
        next(v for v in r["variants"] if v["variant"] == name)["passes_research_screen"] for r in output["results"])]
    save_new_or_identical(directory/"results.json", output)
    print("Saved experiment-002/results.json; survivors: " + str(output["screen_survivors_both_symbols"]), flush=True)


if __name__ == "__main__":
    main()
