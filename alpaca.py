"""Alpaca paper account and market data. HTTP calls are GET-only."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
NY = ZoneInfo("America/New_York")
PAPER = "https://paper-api.alpaca.markets"
DATA = "https://data.alpaca.markets"
KEYS = ("ALPACA_API_KEY", "ALPACA_SECRET_KEY")


def credentials():
    values = {key: os.environ.get(key) for key in KEYS}
    env_file = ROOT / ".env"
    if not all(values.values()) and env_file.exists():
        for line in env_file.read_text().splitlines():
            key, _, value = line.partition("=")
            key = key.strip()
            if key in values and not values[key]:
                values[key] = value.strip().strip("\"'")
    if any(not value or value.startswith("paste-your-") for value in values.values()):
        raise SystemExit("Set both Alpaca paper credentials privately in .env or environment variables.")
    return values


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def get(host, path, **params):
    keys = credentials()
    url = host + path
    if params:
        url += "?" + urlencode(params)
    req = Request(url, headers=dict(zip(("APCA-API-KEY-ID", "APCA-API-SECRET-KEY"), keys.values())))
    try:
        with build_opener(NoRedirect()).open(req, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        raise SystemExit(f"Alpaca returned HTTP {exc.code} for {path}.") from None
    except OSError as exc:
        raise SystemExit(f"Could not reach Alpaca for {path}: {exc.reason if hasattr(exc, 'reason') else type(exc).__name__}") from None


def completed_bar_window():
    now = datetime.now(timezone.utc)
    today = now.astimezone(NY).date()
    cutoff = now - timedelta(minutes=16)
    calendar = get(PAPER, "/v2/calendar", start=today - timedelta(days=14), end=today)
    closes = (
        datetime.fromisoformat(f"{session['date']}T{session['close']}").replace(tzinfo=NY)
        for session in calendar
    )
    latest = max((close for close in closes if close <= cutoff), default=None)
    if latest is None:
        raise SystemExit("Alpaca calendar returned no recently completed sessions.")
    return latest.date(), cutoff


def bars(symbols, start, feed, *, window=None):
    completed_day, end = window if window is not None else completed_bar_window()
    params = dict(symbols=",".join(symbols), timeframe="1Day", start=start,
                  end=end.isoformat(), adjustment="all", feed=feed, limit=10000)
    while True:
        page = get(DATA, "/v2/stocks/bars", **params)
        for symbol, rows in (page["bars"] or {}).items():
            for row in rows:
                day = datetime.fromisoformat(row["t"]).astimezone(NY).date()
                if day <= completed_day:
                    yield (day, symbol, *(row[key] for key in ("o", "h", "l", "c", "v")))
        token = page.get("next_page_token")
        if not token:
            break
        params["page_token"] = token


if __name__ == "__main__":
    if sys.argv[1:] == ["mcp"]:
        env = {**os.environ, **credentials(), "ALPACA_PAPER_TRADE": "true"}
        os.chdir(ROOT)
        os.execvpe("uvx", ["uvx", "alpaca-mcp-server"], env)
    if sys.argv[1:] != ["check"]:
        raise SystemExit("Usage: python3 alpaca.py check")
    account = get(PAPER, "/v2/account")
    positions = get(PAPER, "/v2/positions")
    orders = get(PAPER, "/v2/orders", status="open", nested="true", limit=500)
    print(json.dumps({
        "environment": "Alpaca paper",
        "status": account["status"],
        "cash": account["cash"],
        "equity": account["equity"],
        "positions": [{k: p[k] for k in ("symbol", "qty", "side")} for p in positions],
        "open_orders": [{k: o[k] for k in ("symbol", "qty", "side", "status")} for o in orders],
    }, indent=2))
