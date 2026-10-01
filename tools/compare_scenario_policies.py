"""Experiment 004. Offline ablation; preserved inputs, no parameter search."""
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from priceaction.exit_research import POLICIES, orders_from, replay_exit
from priceaction.scenario_research import SCENARIO_POLICIES, replay_scenario
from priceaction.experiments import account
from priceaction.model import ROOT, Bar, iso
from tools.test_frozen_period import loss_groups, save_new_or_identical


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def research_screen(item, baseline):
    return {
        'at_least_30_closed': item['closed_trades'] >= 30,
        'positive_net': item['net_return_pct'] > 0,
        'positive_double_cost': item['double_cost_return_pct'] > 0,
        'positive_without_best_closed_trade': item['pnl_without_best_closed_trade'] > 0,
        'net_not_worse_than_pivot': item['net_return_pct'] >= baseline['net_return_pct'],
        'drawdown_not_worse_than_pivot': item['max_drawdown_pct'] <= baseline['max_drawdown_pct'],
    }


def main():
    root = ROOT/'reports/experiments'
    manifest_paths = [root/f'experiment-{n}/manifest.json' for n in ('002', '003')]
    manifests = [json.loads(p.read_text(encoding='utf-8')) for p in manifest_paths]
    for manifest in manifests:
        for path, expected in manifest['spec']['source_sha256'].items():
            if sha(ROOT/path) != expected:
                raise ValueError(f'Frozen source changed: {path}')
    for path, expected in manifests[-1]['spec']['input_reports'].items():
        if sha(ROOT/path) != expected:
            raise ValueError(f'Frozen input report changed: {path}')
    old_path = root/'experiment-003/results.json'
    old = json.loads(old_path.read_text(encoding='utf-8'))
    if old['manifest_sha256'] != sha(manifest_paths[-1]):
        raise ValueError('Experiment 003 manifest mismatch')
    datasets = []
    for period in manifests[-1]['spec']['periods']:
        for previous in old['results']:
            if previous['period'] != period['id']:
                continue
            path = ROOT/'data/experiments'/f"{previous['symbol']}-{period['start']-period['warmup']}-{period['end']}.json"
            if sha(path) != previous['data_sha256']:
                raise ValueError(f'Frozen candles/funding changed: {path}')
            datasets.append((period, previous, path))
    if len(datasets) != 4:
        raise ValueError('Expected both original periods and BTC/ETH datasets')

    directory = root/'experiment-004'
    directory.mkdir(parents=True, exist_ok=True)
    sources = ('priceaction/engine.py', 'priceaction/model.py', 'priceaction/experiments.py',
               'priceaction/exit_research.py', 'priceaction/scenario_research.py',
               'tools/test_frozen_period.py', 'tools/compare_scenario_policies.py',
               'tests/test_scenario_research.py', 'docs/experiment-004-protocol.md')
    spec = {'policies': list(POLICIES+SCENARIO_POLICIES),
            'validation': 'previously inspected development data; no automatic promotion',
            'source_sha256': {p: sha(ROOT/p) for p in sources},
            'input_sha256': {str(p.relative_to(ROOT)): sha(p)
                             for p in manifest_paths+[old_path]+[d[2] for d in datasets]},
            'periods': manifests[-1]['spec']['periods']}
    manifest_path = directory/'manifest.json'
    if manifest_path.exists():
        if json.loads(manifest_path.read_text(encoding='utf-8'))['spec'] != spec:
            raise ValueError('Frozen experiment 004 changed; refusing overwrite')
    else:
        save_new_or_identical(manifest_path, {'frozen_at': iso(int(time.time())), 'spec': spec})

    output = {'experiment': '004', 'manifest_sha256': sha(manifest_path), 'results': [],
              'prefix_checks': [], 'promoted_to_scanner': False,
              'limitations': ['development only, not holdout', 'independent symbol accounts',
                  'same entry rules, not identical executed entries', 'close-only drawdown',
                  'not a liquidation simulator', 'open PnL excludes future exit costs',
                  'not a reproduction of Kriptotiks rules']}
    for period, previous, path in datasets:
        cfg, start = period['config'], period['start']
        saved = json.loads(path.read_text(encoding='utf-8'))
        bars = [Bar(**b) for b in saved['bars']]
        if bars[0].start != start-period['warmup'] or bars[-1].end != period['end']:
            raise ValueError('Candle coverage mismatch')
        scored = [b for b in bars if b.start >= start]
        policies = []
        for policy in POLICIES+SCENARIO_POLICIES:
            orders, pending, updates = [], [], 0
            replay = replay_exit if policy in POLICIES else replay_scenario
            for side in (1, -1):
                args = (cfg, bars, side, policy, start if period['warmup'] else None)
                engine = replay(*args)
                stream = orders_from(engine, side)
                if any(o['time'] < start for o in stream):
                    raise AssertionError('Warmup order leak')
                orders += stream
                if engine.pending:
                    pending.append({'side': side, 'signal_order': engine.pending})
                updates += sum('protection_update' in e for e in engine.events)
                if policy in SCENARIO_POLICIES:
                    for cut in (len(bars)//2, len(bars)*3//4):
                        partial = replay(cfg, bars[:cut], side, policy, args[-1])
                        if engine.events[:len(partial.events)] != partial.events:
                            raise AssertionError('Historical events changed with future candles')
                        output['prefix_checks'].append({'period': period['id'],
                            'symbol': previous['symbol'], 'policy': policy, 'side': side,
                            'cut': bars[cut-1].end, 'result': 'PASS'})
            normal = account(cfg, scored, orders, saved['funding'])
            stress = account({**cfg, 'fee_bps': cfg['fee_bps']*2,
                              'slippage_bps': cfg['slippage_bps']*2}, scored, orders, saved['funding'])
            if policy in POLICIES:
                reference = next(v for v in previous['policies'] if v['policy'] == policy)
                if any(normal[k] != reference[k] for k in normal if k != 'equity'):
                    raise AssertionError(f'Original result parity failed: {policy}')
                if stress['net_return_pct'] != reference['double_cost_return_pct']:
                    raise AssertionError('Original stress result parity failed')
            trades = normal['trades']
            best = max([0.0]+[t['pnl'] for t in trades])
            item = {'policy': policy, **{k: v for k, v in normal.items() if k != 'equity'},
                'double_cost_return_pct': stress['net_return_pct'],
                'double_cost_drawdown_pct': stress['max_drawdown_pct'],
                'mean_hold_hours': sum(t['exit_time']-t['entry_time'] for t in trades)/3600/len(trades) if trades else None,
                'net_expectancy_usdt': normal['closed_pnl']/len(trades) if trades else None,
                'worst_closed_pnl': min([t['pnl'] for t in trades], default=None),
                'pnl_without_best_closed_trade': normal['equity'][-1]['value']-cfg['initial_cash']-best,
                'diagnostics': loss_groups(trades), 'signal_stream_protection_updates': updates,
                'pending_signal_orders': pending}
            policies.append(item)
            print(json.dumps({'period': period['id'], 'symbol': previous['symbol'],
                **{k: item[k] for k in ('policy', 'closed_trades', 'win_rate_pct', 'net_return_pct',
                    'double_cost_return_pct', 'max_drawdown_pct')}}), flush=True)
        def entries(item):
            positions = item['trades']+([item['open_position']] if item['open_position'] else [])
            return {(p['side'], p['entry_time']) for p in positions}
        baseline = policies[0]
        for item in policies:
            item['shared_entries_with_pivot'] = len(entries(item) & entries(baseline))
            item['executed_entries'] = len(entries(item))
            item['research_screen'] = research_screen(item, baseline)
            item['passes_research_screen'] = all(item['research_screen'].values())
        output['results'].append({'period': period['id'], 'symbol': previous['symbol'],
            'data_sha256': sha(path), 'baseline_parity': 'PASS', 'policies': policies})
    output['candidate_screen'] = {p: all(next(v for v in r['policies'] if v['policy'] == p)
        ['passes_research_screen'] for r in output['results']) for p in SCENARIO_POLICIES}
    save_new_or_identical(directory/'results.json', output)
    print(f"Saved experiment-004/results.json; {len(output['prefix_checks'])} prefix checks PASS", flush=True)


if __name__ == '__main__':
    main()
