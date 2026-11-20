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

## Railway scanner

Deploy this branch using the included Dockerfile. Set the cron schedule to `0 22 * * 1-5` (22:00 UTC on US weekdays) and select the Never restart policy. The container previews the breakout rule after the closing bell and skips days without a completed US market session. Read signals, errors, and skipped runs in the Railway logs.

In the scanner service's Variables tab, set `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` with keys from Alpaca Paper. The job uses read-only market data and does not submit orders.

## Railway dashboard

Deploy a separate service from the dashboard branch with start command `python -u dashboard.py` and healthcheck `/health`. Set `DASHBOARD_PASSWORD` and use the username `paper`. The service needs Alpaca Paper keys in `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`. These can be references to the scanner's service variables. The dashboard displays account data, equity history, positions, fills and open orders. All broker requests use GET.
