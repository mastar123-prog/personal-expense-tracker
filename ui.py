"""Reusable UI building blocks (HTML cards, rings, lists) and chart helpers."""

from __future__ import annotations

import re

import plotly.graph_objects as go
import streamlit as st

from themes import hex_to_rgba, plotly_layout

_LEADING_WS = re.compile(r"^[ \t]+", re.MULTILINE)


# --------------------------------------------------------------------------- basics
def ctx() -> dict:
    """Per-run context (theme, currency, categories) prepared by app.py."""
    return st.session_state["ctx"]


def html(markup: str) -> None:
    """Render raw HTML safely through st.markdown.

    * Strips indentation so Markdown never treats lines as code blocks.
    * Removes blank lines so the HTML block is not split.
    * Encodes ``$`` so currency values are never parsed as LaTeX math.
    """
    clean = _LEADING_WS.sub("", markup)
    clean = "\n".join(line for line in clean.splitlines() if line.strip())
    st.markdown(clean.replace("$", "&#36;"), unsafe_allow_html=True)


def money(value: float, cur: str | None = None, decimals: int | None = None) -> str:
    cur = cur if cur is not None else ctx()["cur"]
    if decimals is None:
        decimals = 0 if cur in ("¥", "₩") else 2
    sign = "-" if value < 0 else ""
    return f"{sign}{cur}{abs(value):,.{decimals}f}"


def money_md(value: float, cur: str | None = None, decimals: int | None = None) -> str:
    """Money string safe for Markdown contexts (toasts, alerts, captions)."""
    return money(value, cur, decimals).replace("$", "\\$")


def esc(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def hero(title: str, subtitle: str = "") -> None:
    html(f"""
    <div style="margin-bottom:1.1rem">
      <h1 class="lm-hero-title">{title}</h1>
      <div class="lm-hero-sub">{subtitle}</div>
    </div>""")


def section(title: str) -> None:
    html(f'<div class="lm-section">{title}</div>')


def empty_state(icon: str, title: str, sub: str = "") -> None:
    html(f"""
    <div class="lm-card lm-empty">
      <div class="big">{icon}</div>
      <h3 style="margin:.6rem 0 .2rem">{title}</h3>
      <div class="lm-muted">{sub}</div>
    </div>""")


# --------------------------------------------------------------------------- cards
def kpi_card(label: str, value: str, icon: str, color: str, foot: str = "", delay: float = 0) -> str:
    return f"""
    <div class="lm-card lm-kpi" style="--kpi-color:{color};animation-delay:{delay}s">
      <div class="lm-kpi-top">
        <div class="lm-kpi-label">{label}</div>
        <div class="lm-kpi-icon" style="background:{hex_to_rgba(color, 0.16)};color:{color}">{icon}</div>
      </div>
      <div class="lm-kpi-value lm-num">{value}</div>
      <div class="lm-kpi-foot">{foot or '&nbsp;'}</div>
    </div>"""


def kpi_row(cards: list[str]) -> None:
    cols = st.columns(len(cards), gap="medium")
    for col, card in zip(cols, cards):
        with col:
            html(card)


def delta_chip(curr: float, prev: float, invert: bool = False, suffix: str = "vs last month") -> str:
    """Chip showing % change. For expenses, an increase is 'bad' (invert=False)."""
    if prev <= 0:
        return f'<span class="lm-chip neutral">New</span> <span>{suffix}</span>'
    pct = (curr - prev) / prev * 100
    arrow = "▲" if pct >= 0 else "▼"
    good = (pct < 0) if not invert else (pct >= 0)
    cls = "good" if good else "bad"
    return f'<span class="lm-chip {cls}">{arrow} {abs(pct):.1f}%</span> <span>{suffix}</span>'


def progress_bar(pct: float) -> str:
    cls = "over" if pct >= 100 else "warn" if pct >= 80 else ""
    width = max(0.0, min(pct, 100.0))
    return f'<div class="lm-bar {cls}"><span style="width:{width:.1f}%"></span></div>'


def ring_svg(pct: float, c1: str, c2: str, track: str, size: int = 92, stroke: int = 10,
             label: str | None = None, text_color: str = "#fff", uid: str = "r") -> str:
    r = (size - stroke) / 2
    circ = 2 * 3.14159265 * r
    off = circ * (1 - max(0.0, min(pct, 100.0)) / 100)
    label = label if label is not None else f"{pct:.0f}%"
    return f"""<svg class="lm-ring" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
    <defs><linearGradient id="rg{uid}" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs>
    <circle cx="{size/2}" cy="{size/2}" r="{r}" stroke="{track}" stroke-width="{stroke}" fill="none"/>
    <circle class="fg" cx="{size/2}" cy="{size/2}" r="{r}" stroke="url(#rg{uid})" stroke-width="{stroke}"
    fill="none" stroke-linecap="round" stroke-dasharray="{circ:.2f}" stroke-dashoffset="{off:.2f}"
    transform="rotate(-90 {size/2} {size/2})"/>
    <text x="50%" y="52%" text-anchor="middle" dominant-baseline="middle" font-family="Outfit, sans-serif"
    font-weight="700" font-size="{size*0.2:.0f}" fill="{text_color}">{label}</text></svg>"""


def tx_list(df, limit: int = 8) -> None:
    c = ctx()
    if df.empty:
        html('<div class="lm-muted" style="padding:1rem 0">No transactions yet.</div>')
        return
    rows = []
    for _, r in df.head(limit).iterrows():
        color = c["cmap"].get(r["category"], c["T"]["primary"])
        emoji = c["emoji"].get(r["category"], "🏷️")
        is_inc = r["type"] == "Income"
        amt = ("+" if is_inc else "−") + money(r["amount"])
        title = esc(r["description"] or r["category"])
        sub = f'{esc(r["category"])} · {r["date"]:%b %d} · {esc(r["payment_method"])}'
        rows.append(f"""
        <div class="lm-tx">
          <div class="lm-tx-icon" style="background:{hex_to_rgba(color, 0.18)}">{emoji}</div>
          <div class="lm-tx-main"><div class="lm-tx-title">{title}</div><div class="lm-tx-sub">{sub}</div></div>
          <div class="lm-tx-amt lm-num {'inc' if is_inc else 'exp'}">{amt}</div>
        </div>""")
    html('<div class="lm-card" style="padding:.6rem .9rem">' + "".join(rows) + "</div>")


def insight_list(items: list[tuple[str, str]]) -> None:
    if not items:
        return
    html("".join(
        f'<div class="lm-insight" style="animation-delay:{i*0.08:.2f}s"><span class="ico">{ico}</span>'
        f'<span>{txt}</span></div>'
        for i, (ico, txt) in enumerate(items)
    ))


# --------------------------------------------------------------------------- charts
def show_chart(fig: go.Figure, key: str, height: int = 340, **layout) -> None:
    T = ctx()["T"]
    fig.update_layout(**plotly_layout(T, height=height, **layout))
    st.plotly_chart(fig, theme=None, key=key,
                    config={"displayModeBar": False, "responsive": True})


def donut(labels, values, colors, center_title: str, center_value: str, key: str,
          height: int = 340) -> None:
    T = ctx()["T"]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.68, sort=True,
        marker=dict(colors=colors, line=dict(color=T["bg"], width=3)),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>%{value:,.2f}<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        showlegend=True,
        annotations=[dict(
            text=f"<span style='font-size:12px;color:{T['muted']}'>{center_title}</span><br>"
                 f"<b style='font-size:22px'>{center_value}</b>",
            x=0.5, y=0.5, showarrow=False, font=dict(color=T["text"]))],
    )
    show_chart(fig, key=key, height=height,
               legend=dict(orientation="v", x=1.02, y=0.5, yanchor="middle", xanchor="left",
                           font=dict(color=T["muted"]), bgcolor="rgba(0,0,0,0)"),
               margin=dict(l=0, r=0, t=10, b=10))
