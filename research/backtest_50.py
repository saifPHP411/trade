"""Replay the existing daily breakout rules and audit the whole-share budget."""
import argparse
import base64
import csv
import io
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from itertools import groupby
from statistics import median
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import backtest
from signals import Bar, candidates, rules, universe

START = date(2021, 7, 23)
END = date(2026, 7, 22)
TRACKER = "3cb6e8055d0f11ed6efd1d7a43fe3661cdd319ae"
SPY_BLOB = "fa0fbcf5246f67e0ad62765ada6f2194f6525be8"
CASH = 50


def download(url):
    request = Request(url, headers={"User-Agent": "trade-research"})
    with urlopen(request, timeout=25) as response:
        return response.read()


def stock_bars(symbol):
    from pyarrow.parquet import read_table

    url = ("https://raw.githubusercontent.com/floyds1995/Auto-Index-Constituents-Tracker/"
           f"{TRACKER}/us_data/raw_ohlcv/parquet/{symbol}.parquet")
    rows = read_table(io.BytesIO(download(url))).to_pylist()
    adjusted, as_traded = {}, {}
    subsequent_split_factor = 1
    for row in sorted(rows, key=lambda item: item["Date"], reverse=True):
        day = row["Date"].date()
        if row["Ticker"] != symbol:
            raise ValueError(f"Unexpected ticker in {symbol} source.")
        if day <= END:
            ratio = row["Adj_Close"] / row["Close"]
            adjusted[day] = Bar(day, *(row[key] * ratio for key in ("Open", "High", "Low", "Close")))
            as_traded[day] = row["Low"] * subsequent_split_factor
        if row["Split_Ratio"]:
            subsequent_split_factor *= row["Split_Ratio"]
    return symbol, adjusted, as_traded


def spy_bars():
    url = f"https://api.github.com/repos/MohammedAlkindi/Quant/git/blobs/{SPY_BLOB}"
    raw = base64.b64decode(json.loads(download(url))["content"]).decode()
    bars = {}
    for row in csv.DictReader(io.StringIO(raw)):
        day = date.fromisoformat(row["date"])
        if day <= END:
            bars[day] = Bar(day, *(float(row[k]) for k in ("open", "high", "low", "close")))
    return bars


def allocation_sweep(prices, signals, sessions, recent, settings):
    results = []
    for bps in (5, 15, 30):
        backtest.COST = bps / 10_000
        for size, cap in ((0.20, 5), (0.33, 3), (0.50, 2), (1.00, 1)):
            config = list(settings)
            config[0], config[4] = size, cap
            row = {"position_allocation_pct": round(size * 100), "max_positions": cap,
                   "cost_bps_each_side": bps}
            for name, period in (("full", sessions), ("recent", recent)):
                curve, trades = backtest.simulate("breakout", signals, prices, period,
                                                  CASH, config, fractional=True)
                ending, ret, drawdown, _, _ = backtest.metrics(curve, period, CASH)
                row[name] = {"ending_usd": round(ending, 2), "profit_usd": round(ending - CASH, 2),
                             "return_pct": round(ret * 100, 2),
                             "max_drawdown_pct": round(drawdown * 100, 2), "closed_trades": len(trades)}
            results.append(row)
    return results


def analyze(prices, raw_lows, symbols):
    sessions = sorted(day for day in prices["SPY"] if START <= day <= END)
    if not sessions or sessions[0] != START or sessions[-1] != END:
        raise ValueError("SPY does not cover the requested dates.")
    for symbol in symbols:
        if not set(sessions).issubset(prices[symbol]) or sum(d < START for d in prices[symbol]) < 199:
            raise ValueError(f"Incomplete data for {symbol}.")
    signals = candidates(prices, symbols)["breakout"]
    settings = rules()
    budget = CASH * settings[0]
    opportunities = [
        (symbol, next_day, raw_lows[symbol][next_day])
        for day, next_day in zip(sessions, sessions[1:])
        for _, symbol, *_ in signals.get(day, [])
    ]
    if not opportunities:
        raise ValueError("No breakout signals to audit.")
    cheapest = min(opportunities, key=lambda item: item[2])
    recent = [day for day in sessions if day >= date(2024, 12, 31)]
    results = []
    for bps in (5, 15, 30):
        backtest.COST = bps / 10_000
        for fractional in (False, True):
            curve, trades = backtest.simulate(
                "breakout", signals, prices, sessions, CASH, settings, fractional=fractional
            )
            final, ret, drawdown, _, _ = backtest.metrics(curve, sessions, CASH)
            row = {"cost_bps_each_side": bps, "size_mode": "fractional" if fractional else "whole",
                   "ending_usd": round(final, 2), "profit_usd": round(final - CASH, 2),
                   "return_pct": round(100 * ret, 4), "max_drawdown_pct": round(100 * drawdown, 4),
                   "closed_trades": len(trades),
                   "win_rate_pct": round(100 * sum(t.pnl > 0 for t in trades) / len(trades), 2) if trades else None}
            if fractional:
                recent_curve, recent_trades = backtest.simulate(
                    "breakout", signals, prices, recent, CASH, settings, fractional=True
                )
                row["recent_2025_ending_usd"] = round(recent_curve[-1], 2)
                row["recent_2025_closed_trades"] = len(recent_trades)
                row["spy_full_ending_usd"] = round(backtest.benchmark(prices, ["SPY"], sessions, CASH)[-1], 2)
                row["spy_recent_ending_usd"] = round(backtest.benchmark(prices, ["SPY"], recent[1:], CASH)[-1], 2)
                # Rolling within the same portfolio includes carryover positions and marks them at the close.
                weekly = []
                previous = CASH
                for _, days in groupby(zip(sessions, curve), key=lambda item: item[0].isocalendar()[:2]):
                    _, last = list(days)[-1]
                    weekly.append(last / previous - 1)
                    previous = last
                row["calendar_weeks"] = len(weekly)
                row["profitable_weeks"] = sum(pnl > 1e-12 for pnl in weekly)
                row["median_week_return_pct"] = round(100 * median(weekly), 4)
            results.append(row)
    return {"start": str(START), "end": str(END), "sessions": len(sessions), "stocks": len(symbols),
            "starting_cash_usd": CASH, "per_position_budget_usd": budget, "results": results,
            "allocation_sweep": allocation_sweep(prices, signals, sessions, recent, settings),
            "breakout_candidates": len(opportunities),
            "candidates_with_next_session_low_within_budget": sum(low <= budget for _, _, low in opportunities),
            "cheapest_candidate": {"symbol": cheapest[0], "session": str(cheapest[1]), "low_usd": round(cheapest[2], 2)},
            "minimum_initial_equity_for_cheapest_candidate_before_costs": round(cheapest[2] / settings[0], 2)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=Path("backtest-50.json"), type=Path)
    args = parser.parse_args()
    symbols = universe()
    with ThreadPoolExecutor(max_workers=8) as workers:
        sources = list(workers.map(stock_bars, symbols))
    prices = {symbol: history for symbol, history, _ in sources}
    prices["SPY"] = spy_bars()
    result = analyze(prices, {symbol: lows for symbol, _, lows in sources}, symbols)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"### Breakout backtest from ${CASH} ({START} to {END})\n")
    print(f"Tested {result['stocks']} symbols and {result['sessions']} market sessions.")
    print(f"The initial allocation limit is ${result['per_position_budget_usd']:.2f} per stock. "
          f"Of {result['breakout_candidates']} breakout candidates, "
          f"{result['candidates_with_next_session_low_within_budget']} had a next-day session low within this budget.\n")
    print("| Size mode | Cost/side | Final equity | Net profit | Closed trades | Win rate | Max drawdown | Recent final | SPY final | Profitable weeks | Median week |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in result["results"]:
        def cell(key):
            return r.get(key) if r.get(key) is not None else "—"
        weeks = f"{r['profitable_weeks']}/{r['calendar_weeks']}" if "calendar_weeks" in r else "—"
        print(f"| {r['size_mode']} | {r['cost_bps_each_side']} bps | ${r['ending_usd']:.2f} | "
              f"${r['profit_usd']:.2f} | {r['closed_trades']} | {cell('win_rate_pct')} | "
              f"{r['max_drawdown_pct']} | {cell('recent_2025_ending_usd')} | "
              f"{cell('spy_full_ending_usd')} | {weeks} | {cell('median_week_return_pct')} |")
    print("\n### Fractional allocation sensitivity")
    print("| Allocation per position | Max positions | Cost per side | Full final | Full drawdown | Recent final | Recent drawdown | Full trades | Recent trades |")
    print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in result["allocation_sweep"]:
        full, recent = row["full"], row["recent"]
        print(f"| {row['position_allocation_pct']}% | {row['max_positions']} | {row['cost_bps_each_side']} bps | "
              f"${full['ending_usd']:.2f} | {full['max_drawdown_pct']:.2f}% | "
              f"${recent['ending_usd']:.2f} | {recent['max_drawdown_pct']:.2f}% | "
              f"{full['closed_trades']} | {recent['closed_trades']} |")
    print("\nFractional purchases are rounded down to nine decimals and have a $1 stock-value minimum.")
    print("Daily bars model fills and protection. This replay uses the next session's open as its entry "
          "price, while the deployed whole-share executor uses timed limit orders.")



if __name__ == "__main__":
    main()
