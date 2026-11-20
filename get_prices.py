"""Save five years of daily prices plus indicator warm-up history."""
import argparse
import csv
from collections import defaultdict
from datetime import datetime, timedelta

from alpaca import NY, ROOT, bars
from signals import COLUMNS, universe

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feed", choices=("sip", "iex"), default="sip")
    args = parser.parse_args()
    today = datetime.now(NY).date()
    symbols = sorted(set(universe()) | {"SPY"})
    rows = sorted(bars(symbols, today - timedelta(days=5 * 366 + 460), args.feed))
    sessions = defaultdict(set)
    for day, symbol, *_ in rows:
        sessions[symbol].add(day)
    if not sessions["SPY"]:
        raise SystemExit("Alpaca did not return SPY bars.")
    for symbol in symbols:
        missing = sessions["SPY"] - sessions[symbol]
        print(f"{symbol}: {len(sessions[symbol])} bars, {len(missing)} missing SPY sessions")
    temp = ROOT / "prices.csv.tmp"
    with temp.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(COLUMNS)
        writer.writerows(rows)
    temp.replace(ROOT / "prices.csv")
