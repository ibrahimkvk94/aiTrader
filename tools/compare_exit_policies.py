"""Experiment 003: exit-rule ablation on two already inspected periods."""
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from priceaction.exit_research import POLICIES, replay_exit, orders_from
from priceaction.experiments import account
from priceaction.model import ROOT, Bar, iso, timestamp
from tools.test_frozen_period import save_new_or_identical


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root=ROOT/'reports/experiments'
    old_manifest=json.loads((root/'experiment-002/manifest.json').read_text(encoding='utf-8'))
    for path,expected in old_manifest['spec']['source_sha256'].items():
        if sha(ROOT/path)!=expected:
            raise ValueError(f'Frozen experiment 002 source changed: {path}')
    first_path=root/'comparison.json'
    second_path=root/'experiment-002/results.json'
    first=json.loads(first_path.read_text(encoding='utf-8'))
    second=json.loads(second_path.read_text(encoding='utf-8'))
    periods=[('001',first,first['config'],timestamp(first['start']),timestamp(first['end']),0),
             ('002',second,old_manifest['spec']['config'],timestamp(old_manifest['spec']['start']),
              timestamp(old_manifest['spec']['end']),14*86400)]
    directory=root/'experiment-003'
    directory.mkdir(parents=True,exist_ok=True)
    files=('priceaction/engine.py','priceaction/model.py','priceaction/experiments.py',
           'priceaction/exit_research.py','tools/compare_exit_policies.py','tools/test_frozen_period.py',
           'docs/experiment-003-protocol.md')
    spec={'policies':list(POLICIES),'entry_model':'long_short_mtf','validation':'development only; both periods inspected',
          'source_sha256':{p:sha(ROOT/p) for p in files},
          'input_reports':{str(p.relative_to(ROOT)):sha(p) for p in (first_path,second_path)},
          'periods':[{'id':p,'config':cfg,'start':start,'end':end,'warmup':warmup}
                     for p,_,cfg,start,end,warmup in periods]}
    manifest_path=directory/'manifest.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest['spec']!=spec:
            raise ValueError('Frozen experiment 003 changed; refusing overwrite')
    else:
        save_new_or_identical(manifest_path,{'frozen_at':iso(int(time.time())),'spec':spec})
    output={'experiment':'003','manifest_sha256':sha(manifest_path),'results':[],'prefix_checks':[],
            'limitations':['development periods, not holdout','same entry rules, not identical executed entries',
                           'independent symbol accounts','close-only drawdown','fixed cost assumptions',
                           'not an exchange liquidation simulator'],'promoted_to_scanner':False}
    for period,old,cfg,start,end,warmup in periods:
        for previous in old['results']:
            symbol=previous['symbol']
            path=ROOT/'data/experiments'/f'{symbol}-{start-warmup}-{end}.json'
            saved=json.loads(path.read_text(encoding='utf-8'))
            if period=='002' and sha(path)!=previous['data_sha256']:
                raise ValueError('Historical cache changed')
            bars=[Bar(**b) for b in saved['bars']]
            scored=[b for b in bars if b.start>=start]
            expected=next(v for v in previous['variants'] if v['variant']=='long_short_mtf')
            outputs=[]
            for policy in POLICIES:
                orders=[]
                updates=0
                for side in (1,-1):
                    engine=replay_exit(cfg,bars,side,policy,start if warmup else None)
                    side_orders=orders_from(engine,side)
                    if any(o['time']<start for o in side_orders):
                        raise AssertionError('Warmup order leak')
                    orders+=side_orders
                    updates+=sum('protection_update' in e for e in engine.events)
                    if policy=='bos_confirmed':
                        # Events (including protection evidence), not just completed fills.
                        for cut in (len(bars)//2,len(bars)*3//4):
                            partial=replay_exit(cfg,bars[:cut],side,policy,start if warmup else None)
                            assert engine.events[:len(partial.events)]==partial.events
                            output['prefix_checks'].append({'period':period,'symbol':symbol,'side':side,
                                'cut':bars[cut-1].end,'result':'PASS'})
                normal=account(cfg,scored,orders,saved['funding'])
                stress=account({**cfg,'fee_bps':cfg['fee_bps']*2,'slippage_bps':cfg['slippage_bps']*2},
                               scored,orders,saved['funding'])
                if policy=='pivot':
                    for key in ('closed_trades','win_rate_pct','net_return_pct','max_drawdown_pct'):
                        assert normal[key]==expected[key],(period,symbol,key)
                    assert stress['net_return_pct']==expected['double_cost_return_pct']
                item={'policy':policy,**{k:v for k,v in normal.items() if k!='equity'},
                      'double_cost_return_pct':stress['net_return_pct'],
                      'mean_hold_hours':sum(t['exit_time']-t['entry_time'] for t in normal['trades'])/3600/len(normal['trades']) if normal['trades'] else None,
                      'worst_closed_pnl':min([t['pnl'] for t in normal['trades']],default=None),
                      'signal_stream_protection_updates':updates if policy=='bos_confirmed' else None}
                outputs.append(item)
                print(json.dumps({'period':period,'symbol':symbol,**{k:item[k] for k in (
                    'policy','closed_trades','win_rate_pct','net_return_pct','double_cost_return_pct',
                    'max_drawdown_pct','mean_hold_hours')}}),flush=True)
            def entry_keys(item):
                positions=item['trades']+([item['open_position']] if item['open_position'] else [])
                return {(t['side'],t['entry_time']) for t in positions}
            left,right=entry_keys(outputs[0]),entry_keys(outputs[1])
            output['results'].append({'period':period,'symbol':symbol,'data_sha256':sha(path),
                'baseline_parity':'PASS','policies':outputs,'shared_executed_entries':len(left&right),
                'old_executed_entries':len(left),'new_executed_entries':len(right)})
    save_new_or_identical(directory/'results.json',output)
    print(f"Saved experiment-003/results.json; {len(output['prefix_checks'])} prefix checks PASS",flush=True)


if __name__=='__main__':
    main()
