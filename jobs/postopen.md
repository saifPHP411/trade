# jobs/postopen.md
1. Read rules.md and log.md, then check the Alpaca account, open positions and open orders.
2. For each order the morning job placed today, check it filled. If it didn't,
   cancel it and write why in the log.
3. For each position bought today, work out the stop and the target again from
   the price actually paid and the ATR in log.md (or recompute the ATR from the
   daily bars), using rules.md, and move its two exit orders there. If Alpaca
   won't move one, cancel both, check they show as cancelled, and place a new
   OCO sell order (stop and target, time in force gtc) for the shares held.
4. Sell every position that has reached the time limit in rules.md: cancel its
   stop and target first, check they show as cancelled, then sell it at the market.
5. Write what you did at the top of log.md.
If anything looks wrong, change nothing and say why in the log.
