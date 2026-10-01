import unittest
from priceaction.engine import Engine
from priceaction.exit_research import BosProtectedStructure, ExitResearchEngine, replay_exit, orders_from
from priceaction.experiments import direction_signals
from priceaction.model import Bar, config


def bar(i,close=100,low=99,high=None):
    return Bar(i*900,(i+1)*900,100,max(101,close) if high is None else high,low,close,10)


class ExitPolicyTests(unittest.TestCase):
    def setUp(self):
        self.cfg=config('crypto')

    def seeded(self):
        s=BosProtectedStructure(self.cfg,'base')
        for i in range(10):
            s.push(bar(i))
        s.high_pivot=(1800,103,4500)
        s.low_pivot=(4500,96,7200)
        return s

    def test_new_break_uses_preknown_pullback_low(self):
        s=self.seeded()
        self.assertTrue(s.push(bar(10,104))['bull'])
        self.assertEqual(s.new_low,(4500,96,7200))

    def test_pivot_without_break_does_not_tighten(self):
        s=self.seeded()
        s.push(bar(10,102))
        self.assertIsNone(s.new_low)

    def test_low_confirmed_at_break_close_is_not_eligible(self):
        s=self.seeded()
        s.low_pivot=(7200,96,9900)
        s.push(bar(10,104))
        self.assertIsNone(s.new_low)

    def test_low_before_broken_high_is_not_eligible(self):
        s=self.seeded()
        s.low_pivot=(900,96,3600)
        s.push(bar(10,104))
        self.assertIsNone(s.new_low)

    def test_same_break_cannot_be_used_again(self):
        s=self.seeded()
        s.push(bar(10,104))
        s.push(bar(11,102))
        s.push(bar(12,104))
        self.assertIsNone(s.new_low)

    def positioned(self,protected=90,entry_time=0):
        e=ExitResearchEngine(self.cfg,'bos_confirmed')
        e.pending={'side':'buy','zone_low':90,'signal_price':100,'atr':10,
                   'signal_time':0,'model':'test','zone_id':'test'}
        e.fill(bar(0))
        e.base=self.seeded()
        e.position['entry_time']=entry_time
        e.position['protected_low']=protected
        return e

    def test_engine_tightens_and_logs_bos_evidence(self):
        e=self.positioned()
        e.step(bar(10,104))
        self.assertEqual(e.position['protected_low'],96)
        self.assertEqual(e.events[-1]['protection_update']['broken_high'],(1800,103,4500))

    def test_reference_never_loosens_and_preentry_pivot_rejected(self):
        for protected,entry_time in ((97,0),(90,5400)):
            e=self.positioned(protected,entry_time)
            e.step(bar(10,104))
            self.assertEqual(e.position['protected_low'],protected)

    def test_higher_frame_exit_has_priority_over_tightening(self):
        e=self.positioned()
        e.context.trend=-1
        e.step(bar(10,104))
        self.assertEqual(e.events[-1]['action'],'EXIT_SIGNAL')
        self.assertEqual(e.position['protected_low'],90)

    def test_wick_is_not_exit_and_fill_is_next_open(self):
        e=self.positioned(96)
        e.step(bar(10,100,low=94))
        self.assertIsNone(e.pending)
        e.step(bar(11,95,low=94))
        self.assertEqual(e.pending['side'],'sell')
        self.assertEqual(e.trades,[])
        e.step(bar(12,100))
        self.assertEqual(e.trades[0]['exit_time'],10800)

    def test_default_engine_not_replaced(self):
        self.assertEqual(type(Engine(self.cfg).base).__name__,'Structure')
        with self.assertRaises(ValueError):
            ExitResearchEngine(self.cfg,'unknown')

    def test_pivot_adapter_matches_original_long_and_short(self):
        bars=[bar(i,100+(i%7)*.1) for i in range(96)]
        for side in (1,-1):
            e=replay_exit(self.cfg,bars,side,'pivot')
            self.assertEqual(orders_from(e,side),direction_signals(self.cfg,bars,side,True))


if __name__=='__main__':
    unittest.main()
