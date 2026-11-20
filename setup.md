# I Turned Fable 5.2 Into a 24/7 Stock Trader: the setup file

This is the free setup file from the video. Drop it into Claude Code and Claude builds the whole trading desk with you, one step at a time: the Alpaca connection, your rulebook, a tested strategy, the analyst that checks your stocks every morning, and the schedule that runs it all while your laptop is closed.

> **Paper trading only.** Everything in this file runs on an Alpaca paper account: real stocks and real prices with fake money. Nothing here is financial advice. The backtest and the replay are simulations on past prices, not a track record.

## How to use this file

1. Make an empty folder on your computer called `trading-desk`.
2. Open Claude Code in that folder: the **Code** tab in the Claude desktop app (choose the folder), or run `claude` in a terminal inside the folder.
3. Choose **Fable 5.2** as the model (type `/model`). It's the model Miles uses for the decisions. On Max plans (and premium Team seats) Fable is included, up to half of your weekly usage limit. On Pro plans (and standard Team seats) Fable is paid per use with usage credits, so you may prefer Opus, which your plan includes.
4. Drag this file into the chat and type the line below. (Or copy the file into the folder and add its name to the line.)

   **Set up my trading desk from this file.**

5. Answer Claude's questions. It asks one thing at a time, suggests a starting point when you're not sure, and checks with you before it connects an account or places an order.

You can stop whenever you like. Claude saves a copy of this file in the folder as `setup.md`, so to carry on later, open Claude Code in the same folder and type **Read setup.md and carry on with the trading desk setup.**

**What you need**

- A Claude plan that includes Claude Code (Pro or above).
- A free Alpaca paper trading account from [alpaca.markets](https://alpaca.markets). In the paper dashboard you create an API key, which gives you a **key** and a **secret**. Don't paste them into any chat. Claude gives you a file to put them in.
- To run it with your laptop closed (Part 6): a free GitHub account, or a computer you leave switched on, or a small rented server.
- Optional: Telegram, if you want the desk to message your phone (Part 7).

---

## Instructions for Claude

You're setting up a stock trading desk with the user, following Miles's video "I Turned Fable 5.2 Into a 24/7 Stock Trader". Read this whole file first, then run the setup like this:

1. **Check where you are.** This setup needs Claude Code, because you'll create files, run commands and connect to Alpaca. If you can't do those things here (in a normal chat, for example), tell the user this file is made for Claude Code, explain how to open it there, and stop.
2. **Check for progress.** If `setup-progress.md` exists in the folder, read it and `setup.md` (your saved copy of this file), and carry on from where the progress file says. Otherwise start at Part 1. After every part, update `setup-progress.md` with what's done, so a new session can pick up. Its first line always says: `Setup instructions: setup.md`.
3. **One question at a time.** Ask, wait for the answer, then move on. Use plain words: the user may be new to trading and to Claude Code.
4. **Fill the brackets, keep the rest.** Prompts and files below have `[brackets]` for the user's own details. Fill each bracket from the user's answers and keep every other word exactly as written. Where a part lists **Miles's choice**, offer it as the suggestion when the user isn't sure, and say in a sentence or two why it's a sensible start.
5. **Paper only.** The desk runs on an Alpaca paper account. Never connect a live account. During the setup, don't place, cancel or close anything without first showing the user the exact order and getting a yes for it.
6. **Keys stay out of the chat.** Never ask for an API key, secret, token or password in the chat. Keys go into the `.env` file, which the user opens and fills in themselves. Never print that file. If the user pastes a key into the chat anyway, tell them to create a new key in Alpaca and delete the old one.
7. **Ask before connecting or installing anything.** That includes Alpaca, GitHub, Telegram, a server and any software.
8. **Run each part once.** At the end of a part, show what you made in a few lines and ask whether to carry on. Parts marked optional can be skipped.
9. **Check the details.** The commands, settings and menu names in this file were checked in November 2026. If something works differently in the user's version of Claude Code or Alpaca, use what's current, tell the user what changed, and keep the same result.
10. **Finish with the summary** described under "Finish" at the end.

The **Notes for Claude** section near the end has the detailed specs for the scripts. Use them when a part points to them.

---

## Part 1: Connect Alpaca and place a first trade

**What this does:** connects Claude to the Alpaca paper account so it can read the account and place orders. The keys stay in a file on the user's computer.

**Questions to ask**

1. Do you have an Alpaca paper account and an API key yet? If not, walk them through it: sign up at alpaca.markets, open the paper trading dashboard and generate an API key. The secret is shown once, so they should keep that page open until the file in step 4 is filled in.
2. Optional: Miles used a second paper account with $10,000, so the numbers in the video are easy to follow. Do you want the same? (In the Alpaca dashboard you can open a new paper account and choose its starting balance; you can have up to three. The balance can't be changed after the account is made, and each paper account has its own API keys, so the keys must come from the account the desk will use. The default $100,000 works too, because the desk works in percentages.)

**Steps for Claude**

1. Confirm the user is in the folder they want the desk in. Then save a copy of this whole file into the folder as `setup.md` (copy it if you have its path; otherwise write it out exactly), because step 6 starts a new session that won't have the dragged-in file.
2. Check the tools with `python3 --version` and `uvx --version`. In a terminal, also check `claude --version` and run `claude update` if it's out of date (Part 6 needs v2.1.259 or later; the desktop app updates itself). If `uv` is missing, ask, then install it with the official instructions at docs.astral.sh/uv. On Windows, if `bash` isn't available to start the connection below, tell the user and write a Windows version of the `.mcp.json`.
3. Create `.gitignore` before the `.env` file exists:

   ```
   .env
   logs/
   prices.csv
   __pycache__/
   ```

4. Create `.env` with placeholders. Ask the user to open it in a text editor, replace the placeholders with their two **paper** keys and save it. Don't read or print the file after they've filled it in.

   ```
   ALPACA_API_KEY=paste-your-paper-api-key-here
   ALPACA_SECRET_KEY=paste-your-paper-secret-key-here
   ```

   Then create `.claude/settings.json`. The first rule stops Claude's file reader from opening `.env`, so the keys never come into a session. The second turns on the Alpaca connection from step 5:

   ```json
   {
     "permissions": {
       "deny": ["Read(./.env)"]
     },
     "enabledMcpjsonServers": ["alpaca"]
   }
   ```

5. Create `.mcp.json`. This is the Alpaca connection: it starts Alpaca's official MCP server (`alpaca-mcp-server`, version 2), loads the keys from `.env` when the file is there, and locks the server to paper trading. (Alpaca's own instructions connect it with one `claude mcp add` command with the keys typed into it. This file uses `.mcp.json` instead, so the keys stay in `.env` and the same connection works in the cloud and on a server later.)

   ```json
   {
     "mcpServers": {
       "alpaca": {
         "command": "bash",
         "args": [
           "-c",
           "cd \"$CLAUDE_PROJECT_DIR\" 2>/dev/null; if [ -f .env ]; then set -a; . ./.env; set +a; fi; export ALPACA_PAPER_TRADE=true; exec uvx alpaca-mcp-server"
         ]
       }
     }
   }
   ```

6. Update `setup-progress.md` so the next session starts at step 7. Then ask the user to start a new Claude Code session in the same folder (in a terminal: exit and run `claude` again; in the desktop app: start a new session on this folder), approve the `alpaca` server if Claude Code asks, and type **Read setup.md and carry on with the trading desk setup.** In the new session, check that `/mcp` shows `alpaca` as connected.
7. Check the connection with Miles's prompt. It only reads:

   ```
   Check my Alpaca paper account. Tell me the cash balance, open positions and open orders. Don't place anything.
   ```

   If anything suggests this isn't a paper account, stop and tell the user.

8. **Optional: a first trade, typed by hand.** In the video Miles places one trade just by typing it. Ask whether the user wants to try one:

   ```
   Buy [stock] with [percent]% of the account.
   ```

   **Miles's choice:** Nvidia with 20% of a $10,000 account, so roughly a $2,000 order. Work out the whole number of shares from the latest price, show the user the shares, the price and the total, and place it only after they say yes. If the market is closed, explain that the order waits for the next open.

   Then offer a stop loss, which Miles recommends deciding in advance so a trade always has a level where it's wrong:

   ```
   Put a stop loss [percent]% below my entry on [stock].
   ```

   Place it as a stop order with time in force `gtc`, so it doesn't expire at the close, and show it before placing it. Place it only once the buy has filled: while the buy is still waiting (for example overnight, for the open), Alpaca rejects a sell order on the same stock as a possible wash trade. If the buy hasn't filled yet, say so, and offer to place the stop after the open. After Part 2, every trade gets its stop and its target automatically, because the bracket order sends them with the buy.

---

## Part 2: Step 1, the rulebook

**What this does:** writes `rules.md`, a plain text file with every decision the user makes on a trade: which stocks, how much goes in, where to sell if it goes wrong and where to take the profit. Fable reads it before every trade, so it never has to guess. Then it writes `CLAUDE.md`, which tells Fable to use the rulebook.

**Explain first, in a few lines:** there are two kinds of rule. Risk rules are personal: how much goes into each trade, how many trades at once, and how much the account can lose in a day. The main one is how much of the account you're willing to lose if a trade goes wrong. Strategy rules are what to buy, where the stop goes and where you take profit, and they come from a tested strategy in Part 3.

**Run this prompt** (Miles's prompt, word for word):

```
Create rules.md in this folder. It's the rulebook for my trading desk.
Ask me these questions one at a time, then write the file:
1. Which stocks am I allowed to trade?
2. How much of the account goes into each trade?
3. How many positions can I hold at once?
4. How much can the account lose in a day before you stop opening trades?
5. Where does the stop go on each trade, and where does the target go?
6. How long do I hold a trade that isn't going anywhere?
If I'm not sure about one, suggest a starting point and tell me why.
Leave a line for the entry rule and a line for the mode. I'll fill those in later.
```

**Miles's choices, to offer as suggestions**

| Question | Miles's choice | Why |
| --- | --- | --- |
| Stocks | 30 large US companies: AAPL, ABBV, AMZN, AVGO, BAC, CAT, COST, CRM, CSCO, CVX, DIS, GOOGL, HD, JNJ, JPM, KO, MA, MCD, META, MRK, MSFT, NVDA, ORCL, PEP, PG, TSLA, UNH, V, WMT, XOM | Easy to buy and sell, and lots of price history behind them |
| Size | 20% of the account per trade, whole shares | He works backwards from losing about 1% of the account on a bad trade: with the stop about 5% below the price, a 20% position loses about 1% |
| Positions | 5 at most | Five trades at 20% is the whole account, so it can never spend more than it has |
| Daily limit | 3% | If the account is down 3% on the day, it stops opening new trades |
| Stop and target | Stop 2 x ATR(14) below the entry price, target 4 x ATR(14) above it | ATR is the stock's average daily move over 14 days. On these stocks 2 ATR is usually around 5%, and a win makes about twice what a loss costs |
| Time limit | Sell at the open after 30 trading days | A trade that's gone nowhere gets closed |

**Steps for Claude**

1. Ask the six questions one at a time, as the prompt says.
2. Write the stocks into `stocks.txt`, one ticker per line.
3. Check the numbers add up: size x maximum positions should be 100% or less. Tell the user roughly what one losing trade costs (size x the distance to the stop).
4. Write `rules.md` in this format:

   ```
   # rules.md
   Account:     Alpaca paper
   Stocks:      only the ones in stocks.txt
   Size:        [size]% of the account per trade, whole shares
   Stop:        [stop rule]
   Target:      [target rule]
   Time limit:  sell at the open after [days] trading days
   Limits:      [positions] positions max. No new trades if the account is down [daily limit]% today.
   Entry:       none yet. I call the trades.
   Mode:        alert. Approvals of a morning run only count before the open.
   ```

5. Create `log.md` with one line: `# log.md (newest entries at the top)`.

**Then run the second prompt** (word for word):

```
Create CLAUDE.md in this folder with these standing instructions:
You run a trading desk on an Alpaca paper account.
Before any trading action, read rules.md and follow it exactly.
Show me the shares, stop and target, then place the order as a bracket order.
Never trade a stock that isn't in stocks.txt. Write every action to log.md.
The broker account is the source of truth. If anything looks wrong, place nothing.
```

After creating it, add these two lines at the end of `CLAUDE.md`. The first is what Alpaca needs for the stop and target to stay in place overnight. The second makes the daily loss limit work before the market opens, when today's change is still about zero:

```
Bracket orders: buy at the market with time in force gtc, so Alpaca holds the stop and the target until one of them is hit.
Daily limit: before the open, check the last full trading day's change in Alpaca's portfolio history. During market hours, check today's change.
```

**Explain to the user:** Claude Code reads `CLAUDE.md` at the start of every session, so these instructions never need repeating. A bracket order is the buy with the stop and the target attached. Alpaca holds those two exit orders from then on, which is why a trade stays protected overnight, or when nothing on the user's computer is running. To try it, they can type `Buy [stock].` (during the setup, still show the order and wait for their yes). The line that's still empty is the entry rule, which is Part 3.

---

## Part 3: Step 2, find a strategy and test it

**What this does:** finds an entry rule (what to buy), tests it on five years of real prices, and writes the winner into the rulebook.

**Explain first, briefly:** a strategy is a set of rules for exactly when to buy and when to sell, so there's no judgement involved. It has three parts: the entry (the signal to buy), the exit (the stop and the target) and the size. The size is already set. Most strategies are either **trend following**, which buys stocks that are already rising on the idea they keep rising, or **mean reversion**, which buys stocks that have dropped on the idea they bounce back.

There are four places to find one, as Miles says in the video:

1. **Your own trading.** Describe a setup that works for you, paste a TradingView Pine Script, or share your trading journal, and Fable turns it into rules.
2. **Famous published strategies.** Many well-known traders have written their rules down. Sites like [Quantpedia](https://quantpedia.com) collect them, and you can ask Fable for one by name.
3. **GitHub repos.** Free tools people share, which Miles has covered on the channel:
   - [TradingAgents](https://github.com/TauricResearch/TradingAgents): a team of AI analysts that debate a stock and come back with buy, hold or sell. Good for the fundamental side.
   - [AI Hedge Fund](https://github.com/virattt/ai-hedge-fund): similar, with analysts modelled on famous investors.
   - [Vibe-Trading](https://github.com/HKUDS/Vibe-Trading): describe a strategy in plain English and it backtests it for you.
   - [Daily Stock Analysis](https://github.com/ZhuLinsen/daily_stock_analysis): a written note on each of your stocks every morning.
4. **Fable itself.** Ask it to suggest strategies and test them. That needs nothing extra, and it's what Miles does in the video.

**Question to ask:** Do you already have a strategy you want to use (your own setup, a Pine Script, a journal or a published strategy), or should Fable suggest three to test, like Miles did?

**If they have their own**, run:

```
Here's my strategy: [describe it, or paste the Pine Script or journal].
Turn it into an exact entry rule for rules.md, using the stop, target and time limit style in rules.md, and tell me anything that's unclear.
```

**If Fable should suggest them**, run Miles's prompt (word for word):

```
Read rules.md. I want an entry rule for this desk, which checks in three
times a day and trades [US large-cap stocks] on daily bars, long only.
Propose three well-known candidates of different types: a breakout, a
pullback in an uptrend, and an oversold bounce. Give the exact entry rule
for each, using the stop, target and time limit style in rules.md.
```

**Miles's three, for reference:** a breakout that buys when a stock closes above its highest close of the last 55 trading days and is above its 200-day average (trend following, based on the Turtle Traders' rule); a pullback that buys a stock above its 200-day average when its 2-day RSI drops below 10 (from Larry Connors); and an oversold bounce that buys when the 14-day RSI drops below 30 (mean reversion).

**Get the prices.** The test needs five years of daily prices. Explain that this uses Alpaca's free market data, so nothing extra is needed. Then run:

```
Write get_prices.py to download five years of daily prices for every stock in stocks.txt, plus SPY for the S&P 500, from Alpaca, and save them as prices.csv.
```

Build it from the `get_prices.py` spec in Notes for Claude. If the user would rather use a paid data provider, Miles's recommended one is FMP (20% off here: https://tinyurl.com/FMPMiles).

**Then run the backtest prompt** (word for word, apart from the brackets):

```
Write backtest.py to test all three rules on the daily prices in prices.csv.
Start with $[starting amount] and use the size and the limits in rules.md.
Buy at the next day's open, and add a 0.05% cost to every buy and sell.
If the stop and the target are both hit on the same day, assume the stop
was hit first.
Compare the results with holding the S&P 500, and with holding all [number] stocks.
```

**Miles's choice:** $10,000. Build `backtest.py` from the spec in Notes for Claude. If the user brought one strategy of their own, test that one rule against the same two comparisons.

**Show the results** as one table: what the starting amount became, the total return, the worst drop from a high (max drawdown), the Sharpe ratio (return for the risk taken), the number of trades, the win rate, and the return in each calendar year. Save the chart as `equity_curves.png`. Then explain it the way Miles does:

- Which strategy made the most, and whether it beat holding the S&P 500.
- Whether it beat simply holding all the stocks. In Miles's test, none of the three did, because the market rose strongly over those five years and any rule that sells and waits for the next signal misses some of that rise.
- That returns aren't everything: a lower return with a smaller drawdown can be the better deal. Point to a year where trading helped (a falling market) and one where it hurt.
- That the list is today's big companies, so the past looks a bit better than it really was for everyone.

**Question to ask:** Which strategy should go into the rulebook? **Miles's choice:** the breakout, which made the most of the three over five years. If more stocks can qualify on one day than there are free slots, ask Fable to suggest how to pick between them (for example the biggest gain over the last six months), and put that in the entry line too.

**Then run** (word for word):

```
Add the [strategy] to rules.md as the entry rule.
```

**Explain the finished rulebook line by line:** the entry line is what to buy. The stop is where it sells if the trade goes against you, the target is where it sells to take profit, and the time limit sells a trade that's gone nowhere. The rulebook is now finished: the desk knows what to buy, how much, and when to sell. What it can't do yet is check the stocks by itself, which is Part 4.

---

## Part 4: Step 3, the analyst and the daily jobs

**What this does:** builds the part that does the work every morning. Checking the stocks goes to **Sonnet**, the cheaper Claude model, as a sub-agent called the scanner. The deciding stays with **Fable**, because that's where a mistake costs money.

**Run this prompt** (word for word):

```
Build the scanner for this desk.
1. Write scan.py. It checks every stock in stocks.txt against the entry rule
   in rules.md using daily prices from Alpaca, and prints a table of the ones
   that qualify. Use the same maths as backtest.py.
2. Create a sub-agent called scanner in .claude/agents/scanner.md. Put it on
   Sonnet. It can read files, run scan.py and read Alpaca news, and nothing
   else. For each stock in the table it adds one line of news. It never
   places orders and never gives an opinion on the trade.
```

Build `scan.py` from the spec in Notes for Claude. The sub-agent file should come out like this:

```
---
name: scanner
description: Runs the scan and checks the news on each candidate. Use for every scan.
model: sonnet
tools: Read, Bash, mcp__alpaca__get_news
---
Run python3 scan.py --live. For each stock it returns, read the latest news and add
one line: earnings in the next two days, or a specific reason for the move.
Return the table. Never place orders and never give an opinion on the trade.
```

**Explain:** `scan.py` is a small program, not an AI, because checking the rule is maths and a program gets maths right every time. The line `model: sonnet` puts the scanner on the cheaper model, and the `tools` line lists the only things it can use: reading files, running commands and Alpaca's news tool. It has no Alpaca order tool, and its instructions forbid placing orders.

**Create the morning job**, the checklist Fable follows with the scanner's list:

```
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
```

**Try it.** The rulebook is on alert, so run:

```
Run jobs/morning.md
```

The user should see Fable hand the check to the scanner sub-agent, a short table come back with a line of news on each stock, and then Fable's proposed trades with shares, stop and target. If they want to place one:

```
Take it.
```

That places a real paper order, so only do it when the user types it. This is a test run during the setup, so if the market is already open, the user's "Take it." still counts: say the order fills straight away at the current price rather than at the open. If nothing qualifies today, say so: that's normal, and the breakout rule can go days without a signal.

**Create the other three jobs.** These keep the trades looked after:

```
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
```

```
# jobs/close.md
1. Read rules.md and log.md, then check the Alpaca account, open positions and open orders.
2. Check every open position still has its stop and its target with Alpaca.
   If one is missing, put it back using rules.md.
3. List any position that reaches the time limit at tomorrow's open, so the
   post-open job sells it.
4. Write a short summary of the day at the top of log.md: what was bought,
   what was sold, the account value, and anything that looked wrong.
If anything looks wrong, change nothing and say why in the log.
```

```
# jobs/review.md
1. Read rules.md, log.md and this week's closed trades in the Alpaca account.
2. Compare the week with what the backtest expects: win rate, average win,
   average loss, and how far the fills were from the prices the morning job planned.
3. Write what you learned under "Lessons" at the top of log.md, so the next runs read it.
4. If you think a rule should change, write the change and your reason under
   "Proposed changes" in log.md. Don't edit rules.md. I decide, and any change
   gets backtested first.
```

**Explain:** the post-open job runs just after the market opens, checks the orders went through and moves the stop and target to the price actually paid. The close job runs just before the close and writes the day's summary. The review job is the learning part Miles gives to Fable: once a week it compares real results with the backtest and suggests improvements, but it never changes the rulebook without the user.

---

## Part 5: Alert or auto

**What this does:** decides whether the desk asks before every trade or places trades on its own.

**Explain:** in **alert** mode the desk finds the trades and the user approves each one ("Take it."). In **auto** mode it places them without asking. Switching is one word in the rulebook. Miles thinks alert mode is where most people should start: the research is done for you and approving is one message. On this paper account the user can try auto to see the full system run.

**Question to ask:** Stay on alert, or switch to auto?

To switch, run:

```
Change the mode in rules.md from alert to auto.
```

Before changing it, confirm again that the account is a paper account. Then offer to run the morning job once more, so the user sees it place the order and log it without asking. Tell them first that it will place any trades that qualify without a question, and run it only if they say yes.

**How often to check:** the breakout rule uses daily closing prices, so checking once a morning is enough. A server or a computer that stays on can run checks much more often (every ten minutes, say) if the user later moves to a faster rule. Claude's cloud scheduled tasks run at most once an hour.

---

## Part 6: Step 4, make it run on its own

**What this does:** right now everything lives in the `trading-desk` folder on the user's computer, so it only runs when the computer is on and someone starts it. This part puts the jobs on a timer somewhere that's always on.

**Explain the options and ask which one the user wants:**

- **A. Claude's scheduled tasks (cloud).** The easiest. The jobs run on Anthropic's computers, so they work with the laptop closed. The folder goes into a private GitHub repo, which works like a cloud copy of the folder. Needs a Pro, Max, Team or Enterprise plan with Claude Code on the web. It's a research preview, and it runs at most once an hour.
- **B. A computer you leave on, like a Mac Mini.** The Claude desktop app runs the jobs from the folder on that computer, as long as the app is open and the computer is awake.
- **C. A server you rent (a VPS).** Miles's preferred option for control. A small computer in a data centre that's always on, with Claude Code installed on it. Miles uses Hostinger: up to 79% off, plus 10% with the code `aiedge`, at https://www.hostinger.com/aiedge
- **D. An always-on agent.** Miles also mentions Claude Duet (Anthropic's always-on agent, a research preview), Grok Bot and ChatGPT Dots, and Hermes (an open-source agent from Nous Research that runs on a server and can work with several models). This file doesn't set those up. If the user wants one, do option A's GitHub step, then point the agent at the repo and give it the four job prompts from the table below.

**Before any option, add the allow rules to `.claude/settings.json`** (ask first), keeping what Part 1 put there. Nobody is there to click approve during a scheduled run, so these rules let the desk use its own tools without a click. The finished file:

```json
{
  "permissions": {
    "deny": ["Read(./.env)"],
    "allow": [
      "Edit(./log.md)",
      "Bash(python3 scan.py *)",
      "Bash(python3 scan.py)",
      "Bash(git add log.md)",
      "Bash(git commit *)",
      "Bash(git push *)",
      "Bash(git pull *)",
      "mcp__alpaca__get_account_info",
      "mcp__alpaca__get_account_activities",
      "mcp__alpaca__get_portfolio_history",
      "mcp__alpaca__get_all_positions",
      "mcp__alpaca__get_open_position",
      "mcp__alpaca__get_orders",
      "mcp__alpaca__get_order_by_id",
      "mcp__alpaca__get_clock",
      "mcp__alpaca__get_calendar",
      "mcp__alpaca__get_news",
      "mcp__alpaca__get_stock_bars",
      "mcp__alpaca__place_stock_order",
      "mcp__alpaca__replace_order_by_id",
      "mcp__alpaca__cancel_order_by_id",
      "mcp__alpaca__close_position"
    ]
  },
  "enabledMcpjsonServers": ["alpaca"]
}
```

Tell the user this also means Claude can place and change orders on this paper account without a permission click in their own sessions too. Check the tool names against what `/mcp` shows for the `alpaca` server and fix any that differ.

**The schedule** (all weekdays, New York time, off the hour so runs start on time):

| Job | Time | Prompt for the scheduled run |
| --- | --- | --- |
| Morning | 8:37am | `Run jobs/morning.md. If today isn't a trading day, or it's already past 9:25am New York time, place nothing, write that in log.md and stop.` |
| Post-open | 10:07am | `Run jobs/postopen.md. If today isn't a trading day, do nothing.` |
| Close | 3:37pm | `Run jobs/close.md. If today isn't a trading day, do nothing.` |
| Review | Fridays 4:37pm | `Run jobs/review.md.` |

Use Fable 5.2 as the model for all four. If the user's computer isn't on New York time, convert the times for anything that asks for local time.

Before scheduling anything, ask which Claude plan the user is on, because Fable is paid for differently. On Max plans and premium Team seats, Fable is included up to half of the weekly usage limit, and scheduled runs count toward it. If runs start stopping on that limit, keep Fable on the morning and review jobs, where the decisions are, and move the post-open and close jobs to Opus, since they're routine checks. On Pro plans and standard Team seats, Fable is paid per use with usage credits, so four runs every trading day add up to a real cost. Tell the user that plainly, and unless they choose to pay for it, use Opus for all four jobs. This applies everywhere the desk names a model: the scheduled tasks, `run.sh` (`claude-opus-5-5` in place of `claude-fable-5-2`) and `start-telegram.sh`.

### Option A: Claude's scheduled tasks (cloud)

1. **Put the folder on GitHub.** Run Miles's prompt below. Before the first commit, check with `git check-ignore .env` (and `git status`) that `.env` won't be uploaded, and stop if it would be.

   ```
   Create a private GitHub repo from this folder and push everything to it.
   ```

   Use the GitHub CLI (`gh`) if it's installed and signed in. If not, walk the user through creating an empty private repo on github.com and pushing to it.

2. **Give Claude access to the repo.** In claude.ai/code, the user connects GitHub if they haven't already.
3. **Make a cloud environment for the desk.** Each scheduled task runs in a cloud environment. Have the user create their own environment (or edit theirs) and set:
   - **Network access: Custom**, with `paper-api.alpaca.markets` and `data.alpaca.markets` in **Allowed domains** (one per line), and the option to also include the default list (the common package managers) turned on, so the run can download the Alpaca server. On the default **Trusted** setting, every request to Alpaca is blocked.
   - **Environment variables:** `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`, with the paper keys. The user types these into the settings page themselves. Claude's docs point out that anyone who uses an environment can read its variables, so this should be a private environment just for the desk, holding paper keys only.
4. **Create the tasks.** At claude.ai/code/routines (or in the desktop app's Code tab: **Scheduled**, then **New task**, then Cloud) the user creates one task per job from the table above: a name, the prompt, **Fable 5.2** in the model selector, the repo, and the desk's environment. Add this sentence to the end of every task's prompt, because each run starts from a fresh copy of the repo:

   ```
   When you're done, and again after any trade I approve in this session, commit log.md and push it to the main branch.
   ```

   Under **Connectors**, remove any the desk doesn't need. For the schedule, create the task with a daily preset, then open **Edit**, choose **Custom** and enter the cron line, keeping the `CRON_TZ=` prefix so the hours are New York time:

   ```
   Morning:    CRON_TZ=America/New_York 37 8 * * 1-5
   Post-open:  CRON_TZ=America/New_York 7 10 * * 1-5
   Close:      CRON_TZ=America/New_York 37 15 * * 1-5
   Review:     CRON_TZ=America/New_York 37 16 * * 5
   ```

5. **Test it.** Click **Run now** on the morning task and open the run. Check it reached Alpaca. If requests to Alpaca failed with a `403` or a message that the host is blocked or not allowed, the network setting in step 3 isn't saved. If the run is waiting on an approval, answer it there.
6. **Explain how it works from now on:** each run starts fresh and remembers nothing, which is what `log.md` is for: every run saves it back to GitHub and the next run reads it. To approve a trade in alert mode, the user opens that morning's run (the Claude app on their phone works) and replies `Take it.` before 9:30am New York time. To place a trade by hand from the phone, they start a new cloud session on the repo with the desk's environment and type it, for example `Buy [stock].` If the main branch is protected on GitHub, the log push may be blocked.

### Option B: a computer you leave on (Mac Mini)

1. In the Claude desktop app, **Code** tab: **Scheduled**, then **New task**. Choose a local task ("Only on this computer" under Advanced settings, or **Local** if the app asks), and pick the `trading-desk` folder.
2. Create one task per job from the table, with the prompt and **Fable 5.2** as the model. For the permission mode, choose **Auto** if the menu offers it; otherwise step 3 takes care of the approvals. Create it with a preset, then open **Edit** and choose **Custom** to enter the time. Custom times on this computer use its local time zone, so convert from New York time.
3. Click **Run now** on the morning task and watch for permission prompts. Choosing "always allow" means later runs won't stop on them.
4. Turn on **Keep computer awake** in the app's settings. Runs only happen while the app is open and the computer is awake, and a computer that slept through a run does one catch-up run when it wakes (the morning prompt's time check stops a late run from trading).
5. In alert mode, the user approves by opening the morning run's session and typing `Take it.`, or sets up Part 7 to approve from their phone.

### Option C: a server you rent (VPS)

The simplest way is to do this part on the server itself:

1. The user rents a small Ubuntu server (Miles: Hostinger, link above) and connects to it with SSH.
2. Install Claude Code with the official installer, then run `claude` and sign in with the Claude account:

   ```
   curl -fsSL https://claude.ai/install.sh | bash
   ```

3. Get the folder onto the server: clone the private GitHub repo from option A, or copy the folder across. The `.env` file stays behind on purpose; Claude makes a fresh one on the server in the next step.
4. Make sure `setup.md` is in the folder on the server too (it is if the folder went to GitHub). Open Claude Code in the `trading-desk` folder on the server and say: **Read setup.md and set up Part 6, option C, on this server.** Then Claude on the server does the rest:
   - Install Python 3 and uv if they're missing.
   - Create a fresh `.env` with the same placeholders as Part 1, and have the user fill in the paper keys themselves with a text editor on the server (for example `nano .env`).
   - Set the server's time zone to New York, so the timetable reads in market time, and check it with `date`:

     ```
     sudo timedatectl set-timezone America/New_York
     sudo systemctl restart cron
     ```

   - Create `run.sh`, which starts Claude Code in the background with a job. Nobody is there to click, so it runs in auto mode, where a safety check decides each action the settings file doesn't already allow, and anything that would still wait for a click is refused:

     ```bash
     #!/usr/bin/env bash
     # run.sh: runs one desk job unattended. Example: ./run.sh morning
     cd "$(dirname "$0")" || exit 1
     export PATH="$HOME/.local/bin:$PATH"
     mkdir -p logs
     case "$1" in
       morning)  PROMPT="Run jobs/morning.md. If today isn't a trading day, or it's already past 9:25am New York time, place nothing, write that in log.md and stop." ;;
       postopen) PROMPT="Run jobs/postopen.md. If today isn't a trading day, do nothing." ;;
       close)    PROMPT="Run jobs/close.md. If today isn't a trading day, do nothing." ;;
       review)   PROMPT="Run jobs/review.md." ;;
       *) echo "Usage: ./run.sh morning|postopen|close|review"; exit 1 ;;
     esac
     claude -p "$PROMPT" --model claude-fable-5-2 \
       --permission-mode auto --permission-prompts none \
       >> "logs/$1.log" 2>&1
     ```

   - Make it executable (`chmod +x run.sh`) and add the timetable with `crontab -e`, using the folder's full path:

     ```
     37 8  * * 1-5  [full path]/trading-desk/run.sh morning
     7  10 * * 1-5  [full path]/trading-desk/run.sh postopen
     37 15 * * 1-5  [full path]/trading-desk/run.sh close
     37 16 * * 5    [full path]/trading-desk/run.sh review
     ```

   - Test it once by hand: `./run.sh morning`, then read `logs/morning.log`. If the model name isn't accepted, use the name `/model` shows for Fable 5.2.
   - A normal sign-in can expire on a server nobody logs in to. For a sign-in that lasts a year, the user runs `claude setup-token` on the server, approves it in the browser, and adds the token it prints to the end of `.env` themselves, as `CLAUDE_CODE_OAUTH_TOKEN=[token]` (never pasted into the chat). Then add `set -a; . ./.env; set +a` to `run.sh` on the line after `mkdir -p logs`, so the runs use it.
5. **Explain:** this is the 24/7 part, because the server never switches off, and Alpaca holds the stop and target the whole time a trade is open. On a server, alert mode has no one to ask, so either switch to auto (Part 5) or set up Part 7 to approve from Telegram. If the folder is also on GitHub, the user can edit the rules there and add `git pull` to the top of `run.sh`.

---

## Part 7 (optional): alerts and approvals on Telegram

**What this does:** the desk messages the user's phone, and the user can reply `Take it.` from Telegram, or type a trade (`Buy [stock].`), which the desk handles the same way as at the computer. Replying needs option B or C from Part 6, because something has to stay running to hear the reply. (With option A, the cloud runs can still send the messages, using `notify.py` from the notes, and the user approves in the run itself.) Miles mentions two ways: a Claude Code session connected to Telegram, or Hermes as an orchestrator agent on the server. This part sets up the first. For Hermes, point the user to its docs at hermes-agent.nousresearch.com/docs.

**Steps for Claude** (Claude Code calls this feature channels; it's a research preview, it needs Bun installed, and on Team and Enterprise plans an admin has to turn it on):

1. The user creates a bot: in Telegram, open **@BotFather**, send `/newbot`, pick a name and a username ending in `bot`, and copy the token.
2. The user gets their Telegram user ID by messaging **@userinfobot**.
3. Add two placeholder lines to the end of `.env` with a shell command, without opening the file (it holds the Alpaca keys), and ask the user to fill them in themselves:

   ```
   printf '\nTELEGRAM_BOT_TOKEN=paste-your-bot-token-here\nTELEGRAM_CHAT_ID=paste-your-telegram-user-id-here\n' >> .env
   ```

4. Check Bun is installed (`bun --version`). If it isn't, ask, then install it from bun.sh. Then install the Telegram plugin in Claude Code (choose the user scope when asked):

   ```
   /plugin install telegram@claude-plugins-official
   ```

   If Claude Code can't find the marketplace, run `/plugin marketplace add anthropics/claude-plugins-official` and try again.

5. Write `notify.py` from the spec in Notes for Claude, and add this sentence to the end of each scheduled job prompt from Part 6 (for option C, those are the prompts inside `run.sh`): `Then send a short summary to Telegram with python3 notify.py, including any trades waiting for my approval.` Also add `"Bash(python3 notify.py *)"` to the allow list in `.claude/settings.json`. In `run.sh`, add a line after the `claude` command that runs `python3 notify.py "The $1 run failed"` if Claude Code exits with an error.
6. Add this line to `CLAUDE.md`:

   ```
   If I reply "Take it." on Telegram, place the trades the last morning run listed as waiting in log.md, only if it's before the open, and reply with what you placed.
   ```

7. Write `start-telegram.sh`, which loads the token from `.env` (so it never goes into a chat) and starts the session that listens to Telegram:

   ```bash
   #!/usr/bin/env bash
   cd "$(dirname "$0")" || exit 1
   set -a; . ./.env; set +a
   exec claude --channels plugin:telegram@claude-plugins-official --model claude-fable-5-2
   ```

8. Make it executable (`chmod +x start-telegram.sh`), then start it so it keeps running after the user disconnects. On a server, inside tmux: `tmux new -s desk`, run `./start-telegram.sh`, then detach with Ctrl+B and then D. On a Mac, leave the terminal window open.
9. Pair the account: the user sends any message to their bot, the bot replies with a pairing code, and in the Claude Code session they run `/telegram:access pair [code]` and then `/telegram:access policy allowlist`, so only their account can talk to the desk.

**Explain:** anyone on the allowlist can approve trades, so it should only ever hold the user's own account.

---

## Part 8: What it would have made, and tweaking it

**What this does:** runs the finished desk on the past year's prices, as a simulation, and shows how to improve the strategy over time.

**The replay.** Explain that the desk is brand new, so there's no live track record. What it can do is run the same test as Part 3 on just the past year's prices, starting fresh:

```
Run the same test as step two on just the past year's prices, starting with a fresh $[starting amount], using the rule in rules.md. Compare it with holding the S&P 500 and holding all [number] stocks.
```

Show the chart and label it clearly: "Replay on real prices. Not a live account." Report the end value, the number of trades, the win rate, the average win against the average loss, and the worst drop from a high. In the video, Miles's breakout replay turned $10,000 into about $11,600 over the year from 75 trades, ahead of the S&P 500. The user's numbers will differ with their dates, stocks and data.

Then show what the desk would have done this week:

```
Run the scan as of [last Monday] and show me what the desk would have bought.
```

**Tweaking it.** Any time, the user can ask Fable for its view:

```
What do you think of this strategy and how it's performing? Based on the current market, would you change anything?
```

If they decide on a change, edit `rules.md`, re-run the backtest, and (for option A) push the change to the GitHub repo so the scheduled runs pick it up. One good year doesn't outweigh the five-year test, so suggest keeping it on paper until the rule has earned trust.

**Other brokers.** This file is built for Alpaca and US stocks. Miles mentions you could use Interactive Brokers for more asset types (trickier to set up), Bybit for perpetuals, or Hyperliquid. If the user wants to try another broker later, Claude can adapt the desk, on a paper or test account first.

---

## Finish

When the setup is done, give the user a short summary:

1. The files in the folder and what each one does (use the list in "The whole system on one page").
2. What's connected: the Alpaca paper account, and GitHub, a server or Telegram if set up.
3. The mode (alert or auto) and how to switch it.
4. The schedule and where it runs, or that it's not scheduled yet and runs by typing `Run jobs/morning.md`.
5. What to do next: watch it on paper in alert mode for a few weeks, read `log.md`, and check the weekly review.

Then mark `setup-progress.md` as complete.

---

## Notes for Claude: the scripts

Keep every script short, commented in plain English and runnable with `python3 [script].py`, apart from `backtest.py` (see below). Every script that talks to Alpaca reads `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` from the environment first, then from `.env`, and never prints them. Put the entry rule maths in one shared file, `signals.py`, so `backtest.py` and `scan.py` always agree.

**Alpaca market data.** Daily bars come from `https://data.alpaca.markets/v2/stocks/bars` with the headers `APCA-API-KEY-ID` and `APCA-API-SECRET-KEY`, and the parameters `symbols` (comma separated), `timeframe=1Day`, `start`, `end`, `adjustment=all` (adjusted for splits and dividends), `feed=sip`, `limit=10000`, and `page_token` to page through results. The free plan can't fetch the latest 15 minutes of full-market data, so always set `end` to a time at least 16 minutes in the past. If Alpaca still refuses, use `feed=iex` and tell the user the prices may differ slightly. The free plan allows about 200 requests a minute. Before the close, the latest daily bar is today's unfinished one, so drop any bar dated today (New York time) unless the market has already closed.

**get_prices.py.** Downloads daily bars for every ticker in `stocks.txt` plus SPY, covering five years plus about 300 extra trading days before that, so the 200-day average already exists on the first test day. Saves `prices.csv` with the columns date, symbol, open, high, low, close, volume. Prints how many days it got for each ticker and flags any with gaps. Uses only the standard library, so it runs with nothing installed.

**signals.py.** The indicators and the entry rules from `rules.md`. It uses only Python's standard library, because `scan.py` imports it and has to run with nothing installed. Use closing prices. The highest close of the last N days means the N days before today, not including today. The 200-day average is a simple average of closes. ATR(14) uses Wilder's method. RSI uses Wilder's method. Include the ranking used when more stocks qualify than there are free slots.

**backtest.py.** Simulates the rules day by day on `prices.csv`:

- Signals use a day's close, and the trade buys at the next day's open.
- Size is the percentage in `rules.md` of the account value at that close, rounded down to whole shares. Skip a trade if there isn't enough cash.
- Never hold more than the maximum positions or two positions in one stock. When more stocks qualify than there are free slots, use the ranking from `signals.py`.
- Stop and target come from the ATR at the signal day's close, measured from the entry price.
- Each day, check the low against the stop and the high against the target. If the day opens beyond either one, exit at the open. If both are hit on the same day, the stop was hit first.
- Sell at the open once a trade reaches the time limit.
- Charge 0.05% on every buy and every sell.
- Daily limit: if the account closes down by the limit or more on a day, open no new trades the next morning.
- Compare with buying SPY on day one and holding it, and with splitting the starting amount equally across all the stocks on day one and holding them.
- Options: `--rule` (one rule or all), `--start` and `--end` dates, `--cash`. The same code runs the five-year test and the replay in Part 8.
- Output: the results table described in Part 3, a list of every trade in `trades.csv`, and `equity_curves.png` with every line on one chart.
- It can use pandas and matplotlib. Run it with `uv run --with pandas --with matplotlib backtest.py` (uv was set up in Part 1), so nothing has to be installed into the computer's own Python. Use the same command for the replay in Part 8.

**scan.py.** Uses only Python's standard library, so it runs in the cloud and on a server with nothing to install. With `--live` it fetches the last 300 daily bars for each stock from Alpaca. With `--date YYYY-MM-DD` it scans as of that date from `prices.csv`, which the replay uses. It prints one table of the stocks that qualify, ranked, with the close, the levels the rule uses, the ATR and the stop and target each trade would get. It doesn't check holdings or limits: Fable does that in the morning job.

**The live orders (morning and post-open jobs).** The morning job estimates the stop and target from the last close and places a bracket order: a market buy with time in force `gtc`, with the stop and the target attached. The post-open job then moves both exit orders to the price actually paid, so they match the rule (the job file includes the OCO fallback if Alpaca won't move one). The stop and target take the buy order's time in force, which is why the buy must be `gtc`: with `day`, Alpaca cancels them after the first day. The daily limit line in `CLAUDE.md` makes the live check match the backtest: before the open it looks at the last full trading day, and during market hours at today's change. These live rules are written into `CLAUDE.md` and the job files because scheduled runs don't read this setup file. The post-open job sells time-limit trades shortly after the open, which is close enough to the backtest's open price for a daily rule. Alpaca holds a position's shares for its open exit orders, and rejects a new order while an opposite-side order on the same stock is still open, which is why the post-open job checks its cancels have gone through before it places anything new on that stock.

**notify.py** (Part 7 only). Uses only the standard library. Reads `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from the environment or `.env`, and sends the text it's given (as an argument, or on standard input) with Telegram's `sendMessage` method at `https://api.telegram.org/bot[token]/sendMessage`. For option A runs, add `api.telegram.org` to the environment's allowed domains and the two Telegram values to its variables.

---

## The whole system on one page

```
  rules.md  (your rules: stocks, size, stop, target, time limit, limits, entry, mode)
     |
     |   read before every trade
     v
  morning job, run by Fable 5.2 on a schedule (cloud, a Mac that stays on, or a server)
     |
     |-- asks the scanner (Sonnet) --> scan.py checks the entry rule + one line of news each
     |
     |-- checks the list against rules.md and the Alpaca account
     |
     |-- alert mode: sends you the trades and waits for "Take it."
     |-- auto mode:  places them
     v
  Alpaca paper account: a bracket order (the buy, with the stop and the target held by Alpaca)
     |
     |-- post-open job: checks the fill and moves the stop and target to the price paid
     |-- close job:     daily summary, checks every trade still has its stop and target
     v
  log.md: what happened, and what the next run needs to know
     |
     v
  weekly review (Fable): lessons, and proposed rule changes for you to decide on
```

**The folder when it's finished**

```
trading-desk/
  setup.md                 a copy of this setup file
  setup-progress.md        how far the setup got
  .env                     your Alpaca keys (never shared, never uploaded)
  .gitignore               keeps .env, logs and the price file out of GitHub
  .mcp.json                connects Claude to Alpaca, locked to paper trading
  CLAUDE.md                standing instructions Claude reads every session
  rules.md                 your rulebook
  stocks.txt               the stocks you allow
  log.md                   the desk's memory between runs
  get_prices.py            downloads daily prices into prices.csv
  prices.csv               five years of daily prices (stays on your computer)
  signals.py               the entry rule maths, shared by the backtest and the scan
  backtest.py              the five-year test and the replay
  trades.csv               every trade from the last backtest or replay
  equity_curves.png        the backtest chart
  scan.py                  the daily check the scanner runs
  .claude/agents/scanner.md   the Sonnet analyst
  .claude/settings.json    keeps .env out of sessions, and what runs may do without a click
  jobs/morning.md          find and place (or propose) the day's trades
  jobs/postopen.md         check fills, fix stops and targets, time-limit exits
  jobs/close.md            daily summary and protection check
  jobs/review.md           weekly lessons and proposed changes
  run.sh                   (server only) runs a job unattended
  notify.py                (Telegram only) sends you messages
  start-telegram.sh        (Telegram only) starts the session that hears "Take it."
```
