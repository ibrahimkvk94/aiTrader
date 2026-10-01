"""Read-only forensic replay of experiment 002. No strategy or parameter changes.

All-trade diagnostics plus deterministic examples: worst, best, median loss per
symbol in long_short_mtf. Extrema are hindsight diagnostics, NOT achievable exits.
Optional matplotlib is needed only to render PNG charts.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import median
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from priceaction.engine import Engine
from priceaction.experiments import account, reflect, research_filter
from priceaction.model import ROOT, Bar, aggregate, iso, timestamp


def excursions(trade, bars):
    held = [b for b in bars if trade['entry_time'] <= b.start < trade['exit_time']]
    if not held:
        raise ValueError('No held candles')
    entry = trade['entry_price']
    direction = trade['side']
    moves = [direction*(p-entry)/entry*100 for b in held for p in (b.high, b.low)]
    moves += [0, direction*(trade['exit_price']-entry)/entry*100]
    closes = [direction*(b.close-entry)/entry*100 for b in held]
    return {'mfe_pct': max(moves), 'mae_pct': min(moves), 'best_close_pct': max([0]+closes)}


def replay_evidence(cfg, bars, side, mtf, start):
    anchor = bars[0].open*100
    reflected = bars if side == 1 else reflect(bars, anchor)
    unreflect = lambda p: p if side == 1 else anchor-p
    e = Engine({**cfg, 'fee_bps': 0, 'slippage_bps': 0},
               entry_filter=lambda e,b,z: research_filter(e,b,z,mtf,False,start))
    setups, contexts = aggregate(reflected,3600), aggregate(reflected,14400)
    si=ci=0
    signals={}
    for bar in reflected:
        new_s,new_c=[],[]
        while si<len(setups) and setups[si].end<=bar.end:
            new_s.append(setups[si]); si+=1
        while ci<len(contexts) and contexts[ci].end<=bar.end:
            new_c.append(contexts[ci]); ci+=1
        e.step(bar,new_s,new_c)
        if e.pending and e.pending['side']=='buy':
            z=next(z for z in e.setup.zones if z.id==e.pending['zone_id'])
            def convert(zone):
                value=asdict(zone)
                value['low'],value['high']=sorted((unreflect(zone.low),unreflect(zone.high)))
                return value
            signals[bar.end]={
                'zone':convert(z), 'initial_reference':unreflect(z.low),
                'zone_age_hours':(bar.end-z.known_at)/3600,
                'touch_lag_bars':len(e.base.bars)-1-z.touched_at,
                'distance_beyond_zone_atr':(bar.close-z.high)/e.base.atr,
                'atr':e.base.atr,
                'context_zones':[convert(c) for c in e.context.zones if c.active and c.known_at<=bar.start],
            }
    orders=[{'time':v['time'],'action':v['action'],'side':side,'reason':v['reason'],'model':v.get('model')}
            for v in e.events if v['action'] in {'BUY','SELL'}]
    exits={t['entry_time']:t for t in e.trades}
    levels=[{'time':v['time'],'price':unreflect(v['protected_low'])}
            for v in e.events if v['action'] in {'HOLD','EXIT_SIGNAL'}]
    return orders,signals,exits,levels


def diagnose(trade, evidence, bars):
    _,signals,exits,levels=evidence
    signal=signals[trade['entry_time']]
    reference_trade=exits[trade['entry_time']]
    assert reference_trade['exit_time']==trade['exit_time']
    by_start={b.start:b for b in bars}
    side=trade['side']
    raw_entry=by_start[trade['entry_time']].open
    raw_exit=by_start[trade['exit_time']].open
    raw_pnl=side*trade['qty']*(raw_exit-raw_entry)
    filled_pnl=side*trade['qty']*(trade['exit_price']-trade['entry_price'])
    fees=trade['entry_fee']+trade['exit_fee']
    slippage=raw_pnl-filled_pnl
    assert abs(raw_pnl-fees-slippage+trade['funding']-trade['pnl'])<1e-7
    path=[p for p in levels if trade['entry_time']<p['time']<=trade['exit_time']]
    reference=path[-1]['price']
    signal_close=next(b.close for b in bars if b.end==trade['exit_time'])
    return {**trade,**signal,**excursions(trade,bars),
        'entry_iso':iso(trade['entry_time']),'exit_iso':iso(trade['exit_time']),
        'raw_open_pnl':raw_pnl,'fees':fees,'slippage_cost':slippage,
        'cost_flipped_winner':raw_pnl>0 and trade['pnl']<0,
        'protected_path':[{'time':trade['entry_time'],'price':signal['initial_reference']}]+path,
        'reference_tightened':side*(reference-signal['initial_reference'])>1e-7,
        'initial_zone_survives_exit_close':side*(signal_close-signal['initial_reference'])>=0,
        'hold_hours':(trade['exit_time']-trade['entry_time'])/3600}


def summarize(trades):
    losses=[t for t in trades if t['pnl']<0]
    return {'trades':len(trades),'losses':len(losses),
        'net_pnl':sum(t['pnl'] for t in trades),'raw_open_pnl':sum(t['raw_open_pnl'] for t in trades),
        'fees':sum(t['fees'] for t in trades),'slippage':sum(t['slippage_cost'] for t in trades),
        'funding':sum(t['funding'] for t in trades),
        'cost_flipped_winners':sum(t['cost_flipped_winner'] for t in trades),
        'tightened_exits':sum(t['reference_tightened'] for t in trades),
        'tightened_exits_initial_zone_survived':sum(t['reference_tightened'] and t['initial_zone_survives_exit_close'] for t in trades),
        'losers_with_positive_close':sum(t['best_close_pct']>0 for t in losses),
        'median_loss_mfe_pct':median(t['mfe_pct'] for t in losses) if losses else None,
        'median_loss_best_close_pct':median(t['best_close_pct'] for t in losses) if losses else None,
        'median_zone_age_hours':median(t['zone_age_hours'] for t in trades) if trades else None,
        'median_entry_distance_atr':median(t['distance_beyond_zone_atr'] for t in trades) if trades else None}


def select_examples(trades):
    # Selection intentionally descriptive, not representative random sampling.
    ordered=sorted(trades,key=lambda t:(t['pnl'],t['entry_time']))
    losses=[t for t in ordered if t['pnl']<0]
    picks=[('worst',ordered[0]),('best',ordered[-1])]
    if losses:
        picks.append(('median-loss',losses[len(losses)//2]))
    return picks


def plot_trade(symbol,label,t,bars,directory):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as md
    from matplotlib.patches import Rectangle
    dt=lambda x:datetime.fromtimestamp(x,timezone.utc)
    fig,axes=plt.subplots(2,1,figsize=(13,9),layout='constrained')
    for ax,seconds,prior,after in ((axes[0],900,12*900,8*900),(axes[1],3600,48*3600,8*3600)):
        series=bars if seconds==900 else aggregate(bars,seconds)
        chosen=[b for b in series if t['entry_time']-prior<=b.start<=t['exit_time']+after]
        for b in chosen:
            x=md.date2num(dt(b.start)); width=seconds/86400*.7
            color='#237c63' if b.close>=b.open else '#ae4554'
            ax.vlines(x,b.low,b.high,color=color,lw=.9)
            ax.add_patch(Rectangle((x-width/2,min(b.open,b.close)),width,max(abs(b.close-b.open),.000001),
                                   facecolor=color,edgecolor=color,lw=.6))
        zone=t['zone']
        ax.fill_between([dt(max(zone['known_at'],chosen[0].start)),dt(chosen[-1].end)],
                        zone['low'],zone['high'],color='#617fc2',alpha=.17,label='1h giriş bölgesi (sinyalde)')
        # Only HTF zones overlapping the selected setup zone, and already known at entry.
        labeled_context=False
        for z in t['context_zones']:
            if z['kind'] in {'demand','breaker'} and max(z['low'],zone['low'])<=min(z['high'],zone['high']):
                ax.fill_between([dt(max(z['known_at'],chosen[0].start)),dt(chosen[-1].end)],
                                z['low'],z['high'],color='#9b7bb5',alpha=.10,
                                label='4h örtüşen bölge (sinyalde)' if not labeled_context else None)
                labeled_context=True
        path=t['protected_path']
        ax.step([dt(p['time']) for p in path],[p['price'] for p in path],where='post',
                color='#c18220',lw=1.6,label='Korunan referans (kapanış sonrası)')
        ax.scatter([dt(t['entry_time'])],[t['entry_price']],marker='>',s=80,color='#2253a0',label='Giriş açılışı',zorder=5)
        ax.scatter([dt(t['exit_time'])],[t['exit_price']],marker='X',s=65,color='#a3334b',label='Çıkış açılışı',zorder=5)
        ax.axvspan(dt(t['exit_time']),dt(chosen[-1].end),color='grey',alpha=.07)
        ax.set_xlim(dt(chosen[0].start-seconds),dt(chosen[-1].end))
        # Keep all candle prices and relevant setup/reference levels visible.
        prices=[p for b in chosen for p in (b.low,b.high)]+[zone['low'],zone['high']]+[p['price'] for p in path]
        lo,hi=min(prices),max(prices); pad=(hi-lo)*.08
        ax.set_ylim(lo-pad,hi+pad)
        ax.set_ylabel('Fiyat (USDT)')
        ax.set_title('15 dakika — giriş/çıkış ayrıntısı' if seconds==900 else '1 saat — bölge bağlamı',loc='left')
        ax.xaxis.set_major_locator(md.AutoDateLocator(minticks=4,maxticks=7))
        ax.xaxis.set_major_formatter(md.DateFormatter('%d %b\n%H:%M',tz=timezone.utc))
        ax.grid(alpha=.15)
    axes[0].legend(loc='best',fontsize=9,ncol=2)
    axes[1].set_xlabel('UTC • Gri alan: çıkış sonrası, performans hesabı dışında')
    side='LONG' if t['side']==1 else 'SHORT'
    fig.suptitle(f"{symbol} {side} | {label} | {t['entry_iso'][:16]}\n"
                 f"Net {t['pnl']:+.2f} USDT · MFE %{t['mfe_pct']:.2f} · MAE %{t['mae_pct']:.2f}",fontsize=14)
    path=directory/f'{symbol.lower()}-{label}.png'
    fig.savefig(path,dpi=130)
    plt.close(fig)
    return path.name


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--charts',action='store_true')
    args=parser.parse_args()
    source=ROOT/'reports/experiments/experiment-002'
    result=json.loads((source/'results.json').read_text(encoding='utf-8'))
    manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    cfg=manifest['spec']['config']
    start,end=timestamp(manifest['spec']['start']),timestamp(manifest['spec']['end'])
    directory=ROOT/'reports/trade-review'
    directory.mkdir(parents=True,exist_ok=True)
    output={'source_results_sha256':hashlib.sha256((source/'results.json').read_bytes()).hexdigest(),
            'scope':'experiment-002; retrospective diagnosis only; no new performance test',
            'selection':'per symbol long_short_mtf: worst, best, upper median loss by net PnL',
            'results':[],'examples':[]}
    for symbol_result in result['results']:
        symbol=symbol_result['symbol']
        cache=ROOT/'data/experiments'/f'{symbol}-{start-14*86400}-{end}.json'
        assert hashlib.sha256(cache.read_bytes()).hexdigest()==symbol_result['data_sha256']
        saved=json.loads(cache.read_text(encoding='utf-8'))
        bars=[Bar(**b) for b in saved['bars']]
        for mtf in (False,True):
            variant='long_short_mtf' if mtf else 'long_short_baseline'
            expected=next(v for v in symbol_result['variants'] if v['variant']==variant)
            evidence={side:replay_evidence(cfg,bars,side,mtf,start) for side in (1,-1)}
            actual=account(cfg,[b for b in bars if b.start>=start],evidence[1][0]+evidence[-1][0],saved['funding'])
            assert actual['trades']==expected['trades'] and actual['net_return_pct']==expected['net_return_pct']
            trades=[diagnose(t,evidence[t['side']],bars) for t in actual['trades']]
            summary=summarize(trades)
            output['results'].append({'symbol':symbol,'variant':variant,'parity':'PASS','summary':summary,'trades':trades})
            print(json.dumps({'symbol':symbol,'variant':variant,**summary}),flush=True)
            if mtf:
                for label,trade in select_examples(trades):
                    example={'symbol':symbol,'label':label,'trade':trade}
                    if args.charts:
                        example['chart']=plot_trade(symbol,label,trade,bars,directory)
                    output['examples'].append(example)
    (directory/'review.json').write_text(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print('Saved reports/trade-review/review.json',flush=True)


if __name__=='__main__':
    main()
