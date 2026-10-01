from dataclasses import asdict, replace, FrozenInstanceError
import copy
import json
import math
import unittest

from priceaction.model import Bar
from priceaction.trade_plan import Entry, Target, TradePlan, PlanManager, replay_plan


def plan(**changes):
    p = TradePlan('test', 'TESTUSDT', 'crypto_futures', 1, 0, 100000,
        '15m', '15m', 90, (Entry('entry', 100, 102, 1), Entry('add', 95, 97, 1)),
        (Target('tp1', 110, .5), Target('tp2', 120, .5)), 1000, 300, 50,
        fee_bps=0, slippage_bps=0, protection='fixed')
    return replace(p, **changes)


def bar(i, close=101, opening=None, low=None, high=None, seconds=900):
    opening = close if opening is None else opening
    return Bar(i*seconds, (i+1)*seconds, opening,
        max(opening, close)+1 if high is None else high,
        min(opening, close)-1 if low is None else low, close, 10)


def mirror(b):
    return Bar(b.start, b.end, 200-b.open, 200-b.low, 200-b.high, 200-b.close, b.volume)


def short_plan(**changes):
    return plan(direction=-1, initial_stop=110,
        entries=(Entry('entry', 98, 100, 1), Entry('add', 103, 105, 1)),
        targets=(Target('tp1', 90, .5), Target('tp2', 80, .5)), **changes)


class PlanValidationTests(unittest.TestCase):
    def test_immutable_roundtrip(self):
        p = plan()
        self.assertEqual(p, TradePlan.from_dict(json.loads(json.dumps(asdict(p)))))
        with self.assertRaises(FrozenInstanceError):
            p.initial_stop = 80
        self.assertNotEqual(p.fingerprint, replace(p, protection='bos').fingerprint)

    def test_rejects_bad_plans(self):
        cases = [dict(direction=0), dict(market='bist', direction=-1),
            dict(market='crypto_spot', direction=-1), dict(initial_stop=96),
            dict(risk_budget=1), dict(max_notional=100), dict(expires_at=0),
            dict(fee_bps=math.nan), dict(slippage_bps=10000), dict(protection='unknown'),
            dict(base_frame='1h', stop_frame='15m'), dict(pivot_right=0),
            dict(entries=(Entry('entry', 100, 102, math.nan),)),
            dict(entries=(Entry('entry', 100, 102, 1), Entry('add', 101, 103, 1))),
            dict(targets=(Target('tp1', 110, .2),)),
            dict(targets=(Target('tp1', 120, .5), Target('tp2', 110, .5))),
            dict(targets=(Target('entry', 110, 1),))]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                plan(**changes)

    def test_all_legs_and_costs_share_one_budget(self):
        # 12 + 7 reference loss, not a separate allowance per addition.
        plan(risk_budget=19)
        with self.assertRaises(ValueError):
            plan(risk_budget=18)
        with self.assertRaises(ValueError):
            plan(risk_budget=19, fee_bps=10, slippage_bps=5)


class LifecycleTests(unittest.TestCase):
    def test_entry_add_partial_final_next_open(self):
        bars = [bar(0), bar(1, 96, 101), bar(2, 110, 96),
                bar(3, 113, 112), bar(4, 120), bar(5, 121)]
        for p, series in ((plan(), bars), (short_plan(), [mirror(b) for b in bars])):
            with self.subTest(direction=p.direction):
                e = replay_plan(p, series)
                self.assertEqual(e.state, 'CLOSED')
                self.assertEqual([f['action'] for f in e.fills], ['ENTRY', 'ADD', 'TP', 'TP'])
                self.assertEqual([f['qty'] for f in e.fills], [1, 1, 1, 1])
                self.assertEqual([f['time'] for f in e.fills], [900, 1800, 2700, 4500])
                self.assertAlmostEqual(e.cash, 1036)
                self.assertAlmostEqual(e.report()['net_pnl'], e.realized_pnl)
                self.assertEqual(e.plan.initial_stop, p.initial_stop)

    def test_target_wick_is_not_target_close(self):
        e = replay_plan(plan(), [bar(0), bar(1, high=125)])
        self.assertIsNone(e.pending)
        self.assertIsNone(e.exit_basis)

    def test_stop_wick_equal_boundary_and_true_break(self):
        for p, flip in ((plan(), lambda x:x), (short_plan(), mirror)):
            e = PlanManager(p)
            for b in [bar(0), bar(1, low=85), bar(2, 90, low=80)]:
                e.step(flip(b))
            self.assertIsNone(e.pending)
            e.step(flip(bar(3, 89)))
            self.assertEqual(e.pending['action'], 'EXIT')
            self.assertEqual(len(e.fills), 1)
            e.step(flip(bar(4, 80)))
            self.assertEqual(e.state, 'CLOSED')
            self.assertAlmostEqual(e.realized_pnl, -21)

    def test_stop_has_priority_over_target_and_add(self):
        e = PlanManager(plan(stop_frame='1h'))
        e.step(bar(0)); e.step(bar(1)); e.step(bar(2))
        # Explicit HTF input tests priority independently of the replay aggregator.
        e.step(bar(3, 120), [Bar(0, 3600, 100, 121, 80, 89, 40)])
        self.assertEqual(e.pending['action'], 'EXIT')
        self.assertIsNone(e.exit_basis)

    def test_hourly_stop_ignores_15m_break(self):
        bars = [bar(0), bar(1, 89, 101), bar(2, 91), bar(3, 92)]
        e = replay_plan(plan(stop_frame='1h'), bars)
        self.assertIsNone(e.pending)
        self.assertEqual(e.state, 'OPEN')
        e = replay_plan(plan(stop_frame='1h'), bars + [bar(4, 89), bar(5, 89), bar(6, 89), bar(7, 89)])
        self.assertEqual(e.pending['action'], 'EXIT')

    def test_preentry_invalidation_and_expiry(self):
        e = replay_plan(plan(), [bar(0, 89), bar(1)])
        self.assertEqual(e.state, 'CANCELLED')
        self.assertFalse(e.fills)
        e = replay_plan(plan(expires_at=900), [bar(0)])
        self.assertEqual(e.state, 'CANCELLED')

    def test_initial_open_gap_does_not_fill(self):
        e = replay_plan(plan(), [bar(0), bar(1, 104)])
        self.assertFalse(e.fills)
        self.assertTrue(any(v['action'] == 'ORDER_CANCELLED' for v in e.events))

    def test_add_gap_and_reference_stop_guard(self):
        e = replay_plan(plan(), [bar(0), bar(1, 96, 101), bar(2, 94)])
        self.assertEqual(len(e.fills), 1)
        self.assertEqual(e.qty, 1)

    def test_pending_add_rechecks_cash_and_risk(self):
        for change in ('cash', 'stop'):
            e = replay_plan(plan(), [bar(0), bar(1, 96, 101)])
            if change == 'cash':
                e.cash = 1
            else:
                e.stop = 96  # a tightened reference excludes the pending leg
            e.step(bar(2, 96))
            self.assertEqual(len(e.fills), 1)

    def test_no_readding_after_tp_and_tp_basis_is_filled_qty(self):
        e = replay_plan(plan(), [bar(0), bar(1, 110, 101), bar(2, 96, 111), bar(3, 96)])
        self.assertEqual([f['action'] for f in e.fills], ['ENTRY', 'TP'])
        self.assertEqual(e.qty, .5)
        self.assertIsNone(e.pending)

    def test_multiple_targets_one_close_do_not_overclose(self):
        e = replay_plan(plan(), [bar(0), bar(1, 121, 101), bar(2, 119)])
        self.assertEqual(e.qty, 0)
        self.assertEqual(e.fills[-1]['qty'], 1)
        self.assertEqual(e.fills[-1]['price'], 119)

    def test_last_signal_is_pending_not_forced_execution(self):
        e = replay_plan(plan(), [bar(0)])
        self.assertFalse(e.fills)
        self.assertEqual(e.pending['action'], 'ENTRY')

    def test_fee_slippage_and_funding_accounting_both_sides(self):
        raw = [bar(0), bar(1, 110, 101), bar(2, 120, 112), bar(3, 121)]
        funding = [{'time':1800, 'mark':110, 'rate':.01}, {'time':1900,'mark':112,'rate':.01}]
        for p, bars in ((plan(fee_bps=10, slippage_bps=5), raw),
                        (short_plan(fee_bps=10, slippage_bps=5), [mirror(b) for b in raw])):
            e = replay_plan(p, bars, funding=funding)
            self.assertEqual(e.state, 'CLOSED')
            self.assertAlmostEqual(e.funding_pnl, -p.direction*(1.1+.56))
            gross = sum(f.get('gross_pnl', 0) for f in e.fills)
            self.assertAlmostEqual(e.cash, p.initial_cash+gross-e.fees+e.funding_pnl)
            self.assertAlmostEqual(e.realized_pnl, e.cash-p.initial_cash)

    def test_invalid_candle_input_is_atomic(self):
        e = replay_plan(plan(stop_frame='1h'), [bar(0)])
        before = copy.deepcopy(e.report())
        with self.assertRaises(ValueError):
            e.step(bar(1), [bar(0, seconds=3600)])
        self.assertEqual(before, e.report())
        for wrong in (bar(0), bar(2)):
            with self.assertRaises(ValueError):
                e.step(wrong)
        with self.assertRaises(ValueError):
            replay_plan(plan(created_at=900), [bar(0)])

    def test_replay_rejects_conflicting_higher_data_and_funding(self):
        bars = [bar(i) for i in range(4)]
        with self.assertRaises(ValueError):
            replay_plan(plan(stop_frame='1h'), bars, [bar(0, 105, seconds=3600)])
        for f in ([{'time':3600,'mark':100,'rate':.01}],
                  [{'time':0,'mark':math.nan,'rate':.01}],
                  [{'time':0,'mark':100,'rate':.01}]*2):
            with self.assertRaises(ValueError):
                replay_plan(plan(), bars, funding=f)

    def test_future_extension_cannot_rewrite_history(self):
        bars = [bar(0), bar(1, 96, 101), bar(2, 110, 96), bar(3, 113, 112), bar(4, 89), bar(5, 85)]
        for p, seq in ((plan(), bars), (short_plan(), [mirror(b) for b in bars])):
            full = replay_plan(p, seq)
            for n in range(1, len(seq)):
                prefix = replay_plan(p, seq[:n])
                self.assertEqual(prefix.events, full.events[:len(prefix.events)])
                self.assertEqual(prefix.fills, full.fills[:len(prefix.fills)])
                self.assertEqual(prefix.equity, full.equity[:n])

    def test_bist_sessions_whole_lots_and_partial_rounding(self):
        p = plan(market='bist', symbol='TEST.IS', base_frame='1d', stop_frame='1d', expires_at=900000)
        bars = [bar(0, seconds=86400), bar(1, 110, 101, seconds=86400),
                bar(4, 120, 111, seconds=86400), bar(5, 121, seconds=86400)]
        e = replay_plan(p, bars)
        self.assertEqual(e.state, 'CLOSED')
        self.assertTrue(any(v['action'] == 'TARGET_SKIPPED' for v in e.events))
        self.assertEqual(e.fills[-1]['qty'], 1)
        with self.assertRaises(ValueError):
            replace(p, entries=(Entry('entry', 100, 102, .5),))
        with self.assertRaises(ValueError):
            replay_plan(replace(p, stop_frame='1w'), bars)


class ProtectionTests(unittest.TestCase):
    def prepared(self, direction=1):
        p = plan(protection='bos') if direction == 1 else short_plan(protection='bos')
        flip = (lambda b:b) if direction == 1 else mirror
        e = replay_plan(p, [flip(bar(0)), flip(bar(1)), flip(bar(2))])
        if direction == 1:
            e.structure.high_pivot, e.structure.low_pivot = (0, 103, 900), (900, 96, 1800)
        else:
            e.structure.low_pivot, e.structure.high_pivot = (0, 97, 900), (900, 104, 1800)
        return e, flip

    def test_bos_tightens_symmetrically_with_audit(self):
        for direction, stop in ((1, 96), (-1, 104)):
            e, flip = self.prepared(direction)
            e.step(flip(bar(3, 104)))
            self.assertEqual(e.stop, stop)
            event = next(v for v in e.events if v['action'] == 'PROTECTION_UPDATED')
            self.assertEqual(event['previous'], e.plan.initial_stop)
            self.assertEqual(event['current'], stop)
            self.assertEqual(event['confirmed_at'], 3600)
            self.assertIsNone(e.pending)
            e.step(flip(bar(4, 95)))
            self.assertEqual(e.pending['action'], 'EXIT')

    def test_no_loosen_unknown_pivot_or_preentry_anchor(self):
        for candidate in ((900, 85, 1800), (900, 96, 3600), (100, 96, 1800)):
            e, _ = self.prepared()
            e.structure.low_pivot = candidate
            e.step(bar(3, 104))
            self.assertEqual(e.stop, 90)


if __name__ == '__main__':
    unittest.main()
