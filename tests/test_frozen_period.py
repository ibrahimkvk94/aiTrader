import json
from pathlib import Path
import tempfile
import unittest

from tools.test_frozen_period import gates, save_new_or_identical


class FrozenPeriodTests(unittest.TestCase):
    def test_positive_return_with_small_sample_does_not_pass(self):
        result = {"closed_trades": 7, "net_return_pct": .25,
                  "double_cost_return_pct": .04, "pnl_without_best_closed_trade": 1,
                  "time_blocks": [{"return_pct": 1}, {"return_pct": 1}, {"return_pct": 0}]}
        self.assertFalse(all(gates(result, {}).values()))
        result["closed_trades"] = 30
        self.assertTrue(all(gates(result, {}).values()))

    def test_single_winner_dependency_does_not_pass(self):
        result = {"closed_trades": 30, "net_return_pct": .25,
                  "double_cost_return_pct": .04, "pnl_without_best_closed_trade": -6,
                  "time_blocks": [{"return_pct": 1}, {"return_pct": 1}, {"return_pct": 0}]}
        self.assertFalse(gates(result, {})["positive_without_best_closed_trade"])

    def test_evidence_cannot_be_silently_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"manifest.json"
            save_new_or_identical(path, {"rule": 1})
            save_new_or_identical(path, {"rule": 1})
            with self.assertRaises(ValueError):
                save_new_or_identical(path, {"rule": 2})
            self.assertEqual(json.loads(path.read_text()), {"rule": 1})


if __name__ == "__main__":
    unittest.main()
