"""All app pages for Lumen."""

from __future__ import annotations

import base64
import calendar
import io
import smtplib
import urllib.parse
from datetime import date, datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

import db
import pdf_export
from themes import THEMES, get_theme, hex_to_rgba
from ui import (ctx, delta_chip, donut, empty_state, esc, hero, html, insight_list,
                kpi_card, kpi_row, money, money_md, progress_bar, render_avatar_html,
                ring_svg, section, show_chart, tx_list)

CURRENCY_DICT = {
    "$ (USD) · US Dollar": "$",
    "₹ (INR) · Indian Rupee": "₹",
    "€ (EUR) · Euro": "€",
    "£ (GBP) · British Pound": "£",
    "¥ (JPY / CNY) · Japanese Yen / Yuan": "¥",
    "A$ (AUD) · Australian Dollar": "A$",
    "C$ (CAD) · Canadian Dollar": "C$",
    "CHF (CHF) · Swiss Franc": "CHF ",
    "د.إ (AED) · UAE Dirham": "د.إ ",
    "﷼ (SAR) · Saudi Riyal": "﷼ ",
    "₩ (KRW) · South Korean Won": "₩",
    "R$ (BRL) · Brazilian Real": "R$",
    "₽ (RUB) · Russian Ruble": "₽",
    "฿ (THB) · Thai Baht": "฿",
    "S$ (SGD) · Singapore Dollar": "S$",
    "NZ$ (NZD) · New Zealand Dollar": "NZ$",
    "₱ (PHP) · Philippine Peso": "₱",
    "₨ (PKR) · Pakistani Rupee": "₨ ",
    "৳ (BDT) · Bangladeshi Taka": "৳",
    "₦ (NGN) · Nigerian Naira": "₦",
}
CURRENCIES = list(dict.fromkeys(list(CURRENCY_DICT.values()) + ["$", "€", "£", "₹", "¥", "₩", "₽", "R$", "A$", "C$", "CHF ", "د.إ "]))


# =========================================================================== helpers
def _month_df(df: pd.DataFrame, period: pd.Period) -> pd.DataFrame:
    if df.empty:
        return df
    return df[df["date"].dt.to_period("M") == period]


def _sum(df: pd.DataFrame, tx_type: str) -> float:
    if df.empty:
        return 0.0
    return float(df.loc[df["type"] == tx_type, "amount"].sum())


def apply_theme(name: str) -> None:
    db.set_setting("theme", name)
    key = "last_dark_theme" if THEMES[name]["base"] == "dark" else "last_light_theme"
    db.set_setting(key, name)


def _cat_label(name: str) -> str:
    return f"{ctx()['emoji'].get(name, '🏷️')}  {name}"


def _greeting() -> str:
    h = datetime.now().hour
    return "Good morning" if h < 12 else "Good afternoon" if h < 18 else "Good evening"


# =========================================================================== add form
def transaction_form(prefix: str, in_dialog: bool = False) -> None:
    c = ctx()
    tx_type = st.segmented_control(
        "Type", ["Expense", "Income"], default="Expense", required=True,
        key=f"{prefix}_type", format_func=lambda x: ("💸 " if x == "Expense" else "💰 ") + x,
    ) or "Expense"
    cats = c["cats"]
    options = cats.loc[cats["type"] == tx_type, "name"].tolist() or ["Other"]

    with st.form(f"{prefix}_form", clear_on_submit=True, border=not in_dialog):
        col1, col2 = st.columns(2)
        amount = col1.number_input(f"Amount ({c['cur_md']})", min_value=0.0, step=1.0,
                                   format="%.2f", value=None, placeholder="0.00",
                                   key=f"{prefix}_amount")
        d = col2.date_input("Date", value=date.today(), key=f"{prefix}_date",
                            format="YYYY-MM-DD")
        col3, col4 = st.columns(2)
        category = col3.selectbox("Category", options, format_func=_cat_label,
                                  key=f"{prefix}_cat_{tx_type}")
        pm = col4.selectbox("Payment method", db.PAYMENT_METHODS, key=f"{prefix}_pm")
        desc = st.text_input("Description", placeholder="e.g. Dinner at Luigi's",
                             key=f"{prefix}_desc", max_chars=120)
        tags = st.text_input("Tags (optional, comma separated)", placeholder="work, trip",
                             key=f"{prefix}_tags")
        submitted = st.form_submit_button(f"Add {tx_type.lower()}", type="primary",
                                          icon=":material/add:", width="stretch")
    if submitted:
        if not amount or amount <= 0:
            st.error("Please enter an amount greater than zero.")
            return
        db.add_transaction(d, tx_type, category, amount, desc, pm, tags)
        st.toast(f"{tx_type} of {money_md(amount)} added to **{category}**",
                 icon="✅" if tx_type == "Expense" else "🎉")
        if in_dialog:
            st.rerun()


@st.dialog("Quick add", width="medium", icon=":material/bolt:")
def quick_add_dialog() -> None:
    transaction_form("qa", in_dialog=True)


@st.dialog("Edit transaction", width="medium", icon=":material/edit:")
def edit_dialog(row: dict) -> None:
    c = ctx()
    tx_type = st.segmented_control("Type", ["Expense", "Income"], default=row["type"],
                                   required=True, key="ed_type") or row["type"]
    options = c["cats"].loc[c["cats"]["type"] == tx_type, "name"].tolist()
    if row["category"] not in options:
        options = [row["category"]] + options
    with st.form("edit_form", border=False):
        col1, col2 = st.columns(2)
        amount = col1.number_input("Amount", min_value=0.0, value=float(row["amount"]),
                                   step=1.0, format="%.2f")
        d = col2.date_input("Date", value=pd.Timestamp(row["date"]).date())
        col3, col4 = st.columns(2)
        category = col3.selectbox("Category", options, index=options.index(row["category"]),
                                  format_func=_cat_label)
        pm_opts = db.PAYMENT_METHODS
        pm = col4.selectbox("Payment method", pm_opts,
                            index=pm_opts.index(row["payment_method"])
                            if row["payment_method"] in pm_opts else 0)
        desc = st.text_input("Description", value=row["description"])
        tags = st.text_input("Tags", value=row["tags"])
        if st.form_submit_button("Save changes", type="primary", width="stretch"):
            db.update_transaction(row["id"], date=d, type=tx_type, category=category,
                                  amount=amount, description=desc, payment_method=pm, tags=tags)
            st.toast("Transaction updated", icon="✏️")
            st.rerun()


# =========================================================================== dashboard
def _insights(m_df, p_df, budget_total, period, is_current, days_elapsed, days_in_month):
    cur_exp = m_df[m_df["type"] == "Expense"]
    prev_exp = p_df[p_df["type"] == "Expense"]
    spent, prev_spent = cur_exp["amount"].sum(), prev_exp["amount"].sum()
    income = _sum(m_df, "Income")
    items = []
    if cur_exp.empty:
        return [("🌱", "No expenses recorded for this month yet — a clean slate!")]

    by_cat = cur_exp.groupby("category")["amount"].sum().sort_values(ascending=False)
    top_cat, top_val = by_cat.index[0], by_cat.iloc[0]
    items.append(("🏆", f"<b>{esc(top_cat)}</b> is your biggest spend at <b>{money(top_val)}</b> "
                        f"({top_val / spent * 100:.0f}% of expenses)."))

    if prev_spent > 0 and not is_current:
        diff = (spent - prev_spent) / prev_spent * 100
        word = "more" if diff > 0 else "less"
        items.append(("📊" if diff > 0 else "👏",
                      f"You spent <b>{abs(diff):.0f}% {word}</b> than the previous month."))
    if not prev_exp.empty:
        prev_cat = prev_exp.groupby("category")["amount"].sum()
        jumps = (by_cat - prev_cat.reindex(by_cat.index).fillna(0)).sort_values(ascending=False)
        if len(jumps) and jumps.iloc[0] > max(30, 0.1 * spent):
            items.append(("📈", f"<b>{esc(jumps.index[0])}</b> is up <b>{money(jumps.iloc[0])}</b> "
                                "compared to last month."))

    if is_current and days_elapsed > 0:
        projected = spent / days_elapsed * days_in_month
        if budget_total:
            if projected > budget_total:
                items.append(("⚠️", f"At this pace you'll spend <b>{money(projected)}</b> — "
                                    f"<b>{money(projected - budget_total)}</b> over budget."))
            else:
                items.append(("✅", f"On track! Projected spend <b>{money(projected)}</b> "
                                    f"stays within your {money(budget_total)} budget."))
        else:
            items.append(("🔮", f"Projected month-end spend: <b>{money(projected)}</b>."))

    spend_days = set(cur_exp["date"].dt.day)
    no_spend = max(0, days_elapsed - len([d for d in spend_days if d <= days_elapsed]))
    if no_spend:
        items.append(("🧘", f"<b>{no_spend}</b> no-spend day{'s' if no_spend != 1 else ''} "
                            "this month. Nice discipline!"))
    if income > 0:
        rate = (income - spent) / income * 100
        if rate >= 20:
            items.append(("💎", f"You're saving <b>{rate:.0f}%</b> of your income. Excellent!"))
        elif rate < 0:
            items.append(("🚨", "Expenses exceed income this month — time to review."))
    big = cur_exp.nlargest(1, "amount").iloc[0]
    items.append(("🧾", f"Largest purchase: <b>{esc(big['description'] or big['category'])}</b> "
                        f"for <b>{money(big['amount'])}</b> on {big['date']:%b %d}."))
    return items[:6]


# =========================================================================== reports & sharing
def generate_report_text(df: pd.DataFrame, title: str, user_name: str = "", currency: str = "$") -> str:
    """Generate clean plain text summary of an expense report for WhatsApp, Email, or clipboard."""
    lines = []
    lines.append("📊 LUMEN FINANCIAL REPORT")
    lines.append(f"📌 {title}")
    if user_name:
        lines.append(f"👤 Prepared for: {user_name}")
    lines.append(f"📅 Date: {datetime.now().strftime('%b %d, %Y')}")
    lines.append("────────────────────────")

    if df.empty:
        lines.append("No transactions recorded for this period.")
        lines.append("────────────────────────")
        lines.append("✨ Generated with Lumen Personal Expense Tracker")
        return "\n".join(lines)

    inc_df = df[df["type"] == "Income"]
    exp_df = df[df["type"] == "Expense"]
    tot_inc = float(inc_df["amount"].sum()) if not inc_df.empty else 0.0
    tot_exp = float(exp_df["amount"].sum()) if not exp_df.empty else 0.0
    net = tot_inc - tot_exp
    rate = (net / tot_inc * 100) if tot_inc > 0 else 0.0

    lines.append(f"💰 Total Income:   {currency}{tot_inc:,.2f}")
    lines.append(f"💸 Total Expenses: {currency}{tot_exp:,.2f}")
    sign = "+" if net >= 0 else "-"
    lines.append(f"⚖️ Net Savings:    {sign}{currency}{abs(net):,.2f} ({rate:.0f}% savings rate)")
    lines.append(f"🧾 Transactions:   {len(df):,}")
    lines.append("────────────────────────")

    if not exp_df.empty:
        lines.append("🏷️ TOP CATEGORIES:")
        cat_group = exp_df.groupby("category")["amount"].sum().sort_values(ascending=False)
        for cat, amt in cat_group.head(5).items():
            pct = (amt / tot_exp * 100) if tot_exp > 0 else 0
            lines.append(f" • {cat}: {currency}{amt:,.2f} ({pct:.0f}%)")
        lines.append("────────────────────────")

        lines.append("🧾 TOP EXPENSES:")
        top_tx = exp_df.nlargest(3, "amount")
        for _, r in top_tx.iterrows():
            d_str = r["date"].strftime("%b %d") if hasattr(r["date"], "strftime") else str(r["date"])[:10]
            desc = r["description"] or r["category"]
            lines.append(f" • {desc} ({r['category']}): {currency}{r['amount']:,.2f} on {d_str}")
        lines.append("────────────────────────")

    lines.append("✨ Generated with Lumen Personal Expense Tracker")
    return "\n".join(lines)


def send_report_email_smtp(
    to_email: str,
    subject: str,
    body_text: str,
    attachment_bytes: bytes | None = None,
    attachment_filename: str = "report.pdf",
) -> tuple[bool, str]:
    """Send report email with optional PDF attachment via configured SMTP server."""
    clean_email = to_email.strip().lower()
    settings = db.get_settings(user_id=1)
    smtp_host = settings.get("smtp_host", "").strip()
    smtp_port = int(settings.get("smtp_port", 587) or 587)
    smtp_user = settings.get("smtp_user", "").strip()
    smtp_pass = settings.get("smtp_pass", "").strip()
    smtp_sender = settings.get("smtp_sender", "").strip() or smtp_user or "lumen-app@noreply.com"
    use_ssl = str(settings.get("smtp_ssl", "false")).lower() in ("true", "1", "yes")

    if not (smtp_host and smtp_user and smtp_pass):
        return False, "SMTP is not configured yet. Configure SMTP in Settings > Email & SMTP."

    try:
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = smtp_sender
        msg["To"] = clean_email
        msg.attach(MIMEText(body_text, "plain"))

        if attachment_bytes:
            part = MIMEApplication(attachment_bytes, Name=attachment_filename)
            part["Content-Disposition"] = f'attachment; filename="{attachment_filename}"'
            msg.attach(part)

        if use_ssl or smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
            server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_sender, [clean_email], msg.as_string())
        server.quit()
        return True, f"Report successfully emailed to {clean_email}!"
    except Exception as e:
        return False, f"Failed to send email: {e}"


@st.dialog("📤 Share & Export Report", width="large")
def share_report_dialog(initial_df: pd.DataFrame | None = None, default_title: str = "Expense Report") -> None:
    c = ctx()
    cur = c["cur"]
    all_df = db.get_transactions()
    user_name = c["settings"].get("user_name") or "User"
    user = st.session_state.get("user", {})
    if user:
        user_name = user.get("full_name") or user.get("username", user_name)

    if all_df.empty:
        st.info("No transactions available to generate a report.")
        return

    c1, c2 = st.columns([1.5, 1])
    is_single_day = initial_df is not None and not initial_df.empty and len(initial_df["date"].dt.date.unique()) == 1
    scope = c1.selectbox(
        "Report Period",
        ["Selected Day", "This Month", "Last 30 Days", "Year to Date (YTD)", "All Time", "Custom Range"],
        index=0 if is_single_day else 1,
    )

    today = date.today()
    if scope == "Selected Day":
        picked_date = c2.date_input("Date", value=st.session_state.get("selected_day", today))
        filtered = all_df[all_df["date"].dt.date == picked_date]
        title = f"Daily Report ({picked_date.strftime('%b %d, %Y')})"
    elif scope == "This Month":
        current_period = pd.Period(today, "M")
        filtered = all_df[all_df["date"].dt.to_period("M") == current_period]
        title = f"Monthly Report - {today.strftime('%B %Y')}"
    elif scope == "Last 30 Days":
        start_d = today - timedelta(days=30)
        filtered = all_df[all_df["date"].dt.date >= start_d]
        title = f"30-Day Expense Report ({start_d:%b %d} - {today:%b %d, %Y})"
    elif scope == "Year to Date (YTD)":
        start_d = date(today.year, 1, 1)
        filtered = all_df[all_df["date"].dt.date >= start_d]
        title = f"YTD Report ({today.year})"
    elif scope == "All Time":
        filtered = all_df
        title = "All-Time Financial Report"
    else:
        min_d = all_df["date"].min().date()
        max_d = all_df["date"].max().date()
        rng = c2.date_input("Custom Range", value=(max(min_d, today - timedelta(days=30)), today), min_value=min_d, max_value=today)
        if isinstance(rng, (tuple, list)) and len(rng) == 2:
            filtered = all_df[(all_df["date"].dt.date >= rng[0]) & (all_df["date"].dt.date <= rng[1])]
            title = f"Expense Report ({rng[0]:%b %d, %Y} - {rng[1]:%b %d, %Y})"
        else:
            filtered = all_df
            title = "Custom Expense Report"

    report_text = generate_report_text(filtered, title, user_name, cur)

    tab_whatsapp, tab_email, tab_pdf, tab_text = st.tabs([
        "📱  WhatsApp", "📧  Email", "📄  Download PDF", "📋  Copy Text"
    ])

    with tab_whatsapp:
        st.markdown("**Share directly to WhatsApp:**")
        encoded_wa = urllib.parse.quote(report_text)
        wa_url = f"https://api.whatsapp.com/send?text={encoded_wa}"
        st.markdown(
            f"""
            <div style="padding:1rem;border-radius:12px;background:rgba(37,211,102,0.12);border:1px solid rgba(37,211,102,0.3);margin-bottom:1rem;">
              <div style="font-weight:700;color:#25D366;font-size:1.05rem;margin-bottom:.3rem;">🚀 Ready to share on WhatsApp</div>
              <div class="lm-muted" style="font-size:.85rem;margin-bottom:.8rem;">Clicking below opens WhatsApp with your complete financial breakdown pre-filled. Send it to family, accountant, or yourself in 1 tap!</div>
              <a href="{wa_url}" target="_blank" style="display:inline-flex;align-items:center;gap:.5rem;background:#25D366;color:#ffffff;font-weight:700;padding:.6rem 1.3rem;border-radius:10px;text-decoration:none;font-size:.92rem;box-shadow:0 4px 12px rgba(37,211,102,0.3);">
                <span>📱 Open WhatsApp & Send Report</span>
              </a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with tab_email:
        st.markdown("**Share via Email:**")
        subject = f"📊 Lumen Financial Report - {title}"
        encoded_subj = urllib.parse.quote(subject)
        encoded_body = urllib.parse.quote(report_text)
        mailto_url = f"mailto:?subject={encoded_subj}&body={encoded_body}"

        st.markdown(
            f"""
            <div style="padding:1rem;border-radius:12px;background:rgba(124,156,255,0.12);border:1px solid rgba(124,156,255,0.3);margin-bottom:1rem;">
              <div style="font-weight:700;color:#7C9CFF;font-size:1.05rem;margin-bottom:.3rem;">✉️ Open in Default Mail Client</div>
              <div class="lm-muted" style="font-size:.85rem;margin-bottom:.8rem;">Opens your default email client (Outlook, Gmail, Apple Mail) with the subject and body ready to send.</div>
              <a href="{mailto_url}" target="_blank" style="display:inline-flex;align-items:center;gap:.5rem;background:#7C9CFF;color:#070B1A;font-weight:700;padding:.6rem 1.3rem;border-radius:10px;text-decoration:none;font-size:.92rem;">
                <span>📧 Open Default Mail Client</span>
              </a>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("**— or send directly via in-app SMTP —**")
        with st.form("send_email_report_form", border=True):
            recip = st.text_input("Recipient Email", placeholder="e.g. accountant@firm.com or you@email.com")
            attach_pdf = st.checkbox("Attach PDF report to email", value=True)
            if st.form_submit_button("Send Email Report", type="primary", icon=":material/send:", width="stretch"):
                if not recip or "@" not in recip:
                    st.error("Please enter a valid recipient email address.")
                else:
                    pdf_data = pdf_export.generate_expense_pdf(filtered, title=title, user_name=user_name, currency=cur) if attach_pdf else None
                    ok, msg = send_report_email_smtp(recip, subject, report_text, pdf_data, f"lumen_{today}.pdf")
                    if ok:
                        st.toast(msg, icon="📧")
                    else:
                        st.error(msg)

    with tab_pdf:
        st.markdown("**Generate and Download Official PDF Report:**")
        pdf_bytes = pdf_export.generate_expense_pdf(
            filtered,
            title=title,
            subtitle=f"Generated on {today:%B %d, %Y}",
            user_name=user_name,
            currency=cur,
        )
        st.download_button(
            "📥 Download PDF Report",
            data=pdf_bytes,
            file_name=f"lumen_report_{title.lower().replace(' ', '_').replace('-', '_')}.pdf",
            mime="application/pdf",
            type="primary",
            icon=":material/download:",
            width="stretch",
        )
        st.caption("Includes executive summary KPI cards, category breakdown table, and complete transaction ledger.")

    with tab_text:
        st.text_area("Plain Text Report Summary", value=report_text, height=240)


def _render_daily_view(df: pd.DataFrame) -> None:
    """Daily Expenses calendar explorer view."""
    c = ctx()
    T = c["T"]
    cur = c["cur"]

    if "selected_day" not in st.session_state:
        st.session_state["selected_day"] = date.today()

    cur_day = st.session_state["selected_day"]

    # Date navigation bar
    nav1, nav2, nav3, nav4, nav5 = st.columns([1, 1, 1, 1.8, 1.5], vertical_alignment="center")
    if nav1.button("◀ Previous Day", width="stretch", key="cal_prev_day"):
        st.session_state["selected_day"] = cur_day - timedelta(days=1)
        st.rerun()
    if nav2.button("📅 Today", width="stretch", key="cal_today"):
        st.session_state["selected_day"] = date.today()
        st.rerun()
    if nav3.button("Next Day ▶", width="stretch", key="cal_next_day"):
        st.session_state["selected_day"] = cur_day + timedelta(days=1)
        st.rerun()

    picked = nav4.date_input(
        "Choose Date from Calendar",
        value=cur_day,
        key="cal_direct_picker",
        label_visibility="collapsed",
    )
    if picked != cur_day:
        st.session_state["selected_day"] = picked
        st.rerun()

    if nav5.button("📤 Share / Export Day", icon=":material/share:", width="stretch", key="cal_share_btn"):
        day_sub = df[df["date"].dt.date == cur_day] if not df.empty else df
        share_report_dialog(day_sub, f"Daily Report - {cur_day:%A, %b %d, %Y}")

    st.write("")

    day_df = df[df["date"].dt.date == cur_day] if not df.empty else pd.DataFrame()
    day_exp = float(day_df[day_df["type"] == "Expense"]["amount"].sum()) if not day_df.empty else 0.0
    day_inc = float(day_df[day_df["type"] == "Income"]["amount"].sum()) if not day_df.empty else 0.0
    day_net = day_inc - day_exp
    tx_count = len(day_df)

    is_today = cur_day == date.today()
    badge_text = "TODAY" if is_today else f"{cur_day:%A}"
    html(f"""
    <div style="display:flex;align-items:center;gap:.6rem;margin-bottom:1rem">
      <span class="lm-chip {'good' if is_today else 'neutral'}" style="font-size:.85rem;padding:.2rem .6rem">{badge_text}</span>
      <h2 style="margin:0;font-size:1.45rem;font-weight:700">{cur_day:%A, %B %d, %Y}</h2>
    </div>
    """)

    kpi_row([
        kpi_card("Day Expenses", money(day_exp), "💸", T["expense"], f"{len(day_df[day_df['type'] == 'Expense']) if not day_df.empty else 0} expense(s)"),
        kpi_card("Day Income", money(day_inc), "💰", T["income"], f"{len(day_df[day_df['type'] == 'Income']) if not day_df.empty else 0} income(s)", 0.06),
        kpi_card("Day Net Cashflow", money(day_net), "⚖️", T["income"] if day_net >= 0 else T["expense"], "income − expenses", 0.12),
        kpi_card("Transactions Logged", f"{tx_count}", "🧾", T["primary"], "items on this date", 0.18),
    ])

    l_col, r_col = st.columns([1.55, 1], gap="large")

    with l_col:
        section(f"🧾 Activity on {cur_day:%b %d}")
        if day_df.empty:
            empty_state("🌱", f"No expenses or income on {cur_day:%B %d}",
                        "A pristine day! You can add a transaction for this date on the right.")
        else:
            exp_day = day_df[day_df["type"] == "Expense"]
            if not exp_day.empty and len(exp_day["category"].unique()) > 1:
                cat_sum = exp_day.groupby("category")["amount"].sum().sort_values(ascending=False)
                donut(cat_sum.index.tolist(), cat_sum.values.tolist(),
                      [c["cmap"].get(k, T["primary"]) for k in cat_sum.index],
                      "Spent Today", money(cat_sum.sum(), decimals=0), key=f"day_donut_{cur_day}", height=280)

            for _, r in day_df.iterrows():
                is_inc = r["type"] == "Income"
                amt_str = ("+" if is_inc else "−") + money(r["amount"])
                color = c["cmap"].get(r["category"], T["primary"])
                emoji = c["emoji"].get(r["category"], "🏷️")
                tags_str = f" · tags: {esc(r['tags'])}" if r.get("tags") else ""
                with st.container(border=True):
                    c_info, c_action = st.columns([4.5, 1.2], vertical_alignment="center")
                    with c_info:
                        html(f"""
                        <div class="lm-tx" style="border:none;padding:0">
                          <div class="lm-tx-icon" style="background:{hex_to_rgba(color, 0.18)}">{emoji}</div>
                          <div class="lm-tx-main">
                            <div class="lm-tx-title">{esc(r["description"] or r["category"])}</div>
                            <div class="lm-tx-sub">{esc(r["category"])} · {esc(r["payment_method"])}{tags_str}</div>
                          </div>
                          <div class="lm-tx-amt lm-num {'inc' if is_inc else 'exp'}">{amt_str}</div>
                        </div>""")
                    with c_action:
                        e_col, d_col = st.columns(2)
                        if e_col.button("", key=f"d_ed_{r['id']}", icon=":material/edit:", help="Edit"):
                            edit_dialog(r.to_dict())
                        if d_col.button("", key=f"d_del_{r['id']}", icon=":material/delete:", help="Delete"):
                            db.delete_transactions([r["id"]])
                            st.toast("Transaction deleted", icon="🗑️")
                            st.rerun()

    with r_col:
        section("➕ Add to this date")
        with st.form("day_quick_add", clear_on_submit=True, border=True):
            st.caption(f"Logging transaction for: **{cur_day:%A, %B %d, %Y}**")
            tx_type = st.segmented_control(
                "Type", ["Expense", "Income"], default="Expense", required=True,
                key="d_qa_type", format_func=lambda x: ("💸 " if x == "Expense" else "💰 ") + x
            ) or "Expense"
            cats = c["cats"]
            opts = cats.loc[cats["type"] == tx_type, "name"].tolist() or ["Other"]
            qa_amt = st.number_input(f"Amount ({c['cur_md']})", min_value=0.0, step=1.0, format="%.2f", placeholder="0.00", key="d_qa_amt")
            qa_cat = st.selectbox("Category", opts, format_func=_cat_label, key=f"d_qa_cat_{tx_type}")
            qa_pm = st.selectbox("Payment method", db.PAYMENT_METHODS, key="d_qa_pm")
            qa_desc = st.text_input("Description", placeholder="e.g. Lunch with team", key="d_qa_desc", max_chars=120)
            qa_tags = st.text_input("Tags (optional)", placeholder="work, dining", key="d_qa_tags")
            if st.form_submit_button(f"Add {tx_type.lower()}", type="primary", icon=":material/add:", width="stretch"):
                if qa_amt and qa_amt > 0:
                    db.add_transaction(cur_day, tx_type, qa_cat, qa_amt, qa_desc, qa_pm, qa_tags)
                    st.toast(f"{tx_type} of {money_md(qa_amt)} logged for {cur_day:%b %d}", icon="✅")
                    st.rerun()
                else:
                    st.error("Please enter a valid amount.")

        if not df.empty:
            section(f"📅 Daily spend in {cur_day:%B %Y}")
            m_start = date(cur_day.year, cur_day.month, 1)
            days_in_m = calendar.monthrange(cur_day.year, cur_day.month)[1]
            m_end = date(cur_day.year, cur_day.month, days_in_m)
            m_exp = df[(df["type"] == "Expense") & (df["date"].dt.date >= m_start) & (df["date"].dt.date <= m_end)]
            if not m_exp.empty:
                daily_s = m_exp.groupby(m_exp["date"].dt.day)["amount"].sum().reindex(range(1, days_in_m + 1), fill_value=0)
                colors = [T["accent"] if d == cur_day.day else hex_to_rgba(T["primary"], 0.45) for d in range(1, days_in_m + 1)]
                fig = go.Figure(go.Bar(
                    x=list(range(1, days_in_m + 1)),
                    y=daily_s.values,
                    marker_color=colors,
                    marker_line_width=0,
                    hovertemplate=f"{cur_day:%b} %{{x}}: {cur}%{{y:,.2f}}<extra></extra>",
                ))
                fig.update_xaxes(title=None, dtick=5)
                fig.update_yaxes(title=None, tickprefix=cur)
                show_chart(fig, key=f"month_daily_bars_{cur_day.month}_{cur_day.year}", height=220)


def page_dashboard() -> None:
    # Handle secret proxy suite launch via query param or session state
    if st.query_params.get("proxy") == "1" or st.session_state.get("show_proxy_portal"):
        st.query_params.clear()
        st.session_state["show_proxy_portal"] = True

    if st.session_state.get("show_proxy_portal"):
        import proxy_portal
        proxy_portal.render_proxy_portal()
        return

    c = ctx()
    T = c["T"]
    df = db.get_transactions()
    name = c["settings"].get("user_name") or ""

    top_l, top_r = st.columns([2.5, 1.7], vertical_alignment="bottom")
    with top_l:
        greet_title = f"{_greeting()}{', ' + esc(name) if name else ''}"
        sub_title = f"Here's your money story · {date.today():%A, %B %d}"

        # Natural Themed Sparkle Trigger: Zero outline, themed vector star glyph, zero-jitter layout
        html(f"""
        <style>
        div.st-key-sparkle_proxy_trigger {{
            display: inline-flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            padding: 0 !important;
            margin: 0 !important;
        }}
        div.st-key-sparkle_proxy_trigger button,
        div.st-key-sparkle_proxy_trigger button:hover,
        div.st-key-sparkle_proxy_trigger button:focus,
        div.st-key-sparkle_proxy_trigger button:active,
        div.st-key-sparkle_proxy_trigger button:focus-visible {{
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            border-width: 0 !important;
            box-shadow: none !important;
            outline: none !important;
            padding: 0 4px !important;
            margin: 0 !important;
            min-height: unset !important;
            height: auto !important;
            line-height: 1 !important;
            font-size: 1.7rem !important;
            cursor: pointer !important;
            background: linear-gradient(135deg, {T['primary']}, {T['accent']}) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            transition: transform 0.2s ease, filter 0.2s ease !important;
        }}
        div.st-key-sparkle_proxy_trigger button:hover {{
            transform: scale(1.2) rotate(12deg) !important;
            filter: drop-shadow(0 0 6px {T['accent']}) !important;
        }}
        div.st-key-sparkle_proxy_trigger div[data-testid="stMarkdownContainer"] p {{
            font-size: 1.7rem !important;
            line-height: 1 !important;
            margin: 0 !important;
            background: linear-gradient(135deg, {T['primary']}, {T['accent']}) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
        }}
        </style>
        """)

        c_title, c_star = st.columns([0.9, 0.1], vertical_alignment="center")
        with c_title:
            st.markdown(f'<h1 class="lm-hero-title" style="margin:0;padding:0;line-height:1.2;">{greet_title}</h1>', unsafe_allow_html=True)
        with c_star:
            if st.button("✦", key="sparkle_proxy_trigger", help="Orbit Portal"):
                st.session_state["show_proxy_portal"] = True
                st.rerun()

        st.markdown(f'<div class="lm-hero-sub" style="margin-top:0.25rem;margin-bottom:1.1rem">{sub_title}</div>', unsafe_allow_html=True)

    if df.empty:
        return df
    return df[df["date"].dt.to_period("M") == period]


def _sum(df: pd.DataFrame, tx_type: str) -> float:
    if df.empty:
        return 0.0
    return float(df.loc[df["type"] == tx_type, "amount"].sum())


def apply_theme(name: str) -> None:
    db.set_setting("theme", name)
    key = "last_dark_theme" if THEMES[name]["base"] == "dark" else "last_light_theme"
    db.set_setting(key, name)


def _cat_label(name: str) -> str:
    return f"{ctx()['emoji'].get(name, '🏷️')}  {name}"


def _greeting() -> str:
    h = datetime.now().hour
    return "Good morning" if h < 12 else "Good afternoon" if h < 18 else "Good evening"


# =========================================================================== add form
def transaction_form(prefix: str, in_dialog: bool = False) -> None:
    c = ctx()
    tx_type = st.segmented_control(
        "Type", ["Expense", "Income"], default="Expense", required=True,
        key=f"{prefix}_type", format_func=lambda x: ("💸 " if x == "Expense" else "💰 ") + x,
    ) or "Expense"
    cats = c["cats"]
    options = cats.loc[cats["type"] == tx_type, "name"].tolist() or ["Other"]

    with st.form(f"{prefix}_form", clear_on_submit=True, border=not in_dialog):
        col1, col2 = st.columns(2)
        amount = col1.number_input(f"Amount ({c['cur_md']})", min_value=0.0, step=1.0,
                                   format="%.2f", value=None, placeholder="0.00",
                                   key=f"{prefix}_amount")
        d = col2.date_input("Date", value=date.today(), key=f"{prefix}_date",
                            format="YYYY-MM-DD")
        col3, col4 = st.columns(2)
        category = col3.selectbox("Category", options, format_func=_cat_label,
                                  key=f"{prefix}_cat_{tx_type}")
        pm = col4.selectbox("Payment method", db.PAYMENT_METHODS, key=f"{prefix}_pm")
        desc = st.text_input("Description", placeholder="e.g. Dinner at Luigi's",
                             key=f"{prefix}_desc", max_chars=120)
        tags = st.text_input("Tags (optional, comma separated)", placeholder="work, trip",
                             key=f"{prefix}_tags")
        submitted = st.form_submit_button(f"Add {tx_type.lower()}", type="primary",
                                          icon=":material/add:", width="stretch")
    if submitted:
        if not amount or amount <= 0:
            st.error("Please enter an amount greater than zero.")
            return
        db.add_transaction(d, tx_type, category, amount, desc, pm, tags)
        st.toast(f"{tx_type} of {money_md(amount)} added to **{category}**",
                 icon="✅" if tx_type == "Expense" else "🎉")
        if in_dialog:
            st.rerun()


@st.dialog("Quick add", width="medium", icon=":material/bolt:")
def quick_add_dialog() -> None:
    transaction_form("qa", in_dialog=True)


@st.dialog("Edit transaction", width="medium", icon=":material/edit:")
def edit_dialog(row: dict) -> None:
    c = ctx()
    tx_type = st.segmented_control("Type", ["Expense", "Income"], default=row["type"],
                                   required=True, key="ed_type") or row["type"]
    options = c["cats"].loc[c["cats"]["type"] == tx_type, "name"].tolist()
    if row["category"] not in options:
        options = [row["category"]] + options
    with st.form("edit_form", border=False):
        col1, col2 = st.columns(2)
        amount = col1.number_input("Amount", min_value=0.0, value=float(row["amount"]),
                                   step=1.0, format="%.2f")
        d = col2.date_input("Date", value=pd.Timestamp(row["date"]).date())
        col3, col4 = st.columns(2)
        category = col3.selectbox("Category", options, index=options.index(row["category"]),
                                  format_func=_cat_label)
        pm_opts = db.PAYMENT_METHODS
        pm = col4.selectbox("Payment method", pm_opts,
                            index=pm_opts.index(row["payment_method"])
                            if row["payment_method"] in pm_opts else 0)
        desc = st.text_input("Description", value=row["description"])
        tags = st.text_input("Tags", value=row["tags"])
        if st.form_submit_button("Save changes", type="primary", width="stretch"):
            db.update_transaction(row["id"], date=d, type=tx_type, category=category,
                                  amount=amount, description=desc, payment_method=pm, tags=tags)
            st.toast("Transaction updated", icon="✏️")
            st.rerun()


# =========================================================================== dashboard
def _insights(m_df, p_df, budget_total, period, is_current, days_elapsed, days_in_month):
    cur_exp = m_df[m_df["type"] == "Expense"]
    prev_exp = p_df[p_df["type"] == "Expense"]
    spent, prev_spent = cur_exp["amount"].sum(), prev_exp["amount"].sum()
    income = _sum(m_df, "Income")
    items = []
    if cur_exp.empty:
        return [("🌱", "No expenses recorded for this month yet — a clean slate!")]

    by_cat = cur_exp.groupby("category")["amount"].sum().sort_values(ascending=False)
    top_cat, top_val = by_cat.index[0], by_cat.iloc[0]
    items.append(("🏆", f"<b>{esc(top_cat)}</b> is your biggest spend at <b>{money(top_val)}</b> "
                        f"({top_val / spent * 100:.0f}% of expenses)."))

    if prev_spent > 0 and not is_current:
        diff = (spent - prev_spent) / prev_spent * 100
        word = "more" if diff > 0 else "less"
        items.append(("📊" if diff > 0 else "👏",
                      f"You spent <b>{abs(diff):.0f}% {word}</b> than the previous month."))
    if not prev_exp.empty:
        prev_cat = prev_exp.groupby("category")["amount"].sum()
        jumps = (by_cat - prev_cat.reindex(by_cat.index).fillna(0)).sort_values(ascending=False)
        if len(jumps) and jumps.iloc[0] > max(30, 0.1 * spent):
            items.append(("📈", f"<b>{esc(jumps.index[0])}</b> is up <b>{money(jumps.iloc[0])}</b> "
                                "compared to last month."))

    if is_current and days_elapsed > 0:
        projected = spent / days_elapsed * days_in_month
        if budget_total:
            if projected > budget_total:
                items.append(("⚠️", f"At this pace you'll spend <b>{money(projected)}</b> — "
                                    f"<b>{money(projected - budget_total)}</b> over budget."))
            else:
                items.append(("✅", f"On track! Projected spend <b>{money(projected)}</b> "
                                    f"stays within your {money(budget_total)} budget."))
        else:
            items.append(("🔮", f"Projected month-end spend: <b>{money(projected)}</b>."))

    spend_days = set(cur_exp["date"].dt.day)
    no_spend = max(0, days_elapsed - len([d for d in spend_days if d <= days_elapsed]))
    if no_spend:
        items.append(("🧘", f"<b>{no_spend}</b> no-spend day{'s' if no_spend != 1 else ''} "
                            "this month. Nice discipline!"))
    if income > 0:
        rate = (income - spent) / income * 100
        if rate >= 20:
            items.append(("💎", f"You're saving <b>{rate:.0f}%</b> of your income. Excellent!"))
        elif rate < 0:
            items.append(("🚨", "Expenses exceed income this month — time to review."))
    big = cur_exp.nlargest(1, "amount").iloc[0]
    items.append(("🧾", f"Largest purchase: <b>{esc(big['description'] or big['category'])}</b> "
                        f"for <b>{money(big['amount'])}</b> on {big['date']:%b %d}."))
    return items[:6]


# =========================================================================== reports & sharing
def generate_report_text(df: pd.DataFrame, title: str, user_name: str = "", currency: str = "$") -> str:
    """Generate clean plain text summary of an expense report for WhatsApp, Email, or clipboard."""
    lines = []
    lines.append("📊 LUMEN FINANCIAL REPORT")
    lines.append(f"📌 {title}")
    if user_name:
        lines.append(f"👤 Prepared for: {user_name}")
    lines.append(f"📅 Date: {datetime.now().strftime('%b %d, %Y')}")
    lines.append("────────────────────────")

    if df.empty:
        lines.append("No transactions recorded for this period.")
        lines.append("────────────────────────")
        lines.append("✨ Generated with Lumen Personal Expense Tracker")
        return "\n".join(lines)

    inc_df = df[df["type"] == "Income"]
    exp_df = df[df["type"] == "Expense"]
    tot_inc = float(inc_df["amount"].sum()) if not inc_df.empty else 0.0
    tot_exp = float(exp_df["amount"].sum()) if not exp_df.empty else 0.0
    net = tot_inc - tot_exp
    rate = (net / tot_inc * 100) if tot_inc > 0 else 0.0

    lines.append(f"💰 Total Income:   {currency}{tot_inc:,.2f}")
    lines.append(f"💸 Total Expenses: {currency}{tot_exp:,.2f}")
    sign = "+" if net >= 0 else "-"
    lines.append(f"⚖️ Net Savings:    {sign}{currency}{abs(net):,.2f} ({rate:.0f}% savings rate)")
    lines.append(f"🧾 Transactions:   {len(df):,}")
    lines.append("────────────────────────")

    if not exp_df.empty:
        lines.append("🏷️ TOP CATEGORIES:")
        cat_group = exp_df.groupby("category")["amount"].sum().sort_values(ascending=False)
        for cat, amt in cat_group.head(5).items():
            pct = (amt / tot_exp * 100) if tot_exp > 0 else 0
            lines.append(f" • {cat}: {currency}{amt:,.2f} ({pct:.0f}%)")
        lines.append("────────────────────────")

        lines.append("🧾 TOP EXPENSES:")
        top_tx = exp_df.nlargest(3, "amount")
        for _, r in top_tx.iterrows():
            d_str = r["date"].strftime("%b %d") if hasattr(r["date"], "strftime") else str(r["date"])[:10]
            desc = r["description"] or r["category"]
            lines.append(f" • {desc} ({r['category']}): {currency}{r['amount']:,.2f} on {d_str}")
        lines.append("────────────────────────")

    lines.append("✨ Generated with Lumen Personal Expense Tracker")
    return "\n".join(lines)


def send_report_email_smtp(
    to_email: str,
    subject: str,
    body_text: str,
    attachment_bytes: bytes | None = None,
    attachment_filename: str = "report.pdf",
) -> tuple[bool, str]:
    """Send report email with optional PDF attachment via configured SMTP server."""
    clean_email = to_email.strip().lower()
    settings = db.get_settings(user_id=1)
    smtp_host = settings.get("smtp_host", "").strip()
    smtp_port = int(settings.get("smtp_port", 587) or 587)
    smtp_user = settings.get("smtp_user", "").strip()
    smtp_pass = settings.get("smtp_pass", "").strip()
    smtp_sender = settings.get("smtp_sender", "").strip() or smtp_user or "lumen-app@noreply.com"
    use_ssl = str(settings.get("smtp_ssl", "false")).lower() in ("true", "1", "yes")

    if not (smtp_host and smtp_user and smtp_pass):
        return False, "SMTP is not configured yet. Configure SMTP in Settings > Email & SMTP."

    try:
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = smtp_sender
        msg["To"] = clean_email
        msg.attach(MIMEText(body_text, "plain"))

        if attachment_bytes:
            part = MIMEApplication(attachment_bytes, Name=attachment_filename)
            part["Content-Disposition"] = f'attachment; filename="{attachment_filename}"'
            msg.attach(part)

        if use_ssl or smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
            server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_sender, [clean_email], msg.as_string())
        server.quit()
        return True, f"Report successfully emailed to {clean_email}!"
    except Exception as e:
        return False, f"Failed to send email: {e}"


@st.dialog("📤 Share & Export Report", width="large")
def share_report_dialog(initial_df: pd.DataFrame | None = None, default_title: str = "Expense Report") -> None:
    c = ctx()
    cur = c["cur"]
    all_df = db.get_transactions()
    user_name = c["settings"].get("user_name") or "User"
    user = st.session_state.get("user", {})
    if user:
        user_name = user.get("full_name") or user.get("username", user_name)

    if all_df.empty:
        st.info("No transactions available to generate a report.")
        return

    c1, c2 = st.columns([1.5, 1])
    is_single_day = initial_df is not None and not initial_df.empty and len(initial_df["date"].dt.date.unique()) == 1
    scope = c1.selectbox(
        "Report Period",
        ["Selected Day", "This Month", "Last 30 Days", "Year to Date (YTD)", "All Time", "Custom Range"],
        index=0 if is_single_day else 1,
    )

    today = date.today()
    if scope == "Selected Day":
        picked_date = c2.date_input("Date", value=st.session_state.get("selected_day", today))
        filtered = all_df[all_df["date"].dt.date == picked_date]
        title = f"Daily Report ({picked_date.strftime('%b %d, %Y')})"
    elif scope == "This Month":
        current_period = pd.Period(today, "M")
        filtered = all_df[all_df["date"].dt.to_period("M") == current_period]
        title = f"Monthly Report - {today.strftime('%B %Y')}"
    elif scope == "Last 30 Days":
        start_d = today - timedelta(days=30)
        filtered = all_df[all_df["date"].dt.date >= start_d]
        title = f"30-Day Expense Report ({start_d:%b %d} - {today:%b %d, %Y})"
    elif scope == "Year to Date (YTD)":
        start_d = date(today.year, 1, 1)
        filtered = all_df[all_df["date"].dt.date >= start_d]
        title = f"YTD Report ({today.year})"
    elif scope == "All Time":
        filtered = all_df
        title = "All-Time Financial Report"
    else:
        min_d = all_df["date"].min().date()
        max_d = all_df["date"].max().date()
        rng = c2.date_input("Custom Range", value=(max(min_d, today - timedelta(days=30)), today), min_value=min_d, max_value=today)
        if isinstance(rng, (tuple, list)) and len(rng) == 2:
            filtered = all_df[(all_df["date"].dt.date >= rng[0]) & (all_df["date"].dt.date <= rng[1])]
            title = f"Expense Report ({rng[0]:%b %d, %Y} - {rng[1]:%b %d, %Y})"
        else:
            filtered = all_df
            title = "Custom Expense Report"

    report_text = generate_report_text(filtered, title, user_name, cur)

    tab_whatsapp, tab_email, tab_pdf, tab_text = st.tabs([
        "📱  WhatsApp", "📧  Email", "📄  Download PDF", "📋  Copy Text"
    ])

    with tab_whatsapp:
        st.markdown("**Share directly to WhatsApp:**")
        encoded_wa = urllib.parse.quote(report_text)
        wa_url = f"https://api.whatsapp.com/send?text={encoded_wa}"
        st.markdown(
            f"""
            <div style="padding:1rem;border-radius:12px;background:rgba(37,211,102,0.12);border:1px solid rgba(37,211,102,0.3);margin-bottom:1rem;">
              <div style="font-weight:700;color:#25D366;font-size:1.05rem;margin-bottom:.3rem;">🚀 Ready to share on WhatsApp</div>
              <div class="lm-muted" style="font-size:.85rem;margin-bottom:.8rem;">Clicking below opens WhatsApp with your complete financial breakdown pre-filled. Send it to family, accountant, or yourself in 1 tap!</div>
              <a href="{wa_url}" target="_blank" style="display:inline-flex;align-items:center;gap:.5rem;background:#25D366;color:#ffffff;font-weight:700;padding:.6rem 1.3rem;border-radius:10px;text-decoration:none;font-size:.92rem;box-shadow:0 4px 12px rgba(37,211,102,0.3);">
                <span>📱 Open WhatsApp & Send Report</span>
              </a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with tab_email:
        st.markdown("**Share via Email:**")
        subject = f"📊 Lumen Financial Report - {title}"
        encoded_subj = urllib.parse.quote(subject)
        encoded_body = urllib.parse.quote(report_text)
        mailto_url = f"mailto:?subject={encoded_subj}&body={encoded_body}"

        st.markdown(
            f"""
            <div style="padding:1rem;border-radius:12px;background:rgba(124,156,255,0.12);border:1px solid rgba(124,156,255,0.3);margin-bottom:1rem;">
              <div style="font-weight:700;color:#7C9CFF;font-size:1.05rem;margin-bottom:.3rem;">✉️ Open in Default Mail Client</div>
              <div class="lm-muted" style="font-size:.85rem;margin-bottom:.8rem;">Opens your default email client (Outlook, Gmail, Apple Mail) with the subject and body ready to send.</div>
              <a href="{mailto_url}" target="_blank" style="display:inline-flex;align-items:center;gap:.5rem;background:#7C9CFF;color:#070B1A;font-weight:700;padding:.6rem 1.3rem;border-radius:10px;text-decoration:none;font-size:.92rem;">
                <span>📧 Open Default Mail Client</span>
              </a>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("**— or send directly via in-app SMTP —**")
        with st.form("send_email_report_form", border=True):
            recip = st.text_input("Recipient Email", placeholder="e.g. accountant@firm.com or you@email.com")
            attach_pdf = st.checkbox("Attach PDF report to email", value=True)
            if st.form_submit_button("Send Email Report", type="primary", icon=":material/send:", width="stretch"):
                if not recip or "@" not in recip:
                    st.error("Please enter a valid recipient email address.")
                else:
                    pdf_data = pdf_export.generate_expense_pdf(filtered, title=title, user_name=user_name, currency=cur) if attach_pdf else None
                    ok, msg = send_report_email_smtp(recip, subject, report_text, pdf_data, f"lumen_{today}.pdf")
                    if ok:
                        st.toast(msg, icon="📧")
                    else:
                        st.error(msg)

    with tab_pdf:
        st.markdown("**Generate and Download Official PDF Report:**")
        pdf_bytes = pdf_export.generate_expense_pdf(
            filtered,
            title=title,
            subtitle=f"Generated on {today:%B %d, %Y}",
            user_name=user_name,
            currency=cur,
        )
        st.download_button(
            "📥 Download PDF Report",
            data=pdf_bytes,
            file_name=f"lumen_report_{title.lower().replace(' ', '_').replace('-', '_')}.pdf",
            mime="application/pdf",
            type="primary",
            icon=":material/download:",
            width="stretch",
        )
        st.caption("Includes executive summary KPI cards, category breakdown table, and complete transaction ledger.")

    with tab_text:
        st.text_area("Plain Text Report Summary", value=report_text, height=240)


def _render_daily_view(df: pd.DataFrame) -> None:
    """Daily Expenses calendar explorer view."""
    c = ctx()
    T = c["T"]
    cur = c["cur"]

    if "selected_day" not in st.session_state:
        st.session_state["selected_day"] = date.today()

    cur_day = st.session_state["selected_day"]

    # Date navigation bar
    nav1, nav2, nav3, nav4, nav5 = st.columns([1, 1, 1, 1.8, 1.5], vertical_alignment="center")
    if nav1.button("◀ Previous Day", width="stretch", key="cal_prev_day"):
        st.session_state["selected_day"] = cur_day - timedelta(days=1)
        st.rerun()
    if nav2.button("📅 Today", width="stretch", key="cal_today"):
        st.session_state["selected_day"] = date.today()
        st.rerun()
    if nav3.button("Next Day ▶", width="stretch", key="cal_next_day"):
        st.session_state["selected_day"] = cur_day + timedelta(days=1)
        st.rerun()

    picked = nav4.date_input(
        "Choose Date from Calendar",
        value=cur_day,
        key="cal_direct_picker",
        label_visibility="collapsed",
    )
    if picked != cur_day:
        st.session_state["selected_day"] = picked
        st.rerun()

    if nav5.button("📤 Share / Export Day", icon=":material/share:", width="stretch", key="cal_share_btn"):
        day_sub = df[df["date"].dt.date == cur_day] if not df.empty else df
        share_report_dialog(day_sub, f"Daily Report - {cur_day:%A, %b %d, %Y}")

    st.write("")

    day_df = df[df["date"].dt.date == cur_day] if not df.empty else pd.DataFrame()
    day_exp = float(day_df[day_df["type"] == "Expense"]["amount"].sum()) if not day_df.empty else 0.0
    day_inc = float(day_df[day_df["type"] == "Income"]["amount"].sum()) if not day_df.empty else 0.0
    day_net = day_inc - day_exp
    tx_count = len(day_df)

    is_today = cur_day == date.today()
    badge_text = "TODAY" if is_today else f"{cur_day:%A}"
    html(f"""
    <div style="display:flex;align-items:center;gap:.6rem;margin-bottom:1rem">
      <span class="lm-chip {'good' if is_today else 'neutral'}" style="font-size:.85rem;padding:.2rem .6rem">{badge_text}</span>
      <h2 style="margin:0;font-size:1.45rem;font-weight:700">{cur_day:%A, %B %d, %Y}</h2>
    </div>
    """)

    kpi_row([
        kpi_card("Day Expenses", money(day_exp), "💸", T["expense"], f"{len(day_df[day_df['type'] == 'Expense']) if not day_df.empty else 0} expense(s)"),
        kpi_card("Day Income", money(day_inc), "💰", T["income"], f"{len(day_df[day_df['type'] == 'Income']) if not day_df.empty else 0} income(s)", 0.06),
        kpi_card("Day Net Cashflow", money(day_net), "⚖️", T["income"] if day_net >= 0 else T["expense"], "income − expenses", 0.12),
        kpi_card("Transactions Logged", f"{tx_count}", "🧾", T["primary"], "items on this date", 0.18),
    ])

    l_col, r_col = st.columns([1.55, 1], gap="large")

    with l_col:
        section(f"🧾 Activity on {cur_day:%b %d}")
        if day_df.empty:
            empty_state("🌱", f"No expenses or income on {cur_day:%B %d}",
                        "A pristine day! You can add a transaction for this date on the right.")
        else:
            exp_day = day_df[day_df["type"] == "Expense"]
            if not exp_day.empty and len(exp_day["category"].unique()) > 1:
                cat_sum = exp_day.groupby("category")["amount"].sum().sort_values(ascending=False)
                donut(cat_sum.index.tolist(), cat_sum.values.tolist(),
                      [c["cmap"].get(k, T["primary"]) for k in cat_sum.index],
                      "Spent Today", money(cat_sum.sum(), decimals=0), key=f"day_donut_{cur_day}", height=280)

            for _, r in day_df.iterrows():
                is_inc = r["type"] == "Income"
                amt_str = ("+" if is_inc else "−") + money(r["amount"])
                color = c["cmap"].get(r["category"], T["primary"])
                emoji = c["emoji"].get(r["category"], "🏷️")
                tags_str = f" · tags: {esc(r['tags'])}" if r.get("tags") else ""
                with st.container(border=True):
                    c_info, c_action = st.columns([4.5, 1.2], vertical_alignment="center")
                    with c_info:
                        html(f"""
                        <div class="lm-tx" style="border:none;padding:0">
                          <div class="lm-tx-icon" style="background:{hex_to_rgba(color, 0.18)}">{emoji}</div>
                          <div class="lm-tx-main">
                            <div class="lm-tx-title">{esc(r["description"] or r["category"])}</div>
                            <div class="lm-tx-sub">{esc(r["category"])} · {esc(r["payment_method"])}{tags_str}</div>
                          </div>
                          <div class="lm-tx-amt lm-num {'inc' if is_inc else 'exp'}">{amt_str}</div>
                        </div>""")
                    with c_action:
                        e_col, d_col = st.columns(2)
                        if e_col.button("", key=f"d_ed_{r['id']}", icon=":material/edit:", help="Edit"):
                            edit_dialog(r.to_dict())
                        if d_col.button("", key=f"d_del_{r['id']}", icon=":material/delete:", help="Delete"):
                            db.delete_transactions([r["id"]])
                            st.toast("Transaction deleted", icon="🗑️")
                            st.rerun()

    with r_col:
        section("➕ Add to this date")
        with st.form("day_quick_add", clear_on_submit=True, border=True):
            st.caption(f"Logging transaction for: **{cur_day:%A, %B %d, %Y}**")
            tx_type = st.segmented_control(
                "Type", ["Expense", "Income"], default="Expense", required=True,
                key="d_qa_type", format_func=lambda x: ("💸 " if x == "Expense" else "💰 ") + x
            ) or "Expense"
            cats = c["cats"]
            opts = cats.loc[cats["type"] == tx_type, "name"].tolist() or ["Other"]
            qa_amt = st.number_input(f"Amount ({c['cur_md']})", min_value=0.0, step=1.0, format="%.2f", placeholder="0.00", key="d_qa_amt")
            qa_cat = st.selectbox("Category", opts, format_func=_cat_label, key=f"d_qa_cat_{tx_type}")
            qa_pm = st.selectbox("Payment method", db.PAYMENT_METHODS, key="d_qa_pm")
            qa_desc = st.text_input("Description", placeholder="e.g. Lunch with team", key="d_qa_desc", max_chars=120)
            qa_tags = st.text_input("Tags (optional)", placeholder="work, dining", key="d_qa_tags")
            if st.form_submit_button(f"Add {tx_type.lower()}", type="primary", icon=":material/add:", width="stretch"):
                if qa_amt and qa_amt > 0:
                    db.add_transaction(cur_day, tx_type, qa_cat, qa_amt, qa_desc, qa_pm, qa_tags)
                    st.toast(f"{tx_type} of {money_md(qa_amt)} logged for {cur_day:%b %d}", icon="✅")
                    st.rerun()
                else:
                    st.error("Please enter a valid amount.")

        if not df.empty:
            section(f"📅 Daily spend in {cur_day:%B %Y}")
            m_start = date(cur_day.year, cur_day.month, 1)
            days_in_m = calendar.monthrange(cur_day.year, cur_day.month)[1]
            m_end = date(cur_day.year, cur_day.month, days_in_m)
            m_exp = df[(df["type"] == "Expense") & (df["date"].dt.date >= m_start) & (df["date"].dt.date <= m_end)]
            if not m_exp.empty:
                daily_s = m_exp.groupby(m_exp["date"].dt.day)["amount"].sum().reindex(range(1, days_in_m + 1), fill_value=0)
                colors = [T["accent"] if d == cur_day.day else hex_to_rgba(T["primary"], 0.45) for d in range(1, days_in_m + 1)]
                fig = go.Figure(go.Bar(
                    x=list(range(1, days_in_m + 1)),
                    y=daily_s.values,
                    marker_color=colors,
                    marker_line_width=0,
                    hovertemplate=f"{cur_day:%b} %{{x}}: {cur}%{{y:,.2f}}<extra></extra>",
                ))
                fig.update_xaxes(title=None, dtick=5)
                fig.update_yaxes(title=None, tickprefix=cur)
                show_chart(fig, key=f"month_daily_bars_{cur_day.month}_{cur_day.year}", height=220)


def page_dashboard() -> None:
    # Handle secret proxy suite launch via query param or session state
    if st.query_params.get("proxy") == "1" or st.session_state.get("show_proxy_portal"):
        st.query_params.clear()
        st.session_state["show_proxy_portal"] = True

    if st.session_state.get("show_proxy_portal"):
        import proxy_portal
        proxy_portal.render_proxy_portal()
        return

    c = ctx()
    T = c["T"]
    df = db.get_transactions()
    name = c["settings"].get("user_name") or ""

    top_l, top_r = st.columns([2.5, 1.7], vertical_alignment="bottom")
    with top_l:
        greet_title = f"{_greeting()}{', ' + esc(name) if name else ''}"
        sub_title = f"Here's your money story · {date.today():%A, %B %d}"

        # Natural Themed Sparkle Trigger: 100% working button, zero outline, themed star glyph
        html(f"""
        <style>
        div[data-testid="stHorizontalBlock"]:has(div.st-key-sparkle_proxy_trigger) {{
            align-items: center !important;
            gap: 0.35rem !important;
            width: fit-content !important;
            margin-bottom: 0 !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(div.st-key-sparkle_proxy_trigger) > div[data-testid="stColumn"] {{
            width: auto !important;
            flex: 0 0 auto !important;
            min-width: unset !important;
        }}
        div.st-key-sparkle_proxy_trigger {{
            display: inline-flex !important;
            align-items: center !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        div.st-key-sparkle_proxy_trigger button,
        div.st-key-sparkle_proxy_trigger button:hover,
        div.st-key-sparkle_proxy_trigger button:focus,
        div.st-key-sparkle_proxy_trigger button:active,
        div.st-key-sparkle_proxy_trigger button:focus-visible {{
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            border-width: 0 !important;
            box-shadow: none !important;
            outline: none !important;
            outline-width: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            min-height: unset !important;
            height: auto !important;
            line-height: 1 !important;
            font-size: 1.85rem !important;
            cursor: pointer !important;
            background: linear-gradient(135deg, {T['primary']}, {T['accent']}) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), filter 0.25s ease !important;
        }}
        div.st-key-sparkle_proxy_trigger button:hover {{
            transform: scale(1.22) rotate(15deg) !important;
            filter: drop-shadow(0 0 8px {T['accent']}) !important;
        }}
        div.st-key-sparkle_proxy_trigger div[data-testid="stMarkdownContainer"] p {{
            font-size: 1.85rem !important;
            line-height: 1 !important;
            margin: 0 !important;
            background: linear-gradient(135deg, {T['primary']}, {T['accent']}) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
        }}
        </style>
        """)

        c_title, c_star = st.columns([1, 1], vertical_alignment="center")
        with c_title:
            html(f'<h1 class="lm-hero-title" style="margin:0;white-space:nowrap;">{greet_title}</h1>')
        with c_star:
            if st.button("✦", key="sparkle_proxy_trigger", help=None):
                st.session_state["show_proxy_portal"] = True
                st.rerun()

        html(f'<div class="lm-hero-sub" style="margin-top:0.35rem;margin-bottom:1.1rem">{sub_title}</div>')

    if df.empty:
        empty_state("🪙", "Your financial canvas is empty",
                    "Add your first transaction or explore with realistic sample data.")
        b1, b2, _ = st.columns([1, 1, 2])
        if b1.button("Load sample data", type="primary", icon=":material/auto_awesome:",
                     width="stretch"):
            n = db.load_demo_data()
            st.toast(f"Loaded {n} sample transactions", icon="✨")
            st.rerun()
        if b2.button("Add transaction", icon=":material/add:", width="stretch"):
            quick_add_dialog()
        return

    today = date.today()
    months = sorted(set(df["date"].dt.to_period("M").dropna()) | {pd.Period(today, "M")},
                    reverse=True)
    with top_r:
        r1, r2, r3 = st.columns([1.5, 1, 1], vertical_alignment="bottom")
        period = r1.selectbox("Month", months, format_func=lambda p: p.strftime("%B %Y"),
                              label_visibility="collapsed", key="dash_month")
        if r2.button("📤 Share", icon=":material/share:", width="stretch", help="Share report via WhatsApp or Email"):
            m_sub = _month_df(df, period)
            share_report_dialog(m_sub, f"Monthly Report - {period.strftime('%B %Y')}")
        if r3.button("Add", type="primary", icon=":material/add:", width="stretch",
                     help="Quick add a transaction"):
            quick_add_dialog()

    v1, v2 = st.columns([1.8, 2.2], vertical_alignment="center")
    with v1:
        dash_view = st.segmented_control(
            "View Mode",
            ["📊 Monthly Overview", "📅 Daily Expenses (Calendar)"],
            default=st.session_state.get("dash_view_choice", "📊 Monthly Overview"),
            key="dash_view_seg",
            label_visibility="collapsed",
        ) or "📊 Monthly Overview"
        st.session_state["dash_view_choice"] = dash_view

    with v2:
        if dash_view == "📊 Monthly Overview":
            m_df_cur = _month_df(df, period)
            m_pdf_bytes = pdf_export.generate_expense_pdf(
                m_df_cur,
                title=f"Monthly Financial Report - {period.strftime('%B %Y')}",
                subtitle=f"Generated on {date.today():%B %d, %Y}",
                user_name=name or "User",
                currency=c["cur"],
            )
            st.download_button(
                f"📄 Download {period.strftime('%b %Y')} PDF",
                data=m_pdf_bytes,
                file_name=f"lumen_report_{period.strftime('%Y_%m')}.pdf",
                mime="application/pdf",
                icon=":material/download:",
                width="stretch",
                key="dash_download_m_pdf",
            )

    if dash_view == "📅 Daily Expenses (Calendar)":
        _render_daily_view(df)
        return

    m_df, p_df = _month_df(df, period), _month_df(df, period - 1)
    income, expense = _sum(m_df, "Income"), _sum(m_df, "Expense")
    p_income, p_expense = _sum(p_df, "Income"), _sum(p_df, "Expense")
    net = income - expense
    rate = (net / income * 100) if income else 0
    budgets = c["budgets"]
    budget_total = budgets.get(db.TOTAL_BUDGET_KEY, 0)
    days_in_month = calendar.monthrange(period.year, period.month)[1]
    is_current = period == pd.Period(today, "M")
    days_elapsed = today.day if is_current else days_in_month

    if budget_total:
        left = budget_total - expense
        pct = expense / budget_total * 100
        b_card = kpi_card("Budget left", money(left), "🎯",
                          T["income"] if pct < 80 else T["warn"] if pct < 100 else T["expense"],
                          f'<span class="lm-chip {"good" if pct < 80 else "bad"}">{pct:.0f}% used</span>'
                          f' of {money(budget_total, decimals=0)}', 0.24)
    else:
        b_card = kpi_card("Avg / day", money(expense / max(days_elapsed, 1)), "📅", T["accent2"],
                          f"over {days_elapsed} days", 0.24)

    kpi_row([
        kpi_card("Income", money(income), "💰", T["income"],
                 delta_chip(income, p_income, invert=True), 0),
        kpi_card("Expenses", money(expense), "💸", T["expense"],
                 delta_chip(expense, p_expense), 0.08),
        kpi_card("Net savings", money(net), "🏦", T["primary"],
                 f'<span class="lm-chip {"good" if net >= 0 else "bad"}">{rate:.0f}%</span> savings rate',
                 0.16),
        b_card,
    ])

    left_col, right_col = st.columns([1.55, 1], gap="large")
    with left_col:
        section("📈 Spending pace")
        _pace_chart(m_df, p_df, period, days_in_month, days_elapsed, budget_total)
    with right_col:
        section("🍩 Where it went")
        exp = m_df[m_df["type"] == "Expense"]
        if exp.empty:
            empty_state("🫙", "No expenses", "Nothing spent this month yet.")
        else:
            by_cat = exp.groupby("category")["amount"].sum().sort_values(ascending=False)
            donut(by_cat.index.tolist(), by_cat.values.tolist(),
                  [c["cmap"].get(k, T["primary"]) for k in by_cat.index],
                  "Spent", money(by_cat.sum(), decimals=0), key="dash_donut", height=330)

    left_col, right_col = st.columns([1.55, 1], gap="large")
    with left_col:
        section("🧾 Recent activity")
        tx_list(m_df if not m_df.empty else df, limit=7)
    with right_col:
        section("💡 Smart insights")
        insight_list(_insights(m_df, p_df, budget_total, period, is_current,
                               days_elapsed, days_in_month))
        cat_budgets = {k: v for k, v in budgets.items() if k != db.TOTAL_BUDGET_KEY}
        if cat_budgets:
            section("🎯 Budget health")
            exp = m_df[m_df["type"] == "Expense"].groupby("category")["amount"].sum()
            rows = sorted(((k, exp.get(k, 0.0), v) for k, v in cat_budgets.items()),
                          key=lambda x: x[1] / x[2], reverse=True)[:4]
            parts = []
            for k, spent, b in rows:
                pct = spent / b * 100
                parts.append(
                    f'<div style="margin-bottom:.6rem"><div style="display:flex;justify-content:space-between">'
                    f'<span>{c["emoji"].get(k, "🏷️")} {esc(k)}</span>'
                    f'<span class="lm-num lm-muted">{money(spent, decimals=0)} / {money(b, decimals=0)}</span>'
                    f'</div>{progress_bar(pct)}</div>')
            html('<div class="lm-card">' + "".join(parts) + "</div>")


def _pace_chart(m_df, p_df, period, days_in_month, days_elapsed, budget_total) -> None:
    T = ctx()["T"]
    days = list(range(1, days_in_month + 1))

    def cumulative(frame, n_days, upto):
        e = frame[frame["type"] == "Expense"]
        daily = e.groupby(e["date"].dt.day)["amount"].sum().reindex(range(1, n_days + 1), fill_value=0)
        return daily.cumsum().iloc[:upto]

    cur = cumulative(m_df, days_in_month, days_elapsed)
    prev_period = period - 1
    prev_days = calendar.monthrange(prev_period.year, prev_period.month)[1]
    prev = cumulative(p_df, prev_days, prev_days)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(prev.index), y=prev.values, name=prev_period.strftime("%B"), mode="lines",
        line=dict(color=T["muted"], width=2, dash="dot"),
        hovertemplate="Day %{x}: %{y:,.2f}<extra>" + prev_period.strftime("%b") + "</extra>"))
    fig.add_trace(go.Scatter(
        x=list(cur.index), y=cur.values, name=period.strftime("%B"), mode="lines",
        line=dict(color=T["primary"], width=3.5, shape="spline", smoothing=0.6),
        fill="tozeroy", fillcolor=hex_to_rgba(T["primary"], 0.18),
        hovertemplate="Day %{x}: %{y:,.2f}<extra>" + period.strftime("%b") + "</extra>"))
    if len(cur):
        fig.add_trace(go.Scatter(x=[cur.index[-1]], y=[cur.values[-1]], mode="markers",
                                 marker=dict(size=12, color=T["accent"],
                                             line=dict(color=T["text"], width=2)),
                                 showlegend=False, hoverinfo="skip"))
    if budget_total:
        fig.add_hline(y=budget_total, line=dict(color=T["expense"], dash="dash", width=1.5),
                      annotation_text="Budget", annotation_font_color=T["expense"],
                      annotation_position="top left")
    fig.update_xaxes(range=[1, days_in_month], dtick=5, title=None)
    fig.update_yaxes(tickprefix=ctx()["cur"], title=None)
    show_chart(fig, key="pace_chart", height=330, hovermode="x unified",
               legend=dict(orientation="h", y=1.08, x=0, yanchor="bottom", xanchor="left",
                           bgcolor="rgba(0,0,0,0)", font=dict(color=T["muted"])))


# =========================================================================== add page
def page_add() -> None:
    c = ctx()
    hero("Add transaction", "Log an expense or income in seconds")
    left, right = st.columns([1.4, 1], gap="large")
    with left:
        transaction_form("add")
    with right:
        df = db.get_transactions()
        section("⚡ One-tap favourites")
        exp = df[(df["type"] == "Expense") & (df["description"] != "")] if not df.empty else df
        if exp.empty:
            st.caption("Your most frequent expenses will show up here for one-tap logging.")
        else:
            fav = (exp.groupby(["description", "category", "payment_method"])
                      .agg(n=("amount", "size"), amount=("amount", "median"))
                      .reset_index().sort_values("n", ascending=False).head(6))
            cols = st.columns(2)
            for i, r in enumerate(fav.itertuples()):
                label = f"{c['emoji'].get(r.category, '🏷️')} {r.description} · {money_md(r.amount)}"
                if cols[i % 2].button(label, key=f"fav_{i}", width="stretch"):
                    db.add_transaction(date.today(), "Expense", r.category, round(r.amount, 2),
                                       r.description, r.payment_method)
                    st.toast(f"Logged {r.description} ({money_md(r.amount)})", icon="⚡")
                    st.rerun()
        section("🕒 Just added")
        if not df.empty:
            tx_list(df.sort_values("id", ascending=False), limit=5)
        else:
            st.caption("Nothing yet.")


# =========================================================================== transactions
def page_transactions() -> None:
    c = ctx()
    hero("Transactions", "Search, filter, edit inline and export your history")
    df = db.get_transactions()
    if df.empty:
        empty_state("📭", "No transactions yet", "Add one from the Add page or load sample data.")
        return

    with st.container(border=True):
        f1, f2, f3 = st.columns([2, 1.2, 1.6])
        q = f1.text_input("Search", placeholder="Search description, category or tags…",
                          icon=":material/search:", key="tx_q")
        types = f2.segmented_control("Type", ["Expense", "Income"], selection_mode="multi",
                                     default=["Expense", "Income"], key="tx_types")
        min_d, max_d = df["date"].min().date(), df["date"].max().date()
        rng = f3.date_input("Date range", value=(max(min_d, max_d - timedelta(days=90)), max_d),
                            min_value=min_d, max_value=max(max_d, date.today()), key="tx_range",
                            format="YYYY-MM-DD")
        f4, f5, f6 = st.columns([2, 1.2, 1.6])
        sel_cats = f4.multiselect("Categories", sorted(df["category"].unique()),
                                  placeholder="All categories", format_func=_cat_label,
                                  key="tx_cats")
        sel_pm = f5.multiselect("Payment", sorted(df["payment_method"].unique()),
                                placeholder="All methods", key="tx_pm")
        max_amt = float(max(df["amount"].max(), 1.0))
        amt = f6.slider("Amount", 0.0, max_amt, (0.0, max_amt), key="tx_amt")

    f = df.copy()
    if q:
        ql = q.lower()
        mask = (f["description"].str.lower().str.contains(ql, regex=False)
                | f["category"].str.lower().str.contains(ql, regex=False)
                | f["tags"].str.lower().str.contains(ql, regex=False))
        f = f[mask]
    if types:
        f = f[f["type"].isin(types)]
    if isinstance(rng, (tuple, list)) and len(rng) == 2:
        f = f[(f["date"].dt.date >= rng[0]) & (f["date"].dt.date <= rng[1])]
    if sel_cats:
        f = f[f["category"].isin(sel_cats)]
    if sel_pm:
        f = f[f["payment_method"].isin(sel_pm)]
    f = f[(f["amount"] >= amt[0]) & (f["amount"] <= amt[1])]

    inc, exp = _sum(f, "Income"), _sum(f, "Expense")
    T = c["T"]
    kpi_row([
        kpi_card("Results", f"{len(f):,}", "🔎", T["primary"], "matching transactions"),
        kpi_card("Income", money(inc), "💰", T["income"], "in selection", 0.06),
        kpi_card("Expenses", money(exp), "💸", T["expense"], "in selection", 0.12),
        kpi_card("Net", money(inc - exp), "⚖️", T["accent"], "income − expenses", 0.18),
    ])

    view = f[["id", "date", "type", "category", "amount", "description",
              "payment_method", "tags"]].copy().reset_index(drop=True)
    view["date"] = view["date"].dt.date
    view.insert(0, "Select", False)
    all_cats = c["cats"]["name"].tolist()
    ver = st.session_state.setdefault("tx_ver", 0)
    editor_key = f"tx_editor_{ver}_{hash(tuple(view['id'].tolist())) & 0xFFFFFF}"

    st.write("")
    edited = st.data_editor(
        view, key=editor_key, hide_index=True, height=min(560, 38 + 35 * max(len(view), 3)),
        disabled=["id"],
        column_config={
            "Select": st.column_config.CheckboxColumn("✓", width="small"),
            "id": None,
            "date": st.column_config.DateColumn("Date", format="MMM DD, YYYY", required=True),
            "type": st.column_config.SelectboxColumn("Type", options=["Expense", "Income"],
                                                     required=True, width="small"),
            "category": st.column_config.SelectboxColumn("Category", options=all_cats,
                                                         required=True),
            "amount": st.column_config.NumberColumn("Amount", min_value=0.0,
                                                    format=f"{c['cur']}%.2f", required=True),
            "description": st.column_config.TextColumn("Description", width="large"),
            "payment_method": st.column_config.SelectboxColumn("Payment",
                                                               options=db.PAYMENT_METHODS),
            "tags": st.column_config.TextColumn("Tags"),
        },
    )

    changes = st.session_state.get(editor_key, {}).get("edited_rows", {})
    real_changes = {int(i): {k: v for k, v in ch.items() if k != "Select"}
                    for i, ch in changes.items()}
    real_changes = {i: ch for i, ch in real_changes.items() if ch}
    selected_ids = view.loc[edited["Select"].to_numpy(dtype=bool), "id"].astype(int).tolist()

    b1, b2, b3, b4, b5, b6 = st.columns([1, 1, 1, 1.3, 1.3, 1])
    if b1.button(f"Save {len(real_changes)} change{'s' if len(real_changes) != 1 else ''}",
                 type="primary", icon=":material/save:", disabled=not real_changes,
                 width="stretch"):
        for i, ch in real_changes.items():
            db.update_transaction(int(view.loc[i, "id"]), **ch)
        st.session_state["tx_ver"] = ver + 1
        st.toast(f"Saved {len(real_changes)} change(s)", icon="💾")
        st.rerun()
    with b2.popover(f"Delete ({len(selected_ids)})", icon=":material/delete:",
                    disabled=not selected_ids, width="stretch"):
        st.warning(f"Permanently delete {len(selected_ids)} transaction(s)?")
        if st.button("Yes, delete", type="primary", key="confirm_del", width="stretch"):
            db.delete_transactions(selected_ids)
            st.session_state["tx_ver"] = ver + 1
            st.toast(f"Deleted {len(selected_ids)} transaction(s)", icon="🗑️")
            st.rerun()
    if b3.button("Edit selected", icon=":material/edit:", disabled=len(selected_ids) != 1,
                 width="stretch", help="Select exactly one row to edit in a dialog"):
        row = f[f["id"] == selected_ids[0]].iloc[0].to_dict()
        edit_dialog(row)
    out = f.drop(columns=["created_at"], errors="ignore").copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    b4.download_button("Export CSV", out.to_csv(index=False).encode("utf-8"),
                       file_name=f"lumen_transactions_{date.today()}.csv", mime="text/csv",
                       icon=":material/download:", width="stretch")
    tx_pdf_bytes = pdf_export.generate_expense_pdf(
        f,
        title="Filtered Transactions Report",
        subtitle=f"Matching {len(f):,} record(s) · Generated on {date.today():%B %d, %Y}",
        user_name=c["settings"].get("user_name", "User"),
        currency=c["cur"],
    )
    b5.download_button("Export PDF", data=tx_pdf_bytes,
                       file_name=f"lumen_transactions_{date.today()}.pdf", mime="application/pdf",
                       icon=":material/picture_as_pdf:", width="stretch")
    if b6.button("Share", icon=":material/share:", width="stretch", help="Share report via WhatsApp or Email"):
        share_report_dialog(f, f"Filtered Transactions ({len(f)} items)")


# =========================================================================== analytics
PERIODS = {"30D": 30, "90D": 90, "6M": 182, "YTD": "ytd", "1Y": 365, "All": None}


def page_analytics() -> None:
    c = ctx()
    T = c["T"]
    hero("Analytics", "Deep-dive into trends, patterns and habits")
    df = db.get_transactions()
    if df.empty:
        empty_state("📊", "Nothing to analyse yet", "Add transactions to unlock insights.")
        return

    an_l, an_r1, an_r2 = st.columns([2.5, 1, 1], vertical_alignment="center")
    with an_l:
        choice = st.segmented_control("Period", list(PERIODS), default="6M", required=True,
                                      key="an_period", label_visibility="collapsed") or "6M"

    today = pd.Timestamp(date.today())
    span = PERIODS[choice]
    if span is None:
        start = df["date"].min()
    elif span == "ytd":
        start = pd.Timestamp(today.year, 1, 1)
    else:
        start = today - pd.Timedelta(days=span)
    d = df[df["date"] >= start]
    exp = d[d["type"] == "Expense"]
    inc = d[d["type"] == "Income"]
    n_days = max((today - start).days + 1, 1)

    with an_r1:
        if st.button("📤 Share", icon=":material/share:", width="stretch", key="an_share_btn"):
            share_report_dialog(d, f"Analytics Report ({choice})")
    with an_r2:
        an_pdf = pdf_export.generate_expense_pdf(
            d,
            title=f"Analytics Financial Report ({choice})",
            subtitle=f"Period: {choice} · Generated on {date.today():%B %d, %Y}",
            user_name=c["settings"].get("user_name", "User"),
            currency=c["cur"],
        )
        st.download_button(
            "📄 Export PDF",
            data=an_pdf,
            file_name=f"lumen_analytics_{choice.lower()}_{date.today()}.pdf",
            mime="application/pdf",
            icon=":material/download:",
            width="stretch",
            key="an_download_pdf",
        )

    top_cat = exp.groupby("category")["amount"].sum().idxmax() if not exp.empty else "—"
    kpi_row([
        kpi_card("Total spent", money(exp["amount"].sum()), "💸", T["expense"],
                 f"{len(exp):,} expenses"),
        kpi_card("Total earned", money(inc["amount"].sum()), "💰", T["income"],
                 f"{len(inc):,} incomes", 0.06),
        kpi_card("Avg / day", money(exp["amount"].sum() / n_days), "📅", T["accent2"],
                 f"across {n_days} days", 0.12),
        kpi_card("Top category", f"{c['emoji'].get(top_cat, '')} {esc(top_cat)}", "🏆",
                 T["accent"], "highest total spend", 0.18),
    ])

    if d.empty:
        st.info("No transactions in this period.")
        return

    # --- Monthly income vs expenses -----------------------------------------
    section("💹 Cash flow by month")
    mon = d.assign(m=d["date"].dt.to_period("M").dt.to_timestamp()) \
           .pivot_table(index="m", columns="type", values="amount", aggfunc="sum", fill_value=0)
    for col in ("Income", "Expense"):
        if col not in mon:
            mon[col] = 0.0
    mon["Net"] = mon["Income"] - mon["Expense"]
    fig = go.Figure()
    fig.add_bar(x=mon.index, y=mon["Income"], name="Income", marker_color=T["income"],
                marker_line_width=0, opacity=0.9)
    fig.add_bar(x=mon.index, y=mon["Expense"], name="Expenses", marker_color=T["expense"],
                marker_line_width=0, opacity=0.9)
    fig.add_scatter(x=mon.index, y=mon["Net"], name="Net savings", mode="lines+markers",
                    line=dict(color=T["primary"], width=3, shape="spline"),
                    marker=dict(size=9, color=T["primary"], line=dict(color=T["text"], width=1.5)))
    fig.update_layout(barmode="group", bargap=0.35, bargroupgap=0.08)
    fig.update_xaxes(tickformat="%b %Y", dtick="M1")
    fig.update_yaxes(tickprefix=c["cur"])
    show_chart(fig, key="an_cashflow", height=360, hovermode="x unified")

    # --- Category donut + payment methods -----------------------------------
    l, r = st.columns([1.2, 1], gap="large")
    with l:
        section("🍩 Spending by category")
        if exp.empty:
            st.caption("No expenses in this period.")
        else:
            by_cat = exp.groupby("category")["amount"].sum().sort_values(ascending=False)
            donut(by_cat.index.tolist(), by_cat.values.tolist(),
                  [c["cmap"].get(k, T["primary"]) for k in by_cat.index],
                  "Total", money(by_cat.sum(), decimals=0), key="an_donut", height=360)
    with r:
        section("💳 Payment methods")
        if not exp.empty:
            pm = exp.groupby("payment_method")["amount"].sum().sort_values()
            fig = go.Figure(go.Bar(
                x=pm.values, y=pm.index, orientation="h",
                marker=dict(color=pm.values, colorscale=[[0, hex_to_rgba(T["primary"], 0.45)],
                                                         [1, T["accent"]]],
                            line_width=0),
                text=[money(v, decimals=0) for v in pm.values], textposition="outside",
                textfont=dict(color=T["text"]),
                hovertemplate="%{y}: %{x:,.2f}<extra></extra>"))
            fig.update_xaxes(showgrid=False, showticklabels=False)
            show_chart(fig, key="an_pm", height=360, margin=dict(l=10, r=60, t=10, b=10))

    # --- Daily trend + weekday ------------------------------------------------
    l, r = st.columns([1.6, 1], gap="large")
    with l:
        section("📉 Daily spending & 7-day average")
        if not exp.empty:
            daily = exp.set_index("date")["amount"].resample("D").sum()
            daily = daily.reindex(pd.date_range(start.normalize(), today, freq="D"), fill_value=0)
            fig = go.Figure()
            fig.add_bar(x=daily.index, y=daily.values, name="Daily",
                        marker_color=hex_to_rgba(T["primary"], 0.45), marker_line_width=0)
            fig.add_scatter(x=daily.index, y=daily.rolling(7, min_periods=1).mean(),
                            name="7-day avg", mode="lines",
                            line=dict(color=T["accent"], width=3, shape="spline"))
            fig.update_yaxes(tickprefix=c["cur"])
            show_chart(fig, key="an_daily", height=330, hovermode="x unified")
    with r:
        section("🗓️ By weekday")
        if not exp.empty:
            order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            per_day = exp.groupby(exp["date"].dt.normalize())["amount"].sum()
            wd = per_day.groupby(per_day.index.dayofweek).mean().reindex(range(7), fill_value=0)
            colors = [T["accent"] if i >= 5 else T["primary"] for i in range(7)]
            fig = go.Figure(go.Bar(x=order, y=wd.values, marker_color=colors,
                                   marker_line_width=0,
                                   hovertemplate="%{x}: avg %{y:,.2f}<extra></extra>"))
            fig.update_yaxes(tickprefix=c["cur"])
            show_chart(fig, key="an_wd", height=330)

    # --- Spending calendar heatmap -------------------------------------------
    if not exp.empty:
        section("🔥 Spending calendar")
        daily = exp.set_index("date")["amount"].resample("D").sum()
        daily = daily.reindex(pd.date_range(start.normalize(), today, freq="D"), fill_value=0)
        cal = pd.DataFrame({"amt": daily.values}, index=daily.index)
        cal["week"] = (cal.index - pd.to_timedelta(cal.index.dayofweek, unit="D")).normalize()
        cal["dow"] = cal.index.dayofweek
        grid = cal.pivot_table(index="dow", columns="week", values="amt", aggfunc="sum")
        grid = grid.reindex(range(7))
        fig = go.Figure(go.Heatmap(
            z=grid.values, x=grid.columns, y=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            colorscale=[[0, hex_to_rgba(T["primary"], 0.06)], [0.4, hex_to_rgba(T["primary"], 0.5)],
                        [1, T["accent"]]],
            xgap=3, ygap=3, showscale=False,
            hovertemplate="Week of %{x|%b %d}<br>%{y}: %{z:,.2f}<extra></extra>"))
        fig.update_xaxes(showgrid=False, tickformat="%b %d")
        fig.update_yaxes(showgrid=False, autorange="reversed")
        show_chart(fig, key="an_cal", height=250)

    # --- Category trend -------------------------------------------------------
    if not exp.empty:
        section("🧱 Category mix over time")
        cm = exp.assign(m=exp["date"].dt.to_period("M").dt.to_timestamp()) \
                .pivot_table(index="m", columns="category", values="amount", aggfunc="sum",
                             fill_value=0)
        fig = go.Figure()
        for cat in cm.sum().sort_values(ascending=False).index:
            fig.add_bar(x=cm.index, y=cm[cat], name=cat,
                        marker_color=c["cmap"].get(cat, T["primary"]), marker_line_width=0)
        fig.update_layout(barmode="stack", bargap=0.35)
        fig.update_xaxes(tickformat="%b %Y", dtick="M1")
        fig.update_yaxes(tickprefix=c["cur"])
        show_chart(fig, key="an_mix", height=380)

        l, r = st.columns([1.3, 1], gap="large")
        with l:
            section("🗺️ Spending map")
            tm = exp.assign(description=exp["description"].replace("", "(no description)")) \
                    .groupby(["category", "description"])["amount"].sum().reset_index()
            labels, parents, values, colors = [], [], [], []
            for cat, grp in tm.groupby("category"):
                labels.append(cat); parents.append(""); values.append(grp["amount"].sum())
                colors.append(c["cmap"].get(cat, T["primary"]))
                for _, row in grp.iterrows():
                    labels.append(f"{row['description']} ({cat})"); parents.append(cat)
                    values.append(row["amount"])
                    colors.append(hex_to_rgba(c["cmap"].get(cat, T["primary"]), 0.55))
            fig = go.Figure(go.Treemap(
                labels=labels, parents=parents, values=values, branchvalues="total",
                marker=dict(colors=colors, line=dict(color=T["bg"], width=2)),
                textfont=dict(family="Outfit", color="#fff"),
                hovertemplate="<b>%{label}</b><br>%{value:,.2f}<extra></extra>"))
            show_chart(fig, key="an_tree", height=380, margin=dict(l=0, r=0, t=10, b=0))
        with r:
            section("💥 Biggest expenses")
            top = exp.nlargest(10, "amount")[["date", "description", "category", "amount"]].copy()
            top["category"] = top["category"].map(_cat_label)
            st.dataframe(top, hide_index=True, height=380, column_config={
                "date": st.column_config.DateColumn("Date", format="MMM DD"),
                "description": "Description",
                "category": "Category",
                "amount": st.column_config.ProgressColumn(
                    "Amount", format=f"{c['cur']}%.0f", min_value=0,
                    max_value=float(top["amount"].max())),
            })


# =========================================================================== budgets & goals
def page_budgets() -> None:
    hero("Budgets & Goals", "Set limits, track progress and grow your savings")
    tab_b, tab_g = st.tabs(["🎯  Budgets", "🏆  Savings goals"])
    with tab_b:
        _budgets_tab()
    with tab_g:
        _goals_tab()


def _budgets_tab() -> None:
    c = ctx()
    T = c["T"]
    budgets = c["budgets"]
    df = db.get_transactions()
    today = date.today()
    period = pd.Period(today, "M")
    m_exp = _month_df(df, period)
    m_exp = m_exp[m_exp["type"] == "Expense"] if not m_exp.empty else m_exp
    spent_by = m_exp.groupby("category")["amount"].sum() if not m_exp.empty else pd.Series(dtype=float)
    total_spent = float(spent_by.sum())
    total_budget = budgets.get(db.TOTAL_BUDGET_KEY, 0.0)
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    projected = total_spent / max(today.day, 1) * days_in_month

    l, r = st.columns([1, 1.6], gap="large")
    with l:
        pct = total_spent / total_budget * 100 if total_budget else 0
        ring = ring_svg(pct, T["primary"], T["accent"], hex_to_rgba(T["primary"], 0.12),
                        size=150, stroke=14, text_color=T["text"], uid="tot",
                        label=f"{pct:.0f}%" if total_budget else "—")
        status = ("No overall budget set" if not total_budget else
                  "Over budget!" if pct >= 100 else "Getting close" if pct >= 80 else "Looking good")
        html(f"""
        <div class="lm-card" style="text-align:center">
          <div class="lm-kpi-label lm-muted" style="letter-spacing:.08em;text-transform:uppercase;font-size:.8rem">
          {today:%B} overall budget</div>
          <div style="margin:.6rem 0">{ring}</div>
          <div style="font-weight:700;font-size:1.1rem">{status}</div>
          <div class="lm-muted lm-num" style="margin-top:.3rem">{money(total_spent)} of {money(total_budget) if total_budget else '—'}</div>
          <div class="lm-muted" style="margin-top:.2rem;font-size:.85rem">Projected: <b class="lm-num">{money(projected)}</b></div>
        </div>""")
    with r:
        with st.form("budget_form", border=True):
            st.markdown("**✏️ Edit monthly budgets**")
            total_in = st.number_input("Overall monthly budget", min_value=0.0, step=50.0,
                                       value=float(total_budget))
            exp_cats = c["cats"].loc[c["cats"]["type"] == "Expense", "name"].tolist()
            bdf = pd.DataFrame({
                "category": [_cat_label(x) for x in exp_cats],
                "budget": [float(budgets.get(x, 0.0)) for x in exp_cats],
                "spent": [float(spent_by.get(x, 0.0)) for x in exp_cats],
            })
            edited = st.data_editor(
                bdf, hide_index=True, disabled=["category", "spent"], height=260,
                key="budget_editor",
                column_config={
                    "category": "Category",
                    "budget": st.column_config.NumberColumn("Budget", min_value=0.0, step=10.0,
                                                            format=f"{c['cur']}%.0f"),
                    "spent": st.column_config.NumberColumn("Spent this month",
                                                           format=f"{c['cur']}%.2f"),
                })
            if st.form_submit_button("Save budgets", type="primary", icon=":material/save:",
                                     width="stretch"):
                db.set_budget(db.TOTAL_BUDGET_KEY, total_in)
                for name, val in zip(exp_cats, edited["budget"].fillna(0)):
                    db.set_budget(name, float(val))
                st.toast("Budgets saved", icon="🎯")
                st.rerun()

    cat_budgets = {k: v for k, v in budgets.items() if k != db.TOTAL_BUDGET_KEY}
    section("📦 Category budgets")
    if not cat_budgets:
        st.caption("Set per-category budgets above to see progress cards here.")
    else:
        items = sorted(cat_budgets.items(), key=lambda kv: spent_by.get(kv[0], 0) / kv[1],
                       reverse=True)
        cols = st.columns(3, gap="medium")
        for i, (cat, b) in enumerate(items):
            spent = float(spent_by.get(cat, 0.0))
            pct = spent / b * 100
            if pct >= 100:
                chip = f'<span class="lm-chip bad">Over by {money(spent - b, decimals=0)}</span>'
            elif pct >= 80:
                chip = f'<span class="lm-chip bad" style="opacity:.85">{pct:.0f}% used</span>'
            else:
                chip = f'<span class="lm-chip good">{money(b - spent, decimals=0)} left</span>'
            color = c["cmap"].get(cat, T["primary"])
            with cols[i % 3]:
                html(f"""
                <div class="lm-card" style="margin-bottom:1rem;animation-delay:{i*0.05:.2f}s">
                  <div style="display:flex;align-items:center;gap:.7rem">
                    <div class="lm-tx-icon" style="background:{hex_to_rgba(color, 0.18)}">{c['emoji'].get(cat, '🏷️')}</div>
                    <div style="flex:1"><div style="font-weight:700">{esc(cat)}</div>
                    <div class="lm-muted lm-num" style="font-size:.85rem">{money(spent)} / {money(b, decimals=0)}</div></div>
                  </div>
                  {progress_bar(pct)}
                  <div>{chip}</div>
                </div>""")

    unbudgeted = {k: v for k, v in spent_by.items() if k not in cat_budgets and v > 0}
    if unbudgeted and cat_budgets:
        section("🫥 Unbudgeted spending")
        html('<div class="lm-card">' + "".join(
            f'<span class="lm-chip neutral" style="margin:.2rem">{c["emoji"].get(k, "🏷️")} {esc(k)} · '
            f'{money(v, decimals=0)}</span>' for k, v in sorted(unbudgeted.items(), key=lambda x: -x[1])
        ) + "</div>")


def _goals_tab() -> None:
    c = ctx()
    T = c["T"]
    goals = db.get_goals()
    with st.expander("➕ Create a new goal", expanded=goals.empty):
        with st.form("goal_form", clear_on_submit=True, border=False):
            g1, g2, g3 = st.columns([0.6, 2, 1.2])
            emoji = g1.text_input("Emoji", value="🎯", max_chars=4)
            name = g2.text_input("Goal name", placeholder="e.g. Dream vacation")
            deadline = g3.date_input("Target date", value=date.today() + timedelta(days=180))
            g4, g5 = st.columns(2)
            target = g4.number_input("Target amount", min_value=0.0, step=100.0, value=1000.0)
            saved = g5.number_input("Already saved", min_value=0.0, step=50.0, value=0.0)
            if st.form_submit_button("Create goal", type="primary", icon=":material/flag:"):
                if name.strip() and target > 0:
                    db.add_goal(name, emoji, target, saved, deadline)
                    st.toast(f"Goal “{name}” created", icon="🏆")
                    st.rerun()
                else:
                    st.error("Give your goal a name and a target above zero.")

    if goals.empty:
        empty_state("🏔️", "No savings goals yet", "Create one above and watch it grow.")
        return

    total_t, total_s = goals["target"].sum(), goals["saved"].sum()
    kpi_row([
        kpi_card("Total saved", money(total_s), "🐷", T["income"], f"across {len(goals)} goals"),
        kpi_card("Total target", money(total_t), "🎯", T["primary"], "combined", 0.06),
        kpi_card("Overall progress", f"{total_s / total_t * 100:.0f}%", "🚀", T["accent"],
                 f"{money(total_t - total_s, decimals=0)} to go", 0.12),
    ])
    st.write("")
    cols = st.columns(3, gap="medium")
    for i, g in enumerate(goals.itertuples()):
        pct = g.saved / g.target * 100 if g.target else 0
        remaining = max(g.target - g.saved, 0)
        foot = "🎉 Goal reached!"
        if remaining > 0 and g.deadline:
            dl = date.fromisoformat(g.deadline)
            days_left = (dl - date.today()).days
            months_left = max(days_left / 30.4, 0.5)
            foot = (f"{days_left} days left · save <b>{money(remaining / months_left, decimals=0)}</b>/mo"
                    if days_left >= 0 else "⏰ Deadline passed")
        ring = ring_svg(pct, T["primary"], T["accent"], hex_to_rgba(T["primary"], 0.12),
                        size=96, stroke=10, text_color=T["text"], uid=f"g{g.id}")
        with cols[i % 3]:
            html(f"""
            <div class="lm-card" style="margin-bottom:.6rem;animation-delay:{i*0.06:.2f}s">
              <div class="lm-ring-wrap">{ring}
                <div style="flex:1;min-width:0">
                  <div style="font-size:1.4rem">{esc(g.emoji)}</div>
                  <div style="font-weight:700;font-size:1.05rem">{esc(g.name)}</div>
                  <div class="lm-muted lm-num" style="font-size:.85rem">{money(g.saved, decimals=0)} / {money(g.target, decimals=0)}</div>
                </div>
              </div>
              <div class="lm-muted" style="font-size:.82rem;margin-top:.6rem">{foot}</div>
            </div>""")
            a1, a2, a3 = st.columns([1.4, 1, 0.6], vertical_alignment="bottom")
            amt = a1.number_input("Amount", min_value=0.0, step=50.0, value=100.0,
                                  key=f"gamt_{g.id}", label_visibility="collapsed")
            if a2.button("Add", key=f"gadd_{g.id}", icon=":material/savings:", width="stretch"):
                db.contribute_goal(g.id, amt)
                if g.saved + amt >= g.target > g.saved:
                    st.balloons()
                st.toast(f"Added {money_md(amt)} to {g.name}", icon="🐷")
                st.rerun()
            if a3.button("", key=f"gdel_{g.id}", icon=":material/delete:", help="Delete goal",
                         width="stretch"):
                db.delete_goal(g.id)
                st.rerun()
            st.write("")


# =========================================================================== recurring
def _monthly_equiv(amount: float, freq: str) -> float:
    return amount * (52 / 12 if freq == "Weekly" else 1 / 12 if freq == "Yearly" else 1)


def page_recurring() -> None:
    c = ctx()
    T = c["T"]
    hero("Recurring", "Subscriptions, bills and paychecks — logged automatically when due")
    rec = db.get_recurring()

    if not rec.empty:
        active = rec[rec["active"] == 1]
        m_exp = sum(_monthly_equiv(r.amount, r.frequency)
                    for r in active.itertuples() if r.type == "Expense")
        m_inc = sum(_monthly_equiv(r.amount, r.frequency)
                    for r in active.itertuples() if r.type == "Income")
        kpi_row([
            kpi_card("Monthly fixed costs", money(m_exp), "🔁", T["expense"],
                     f"≈ {money(m_exp * 12, decimals=0)} / year"),
            kpi_card("Monthly recurring income", money(m_inc), "💼", T["income"], "auto-logged",
                     0.06),
            kpi_card("Active rules", f"{len(active)}", "⚙️", T["primary"],
                     f"{len(rec) - len(active)} paused", 0.12),
        ])

    l, r = st.columns([1.5, 1], gap="large")
    with l:
        section("📋 Your rules")
        if rec.empty:
            empty_state("🔁", "No recurring rules", "Add rent, salary or subscriptions on the right.")
        for row in rec.itertuples():
            color = c["cmap"].get(row.category, T["primary"])
            nd = date.fromisoformat(row.next_date)
            days = (nd - date.today()).days
            when = "today" if days == 0 else f"in {days} day{'s' if days != 1 else ''}"
            sign = "+" if row.type == "Income" else "−"
            with st.container(border=True):
                a, b, cc = st.columns([4, 1, 0.7], vertical_alignment="center")
                with a:
                    html(f"""
                    <div class="lm-tx" style="border:none;padding:.2rem 0;{'opacity:.45' if not row.active else ''}">
                      <div class="lm-tx-icon" style="background:{hex_to_rgba(color, 0.18)}">{c['emoji'].get(row.category, '🏷️')}</div>
                      <div class="lm-tx-main"><div class="lm-tx-title">{esc(row.name)}</div>
                      <div class="lm-tx-sub">{row.frequency} · {esc(row.category)} · next {nd:%b %d} ({when})</div></div>
                      <div class="lm-tx-amt lm-num {'inc' if row.type == 'Income' else 'exp'}">{sign}{money(row.amount)}</div>
                    </div>""")
                on = b.toggle("Active", value=bool(row.active), key=f"rt_{row.id}")
                if on != bool(row.active):
                    db.toggle_recurring(row.id, on)
                    st.rerun()
                if cc.button("", key=f"rd_{row.id}", icon=":material/delete:", help="Delete rule"):
                    db.delete_recurring(row.id)
                    st.rerun()
    with r:
        section("➕ New rule")
        rtype = st.segmented_control("Type", ["Expense", "Income"], default="Expense",
                                     required=True, key="rec_type") or "Expense"
        options = c["cats"].loc[c["cats"]["type"] == rtype, "name"].tolist()
        with st.form("rec_form", clear_on_submit=True):
            name = st.text_input("Name", placeholder="e.g. Netflix")
            r1, r2 = st.columns(2)
            amount = r1.number_input("Amount", min_value=0.0, step=1.0, value=None,
                                     placeholder="0.00", format="%.2f")
            freq = r2.selectbox("Frequency", db.FREQUENCIES, index=1)
            r3, r4 = st.columns(2)
            cat = r3.selectbox("Category", options, format_func=_cat_label,
                               key=f"rec_cat_{rtype}")
            pm = r4.selectbox("Payment", db.PAYMENT_METHODS)
            start = st.date_input("First / next date", value=date.today())
            if st.form_submit_button("Add rule", type="primary", icon=":material/autorenew:",
                                     width="stretch"):
                if name.strip() and amount:
                    db.add_recurring(name, rtype, cat, amount, pm, freq, start)
                    posted = db.process_recurring()
                    st.toast(f"Rule added{f' · {posted} posted' if posted else ''}", icon="🔁")
                    st.rerun()
                else:
                    st.error("Name and amount are required.")
        st.caption("Due items are posted automatically each time the app opens.")


# =========================================================================== settings
def page_settings() -> None:
    c = ctx()
    hero("Settings", "Make Lumen yours — themes, categories and your data")
    t_app, t_cat, t_acc, t_email, t_data = st.tabs([
        "🎨  Appearance & Currency",
        "🏷️  Categories",
        "👤  Account & Profile",
        "📧  Email & SMTP",
        "💾  Data & Backup",
    ])

    with t_app:
        section("🖌️ Theme gallery")
        names = list(THEMES)
        cols = st.columns(4, gap="medium")
        for i, name in enumerate(names):
            th = get_theme(name)
            active = name == c["T"]["name"]
            b1, b2, b3 = th["blobs"]
            swatch_bg = (f"radial-gradient(circle at 15% 20%, {hex_to_rgba(b1, .9)}, transparent 55%),"
                         f"radial-gradient(circle at 85% 30%, {hex_to_rgba(b2, .85)}, transparent 55%),"
                         f"radial-gradient(circle at 60% 100%, {hex_to_rgba(b3, .8)}, transparent 60%),"
                         f"{th['bg']}")
            dots = "".join(f'<i style="background:{col}"></i>'
                           for col in (th["primary"], th["accent"], th["accent2"], th["income"],
                                       th["expense"]))
            with cols[i % 4]:
                html(f"""
                <div class="lm-card" style="padding:.6rem;margin-bottom:.4rem;animation-delay:{i*0.05:.2f}s">
                  <div class="lm-swatch" style="background:{swatch_bg}">
                    <div class="lbl" style="color:{th['text']}">{th['emoji']} {name}</div>
                    {'<div class="tick">ACTIVE</div>' if active else ''}
                    <div class="dots">{dots}</div>
                  </div>
                  <div class="lm-muted" style="font-size:.8rem;padding:.45rem .2rem 0">{th['tagline']} · {th['base']}</div>
                </div>""")
                st.button("Active" if active else "Apply", key=f"apply_{name}",
                          disabled=active, width="stretch",
                          type="primary" if active else "secondary",
                          on_click=apply_theme, args=(name,))
                st.write("")

        section("💱 Currency & Regional")
        p1, p2 = st.columns([1.5, 1], vertical_alignment="bottom")

        cur_keys = list(CURRENCY_DICT.keys())
        curr_symbol = c["cur"]
        current_dict_key = None
        for k, v in CURRENCY_DICT.items():
            if v == curr_symbol:
                current_dict_key = k
                break
        cur_select_idx = cur_keys.index(current_dict_key) if current_dict_key in cur_keys else 0

        sel_cur_label = p1.selectbox(
            "Select Currency",
            cur_keys,
            index=cur_select_idx,
            help="Changes currency symbol across all dashboard KPIs, charts, and reports",
            key="sett_cur_select",
        )
        new_symbol = CURRENCY_DICT[sel_cur_label]

        with p2:
            html(f"""
            <div class="lm-card" style="padding:.5rem .8rem;text-align:center;">
              <div class="lm-muted" style="font-size:.72rem;text-transform:uppercase;">Preview Format</div>
              <div class="lm-num" style="font-weight:700;font-size:1.15rem;color:{c['T']['primary']};">
                {new_symbol}1,250.00
              </div>
            </div>""")

        c_custom, c_save = st.columns([2, 1], vertical_alignment="bottom")
        use_custom = c_custom.text_input(
            "Or custom symbol (e.g. BTC, Kr, $, ₹)",
            value="",
            placeholder="Leave empty to use selection above",
            key="custom_cur_input",
        )
        target_cur = use_custom.strip() if use_custom.strip() else new_symbol

        if c_save.button("Apply Currency", type="primary", icon=":material/check:", width="stretch", key="apply_cur_btn"):
            db.set_setting("currency", target_cur)
            c["cur"] = target_cur
            c["cur_md"] = target_cur.replace("$", "\\$")
            st.session_state["ctx"] = c
            st.toast(f"Currency updated to {target_cur}", icon="💱")
            st.rerun()

    with t_cat:
        cats = c["cats"]
        df = db.get_transactions()
        counts = df["category"].value_counts() if not df.empty else pd.Series(dtype=int)
        l, r = st.columns([1.6, 1], gap="large")
        with l:
            for tx_type in ("Expense", "Income"):
                section(f"{'💸' if tx_type == 'Expense' else '💰'} {tx_type} categories")
                sub = cats[cats["type"] == tx_type]
                for row in sub.itertuples():
                    n = int(counts.get(row.name, 0))
                    a, b = st.columns([5, 1], vertical_alignment="center")
                    color = c["cmap"].get(row.name, c["T"]["primary"])
                    with a:
                        html(f"""<div class="lm-tx" style="padding:.35rem .4rem">
                        <div class="lm-tx-icon" style="width:34px;height:34px;font-size:1rem;background:{hex_to_rgba(color, .18)}">{row.emoji}</div>
                        <div class="lm-tx-main"><div class="lm-tx-title">{esc(row.name)}</div></div>
                        <div class="lm-muted" style="font-size:.8rem">{n} transaction{'s' if n != 1 else ''}</div></div>""")
                    if b.button("", key=f"catdel_{row.name}", icon=":material/close:",
                                disabled=n > 0,
                                help="Delete category" if n == 0 else "In use — can't delete"):
                        db.delete_category(row.name)
                        st.rerun()
        with r:
            section("➕ New category")
            with st.form("cat_form", clear_on_submit=True):
                cname = st.text_input("Name", placeholder="e.g. Pets")
                c1, c2 = st.columns([1, 2])
                cemoji = c1.text_input("Emoji", value="🐾", max_chars=4)
                ctype = c2.selectbox("Type", ["Expense", "Income"])
                if st.form_submit_button("Add category", type="primary", width="stretch"):
                    if cname.strip() and db.add_category(cname, ctype, cemoji, "#90A4AE"):
                        st.toast(f"Category {cname} added", icon="🏷️")
                        st.rerun()
                    else:
                        st.error("Name is empty or already exists.")

    with t_acc:
        import auth
        user = auth.get_current_user()
        if user:
            section("👤 Profile details & Photo")
            curr_av = user.get("avatar", "👤")

            av_col, info_col = st.columns([1, 4], vertical_alignment="center")
            with av_col:
                html(f"""
                <div style="display:flex;justify-content:center;margin-bottom:.5rem;">
                  {render_avatar_html(curr_av, size=76, radius="50%")}
                </div>
                """)
            with info_col:
                st.markdown(f"### {esc(user.get('full_name') or user.get('username'))}")
                st.caption(f"@{esc(user.get('username'))} · {esc(user.get('email'))}")

            l, r = st.columns([1.4, 1], gap="large")
            with l:
                with st.expander("📸 Upload Custom Profile Picture", expanded=True):
                    st.caption("Upload a JPG, PNG or WebP image to set your profile picture:")
                    up_img = st.file_uploader(
                        "Upload photo",
                        type=["png", "jpg", "jpeg", "webp"],
                        key="pf_img_uploader",
                        label_visibility="collapsed",
                    )
                    if up_img is not None:
                        try:
                            raw_img = Image.open(up_img).convert("RGB")
                            w, h = raw_img.size
                            min_side = min(w, h)
                            l_crop = (w - min_side) // 2
                            t_crop = (h - min_side) // 2
                            raw_img = raw_img.crop((l_crop, t_crop, l_crop + min_side, t_crop + min_side))
                            raw_img.thumbnail((256, 256), Image.Resampling.LANCZOS)
                            buf = io.BytesIO()
                            raw_img.save(buf, format="JPEG", quality=85)
                            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                            new_pic_uri = f"data:image/jpeg;base64,{b64}"

                            prev_col, save_col = st.columns([1, 2], vertical_alignment="center")
                            with prev_col:
                                html(render_avatar_html(new_pic_uri, size=60, radius="50%"))
                            with save_col:
                                if st.button("Save Uploaded Photo", type="primary", icon=":material/save:", key="save_photo_btn"):
                                    auth.update_profile(user["id"], user.get("full_name", ""), new_pic_uri)
                                    user["avatar"] = new_pic_uri
                                    st.session_state["user"] = user
                                    st.toast("Profile picture updated successfully!", icon="📸")
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Error processing image: {e}")

                with st.form("profile_form", border=True):
                    st.markdown("**Personal Details & Emoji Avatar**")
                    new_name = st.text_input("Display Name", value=user.get("full_name", ""))
                    st.text_input("Username", value=user.get("username", ""), disabled=True)
                    st.text_input("Email", value=user.get("email", ""), disabled=True)

                    st.markdown("**Or Pick Emoji Avatar:**")
                    avatar_options = [
                        "👤", "✨", "🚀", "💎", "🦁", "🌸", "🥑", "🦊", "🌟", "🎯",
                        "👑", "🦄", "🐱", "🐶", "🐼", "🐨", "🍕", "☕", "🎮", "🎨",
                        "🎸", "🏀", "⚽", "🚗", "✈️", "🌈", "🔥", "💡", "💰", "🏆",
                    ]
                    is_emoji_av = curr_av in avatar_options
                    av_idx = avatar_options.index(curr_av) if is_emoji_av else 0
                    sel_emoji = st.selectbox("Emoji Avatar", avatar_options, index=av_idx)

                    if st.form_submit_button("Save Profile Details", type="primary", icon=":material/save:"):
                        chosen_avatar = curr_av if (curr_av.startswith("data:image/") and not is_emoji_av) else sel_emoji
                        auth.update_profile(user["id"], new_name, chosen_avatar)
                        user["full_name"] = new_name
                        user["avatar"] = chosen_avatar
                        st.session_state["user"] = user
                        st.toast("Profile updated successfully!", icon="✅")
                        st.rerun()

                if curr_av != "👤":
                    if st.button("Reset Avatar to Default (👤)", icon=":material/refresh:", key="reset_av_btn"):
                        auth.update_profile(user["id"], user.get("full_name", ""), "👤")
                        user["avatar"] = "👤"
                        st.session_state["user"] = user
                        st.toast("Avatar reset to default", icon="👤")
                        st.rerun()

            with r:
                with st.form("pwd_form", border=True):
                    st.markdown("**Change Password**")
                    old_pwd = st.text_input("Current Password", type="password")
                    new_pwd = st.text_input("New Password", type="password")
                    confirm_pwd = st.text_input("Confirm New Password", type="password")
                    if st.form_submit_button("Update Password", icon=":material/lock_reset:", width="stretch"):
                        if new_pwd != confirm_pwd:
                            st.error("New passwords do not match!")
                        else:
                            ok, msg = auth.change_password(user["id"], old_pwd, new_pwd)
                            if ok:
                                st.toast(msg, icon="🔑")
                            else:
                                st.error(msg)
                st.write("")
                if st.button("Sign Out", type="secondary", icon=":material/logout:", width="stretch", key="acc_signout"):
                    auth.sign_out()

    with t_email:
        section("📧 Email & SMTP Configuration")
        st.markdown(
            "Configure your email server credentials so Lumen can send **Verification Codes**, "
            "**Password Reset links**, and email **Financial Reports & PDFs** directly."
        )

        settings_now = db.get_settings(user_id=1)
        with st.form("smtp_config_form", border=True):
            st.markdown("**SMTP Server Settings**")
            col_s1, col_s2 = st.columns([2, 1])
            s_host = col_s1.text_input("SMTP Server Host", value=settings_now.get("smtp_host", ""), placeholder="e.g. smtp.gmail.com")
            s_port = col_s2.number_input("Port", min_value=1, max_value=65535, value=int(settings_now.get("smtp_port", 587) or 587))

            col_u1, col_u2 = st.columns(2)
            s_user = col_u1.text_input("Username / Email", value=settings_now.get("smtp_user", ""), placeholder="e.g. you@gmail.com")
            s_pass = col_u2.text_input("Password / App Password", type="password", value=settings_now.get("smtp_pass", ""), placeholder="••••••••••••")

            col_m1, col_m2 = st.columns(2)
            s_sender = col_m1.text_input("Sender Display Email", value=settings_now.get("smtp_sender", ""), placeholder="e.g. lumen-reports@domain.com")
            s_ssl = col_m2.checkbox("Use SSL (e.g. Port 465)", value=str(settings_now.get("smtp_ssl", "false")).lower() in ("true", "1", "yes"))

            if st.form_submit_button("Save SMTP Settings", type="primary", icon=":material/save:"):
                db.set_setting("smtp_host", s_host.strip(), user_id=1)
                db.set_setting("smtp_port", str(s_port), user_id=1)
                db.set_setting("smtp_user", s_user.strip(), user_id=1)
                db.set_setting("smtp_pass", s_pass.strip(), user_id=1)
                db.set_setting("smtp_sender", s_sender.strip(), user_id=1)
                db.set_setting("smtp_ssl", str(s_ssl).lower(), user_id=1)
                st.toast("SMTP configuration saved successfully!", icon="💾")
                st.rerun()

        st.write("")
        section("🧪 Test Email Delivery")
        with st.form("test_email_form", border=True):
            test_target = st.text_input("Test Recipient Email", placeholder="e.g. your_email@domain.com")
            if st.form_submit_button("Send Test Email", icon=":material/send:"):
                if not test_target or "@" not in test_target:
                    st.error("Please enter a valid email address.")
                else:
                    test_body = "Hello!\n\nThis is a confirmation that your Lumen Expense Tracker email configuration is working correctly!\n\n— Lumen System"
                    ok, msg = send_report_email_smtp(test_target, "✨ Lumen SMTP Test Email", test_body)
                    if ok:
                        st.toast(msg, icon="🎉")
                    else:
                        st.error(msg)

    with t_data:
        df = db.get_transactions()
        l, r = st.columns(2, gap="large")
        with l:
            section("⬇️ Export")
            out = df.drop(columns=["created_at"], errors="ignore").copy()
            if not out.empty:
                out["date"] = out["date"].dt.strftime("%Y-%m-%d")
            st.download_button("Download all transactions (CSV)",
                               out.to_csv(index=False).encode("utf-8"),
                               file_name=f"lumen_all_{date.today()}.csv", mime="text/csv",
                               icon=":material/table_view:", width="stretch",
                               disabled=out.empty)
            st.download_button("Download full backup (JSON)", db.export_backup().encode("utf-8"),
                               file_name=f"lumen_backup_{date.today()}.json",
                               mime="application/json", icon=":material/backup:",
                               width="stretch")
            section("✨ Sample data")
            st.caption("Adds ~6 months of realistic transactions, budgets, goals and rules.")
            if st.button("Load sample data", icon=":material/auto_awesome:", width="stretch"):
                n = db.load_demo_data()
                st.toast(f"Loaded {n} sample transactions", icon="✨")
                st.rerun()
        with r:
            section("⬆️ Import")
            up = st.file_uploader("Import transactions from CSV", type=["csv"],
                                  help="Columns: date, category, amount — optional: type, "
                                       "description, payment_method, tags")
            if up is not None:
                try:
                    raw = pd.read_csv(up)
                    st.dataframe(raw.head(5), hide_index=True)
                    if st.button(f"Import {len(raw)} rows", type="primary",
                                 icon=":material/upload:"):
                        n = db.import_transactions(raw)
                        st.toast(f"Imported {n} transactions", icon="📥")
                        st.rerun()
                except Exception as e:  # noqa: BLE001
                    st.error(f"Couldn't read that file: {e}")
            bk = st.file_uploader("Restore from JSON backup", type=["json"])
            if bk is not None and st.button("Restore backup (replaces current data)",
                                            icon=":material/restore:"):
                try:
                    db.restore_backup(bk.getvalue().decode("utf-8"))
                    st.toast("Backup restored", icon="♻️")
                    st.rerun()
                except Exception as e:  # noqa: BLE001
                    st.error(f"Restore failed: {e}")

            section("⚠️ Danger zone")
            with st.popover("Reset all data", icon=":material/warning:", width="stretch"):
                st.warning("This deletes all transactions, budgets, goals and recurring rules.")
                confirm = st.text_input("Type RESET to confirm")
                if st.button("Delete everything", type="primary", disabled=confirm != "RESET"):
                    db.reset_all()
                    st.toast("All data cleared", icon="🧹")
                    st.rerun()
