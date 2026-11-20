import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from alpaca import NY
from paper_auto import PaperBroker, accept_entries, cycle, entry_order, manage_positions


class PaperAutoTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 23, 9, 38, tzinfo=NY)
        self.account = {"equity": "10000", "last_equity": "10000", "cash": "10000",
                        "status": "ACTIVE", "trading_blocked": False, "account_blocked": False}

    def test_whole_share_cash_budget_and_protective_prices(self):
        order = entry_order("AAPL", 2, {"ap": "100.001", "bp": "100", "t": self.now.isoformat()},
                            self.now, Decimal("2000"), 2, 4)
        self.assertEqual(order["qty"], "19")
        self.assertEqual(order["order_class"], "bracket")
        self.assertEqual(order["stop_loss"]["stop_price"], "96.01")
        self.assertEqual(order["take_profit"]["limit_price"], "108.01")
        self.assertLessEqual(Decimal(order["limit_price"]) * int(order["qty"]), 2000)

    def test_rejects_old_or_wide_quote(self):
        for quote in [
            {"ap": "100", "bp": "100", "t": "2026-11-23T09:30:00-05:00"},
            {"ap": "100", "bp": "99", "t": self.now.isoformat()},
        ]:
            self.assertIsNone(entry_order("AAPL", 2, quote, self.now, Decimal("2000"), 2, 4))

    def test_blocks_at_daily_loss_threshold(self):
        self.assertTrue(accept_entries(self.account, 0.03))
        self.account["equity"] = "9700"
        self.assertFalse(accept_entries(self.account, 0.03))

    def test_cycle_uses_last_session_signal_and_respects_account_cap(self):
        broker = Mock(spec=PaperBroker)
        clock = {"timestamp": self.now.isoformat(), "is_open": True}
        dates = [self.now.date() - timedelta(days=i) for i in range(65)
                 if (self.now.date() - timedelta(days=i)).weekday() < 5]
        positions = [{"symbol": f"MANUAL{i}", "side": "long"} for i in range(4)]
        self.account["buying_power"] = "20000"
        broker.request.side_effect = lambda path, **kwargs: {
            "/v2/clock": clock, "/v2/calendar": [{"date": str(day)} for day in dates],
            "/v2/account": self.account, "/v2/positions": positions,
        }[path]
        broker.orders.return_value = []
        signals = [(1, "AAPL", 100, 2, ""), (0, "MSFT", 100, 2, "")]
        quote = {"ap": "110", "bp": "109.99", "t": self.now.isoformat()}
        with patch("paper_auto.breakout_candidates", return_value=signals) as scan, \
                patch("paper_auto.get", return_value={"quotes": {"AAPL": quote, "MSFT": quote}}):
            cycle(broker)
        self.assertEqual(scan.call_args.args[2], date(2026, 11, 20))
        broker.submit.assert_called_once()
        order = broker.submit.call_args.args[0]
        self.assertEqual(order["qty"], "18")
        self.assertEqual(order["client_order_id"], "trade-paper-entry-20261123-AAPL")

    def test_existing_client_id_prevents_duplicate_submission(self):
        broker = Mock(spec=PaperBroker)
        broker.order_by_client_id.return_value = {"status": "filled"}
        self.assertFalse(PaperBroker.submit(broker, {"client_order_id": "already-seen"}))
        broker.request.assert_not_called()

    def test_read_only_check_uses_only_paper_clock_and_account(self):
        broker = Mock(spec=PaperBroker)
        broker.request.side_effect = [{"timestamp": self.now.isoformat(), "is_open": False}, self.account]
        cycle(broker, check=True)
        self.assertEqual([call.args for call in broker.request.call_args_list], [("/v2/clock",), ("/v2/account",)])
        broker.submit.assert_not_called()

    def test_incomplete_bracket_close_waits_for_protection_cancel(self):
        broker = Mock(spec=PaperBroker)
        leg = {"id": "stop-1", "side": "sell", "symbol": "AAPL", "type": "stop",
               "filled_qty": "0", "status": "new"}
        parent = {"id": "entry-1", "side": "buy", "symbol": "AAPL", "status": "filled",
                  "filled_qty": "3", "client_order_id": "trade-paper-entry-20261120-AAPL",
                  "submitted_at": "2026-11-20T09:38:00-05:00", "legs": [leg]}
        position = {"symbol": "AAPL", "side": "long", "qty": "3", "qty_available": "3"}
        broker.order.return_value = parent
        broker.request.return_value = [position]
        broker.orders.return_value = []
        sessions = [date(2026, 11, 20), self.now.date()]
        self.assertFalse(manage_positions(broker, self.now, sessions, 30, [parent], [position], [leg], True))
        broker.cancel.assert_called_once_with("stop-1")
        broker.submit.assert_not_called()
        leg["status"] = "canceled"
        self.assertFalse(manage_positions(broker, self.now, sessions, 30, [parent], [position], [], True))
        order = broker.submit.call_args.args[0]
        self.assertEqual(order["position_intent"], "sell_to_close")
        self.assertEqual(order["qty"], "3")

    def test_worker_leaves_manual_positions_alone(self):
        broker = Mock(spec=PaperBroker)
        position = {"symbol": "MSFT", "side": "long", "qty": "3"}
        self.assertTrue(manage_positions(broker, self.now, [self.now.date()], 30, [], [position], [], True))
        broker.order.assert_not_called()
        broker.cancel.assert_not_called()
        broker.submit.assert_not_called()

    def test_disabled_worker_exits_before_creating_an_api_client(self):
        with patch.dict("os.environ", {"PAPER_AUTO_ENABLED": "false"}), patch("sys.argv", ["paper_auto.py"]), \
                patch("paper_auto.PaperBroker") as broker:
            from paper_auto import main
            with self.assertRaisesRegex(SystemExit, "disabled"):
                main()
        broker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
