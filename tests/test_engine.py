import json
import math
from pathlib import Path
import random
import tempfile
import unittest
from priceaction.engine import Engine, Structure, Zone, replay
from priceaction.model import Bar, aggregate, config, validate_bars, read_csv
from priceaction.feed import calendar_aggregate
from priceaction.store import Store


def bar(i, o=100, h=102, l=98, c=100):
    return Bar(i * 900, (i + 1) * 900, o, h, l, c, 100)


def series(count=1200):
    rng = random.Random(42)
    result = []
    price = 100
    for i in range(count):
        close = price * (1 + .003 * math.sin(i / 31) + rng.uniform(-.006, .006))
        result.append(bar(i, price, max(price, close) + rng.uniform(.05, .5),
                          min(price, close) - rng.uniform(.05, .5), close))
        price = close
    return result


class CausalityTests(unittest.TestCase):
    def setUp(self):
        self.cfg = config("crypto")

    def test_pivot_only_confirmed_after_right_bars(self):
        s = Structure(self.cfg, "test")
        values = [bar(0), bar(1), bar(2, h=110), bar(3), bar(4)]
        for b in values[:4]:
            s.push(b)
        self.assertIsNone(s.high_pivot)
        s.push(values[4])
        self.assertEqual(s.high_pivot, (1800, 110, 4500))

    def test_full_future_cannot_change_past_decisions(self):
        bars = series()
        full = replay(self.cfg, bars, aggregate(bars, 3600), aggregate(bars, 14400))
        for cut in (399, 700, 999):
            prefix = bars[:cut]
            partial = replay(self.cfg, prefix, aggregate(prefix, 3600), aggregate(prefix, 14400))
            # Array-prefix comparison includes OPEN events at the next timestamp correctly.
            self.assertEqual(full.events[:len(partial.events)], partial.events)
            self.assertEqual(full.equity[:cut], partial.equity)

    def test_incomplete_htf_is_not_published(self):
        self.assertEqual(aggregate(series(3), 3600), [])
        self.assertEqual(len(aggregate(series(4), 3600)), 1)
        self.assertEqual(aggregate(series(5)[1:4], 3600), [])

    def test_higher_frame_future_rejected(self):
        engine = Engine(self.cfg)
        with self.assertRaises(ValueError):
            engine.step(bar(0), [Bar(0, 3600, 100, 102, 98, 100, 100)])

    def test_market_gap_rejected(self):
        with self.assertRaises(ValueError):
            validate_bars([bar(0), bar(2)], continuous=True)

    def test_no_forced_close_at_end(self):
        e = Engine(self.cfg)
        e.pending = {"side": "buy", "zone_low": 90, "signal_price": 100, "atr": 5,
                     "signal_time": 0, "model": "test", "zone_id": "test"}
        e.step(bar(0))
        self.assertIsNotNone(e.position)
        self.assertEqual(e.trades, [])

    def test_wick_does_not_exit_but_close_does(self):
        e = Engine(self.cfg)
        e.pending = {"side": "buy", "zone_low": 95, "signal_price": 100, "atr": 10,
                     "signal_time": 0, "model": "test", "zone_id": "test"}
        e.step(bar(0, l=90, c=100))
        self.assertEqual(e.events[-1]["action"], "HOLD")
        e.step(bar(1, l=90, c=94))
        self.assertEqual(e.events[-1]["action"], "EXIT_SIGNAL")
        self.assertEqual(e.trades, [])
        e.step(bar(2, o=92, h=94, l=91, c=93))
        trade = e.trades[0]
        self.assertEqual(trade["exit_signal_time"], 1800)
        self.assertEqual(trade["exit_time"], 1800)
        self.assertAlmostEqual(trade["exit_price"], 92 * .9995)
        expected = trade["qty"] * (trade["exit_price"] - trade["entry_price"]) - trade["entry_fee"] - trade["exit_fee"]
        self.assertAlmostEqual(trade["pnl"], expected)
        self.assertAlmostEqual(e.cash, self.cfg["initial_cash"] + expected)

    def test_gap_past_invalidation_cancels_entry(self):
        e = Engine(self.cfg)
        e.pending = {"side": "buy", "zone_low": 95, "signal_price": 100, "atr": 10,
                     "signal_time": 0, "model": "test", "zone_id": "test"}
        e.step(bar(0, o=92, h=94, l=90, c=93))
        self.assertIsNone(e.position)
        self.assertEqual(e.events[0]["action"], "CANCEL")

    def test_entry_requires_known_zone_and_fills_next_open(self):
        e = Engine(self.cfg)
        e.context.trend = e.setup.trend = 1
        for i in range(30):
            e.base.push(bar(i, h=101, l=99))
        e.base.high_pivot = (0, 103, 900)
        e.setup.zones = [Zone("test", 96, 99, "demand", 0, 900, 100)]
        e.step(bar(30, o=99, h=105, l=98, c=104))
        self.assertIsNone(e.position)
        self.assertEqual(e.pending["side"], "buy")
        self.assertEqual(e.events[-1]["action"], "ENTRY_SIGNAL")
        e.step(bar(31, o=104, h=106, l=103, c=105))
        self.assertIsNotNone(e.position)
        self.assertEqual(e.position["entry_time"], 31 * 900)
        self.assertAlmostEqual(e.position["entry_price"], 104 * 1.0005)

    def test_future_zone_cannot_trigger_entry(self):
        e = Engine(self.cfg)
        e.context.trend = e.setup.trend = 1
        for i in range(30):
            e.base.push(bar(i, h=101, l=99))
        e.base.high_pivot = (0, 103, 900)
        e.setup.zones = [Zone("future", 96, 99, "demand", 0, 31*900, 100)]
        e.step(bar(30, o=99, h=105, l=98, c=104))
        self.assertIsNone(e.pending)

    def test_protected_structure_only_tightens(self):
        e = Engine(self.cfg)
        e.pending = {"side": "buy", "zone_low": 90, "signal_price": 100, "atr": 5,
                     "signal_time": 0, "model": "test", "zone_id": "test"}
        for i, low in enumerate([98, 97, 94, 97, 98, 97, 92, 97, 98]):
            e.step(bar(i, l=low))
        self.assertEqual(e.position["protected_low"], 94)

    def test_no_nan_or_invalid_ohlc(self):
        with self.assertRaises(ValueError):
            bar(0, c=float("nan"))
        with self.assertRaises(ValueError):
            bar(0, c=110)

    def test_weekly_not_visible_before_calendar_boundary(self):
        # 2026-09-07 Monday UTC; first full week plus next Monday.
        start = 1788739200
        bars = [Bar(start+i*86400+25200, start+(i+1)*86400, 100, 102, 98, 100, 10) for i in range(5)]
        self.assertEqual(calendar_aggregate(bars, "1w", now=start+6*86400), [])
        completed = calendar_aggregate(bars, "1w", now=start+7*86400)
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0].end, start+7*86400)

    def test_persistence_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder)/"test.sqlite3")
            bars = series(30)
            store.save_bars("crypto", "BTCUSDT", "15m", bars)
            store.save_bars("crypto", "BTCUSDT", "15m", bars)
            self.assertEqual(store.load_bars("crypto", "BTCUSDT", "15m"), bars)

    def test_append_only_audit_reconstructs_exact_decisions(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder)/"test.sqlite3")
            e = Engine(self.cfg)
            e.step(bar(0))
            payload = {"config_id": "cfg", "run_id": "first", "last_bar": 900}
            store.publish("first", self.cfg, "BTCUSDT", e, payload)
            e.step(bar(1))
            payload2 = {"config_id": "cfg", "run_id": "second", "last_bar": 1800}
            store.publish("second", self.cfg, "BTCUSDT", e, payload2)
            self.assertEqual(payload2["audit"]["parent_run_id"], "first")
            self.assertEqual(store.run_records("second"), e.events)
            with store.connect() as db:
                self.assertEqual(db.execute("SELECT count(*) FROM decisions").fetchone()[0], 2)
            # Revised historical source data must branch to a fresh full audit.
            e.events[0]["reason"] = "revised"
            payload3 = {"config_id": "cfg", "run_id": "revision", "last_bar": 1800}
            store.publish("revision", self.cfg, "BTCUSDT", e, payload3)
            self.assertIsNone(payload3["audit"]["parent_run_id"])
            self.assertEqual(store.run_records("revision"), e.events)


if __name__ == "__main__":
    unittest.main()
