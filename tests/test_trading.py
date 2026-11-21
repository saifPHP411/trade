import io
import runpy
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import alpaca
from backtest import COST, simulate
from signals import Bar, rules


class BacktestRiskTests(unittest.TestCase):
    def setUp(self):
        self.days = [date(2025, 5, 5) + timedelta(days=i) for i in range(4)]
        self.settings = list(rules())

    def bars(self, *values):
        return {day: Bar(day, value, value, value, value)
                for day, value in zip(self.days, values)}

    def test_opening_gap_does_not_increase_allocation_above_cap(self):
        self.settings[3] = 1
        signals = {self.days[0]: [(1, "A", 100, 5, "")]}
        prices = {"A": self.bars(100, 110, 110, 110)}
        _, trades = simulate("breakout", signals, prices, self.days, 10_000, self.settings)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].shares, 18)
        self.assertLessEqual(trades[0].shares * trades[0].entry * (1 + COST), 2_000)

    def test_fractional_replay_fits_a_ten_dollar_budget(self):
        self.settings[3] = 1
        signals = {self.days[0]: [(1, "A", 100, 5, "")]}
        prices = {"A": self.bars(100, 100, 105, 105)}
        _, whole = simulate("breakout", signals, prices, self.days, 50, self.settings)
        curve, trades = simulate("breakout", signals, prices, self.days, 50, self.settings, fractional=True)
        self.assertEqual(whole, [])
        self.assertEqual(len(trades), 1)
        trade = trades[0]
        self.assertGreater(trade.shares, 0)
        self.assertLess(trade.shares, 1)
        self.assertLessEqual(trade.shares * trade.entry * (1 + COST), 10)
        self.assertAlmostEqual(curve[-1], 50 + trade.pnl)

    def test_opening_loss_blocks_new_entry_even_if_losing_position_remains_open(self):
        self.settings[3] = 2
        signals = {
            self.days[0]: [(1, "A", 100, 15, "")],
            self.days[1]: [(1, "B", 100, 5, "")],
        }
        prices = {"A": self.bars(100, 100, 80, 80), "B": self.bars(100, 100, 100, 100)}
        curve, trades = simulate("breakout", signals, prices, self.days, 10_000, self.settings)
        self.assertEqual([trade.symbol for trade in trades], ["A"])
        self.assertEqual(trades[0].exit_day, self.days[3])
        self.assertAlmostEqual(curve[2], curve[3] + trades[0].shares * 80 * COST)


class ScannerFreshnessTests(unittest.TestCase):
    def test_calendar_uses_early_close_and_previous_session_on_weekend(self):
        friday = date(2025, 11, 28)
        calendar = [{"date": "2025-11-26", "close": "16:00"},
                    {"date": str(friday), "close": "13:00"}]
        times = [
            (datetime(2025, 11, 28, 18, 15, tzinfo=timezone.utc), date(2025, 11, 26)),
            (datetime(2025, 11, 28, 18, 16, tzinfo=timezone.utc), friday),
            (datetime(2025, 11, 29, 15, tzinfo=timezone.utc), friday),
        ]
        with patch.object(alpaca, "get", return_value=calendar):
            for now, expected in times:
                with self.subTest(now=now), patch.object(alpaca, "datetime", wraps=datetime) as clock:
                    clock.now.return_value = now
                    self.assertEqual(alpaca.completed_bar_window(), (expected, now - timedelta(minutes=16)))

    def test_calendar_filters_unfinished_bars_across_pages(self):
        completed = date(2025, 11, 28)
        cutoff = datetime(2025, 12, 1, 18, tzinfo=timezone.utc)

        def bar(day):
            return {"t": f"{day}T05:00:00Z", "o": 100, "h": 101, "l": 99, "c": 100, "v": 1000}

        pages = [
            {"bars": {"SPY": [bar("2025-12-01")]}, "next_page_token": "next"},
            {"bars": {"SPY": [bar("2025-11-28")]}, "next_page_token": None},
        ]
        with patch.object(alpaca, "get", side_effect=pages) as get:
            rows = list(alpaca.bars(["SPY"], completed, "sip", window=(completed, cutoff)))
        self.assertEqual(rows, [(completed, "SPY", 100, 101, 99, 100, 1000)])
        self.assertEqual(get.call_args.kwargs["page_token"], "next")

    def test_today_scan_skips_a_market_holiday(self):
        last_session = date(2025, 11, 26)
        holiday = datetime(2025, 11, 27, 22, tzinfo=timezone.utc)
        scanner = Path(alpaca.ROOT) / "scan.py"
        output = io.StringIO()
        with patch("datetime.datetime", wraps=datetime) as clock, \
                patch.object(alpaca, "completed_bar_window", return_value=(last_session, holiday)), \
                patch.object(alpaca, "bars") as fetch_bars, \
                patch("sys.argv", [str(scanner), "--live", "--today", "--rule", "breakout"]), \
                redirect_stdout(output):
            clock.now.return_value = holiday.astimezone(alpaca.NY)
            with self.assertRaises(SystemExit) as result:
                runpy.run_path(str(scanner), run_name="__main__")
        self.assertEqual(result.exception.code, 0)
        fetch_bars.assert_not_called()
        self.assertIn("Scan skipped", output.getvalue())

    def test_scanner_rejects_stale_data_before_printing_signals(self):
        expected = date(2025, 11, 28)
        stale = date(2025, 11, 26)
        cutoff = datetime(2025, 11, 29, tzinfo=timezone.utc)
        output = io.StringIO()
        scanner = Path(alpaca.ROOT) / "scan.py"
        with patch.object(alpaca, "completed_bar_window", return_value=(expected, cutoff)), \
                patch.object(alpaca, "bars", return_value=[(stale, "SPY", 100, 101, 99, 100, 1000)]), \
                patch("sys.argv", [str(scanner), "--live", "--rule", "breakout"]), \
                redirect_stdout(output):
            with self.assertRaisesRegex(SystemExit, r"Missing bars for expected session 2025-11-28: .*SPY"):
                runpy.run_path(str(scanner), run_name="__main__")
        self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
