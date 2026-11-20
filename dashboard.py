"""Password-protected, read-only dashboard for the Alpaca Paper account."""
import base64
import binascii
import hmac
import json
import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from alpaca import PAPER, get

UI = Path(__file__).with_name("dashboard_ui")
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}
PERIODS = {"1W", "1M", "3M"}
CACHE = {}
CACHE_LOCK = threading.Lock()


def select_fields(fields):
    return lambda row: {key: row.get(key) for key in fields.split()}


def history_points(history):
    timestamps = history["timestamp"]
    equity = history["equity"]
    pnl = history.get("profit_loss") or [None] * len(timestamps)
    if len(timestamps) != len(equity) or len(timestamps) != len(pnl):
        raise ValueError("Unexpected portfolio history shape")
    return [
        {"time": ts, "equity": value,
         "pnl": net if isinstance(net, (int, float)) and math.isfinite(net) else None}
        for ts, value, net in zip(timestamps, equity, pnl)
        if isinstance(ts, int) and isinstance(value, (int, float)) and math.isfinite(value)
    ]


def read_section(path, params, convert):
    try:
        return convert(get(PAPER, path, **params)), False
    except (SystemExit, OSError, ValueError, KeyError, TypeError, AttributeError):
        return None, True


def snapshot(period):
    requests = {
        "account": ("/v2/account", {}, select_fields("status equity last_equity cash buying_power")),
        "equity": ("/v2/account/portfolio/history", {"period": period, "timeframe": "1D"}, history_points),
        "positions": ("/v2/positions", {}, lambda rows: list(map(
            select_fields("symbol side qty avg_entry_price current_price market_value unrealized_pl unrealized_plpc"),
            rows,
        ))),
        "fills": ("/v2/account/activities/FILL", {"direction": "desc", "page_size": 50}, lambda rows: list(map(
            select_fields("symbol side qty price transaction_time"), rows,
        ))),
        "orders": ("/v2/orders", {"status": "open", "limit": 50}, lambda rows: list(map(
            select_fields("symbol side qty type status limit_price stop_price submitted_at"), rows,
        ))),
    }
    with CACHE_LOCK:
        cached = CACHE.get(period)
        if cached and time.monotonic() - cached[0] < 20:
            return cached[1]
        with ThreadPoolExecutor(max_workers=len(requests)) as pool:
            futures = {name: pool.submit(read_section, *request) for name, request in requests.items()}
            results = {name: future.result() for name, future in futures.items()}
        data = {name: result[0] for name, result in results.items()}
        data["unavailable"] = [name for name, result in results.items() if result[1]]
        data["asOf"] = datetime.now(timezone.utc).isoformat()
        CACHE[period] = time.monotonic(), data
        return data


class DashboardHandler(BaseHTTPRequestHandler):
    def reply(self, status, body, mime="text/plain; charset=utf-8", challenge=False):
        self.send_response(status)
        if challenge:
            self.send_header("WWW-Authenticate", 'Basic realm="Alpaca Paper Dashboard", charset="UTF-8"')
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def log_request(self, code="-", size="-"):
        self.log_message("%s %s", self.command, code)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/health":
            self.reply(200, b"ok")
            return
        password = os.environ.get("DASHBOARD_PASSWORD", "")
        if not password:
            self.reply(503, b"Dashboard authentication is not configured.")
            return
        expected = f"paper:{password}".encode()
        scheme, _, encoded = self.headers.get("Authorization", "").partition(" ")
        try:
            supplied = base64.b64decode(encoded, validate=True) if scheme.lower() == "basic" else b""
        except (ValueError, binascii.Error):
            supplied = b""
        if not hmac.compare_digest(expected, supplied):
            self.reply(401, b"Sign in with your dashboard credentials.", challenge=True)
            return
        if url.path == "/api/portfolio":
            period = parse_qs(url.query).get("period", ["1M"])[0]
            if period not in PERIODS:
                self.reply(400, b"Invalid period.")
                return
            self.reply(200, json.dumps(snapshot(period), allow_nan=False).encode(), "application/json")
        elif url.path in STATIC:
            filename, mime = STATIC[url.path]
            self.reply(200, (UI / filename).read_bytes(), mime)
        else:
            self.reply(404, b"Not found.")


def log_broker_status():
    unavailable = snapshot("1M")["unavailable"]
    if unavailable:
        print("Alpaca Paper unavailable sections: " + ", ".join(unavailable), flush=True)
    else:
        print("Alpaca Paper verified: account, equity history, positions, fills, and open orders.", flush=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"Paper dashboard is listening on port {port}.", flush=True)
    if os.environ.get("DASHBOARD_PASSWORD"):
        threading.Thread(target=log_broker_status, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", port), DashboardHandler).serve_forever()
