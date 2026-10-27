"""Lumen — a beautiful personal expense tracker built with Streamlit.

Run with:  python -m streamlit run app.py
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

import auth
import db
import views
from themes import THEMES, build_css, get_theme, hex_to_rgba, logo_svg, sync_native_theme
from ui import esc, html, money, progress_bar

st.set_page_config(
    page_title="Lumen · Personal Expense Tracker",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Lumen — track spending, budgets and goals with style."},
)

# ----------------------------------------------------------------------------- bootstrap
db.init_db()

# Check authentication state
user = auth.get_current_user()

settings = db.get_settings(user_id=user["id"] if user else 1)
T = get_theme(settings.get("theme"))

# Push the theme into Streamlit's native config (widgets, menus, data grid).
if sync_native_theme(T):
    tries = st.session_state.get("_theme_reruns", 0)
    if tries < 2:
        st.session_state["_theme_reruns"] = tries + 1
        st.rerun()
else:
    st.session_state["_theme_reruns"] = 0

st.markdown(build_css(T), unsafe_allow_html=True)

# ----------------------------------------------------------------------------- logo
assets = Path(__file__).parent / "assets"
assets.mkdir(exist_ok=True)
logo_path = assets / f"logo_{T['name'].lower()}.svg"
if not logo_path.exists():
    logo_path.write_text(logo_svg(T), encoding="utf-8")
st.logo(str(logo_path), size="large")

# ----------------------------------------------------------------------------- sidebar theme helpers
def _on_theme_select() -> None:
    views.apply_theme(st.session_state["sb_theme"])


def _on_dark_toggle() -> None:
    s = db.get_settings()
    target = s["last_dark_theme"] if st.session_state["sb_dark"] else s["last_light_theme"]
    if target not in THEMES:
        target = "Midnight" if st.session_state["sb_dark"] else "Light"
    views.apply_theme(target)


# If user is not authenticated, render login / signup portal
if not user:
    with st.sidebar:
        st.session_state["sb_theme"] = T["name"]
        st.selectbox("🎨 Theme", list(THEMES), key="sb_theme", on_change=_on_theme_select,
                     format_func=lambda n: f"{THEMES[n]['emoji']}  {n}")
        st.session_state["sb_dark"] = T["is_dark"]
        st.toggle("🌙 Dark mode", key="sb_dark", on_change=_on_dark_toggle)

        swatches = "".join(
            f'<span title="{n}" style="display:inline-block;width:14px;height:14px;border-radius:50%;'
            f'margin-right:6px;background:linear-gradient(135deg,{t["primary"]},{t["accent"]});'
            f'box-shadow:0 0 0 2px {hex_to_rgba(T["text"], 0.6) if n == T["name"] else "transparent"}"></span>'
            for n, t in THEMES.items())
        html(f'<div style="margin-top:.4rem">{swatches}</div>'
             f'<div class="lm-muted" style="font-size:.72rem;margin-top:1.2rem">'
             f'Lumen · secure local personal ledger</div>')

    auth.render_auth_page()
    st.stop()

# ----------------------------------------------------------------------------- authenticated setup
if not st.session_state.get(f"_recurring_done_{user['id']}"):
    posted = db.process_recurring(user_id=user["id"])
    st.session_state[f"_recurring_done_{user['id']}"] = True
    if posted:
        st.toast(f"Auto-logged {posted} recurring transaction(s)", icon="🔁")

cats = db.get_categories(user_id=user["id"])
emoji = dict(zip(cats["name"], cats["emoji"]))
cmap = {name: T["palette"][i % len(T["palette"])] for i, name in enumerate(cats["name"])}
cur = settings.get("currency", "$")
st.session_state["ctx"] = {
    "T": T, "settings": settings, "cur": cur, "cur_md": cur.replace("$", "\\$"),
    "cats": cats, "emoji": emoji, "cmap": cmap, "budgets": db.get_budgets(user_id=user["id"]),
}

# ----------------------------------------------------------------------------- navigation
pages = [
    st.Page(views.page_dashboard, title="Dashboard", icon=":material/space_dashboard:",
            url_path="dashboard", default=True),
    st.Page(views.page_add, title="Add transaction", icon=":material/add_circle:",
            url_path="add"),
    st.Page(views.page_transactions, title="Transactions", icon=":material/receipt_long:",
            url_path="transactions"),
    st.Page(views.page_analytics, title="Analytics", icon=":material/insights:",
            url_path="analytics"),
    st.Page(views.page_budgets, title="Budgets & Goals", icon=":material/savings:",
            url_path="budgets"),
    st.Page(views.page_recurring, title="Recurring", icon=":material/autorenew:",
            url_path="recurring"),
    st.Page(views.page_settings, title="Settings", icon=":material/tune:",
            url_path="settings"),
]
nav = st.navigation(pages)

# ----------------------------------------------------------------------------- authenticated sidebar
with st.sidebar:
    # User Profile Header
    u_name = user.get("full_name") or user.get("username", "User")
    u_avatar = user.get("avatar", "👤")
    u_handle = user.get("username", "")

    html(f"""
    <div class="lm-card" style="padding:.75rem .9rem;margin:.2rem 0 .7rem;display:flex;align-items:center;gap:.75rem">
      <div style="font-size:1.55rem;width:42px;height:42px;border-radius:12px;background:{hex_to_rgba(T['primary'], 0.18)};display:grid;place-items:center;flex-shrink:0">{u_avatar}</div>
      <div style="flex:1;min-width:0">
        <div style="font-weight:700;font-size:.95rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{esc(u_name)}</div>
        <div class="lm-muted" style="font-size:.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">@{esc(u_handle)}</div>
      </div>
    </div>""")

    if st.button("Sign Out", icon=":material/logout:", width="stretch", key="sb_logout"):
        auth.sign_out()

    st.write("")

    # Month-at-a-glance mini card
    df = db.get_transactions(user_id=user["id"])
    today = date.today()
    spent = 0.0
    if not df.empty:
        m = df[(df["date"].dt.to_period("M") == pd.Period(today, "M")) & (df["type"] == "Expense")]
        spent = float(m["amount"].sum())
    budget = st.session_state["ctx"]["budgets"].get(db.TOTAL_BUDGET_KEY, 0)
    pct = spent / budget * 100 if budget else 0
    html(f"""
    <div class="lm-card" style="padding:.9rem 1rem;margin:0 0 1rem">
      <div class="lm-muted" style="font-size:.75rem;letter-spacing:.08em;text-transform:uppercase">{today:%B} spending</div>
      <div class="lm-num" style="font-size:1.45rem;font-weight:700;margin-top:.2rem">{money(spent)}</div>
      {progress_bar(pct) if budget else ''}
      <div class="lm-muted" style="font-size:.78rem">{f'{pct:.0f}% of {money(budget, decimals=0)} budget' if budget else 'No monthly budget set'}</div>
    </div>""")

    st.session_state["sb_theme"] = T["name"]
    st.selectbox("🎨 Theme", list(THEMES), key="sb_theme", on_change=_on_theme_select,
                 format_func=lambda n: f"{THEMES[n]['emoji']}  {n}")
    st.session_state["sb_dark"] = T["is_dark"]
    st.toggle("🌙 Dark mode", key="sb_dark", on_change=_on_dark_toggle)

    swatches = "".join(
        f'<span title="{n}" style="display:inline-block;width:14px;height:14px;border-radius:50%;'
        f'margin-right:6px;background:linear-gradient(135deg,{t["primary"]},{t["accent"]});'
        f'box-shadow:0 0 0 2px {hex_to_rgba(T["text"], 0.6) if n == T["name"] else "transparent"}"></span>'
        for n, t in THEMES.items())
    html(f'<div style="margin-top:.4rem">{swatches}</div>'
         f'<div class="lm-muted" style="font-size:.72rem;margin-top:1.2rem">'
         f'Lumen · local SQLite database</div>')

nav.run()
