import unittest
from priceaction.model import Bar
from tools.review_trades import excursions, select_examples


class TradeReviewTests(unittest.TestCase):
    def test_exit_candle_range_is_not_counted_as_held(self):
        bars=[Bar(0,900,100,102,98,101,1),Bar(900,1800,101,900,1,100,1)]
        trade={'entry_time':0,'exit_time':900,'entry_price':100,'exit_price':101,'side':1}
        result=excursions(trade,bars)
        self.assertEqual(result['mfe_pct'],2)
        self.assertEqual(result['mae_pct'],-2)
        self.assertEqual(result['best_close_pct'],1)

    def test_short_excursions_use_original_prices(self):
        bars=[Bar(0,900,100,102,95,96,1)]
        trade={'entry_time':0,'exit_time':900,'entry_price':100,'exit_price':96,'side':-1}
        result=excursions(trade,bars)
        self.assertEqual(result['mfe_pct'],5)
        self.assertEqual(result['mae_pct'],-2)
        self.assertEqual(result['best_close_pct'],4)

    def test_sample_selection_is_deterministic(self):
        trades=[{'entry_time':i,'pnl':p} for i,p in enumerate((-9,-4,-2,1,6))]
        picks=select_examples(trades)
        self.assertEqual([(label,t['pnl']) for label,t in picks],[('worst',-9),('best',6),('median-loss',-4)])


if __name__=='__main__':
    unittest.main()
