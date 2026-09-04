"""
LangGraph tool definitions for the PrismAI assistant.

All tools call the existing service layer — no direct exchange/Binance API calls here.
Every tool:
  1. Extracts user_id and db from the LangGraph config (injected by the graph)
  2. Loads the User object from DB for service call compatibility
  3. Calls the exact existing service method (no new methods invented)
  4. Returns a clean natural-language string the LLM can reason about
  5. Never returns raw credentials, encrypted blobs, or internal UUIDs

On failure, tools return a user-safe error message string rather than raising,
so the LLM can relay the issue gracefully.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from sqlalchemy import select


# ── Tool error sentinel ───────────────────────────────────────────────────────

class ToolError(Exception):
    """Raised by tools to signal a user-safe error message."""


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _load_user(db, user_id: str):
    """Load User row from DB. Raises ToolError if not found."""
    from app.models.user import User
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ToolError("User account not found.")
    return user


def _normalize_symbol(symbol: str) -> str:
    sym = symbol.upper().strip().replace("/", "").replace("-", "")
    known_quotes = ("USDT", "USDC", "FDUSD", "BUSD", "EUR", "TRY")
    if any(sym.endswith(q) for q in known_quotes):
        return sym
    if len(sym) > 4 and any(sym.endswith(q) for q in ("BTC", "ETH", "BNB")):
        return sym
    return sym + "USDT"


# ── Tools ─────────────────────────────────────────────────────────────────────

# Stablecoins priced at 1:1 USD — no ticker lookup needed.
_STABLECOINS = frozenset({"USDT", "BUSD", "USDC", "TUSD", "FDUSD"})


def _fmt_amount(amount: float) -> str:
    """Format a crypto amount for display: comma-thousands with context-appropriate decimals."""
    if amount >= 1000:
        return f"{amount:,.2f}"
    if amount >= 1:
        return f"{amount:.4f}"
    return f"{amount:.6f}"


@tool
async def get_portfolio_summary(config: RunnableConfig) -> str:
    """
    Retrieve the user's portfolio summary including top asset balances
    and estimated USD values where available.
    Use this for general portfolio questions like 'what's my portfolio?',
    'show me my holdings', or 'what's my total balance?'.
    """
    user_id: str = config["configurable"]["user_id"]
    db = config["configurable"]["db"]

    # Maximum assets to surface to the LLM. Testnet accounts have hundreds of
    # dust tokens; sending them all overflows the model context window.
    _MAX_DISPLAY = 20

    try:
        from app.services import portfolio_service
        user = await _load_user(db, user_id)
        data = await portfolio_service.get_portfolio(db, user, include_usd_valuation=True)
    except portfolio_service.NoExchangeConnectedError:
        return (
            "No exchange is connected to your account. "
            "Please connect an exchange first to view your portfolio."
        )
    except ToolError as e:
        return str(e)
    except Exception:
        return "Could not retrieve portfolio data. The exchange may be temporarily unavailable."

    assets = data["assets"]
    if not assets:
        return "Your connected exchange account has no non-zero balances."

    # Sort: priced assets (descending USD value) first, unpriced after.
    valued = sorted(
        [b for b in assets if b.estimated_usd_value is not None],
        key=lambda b: b.estimated_usd_value,
        reverse=True,
    )
    unvalued = [b for b in assets if b.estimated_usd_value is None]
    display = (valued + unvalued)[:_MAX_DISPLAY]
    hidden = len(assets) - len(display)

    # Pre-calculate total and allocation percentages from priced display assets.
    total_usd = sum(float(b.estimated_usd_value) for b in valued if b in set(display))
    # Fallback: include all valued assets' sum even if truncated
    if not total_usd:
        total_usd = sum(float(b.estimated_usd_value) for b in valued)

    # ── Portfolio Summary section ──────────────────────────────────────────────
    lines = ["Portfolio Summary", ""]
    for b in display:
        total = float(b.free + b.locked)
        lines.append(f"{b.asset}: {_fmt_amount(total)} {b.asset}")
    if hidden > 0:
        lines.append(f"(and {hidden} more assets not shown)")

    # ── Total Value ───────────────────────────────────────────────────────────
    lines.append("")
    if total_usd > 0:
        lines.append(f"Total Value: ${total_usd:,.2f} USDT")
    else:
        lines.append("Total Value: unavailable")

    # ── Allocation ────────────────────────────────────────────────────────────
    display_valued = [b for b in display if b.estimated_usd_value is not None]
    if display_valued and total_usd > 0:
        lines.extend(["", "Allocation:"])
        for b in display_valued:
            pct = float(b.estimated_usd_value) / total_usd * 100
            lines.append(f"{b.asset}: {pct:.2f}%")

    # ── Available (free balance) ───────────────────────────────────────────────
    # Only show if any displayed asset has locked amounts.
    has_locked = any(b.locked > 0 for b in display)
    lines.extend(["", "Available:"])
    for b in display:
        free = float(b.free)
        lines.append(f"{b.asset}: {_fmt_amount(free)} {b.asset}")

    return "\n".join(lines)


@tool
async def get_asset_balance(asset: str, config: RunnableConfig) -> str:
    """
    Retrieve the balance for a specific asset (e.g. 'BTC', 'ETH', 'USDT').
    Use this when the user asks about a specific coin's holding, e.g.
    'how much BTC do I have?', 'what's my ETH balance?'.

    Args:
        asset: The asset ticker symbol, e.g. 'BTC', 'ETH', 'USDT'.
    """
    user_id: str = config["configurable"]["user_id"]
    db = config["configurable"]["db"]
    asset = asset.upper().strip()

    try:
        from app.services import portfolio_service
        user = await _load_user(db, user_id)
        data = await portfolio_service.get_portfolio(db, user, include_usd_valuation=True)
    except portfolio_service.NoExchangeConnectedError:
        return "No exchange is connected. Please connect an exchange to check your balance."
    except ToolError as e:
        return str(e)
    except Exception:
        return f"Could not retrieve balance for {asset}."

    for b in data["assets"]:
        if b.asset == asset:
            total = float(b.free + b.locked)
            free = float(b.free)
            locked = float(b.locked)
            usd = f" (~${float(b.estimated_usd_value):,.2f} USD)" if b.estimated_usd_value else ""
            lines = [
                f"{asset} Balance",
                "",
                f"Total: {_fmt_amount(total)} {asset}{usd}",
                f"Available: {_fmt_amount(free)} {asset}",
            ]
            if locked > 0:
                lines.append(f"Locked: {_fmt_amount(locked)} {asset}")
            return "\n".join(lines)

    return f"You have no {asset} holdings in your connected exchange account."


@tool
async def get_market_ticker(symbol: str, config: RunnableConfig) -> str:
    """
    Fetch the current market price and 24-hour statistics for a trading pair.
    Use this for price questions like 'what's the price of BTC?',
    'how is ETH doing today?', 'what's the 24h change for SOL?'.
    Automatically appends USDT if only a base asset is given (e.g. BTC → BTCUSDT).

    Args:
        symbol: Trading pair symbol, e.g. 'BTCUSDT' or just 'BTC'.
    """
    user_id: str = config["configurable"]["user_id"]
    db = config["configurable"]["db"]

    sym = _normalize_symbol(symbol)

    try:
        from app.services import market_service
        user = await _load_user(db, user_id)
        ticker = await market_service.get_ticker(db, user, sym)
    except market_service.NoExchangeConnectedError:
        return "No exchange is connected. Please connect an exchange to get live market data."
    except ToolError as e:
        return str(e)
    except Exception:
        return f"Could not retrieve price data for {sym}. The symbol may not exist or the exchange is unavailable."

    change_sign = "+" if ticker.change_24h_pct >= 0 else ""
    return (
        f"{ticker.symbol} current price: {float(ticker.price):,.4f} {ticker.quote_asset}\n"
        f"24h change: {change_sign}{float(ticker.change_24h_pct):.2f}%\n"
        f"24h high: {float(ticker.high_24h):,.4f} | 24h low: {float(ticker.low_24h):,.4f}\n"
        f"24h volume: {float(ticker.volume_24h):,.2f} {ticker.base_asset}"
    )


@tool
async def get_price_candles(symbol: str, interval: str, config: RunnableConfig) -> str:
    """
    Retrieve recent OHLCV candlestick data for historical price analysis.
    Use this when the user asks about price history, trends, or chart data.
    E.g. 'how has BTC moved this week?', 'show me ETH daily candles',
    'what was the price range for SOL in the last month?'.

    Args:
        symbol: Trading pair, e.g. 'BTCUSDT' or 'BTC'.
        interval: Time interval — '15m', '1h', '4h', '1d', '1w'.
    """
    user_id: str = config["configurable"]["user_id"]
    db = config["configurable"]["db"]

    sym = _normalize_symbol(symbol)

    # Validate interval; default to 1d if invalid
    valid = {"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"}
    if interval not in valid:
        interval = "1d"

    try:
        from app.services import market_service
        user = await _load_user(db, user_id)
        candles = await market_service.get_candles(db, user, sym, interval=interval, limit=14)
    except market_service.NoExchangeConnectedError:
        return "No exchange is connected. Please connect an exchange to get historical data."
    except ToolError as e:
        return str(e)
    except Exception:
        return f"Could not retrieve candle data for {sym}."

    if not candles:
        return f"No candle data available for {sym} at {interval} interval."

    first = candles[0]
    last = candles[-1]
    highs = [float(c.high) for c in candles]
    lows = [float(c.low) for c in candles]

    return (
        f"{sym} {interval} candles (last {len(candles)} periods):\n"
        f"Period open: {float(first.open):,.4f} → Period close: {float(last.close):,.4f}\n"
        f"Range high: {max(highs):,.4f} | Range low: {min(lows):,.4f}\n"
        f"Most recent candle — open: {float(last.open):,.4f}, close: {float(last.close):,.4f}, "
        f"high: {float(last.high):,.4f}, low: {float(last.low):,.4f}"
    )


@tool
async def get_exchange_status(config: RunnableConfig) -> str:
    """
    Check the user's connected exchange status and last sync time.
    Use this when the user asks about their exchange connection, e.g.
    'is my Binance connected?', 'when was my exchange last synced?'.
    """
    user_id: str = config["configurable"]["user_id"]
    db = config["configurable"]["db"]

    try:
        from app.services import exchange_service
        user = await _load_user(db, user_id)
        exchanges = await exchange_service.list_exchanges(db, user)
    except ToolError as e:
        return str(e)
    except Exception:
        return "Could not retrieve exchange connection information."

    if not exchanges:
        return "You have no connected exchanges. Go to the Exchanges page to connect one."

    lines = []
    for ex in exchanges:
        last_sync = ex.last_synced_at.strftime("%Y-%m-%d %H:%M UTC") if ex.last_synced_at else "Never"
        label = ex.display_label or ex.exchange_name.capitalize()
        lines.append(f"• {label}: Active, last synced {last_sync}")

    return "Connected exchanges:\n" + "\n".join(lines)


@tool
async def get_user_watchlists(config: RunnableConfig) -> str:
    """
    Retrieve the user's saved crypto watchlists and tracked coins, along with
    live market prices and 24-hour performance where available.
    Use this when the user asks about their watchlists, tracked coins, or
    market performance of the assets they are watching (e.g. 'what's on my watchlist?',
    'show my watched coins', 'how are the coins on my watchlist doing?').
    """
    user_id: str = config["configurable"]["user_id"]
    db = config["configurable"]["db"]

    try:
        from app.services import watchlist_service
        user = await _load_user(db, user_id)
        watchlists = await watchlist_service.list_watchlists(db, user)
    except ToolError as e:
        return str(e)
    except Exception:
        return "Could not retrieve watchlist information."

    if not watchlists:
        return "You don't have any watchlists yet. You can create one on the Watchlists page."

    output_lines = []
    for wl in watchlists:
        try:
            detail = await watchlist_service.get_watchlist(
                db, user, wl["id"], enrich_market_data=True
            )
            items = detail["items"]
            header = f"Watchlist '{detail['name']}' ({len(items)} items):"
            output_lines.append(header)
            if not items:
                output_lines.append("  (No symbols added to this watchlist yet)")
            else:
                for item in items:
                    sym = item["symbol"]
                    if item["price"] is not None:
                        price_str = f"${float(item['price']):,.4f}"
                        chg = float(item["change_24h_pct"]) if item["change_24h_pct"] is not None else 0.0
                        chg_sign = "+" if chg >= 0 else ""
                        output_lines.append(f"  • {sym}: {price_str} ({chg_sign}{chg:.2f}% 24h)")
                    else:
                        output_lines.append(f"  • {sym}")
        except Exception:
            output_lines.append(f"Watchlist '{wl['name']}': (details temporarily unavailable)")

    return "\n".join(output_lines)


@tool
async def get_user_alerts(config: RunnableConfig) -> str:
    """
    Retrieve the user's price and condition alerts, including current active status,
    target price thresholds, trigger history, and distance to target based on live market prices.
    Use this when the user asks about their price alerts, notifications, or threshold triggers
    (e.g. 'do I have any alerts set?', 'what are my price alerts for BTC?', 'did any of my alerts trigger?').
    """
    user_id: str = config["configurable"]["user_id"]
    db = config["configurable"]["db"]

    try:
        from app.services import alert_service
        user = await _load_user(db, user_id)
        alerts = await alert_service.list_alerts(db, user, enrich_market_data=True)
    except ToolError as e:
        return str(e)
    except Exception:
        return "Could not retrieve alert information."

    if not alerts:
        return "You have no price alerts configured. You can set alerts on the Alerts page."

    lines = [f"Your Price Alerts ({len(alerts)} total):"]
    for a in alerts:
        sym = a["symbol"]
        cond_sym = "≥" if a["condition"] == "above" else "≤"
        target_str = f"${float(a['target_price']):,.4f}"
        status_tag = a["status"].upper()

        detail_parts = [f"• {sym} ({cond_sym} {target_str}) — [{status_tag}]"]

        if a["status"] == "triggered" and a["triggered_price"] is not None:
            trig_p = f"${float(a['triggered_price']):,.4f}"
            trig_t = a["triggered_at"].strftime("%Y-%m-%d %H:%M UTC") if a.get("triggered_at") else ""
            detail_parts.append(f"    Triggered at {trig_p} on {trig_t}")
        elif a["current_price"] is not None:
            curr_p = f"${float(a['current_price']):,.4f}"
            dist_p = float(a["distance_pct"]) if a["distance_pct"] is not None else 0.0
            dist_sign = "+" if dist_p >= 0 else ""
            detail_parts.append(f"    Current price: {curr_p} ({dist_sign}{dist_p:.2f}% to target)")
        else:
            detail_parts.append("    (Live exchange quote unavailable)")

        if a.get("notes"):
            detail_parts.append(f"    Notes: {a['notes']}")

        lines.append("\n".join(detail_parts))

    return "\n".join(lines)


@tool
async def get_saved_analyses(
    symbol: str = "",
    config: RunnableConfig = None,
) -> str:
    """
    Retrieve the user's saved AI intelligence and technical analysis reports,
    including the standardized assessment (Buy Gradually, Hold, Consider Selling, Insufficient Context),
    risk level, key price levels (support, resistance, target, stop loss), and summary.
    Optionally filter by crypto symbol (e.g. 'BTC', 'ETHUSDT').
    Use this when the user asks to review previous analyses, check past reports, or see what
    the system previously assessed for a coin (e.g. 'what was my last analysis on Bitcoin?',
    'show my saved reports', 'do I have any Buy assessments?').
    """
    user_id: str = config["configurable"]["user_id"]
    db = config["configurable"]["db"]

    try:
        from app.services import analysis_service
        user = await _load_user(db, user_id)
        reports = await analysis_service.list_analyses(
            db=db,
            user=user,
            symbol_filter=symbol.strip().upper() if symbol.strip() else None,
            limit=5,
        )
    except ToolError as e:
        return str(e)
    except Exception:
        return "Could not retrieve analysis reports."

    if not reports:
        if symbol.strip():
            return f"No saved analysis reports found for {symbol.upper()}. You can generate one on the AI Reports page."
        return "You have no saved analysis reports yet. You can generate new AI reports on the AI Reports page."

    lines = [f"Saved AI Analysis Reports ({len(reports)} found):"]
    for r in reports:
        sym = r.symbol
        assess = r.assessment
        risk = r.risk_level
        price = f"${float(r.market_price):,.4f}"
        date_str = r.created_at.strftime("%Y-%m-%d %H:%M UTC") if r.created_at else ""

        report_lines = [
            f"• {sym} ({r.timeframe}) — Assessment: [{assess.upper()}] | Risk: {risk} | Price at analysis: {price} ({date_str})",
            f"  Summary: {r.summary}",
        ]

        if r.key_price_levels:
            lvl = r.key_price_levels
            levels_str = []
            if lvl.get("support") is not None:
                levels_str.append(f"Support: ${float(lvl['support']):,.2f}")
            if lvl.get("resistance") is not None:
                levels_str.append(f"Resistance: ${float(lvl['resistance']):,.2f}")
            if lvl.get("target") is not None:
                levels_str.append(f"Target: ${float(lvl['target']):,.2f}")
            if lvl.get("stop_loss") is not None:
                levels_str.append(f"Stop Loss: ${float(lvl['stop_loss']):,.2f}")
            if levels_str:
                report_lines.append(f"  Key Levels: {', '.join(levels_str)}")

        lines.append("\n".join(report_lines))

    return "\n".join(lines)


@tool
async def get_user_complaints(config: RunnableConfig) -> str:
    """
    Retrieve the user's submitted support tickets and complaints, including their
    current resolution status (open, in_progress, resolved, closed), priority, category,
    and message counts.
    Use this when the user asks about their support tickets, complaints, or issue status
    (e.g. 'what is the status of my support ticket?', 'show my complaints', 'did support answer my issue?').
    """
    user_id: str = config["configurable"]["user_id"]
    db = config["configurable"]["db"]

    try:
        from app.services import complaint_service
        user = await _load_user(db, user_id)
        complaints = await complaint_service.list_complaints(db, user)
    except ToolError as e:
        return str(e)
    except Exception:
        return "Could not retrieve support ticket information."

    if not complaints:
        return "You have not submitted any support tickets or complaints yet. You can submit one on the Support Portal page."

    lines = [f"Your Support Tickets & Complaints ({len(complaints)} total):"]
    for c in complaints:
        status_tag = c["status"].upper()
        prio_tag = c["priority"].capitalize()
        cat = c["category"]
        subj = c["subject"]
        date_str = c["created_at"].strftime("%Y-%m-%d") if c.get("created_at") else ""
        msg_count = c.get("message_count", 0)

        lines.append(
            f"• [{status_tag}] {subj} (Category: {cat}, Priority: {prio_tag}, {msg_count} messages, Submitted: {date_str})"
        )
        if c.get("resolution_notes"):
            lines.append(f"    Resolution: {c['resolution_notes']}")

    return "\n".join(lines)


# ── Tool registry ─────────────────────────────────────────────────────────────

ALL_TOOLS = [
    get_portfolio_summary,
    get_asset_balance,
    get_market_ticker,
    get_price_candles,
    get_exchange_status,
    get_user_watchlists,
    get_user_alerts,
    get_saved_analyses,
    get_user_complaints,
]
