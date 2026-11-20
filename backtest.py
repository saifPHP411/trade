"""Backtest the three daily stock rules against two buy-and-hold benchmarks."""
import argparse
import csv
import math
import statistics
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

from signals import ROOT, RULES, candidates, load_prices, rules, universe

COST = 0.0005


@dataclass
class Position:
    shares: int
    entry_day: date
    session: int
    entry: float
    stop: float
    target: float


@dataclass
class Trade:
    rule: str
    symbol: str
    entry_day: date
    exit_day: date
    shares: int
    entry: float
    exit: float
    reason: str
    pnl: float


def simulate(rule, signals, prices, sessions, starting_cash, settings):
    size, stop, target, hold, cap, daily_limit, _ = settings
    positions, pending, closed, curve = {}, [], [], []
    cash = previous_equity = starting_cash

    def sell(symbol, price, day, reason):
        nonlocal cash
        position = positions.pop(symbol)
        proceeds = position.shares * price * (1 - COST)
        cash += proceeds
        pnl = proceeds - position.shares * position.entry * (1 + COST)
        closed.append(Trade(rule, symbol, position.entry_day, day, position.shares,
                            position.entry, price, reason, pnl))

    for index, day in enumerate(sessions):
        for symbol, position in list(positions.items()):
            bar = prices[symbol][day]
            if index - position.session >= hold:
                sell(symbol, bar.open, day, "time limit")
            elif bar.open <= position.stop or bar.open >= position.target:
                sell(symbol, bar.open, day, "gap through stop or target")
        for _, symbol, close, atr, _ in pending:
            if len(positions) >= cap:
                break
            if symbol in positions:
                continue
            bar = prices[symbol][day]
            shares = int(previous_equity * size / close)
            stop_price = bar.open - stop * atr
            total = shares * bar.open * (1 + COST)
            if shares > 0 and stop_price > 0 and total <= cash:
                positions[symbol] = Position(shares, day, index, bar.open, stop_price, bar.open + target * atr)
                cash -= total
        for symbol, position in list(positions.items()):
            bar = prices[symbol][day]
            if bar.low <= position.stop:
                sell(symbol, position.stop, day, "stop")
            elif bar.high >= position.target:
                sell(symbol, position.target, day, "target")
        equity = cash + sum(p.shares * prices[symbol][day].close for symbol, p in positions.items())
        curve.append(equity)
        pending = [
            item for item in signals.get(day, []) if item[1] not in positions
        ] if equity > previous_equity * (1 - daily_limit) else []
        previous_equity = equity
    return curve, closed


def benchmark(prices, symbols, sessions, cash):
    return [sum(cash / len(symbols) * prices[symbol][day].close /
                (prices[symbol][sessions[0]].open * (1 + COST)) for symbol in symbols)
            for day in sessions]


def metrics(curve, sessions, cash):
    high = cash
    drawdown = 0
    previous = cash
    daily = []
    yearly = {}
    for day, value in zip(sessions, curve):
        high = max(high, value)
        drawdown = min(drawdown, value / high - 1)
        daily.append(value / previous - 1)
        yearly.setdefault(day.year, [previous, value])[1] = value
        previous = value
    deviation = statistics.stdev(daily) if len(daily) > 1 else 0
    sharpe = f"{math.sqrt(252) * statistics.mean(daily) / deviation:.2f}" if deviation else "—"
    return curve[-1], curve[-1] / cash - 1, drawdown, sharpe, {
        year: end / start - 1 for year, (start, end) in yearly.items()
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rule", choices=(*RULES, "all"), default="all")
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    parser.add_argument("--cash", type=float, default=10_000)
    parser.add_argument("--prices", type=Path, default=ROOT / "prices.csv")
    args = parser.parse_args()
    if not math.isfinite(args.cash) or args.cash <= 0:
        parser.error("--cash must be positive and finite.")
    if not args.prices.is_file():
        parser.error("prices.csv is missing. Fetch Alpaca history first or provide --prices.")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    prices = load_prices(args.prices)
    symbols = universe()
    if not prices.get("SPY"):
        parser.error("The CSV must contain SPY for the benchmark and market sessions.")
    end = args.end or max(prices["SPY"])
    start = args.start or end - timedelta(days=5 * 365 + 1)
    sessions = sorted(day for day in prices["SPY"] if start <= day <= end)
    if not sessions:
        parser.error("No SPY sessions in the selected period.")
    for symbol in symbols:
        missing = set(sessions) - prices.get(symbol, {}).keys()
        warmup = sum(day < sessions[0] for day in prices.get(symbol, {}))
        if missing or warmup < 199:
            parser.error(f"{symbol}: {len(missing)} missing sessions and {warmup} warm-up bars (need 199).")
    signals = candidates(prices, symbols)
    settings = rules()
    chosen = RULES if args.rule == "all" else (args.rule,)
    results = {rule: simulate(rule, signals[rule], prices, sessions, args.cash, settings) for rule in chosen}
    results["SPY hold"] = benchmark(prices, ["SPY"], sessions, args.cash), None
    results["Equal-weight hold"] = benchmark(prices, symbols, sessions, args.cash), None
    years = sorted({day.year for day in sessions})
    headers = ["Strategy", "Ending value", "Return", "Max drawdown", "Sharpe", "Closed trades", "Win rate", *map(str, years)]
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join(["---"] * len(headers)) + " |")
    fig, ax = plt.subplots(figsize=(10, 5))
    with (ROOT / "trades.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(Trade.__dataclass_fields__))
        writer.writeheader()
        for name, (curve, trades) in results.items():
            ending, total, drawdown, sharpe, yearly = metrics(curve, sessions, args.cash)
            rate = f"{sum(trade.pnl > 0 for trade in trades)/len(trades):.1%}" if trades else "—"
            fields = [name, f"${ending:,.2f}", f"{total:.2%}", f"{drawdown:.2%}", sharpe,
                      str(len(trades)) if trades is not None else "—", rate]
            fields.extend(f"{yearly[year]:.2%}" for year in years)
            print("| " + " | ".join(fields) + " |")
            writer.writerows(asdict(trade) for trade in (trades or []))
            ax.plot(sessions, curve, label=name)
    ax.set(title="Historical simulation", ylabel="Equity (USD)")
    ax.legend()
    fig.autofmt_xdate()
    fig.savefig(ROOT / "equity_curves.png", dpi=140, bbox_inches="tight")


if __name__ == "__main__":
    main()
