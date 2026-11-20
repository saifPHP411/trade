"""List daily long signals. Market-data requests are read-only."""
import argparse
from collections import defaultdict
from datetime import date, timedelta

from alpaca import NY, ROOT, bars, completed_bar_window
from signals import RULES, Bar, candidates, load_prices, rules, universe

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--live", action="store_true", help="use Alpaca market data")
    source.add_argument("--date", type=date.fromisoformat, help="replay a session from prices.csv")
    parser.add_argument("--rule", choices=RULES, help="preview a research candidate")
    parser.add_argument("--feed", choices=("sip", "iex"), default="sip")
    args = parser.parse_args()
    _, stop, target, _, _, _, entry = rules()
    entry = args.rule or entry
    if entry not in RULES:
        parser.error("There is no selected entry rule. Use --rule to preview a candidate.")
    symbols = universe()
    if args.live:
        day, cutoff = completed_bar_window()
        watched = sorted(set(symbols) | {"SPY"})
        prices = defaultdict(dict)
        start = cutoff.astimezone(NY).date() - timedelta(days=460)
        for session, symbol, open_price, high, low, close, _ in bars(
            watched, start, args.feed, window=(day, cutoff)
        ):
            prices[symbol][session] = Bar(session, open_price, high, low, close)
        missing = [symbol for symbol in watched if day not in prices.get(symbol, {})]
        if missing:
            raise SystemExit(f"Missing bars for expected session {day}: {', '.join(missing)}.")
    else:
        day = args.date
        prices = load_prices(ROOT / "prices.csv")
        if day not in prices.get("SPY", {}):
            raise SystemExit(f"No completed market session for {day}.")
    print(f"{entry} · {day} · indicative levels based on last close")
    print("symbol     close      ATR     stop   target  signal")
    picks = [
        item for item in candidates(prices, symbols)[entry].get(day, [])
        if item[2] - stop * item[3] > 0
    ]
    for _, symbol, close, atr, levels in picks:
        print(f"{symbol:8} {close:7.2f} {atr:8.2f} {close-stop*atr:8.2f} {close+target*atr:8.2f}  {levels}")
    if not picks:
        print("No qualifying stocks.")
