import unittest
from datetime import date, timedelta

from research.backtest_100 import run
from signals import Bar, rules


class IsolatedExposureTests(unittest.TestCase):
    def test_stop_gate_skips_a_trade_where_liquidation_would_come_first(self):
        first = date(2025, 10, 1)
        next_day = first + timedelta(days=1)
        prices = {"TEST": {next_day: Bar(next_day, 100, 101, 99, 100)}}
        signals = {first: [(1, "TEST", 100, 1, "breakout")]}
        gate = run(prices, signals, [first, next_day], 50, rules(), 0.0015, 1.0, True)
        self.assertEqual(gate["rejected_stop_inside_liquidation"], 1)
        self.assertEqual(gate["ending_usd"], 50)
        control = run(prices, signals, [first, next_day], 50, rules(), 0.0015, 1.0, False)
        self.assertEqual(control["liquidations"], 1)
        self.assertEqual(control["ending_usd"], 0)

    def test_fees_can_leave_no_initial_room_above_liquidation(self):
        first = date(2025, 10, 1)
        next_day = first + timedelta(days=1)
        prices = {"TEST": {next_day: Bar(next_day, 100, 101, 99, 100)}}
        signals = {first: [(1, "TEST", 100, 1, "breakout")]}
        result = run(prices, signals, [first, next_day], 50, rules(), 0.003, 0.05, False)
        self.assertEqual(result["rejected_no_margin_room"], 1)
        self.assertEqual(result["entries"], 0)
