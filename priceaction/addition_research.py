"""Causal research-only zone plans and equal-reference-risk paired trials."""
from collections import Counter
from dataclasses import asdict, replace
from bisect import bisect_left
from statistics import mean

from .engine import Structure
from .experiments import reflect
from .model import aggregate, validate_bars
from .trade_plan import Entry, Target, TradePlan, PlanManager

POLICIES = ('single', 'scale_in', 'half_control')


def pick_levels(setup, context, bar):
    """Return long-space levels known before this candle, never future pivots."""
    if setup.trend != 1 or context.trend != 1:
        return None, 'trend'
    demand = [z for z in setup.zones if z.active and z.known_at <= bar.start
              and z.kind in ('demand', 'breaker') and z.high < bar.close]
    if not demand:
        return None, 'first_zone'
    first = max(demand, key=lambda z: (z.high, z.known_at, z.id))
    below = [z for z in demand if z.high < first.low]
    if not below:
        return None, 'second_zone'
    second = max(below, key=lambda z: (z.high, z.known_at, z.id))
    stops, targets = [], []
    for structure in (setup, context):
        p = structure.low_pivot
        if p and p[2] <= bar.start and p[1] < second.low:
            stops.append({'price':p[1], 'kind':'swing_low', 'frame':structure.name,
                          'source_time':p[0], 'known_at':p[2]})
        p = structure.high_pivot
        if p and p[2] <= bar.start and p[1] > bar.close:
            targets.append({'price':p[1], 'kind':'swing_high', 'frame':structure.name,
                            'source_time':p[0], 'known_at':p[2]})
        for z in structure.zones:
            if not z.active or z.known_at > bar.start:
                continue
            evidence = {'kind':z.kind, 'frame':structure.name, 'zone_id':z.id,
                        'source_time':z.source_time, 'known_at':z.known_at}
            if structure is context and z.kind in ('demand', 'breaker') and z.low < second.low:
                stops.append({'price':z.low, **evidence})
            if z.kind == 'supply' and z.low > bar.close:
                targets.append({'price':z.low, **evidence})
    if not stops:
        return None, 'structural_stop'
    unique = {t['price']:t for t in targets}
    if len(unique) < 2:
        return None, 'two_targets'
    return {'zones':[asdict(first), asdict(second)],
            'stop':max(stops, key=lambda v:v['price']),
            'targets':[unique[p] for p in sorted(unique)[:2]]}, None


def generate_setups(cfg, bars, symbol, trade_start):
    validate_bars(bars, continuous=True)
    if not bars or any(b.end-b.start != 900 or b.start % 900 for b in bars):
        raise ValueError('Continuous aligned 15m data required')
    records, counts = [], Counter()
    anchor = bars[0].open*100
    for side in (1, -1):
        prices = bars if side == 1 else reflect(bars, anchor)
        structures = [Structure(cfg, '1h'), Structure(cfg, '4h')]
        higher = [aggregate(prices, 3600), aggregate(prices, 14400)]
        indices, seen = [0, 0], set()
        for bar in prices:
            for k, structure in enumerate(structures):
                while indices[k] < len(higher[k]) and higher[k][indices[k]].end <= bar.end:
                    structure.push(higher[k][indices[k]])
                    indices[k] += 1
            if bar.end < trade_start:
                continue
            levels, reason = pick_levels(*structures, bar)
            if reason:
                counts[f'{side}:{reason}'] += 1
                continue
            key = tuple(z['id'] for z in levels['zones'])
            if key in seen:
                counts[f'{side}:already_planned'] += 1
                continue
            seen.add(key)
            def actual(p):
                return p if side == 1 else anchor-p
            zones = [sorted((actual(z['low']), actual(z['high']))) for z in levels['zones']]
            records.append({'id':f'{symbol}-{side}-{bar.end}', 'symbol':symbol, 'side':side,
                'created_at':bar.end, 'expires_at':bar.end+cfg['entry_window']*900,
                'zones':zones, 'stop':actual(levels['stop']['price']),
                'targets':[actual(t['price']) for t in levels['targets']],
                'evidence_space':'original' if side == 1 else 'reflected',
                'reflection_anchor':None if side == 1 else anchor, 'evidence':levels})
    return sorted(records, key=lambda r:(r['created_at'], r['side'])), dict(sorted(counts.items()))


def sized_plans(record, cfg):
    side, stop = record['side'], record['stop']
    fee, slip = cfg['fee_bps']/10000, cfg['slippage_bps']/10000
    worst = [z[1] if side == 1 else z[0] for z in record['zones']]
    def costs(raw, multiplier):
        entry = raw*(1+side*slip*multiplier)
        exit_price = stop*(1-side*slip*multiplier)
        risk = side*(entry-exit_price)+(entry+exit_price)*fee*multiplier
        return entry, risk
    units = [costs(p, 1)[1] for p in worst]
    weights = {'single':(1,0), 'scale_in':(.5,.5), 'half_control':(.5,0)}
    # Common R leaves enough headroom for identical quantities at double costs.
    ceiling, notional_cap = 100.0, 1000.0
    limits = [ceiling]
    for policy in ('single', 'scale_in'):
        for multiplier in (1,2):
            # Short's worst loss is at zone LOW, but largest collateral is at HIGH.
            ns = sum(w*costs(z[1],multiplier)[0]/u for w,z,u in zip(weights[policy],record['zones'],units))
            rs = sum(w*costs(p,multiplier)[1]/u for w,p,u in zip(weights[policy],worst,units))
            limits.extend((notional_cap/ns, ceiling/rs))
    common_r = min(limits)*(1-1e-10)
    plans = {}
    for policy in POLICIES:
        entries = tuple(Entry('entry' if i == 0 else 'add', *zone, common_r*w/u)
                        for i,(zone,w,u) in enumerate(zip(record['zones'],weights[policy],units)) if w)
        plans[policy] = TradePlan(record['id']+'-'+policy, record['symbol'], 'crypto_futures',
            side, record['created_at'], record['expires_at'], '15m', '1h', stop, entries,
            tuple(Target(f'tp{i+1}',p,.5) for i,p in enumerate(record['targets'])),
            10000, notional_cap, ceiling, cfg['fee_bps'], cfg['slippage_bps'], 'bos',
            cfg['pivot_left'], cfg['pivot_right'])
    return common_r, plans


def run_plan(plan, bars, funding):
    # Initial incomplete higher bucket is deliberately excluded, as replay_plan.
    stops = aggregate(bars, 3600)
    manager = PlanManager(plan)
    si = fi = 0
    for bar in bars:
        ss, ff = [], []
        while si < len(stops) and stops[si].end <= bar.end:
            ss.append(stops[si]); si += 1
        while fi < len(funding) and funding[fi]['time'] < bar.end:
            ff.append(funding[fi]); fi += 1
        manager.step(bar, ss, ff)
        if manager.state in ('CLOSED', 'CANCELLED'):
            break
    return manager


def outcome(manager, common_r):
    peak, dd = manager.plan.initial_cash, 0.0
    for point in manager.equity:
        peak = max(peak, point['value'])
        dd = max(dd, peak-point['value'])
    r = manager.report()
    return {'state':r['state'], 'entered':bool(manager.entry_time is not None),
        'entry_time':manager.entry_time, 'add_fills':sum(f['action']=='ADD' for f in manager.fills),
        'net_pnl':r['net_pnl'], 'net_r':r['net_pnl']/common_r, 'drawdown_r':dd/common_r,
        'fees':r['fees'], 'funding':r['funding_pnl'], 'remaining_qty':r['remaining_qty'],
        'pending':r['pending'], 'plan':r['plan'], 'plan_hash':r['plan_hash'],
        'fills':manager.fills,
        'decisions':[e for e in manager.events if e['action'] not in ('WATCH','HOLD')],
        'equity_curve':manager.equity}


def evaluate(cfg, bars, funding, symbol, start):
    if not funding:
        raise ValueError('Historical futures funding required')
    times = [f['time'] for f in funding]
    if times != sorted(set(times)):
        raise ValueError('Unordered or duplicate funding')
    setups, rejected = generate_setups(cfg, bars, symbol, start)
    starts = [b.start for b in bars]
    results = []
    for record in setups:
        common_r, plans = sized_plans(record, cfg)
        future = bars[bisect_left(starts, record['created_at']):]
        ff = funding[bisect_left(times, record['created_at']):]
        arms = {}
        for cost in (1,2):
            arms[str(cost)] = {}
            for policy, plan in plans.items():
                p = replace(plan, fee_bps=plan.fee_bps*cost, slippage_bps=plan.slippage_bps*cost)
                arms[str(cost)][policy] = outcome(run_plan(p, future, ff), common_r)
            entries = {v['entry_time'] for v in arms[str(cost)].values()}
            if len(entries) != 1:
                raise AssertionError('Paired first entries diverged')
        results.append({'setup':record, 'common_r':common_r, 'arms':arms})
    return {'setups':results, 'selection_counts_per_bar':rejected}


def verify_prefix(full, partial, cutoff):
    expected = [r for r in full['setups'] if r['setup']['created_at'] <= cutoff]
    if [r['setup'] for r in expected] != [r['setup'] for r in partial['setups']]:
        raise AssertionError('Future data changed generated plans')
    for a,b in zip(expected, partial['setups']):
        if a['common_r'] != b['common_r']:
            raise AssertionError('Future data changed sizing')
        for cost in ('1','2'):
            for policy in POLICIES:
                aa, bb = a['arms'][cost][policy], b['arms'][cost][policy]
                for key in ('fills','decisions','equity_curve'):
                    if aa[key][:len(bb[key])] != bb[key]:
                        raise AssertionError('Future data changed historical '+key)


def summarize(records, cost='1'):
    summaries = {}
    for policy in POLICIES:
        all_items = [r['arms'][cost][policy] for r in records]
        items = [r for r in all_items if r['entered']]
        closed = [r for r in items if r['state']=='CLOSED']
        gains = sum(max(0,r['net_r']) for r in closed)
        losses = -sum(min(0,r['net_r']) for r in closed)
        summaries[policy] = {'plans':len(all_items), 'entered':len(items), 'closed':len(closed),
            'open':sum(r['remaining_qty']>0 for r in items),
            'unfilled':sum(not r['entered'] for r in all_items),
            'cancelled':sum(r['state']=='CANCELLED' for r in all_items),
            'pending':sum(r['pending'] is not None for r in all_items),
            'added_setups':sum(r['add_fills']>0 for r in items),
            'mean_net_r':mean(r['net_r'] for r in items) if items else None,
            'mean_closed_r':mean(r['net_r'] for r in closed) if closed else None,
            'win_rate_pct':100*sum(r['net_pnl']>0 for r in closed)/len(closed) if closed else None,
            'profit_factor_r':gains/losses if losses else None,
            'mean_setup_drawdown_r':mean(r['drawdown_r'] for r in items) if items else None,
            'worst_setup_drawdown_r':max((r['drawdown_r'] for r in items), default=None),
            'worst_setup_net_r':min((r['net_r'] for r in items), default=None),
            'fees_usdt':sum(r['fees'] for r in items), 'funding_usdt':sum(r['funding'] for r in items)}
    pairs = [r for r in records if r['arms'][cost]['single']['entered']]
    def delta(group, comparator):
        values = [r['arms'][cost]['scale_in']['net_r']-r['arms'][cost][comparator]['net_r'] for r in group]
        return {'n':len(values), 'mean_delta_r':mean(values) if values else None,
                'better':sum(v>1e-10 for v in values), 'worse':sum(v< -1e-10 for v in values),
                'equal':sum(abs(v)<=1e-10 for v in values)}
    summaries['paired'] = {group:delta(rs, 'single') for group,rs in (
        ('all',pairs), ('added',[r for r in pairs if r['arms'][cost]['scale_in']['add_fills']]),
        ('not_added',[r for r in pairs if not r['arms'][cost]['scale_in']['add_fills']]))}
    summaries['paired']['vs_half_control'] = delta(pairs, 'half_control')
    return summaries
