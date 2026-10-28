"""SQLite persistence layer for Lumen — the personal expense tracker.

All data lives in a single local SQLite file (``data/lumen.db``) so it
survives restarts. Every public function opens a short-lived connection,
which keeps things simple and safe with Streamlit's rerun model.
Supports multi-user data isolation.
"""

from __future__ import annotations

import json
import random
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent / "data" / "lumen.db"

PAYMENT_METHODS = ["Card", "Cash", "UPI / Wallet", "Bank Transfer", "Other"]
FREQUENCIES = ["Weekly", "Monthly", "Yearly"]

# (name, type, emoji, color)
DEFAULT_CATEGORIES = [
    ("Food & Dining", "Expense", "🍔", "#FF8A65"),
    ("Groceries", "Expense", "🛒", "#AED581"),
    ("Transport", "Expense", "🚗", "#4FC3F7"),
    ("Shopping", "Expense", "🛍️", "#F06292"),
    ("Bills & Utilities", "Expense", "💡", "#FFD54F"),
    ("Rent & Housing", "Expense", "🏠", "#9575CD"),
    ("Entertainment", "Expense", "🎬", "#BA68C8"),
    ("Health", "Expense", "💊", "#4DB6AC"),
    ("Travel", "Expense", "✈️", "#7986CB"),
    ("Education", "Expense", "📚", "#64B5F6"),
    ("Subscriptions", "Expense", "📺", "#E57373"),
    ("Gifts & Donations", "Expense", "🎁", "#FFB74D"),
    ("Other", "Expense", "📦", "#90A4AE"),
    ("Salary", "Income", "💼", "#66BB6A"),
    ("Freelance", "Income", "💻", "#26C6DA"),
    ("Investments", "Income", "📈", "#9CCC65"),
    ("Gifts Received", "Income", "🎉", "#FFCA28"),
    ("Other Income", "Income", "💰", "#8D6E63"),
]

DEFAULT_SETTINGS = {
    "theme": "Midnight",
    "last_dark_theme": "Midnight",
    "last_light_theme": "Light",
    "currency": "$",
    "user_name": "",
}

TX_COLUMNS = ["id", "date", "type", "category", "amount", "description",
              "payment_method", "tags", "created_at"]


def get_current_user_id() -> int:
    """Retrieve active user_id from session state, defaulting to 1."""
    try:
        import streamlit as st
        u = st.session_state.get("user")
        if u and "id" in u:
            return int(u["id"])
    except Exception:
        pass
    return 1


@contextmanager
def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    """Create tables, run migrations, and seed defaults (idempotent)."""
    with _conn() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                full_name TEXT DEFAULT '',
                avatar TEXT DEFAULT '👤',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                date TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('Expense','Income')),
                category TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount >= 0),
                description TEXT DEFAULT '',
                payment_method TEXT DEFAULT 'Card',
                tags TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                emoji TEXT DEFAULT '📦',
                color TEXT DEFAULT '#90A4AE',
                UNIQUE(user_id, name)
            );

            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                UNIQUE(user_id, category)
            );

            CREATE TABLE IF NOT EXISTS recurring (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                payment_method TEXT DEFAULT 'Card',
                frequency TEXT NOT NULL,
                next_date TEXT NOT NULL,
                active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                name TEXT NOT NULL,
                emoji TEXT DEFAULT '🎯',
                target REAL NOT NULL,
                saved REAL DEFAULT 0,
                deadline TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                key TEXT NOT NULL,
                value TEXT,
                UNIQUE(user_id, key)
            );
            """
        )

        # Run schema migrations to add user_id if upgrading an older schema
        for tbl in ("transactions", "categories", "budgets", "recurring", "goals", "settings"):
            cols = [r["name"] for r in con.execute(f"PRAGMA table_info({tbl})").fetchall()]
            if "user_id" not in cols:
                con.execute(f"ALTER TABLE {tbl} ADD COLUMN user_id INTEGER DEFAULT 1")

        # Migrate legacy tables that lack an 'id' primary key or had single-column primary keys (categories, budgets, settings)
        cat_cols = [r["name"] for r in con.execute("PRAGMA table_info(categories)").fetchall()]
        if "id" not in cat_cols:
            con.executescript(
                """
                CREATE TABLE categories_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER DEFAULT 1,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    emoji TEXT DEFAULT '📦',
                    color TEXT DEFAULT '#90A4AE',
                    UNIQUE(user_id, name)
                );
                INSERT OR IGNORE INTO categories_new (user_id, name, type, emoji, color)
                SELECT COALESCE(user_id, 1), name, type, emoji, color FROM categories;
                DROP TABLE categories;
                ALTER TABLE categories_new RENAME TO categories;
                """
            )

        budget_cols = [r["name"] for r in con.execute("PRAGMA table_info(budgets)").fetchall()]
        if "id" not in budget_cols:
            con.executescript(
                """
                CREATE TABLE budgets_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER DEFAULT 1,
                    category TEXT NOT NULL,
                    amount REAL NOT NULL,
                    UNIQUE(user_id, category)
                );
                INSERT OR IGNORE INTO budgets_new (user_id, category, amount)
                SELECT COALESCE(user_id, 1), category, amount FROM budgets;
                DROP TABLE budgets;
                ALTER TABLE budgets_new RENAME TO budgets;
                """
            )

        settings_cols = [r["name"] for r in con.execute("PRAGMA table_info(settings)").fetchall()]
        if "id" not in settings_cols:
            con.executescript(
                """
                CREATE TABLE settings_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER DEFAULT 1,
                    key TEXT NOT NULL,
                    value TEXT,
                    UNIQUE(user_id, key)
                );
                INSERT OR IGNORE INTO settings_new (user_id, key, value)
                SELECT COALESCE(user_id, 1), key, value FROM settings;
                DROP TABLE settings;
                ALTER TABLE settings_new RENAME TO settings;
                """
            )

        con.execute("CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id)")

        # Seed default Demo user if no users exist
        try:
            import auth
            pwd_hash, salt = auth.hash_password("demo123")
            con.execute(
                """
                INSERT OR IGNORE INTO users (id, username, email, password_hash, salt, full_name, avatar, created_at)
                VALUES (1, 'demo', 'demo@lumen.app', ?, ?, 'Demo Explorer', '✨', ?)
                """,
                (pwd_hash, salt, datetime.now().isoformat(timespec="seconds")),
            )
        except Exception:
            pass

        # Seed categories & settings for all existing users if missing
        user_rows = con.execute("SELECT id FROM users").fetchall()
        for u_row in user_rows:
            uid = u_row["id"]
            if con.execute("SELECT COUNT(*) FROM categories WHERE user_id = ?", (uid,)).fetchone()[0] == 0:
                con.executemany(
                    "INSERT OR IGNORE INTO categories(name, type, emoji, color, user_id) VALUES (?,?,?,?,?)",
                    [(*c, uid) for c in DEFAULT_CATEGORIES],
                )
            for k, v in DEFAULT_SETTINGS.items():
                con.execute(
                    "INSERT OR IGNORE INTO settings(key, value, user_id) VALUES (?,?,?)", (k, v, uid)
                )


# --------------------------------------------------------------------------- settings
def get_settings(user_id: int | None = None) -> dict:
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        rows = con.execute("SELECT key, value FROM settings WHERE user_id = ?", (uid,)).fetchall()
    out = dict(DEFAULT_SETTINGS)
    out.update({r["key"]: r["value"] for r in rows})
    return out


def set_setting(key: str, value, user_id: int | None = None) -> None:
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        existing = con.execute(
            "SELECT id FROM settings WHERE key = ? AND user_id = ?", (key, uid)
        ).fetchone()
        if existing:
            con.execute(
                "UPDATE settings SET value = ? WHERE id = ?", (str(value), existing["id"])
            )
        else:
            con.execute(
                "INSERT INTO settings(key, value, user_id) VALUES (?,?,?)",
                (key, str(value), uid),
            )


# --------------------------------------------------------------------------- categories
def get_categories(tx_type: str | None = None, user_id: int | None = None) -> pd.DataFrame:
    uid = user_id if user_id is not None else get_current_user_id()
    q = "SELECT name, type, emoji, color FROM categories WHERE user_id = ?"
    params = [uid]
    if tx_type:
        q += " AND type = ?"
        params.append(tx_type)
    with _conn() as con:
        df = pd.read_sql_query(q + " ORDER BY type DESC, name", con, params=params)
    if df.empty:
        # Fallback to default categories if not yet seeded for this user
        with _conn() as con:
            has_any = con.execute("SELECT 1 FROM categories WHERE user_id = ? LIMIT 1", (uid,)).fetchone()
            if not has_any:
                for cat, t_type, emoji, color in DEFAULT_CATEGORIES:
                    con.execute(
                        "INSERT OR IGNORE INTO categories(name, type, emoji, color, user_id) VALUES (?,?,?,?,?)",
                        (cat, t_type, emoji, color, uid),
                    )
            df = pd.read_sql_query(q + " ORDER BY type DESC, name", con, params=params)
    return df


def add_category(name: str, tx_type: str, emoji: str, color: str, user_id: int | None = None) -> bool:
    uid = user_id if user_id is not None else get_current_user_id()
    name_clean = name.strip()
    with _conn() as con:
        exists = con.execute(
            "SELECT id FROM categories WHERE name = ? AND user_id = ?", (name_clean, uid)
        ).fetchone()
        if exists:
            return False
        con.execute(
            "INSERT INTO categories(name, type, emoji, color, user_id) VALUES (?,?,?,?,?)",
            (name_clean, tx_type, emoji or "📦", color, uid),
        )
    return True


def delete_category(name: str, user_id: int | None = None) -> None:
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        con.execute("DELETE FROM categories WHERE name = ? AND user_id = ?", (name, uid))
        con.execute("DELETE FROM budgets WHERE category = ? AND user_id = ?", (name, uid))


# --------------------------------------------------------------------------- transactions
def add_transaction(d: date, tx_type: str, category: str, amount: float,
                    description: str = "", payment_method: str = "Card",
                    tags: str = "", user_id: int | None = None) -> None:
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        con.execute(
            "INSERT INTO transactions(user_id, date, type, category, amount, description, "
            "payment_method, tags, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (uid, pd.Timestamp(d).strftime("%Y-%m-%d"), tx_type, category, float(amount),
             description.strip(), payment_method, tags.strip(),
             datetime.now().isoformat(timespec="seconds")),
        )


def get_transactions(user_id: int | None = None) -> pd.DataFrame:
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        df = pd.read_sql_query(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC, id DESC",
            con,
            params=(uid,),
        )
    if df.empty:
        df = pd.DataFrame(columns=TX_COLUMNS)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    for c in ("description", "payment_method", "tags"):
        df[c] = df[c].fillna("").astype(str)
    return df


def update_transaction(tx_id: int, user_id: int | None = None, **fields) -> None:
    uid = user_id if user_id is not None else get_current_user_id()
    allowed = {"date", "type", "category", "amount", "description", "payment_method", "tags"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return
    if "date" in fields:
        fields["date"] = pd.Timestamp(fields["date"]).strftime("%Y-%m-%d")
    sets = ", ".join(f"{k} = ?" for k in fields)
    with _conn() as con:
        con.execute(
            f"UPDATE transactions SET {sets} WHERE id = ? AND user_id = ?",
            (*fields.values(), int(tx_id), uid),
        )


def delete_transactions(ids: list[int], user_id: int | None = None) -> None:
    if not ids:
        return
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        con.executemany(
            "DELETE FROM transactions WHERE id = ? AND user_id = ?",
            [(int(i), uid) for i in ids],
        )


def import_transactions(df: pd.DataFrame, user_id: int | None = None) -> int:
    """Import rows from a dataframe with at least date, type, category, amount."""
    uid = user_id if user_id is not None else get_current_user_id()
    cols = {c.lower().strip().replace(" ", "_"): c for c in df.columns}
    required = ["date", "category", "amount"]
    if any(r not in cols for r in required):
        raise ValueError("CSV must contain at least: date, category, amount (type optional).")
    count = 0
    with _conn() as con:
        known = {r["name"] for r in con.execute("SELECT name FROM categories WHERE user_id = ?", (uid,))}
        for _, row in df.iterrows():
            try:
                d = pd.to_datetime(row[cols["date"]]).strftime("%Y-%m-%d")
                amount = abs(float(row[cols["amount"]]))
            except (ValueError, TypeError):
                continue
            tx_type = str(row[cols["type"]]).strip().title() if "type" in cols else "Expense"
            if tx_type not in ("Expense", "Income"):
                tx_type = "Expense"
            category = str(row[cols["category"]]).strip() or "Other"
            if category not in known:
                con.execute(
                    "INSERT OR IGNORE INTO categories(name, type, emoji, color, user_id) VALUES (?,?,?,?,?)",
                    (category, tx_type, "🏷️", "#90A4AE", uid),
                )
                known.add(category)

            def _get(name: str, default: str = "") -> str:
                if name in cols and pd.notna(row[cols[name]]):
                    return str(row[cols[name]])
                return default

            con.execute(
                "INSERT INTO transactions(user_id, date, type, category, amount, description, "
                "payment_method, tags, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (uid, d, tx_type, category, amount, _get("description"),
                 _get("payment_method", "Card"), _get("tags"),
                 datetime.now().isoformat(timespec="seconds")),
            )
            count += 1
    return count


# --------------------------------------------------------------------------- budgets
TOTAL_BUDGET_KEY = "__TOTAL__"


def get_budgets(user_id: int | None = None) -> dict[str, float]:
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        return {r["category"]: r["amount"] for r in con.execute("SELECT * FROM budgets WHERE user_id = ?", (uid,))}


def set_budget(category: str, amount: float, user_id: int | None = None) -> None:
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        if amount and amount > 0:
            existing = con.execute(
                "SELECT id FROM budgets WHERE category = ? AND user_id = ?", (category, uid)
            ).fetchone()
            if existing:
                con.execute(
                    "UPDATE budgets SET amount = ? WHERE id = ?", (float(amount), existing["id"])
                )
            else:
                con.execute(
                    "INSERT INTO budgets(category, amount, user_id) VALUES (?,?,?)",
                    (category, float(amount), uid),
                )
        else:
            con.execute("DELETE FROM budgets WHERE category = ? AND user_id = ?", (category, uid))


# --------------------------------------------------------------------------- recurring
def _advance(d: date, frequency: str) -> date:
    if frequency == "Weekly":
        return d + timedelta(days=7)
    if frequency == "Yearly":
        try:
            return d.replace(year=d.year + 1)
        except ValueError:  # Feb 29
            return d.replace(year=d.year + 1, day=28)
    month = d.month % 12 + 1
    year = d.year + (1 if d.month == 12 else 0)
    day = min(d.day, [31, 29 if year % 4 == 0 and (year % 100 or year % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day)


def get_recurring(user_id: int | None = None) -> pd.DataFrame:
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        return pd.read_sql_query(
            "SELECT * FROM recurring WHERE user_id = ? ORDER BY next_date", con, params=(uid,)
        )


def add_recurring(name, tx_type, category, amount, payment_method, frequency, start: date,
                  user_id: int | None = None) -> None:
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        con.execute(
            "INSERT INTO recurring(user_id, name, type, category, amount, payment_method, frequency, "
            "next_date, active) VALUES (?,?,?,?,?,?,?,?,1)",
            (uid, name.strip(), tx_type, category, float(amount), payment_method, frequency,
             start.isoformat()),
        )


def toggle_recurring(rid: int, active: bool, user_id: int | None = None) -> None:
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        con.execute(
            "UPDATE recurring SET active = ? WHERE id = ? AND user_id = ?",
            (1 if active else 0, int(rid), uid),
        )


def delete_recurring(rid: int, user_id: int | None = None) -> None:
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        con.execute("DELETE FROM recurring WHERE id = ? AND user_id = ?", (int(rid), uid))


def process_recurring(today: date | None = None, user_id: int | None = None) -> int:
    """Post every due recurring transaction up to ``today``. Returns count posted."""
    uid = user_id if user_id is not None else get_current_user_id()
    today = today or date.today()
    posted = 0
    with _conn() as con:
        rules = con.execute("SELECT * FROM recurring WHERE active = 1 AND user_id = ?", (uid,)).fetchall()
        for r in rules:
            nxt = date.fromisoformat(r["next_date"])
            guard = 0
            while nxt <= today and guard < 400:
                con.execute(
                    "INSERT INTO transactions(user_id, date, type, category, amount, description, "
                    "payment_method, tags, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (uid, nxt.isoformat(), r["type"], r["category"], r["amount"],
                     f"{r['name']} (recurring)", r["payment_method"], "recurring",
                     datetime.now().isoformat(timespec="seconds")),
                )
                nxt = _advance(nxt, r["frequency"])
                posted += 1
                guard += 1
            con.execute("UPDATE recurring SET next_date = ? WHERE id = ? AND user_id = ?",
                        (nxt.isoformat(), r["id"], uid))
    return posted


# --------------------------------------------------------------------------- goals
def get_goals(user_id: int | None = None) -> pd.DataFrame:
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        return pd.read_sql_query("SELECT * FROM goals WHERE user_id = ? ORDER BY id", con, params=(uid,))


def add_goal(name: str, emoji: str, target: float, saved: float, deadline: date | None,
             user_id: int | None = None) -> None:
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        con.execute(
            "INSERT INTO goals(user_id, name, emoji, target, saved, deadline) VALUES (?,?,?,?,?,?)",
            (uid, name.strip(), emoji or "🎯", float(target), float(saved),
             deadline.isoformat() if deadline else None),
        )


def contribute_goal(gid: int, amount: float, user_id: int | None = None) -> None:
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        con.execute(
            "UPDATE goals SET saved = MAX(0, saved + ?) WHERE id = ? AND user_id = ?",
            (float(amount), int(gid), uid),
        )


def delete_goal(gid: int, user_id: int | None = None) -> None:
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        con.execute("DELETE FROM goals WHERE id = ? AND user_id = ?", (int(gid), uid))


# --------------------------------------------------------------------------- backup / reset
def export_backup(user_id: int | None = None) -> str:
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        data = {
            t: [dict(r) for r in con.execute(f"SELECT * FROM {t} WHERE user_id = ?", (uid,))]
            for t in ("transactions", "categories", "budgets", "recurring", "goals", "settings")
        }
    data["user_id"] = uid
    data["exported_at"] = datetime.now().isoformat(timespec="seconds")
    return json.dumps(data, indent=2, ensure_ascii=False)


def restore_backup(raw: str, user_id: int | None = None) -> None:
    uid = user_id if user_id is not None else get_current_user_id()
    data = json.loads(raw)
    tables = ("transactions", "categories", "budgets", "recurring", "goals", "settings")
    with _conn() as con:
        for t in tables:
            rows = data.get(t)
            if rows is None:
                continue
            con.execute(f"DELETE FROM {t} WHERE user_id = ?", (uid,))
            for row in rows:
                row["user_id"] = uid
                keys = ", ".join(row.keys())
                qs = ", ".join("?" for _ in row)
                con.execute(f"INSERT INTO {t}({keys}) VALUES ({qs})", tuple(row.values()))


def reset_all(keep_settings: bool = True, user_id: int | None = None) -> None:
    uid = user_id if user_id is not None else get_current_user_id()
    with _conn() as con:
        for t in ("transactions", "budgets", "recurring", "goals"):
            con.execute(f"DELETE FROM {t} WHERE user_id = ?", (uid,))
        con.execute("DELETE FROM categories WHERE user_id = ?", (uid,))
        con.executemany(
            "INSERT INTO categories(name, type, emoji, color, user_id) VALUES (?,?,?,?,?)",
            [(*c, uid) for c in DEFAULT_CATEGORIES],
        )
        if not keep_settings:
            con.execute("DELETE FROM settings WHERE user_id = ?", (uid,))


# --------------------------------------------------------------------------- demo data
def load_demo_data(months: int = 6, user_id: int | None = None) -> int:
    """Generate realistic sample data for the active user."""
    uid = user_id if user_id is not None else get_current_user_id()
    rng = random.Random(42 + uid)
    today = date.today()
    start = (today.replace(day=1) - timedelta(days=31 * (months - 1))).replace(day=1)
    rows = []

    def add(d, t, c, a, desc, pm="Card", tags=""):
        rows.append((uid, d.isoformat(), t, c, round(a, 2), desc, pm, tags,
                     datetime.now().isoformat(timespec="seconds")))

    spenders = [
        ("Food & Dining", (8, 45), 0.55, ["Lunch with team", "Pizza night", "Coffee & bagel",
                                          "Sushi dinner", "Burger joint", "Brunch"]),
        ("Groceries", (25, 120), 0.25, ["Weekly groceries", "Farmers market", "Costco run"]),
        ("Transport", (4, 35), 0.35, ["Uber ride", "Metro card top-up", "Gas refill", "Parking"]),
        ("Shopping", (20, 160), 0.10, ["New sneakers", "Amazon order", "Home decor", "Jacket"]),
        ("Entertainment", (10, 70), 0.10, ["Movie tickets", "Concert", "Bowling", "Game purchase"]),
        ("Health", (15, 90), 0.04, ["Pharmacy", "Doctor co-pay", "Vitamins"]),
        ("Gifts & Donations", (15, 80), 0.03, ["Birthday gift", "Charity donation"]),
        ("Education", (12, 60), 0.03, ["Online course", "Books"]),
    ]
    d = start
    while d <= today:
        for cat, (lo, hi), p, descs in spenders:
            if rng.random() < p:
                pm = rng.choices(PAYMENT_METHODS[:4], weights=[55, 15, 20, 10])[0]
                add(d, "Expense", cat, rng.uniform(lo, hi), rng.choice(descs), pm)
        if d.day == 1:
            add(d, "Expense", "Rent & Housing", 1450, "Monthly rent", "Bank Transfer", "fixed")
            add(d, "Income", "Salary", 5200 + rng.uniform(-50, 50), "Monthly salary",
                "Bank Transfer")
        if d.day == 5:
            add(d, "Expense", "Subscriptions", 15.99, "Netflix", "Card", "streaming")
            add(d, "Expense", "Subscriptions", 10.99, "Spotify", "Card", "music")
        if d.day == 12:
            add(d, "Expense", "Bills & Utilities", rng.uniform(70, 130), "Electricity bill",
                "Bank Transfer")
            add(d, "Expense", "Bills & Utilities", 59.99, "Internet", "Card")
        if d.day == 18 and rng.random() < 0.7:
            add(d, "Income", "Freelance", rng.uniform(300, 1200), "Freelance project",
                "Bank Transfer")
        if d.day == 25 and rng.random() < 0.5:
            add(d, "Income", "Investments", rng.uniform(40, 220), "Dividend payout",
                "Bank Transfer")
        if d.day == 20 and d.month % 3 == 0:
            add(d, "Expense", "Travel", rng.uniform(250, 700), "Weekend getaway", "Card",
                "vacation")
        d += timedelta(days=1)

    with _conn() as con:
        con.executemany(
            "INSERT INTO transactions(user_id, date, type, category, amount, description, "
            "payment_method, tags, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            rows,
        )
        for cat, amt in [(TOTAL_BUDGET_KEY, 3200), ("Food & Dining", 450), ("Groceries", 400),
                         ("Transport", 200), ("Shopping", 300), ("Entertainment", 150),
                         ("Subscriptions", 40)]:
            existing = con.execute("SELECT id FROM budgets WHERE category = ? AND user_id = ?", (cat, uid)).fetchone()
            if existing:
                con.execute("UPDATE budgets SET amount = ? WHERE id = ?", (amt, existing["id"]))
            else:
                con.execute("INSERT INTO budgets(category, amount, user_id) VALUES (?,?,?)", (cat, amt, uid))

        if con.execute("SELECT COUNT(*) FROM goals WHERE user_id = ?", (uid,)).fetchone()[0] == 0:
            con.executemany(
                "INSERT INTO goals(user_id, name, emoji, target, saved, deadline) VALUES (?,?,?,?,?,?)",
                [
                    (uid, "Emergency Fund", "🛟", 10000, 6400,
                     (today + timedelta(days=200)).isoformat()),
                    (uid, "Japan Trip", "🗾", 4000, 1350, (today + timedelta(days=150)).isoformat()),
                    (uid, "New Laptop", "💻", 2200, 1900, (today + timedelta(days=45)).isoformat()),
                ],
            )
        if con.execute("SELECT COUNT(*) FROM recurring WHERE user_id = ?", (uid,)).fetchone()[0] == 0:
            nxt_month = _advance(today.replace(day=1), "Monthly")
            con.executemany(
                "INSERT INTO recurring(user_id, name, type, category, amount, payment_method, "
                "frequency, next_date, active) VALUES (?,?,?,?,?,?,?,?,1)",
                [
                    (uid, "Rent", "Expense", "Rent & Housing", 1450, "Bank Transfer", "Monthly",
                     nxt_month.isoformat()),
                    (uid, "Salary", "Income", "Salary", 5200, "Bank Transfer", "Monthly",
                     nxt_month.isoformat()),
                    (uid, "Gym membership", "Expense", "Health", 39.0, "Card", "Monthly",
                     (today + timedelta(days=9)).isoformat()),
                ],
            )
    return len(rows)
