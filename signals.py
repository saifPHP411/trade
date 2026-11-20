"""Daily indicators and ranked signals shared by the scanner and backtester."""
import csv
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from alpaca import ROOT

RULES = ("breakout", "pullback", "oversold")
COLUMNS = ("date", "symbol", "open", "high", "low", "close", "volume")


@dataclass(frozen=True)
class Bar:
    day: date
    open: float
    high: float
    low: float
    close: float


def universe():
    names = (ROOT / "stocks.txt").read_text().split()
    if not names or len(set(names)) != len(names):
        raise SystemExit("stocks.txt needs a nonempty list of unique tickers.")
    return names


def rules():
    text = (ROOT / "rules.md").read_text()
    size = float(re.search(r"^Size:\s*([\d.]+)%", text, re.M)[1]) / 100
    stop = float(re.search(r"^Stop:\s*([\d.]+) x ATR\(14\)", text, re.M)[1])
    target = float(re.search(r"^Target:\s*([\d.]+) x ATR\(14\)", text, re.M)[1])
    hold = int(re.search(r"^Time limit:.*after (\d+) trading days", text, re.M)[1])
    positions, loss = re.search(r"^Limits:\s*(\d+) positions max\. No new trades if the account is down ([\d.]+)%", text, re.M).groups()
    limit = float(loss) / 100
    if min(size, stop, target, hold, int(positions), limit) <= 0 or size * int(positions) > 1 or limit > 1:
        raise SystemExit("Invalid risk limits in rules.md.")
    entry = re.search(r"^Entry:\s*(\w+)", text, re.M)[1].lower()
    return size, stop, target, hold, int(positions), limit, entry


def load_prices(path):
    prices = defaultdict(dict)
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            day = date.fromisoformat(row["date"])
            symbol = row["symbol"]
            bar = Bar(day, *(float(row[key]) for key in COLUMNS[2:6]))
            if day in prices[symbol] or not (
                all(math.isfinite(value) for value in (bar.low, bar.high, bar.open, bar.close))
                and 0 < bar.low <= min(bar.open, bar.close)
                and max(bar.open, bar.close) <= bar.high
            ):
                raise SystemExit(f"Duplicate or invalid bar for {symbol} on {day}.")
            prices[symbol][day] = bar
    return prices


def wilder(values, period):
    result = [None] * len(values)
    if len(values) < period:
        return result
    result[period - 1] = sum(values[:period]) / period
    for index in range(period, len(values)):
        result[index] = (result[index - 1] * (period - 1) + values[index]) / period
    return result


def rsi(closes, period):
    change = [after - before for before, after in zip(closes, closes[1:])]
    gains = wilder([max(0, value) for value in change], period)
    losses = wilder([max(0, -value) for value in change], period)
    return [None] + [
        None if gain is None else 100 * gain / (gain + loss) if gain + loss else 50
        for gain, loss in zip(gains, losses)
    ]


def candidates(prices, symbols):
    result = {rule: defaultdict(list) for rule in RULES}
    for symbol in symbols:
        bars = sorted(prices[symbol].values(), key=lambda bar: bar.day)
        closes = [bar.close for bar in bars]
        if not bars:
            continue
        ranges = [bars[0].high - bars[0].low]
        ranges += [max(bar.high, prior.close) - min(bar.low, prior.close)
                   for prior, bar in zip(bars, bars[1:])]
        atr = wilder(ranges, 14)
        short_rsi, long_rsi = rsi(closes, 2), rsi(closes, 14)
        for index in range(199, len(bars)):
            close = closes[index]
            average = sum(closes[index - 199:index + 1]) / 200
            prior_high = max(closes[index - 55:index])
            score = close / closes[index - 126] - 1
            checks = {
                "breakout": (close > prior_high and close > average, f"55-day high {prior_high:.2f}, SMA200 {average:.2f}"),
                "pullback": (close > average and short_rsi[index] < 10, f"RSI2 {short_rsi[index]:.2f}, SMA200 {average:.2f}"),
                "oversold": (long_rsi[index] < 30, f"RSI14 {long_rsi[index]:.2f}"),
            }
            for rule, (qualifies, levels) in checks.items():
                if qualifies and atr[index] > 0:
                    result[rule][bars[index].day].append((score, symbol, close, atr[index], levels))
    for by_date in result.values():
        for items in by_date.values():
            items.sort(key=lambda row: (-row[0], row[1]))
    return result
