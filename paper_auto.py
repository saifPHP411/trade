"""Run one polling cycle of the unattended Alpaca Paper strategy."""
import argparse
import json
import os
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, build_opener

from alpaca import DATA, NY, PAPER, NoRedirect, bars, completed_bar_window, credentials, get
from signals import Bar, candidates, rules, universe

ENTRY_PREFIX = "trade-paper-entry-"
EXIT_PREFIX = "trade-paper-exit-"
ENTRY_START = time(9, 35)
ENTRY_END = time(9, 50)
TERMINAL = {"filled", "canceled", "expired", "rejected", "replaced"}
ORDER_LIMIT = 500
CENT = Decimal("0.01")


class BrokerError(RuntimeError):
    def __init__(self, status, method, path):
        self.status = status
        super().__init__(f"{method} {path}: Alpaca Paper returned {status}")


class PaperBroker:
    def __init__(self):
        keys = credentials()
        self.headers = {
            "APCA-API-KEY-ID": keys["ALPACA_API_KEY"],
            "APCA-API-SECRET-KEY": keys["ALPACA_SECRET_KEY"],
            "Content-Type": "application/json",
        }
        self.opener = build_opener(NoRedirect())

    def request(self, path, *, method="GET", body=None, **params):
        url = PAPER + path + (f"?{urlencode(params)}" if params else "")
        request = Request(url, json.dumps(body).encode() if body is not None else None,
                          headers=self.headers, method=method)
        try:
            with self.opener.open(request, timeout=12) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except HTTPError as error:
            raise BrokerError(error.code, method, path) from None
        except URLError:
            raise RuntimeError(f"{method} {path}: unable to reach Alpaca Paper") from None

    def orders(self, status, **params):
        orders = self.request("/v2/orders", status=status, limit=ORDER_LIMIT, **params)
        if not isinstance(orders, list) or len(orders) >= ORDER_LIMIT:
            raise RuntimeError("Order snapshot is incomplete. Cycle stopped.")
        return orders

    def order(self, order_id):
        return self.request(f"/v2/orders/{quote(order_id, safe='')}", nested="true")

    def order_by_client_id(self, client_id):
        try:
            return self.request("/v2/orders:by_client_order_id", client_order_id=client_id)
        except BrokerError as error:
            if error.status != 404:
                raise
            return None

    def submit(self, order):
        client_id = order["client_order_id"]
        if self.order_by_client_id(client_id) is not None:
            print(f"Order already recorded: {client_id}")
            return False
        result = self.request("/v2/orders", method="POST", body=order)
        if not result or result.get("client_order_id") != client_id:
            raise RuntimeError(f"Order receipt could not be verified: {client_id}")
        print(f"{client_id}: {result.get('status', 'accepted')}")
        return True

    def cancel(self, order_id):
        try:
            self.request(f"/v2/orders/{quote(order_id, safe='')}", method="DELETE")
        except BrokerError as error:
            if error.status not in {404, 422}:
                raise
            # A fill or another cancel may have won. The next snapshot decides what to do.


def d(value):
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ValueError("Non-numeric broker field.") from None
    if not number.is_finite():
        raise ValueError("Non-finite broker field.")
    return number


def ny_timestamp(value):
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None:
        raise ValueError("Broker timestamp has no offset.")
    return stamp.astimezone(NY)


def is_owned_entry(order):
    return order["side"] == "buy" and order["client_order_id"].startswith(ENTRY_PREFIX)


def accept_entries(account, daily_limit):
    equity, previous = d(account["equity"]), d(account["last_equity"])
    return (account["status"] == "ACTIVE" and not account["trading_blocked"]
            and not account["account_blocked"] and not account.get("trade_suspended_by_user") and previous > 0
            and equity > previous * (1 - d(daily_limit)) and d(account["cash"]) > 0)


def breakout_candidates(symbols, today, previous_session):
    day, cutoff = completed_bar_window()
    if day != previous_session:
        raise RuntimeError(f"Expected bars for {previous_session}; Alpaca calendar indicated {day}.")
    watched = sorted(set(symbols) | {"SPY"})
    prices = defaultdict(dict)
    for session, symbol, opening, high, low, close, _ in bars(
        watched, today - timedelta(days=460), "sip", window=(day, cutoff)
    ):
        prices[symbol][session] = Bar(session, opening, high, low, close)
    if any(day not in prices[symbol] or len(prices[symbol]) < 200 for symbol in watched):
        raise RuntimeError("Daily market data is incomplete. Entry skipped.")
    return candidates(prices, symbols)["breakout"].get(day, [])


def entry_order(symbol, atr, market_quote, now, budget, stop_factor, target_factor):
    if not market_quote:
        return None
    bid, ask = d(market_quote["bp"]), d(market_quote["ap"])
    age = (now - ny_timestamp(market_quote["t"])).total_seconds()
    if not -5 <= age <= 90 or not 1 <= bid <= ask or (ask - bid) / ask > d("0.005"):
        return None
    limit = ask.quantize(CENT, rounding=ROUND_CEILING)
    stop = (limit - d(atr) * d(stop_factor)).quantize(CENT, rounding=ROUND_FLOOR)
    target = (limit + d(atr) * d(target_factor)).quantize(CENT, rounding=ROUND_CEILING)
    qty = int(budget // limit)
    if qty <= 0 or stop <= 0 or stop > bid - CENT or target < limit + CENT:
        return None
    return {
        "symbol": symbol, "side": "buy", "type": "limit", "time_in_force": "gtc",
        "order_class": "bracket", "qty": str(qty), "limit_price": str(limit),
        "stop_loss": {"stop_price": str(stop)}, "take_profit": {"limit_price": str(target)},
        "client_order_id": f"{ENTRY_PREFIX}{now.date():%Y%m%d}-{symbol}",
    }


def remaining_qty(parent):
    return d(parent["filled_qty"]) - sum(d(leg["filled_qty"]) for leg in parent.get("legs") or [])


def manage_positions(broker, current, sessions, hold, history, positions, open_orders, allow_entry):
    today = current.date()
    safe_to_enter = True
    for order in open_orders:
        if is_owned_entry(order) and (
            not allow_entry or current.time() >= ENTRY_END or ny_timestamp(order["submitted_at"]).date() < today
        ):
            broker.cancel(order["id"])
            print(f"Cancellation requested: {order['client_order_id']}")
            safe_to_enter = False

    open_by_symbol = defaultdict(list)
    for order in open_orders:
        open_by_symbol[order["symbol"]].append(order)
    owned = {}
    for order in history:
        if is_owned_entry(order) and d(order["filled_qty"]) > 0:
            owned.setdefault(order["symbol"], order)  # Broker returns newest first.

    for position in positions:
        symbol = position["symbol"]
        if position["side"] != "long" or symbol not in owned:
            continue
        parent = broker.order(owned[symbol]["id"])
        qty = d(position["qty"])
        legs = {leg["id"]: leg for leg in parent.get("legs") or []}
        submitted = ny_timestamp(parent["submitted_at"])
        already_exited = sum(
            d(order["filled_qty"]) for order in history
            if order["symbol"] == symbol and order["client_order_id"].startswith(EXIT_PREFIX)
            and ny_timestamp(order["submitted_at"]) >= submitted
        )
        if qty <= 0 or qty != remaining_qty(parent) - already_exited:
            safe_to_enter = False
            print(f"{symbol}: position size does not match the strategy order. Review required.")
            continue
        related = open_by_symbol[symbol]
        if parent["status"] not in TERMINAL or any(o["id"] not in legs for o in related):
            continue
        opened = ny_timestamp(parent.get("filled_at") or parent["submitted_at"])
        if (current - opened).total_seconds() < 180:
            continue
        protected = {order["type"] for order in related if order["status"] != "pending_cancel"}
        expired = sum(opened.date() < day <= today for day in sessions) >= hold
        if not expired and "limit" in protected and protected & {"stop", "stop_limit"}:
            continue
        safe_to_enter = False
        for order in related:
            if order["status"] != "pending_cancel":
                broker.cancel(order["id"])
        active_legs = [leg for leg in legs.values() if leg["status"] not in TERMINAL]
        if related or active_legs:
            print(f"{symbol}: waiting for protective orders to cancel before closing.")
            continue

        fresh = next((p for p in broker.request("/v2/positions") if p["symbol"] == symbol), None)
        if (not fresh or fresh["side"] != "long" or d(fresh["qty"]) != qty
                or d(fresh.get("qty_available", fresh["qty"])) != qty
                or any(o["symbol"] == symbol for o in broker.orders("open"))):
            continue
        broker.submit({
            "symbol": symbol, "side": "sell", "type": "market", "time_in_force": "day",
            "qty": str(qty), "position_intent": "sell_to_close",
            "client_order_id": f"{EXIT_PREFIX}{today:%Y%m%d}-{symbol}",
        })

    return safe_to_enter


def enter_positions(broker, current, previous_session, settings, account, positions, open_orders, history):
    size, stop, target, _, max_positions, daily_limit, _ = settings
    busy = {p["symbol"] for p in positions} | {o["symbol"] for o in open_orders}
    if len(busy) >= max_positions:
        print("Position and order limit reached.")
        return
    pending_buys = [o for o in open_orders if o["side"] == "buy"]
    if any(not o.get("limit_price") for o in pending_buys):
        print("Unpriced pending buy. No new entries.")
        return
    covered = sum(d(o["limit_price"]) * (d(o["qty"]) - d(o["filled_qty"])) for o in pending_buys)
    free_cash = min(d(account["cash"]) - covered, d(account["buying_power"]))
    per_trade = d(account["equity"]) * d(size)
    if free_cash <= 0:
        print("No unreserved cash for entries.")
        return

    ranked = breakout_candidates(universe(), current.date(), previous_session)
    today_prefix = f"{ENTRY_PREFIX}{current.date():%Y%m%d}-"
    already_attempted = {o["symbol"] for o in history if o["client_order_id"].startswith(today_prefix)}
    available = [item for item in ranked if item[1] not in busy | already_attempted]
    if not available:
        print(f"Breakout {previous_session}: no new eligible stocks.")
        return
    quotes = get(DATA, "/v2/stocks/quotes/latest", feed="iex",
                 symbols=",".join(item[1] for item in available))["quotes"]
    clock = broker.request("/v2/clock")
    now = ny_timestamp(clock["timestamp"])
    if not clock["is_open"] or now.date() != current.date() or not ENTRY_START <= now.time() < ENTRY_END:
        print("Opening window ended before order submission.")
        return
    account = broker.request("/v2/account")
    if not accept_entries(account, daily_limit):
        print("Entry blocked after refreshing Alpaca account risk limits.")
        return
    free_cash = min(free_cash, d(account["cash"]) - covered, d(account["buying_power"]))
    per_trade = min(per_trade, d(account["equity"]) * d(size))
    for _, symbol, _, atr, _ in available:
        order = entry_order(symbol, atr, quotes.get(symbol), now, min(per_trade, free_cash), stop, target)
        if order is None:
            print(f"{symbol}: skipped for quote quality, price levels, or available budget.")
            continue
        # Reserve this slot even if an identical order was just submitted by a retry.
        broker.submit(order)
        busy.add(symbol)
        free_cash -= d(order["qty"]) * d(order["limit_price"])
        if len(busy) >= max_positions or free_cash <= 0:
            break


def cycle(broker, check=False):
    clock = broker.request("/v2/clock")
    current = ny_timestamp(clock["timestamp"])
    if check:
        account = broker.request("/v2/account")
        eligible = accept_entries(account, rules()[5])
        print(f"Alpaca Paper connection verified: {account['status']}. "
              f"Market open: {clock['is_open']}. Account entry gate: {eligible}.")
        return
    if not clock["is_open"]:
        next_open = ny_timestamp(clock["next_open"])
        if next_open.date() == current.date() and next_open - current <= timedelta(hours=2):
            for order in broker.orders("open"):
                if is_owned_entry(order) and ny_timestamp(order["submitted_at"]).date() < current.date():
                    broker.cancel(order["id"])
                    print(f"Pre-open cancellation requested: {order['client_order_id']}")
        print("US regular market is closed.")
        return
    config = rules()
    _, _, _, hold, _, daily_limit, _ = config
    today = current.date()
    calendar = broker.request("/v2/calendar", start=today - timedelta(days=120), end=today)
    sessions = sorted({date.fromisoformat(row["date"]) for row in calendar})
    if len(sessions) <= hold or sessions[-1] != today:
        raise RuntimeError("Alpaca session calendar does not match the market clock.")
    account = broker.request("/v2/account")
    positions = broker.request("/v2/positions")
    open_orders = broker.orders("open")
    history = broker.orders("all", after=f"{sessions[0]}T00:00:00Z", direction="desc")
    allow_entry = accept_entries(account, daily_limit)
    ready = manage_positions(broker, current, sessions, hold, history, positions, open_orders, allow_entry)
    if not ENTRY_START <= current.time() < ENTRY_END:
        return
    if not allow_entry or not ready:
        print("Entry blocked: account risk limit or pending order reconciliation.")
        return
    enter_positions(broker, current, sessions[-2], config, account, positions, open_orders, history)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the Paper API without sending orders")
    args = parser.parse_args()
    if not args.check and os.environ.get("PAPER_AUTO_ENABLED") != "true":
        raise SystemExit("Paper auto execution is disabled.")
    try:
        cycle(PaperBroker(), args.check)
    except (RuntimeError, ValueError, KeyError, TypeError, OSError) as error:
        raise SystemExit(f"Paper cycle stopped: {error}") from None


if __name__ == "__main__":
    main()
