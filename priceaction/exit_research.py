"""Opt-in exit-policy experiment. Production Engine and frozen sources untouched."""
from .engine import Engine, Structure
from .experiments import reflect, research_filter
from .model import aggregate, validate_bars

POLICIES = ('pivot', 'bos_confirmed')


class BosProtectedStructure(Structure):
    """Publish a trailing candidate only after a new bullish close break.

    Candidate is the latest confirmed low known BEFORE the break candle, formed
    AFTER the broken high. Engine still enforces post-entry and tightening-only.
    Reflected short prices implement the exact symmetric rule.
    """
    def __init__(self, cfg, name):
        super().__init__(cfg, name)
        self.protection_confirmation = None

    def push(self, bar):
        high, low = self.high_pivot, self.low_pivot
        signal = super().push(bar)
        # super() can confirm a new low at this close. It is not eligible for
        # this break: candidate and broken swing must already be known at open.
        self.new_low = None
        self.protection_confirmation = None
        if (signal['bull'] and high and low
                and high[2] <= bar.start and low[2] <= bar.start
                and high[0] < low[0] < bar.start):
            self.new_low = low
            self.protection_confirmation = {
                'break_close_time': bar.end,
                'broken_high': high,
                'candidate_low': low,
            }
        return signal


class ExitResearchEngine(Engine):
    def __init__(self, cfg, policy, entry_filter=None):
        if policy not in POLICIES:
            raise ValueError(f'Unknown exit policy: {policy}')
        if cfg['market'] != 'crypto':
            raise ValueError('This experimental adapter is crypto-only')
        super().__init__(cfg, entry_filter)
        self.exit_policy = policy
        if policy == 'bos_confirmed':
            self.base = BosProtectedStructure(cfg, 'base')

    def step(self, bar, setup_bars=(), context_bars=()):
        old = self.position['protected_low'] if self.position else None
        super().step(bar, setup_bars, context_bars)
        if (self.exit_policy == 'bos_confirmed' and old is not None and self.position
                and self.position['protected_low'] > old):
            # Enrich the existing HOLD event, never mutate history or exit orders.
            event = self.events[-1]
            assert event['action'] == 'HOLD' and self.base.protection_confirmation
            event['protection_update'] = {
                'policy': self.exit_policy, 'previous': old,
                **self.base.protection_confirmation,
            }


def replay_exit(cfg, bars, side, policy, trade_start=None, use_mtf=True):
    if side not in (1, -1):
        raise ValueError('Side must be 1 or -1')
    validate_bars(bars, continuous=True)
    if not bars:
        raise ValueError('No bars')
    prices = bars if side == 1 else reflect(bars, bars[0].open*100)
    engine = ExitResearchEngine({**cfg, 'fee_bps': 0, 'slippage_bps': 0}, policy,
        entry_filter=lambda e,b,z: research_filter(e,b,z,use_mtf,False,trade_start))
    setups, contexts = aggregate(prices,3600), aggregate(prices,14400)
    si=ci=0
    for bar in prices:
        ss,cc=[],[]
        while si<len(setups) and setups[si].end<=bar.end:
            ss.append(setups[si]); si+=1
        while ci<len(contexts) and contexts[ci].end<=bar.end:
            cc.append(contexts[ci]); ci+=1
        engine.step(bar,ss,cc)
    return engine


def orders_from(engine, side):
    return [{'time':e['time'],'action':e['action'],'side':side,'reason':e['reason'],'model':e.get('model')}
            for e in engine.events if e['action'] in {'BUY','SELL'}]
