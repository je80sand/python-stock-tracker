"""
stock_tracker.py
Live-price stock tracker with totals and profit/loss.

Data file: stock_data.json
Each entry:
  {
    "symbol": "AAPL",
    "shares": 3.0,
    "price": 175.25 # <-- YOUR COST BASIS per share
  }
"""

from __future__ import annotations
import json
import os
from typing import List, Dict, Any

DATA_FILE = "stock_data.json"

# ---------- Utilities ----------

def load_portfolio() -> List[Dict[str, Any]]:
    """Load holdings; return [] if file missing/empty/bad."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                # normalize keys
                for row in data:
                    row["symbol"] = str(row.get("symbol", "")).upper()
                    row["shares"] = float(row.get("shares", 0) or 0)
                    row["price"] = float(row.get("price", 0) or 0) # cost basis
                return data
    except json.JSONDecodeError:
        pass
    return []

def save_portfolio(rows: List[Dict[str, Any]]) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(rows, f, indent=2)

def find_row(rows: List[Dict[str, Any]], symbol: str) -> Dict[str, Any] | None:
    symbol = symbol.upper().strip()
    for r in rows:
        if r.get("symbol", "").upper() == symbol:
            return r
    return None

# ---------- Live price (yfinance with safe fallback) ----------

def get_live_price(symbol: str) -> float | None:
    """
    Try to fetch a live last price using yfinance.
    Returns None if it fails (no internet, invalid ticker, etc.).
    """
    try:
        import yfinance as yf # requires: pip install yfinance
    except Exception:
        return None

    symbol = symbol.upper().strip()
    try:
        t = yf.Ticker(symbol)
        # Fast path first
        fast = getattr(t, "fast_info", None)
        if fast and isinstance(fast, dict):
            lp = fast.get("lastPrice") or fast.get("last_price") or fast.get("last_price", None)
            if lp:
                return float(lp)

        # Fallback to one-day history close
        hist = t.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        return None

    return None

# ---------- Menu actions ----------

def add_stock():
    rows = load_portfolio()

    # Symbol
    sym = input("Enter symbol (e.g., AAPL): ").strip().upper()
    if not sym:
        print("No symbol entered.")
        return

    # Shares (float)
    try:
        shares = float(input("Enter shares (e.g., 3 or 3.5): ").strip())
        if shares <= 0:
            print("Shares must be > 0.")
            return
    except ValueError:
        print("Invalid shares.")
        return

    # Cost basis per share
    try:
        cost = float(input("Enter your average cost per share: ").strip())
        if cost < 0:
            print("Cost cannot be negative.")
            return
    except ValueError:
        print("Invalid cost.")
        return

    existing = find_row(rows, sym)
    if existing:
        # Re-average cost basis if adding more
        old_shares = float(existing.get("shares", 0))
        old_cost = float(existing.get("price", 0))
        new_total_shares = old_shares + shares
        if new_total_shares > 0:
            # weighted average cost
            existing["price"] = (old_shares * old_cost + shares * cost) / new_total_shares
        existing["shares"] = new_total_shares
        print(f"Updated {sym}: {existing['shares']} shares @ avg cost ${existing['price']:.2f}")
    else:
        rows.append({"symbol": sym, "shares": shares, "price": cost})
        print(f"Added {sym}: {shares} shares @ cost ${cost:.2f}")

    save_portfolio(rows)

def view_portfolio():
    rows = load_portfolio()
    if not rows:
        print("\nPortfolio is empty.")
        return

    # Fetch live prices (with cache so duplicates don't refetch)
    price_cache: Dict[str, float | None] = {}

    print("\nYour Portfolio:")
    print("-" * 78)
    print(f"{'Symbol':<8} {'Shares':>10} {'Cost/Share':>12} {'Live':>12} {'Value':>12} {'P/L':>12}")
    print("-" * 78)

    grand_value = 0.0
    grand_cost = 0.0

    for r in rows:
        sym = r.get("symbol", "").upper()
        sh = float(r.get("shares", 0))
        cost = float(r.get("price", 0)) # cost basis

        if sym not in price_cache:
            price_cache[sym] = get_live_price(sym)
        live = price_cache[sym]

        live_display = f"${live:.2f}" if isinstance(live, (float, int)) else "n/a"
        value = (live or 0) * sh
        pl = value - (cost * sh)

        grand_value += value
        grand_cost += (cost * sh)

        print(f"{sym:<8} {sh:>10.2f} ${cost:>11.2f} {live_display:>12} ${value:>11.2f} ${pl:>11.2f}")

    print("-" * 78)
    print(f"{'TOTALS':<8} {'':>10} {'':>12} {'':>12} ${grand_value:>11.2f} ${grand_value - grand_cost:>11.2f}")
    if grand_value and grand_cost:
        change_pct = (grand_value - grand_cost) / grand_cost * 100
        print(f"Portfolio Change vs Cost Basis: {change_pct:+.2f}%")
    print()

# ---------- Main loop ----------

def main():
    while True:
        print("📈 Stock Tracker Menu:")
        print("1. Add Stock")
        print("2. View Portfolio (live prices)")
        print("3. Exit")
        choice = input("Choose an option (1–3): ").strip()

        if choice == "1":
            add_stock()
        elif choice == "2":
            view_portfolio()
        elif choice == "3":
            print("Goodbye, Jose! Stay invested 💼")
            break
        else:
            print("Invalid choice. Please select 1–3.\n")

if __name__ == "__main__":
    main()