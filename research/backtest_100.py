"""Stress-test hypothetical 100x isolated long exposure on daily stock bars."""
import math
from dataclasses import dataclass

LEVERAGE = 100
ASSUMED_MAINTENANCE = 0.005
BORROW_APR = 0.065
MIN_NOTIONAL_USD = 1


@dataclass
class Position:
    symbol: str
    opened: int
    entry: float
    quantity: float
    margin: float
    stop: float
    target: float
    interest: float = 0.0

    def liquidation(self, fee):
        equity_excluding_market_value = self.margin - self.quantity * self.entry * (1 + fee) - self.interest
        return -equity_excluding_market_value / (self.quantity * (1 - ASSUMED_MAINTENANCE - fee))

    def value(self, price, fee):
        trading_pnl = self.quantity * (price * (1 - fee) - self.entry * (1 + fee))
        return max(0, self.margin + trading_pnl - self.interest)


def exit_price(position, bar, fee, expired):
    liquidation = position.liquidation(fee)
    if bar.open <= liquidation:
        return None, "liquidation"
    if expired or bar.open <= position.stop or bar.open >= position.target:
        return bar.open, "regular"
    if liquidation >= position.stop and bar.low <= liquidation:
        return None, "liquidation"
    if bar.low <= position.stop:
        return position.stop, "regular"
    if bar.high >= position.target:
        return position.target, "regular"
    return None, None


def run(prices, signals, sessions, starting_cash, settings, fee, collateral_fraction, selective):
    _, stop_multiple, target_multiple, max_hold, _, loss_limit, _ = settings
    cash = previous_equity = peak = starting_cash
    position = None
    closed = wins = liquidations = entries = rejected = zero_room = 0
    drawdown = 0.0
    first_double = None
    pending = []
    for index, day in enumerate(sessions):
        margin = cash * collateral_fraction
        if position is None and margin * LEVERAGE >= MIN_NOTIONAL_USD:
            for _, symbol, _, atr, _ in pending:
                entry = prices[symbol][day].open
                units = margin * LEVERAGE / entry
                candidate = Position(symbol, index, entry, units, margin,
                                     entry - stop_multiple * atr, entry + target_multiple * atr)
                liq = candidate.liquidation(fee)
                if liq >= entry or not math.isfinite(liq):
                    zero_room += 1
                    continue
                if selective and (candidate.stop <= liq or candidate.stop <= 0):
                    rejected += 1
                    continue
                position = candidate
                cash -= margin
                entries += 1
                break
        if position is not None:
            bar = prices[position.symbol][day]
            if index > position.opened:
                debit = position.quantity * position.entry - position.margin
                position.interest += debit * BORROW_APR * (day - sessions[index - 1]).days / 360
            price, reason = exit_price(position, bar, fee, index - position.opened >= max_hold)
            if reason is not None:
                returned = 0 if price is None else position.value(price, fee)
                cash += returned
                wins += returned > position.margin
                closed += 1
                liquidations += reason == "liquidation"
                position = None

        equity = cash
        if position is not None:
            equity += position.value(prices[position.symbol][day].close, fee)
        peak = max(peak, equity)
        drawdown = min(drawdown, equity / peak - 1)
        if equity >= starting_cash * 2 and first_double is None:
            first_double = str(day)
        pending = signals.get(day, []) if equity > previous_equity * (1 - loss_limit) else []
        previous_equity = equity
    return {"ending_usd": round(equity, 4), "max_drawdown_pct": round(100 * drawdown, 2),
            "entries": entries, "closed_trades": closed, "wins": wins, "liquidations": liquidations,
            "rejected_stop_inside_liquidation": rejected, "rejected_no_margin_room": zero_room,
            "first_double": first_double}


def stress_rows(prices, signals, sessions, recent, starting_cash, settings):
    return [
        {"period": name, "fee_bps_each_side": bps, "collateral_pct": round(100 * margin),
         "protective_gate": selective, **run(prices, signals, days, starting_cash, settings,
                                            bps / 10_000, margin, selective)}
        for name, days in (("full", sessions), ("recent", recent))
        for bps in (5, 15, 30)
        for margin, selective in ((0.05, False), (0.05, True), (1.0, False))
    ]
