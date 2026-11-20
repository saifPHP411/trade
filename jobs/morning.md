# jobs/morning.md
1. Read rules.md and log.md, then check the Alpaca account and open positions.
2. Have the scanner run the scan.
3. Check its table against rules.md yourself. Skip anything we already hold
   and anything that breaks a limit.
4. Work out the shares, stop and target for each trade.
5. If the mode is alert, send me the trades and wait. If I haven't approved
   by the open, drop them. If the mode is auto, place each one as a bracket
   order for the open.
6. Write what you did, and what the next run needs to know, at the top of log.md.
   For each trade write the shares, ATR, stop and target. In alert mode, list
   the trades under "Waiting for approval".
If anything looks wrong, place nothing and say why in the log.
