from dataclasses import replace
from types import SimpleNamespace
import unittest

from priceaction.addition_research import (pick_levels, sized_plans, run_plan, outcome,
                                         summarize, verify_prefix, generate_setups)
from priceaction.engine import Zone
from priceaction.model import Bar, config


def record(side=1):
    return {'id':'test','symbol':'TESTUSDT','side':side,'created_at':0,'expires_at':7200,
        'zones':[[100,102],[95,97]] if side==1 else [[98,100],[103,105]],
        'stop':90 if side==1 else 110,'targets':[110,120] if side==1 else [90,80]}


def bars():
    pairs = [(101,101),(101,96),(96,110),(112,113),(120,120),(121,121)]
    return [Bar(i*900,(i+1)*900,o,max(o,c)+1,min(o,c)-1,c,10) for i,(o,c) in enumerate(pairs)]


class AdditionResearchTests(unittest.TestCase):
    def test_equal_reference_risk_and_stress_quantities(self):
        for side in (1,-1):
            risk, plans = sized_plans(record(side), config('crypto'))
            for name,p in plans.items():
                actual = sum(p.reference_risk(e.qty,p.entry_price(e.high if side==1 else e.low),p.initial_stop) for e in p.entries)
                self.assertAlmostEqual(actual, risk*(.5 if name=='half_control' else 1))
                stress = replace(p, fee_bps=p.fee_bps*2, slippage_bps=p.slippage_bps*2)
                self.assertEqual(stress.entries,p.entries)
            self.assertEqual(plans['scale_in'].entries[0].qty,plans['half_control'].entries[0].qty)
            self.assertAlmostEqual(plans['single'].entries[0].qty,2*plans['scale_in'].entries[0].qty)

    def test_common_signals_accounting_and_control(self):
        for side in (1,-1):
            risk,plans = sized_plans(record(side),config('crypto'))
            series = bars() if side==1 else [Bar(b.start,b.end,200-b.open,200-b.low,200-b.high,200-b.close,b.volume) for b in bars()]
            results = {k:outcome(run_plan(p,series,[]),risk) for k,p in plans.items()}
            self.assertEqual({r['entry_time'] for r in results.values()},{900})
            self.assertEqual({r['state'] for r in results.values()},{'CLOSED'})
            self.assertEqual(results['scale_in']['add_fills'],1)
            self.assertAlmostEqual(results['single']['net_r'],2*results['half_control']['net_r'])
            summary = summarize([{'arms':{'1':results}}])
            self.assertEqual(summary['scale_in']['closed'],1)
            self.assertEqual(summary['paired']['added']['n'],1)
            self.assertEqual(summary['paired']['not_added']['n'],0)

    def test_no_fill_is_not_a_loss_or_closed_trade(self):
        risk, plans = sized_plans(record(),config('crypto'))
        rows = {k:outcome(run_plan(p,[],[]),risk) for k,p in plans.items()}
        summary = summarize([{'arms':{'1':rows}}])
        self.assertEqual(summary['single']['unfilled'],1)
        self.assertIsNone(summary['single']['win_rate_pct'])
        self.assertIsNone(summary['single']['mean_net_r'])

    def test_known_structural_levels_and_disjoint_order(self):
        def zone(name,lo,hi,kind='demand',known=100):
            return Zone(name,lo,hi,kind,0,known,100)
        setup = SimpleNamespace(name='1h',trend=1,
            zones=[zone('entry',100,102),zone('add',95,97),zone('future',103,104,known=1001)],
            low_pivot=(0,90,100),high_pivot=(0,110,100))
        context = SimpleNamespace(name='4h',trend=1,zones=[],low_pivot=None,high_pivot=(0,120,100))
        levels, reason = pick_levels(setup,context,Bar(1000,1900,105,106,104,105,10))
        self.assertIsNone(reason)
        self.assertEqual([z['id'] for z in levels['zones']],['entry','add'])
        self.assertEqual(levels['stop']['price'],90)
        self.assertEqual([t['price'] for t in levels['targets']],[110,120])
        setup.low_pivot=(0,90,1001)
        self.assertEqual(pick_levels(setup,context,Bar(1000,1900,105,106,104,105,10))[1],'structural_stop')

    def test_prefix_lifecycle_and_detector_reject_changed_history(self):
        risk,plans = sized_plans(record(),config('crypto'))
        def result(series):
            arms = {str(cost):{k:outcome(run_plan(replace(p,fee_bps=p.fee_bps*cost,
                slippage_bps=p.slippage_bps*cost),series,[]),risk) for k,p in plans.items()} for cost in (1,2)}
            return {'setups':[{'setup':record(),'common_r':risk,'arms':arms}]}
        full,partial = result(bars()),result(bars()[:3])
        verify_prefix(full,partial,2700)
        partial['setups'][0]['arms']['1']['single']['fills'][0]['price'] += 1
        with self.assertRaises(AssertionError):
            verify_prefix(full,partial,2700)

    def test_generator_rejects_wrong_base_frame(self):
        with self.assertRaises(ValueError):
            generate_setups(config('crypto'),[Bar(0,3600,100,101,99,100,1)],'TESTUSDT',0)


if __name__ == '__main__':
    unittest.main()
