"""Lumen Orbit — Integrated Web Proxy, Chatroom, Mirror Links, and Beam AI.

Accessible via the secret '✨' sparkle on the home greeting.
"""

from __future__ import annotations

import html
import http.server
import math
import os
import re
import socket
import threading
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any
from urllib.parse import quote, urlparse

import requests
import streamlit as st
import urllib3

import arcade_games
import db
from themes import hex_to_rgba
from ui import ctx, esc, hero, render_avatar_html, section

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _get_session_val(key: str, default: Any = None) -> Any:
    """Safely get session_state value even when running outside active Streamlit context."""
    try:
        return st.session_state.get(key, default)
    except Exception:
        return default


# ----------------------------------------------------------------------------- Beam AI Engine
def _try_eval_math(text: str) -> str | None:
    """Safely detect and evaluate basic mathematical expressions."""
    t = text.strip()

    # Percentage: e.g. "15% of 850" or "20% 500"
    pct_m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:of\s*)?(\d+(?:\.\d+)?)", t, re.I)
    if pct_m:
        p = float(pct_m.group(1))
        val = float(pct_m.group(2))
        res = (p / 100.0) * val
        return (
            f"🧮 **Calculation Result**:\n\n"
            f"**{p:g}% of {val:,.2f}** = **{res:,.2f}**\n\n"
            f"- Calculation: `({p} / 100) × {val} = {res:,.4f}`"
        )

    # Basic arithmetic: + - * / ** sqrt
    cleaned = re.sub(r"[^0-9\+\-\*\/\.\(\)\s]", "", t).strip()
    if cleaned and any(op in cleaned for op in ("+", "-", "*", "/")) and len(cleaned) >= 3:
        try:
            val = eval(
                cleaned,
                {"__builtins__": {}},
                {"sqrt": math.sqrt, "abs": abs, "round": round, "pow": pow},
            )
            return (
                f"🧮 **Calculation Result**:\n\n"
                f"`{cleaned}` = **{val:,.4g}**"
            )
        except Exception:
            pass
    return None


def _get_finance_snapshot(user_id: int | None = None) -> str:
    """Analyze real SQLite transaction and budget data for personalized insights."""
    try:
        uid = user_id or db.get_current_user_id()
        df = db.get_transactions(uid)
        settings = db.get_settings(uid)
        sym = settings.get("currency", "$")

        if df.empty:
            return (
                "📊 **Personal Financial Snapshot**:\n\n"
                "- You currently have **0 transactions** logged in your account.\n"
                "- Add expenses or income from the **Dashboard** or **Transactions** page, "
                "and I will analyze your spending patterns, savings rate, and category breakdowns here!"
            )

        expenses = df[df["type"] == "Expense"]
        income = df[df["type"] == "Income"]

        tot_exp = float(expenses["amount"].sum()) if not expenses.empty else 0.0
        tot_inc = float(income["amount"].sum()) if not income.empty else 0.0
        net = tot_inc - tot_exp
        savings_rate = (net / tot_inc * 100) if tot_inc > 0 else 0.0

        top_cats_lines = []
        if not expenses.empty:
            cat_sums = expenses.groupby("category")["amount"].sum().sort_values(ascending=False).head(3)
            for c_name, c_amt in cat_sums.items():
                pct = (c_amt / tot_exp * 100) if tot_exp > 0 else 0.0
                top_cats_lines.append(f"  - **{c_name}**: {sym}{c_amt:,.2f} ({pct:.1f}%)")

        status_emoji = "🟢" if net >= 0 else "🔴"
        status_text = "Net Surplus" if net >= 0 else "Net Deficit"

        res = (
            f"📊 **Personal Financial Snapshot (Live Account Data)**:\n\n"
            f"- **Total Income**: `{sym}{tot_inc:,.2f}` across {len(income)} entries\n"
            f"- **Total Expenses**: `{sym}{tot_exp:,.2f}` across {len(expenses)} entries\n"
            f"- **Net Balance**: `{sym}{net:,.2f}` ({status_emoji} {status_text})\n"
            f"- **Savings Rate**: `{savings_rate:.1f}%`\n"
        )

        if top_cats_lines:
            res += f"- **Top Spending Categories**:\n" + "\n".join(top_cats_lines) + "\n\n"

        if net < 0:
            res += "⚠️ **Insight**: Your spending currently exceeds income. Consider reviewing your top categories to optimize discretionary expenses.\n"
        else:
            res += "💡 **Insight**: Healthy positive cashflow! Consider allocating excess surplus into your emergency reserve or investments.\n"

        return res
    except Exception as e:
        return f"📊 *Unable to load financial snapshot at this moment: {e}*"


def _clean_html_tags(raw: str) -> str:
    """Remove HTML tags and decode HTML entities."""
    if not raw:
        return ""
    cleaned = re.sub(r"<[^>]+>", "", raw)
    return html.unescape(cleaned).strip()


def _search_web(query: str, max_results: int = 5) -> dict[str, Any]:
    """Execute live multi-source web search across Wikipedia, Google Web RSS, and HN Algolia."""
    clean_q = re.sub(r"^(search for|search|look up|google|find|browse|web search)\s+", "", query, flags=re.I).strip(" ?.")
    if not clean_q:
        clean_q = query.strip()

    results: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    # 1. Wikipedia Search API (Authoritative encyclopedia knowledge)
    try:
        w_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote(clean_q)}&utf8=&format=json&srlimit=3"
        w_res = requests.get(w_url, headers=headers, timeout=6)
        if w_res.status_code == 200:
            for it in w_res.json().get("query", {}).get("search", []):
                t = it.get("title", "")
                sn = _clean_html_tags(it.get("snippet", ""))
                u = f"https://en.wikipedia.org/wiki/{quote(t.replace(' ', '_'))}"
                if u not in seen_urls and t:
                    seen_urls.add(u)
                    results.append({
                        "source": "Wikipedia",
                        "title": t,
                        "snippet": sn,
                        "url": u,
                        "icon": "📚",
                    })
    except Exception:
        pass

    # 2. Google News & Web RSS (Live news, web articles, media coverage)
    try:
        g_url = f"https://news.google.com/rss/search?q={quote(clean_q)}&hl=en-US&gl=US&ceid=US:en"
        g_res = requests.get(g_url, headers=headers, timeout=6)
        if g_res.status_code == 200:
            root = ET.fromstring(g_res.text)
            for it in root.findall(".//item")[:4]:
                t = it.find("title").text if it.find("title") is not None else ""
                l = it.find("link").text if it.find("link") is not None else ""
                if l and l not in seen_urls and t:
                    seen_urls.add(l)
                    results.append({
                        "source": "Google Web",
                        "title": _clean_html_tags(t),
                        "snippet": f"Recent coverage and web updates on '{clean_q}'.",
                        "url": l,
                        "icon": "🌐",
                    })
    except Exception:
        pass

    # 3. Hacker News Algolia Search (Tech, tools, web applications)
    if len(results) < max_results:
        try:
            hn_url = f"https://hn.algolia.com/api/v1/search?query={quote(clean_q)}&hitsPerPage=3"
            hn_res = requests.get(hn_url, headers=headers, timeout=5)
            if hn_res.status_code == 200:
                for hit in hn_res.json().get("hits", []):
                    t = hit.get("title") or hit.get("story_title")
                    u = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                    if u and u not in seen_urls and t:
                        seen_urls.add(u)
                        results.append({
                            "source": "Tech & Web",
                            "title": _clean_html_tags(t),
                            "snippet": "Community discussion and web project on Hacker News.",
                            "url": u,
                            "icon": "📰",
                        })
        except Exception:
            pass

    return {"query": clean_q, "results": results[:max_results]}


def _format_search_response(search_data: dict[str, Any]) -> str:
    """Format structured search results with one-click Orbit Proxy launchers."""
    q = search_data["query"]
    items = search_data.get("results", [])
    if not items:
        return (
            f"🔍 **Live Web Search: *'{q}'***\n\n"
            f"No direct web results could be retrieved right now. "
            f"You can search directly inside the **'Web Proxy'** tab using [DuckDuckGo](https://html.duckduckgo.com/html/) or Wikipedia!"
        )

    lines = [
        f"🔍 **Live Web Search Results for: *'{q}'***\n",
        f"Found {len(items)} top resources across live web sources:\n",
    ]
    for i, it in enumerate(items, 1):
        icon = it.get("icon", "🌐")
        title = it.get("title", "Resource")
        src = it.get("source", "Web")
        sn = it.get("snippet", "")
        u = it.get("url", "")
        proxy_href = f"?proxy_url={quote(u, safe='')}"

        lines.append(
            f"**{i}. {icon} [{title}]({u})**  \n"
            f"*{src}* — {sn}  \n"
            f"👉 [🌐 Open in Orbit Web Proxy]({proxy_href}) &nbsp;|&nbsp; [Direct Link ↗]({u})\n"
        )

    lines.append(
        "\n💡 *Tip: Click 'Open in Orbit Web Proxy' on any result to stream and interact with it inside Orbit!*"
    )
    return "\n".join(lines)


def _beam_respond(prompt: str, user_id: int | None = None) -> str:
    """Generate intelligent, accurate responses using live search, AI, local database, or built-in knowledge."""
    p_lower = prompt.lower().strip()

    # 1. Explicit or Mode-based Web Search
    is_search_intent = (
        p_lower.startswith(("/search", "search ", "search for ", "find ", "look up ", "google ", "web search ", "browse "))
        or _get_session_val("beam_search_mode", False)
    )
    if is_search_intent:
        search_data = _search_web(prompt)
        return _format_search_response(search_data)

    # 2. Financial analysis from local SQLite database
    if any(k in p_lower for k in ("my expense", "my spending", "how much did i spend", "my budget", "my balance", "my money", "financial snapshot", "analyze my", "spending summary")):
        return _get_finance_snapshot(user_id)

    # 3. Math evaluation
    math_ans = _try_eval_math(prompt)
    if math_ans:
        return math_ans

    # 4. Question-based web search intent (who is, what is, where is, etc.)
    if any(p_lower.startswith(q) for q in ("who is ", "who was ", "what is ", "what was ", "where is ", "when was ", "tell me about ", "latest news", "news on ", "find me ")):
        search_data = _search_web(prompt)
        if search_data.get("results"):
            return _format_search_response(search_data)

    # 5. Optional Gemini API integration (if user entered key or set in environment)
    gemini_key = _get_session_val("beam_gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            if response and response.text:
                return response.text
        except Exception:
            pass

    # 6. Live Cloud AI completion via Pollinations (Fast, free, reliable, no auth required)
    try:
        url = "https://text.pollinations.ai/"
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Beam, an intelligent, helpful, and concise AI companion inside the Lumen Orbit "
                        "Proxy Suite. Provide direct, informative, well-structured answers using Markdown. "
                        "Help users with web search, coding, math, general science, trivia, and finance."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "model": "openai",
            "seed": 42,
        }
        res = requests.post(url, json=payload, timeout=7)
        if res.status_code == 200 and res.text.strip():
            return res.text.strip()
    except Exception:
        pass

    # 7. Live Web Search fallback before offline templates
    try:
        search_data = _search_web(prompt)
        if search_data.get("results"):
            return _format_search_response(search_data)
    except Exception:
        pass

    # 8. Comprehensive Offline Knowledge & Conversational Engine
    # Technical proxy & header issues (targeted check, does not hijack search queries)
    if any(w in p_lower for w in ("how does the proxy work", "how does a proxy work", "refused to connect", "csp header", "frame-ancestors", "x-frame-options", "why does a site block")):
        return (
            "🌐 **Why 'Refused to Connect' Happens & How Orbit Solves It**:\n\n"
            "1. **Why Sites Refuse to Connect**:\n"
            "   High-security sites like Google Translate (`*.translate.goog`), Poki, or banks send HTTP response headers:\n"
            "   - `X-Frame-Options: SAMEORIGIN`\n"
            "   - `Content-Security-Policy: frame-ancestors ...`\n"
            "   When loaded directly in an iframe, the browser enforces these headers and refuses to connect.\n\n"
            "2. **The Working Solution: ⚡ Smart Web Proxy (Direct Stream)**:\n"
            "   - Our Python engine fetches the target site server-side.\n"
            "   - Strips all `X-Frame-Options`, CSP, and frame-busting scripts.\n"
            "   - Injects `<base href>` so CSS, images, and links resolve seamlessly.\n"
            "   - Serves the unblocked page locally with zero header restrictions!\n\n"
            "💡 *Tip: Ensure the Proxy Engine is set to **'⚡ Smart Web Proxy (Direct Stream)'**.*"
        )

    # Poki / Games queries
    if any(w in p_lower for w in ("poki", "game", "games", "play", "arcade", "retro bowl", "subway surfers")):
        return (
            "🎮 **Interactive Games on Lumen Orbit**:\n\n"
            "- You can play **Poki games, 2048, Retro Bowl, Subway Surfers**, and unblocked web games right inside Orbit!\n"
            "- Go to the **'Web Proxy'** tab and select **'🌐 Interactive Web Gateway'** or **'🎮 Playable Web Games'**.\n"
            "- We automatically grant pointer-lock, WebGL, gamepad, and audio permissions so games run smoothly without 'refused to connect' errors!"
        )

    # General Greetings
    if any(w in p_lower for w in ("hello", "hi", "hey", "who are you", "what is beam")):
        return (
            "⚡ **Greetings! I am Beam**, your integrated AI companion in Lumen Orbit.\n\n"
            "I can answer questions, analyze numbers, explain complex topics, research concepts, "
            "and inspect your financial data. Try asking me:\n"
            "- *'What are my total expenses?'*\n"
            "- *'What is 15% of 850?'*\n"
            "- *'How does a reverse proxy bypass CSP headers?'*\n"
            "- *'Explain quantum computing in simple terms'*"
        )

    # Finance Strategy
    if any(w in p_lower for w in ("save", "budget", "invest", "money", "debt", "emergency fund")):
        return (
            "💡 **Core Principles of Financial Health**:\n\n"
            "1. **The 50/30/20 Framework**: Allocate 50% of net income to Needs (housing, utilities, food), 30% to Wants (hobbies, dining out), and 20% to Savings and Debt payoff.\n"
            "2. **Emergency Buffer**: Strive for 3–6 months of non-negotiable living expenses stored in a liquid, high-yield account.\n"
            "3. **Pay Yourself First**: Automate transfers to your savings or investment account on the exact day your paycheck arrives.\n"
            "4. **Compound Interest**: Investing even $100/month at an average 8% annual return yields over $150,000 across 30 years."
        )

    # Tech & Programming
    if any(w in p_lower for w in ("python", "code", "streamlit", "sqlite", "javascript", "html", "css", "api")):
        return (
            f"⚡ **Technical Insight on: *'{prompt}'***\n\n"
            "- **Architecture**: Lumen is built using a reactive Python & Streamlit frontend backed by a robust SQLite persistence engine.\n"
            "- **Proxy Layer**: Uses server-side header rewriting, `<base>` injection, CSP stripping, and reverse-proxy translation to embed interactive web content safely.\n"
            "- **Tip**: If you have a specific programming question, bug, or snippet you want analyzed, paste it here and I'll break it down for you!"
        )

    # Deep Contextual Fallback Answer
    return (
        f"⚡ **Beam Analysis for: *'{prompt}'***\n\n"
        f"Here is what you need to know:\n\n"
        f"- **Core Overview**: Your query pertains to **{prompt}**. When exploring this topic, key factors include "
        f"understanding the underlying mechanisms, verifying primary sources, and applying practical steps.\n"
        f"- **Actionable Insight**: You can use the **'Web Proxy'** tab above to research this topic across Wikipedia, DuckDuckGo, "
        f"or live web portals, or ask me for a specific calculation, definition, or strategy breakdown.\n"
        f"- **Need More Details?**: Feel free to ask follow-up questions, request step-by-step guides, or ask for financial calculations!"
    )


# ----------------------------------------------------------------------------- Local IP Helper
def _get_local_ip() -> str:
    """Detect active local LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ----------------------------------------------------------------------------- Main Render Function
def render_proxy_portal() -> None:
    """Render the full-featured Lumen Orbit Proxy Suite."""
    c = ctx()
    T = c["T"]
    user = st.session_state.get("user", {})
    user_name = user.get("full_name") or user.get("username", "Explorer")
    avatar = user.get("avatar", "👤")

    # Check if a search result or query param requested a specific proxy target
    qp_proxy = st.query_params.get("proxy_url")
    if qp_proxy:
        st.session_state["proxy_target_url"] = qp_proxy
        st.session_state["proxy_active_url"] = qp_proxy
        st.session_state["proxy_input_val"] = qp_proxy
        st.session_state["proxy_mode_sel"] = "⚡ Smart Web Proxy (Direct Stream - Bypasses Header Blocks)"
        hist = st.session_state.get("proxy_history", [])
        if not hist or hist[-1] != qp_proxy:
            hist.append(qp_proxy)
            st.session_state["proxy_history"] = hist
        st.query_params.clear()

    # Header Bar
    top_col1, top_col2 = st.columns([5, 1.2], vertical_alignment="center")
    with top_col1:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.5rem">
              <span style="font-size:2.2rem;display:inline-block;animation:lm-float 3s ease-in-out infinite">🌌</span>
              <div>
                <h1 style="margin:0;font-size:1.85rem;font-weight:800;letter-spacing:-0.02em;background:linear-gradient(135deg, {T['primary']}, {T['accent']});-webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                  Lumen Orbit · Interactive Proxy Suite
                </h1>
                <div class="lm-muted" style="font-size:.88rem">
                  Interactive Web Proxy & Unblocker · Live Chatroom · Mirror Links · In-Built Beam AI Agent
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top_col2:
        if st.button("✖ Exit Orbit", icon=":material/close:", width="stretch", type="primary", key="close_orbit_btn"):
            st.session_state["show_proxy_portal"] = False
            st.query_params.clear()
            st.rerun()

    st.write("")

    # Navigation Tabs
    tab_proxy, tab_chat, tab_mirror, tab_beam = st.tabs([
        "🌐  Web Proxy & Games",
        "💬  Chatroom",
        "🔗  Mirror Links",
        "⚡  Beam AI Agent",
    ])

    # ------------------------------------------------------------------------- Tab 1: Web Proxy
    with tab_proxy:
        section("🌐 Interactive Web Proxy & Unblocker")
        st.caption("Browse web pages, unblock filtered sites, play games, and interact freely inside Lumen:")

        # Track navigation history
        if "proxy_history" not in st.session_state:
            st.session_state["proxy_history"] = []

        # Quick preset buttons (Games + Tools)
        st.markdown("<div style='font-size:0.8rem;font-weight:600;margin-bottom:6px;color:#8B93B5;'>⚡ QUICK LAUNCH PRESETS:</div>", unsafe_allow_html=True)
        preset_cols = st.columns(6)

        def _launch_arcade(game_title: str) -> None:
            st.session_state["proxy_mode_sel"] = "🎮 Playable Web Games (Arcade Hub)"
            st.session_state["arcade_selected"] = game_title
            st.rerun()

        def _set_preset(u: str, eng: str = "⚡ Smart Web Proxy (Direct Stream - Bypasses Header Blocks)") -> None:
            st.session_state["proxy_target_url"] = u
            st.session_state["proxy_active_url"] = u
            st.session_state["proxy_input_val"] = u
            st.session_state["proxy_mode_sel"] = eng
            hist = st.session_state.get("proxy_history", [])
            if not hist or hist[-1] != u:
                hist.append(u)
                st.session_state["proxy_history"] = hist
            st.rerun()

        if preset_cols[0].button("🎮 2048 Arcade", width="stretch", key="ps_2048", help="Instant Playable 2048 Game"):
            _launch_arcade("2048")
        if preset_cols[1].button("🟩 Wordle Game", width="stretch", key="ps_wordle", help="Instant Playable Wordle Unlimited"):
            _launch_arcade("Wordle")
        if preset_cols[2].button("🐍 Snake Retro", width="stretch", key="ps_snake", help="Instant Playable Retro Snake"):
            _launch_arcade("Snake")
        if preset_cols[3].button("🌐 Wikipedia", width="stretch", key="ps_wiki", help="Interactive Wikipedia"):
            _set_preset("https://en.wikipedia.org/wiki/Main_Page")
        if preset_cols[4].button("📰 Hacker News", width="stretch", key="ps_hn", help="Tech News & Discussions"):
            _set_preset("https://news.ycombinator.com")
        if preset_cols[5].button("🔍 DuckDuckGo", width="stretch", key="ps_ddg", help="Private Web Search"):
            _set_preset("https://html.duckduckgo.com/html/")

        default_target = st.session_state.get("proxy_target_url", "https://en.wikipedia.org/wiki/Main_Page")
        active_current = st.session_state.get("proxy_active_url", default_target)
        if "proxy_input_val" not in st.session_state:
            st.session_state["proxy_input_val"] = active_current

        # Ensure active_url is in history
        if not st.session_state["proxy_history"]:
            st.session_state["proxy_history"] = [active_current]

        # Navigation Bar Form
        with st.form("proxy_nav_bar_form", border=False):
            u_col1, u_col2, u_col3 = st.columns([3.1, 1.6, 0.8], vertical_alignment="bottom")
            url_input = u_col1.text_input(
                "Target Website URL",
                value=st.session_state["proxy_input_val"],
                placeholder="e.g. https://en.wikipedia.org/ or https://news.ycombinator.com",
                key="proxy_url_input_box",
            )
            modes = [
                "⚡ Smart Web Proxy (Direct Stream - Bypasses Header Blocks)",
                "📖 Universal Web Reader (Bypasses 100% of Iframe Blocks)",
                "🎮 Playable Web Games (Arcade Hub)",
                "🛡️ Multi-Proxy Mirror Launcher",
            ]
            current_mode = st.session_state.get("proxy_mode_sel", modes[0])
            mode_idx = modes.index(current_mode) if current_mode in modes else 0
            mode = u_col2.selectbox("Proxy Engine", modes, index=mode_idx, key="proxy_mode_sel")
            browse_clicked = u_col3.form_submit_button("🚀 Go", type="primary", width="stretch")

            if browse_clicked and url_input.strip():
                clean_target = url_input.strip()
                if not clean_target.startswith(("http://", "https://")):
                    clean_target = "https://" + clean_target
                st.session_state["proxy_target_url"] = clean_target
                st.session_state["proxy_active_url"] = clean_target
                st.session_state["proxy_input_val"] = clean_target
                hist = st.session_state.get("proxy_history", [])
                if not hist or hist[-1] != clean_target:
                    hist.append(clean_target)
                    st.session_state["proxy_history"] = hist
                st.rerun()

        active_url = st.session_state.get("proxy_active_url", default_target).strip()
        if not active_url.startswith(("http://", "https://")):
            active_url = "https://" + active_url

        # Proxy toolbar & interactive controls
        tb_col1, tb_col2 = st.columns([3.0, 3.0], vertical_alignment="center")
        with tb_col1:
            st.markdown(
                f"""
                <div style="font-size:.88rem;color:{T['text']};padding:.3rem 0;display:flex;align-items:center;gap:.5rem;">
                  <span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#10B981;"></span>
                  <span>Active Target:</span>
                  <b style="color:{T['accent']};word-break:break-all;">{esc(active_url)}</b>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with tb_col2:
            hist = st.session_state.get("proxy_history", [])
            has_back = len(hist) > 1
            is_theater = st.session_state.get("proxy_theater_mode", False)

            if has_back:
                m0, m1, m2, m3, m4 = st.columns([1, 1, 1.2, 1, 1])
                with m0:
                    if st.button("⬅️ Back", width="stretch", key="proxy_back_btn", help="Go back to previous page"):
                        hist.pop()  # remove current
                        prev_u = hist[-1]
                        st.session_state["proxy_target_url"] = prev_u
                        st.session_state["proxy_active_url"] = prev_u
                        st.session_state["proxy_input_val"] = prev_u
                        st.session_state["proxy_history"] = hist
                        st.rerun()
            else:
                m1, m2, m3, m4 = st.columns(4)

            with m1:
                if st.button("🔄 Reload", width="stretch", key="proxy_reload_btn", help="Reload the proxied window"):
                    st.rerun()
            with m2:
                th_label = "🗗 Standard" if is_theater else "⛶ Theater"
                if st.button(th_label, width="stretch", key="proxy_theater_btn", help="Toggle expanded view height"):
                    st.session_state["proxy_theater_mode"] = not is_theater
                    st.rerun()
            with m3:
                st.link_button("↗ Popout", active_url, width="stretch", help="Open directly in a new browser tab")
            with m4:
                st.link_button("🛡️ 12ft", f"https://12ft.io/{active_url}", width="stretch", help="Unblock with 12ft ladder")

        frame_height = 960 if st.session_state.get("proxy_theater_mode", False) else 780
        iframe_sandbox = "allow-same-origin allow-scripts allow-forms allow-popups allow-pointer-lock allow-modals allow-downloads allow-presentation"
        iframe_allow = "accelerometer; autoplay; camera; clipboard-read; clipboard-write; display-capture; encrypted-media; fullscreen; gamepad; geolocation; gyroscope; microphone; midi; payment; picture-in-picture; screen-wake-lock; web-share"

        # --------------------------------------------------------------------- Mode 1: Smart Direct Stream
        if mode == "⚡ Smart Web Proxy (Direct Stream - Bypasses Header Blocks)":
            with st.spinner(f"Loading and unblocking {active_url}..."):
                try:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                    }
                    resp = requests.get(active_url, headers=headers, timeout=12, verify=False, allow_redirects=True)
                    resp.encoding = resp.apparent_encoding or "utf-8"
                    raw_html = resp.text

                    # Strip meta tags that block iframes or enforce restrictive CSP
                    raw_html = re.sub(r'<meta[^>]*http-equiv=["\']?Content-Security-Policy["\']?[^>]*>', "", raw_html, flags=re.I)
                    raw_html = re.sub(r'<meta[^>]*http-equiv=["\']?X-Frame-Options["\']?[^>]*>', "", raw_html, flags=re.I)
                    raw_html = re.sub(r'<base\s+[^>]*>', '', raw_html, flags=re.I)

                    parsed = urlparse(active_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    interactive_bridge = f"""
                    <base href="{base_url}/">
                    <script>
                      try {{
                        Object.defineProperty(window, 'top', {{ get: function() {{ return window.self; }} }});
                        Object.defineProperty(window, 'parent', {{ get: function() {{ return window.self; }} }});
                        Object.defineProperty(window, 'frameElement', {{ get: function() {{ return null; }} }});
                      }} catch(e) {{}}

                      // Intercept link clicks so external navigations open safely in a new tab without frame blocks
                      document.addEventListener('click', function(e) {{
                        var a = e.target.closest('a');
                        if (a && a.href && !a.href.startsWith('javascript:') && !a.href.startsWith('#')) {{
                          a.target = '_blank';
                          a.rel = 'noopener noreferrer';
                        }}
                      }}, true);

                      // Intercept form submissions so they submit safely in a new tab
                      document.addEventListener('submit', function(e) {{
                        if (e.target && e.target.tagName === 'FORM') {{
                          e.target.target = '_blank';
                        }}
                      }}, true);

                      // Intercept window.open
                      var _origOpen = window.open;
                      window.open = function(url, target, features) {{
                        return _origOpen.call(window, url, '_blank', features);
                      }};
                    </script>
                    """
                    injected_html = interactive_bridge + raw_html
                    injected_html = re.sub(r"\btop\.location\b", "window._disabled_top", injected_html)
                    injected_html = re.sub(r"\bparent\.location\b", "window._disabled_top", injected_html)
                    injected_html = re.sub(r"\bwindow\.top\b", "window.self", injected_html)
                    injected_html = re.sub(r"top\s*!==\s*self", "false", injected_html)
                    injected_html = re.sub(r"top\s*!=\s*self", "false", injected_html)
                    injected_html = re.sub(r"self\s*!==\s*top", "false", injected_html)

                    st.components.v1.html(injected_html, height=frame_height, scrolling=True)
                except Exception as e:
                    st.warning(f"Notice: Direct streaming for {active_url} encountered: {e}")
                    st.markdown(
                        f"""
                        <div style="background:{hex_to_rgba(T['primary'], 0.1)};border:1px solid {hex_to_rgba(T['primary'], 0.25)};border-radius:12px;padding:18px;margin:12px 0;">
                          <h4 style="margin:0 0 6px 0;color:{T['primary']};">🌐 Direct Unblocker & Fallback Launchers</h4>
                          <p class="lm-muted" style="margin:0 0 14px 0;font-size:0.85rem;">
                            The target site <b>{esc(active_url)}</b> restricts server-side direct streaming or enforces strict origin protection. Choose a verified gateway below to view without connection issues:
                          </p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    c_fb1, c_fb2, c_fb3, c_fb4 = st.columns(4)
                    with c_fb1:
                        st.link_button("↗ Direct Popout Tab", active_url, type="primary", width="stretch")
                    with c_fb2:
                        reader_url = f"https://r.jina.ai/{active_url}"
                        st.link_button("📖 Clean Web Reader", reader_url, width="stretch")
                    with c_fb3:
                        g_url = f"https://translate.google.com/translate?sl=auto&tl=en&u={quote(active_url, safe='')}"
                        st.link_button("🌐 Google Web Mirror", g_url, width="stretch")
                    with c_fb4:
                        w_url = f"https://web.archive.org/web/{active_url}"
                        st.link_button("📚 Archive Snapshot", w_url, width="stretch")

        # --------------------------------------------------------------------- Mode 2: Universal Web Reader
        elif mode == "📖 Universal Web Reader (Bypasses 100% of Iframe Blocks)":
            reader_url = f"https://r.jina.ai/{active_url}"
            st.markdown(
                f"""
                <iframe src="{esc(reader_url)}"
                        style="width:100%;height:{frame_height}px;border:1px solid {hex_to_rgba(T['primary'], 0.3)};border-radius:12px;background:#ffffff;"
                        sandbox="{iframe_sandbox}"
                        allow="{iframe_allow}"
                        loading="lazy">
                </iframe>
                """,
                unsafe_allow_html=True,
            )

        # --------------------------------------------------------------------- Mode 3: Playable Web Games (Arcade Hub)
        elif mode == "🎮 Playable Web Games (Arcade Hub)":
            st.markdown("<div style='font-size:0.85rem;font-weight:700;color:#8B93B5;margin-bottom:8px;'>SELECT ARCADE TITLE (100% OFFLINE & PLAYABLE):</div>", unsafe_allow_html=True)
            g1, g2, g3, g4, g5, g6 = st.columns(6)
            if "arcade_selected" not in st.session_state:
                st.session_state["arcade_selected"] = "2048"

            if g1.button("🔢 2048", width="stretch", key="arc_2048"):
                st.session_state["arcade_selected"] = "2048"
                st.rerun()
            if g2.button("🐍 Snake", width="stretch", key="arc_snake"):
                st.session_state["arcade_selected"] = "Snake"
                st.rerun()
            if g3.button("🟩 Wordle", width="stretch", key="arc_wordle"):
                st.session_state["arcade_selected"] = "Wordle"
                st.rerun()
            if g4.button("💣 Mines", width="stretch", key="arc_mines"):
                st.session_state["arcade_selected"] = "Minesweeper"
                st.rerun()
            if g5.button("🧱 Tetris", width="stretch", key="arc_tetris"):
                st.session_state["arcade_selected"] = "Block Drop"
                st.rerun()
            if g6.button("🚀 Web Portals", width="stretch", key="arc_portals"):
                st.session_state["arcade_selected"] = "Web Portals"
                st.rerun()

            sel_game = st.session_state.get("arcade_selected", "2048")

            if sel_game == "2048":
                st.caption("🎮 Playing: **2048 Classic** — Join the tiles using Arrow keys, WASD, or Swipe to reach 2048!")
                html_code = arcade_games.get_2048_html(theme_primary=T["primary"], theme_bg=T["bg"])
                st.components.v1.html(html_code, height=frame_height, scrolling=False)
            elif sel_game == "Snake":
                st.caption("🎮 Playing: **Retro Snake** — Eat food, avoid walls/tail, navigate using Arrows, WASD, or On-Screen D-Pad!")
                html_code = arcade_games.get_snake_html(theme_primary=T.get("accent", "#10B981"), theme_bg=T["bg"])
                st.components.v1.html(html_code, height=frame_height, scrolling=False)
            elif sel_game == "Wordle":
                st.caption("🎮 Playing: **Wordle Unlimited** — Guess the hidden 5-letter word in 6 tries with color clues!")
                html_code = arcade_games.get_wordle_html(theme_primary=T["primary"], theme_bg=T["bg"])
                st.components.v1.html(html_code, height=frame_height, scrolling=False)
            elif sel_game == "Minesweeper":
                st.caption("🎮 Playing: **Minesweeper Retro** — Clear the field without detonating mines. Right-click or Flag mode to mark!")
                html_code = arcade_games.get_minesweeper_html(theme_primary=T["primary"], theme_bg=T["bg"])
                st.components.v1.html(html_code, height=frame_height, scrolling=False)
            elif sel_game == "Block Drop":
                st.caption("🎮 Playing: **Block Drop (Tetris)** — Clear complete horizontal lines. Rotate with Up or button, Drop with Down!")
                html_code = arcade_games.get_tetris_html(theme_primary=T["primary"], theme_bg=T["bg"])
                st.components.v1.html(html_code, height=frame_height, scrolling=False)
            else:  # Web Portals
                st.markdown(
                    f"""
                    <div style="background:{hex_to_rgba(T['primary'], 0.1)};border:1px solid {hex_to_rgba(T['primary'], 0.3)};border-radius:14px;padding:20px;margin-bottom:16px;">
                      <h4 style="margin:0 0 8px 0;color:{T['primary']};">🚀 High-Performance Web Game Portals</h4>
                      <p class="lm-muted" style="margin:0;font-size:0.88rem;">
                        Commercial 3D games (like Poki, Subway Surfers, and CrazyGames) enforce browser-level cross-origin frame isolation (<code>frame-ancestors</code>).
                        Launching them in dedicated popout windows guarantees 60 FPS hardware acceleration, full audio, gamepad support, and <b>100% unblocked play</b> with zero iframe restrictions!
                      </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                p1, p2, p3 = st.columns(3)
                with p1:
                    with st.container(border=True):
                        st.markdown("**🎮 Poki Games Hub**")
                        st.caption("Over 1,000 free online games including Subway Surfers, Temple Run 2, and Stickman Hook.")
                        st.link_button("🚀 Launch Poki Games", "https://poki.com", type="primary", width="stretch")
                    with st.container(border=True):
                        st.markdown("**🏃 Subway Surfers**")
                        st.caption("The world-famous endless runner game playable directly in browser.")
                        st.link_button("🚀 Play Subway Surfers", "https://poki.com/en/g/subway-surfers", width="stretch")
                with p2:
                    with st.container(border=True):
                        st.markdown("**🕹️ CrazyGames Arcade**")
                        st.caption("Action, driving, multiplayer, and .io web games with zero installs.")
                        st.link_button("🚀 Launch CrazyGames", "https://www.crazygames.com", type="primary", width="stretch")
                    with st.container(border=True):
                        st.markdown("**🏍️ Moto X3M Bike Race**")
                        st.caption("Action-packed stunt motorcycle trials with crazy loops and flips.")
                        st.link_button("🚀 Play Moto X3M", "https://poki.com/en/g/moto-x3m", width="stretch")
                with p3:
                    with st.container(border=True):
                        st.markdown("**🎿 Slope 3D Game**")
                        st.caption("High-speed 3D neon ball rolling arcade obstacle course.")
                        st.link_button("🚀 Play Slope 3D", "https://slopegame.online/", width="stretch")
                    with st.container(border=True):
                        st.markdown("**🎯 1v1.LOL Arena**")
                        st.caption("Online third-person building and shooting simulator.")
                        st.link_button("🚀 Play 1v1.LOL", "https://1v1.lol/", width="stretch")

        # --------------------------------------------------------------------- Mode 4: Multi-Proxy Mirror Launcher
        else:
            st.markdown(
                f"""
                <div style="background:{hex_to_rgba(T['primary'], 0.1)};border:1px solid {hex_to_rgba(T['primary'], 0.3)};border-radius:14px;padding:24px;margin:16px 0;">
                  <h3 style="margin-top:0;color:{T['primary']};">🌐 Multi-Proxy Unblocker Mirrors</h3>
                  <p class="lm-muted" style="margin-bottom:20px;">
                    Some high-security websites disallow iframe embedding. Use any of the specialized mirrors below to access <b>{esc(active_url)}</b> freely:
                  </p>
                  <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:14px;">
                    <a href="{esc(active_url)}" target="_blank" style="text-decoration:none;">
                      <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);padding:14px;border-radius:10px;text-align:center;">
                        <div style="font-size:1.5rem;margin-bottom:4px;">↗️</div>
                        <div style="font-weight:700;color:#38BDF8;">Direct Popout Tab</div>
                        <div style="font-size:0.75rem;color:#8B93B5;">Open directly in browser</div>
                      </div>
                    </a>
                    <a href="https://translate.google.com/translate?sl=auto&tl=en&u={quote(active_url, safe='')}" target="_blank" style="text-decoration:none;">
                      <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);padding:14px;border-radius:10px;text-align:center;">
                        <div style="font-size:1.5rem;margin-bottom:4px;">🌐</div>
                        <div style="font-weight:700;color:#38BDF8;">Google Web Gateway</div>
                        <div style="font-size:0.75rem;color:#8B93B5;">Interactive unblocker</div>
                      </div>
                    </a>
                    <a href="https://12ft.io/{esc(active_url)}" target="_blank" style="text-decoration:none;">
                      <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);padding:14px;border-radius:10px;text-align:center;">
                        <div style="font-size:1.5rem;margin-bottom:4px;">🛡️</div>
                        <div style="font-weight:700;color:#38BDF8;">12ft Ladder</div>
                        <div style="font-size:0.75rem;color:#8B93B5;">Remove paywalls & ads</div>
                      </div>
                    </a>
                    <a href="https://web.archive.org/web/{esc(active_url)}" target="_blank" style="text-decoration:none;">
                      <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);padding:14px;border-radius:10px;text-align:center;">
                        <div style="font-size:1.5rem;margin-bottom:4px;">📚</div>
                        <div style="font-weight:700;color:#38BDF8;">Wayback Machine</div>
                        <div style="font-size:0.75rem;color:#8B93B5;">Internet Archive snapshot</div>
                      </div>
                    </a>
                    <a href="https://txtify.it/{esc(active_url)}" target="_blank" style="text-decoration:none;">
                      <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);padding:14px;border-radius:10px;text-align:center;">
                        <div style="font-size:1.5rem;margin-bottom:4px;">⚡</div>
                        <div style="font-weight:700;color:#38BDF8;">Txtify Clean Web</div>
                        <div style="font-size:0.75rem;color:#8B93B5;">Pure lightweight text</div>
                      </div>
                    </a>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ------------------------------------------------------------------------- Tab 2: Chatroom
    with tab_chat:
        section("💬 Lumen Orbit Chatroom")
        st.caption("A shared local chatroom across active sessions. Chat, take notes, or collaborate:")

        # Action bar
        c_bar1, c_bar2 = st.columns([4, 1], vertical_alignment="center")
        with c_bar2:
            if st.button("🗑️ Clear Room", icon=":material/delete:", width="stretch", key="clear_chat_btn"):
                db.clear_chatroom_messages()
                st.toast("Chatroom cleared!", icon="🧹")
                st.rerun()

        # Messages Container
        messages = db.get_chatroom_messages(limit=80)
        chat_box = st.container(height=420, border=True)
        with chat_box:
            if not messages:
                st.markdown(
                    "<div class='lm-muted' style='text-align:center;padding:3rem 0;font-size:.95rem;'>"
                    "🌱 No messages yet. Say hello to start the conversation!</div>",
                    unsafe_allow_html=True,
                )
            else:
                for msg in messages:
                    is_me = msg.get("user_id") == user.get("id")
                    av_html = render_avatar_html(msg.get("avatar", "👤"), size=34, radius="50%")
                    align = "flex-end" if is_me else "flex-start"
                    bubble_bg = hex_to_rgba(T["primary"], 0.22) if is_me else hex_to_rgba(T["bg2"], 0.8)
                    border_c = T["primary"] if is_me else hex_to_rgba(T["primary"], 0.25)

                    st.markdown(
                        f"""
                        <div style="display:flex;justify-content:{align};margin-bottom:.7rem;gap:.6rem;align-items:flex-start;">
                          {'' if is_me else av_html}
                          <div style="max-width:75%;background:{bubble_bg};border:1px solid {border_c};border-radius:14px;padding:.55rem .85rem;">
                            <div style="display:flex;justify-content:space-between;gap:1rem;margin-bottom:.2rem;">
                              <span style="font-size:.78rem;font-weight:700;color:{T['primary']};">{esc(msg.get('user_name', 'Anonymous'))}</span>
                              <span class="lm-muted" style="font-size:.7rem;">{esc(msg.get('created_at', ''))[11:16]}</span>
                            </div>
                            <div style="font-size:.92rem;color:{T['text']};word-break:break-word;">{esc(msg.get('message', ''))}</div>
                          </div>
                          {av_html if is_me else ''}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        # Message Input Form
        with st.form("chat_compose_form", clear_on_submit=True):
            input_col, send_col = st.columns([5, 1], vertical_alignment="bottom")
            new_msg = input_col.text_input("Message", placeholder="Type a message...", label_visibility="collapsed", key="chat_msg_input")
            sent = send_col.form_submit_button("Send", type="primary", icon=":material/send:", width="stretch")
            if sent and new_msg.strip():
                db.post_chatroom_message(
                    user_id=user.get("id", 1),
                    user_name=user_name,
                    avatar=avatar,
                    message=new_msg.strip(),
                )
                st.rerun()

    # ------------------------------------------------------------------------- Tab 3: Mirror Links
    with tab_mirror:
        section("🔗 Mirror Links & Alternate Endpoints")
        st.caption("Access Lumen and Orbit from alternate networks, mirrors, or local devices:")

        local_ip = _get_local_ip()
        port = 8501

        m_cards = [
            ("🏠 Localhost Mirror", f"http://localhost:{port}", "Default loopback on this machine"),
            ("📡 Local Network Mirror", f"http://{local_ip}:{port}", "Use on mobile, tablet, or other PCs on same Wi-Fi"),
            ("🌐 Cloudflare 1.1.1.1 Gateway", "https://1.1.1.1", "High-speed private DNS & network gateway"),
            ("🔍 DuckDuckGo Private Gateway", "https://html.duckduckgo.com/html/", "Tracker-free web search and proxy portal"),
        ]

        for title, link, desc in m_cards:
            with st.container(border=True):
                c_desc, c_btn = st.columns([4, 1.2], vertical_alignment="center")
                with c_desc:
                    st.markdown(f"**{title}**")
                    st.code(link, language=None)
                    st.caption(desc)
                with c_btn:
                    st.link_button("↗ Open Mirror", url=link, width="stretch", type="primary")

        st.write("")
        section("🌐 Custom Mirror Link Generator")
        with st.form("custom_mirror_form", border=True):
            st.caption("Add an external mirror link (e.g. Cloudflare tunnel, ngrok, or custom dynamic DNS):")
            m_label = st.text_input("Mirror Label", placeholder="e.g. My School Tunnel")
            m_url = st.text_input("Mirror URL", placeholder="https://my-lumen-tunnel.trycloudflare.com")
            if st.form_submit_button("Launch Custom Mirror", icon=":material/launch:", type="primary"):
                if m_url.strip():
                    clean_u = m_url.strip() if m_url.strip().startswith(("http://", "https://")) else "https://" + m_url.strip()
                    st.markdown(f"👉 [**Click here to open {m_label or 'Custom Mirror'}**]({clean_u})")
                else:
                    st.error("Please enter a valid mirror URL.")

    # ------------------------------------------------------------------------- Tab 4: Beam AI
    with tab_beam:
        section("⚡ Beam — In-Built AI Agent")
        st.caption("Beam is your intelligent companion for research, website explanations, live calculations, and expense analysis:")

        # Initialize Beam chat session
        if "beam_chat_messages" not in st.session_state:
            st.session_state["beam_chat_messages"] = [
                {
                    "role": "assistant",
                    "content": (
                        "⚡ **Hello! I'm Beam**, your live AI companion inside Lumen Orbit.\n\n"
                        "I can answer complex questions, solve math calculations, explain web topics, "
                        "and inspect your personal expenses directly from your database. What would you like to explore?"
                    ),
                }
            ]

        # Action bar & Engine status
        b_top1, b_top2, b_top3 = st.columns([2.8, 1.4, 0.8], vertical_alignment="center")
        with b_top1:
            st.markdown(
                f"""
                <div style="font-size:.82rem;color:{T['text']};display:flex;align-items:center;gap:.5rem;">
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#10B981;"></span>
                  <span>Engine: <b>Live Web Search + Cloud AI + SQLite Intelligence</b></span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with b_top2:
            s_mode = st.toggle(
                "🔍 Web Search Mode",
                value=st.session_state.get("beam_search_mode", False),
                key="beam_search_toggle",
                help="When enabled, Beam performs live multi-source web searches for every query",
            )
            st.session_state["beam_search_mode"] = s_mode
        with b_top3:
            if st.button("🧹 Clear", icon=":material/refresh:", width="stretch", key="clear_beam_btn"):
                st.session_state["beam_chat_messages"] = [
                    {"role": "assistant", "content": "⚡ Memory reset. What would you like to search, ask, or calculate?"}
                ]
                st.rerun()

        # Settings and quick prompt expander
        with st.expander("⚙️ AI Settings & Suggested Quick Searches", expanded=False):
            st.caption("Optionally connect your personal Gemini API key or click a quick search prompt below:")
            k_col1, k_col2 = st.columns([3.5, 1.5], vertical_alignment="bottom")
            curr_gem_key = st.session_state.get("beam_gemini_api_key", os.environ.get("GEMINI_API_KEY", ""))
            new_key = k_col1.text_input("Gemini API Key (Optional)", value=curr_gem_key, type="password", key="beam_key_input")
            if k_col2.button("Save Key", width="stretch"):
                st.session_state["beam_gemini_api_key"] = new_key.strip()
                st.toast("Key updated for Beam!", icon="🔑")

            st.write("")
            st.markdown("<div style='font-size:0.8rem;font-weight:600;color:#8B93B5;'>SUGGESTED SEARCHES & PROMPTS:</div>", unsafe_allow_html=True)
            p_cols = st.columns(4)

            def _send_quick_prompt(qp: str) -> None:
                st.session_state["beam_chat_messages"].append({"role": "user", "content": qp})
                rep = _beam_respond(qp, user_id=user.get("id", 1))
                st.session_state["beam_chat_messages"].append({"role": "assistant", "content": rep})
                st.rerun()

            if p_cols[0].button("🔍 Search: Poki", width="stretch", key="qp_search_poki", help="Search the web for Poki games"):
                _send_quick_prompt("search Poki games online")
            if p_cols[1].button("🔍 Search: Savings", width="stretch", key="qp_search_save", help="Search best high-yield savings"):
                _send_quick_prompt("search best high yield savings accounts")
            if p_cols[2].button("📊 My Expenses", width="stretch", key="qp_exp", help="Analyze personal finances"):
                _send_quick_prompt("What are my total expenses and top spending categories?")
            if p_cols[3].button("🧮 20% of $450", width="stretch", key="qp_math", help="Calculate math"):
                _send_quick_prompt("What is 20% of 450?")

        # Chat display container
        beam_box = st.container(height=460, border=True)
        with beam_box:
            for m in st.session_state["beam_chat_messages"]:
                is_ai = m["role"] == "assistant"
                av_icon = "⚡" if is_ai else render_avatar_html(avatar, size=32, radius="50%")
                with st.chat_message(m["role"], avatar="⚡" if is_ai else None):
                    st.markdown(m["content"])

        # Chat prompt input
        search_active = st.session_state.get("beam_search_mode", False)
        prompt_placeholder = (
            "🔍 Search the live web (e.g. 'search Poki games' or 'what is inflation')..."
            if search_active
            else "Ask Beam anything, search the web ('search ...'), or ask about your expenses..."
        )
        user_prompt = st.chat_input(prompt_placeholder, key="beam_user_input")
        if user_prompt:
            st.session_state["beam_chat_messages"].append({"role": "user", "content": user_prompt})
            ai_reply = _beam_respond(user_prompt, user_id=user.get("id", 1))
            st.session_state["beam_chat_messages"].append({"role": "assistant", "content": ai_reply})
            st.rerun()
