import unittest
from priceaction.engine import Engine, Zone, replay
from priceaction.experiments import account, mtf_filter, reflect, direction_signals
from priceaction.model import Bar, config, aggregate


def b(i, price):
    return Bar(i*900,(i+1)*900,price,price+1,price-1,price,100)


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.cfg={**config('crypto'),'initial_cash':10000,'allocation_fraction':.1,'fee_bps':0,'slippage_bps':0}

    def test_short_profit_uses_original_market_price(self):
        bars=[b(0,100),b(1,90),b(2,80)]
        orders=[{'time':0,'action':'BUY','side':-1,'reason':'entry'},
                {'time':1800,'action':'SELL','side':-1,'reason':'exit'}]
        result=account(self.cfg,bars,orders,[])
        self.assertAlmostEqual(result['closed_pnl'],200)
        self.assertAlmostEqual(result['net_return_pct'],2)
        self.assertEqual(result['short_trades'],1)

    def test_funding_charged_to_existing_position_at_exit_boundary(self):
        bars=[b(0,100),b(1,100),b(2,100)]
        for side,expected in ((1,-10),(-1,10)):
            orders=[{'time':0,'action':'BUY','side':side,'reason':'entry'},
                    {'time':1800,'action':'SELL','side':side,'reason':'exit'}]
            result=account(self.cfg,bars,orders,[{'time':1800,'mark':100,'rate':.01}])
            self.assertAlmostEqual(result['closed_pnl'],expected)
            self.assertAlmostEqual(result['funding_pnl'],expected)

    def test_new_entry_at_funding_boundary_is_not_charged(self):
        orders=[{'time':900,'action':'BUY','side':1,'reason':'entry'}]
        result=account(self.cfg,[b(0,100),b(1,100)],orders,[{'time':900,'mark':100,'rate':.01}])
        self.assertEqual(result['funding_pnl'],0)

    def test_short_costs_are_adverse_both_ways(self):
        cfg={**self.cfg,'fee_bps':10,'slippage_bps':5}
        orders=[{'time':0,'action':'BUY','side':-1,'reason':'entry'},
                {'time':900,'action':'SELL','side':-1,'reason':'exit'}]
        r=account(cfg,[b(0,100),b(1,100)],orders,[])
        trade=r['trades'][0]
        self.assertAlmostEqual(trade['entry_price'],99.95)
        self.assertAlmostEqual(trade['exit_price'],100.05)
        self.assertLess(trade['pnl'],0)

    def test_mtf_requires_known_overlap_and_clearance(self):
        e=Engine(self.cfg)
        zone=Zone('setup',95,98,'demand',0,900,100)
        candle=b(10,100)
        self.assertFalse(mtf_filter(e,candle,zone))
        e.context.zones=[Zone('upper',94,99,'demand',0,900,100)]
        self.assertTrue(mtf_filter(e,candle,zone))
        e.context.zones.append(Zone('obstacle',102,104,'supply',0,900,100))
        self.assertFalse(mtf_filter(e,candle,zone))
        e.context.zones=e.context.zones[:1]
        e.context.zones[0].known_at=candle.end
        self.assertFalse(mtf_filter(e,candle,zone))

    def test_reflection_is_involutive_and_preserves_time(self):
        bars=[b(i,100+i) for i in range(10)]
        self.assertEqual(reflect(reflect(bars,10000),10000),bars)

    def test_long_account_matches_reference_engine_without_funding(self):
        # Exercise source engine entry/exit via deterministic structural seed.
        cfg={**self.cfg,'fee_bps':10,'slippage_bps':5}
        e=Engine(cfg)
        e.pending={'side':'buy','zone_low':95,'signal_price':100,'atr':10,
                   'signal_time':0,'model':'test','zone_id':'test'}
        bars=[b(0,100),b(1,94),b(2,93)]
        for bar in bars:
            e.step(bar)
        orders=[{'time':x['time'],'action':x['action'],'side':1,'reason':x['reason']}
                for x in e.events if x['action'] in {'BUY','SELL'}]
        result=account(cfg,bars,orders,[])
        self.assertAlmostEqual(result['net_return_pct'],e.summary()['net_return_pct'])
        self.assertAlmostEqual(result['closed_pnl'],e.summary()['closed_pnl'])


if __name__=='__main__':
    unittest.main()
