"""Run four predeclared variants on the SAME USD-M futures candles/funding."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from priceaction.experiments import futures_data, compare
from priceaction.model import ROOT, config, fingerprint, iso


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--days',type=int,default=180)
    parser.add_argument('--symbols',nargs='+',default=['BTCUSDT','ETHUSDT'])
    args=parser.parse_args()
    if not 30<=args.days<=365:
        parser.error('days must be 30..365')
    end=int(time.time())//14400*14400
    start=end-args.days*86400
    cfg=config('crypto')
    output={'experiment':'mtf-direction-v1','created_at':iso(int(time.time())), 'start':iso(start),'end':iso(end),
        'market':'Binance USD-M perpetual futures','config':cfg,'config_hash':fingerprint(cfg),
        'validation':'exploratory; no untouched holdout; not a profitability certification',
        'limitations':['close-to-close drawdown','fixed slippage assumption','not a liquidation simulator',
                       'preselected BTC/ETH universe','entry-filter ablation only; exit rules unchanged'],
        'results':[]}
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs={s:pool.submit(futures_data,s,start,end) for s in args.symbols}
        for symbol,job in jobs.items():
            bars,funding=job.result()
            print(f'{symbol}: {len(bars)} candles, {len(funding)} funding records',flush=True)
            variants=compare(cfg,bars,funding)
            output['results'].append({'symbol':symbol,'candles':len(bars),'funding_records':len(funding),'variants':variants})
            for v in variants:
                print(json.dumps({k:v[k] for k in ('variant','closed_trades','win_rate_pct','net_return_pct','max_drawdown_pct','double_cost_return_pct')},ensure_ascii=False),flush=True)
    directory=ROOT/'reports'/'experiments'
    directory.mkdir(parents=True,exist_ok=True)
    (directory/'comparison.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Saved reports/experiments/comparison.json',flush=True)


if __name__=='__main__':
    main()
