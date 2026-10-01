"""Versioned, offline setup lifecycle. No broker, leverage or order API.

All decisions use closed candles, all simulated fills use the next available
open. The original plan never changes. A separate protection reference can
only tighten after a confirmed break of structure (BOS).
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import math

from .engine import Structure
from .model import DURATIONS, aggregate, config, symbol_name, validate_bars

VERSION = "planned-lifecycle-v1"


def positive(*values):
    return all(not isinstance(v, bool) and math.isfinite(v) and v > 0 for v in values)


@dataclass(frozen=True)
class Entry:
    id: str
    low: float
    high: float
    qty: float


@dataclass(frozen=True)
class Target:
    id: str
    price: float
    fraction: float


@dataclass(frozen=True)
class TradePlan:
    id: str
    symbol: str
    market: str                 # crypto_futures, crypto_spot, bist
    direction: int              # +1 long, -1 short (futures only)
    created_at: int             # when ALL initial levels were available
    expires_at: int             # last permissible initial fill; exclusive
    base_frame: str
    stop_frame: str
    initial_stop: float
    entries: tuple[Entry, ...]
    targets: tuple[Target, ...]
    initial_cash: float
    max_notional: float         # lifetime entry notional; profit not recycled
    risk_budget: float          # reference-price risk, NOT maximum actual loss
    fee_bps: float = 10
    slippage_bps: float = 5
    protection: str = "bos"     # fixed or BOS-confirmed tightening
    pivot_left: int = 2
    pivot_right: int = 2

    def __post_init__(self):
        object.__setattr__(self, 'entries', tuple(self.entries))
        object.__setattr__(self, 'targets', tuple(self.targets))
        if not self.id or symbol_name(self.symbol) != self.symbol:
            raise ValueError('Plan id and uppercase symbol required')
        if self.market not in ('crypto_futures', 'crypto_spot', 'bist'):
            raise ValueError('Unknown market')
        if self.direction not in (-1, 1) or isinstance(self.direction, bool):
            raise ValueError('Direction must be +1 or -1')
        if self.direction == -1 and self.market != 'crypto_futures':
            raise ValueError('Shorts are research-only crypto futures')
        if any(type(v) is not int or v < 0 for v in (self.created_at, self.expires_at)) or self.expires_at <= self.created_at:
            raise ValueError('Invalid plan availability/expiry')
        if self.market == 'bist':
            if self.base_frame != '1d' or self.stop_frame not in ('1d', '1w', '1mo'):
                raise ValueError('BIST requires daily base and daily/weekly/monthly stop candles')
        elif (self.base_frame not in DURATIONS or self.stop_frame not in DURATIONS
              or DURATIONS[self.stop_frame] % DURATIONS[self.base_frame]):
            raise ValueError('Stop frame must be an integer multiple of base frame')
        if self.protection not in ('fixed', 'bos') or any(type(v) is not int or v < 1 for v in (self.pivot_left, self.pivot_right)):
            raise ValueError('Invalid protection policy/pivots')
        if not positive(self.initial_stop, self.initial_cash, self.max_notional, self.risk_budget):
            raise ValueError('Positive finite price and budgets required')
        if any(not math.isfinite(v) or not 0 <= v < 10000 for v in (self.fee_bps, self.slippage_bps)):
            raise ValueError('Invalid costs')
        if self.risk_budget > self.initial_cash or self.max_notional*(1+self.fee_bps/10000) > self.initial_cash:
            raise ValueError('Budgets cannot borrow capital')
        if not self.entries or not self.targets:
            raise ValueError('At least one entry and target required')
        ids = [v.id for v in (*self.entries, *self.targets)]
        if any(not isinstance(v, str) or not v for v in ids) or len(ids) != len(set(ids)):
            raise ValueError('Level IDs must be unique')
        for e in self.entries:
            if not positive(e.low, e.high, e.qty) or e.low > e.high:
                raise ValueError('Invalid entry zone or quantity')
            if self.market == 'bist' and e.qty != int(e.qty):
                raise ValueError('BIST quantities must be whole lots')
            if not (self.initial_stop < e.low if self.direction == 1 else self.initial_stop > e.high):
                raise ValueError('Initial stop must be beyond every entry zone')
        for a, b in zip(self.entries, self.entries[1:]):
            if not (b.high < a.low if self.direction == 1 else b.low > a.high):
                raise ValueError('Addition zones must be disjoint, ordered adversely')
        for t in self.targets:
            if not positive(t.price, t.fraction) or t.fraction > 1:
                raise ValueError('Invalid target')
            if not all(t.price > e.high if self.direction == 1 else t.price < e.low for e in self.entries):
                raise ValueError('Targets must be beyond all entry zones in profit direction')
        if not math.isclose(sum(t.fraction for t in self.targets), 1, abs_tol=1e-9):
            raise ValueError('Target fractions must total one')
        if any(self.direction*(b.price-a.price) <= 0 for a, b in zip(self.targets, self.targets[1:])):
            raise ValueError('Targets must be ordered in profit direction')
        # Worst allowed entry fills include adverse slippage; stop execution
        # here is only a reference for sizing, never a guaranteed fill price.
        prices = [self.entry_price(e.high if self.direction == 1 else e.low) for e in self.entries]
        planned_notional = sum(e.qty*p for e, p in zip(self.entries, prices))
        planned_risk = sum(self.reference_risk(e.qty, p, self.initial_stop) for e, p in zip(self.entries, prices))
        if not math.isfinite(planned_notional+planned_risk) or planned_notional > self.max_notional+1e-9 or planned_risk > self.risk_budget+1e-9:
            raise ValueError('All planned legs together exceed notional/reference-risk budget')

    def entry_price(self, price):
        return price*(1+self.direction*self.slippage_bps/10000)

    def exit_price(self, price):
        return price*(1-self.direction*self.slippage_bps/10000)

    def reference_risk(self, qty, entry, stop):
        exit_price = self.exit_price(stop)
        return qty*(max(0, self.direction*(entry-exit_price)) + (entry+exit_price)*self.fee_bps/10000)

    @property
    def fingerprint(self):
        return hashlib.sha256(json.dumps({'version': VERSION, 'plan': asdict(self)}, sort_keys=True).encode()).hexdigest()

    @classmethod
    def from_dict(cls, value):
        return cls(**{**value, 'entries': tuple(Entry(**v) for v in value['entries']),
                      'targets': tuple(Target(**v) for v in value['targets'])})


class PlanManager:
    """One immutable setup, one independent fully collateralized paper account.

    zone_close entry: signal only when the base candle closes INSIDE the next
    zone. Fill requires next open still in that zone. No inferred intrabar path.
    TP is also close-confirmed (not a resting limit order). First TP freezes
    the exit quantity basis and disables all remaining additions.
    """
    def __init__(self, plan):
        self.plan = plan
        self.state = 'PLANNED'
        self.stop = plan.initial_stop
        self.cash = float(plan.initial_cash)
        self.qty = self.avg = self.entry_notional = 0.0
        self.fees = self.funding_pnl = self.realized_pnl = 0.0
        self.entry_time = None
        self.leg_index = 0
        self.target_index = 0
        self.exit_basis = None
        self.pending = None
        self.previous = None
        self.stop_bars = []
        self.events, self.fills, self.equity = [], [], []
        cfg = config('bist' if plan.market == 'bist' else 'crypto')
        self.structure = Structure({**cfg, 'pivot_left': plan.pivot_left, 'pivot_right': plan.pivot_right}, 'protection')
        self.record(plan.created_at, 'PLAN_CREATED', 'Immutable setup registered', plan=asdict(plan))

    def record(self, time, action, reason, **details):
        self.events.append({'seq': len(self.events), 'time': time, 'plan_id': self.plan.id,
            'action': action, 'reason': reason, 'state': self.state, **details})

    def beyond_stop(self, price):
        return self.plan.direction*(price-self.stop) < 0

    def cancel(self, time, reason):
        self.pending = None
        self.state = 'CANCELLED'
        self.record(time, 'SETUP_CANCELLED', reason)

    def signal(self, bar, action, reason, **details):
        self.pending = {'action': action, 'signal_time': bar.end, 'reason': reason, **details}
        self.record(bar.end, action+'_SIGNAL', reason, **details)

    def fill_pending(self, bar):
        if not self.pending:
            return
        p, self.pending = self.pending, None
        plan = self.plan
        if p['action'] in ('ENTRY', 'ADD'):
            leg = plan.entries[p['leg']]
            reason = None
            price = plan.entry_price(bar.open)
            if self.qty == 0 and bar.start >= plan.expires_at:
                self.cancel(bar.start, 'Setup expired before initial execution')
                return
            if not leg.low <= bar.open <= leg.high or self.beyond_stop(bar.open) or plan.direction*(bar.open-self.stop) == 0:
                reason = 'Next open outside entry zone or beyond active protection'
            risk = plan.reference_risk(self.qty, self.avg, self.stop) + plan.reference_risk(leg.qty, price, self.stop)
            notional, fee = leg.qty*price, leg.qty*price*plan.fee_bps/10000
            if risk > plan.risk_budget+1e-9 or self.entry_notional+notional > plan.max_notional+1e-9 or notional+fee > self.cash+1e-9:
                reason = 'Reference risk, lifetime notional or available cash exceeded'
            if reason:
                self.record(bar.start, 'ORDER_CANCELLED', reason, order=p)
                return
            self.avg = (self.qty*self.avg+notional)/(self.qty+leg.qty)
            self.qty += leg.qty
            self.cash -= notional+fee
            self.entry_notional += notional
            self.fees += fee
            self.realized_pnl -= fee
            self.leg_index += 1
            self.entry_time = bar.start if self.entry_time is None else self.entry_time
            self.state = 'OPEN'
            fill = {'time': bar.start, 'action': p['action'], 'level_id': leg.id,
                    'signal_time': p['signal_time'], 'qty': leg.qty, 'price': price, 'fee': fee}
        else:
            qty = self.qty if p['action'] == 'EXIT' else min(self.qty, p['qty'])
            price = plan.exit_price(bar.open)
            fee = qty*price*plan.fee_bps/10000
            gross = plan.direction*qty*(price-self.avg)
            self.cash += qty*self.avg + gross-fee
            self.qty -= qty
            self.fees += fee
            self.realized_pnl += gross-fee
            if p['action'] == 'TP':
                self.target_index = p['target_end']
            self.state = 'CLOSED' if self.qty < 1e-10 else 'MANAGING'
            if self.state == 'CLOSED':
                self.qty = 0.0
            fill = {'time': bar.start, 'action': p['action'], 'signal_time': p['signal_time'],
                    'qty': qty, 'price': price, 'fee': fee, 'gross_pnl': gross, 'reason': p['reason']}
        self.fills.append(fill)
        self.record(bar.start, fill['action']+'_FILLED', 'Next available open simulation', fill=dict(fill),
                    remaining_qty=self.qty, average_entry=self.avg, cash=self.cash)

    def apply_funding(self, item):
        if self.qty and self.entry_time < item['time']:
            value = -self.plan.direction*self.qty*item['mark']*item['rate']
            self.cash += value
            self.realized_pnl += value
            self.funding_pnl += value
            self.record(item['time'], 'FUNDING', 'Historical funding, before boundary fills', amount=value)

    def validate_step(self, bar, stop_bars, funding):
        plan = self.plan
        if self.previous and (bar.start < self.previous.end or (plan.market != 'bist' and bar.start != self.previous.end)):
            raise ValueError('Duplicate, overlapping or missing base candle')
        if bar.start < plan.created_at:
            raise ValueError('Cannot trade before plan availability')
        if plan.market != 'bist' and (bar.end-bar.start != DURATIONS[plan.base_frame] or bar.start % DURATIONS[plan.base_frame]):
            raise ValueError('Expected aligned base candles')
        if plan.stop_frame == plan.base_frame and stop_bars != [bar]:
            raise ValueError('Same-frame stop must use the exact base candle')
        validate_bars(stop_bars)
        for b in stop_bars:
            if b.end > bar.end or (self.previous and b.end <= self.previous.end) or (self.stop_bars and b.start < self.stop_bars[-1].end):
                raise ValueError('Future or stale stop candle')
            if plan.market != 'bist' and (b.end-b.start != DURATIONS[plan.stop_frame] or b.start % DURATIONS[plan.stop_frame]):
                raise ValueError('Expected aligned stop candles')
        times = [f['time'] for f in funding]
        if times != sorted(set(times)) or any(not bar.start <= t < bar.end for t in times):
            raise ValueError('Funding must be ordered, unique and inside the current candle')
        if funding and plan.market != 'crypto_futures':
            raise ValueError('Funding only applies to crypto futures')
        if any(not positive(f['mark']) or not math.isfinite(f['rate']) for f in funding):
            raise ValueError('Invalid funding')

    def step(self, bar, stop_bars=None, funding=()):
        plan = self.plan
        stop_bars = [bar] if stop_bars is None and plan.stop_frame == plan.base_frame else list(stop_bars or ())
        self.validate_step(bar, stop_bars, funding)  # reject invalid input before mutation
        for item in funding:
            if item['time'] == bar.start:
                self.apply_funding(item)
        self.fill_pending(bar)
        for item in funding:
            if item['time'] > bar.start:
                self.apply_funding(item)
        candidates, invalid = [], False
        for b in stop_bars:
            invalid |= self.beyond_stop(b.close)
            high, low = self.structure.high_pivot, self.structure.low_pivot
            sig = self.structure.push(b)
            broken, candidate = (high, low) if plan.direction == 1 else (low, high)
            if (sig['bull' if plan.direction == 1 else 'bear'] and broken and candidate
                    and broken[2] <= b.start and candidate[2] <= b.start
                    and broken[0] < candidate[0] < b.start):
                candidates.append((candidate, broken, b))
            self.stop_bars.append(b)
        if self.state not in ('CLOSED', 'CANCELLED'):
            if invalid:
                if self.qty:
                    self.state = 'EXIT_PENDING'
                    self.signal(bar, 'EXIT', 'Structural invalidation on stop-frame close', stop=self.stop, frame=plan.stop_frame)
                else:
                    self.cancel(bar.end, 'Structure invalidated before entry')
            elif self.qty == 0 and bar.end >= plan.expires_at:
                self.cancel(bar.end, 'Setup expired without entry')
            else:
                self.manage(bar, candidates)
        value = self.cash + self.qty*self.avg + plan.direction*self.qty*(bar.close-self.avg)
        self.equity.append({'time': bar.end, 'value': value})
        self.previous = bar

    def manage(self, bar, candidates):
        plan = self.plan
        if self.qty:
            end = self.target_index
            while end < len(plan.targets) and plan.direction*(bar.close-plan.targets[end].price) >= 0:
                end += 1
            if end > self.target_index:
                if self.exit_basis is None:
                    self.exit_basis = self.qty
                    self.record(bar.end, 'ADDITIONS_DISABLED', 'First target signal freezes filled quantity for all partial exits',
                                cancelled_legs=[e.id for e in plan.entries[self.leg_index:]])
                qty = self.exit_basis*sum(t.fraction for t in plan.targets[self.target_index:end])
                if plan.market == 'bist':
                    qty = math.floor(qty)
                if end == len(plan.targets):
                    qty = self.qty
                if qty <= 0:
                    self.record(bar.end, 'TARGET_SKIPPED', 'Partial exit smaller than one BIST lot',
                                targets=[t.id for t in plan.targets[self.target_index:end]])
                    self.target_index = end
                else:
                    self.signal(bar, 'TP', 'Target confirmed by base close', qty=qty, target_end=end,
                                targets=[t.id for t in plan.targets[self.target_index:end]])
            if plan.protection == 'bos':
                for candidate, broken, b in candidates:
                    price = candidate[1]
                    if candidate[0] >= self.entry_time and plan.direction*(price-self.stop) > 0 and plan.direction*(bar.close-price) > 0:
                        old, self.stop = self.stop, price
                        self.record(bar.end, 'PROTECTION_UPDATED', 'Confirmed directional BOS; tightening only, effective from next candle',
                            previous=old, current=price, frame=plan.stop_frame,
                            pivot=candidate, broken_pivot=broken, confirmed_at=b.end)
            if self.pending:
                return
        if self.exit_basis is None and self.leg_index < len(plan.entries):
            leg = plan.entries[self.leg_index]
            safe_zone = leg.low > self.stop if plan.direction == 1 else leg.high < self.stop
            if safe_zone and leg.low <= bar.close <= leg.high:
                self.signal(bar, 'ENTRY' if not self.qty else 'ADD', 'Base close inside preplanned zone', leg=self.leg_index, level_id=leg.id)
                return
        self.record(bar.end, 'HOLD' if self.qty else 'WATCH', 'No actionable closed-candle condition',
                    stop=self.stop, qty=self.qty, stop_frame=plan.stop_frame, stop_candle_seen=bool(self.stop_bars))

    def report(self):
        last = self.equity[-1]['value'] if self.equity else self.plan.initial_cash
        return {'version': VERSION, 'mode': 'offline_plan_replay', 'execution': 'DISABLED',
            'plan': asdict(self.plan), 'plan_hash': self.plan.fingerprint,
            'state': self.state, 'active_stop': self.stop, 'remaining_qty': self.qty,
            'average_entry': self.avg if self.qty else None, 'pending': self.pending,
            'cash': self.cash, 'equity': last, 'net_pnl': last-self.plan.initial_cash,
            'realized_pnl': self.realized_pnl, 'fees': self.fees, 'funding_pnl': self.funding_pnl,
            'events': self.events, 'fills': self.fills, 'equity_curve': self.equity,
            'limitations': ['Manually specified levels; not a verified reproduction of Kriptotiks',
                'No live orders or liquidation/margin-tier model; one independent account per setup',
                'Risk budget is a reference estimate, not a guaranteed maximum loss',
                'Close-confirmed entries and TP; not resting intrabar limit orders',
                'Open PnL excludes future exit costs; no forced final close',
                'BIST timestamps/calendars/corporate actions must be validated externally']}


def replay_plan(plan, bars, stop_bars=None, funding=()):
    """Bars are from plan availability onward. BIST HTF input is explicit.

    Crypto higher candles are derived from the same closed base series. Missing
    initial partial higher buckets cannot be used for historical invalidation.
    """
    if not bars:
        raise ValueError('No closed candles')
    validate_bars(bars, continuous=plan.market != 'bist')
    if plan.stop_frame == plan.base_frame:
        if stop_bars is not None and list(stop_bars) != list(bars):
            raise ValueError('Same-frame stop candles differ from base')
        stop_bars = bars
    elif plan.market != 'bist':
        derived = aggregate(bars, DURATIONS[plan.stop_frame])
        if stop_bars is not None and list(stop_bars) != derived:
            raise ValueError('Crypto higher candles must match base aggregation')
        stop_bars = derived
    elif stop_bars is None:
        raise ValueError('BIST weekly/monthly closed candles must be supplied explicitly')
    validate_bars(stop_bars)
    if stop_bars and (stop_bars[0].end <= bars[0].start or stop_bars[-1].end > bars[-1].end):
        raise ValueError('Stop candles outside replay window')
    times = [f['time'] for f in funding]
    if times != sorted(set(times)) or any(not bars[0].start <= t < bars[-1].end for t in times):
        raise ValueError('Funding outside replay window, duplicated or unsorted')
    manager = PlanManager(plan)
    si = fi = 0
    for bar in bars:
        ss, ff = [], []
        while si < len(stop_bars) and stop_bars[si].end <= bar.end:
            ss.append(stop_bars[si]); si += 1
        while fi < len(funding) and funding[fi]['time'] < bar.end:
            ff.append(funding[fi]); fi += 1
        manager.step(bar, ss, ff)
    return manager
