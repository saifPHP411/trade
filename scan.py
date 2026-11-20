"""List daily long signals. Market-data requests are read-only."""
import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta

from alpaca import NY, ROOT, bars
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
        prices = defaultdict(dict)
        for day, symbol, open_price, high, low, close, _ in bars(
            sorted(set(symbols) | {"SPY"}), datetime.now(NY).date() - timedelta(days=460), args.feed
        ):
            prices[symbol][day] = Bar(day, open_price, high, low, close)
    else:
        prices = load_prices(ROOT / "prices.csv")
    sessions = prices.get("SPY", {})
    if not sessions:
        raise SystemExit("No SPY sessions. Cannot verify the scan date.")
    day = max(sessions) if args.live else args.date
    if day not in sessions:
        raise SystemExit(f"No completed market session for {day}.")
    print(f"{entry} · {day} · indicative levels based on last close")
    print("symbol     close      ATR     stop   target  signal")
    if args.live:
        missing = [symbol for symbol in symbols if day not in prices.get(symbol, {})]
        if missing:
            raise SystemExit("Latest session bars are missing for " + ", ".join(missing) + ".")
    picks = [
        item for item in candidates(prices, symbols)[entry].get(day, [])
        if item[2] - stop * item[3] > 0
    ]
    for _, symbol, close, atr, levels in picks:
        print(f"{symbol:8} {close:7.2f} {atr:8.2f} {close-stop*atr:8.2f} {close+target*atr:8.2f}  {levels}")
    if not picks:
        print("No qualifying stocks.")
