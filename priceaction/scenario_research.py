"""Opt-in, crypto-only scenario exits; not a replica of any trader's system.

Entry rules and accounting are inherited, not promoted to the live scanner.
Signal prices for shorts are reflected; only original-price account() is PnL.
"""
from .engine import Engine
from .exit_research import BosProtectedStructure
from .experiments import reflect, research_filter
from .model import aggregate, validate_bars

SCENARIO_POLICIES = ('scenario_only', 'setup_bos')


class ScenarioResearchEngine(Engine):
    def __init__(self, cfg, policy, entry_filter=None):
        if policy not in SCENARIO_POLICIES:
            raise ValueError(f'Unknown scenario policy: {policy}')
        if cfg['market'] != 'crypto' or tuple(cfg[k] for k in ('base', 'setup', 'context')) != ('15m', '1h', '4h'):
            raise ValueError('Scenario research requires crypto 15m/1h/4h')
        super().__init__(cfg, entry_filter)
        self.exit_policy = policy
        if policy == 'setup_bos':
            self.setup = BosProtectedStructure(cfg, 'setup')

    def step(self, bar, setup_bars=(), context_bars=()):
        # A 15m replay can publish at most one newly closed candle per frame.
        # Reject stale/repeated/unclosed inputs before even filling an order.
        for updates, seconds, structure in ((setup_bars, 3600, self.setup),
                                            (context_bars, 14400, self.context)):
            if len(updates) > 1 or any(
                b.end != bar.end or b.end-b.start != seconds or b.start % seconds
                or (structure.bars and b.start < structure.bars[-1].end)
                for b in updates
            ):
                raise ValueError('Expected only newly closed aligned higher candles')
        self.fill(bar)
        if self.position is None:
            # fill() cleared pending. The parent's second fill is a no-op.
            # Keep entry selection, zone consumption and cancellation identical.
            return super().step(bar, setup_bars, context_bars)

        for higher in context_bars:
            self.context.push(higher)
        for higher in setup_bars:
            self.setup.push(higher)
        signal = self.base.push(bar)
        if signal['sweep']:
            self.last_sweep = len(self.base.bars)-1
        p = self.position
        p['mfe_pct'] = max(p['mfe_pct'], (bar.high/p['entry_price']-1)*100)
        p['mae_pct'] = min(p['mae_pct'], (bar.low/p['entry_price']-1)*100)
        snapshot = {'context_trend': self.context.trend, 'setup_trend': self.setup.trend,
                    'base_trend': self.base.trend, 'sweep': signal['sweep'],
                    'exit_policy': self.exit_policy, 'invalidation_frame': '1h',
                    'zone_low': p['zone_low']}
        reason = None
        # Initial setup boundary takes priority, then the existing 4h structure.
        # A 15m close below either reference is explicitly NOT an exit here.
        if setup_bars and setup_bars[-1].close < p['zone_low']:
            reason = '1h kapanışı başlangıç senaryo bölgesini geçersizleştirdi'
        elif self.context.trend == -1:
            reason = '4h karşı yapı onaylandı'
        elif setup_bars and setup_bars[-1].close < p['protected_low']:
            reason = '1h kapanışı BOS teyitli korunan seviyeyi kırdı'

        if reason:
            self.pending = {'side': 'sell', 'signal_time': bar.end, 'reason': reason}
            self.event(bar, 'EXIT_SIGNAL', reason, **snapshot, protected_low=p['protected_low'])
        else:
            update = {}
            # setup.new_low persists between 1h closes: never reuse it on 15m.
            if self.exit_policy == 'setup_bos' and setup_bars:
                low = self.setup.new_low
                if low and low[0] >= p['entry_time'] and p['protected_low'] < low[1] < bar.close:
                    update['protection_update'] = {
                        'policy': self.exit_policy, 'frame': '1h',
                        'previous': p['protected_low'], 'current': low[1],
                        **self.setup.protection_confirmation,
                    }
                    p['protected_low'] = low[1]
            self.event(bar, 'HOLD', 'Ana senaryo kapanışta geçerli', **snapshot,
                       protected_low=p['protected_low'], **update)
        self.equity.append({'time': bar.end, 'value': self.cash+p['qty']*bar.close})


def replay_scenario(cfg, bars, side, policy, trade_start=None):
    if side not in (1, -1):
        raise ValueError('Side must be 1 or -1')
    validate_bars(bars, continuous=True)
    if not bars or any(b.end-b.start != 900 or b.start % 900 for b in bars):
        raise ValueError('Aligned continuous 15m candles required')
    prices = bars if side == 1 else reflect(bars, bars[0].open*100)
    engine = ScenarioResearchEngine({**cfg, 'fee_bps': 0, 'slippage_bps': 0}, policy,
        entry_filter=lambda e, b, z: research_filter(e, b, z, True, False, trade_start))
    setups, contexts = aggregate(prices, 3600), aggregate(prices, 14400)
    si = ci = 0
    for bar in prices:
        ss, cc = [], []
        while si < len(setups) and setups[si].end <= bar.end:
            ss.append(setups[si]); si += 1
        while ci < len(contexts) and contexts[ci].end <= bar.end:
            cc.append(contexts[ci]); ci += 1
        engine.step(bar, ss, cc)
    return engine
