"""Frozen experiment 005: paired setups, not a portfolio backtest."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from priceaction.addition_research import evaluate, summarize, verify_prefix
from priceaction.model import ROOT, Bar, iso
from tools.test_frozen_period import save_new_or_identical


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    previous_path = ROOT/'reports/experiments/experiment-004/manifest.json'
    previous = json.loads(previous_path.read_text(encoding='utf-8'))
    for group in ('source_sha256', 'input_sha256'):
        for path, expected in previous['spec'][group].items():
            if sha(ROOT/path) != expected:
                raise ValueError('Frozen evidence changed: '+path)
    datasets = []
    for period in previous['spec']['periods']:
        for symbol in ('BTCUSDT','ETHUSDT'):
            path = ROOT/'data/experiments'/f"{symbol}-{period['start']-period['warmup']}-{period['end']}.json"
            saved = json.loads(path.read_text(encoding='utf-8'))
            bars = [Bar(**b) for b in saved['bars']]
            if bars[0].start != period['start']-period['warmup'] or bars[-1].end != period['end']:
                raise ValueError('Wrong coverage')
            funding = saved['funding']
            if (not funding or funding[0]['time']-bars[0].start > 12*3600
                    or bars[-1].end-funding[-1]['time'] > 12*3600
                    or any(b['time']-a['time'] > 12*3600 for a,b in zip(funding,funding[1:]))):
                raise ValueError('Funding coverage gap')
            datasets.append((period, symbol, path, bars, funding))
    sources = ['priceaction/addition_research.py', 'priceaction/trade_plan.py',
        'priceaction/engine.py','priceaction/experiments.py','priceaction/model.py',
        'configs/crypto.json','tools/compare_additions.py','tools/test_frozen_period.py',
        'tests/test_addition_research.py','docs/experiment-005-protocol.md']
    spec = {'periods':previous['spec']['periods'], 'source_sha256':{p:sha(ROOT/p) for p in sources},
        'input_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [previous_path]+[d[2] for d in datasets]},
        'mode':'independent matched setup trials, not portfolio returns',
        'validation':'previously inspected development data; no parameter search'}
    directory = ROOT/'reports/experiments/experiment-005'
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory/'manifest.json'
    if manifest_path.exists():
        if json.loads(manifest_path.read_text(encoding='utf-8'))['spec'] != spec:
            raise ValueError('Experiment 005 changed; refusing overwrite')
    else:
        save_new_or_identical(manifest_path, {'frozen_at':iso(int(time.time())), 'spec':spec})
    output = {'experiment':'005', 'manifest_sha256':sha(manifest_path),
              'execution':'DISABLED', 'promoted_to_scanner':False, 'results':[], 'prefix_checks':[]}
    for period, symbol, path, bars, funding in datasets:
        full = evaluate(period['config'], bars, funding, symbol, period['start'])
        for cut in (len(bars)//2, len(bars)*3//4):
            end = bars[cut-1].end
            partial = evaluate(period['config'], bars[:cut], [f for f in funding if f['time'] < end], symbol, period['start'])
            verify_prefix(full, partial, end)
            output['prefix_checks'].append({'period':period['id'], 'symbol':symbol,
                'cutoff':end, 'paired_plans':len(partial['setups']), 'arms_per_plan':6, 'result':'PASS'})
        summaries = {str(cost):summarize(full['setups'], str(cost)) for cost in (1,2)}
        directions = {str(side):{str(cost):summarize([r for r in full['setups'] if r['setup']['side']==side], str(cost))
                                  for cost in (1,2)} for side in (1,-1)}
        single, scale = summaries['1']['single'], summaries['1']['scale_in']
        screen = {'at_least_30_closed_pairs':min(single['closed'], scale['closed'])>=30,
            'at_least_10_additions':scale['added_setups']>=10,
            'better_normal':summaries['1']['paired']['all']['mean_delta_r'] is not None and summaries['1']['paired']['all']['mean_delta_r']>0,
            'better_stress':summaries['2']['paired']['all']['mean_delta_r'] is not None and summaries['2']['paired']['all']['mean_delta_r']>0,
            'no_worse_mean_setup_drawdown':scale['mean_setup_drawdown_r'] is not None and scale['mean_setup_drawdown_r']<=single['mean_setup_drawdown_r']}
        # JSON roundtrip normalizes dataclass tuples for immutable report reruns.
        cell = json.loads(json.dumps({'period':period['id'], 'symbol':symbol, 'data_sha256':sha(path),
            'summary':summaries, 'directions':directions, 'screen':screen,
            'passes_screen':all(screen.values()), **full}, allow_nan=False))
        evidence_path = directory/f"{period['id']}-{symbol}.json"
        save_new_or_identical(evidence_path, cell)
        compact = {k:v for k,v in cell.items() if k!='setups'}
        compact['evidence_file'] = str(evidence_path.relative_to(ROOT))
        compact['evidence_sha256'] = sha(evidence_path)
        output['results'].append(compact)
        print(json.dumps({'period':period['id'], 'symbol':symbol, 'summary':summaries,
                          'screen':screen}), flush=True)
    output['passes_all_cells'] = all(r['passes_screen'] for r in output['results'])
    save_new_or_identical(directory/'results.json', output)
    print('Saved experiment-005/results.json; eight dataset prefix checks PASS', flush=True)


if __name__ == '__main__':
    main()
