"""Offline prefix invariance checks for long/short signals and MTF filtering."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from priceaction.experiments import direction_signals, account
from priceaction.model import ROOT, Bar, timestamp


def main():
    report=json.loads((ROOT/'reports'/'experiments'/'comparison.json').read_text(encoding='utf-8'))
    start,end=timestamp(report['start']),timestamp(report['end'])
    cfg=report['config']
    checks=[]
    for result in report['results']:
        symbol=result['symbol']
        saved=json.loads((ROOT/'data'/'experiments'/f'{symbol}-{start}-{end}.json').read_text(encoding='utf-8'))
        bars=[Bar(**b) for b in saved['bars']]
        for mtf in (False,True):
            for side in (1,-1):
                full=direction_signals(cfg,bars,side,mtf)
                for cut in (len(bars)//2,len(bars)*3//4):
                    prefix=bars[:cut]
                    part=direction_signals(cfg,prefix,side,mtf)
                    assert part==[o for o in full if o['time']<prefix[-1].end], (symbol,side,mtf,cut)
                checks.append({'symbol':symbol,'side':side,'mtf':mtf,'orders':len(full),'prefix_checks':2,'result':'PASS'})
        combined=direction_signals(cfg,bars,1,True)+direction_signals(cfg,bars,-1,True)
        full_account=account(cfg,bars,combined,saved['funding'])
        cut=len(bars)//2
        partial_account=account(cfg,bars[:cut],combined,saved['funding'])
        assert partial_account['equity']==full_account['equity'][:cut], 'Funding/equity history changed'
    (ROOT/'reports'/'experiments'/'validation.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print(json.dumps(checks,indent=2))


if __name__=='__main__':
    main()
