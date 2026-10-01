import unittest

from priceaction.engine import Engine, Zone
from priceaction.exit_research import BosProtectedStructure
from priceaction.model import Bar, config
from priceaction.scenario_research import ScenarioResearchEngine, replay_scenario


def candle(i, close=100, low=99, high=None, seconds=900):
    return Bar(i*seconds, (i+1)*seconds, 100,
               max(101, close) if high is None else high, low, close, 10)


class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.cfg = config('crypto')

    def positioned(self, policy='scenario_only', protected=90):
        e = ScenarioResearchEngine(self.cfg, policy)
        e.pending = {'side': 'buy', 'zone_low': 90, 'signal_price': 100, 'atr': 10,
                     'signal_time': 0, 'model': 'test', 'zone_id': 'test'}
        e.fill(candle(0))
        e.position['protected_low'] = protected
        return e

    def setup_seed(self, e):
        for i in range(10):
            e.setup.push(candle(i, seconds=3600))
        e.setup.high_pivot = (2*3600, 103, 5*3600)
        e.setup.low_pivot = (5*3600, 96, 8*3600)

    def test_15m_close_below_original_boundary_is_not_exit(self):
        for policy in ('scenario_only', 'setup_bos'):
            e = self.positioned(policy)
            e.step(candle(1, 89, 88))
            self.assertIsNone(e.pending)
            self.assertEqual(e.position['protected_low'], 90)

    def test_hourly_wick_and_equal_boundary_close_are_not_exit(self):
        e = self.positioned()
        e.step(candle(3, 90, 88), [candle(0, 90, 88, seconds=3600)])
        self.assertIsNone(e.pending)

    def test_hourly_close_exits_at_next_open_not_final_close(self):
        e = self.positioned()
        e.step(candle(3, 89, 88), [candle(0, 89, 88, seconds=3600)])
        self.assertEqual(e.pending['signal_time'], 3600)
        self.assertEqual(e.trades, [])
        # Gapped open is executable, not the invalidation boundary or signal close.
        e.step(Bar(3600, 4500, 80, 82, 79, 81, 10))
        self.assertEqual(len(e.trades), 1)
        self.assertEqual(e.trades[0]['exit_time'], 3600)
        self.assertAlmostEqual(e.trades[0]['exit_price'], 80*(1-self.cfg['slippage_bps']/10000))

    def test_4h_counter_structure_exits_without_zone_break(self):
        e = self.positioned()
        e.context.push(candle(0, seconds=14400))
        e.context.low_pivot = (0, 99, 14400)
        e.step(candle(31, 98, 97), context_bars=[candle(1, 98, 97, seconds=14400)])
        self.assertEqual(e.events[-1]['action'], 'EXIT_SIGNAL')
        self.assertEqual(e.events[-1]['reason'], '4h karşı yapı onaylandı')

    def test_15m_pivot_never_tightens_scenario_reference(self):
        e = self.positioned()
        for i, low in enumerate((99, 98, 94, 98, 99)):
            e.step(candle(i, low=low))
        self.assertIsNotNone(e.base.new_low)
        self.assertEqual(e.position['protected_low'], 90)

    def test_hourly_bos_tightens_with_evidence(self):
        e = self.positioned('setup_bos')
        self.setup_seed(e)
        e.step(candle(43, 104), [candle(10, 104, seconds=3600)])
        self.assertEqual(e.position['protected_low'], 96)
        update = e.events[-1]['protection_update']
        self.assertEqual(update['frame'], '1h')
        self.assertEqual(update['candidate_low'], (5*3600, 96, 8*3600))
        e.step(candle(44, 95, 94))
        self.assertIsNone(e.pending)
        self.assertNotIn('protection_update', e.events[-1])
        e.step(candle(47, 95, 94), [candle(11, 95, 94, seconds=3600)])
        self.assertEqual(e.events[-1]['reason'], '1h kapanışı BOS teyitli korunan seviyeyi kırdı')

    def test_scenario_only_does_not_trail_hourly_pivot(self):
        e = self.positioned()
        self.setup_seed(e)
        e.step(candle(43, 104), [candle(10, 104, seconds=3600)])
        self.assertEqual(e.position['protected_low'], 90)

    def test_same_close_unknown_and_preentry_pivots_rejected(self):
        for entry_time, known_at in ((6*3600, 8*3600), (0, 11*3600)):
            e = self.positioned('setup_bos')
            self.setup_seed(e)
            e.position['entry_time'] = entry_time
            e.setup.low_pivot = (5*3600, 96, known_at)
            e.step(candle(43, 104), [candle(10, 104, seconds=3600)])
            self.assertEqual(e.position['protected_low'], 90)

    def test_reference_never_loosens(self):
        e = self.positioned('setup_bos', 97)
        self.setup_seed(e)
        e.step(candle(43, 104), [candle(10, 104, seconds=3600)])
        self.assertEqual(e.position['protected_low'], 97)

    def test_exit_has_priority_over_new_protection(self):
        e = self.positioned('setup_bos')
        self.setup_seed(e)
        e.context.trend = -1
        e.step(candle(43, 104), [candle(10, 104, seconds=3600)])
        self.assertEqual(e.events[-1]['action'], 'EXIT_SIGNAL')
        self.assertEqual(e.position['protected_low'], 90)

    def test_rejects_unclosed_stale_and_repeated_higher_candles(self):
        e = self.positioned()
        with self.assertRaises(ValueError):
            e.step(candle(1), [candle(0, seconds=3600)])
        e.step(candle(3), [candle(0, seconds=3600)])
        for i in (3, 4):
            with self.assertRaises(ValueError):
                e.step(candle(i), [candle(0, seconds=3600)])

    def test_entry_selection_and_pending_are_unchanged(self):
        engines = [Engine(self.cfg)] + [ScenarioResearchEngine(self.cfg, p)
                    for p in ('scenario_only', 'setup_bos')]
        for e in engines:
            for i in range(15):
                e.base.push(candle(i))
            e.base.high_pivot = (0, 103, 9000)
            e.context.trend = e.setup.trend = 1
            e.setup.zones.append(Zone('test', 90, 99, 'demand', 0, 3600, 100))
            e.step(candle(15, 104, 97))
            self.assertEqual(e.events[-1]['action'], 'ENTRY_SIGNAL')
        self.assertEqual(engines[0].pending, engines[1].pending)
        self.assertEqual(engines[0].events, engines[2].events)

    def test_invalid_profiles_policies_and_bars(self):
        for cfg, policy in ((config('bist'), 'setup_bos'), (self.cfg, 'unknown')):
            with self.assertRaises(ValueError):
                ScenarioResearchEngine(cfg, policy)
        for bars, side in (([], 1), ([candle(0)], 0),
                           ([candle(0, seconds=3600)], 1), ([candle(0), candle(2)], 1)):
            with self.assertRaises(ValueError):
                replay_scenario(self.cfg, bars, side, 'scenario_only')
        self.assertNotIsInstance(Engine(self.cfg).setup, BosProtectedStructure)


if __name__ == '__main__':
    unittest.main()
