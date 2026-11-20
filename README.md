# Alpaca Paper stock desk

This project follows the attached setup guide. The example starting balance is $10,000, with 20% per trade, up to five positions, a 3% daily loss limit, a 2 ATR stop, a 4 ATR target, and a 30-session time limit. The desk starts in alert mode. The breakout, pullback and oversold rules are research candidates until you select one. Candidates are ranked by their prior 126-session return, with ticker as a tie-breaker.

Once you approve the connection, copy .env.example to .env in your private runtime and set the two Alpaca paper credentials there. Keep the credentials out of chat and source control. A read-only account check verifies cash, positions and open orders. The Python tools also work with credentials supplied as environment variables.

```sh
python3 alpaca.py check
python3 get_prices.py
uv run --with matplotlib backtest.py --rule all
python3 scan.py --date YYYY-MM-DD --rule breakout
python3 -m unittest discover -s tests -v
```

The live scanner checks the latest completed session against Alpaca’s market calendar and requires a bar for each stock and SPY. In the backtest, the entry budget uses opening equity and includes entry costs. New entries are skipped when the opening equity loss reaches the daily limit.

The backtest uses the current stock list, which can introduce survivorship bias. Open positions are marked to market and the win rate counts closed trades. The buy-and-hold benchmarks enter at the first open with the same entry cost and are marked at the last close. Use `--start` and `--end` for a replay and keep the warm-up history in the CSV.

Claude Code can open this folder and read setup-progress.md to continue. The included Alpaca MCP configuration sets paper mode explicitly. Check the account before attempting a broker action. The jobs folder contains the review, pre-open, post-open and close prompts. See setup.md for the hosting options and New York schedule.
