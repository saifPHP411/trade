"""Compare fixed market-breadth entry rules against the current daily signals."""
from collections import defaultdict, deque
from datetime import date
from itertools import groupby

import backtest
from signals import candidates


def market_breadth(prices, symbols, window=50):
    counts = defaultdict(lambda: [0, 0])
    for symbol in symbols:
        recent = deque(maxlen=window)
        for day, bar in sorted(prices[symbol].items()):
            recent.append(bar.close)
            if len(recent) == window:
                counts[day][0] += bar.close > sum(recent) / window
                counts[day][1] += 1
    return {day: up / count for day, (up, count) in counts.items() if count == len(symbols)}


def daily_variants(prices, symbols):
    original = candidates(prices, symbols)
    breadth = market_breadth(prices, symbols)
    variants = {
        "breakout": original["breakout"],
        "pullback": original["pullback"],
        "breakout_breadth": {},
        "pullback_breadth": {},
        "breadth_switch": {},
    }
    for day, fraction in breadth.items():
        if fraction >= 0.55:
            variants["breakout_breadth"][day] = original["breakout"].get(day, [])
            variants["pullback_breadth"][day] = original["pullback"].get(day, [])
        if fraction >= 0.45:
            rule = "breakout" if fraction >= 0.70 else "pullback"
            variants["breadth_switch"][day] = original[rule].get(day, [])
    return variants


def evaluate(prices, symbols, sessions, cash, settings, *, fresh=(), allocation=(0.50, 2), share_scales=None):
    variants = daily_variants(prices, symbols)
    settings = list(settings)
    settings[0], settings[4] = allocation
    split = date(2025, 1, 1)
    early = [day for day in sessions if day < split]
    later = [early[-1]] + [day for day in sessions if day >= split]
    periods = [("2021-2024", early, False), ("2025-Jul2026", later, True)]
    if fresh:
        periods.append(("Jul-Nov2026 forward", [sessions[-1], *fresh], True))
    rows = []
    prior_cost = backtest.COST
    try:
        for bps in (15, 30):
            backtest.COST = bps / 10_000
            for period, days, has_anchor in periods:
                benchmark_days = days[1:] if has_anchor else days
                benchmark_ending = None
                if all(day in prices["SPY"] for day in benchmark_days):
                    benchmark_ending = round(backtest.benchmark(prices, ["SPY"], benchmark_days, cash)[-1], 2)
                for name, signals in variants.items():
                    curve, trades = backtest.simulate(name, signals, prices, days, cash, settings,
                                                      fractional=share_scales is None, share_scales=share_scales)
                    value, ret, dd, _, _ = backtest.metrics(curve, days, cash)
                    gains = sum(t.pnl for t in trades if t.pnl > 0)
                    losses = -sum(t.pnl for t in trades if t.pnl < 0)
                    previous = cash
                    profitable_months = months = 0
                    monthly_data = zip(days[1:], curve[1:]) if has_anchor else zip(days, curve)
                    for _, values in groupby(monthly_data, key=lambda pair: (pair[0].year, pair[0].month)):
                        month_close = list(values)[-1][1]
                        profitable_months += month_close > previous + 1e-10
                        months += 1
                        previous = month_close
                    rows.append({"period": period, "variant": name, "cost_bps_each_side": bps,
                                 "ending_usd": round(value, 2), "return_pct": round(ret * 100, 2),
                                 "max_drawdown_pct": round(dd * 100, 2), "closed_trades": len(trades),
                                 "profit_factor": round(gains / losses, 3) if losses else None,
                                 "profitable_months": profitable_months, "months": months,
                                 "spy_ending_usd": benchmark_ending})
    finally:
        backtest.COST = prior_cost
    return rows
