import unittest
from datetime import date, timedelta

from research.selective_breakout import market_breadth
from signals import Bar


class MarketBreadthTests(unittest.TestCase):
    def test_breadth_waits_for_data_on_all_symbols_and_ignores_future_bars(self):
        first = date(2025, 5, 5)
        days = [first + timedelta(days=i) for i in range(4)]

        def bars(values):
            return {day: Bar(day, price, price, price, price)
                    for day, price in zip(days, values)
                    if price is not None}

        prices = {"A": bars([100, 101, 102, 1]), "B": bars([None, 100, 99, 999])}
        value = market_breadth(prices, ["A", "B"], window=2)
        self.assertNotIn(days[1], value)
        self.assertEqual(value[days[2]], 0.5)
        for history in prices.values():
            history.pop(days[3])
        self.assertEqual(market_breadth(prices, ["A", "B"], window=2)[days[2]], value[days[2]])
