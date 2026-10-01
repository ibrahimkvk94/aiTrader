"""Offline CLI adapter for immutable, user-specified setup plans."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from .model import ROOT, Bar
from .trade_plan import Entry, Target, TradePlan, VERSION, replay_plan


def register_parser(sub):
    parser = sub.add_parser('plan-replay', help='Offline planned trade management; no live orders')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--input', type=Path, help='JSON with plan, bars, optional stop_bars and funding')
    source.add_argument('--demo', action='store_true', help='Synthetic long, short, gap-stop and BIST scenarios')
    parser.add_argument('--output', type=Path, help='New immutable JSON report; differing existing file is rejected')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def demo_cases():
    """Engineering fixtures, deliberately NOT a profitability benchmark."""
    p = TradePlan('demo-long', 'DEMOUSDT', 'crypto_futures', 1, 0, 86400,
        '15m', '15m', 90,
        (Entry('entry', 100, 102, 1), Entry('add', 95, 97, 1)),
        (Target('tp1', 110, .5), Target('tp2', 120, .5)), 1000, 300, 50,
        protection='bos')
    prices = [(101,101), (101,96), (96,110), (112,113), (120,120), (121,121)]
    bars = [Bar(i*900, (i+1)*900, o, max(o,c)+1, min(o,c)-1, c, 10) for i,(o,c) in enumerate(prices)]
    long = {'plan':asdict(p), 'bars':[asdict(b) for b in bars], 'funding':[]}
    short = {'plan':{**asdict(p), 'id':'demo-short', 'direction':-1, 'initial_stop':110,
        'entries':[asdict(Entry('entry',98,100,1)),asdict(Entry('add',103,105,1))],
        'targets':[asdict(Target('tp1',90,.5)),asdict(Target('tp2',80,.5))]},
        'bars':[asdict(Bar(b.start,b.end,200-b.open,200-b.low,200-b.high,200-b.close,b.volume)) for b in bars],
        'funding':[]}
    stop_bars = bars[:4]+[Bar(3600,4500,113,114,85,88,10), Bar(4500,5400,80,82,79,81,10)]
    gap = {'plan':{**asdict(p), 'id':'demo-gap-stop'}, 'bars':[asdict(b) for b in stop_bars], 'funding':[]}
    bist_bars = [Bar(i*86400, (i+1)*86400,b.open,b.high,b.low,b.close,b.volume) for i,b in zip((0,1,4,5,6,7),bars)]
    bist = {'plan':{**asdict(p), 'id':'demo-bist', 'symbol':'DEMO.IS', 'market':'bist',
        'base_frame':'1d', 'stop_frame':'1d', 'expires_at':10*86400}, 'bars':[asdict(b) for b in bist_bars]}
    return [long, short, gap, bist]


def run_case(bundle):
    allowed = {'plan','bars','stop_bars','funding'}
    if set(bundle)-allowed:
        raise ValueError('Unknown replay input keys: '+str(set(bundle)-allowed))
    plan = TradePlan.from_dict(bundle['plan'])
    bars = [Bar(**b) for b in bundle['bars']]
    stops = [Bar(**b) for b in bundle['stop_bars']] if 'stop_bars' in bundle else None
    funding = bundle.get('funding', [])
    e = replay_plan(plan, bars, stops, funding)
    # Validate historical decisions, fills AND accounting on several prefixes.
    checks = []
    for n in sorted({1, len(bars)//2, len(bars)-1} - {0, len(bars)}):
        end = bars[n-1].end
        ss = [b for b in stops if b.end <= end] if stops is not None else None
        prefix = replay_plan(plan, bars[:n], ss, [f for f in funding if f['time'] < end])
        if (prefix.events != e.events[:len(prefix.events)] or prefix.fills != e.fills[:len(prefix.fills)]
                or prefix.equity != e.equity[:n]):
            raise AssertionError('Future candles rewrote historical replay')
        checks.append({'bar_count':n, 'result':'PASS'})
    report = e.report()
    report['input_hash'] = digest(bundle)
    report['funding_input'] = 'supplied' if 'funding' in bundle else 'omitted (not cost-complete futures performance)'
    report['prefix_checks'] = checks
    return report


def main(args):
    bundles = demo_cases() if args.demo else [json.loads(args.input.read_text(encoding='utf-8-sig'))]
    sources = ['priceaction/trade_plan.py','priceaction/plan_replay.py','priceaction/engine.py',
               'priceaction/model.py','configs/crypto.json','configs/bist.json']
    output = {'version':VERSION, 'synthetic_demo':bool(args.demo), 'execution':'DISABLED',
        'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
        'input_sha256':digest(bundles), 'results':[run_case(b) for b in bundles]}
    # Normalize tuples from frozen dataclasses to their persisted JSON form.
    output = json.loads(json.dumps(output, ensure_ascii=False, allow_nan=False))
    destination = args.output or ROOT/'reports'/'plans'/f'{digest(output)[:20]}.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if json.loads(destination.read_text(encoding='utf-8')) != output:
            raise ValueError('Existing report differs; choose a NEW output file (no overwrite)')
    else:
        with destination.open('x', encoding='utf-8') as handle:
            json.dump(output, handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({'report':str(destination.resolve()), 'synthetic_demo':bool(args.demo),
        'execution':'DISABLED', 'results':[{'id':r['plan']['id'], 'state':r['state'],
            'fills':len(r['fills']), 'net_pnl':r['net_pnl'], 'pending':r['pending'],
            'prefix_checks':len(r['prefix_checks'])} for r in output['results']]}, ensure_ascii=False, indent=2))
