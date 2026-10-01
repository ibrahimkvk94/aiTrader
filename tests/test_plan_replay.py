from argparse import Namespace
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from priceaction.model import ROOT
from priceaction.plan_replay import demo_cases, main, run_case


class PlanReplayTests(unittest.TestCase):
    def test_four_demo_scenarios_are_closed_and_causal(self):
        cases = demo_cases()
        self.assertEqual(len(cases), 4)
        for case in cases:
            report = run_case(case)
            self.assertEqual(report['state'], 'CLOSED')
            self.assertEqual(report['execution'], 'DISABLED')
            self.assertEqual(len(report['prefix_checks']), 3)
            self.assertEqual(len(report['input_hash']), 64)
        self.assertLess(run_case(cases[2])['net_pnl'], 0)

    def test_supplied_example_is_hourly_stop_and_no_add_after_tp(self):
        data = json.loads((ROOT/'examples/planned-trade.json').read_text())
        result = run_case(data)
        exits = [e for e in result['events'] if e['action'] == 'EXIT_SIGNAL']
        self.assertEqual(len(exits), 1)
        self.assertEqual(exits[0]['time'], 7200)
        self.assertEqual(result['fills'][-1]['time'], 7200)
        self.assertEqual(result['fills'][-1]['action'], 'EXIT')

    def test_report_reproducible_and_existing_different_report_preserved(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            path = Path(directory)/'report.json'
            args = Namespace(demo=True, input=None, output=path)
            main(args)
            original = path.read_bytes()
            main(args)
            self.assertEqual(path.read_bytes(), original)
            args.demo = False
            args.input = ROOT/'examples/planned-trade.json'
            with self.assertRaisesRegex(ValueError, 'Existing report differs'):
                main(args)
            self.assertEqual(path.read_bytes(), original)

    def test_funding_omission_is_explicit_and_unknown_keys_rejected(self):
        case = demo_cases()[0]
        del case['funding']
        self.assertIn('omitted', run_case(case)['funding_input'])
        case['lookahead'] = True
        with self.assertRaises(ValueError):
            run_case(case)


if __name__ == '__main__':
    unittest.main()
