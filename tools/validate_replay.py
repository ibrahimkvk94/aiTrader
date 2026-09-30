"""Offline integration checks against downloaded data. Run after `run.py scan`."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from priceaction.engine import replay
from priceaction.model import ROOT, aggregate, config
from priceaction.store import Store


def main():
    cfg, store = config("crypto"), Store()
    checks = []
    for symbol in ("BTCUSDT", "ETHUSDT"):
        bars = store.load_bars("crypto", symbol, "15m")
        if len(bars) < 1000:
            raise SystemExit("Download at least 1,000 candles before integration validation")
        full = replay(cfg, bars, aggregate(bars, 3600), aggregate(bars, 14400))
        assert full.trades, "Integration fixture should exercise real entry/exit decisions"
        for cut in (len(bars)//2, len(bars)*3//4, len(bars)-17):
            prefix = bars[:cut]
            partial = replay(cfg, prefix, aggregate(prefix, 3600), aggregate(prefix, 14400))
            assert partial.events == full.events[:len(partial.events)], f"Changed historical decisions: {symbol} at {cut}"
            assert partial.equity == full.equity[:cut], f"Changed historical equity: {symbol} at {cut}"
        assert all(t["exit_time"] >= t["exit_signal_time"] and t["entry_time"] >= t["entry_signal_time"] for t in full.trades)
        stress_cfg = {**cfg, "fee_bps": cfg["fee_bps"] * 2, "slippage_bps": cfg["slippage_bps"] * 2}
        stress = replay(stress_cfg, bars, aggregate(bars, 3600), aggregate(bars, 14400))
        checks.append({"symbol": symbol, "candles": len(bars), "closed_trades_exercised": len(full.trades),
                       "prefix_checks": 3, "causality_result": "PASS",
                       "base_net_return_pct": full.summary()["net_return_pct"],
                       "double_cost_net_return_pct": stress.summary()["net_return_pct"],
                       "profitability_validated": False})
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "validation.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
