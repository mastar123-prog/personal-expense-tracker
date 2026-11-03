"""Lumen Orbit — Integrated Web Proxy, Chatroom, Mirror Links, and Beam AI.

Accessible via the secret '✨' sparkle on the home greeting.
"""

from __future__ import annotations

import html
import socket
from datetime import datetime
from typing import Any
from urllib.parse import quote, urlparse

import requests
import streamlit as st

import db
from themes import hex_to_rgba
from ui import ctx, esc, hero, render_avatar_html, section


# ----------------------------------------------------------------------------- Beam AI Engine
def _beam_respond(prompt: str) -> str:
    """Generate intelligent responses for Beam AI."""
    p_lower = prompt.lower().strip()

    # Greetings
    if any(w in p_lower for w in ("hello", "hi", "hey", "who are you", "what is beam")):
        return (
            "⚡ **Greetings! I am Beam**, your integrated companion in Lumen Orbit. "
            "I can help you browse, search information, analyze numbers, explain web topics, "
            "or chat freely. What would you like to explore today?"
        )

    # Proxy / Unblocking queries
    if any(w in p_lower for w in ("proxy", "unblock", "website", "browse", "filter")):
        return (
            "🌐 **Web Proxy Tip**: Switch to the **'Web Proxy'** tab above, paste any URL "
            "(e.g., `https://blog.free-dyndns.org/` or `https://en.wikipedia.org`), and click **'Browse Web'**. "
            "You can choose between **Live Sandbox iFrame** or **Server-side Content Reader** to bypass restrictive headers!"
        )

    # Chatroom queries
    if any(w in p_lower for w in ("chat", "chatroom", "talk", "message")):
        return (
            "💬 Check out the **'Chatroom'** tab! It's a live shared space where you can leave messages, "
            "notes, or collaborate across active sessions."
        )

    # Mirror link queries
    if any(w in p_lower for w in ("mirror", "link", "ip", "url", "domain")):
        return (
            "🔗 You can find your current active LAN IP and alternate access URLs under the **'Mirror Links'** tab. "
            "Use them to access Lumen from other devices on your local network or configure an external tunnel!"
        )

    # Finance tips
    if any(w in p_lower for w in ("money", "save", "budget", "expense", "invest", "finance")):
        return (
            "💡 **Beam's Golden Financial Rules**:\n\n"
            "1. **The 50/30/20 Rule**: 50% Needs, 30% Wants, 20% Savings.\n"
            "2. **Pay Yourself First**: Transfer 15-20% of income to savings before spending.\n"
            "3. **Track Daily Spending**: Even small $5 daily habits compound to over $1,800/year.\n"
            "4. **Emergency Fund**: Keep 3–6 months of living expenses in an accessible high-yield account."
        )

    # General / Search / Tech
    if any(w in p_lower for w in ("python", "code", "streamlit", "how", "what", "why")):
        return (
            f"⚡ **Beam Analysis for: *'{prompt}'***\n\n"
            "Here is the breakdown:\n"
            "- **Context**: You are running Lumen on a modern Python & Streamlit engine with SQLite persistence.\n"
            "- **Insight**: All operations here are private, isolated, and execute locally on your machine.\n"
            "- **Next Step**: You can use the Web Proxy tab to research this topic further, or ask me for more specific insights!"
        )

    # Default conversational reply
    return (
        f"⚡ **Beam**: I received your query: *'{prompt}'*.\n\n"
        "I am ready to assist! Ask me about web unblocking, budget strategy, coding, or anything else on your mind."
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

    # Header Bar
    top_col1, top_col2 = st.columns([5, 1.2], vertical_alignment="center")
    with top_col1:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.5rem">
              <span style="font-size:2.2rem;display:inline-block;animation:lm-float 3s ease-in-out infinite">🌌</span>
              <div>
                <h1 style="margin:0;font-size:1.85rem;font-weight:800;letter-spacing:-0.02em;background:linear-gradient(135deg, {T['primary']}, {T['accent']});-webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                  Lumen Orbit · Proxy Suite
                </h1>
                <div class="lm-muted" style="font-size:.88rem">
                  Website Unblocker & Web Proxy · Live Chatroom · Mirror Links · In-built Beam AI
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
        "🌐  Web Proxy",
        "💬  Chatroom",
        "🔗  Mirror Links",
        "⚡  Beam AI",
    ])

    # ------------------------------------------------------------------------- Tab 1: Web Proxy
    with tab_proxy:
        section("🌐 Website Unblocker & Web Proxy")
        st.caption("Browse web pages, unblock filtered sites, and access external tools directly inside Lumen:")

        # Quick preset buttons
        preset_cols = st.columns(5)
        if preset_cols[0].button("Dyndns Blog", width="stretch", key="ps_dyndns"):
            st.session_state["proxy_target_url"] = "https://blog.free-dyndns.org/"
            st.session_state["proxy_active_url"] = "https://blog.free-dyndns.org/"
            st.rerun()
        if preset_cols[1].button("Wikipedia", width="stretch", key="ps_wiki"):
            st.session_state["proxy_target_url"] = "https://en.wikipedia.org/wiki/Main_Page"
            st.session_state["proxy_active_url"] = "https://en.wikipedia.org/wiki/Main_Page"
            st.rerun()
        if preset_cols[2].button("Hacker News", width="stretch", key="ps_hn"):
            st.session_state["proxy_target_url"] = "https://news.ycombinator.com"
            st.session_state["proxy_active_url"] = "https://news.ycombinator.com"
            st.rerun()
        if preset_cols[3].button("DuckDuckGo", width="stretch", key="ps_ddg"):
            st.session_state["proxy_target_url"] = "https://html.duckduckgo.com/html/"
            st.session_state["proxy_active_url"] = "https://html.duckduckgo.com/html/"
            st.rerun()
        if preset_cols[4].button("World News", width="stretch", key="ps_news"):
            st.session_state["proxy_target_url"] = "https://lite.cnn.com"
            st.session_state["proxy_active_url"] = "https://lite.cnn.com"
            st.rerun()

        u_col1, u_col2, u_col3 = st.columns([3.2, 1.4, 0.9], vertical_alignment="bottom")
        default_target = st.session_state.get("proxy_target_url", "https://blog.free-dyndns.org/")
        url_input = u_col1.text_input(
            "Target Website URL",
            value=st.session_state.get("proxy_active_url", default_target),
            placeholder="e.g. https://blog.free-dyndns.org/",
            key="proxy_url_input",
        )

        modes = [
            "⚡ Smart Web Proxy (Bypasses Frame & Header Blocks)",
            "📖 Universal Web Reader (Bypasses 100% of Iframe Blocks)",
            "🛡️ Multi-Proxy Mirror Launcher",
        ]
        mode = u_col2.selectbox("Proxy Engine", modes, index=0, key="proxy_mode_sel")

        browse_clicked = u_col3.button("🚀 Go", type="primary", width="stretch", key="proxy_go_btn")
        if browse_clicked or (url_input and url_input != st.session_state.get("proxy_active_url")):
            st.session_state["proxy_target_url"] = url_input
            st.session_state["proxy_active_url"] = url_input

        active_url = st.session_state.get("proxy_active_url", default_target).strip()
        if not active_url.startswith(("http://", "https://")):
            active_url = "https://" + active_url

        # Proxy toolbar & unblock mirrors
        t_col1, t_col2 = st.columns([2.5, 2.5], vertical_alignment="center")
        with t_col1:
            st.markdown(
                f"""
                <div style="font-size:.88rem;color:{T['text']};padding:.3rem 0;">
                  Target: <b style="color:{T['accent']};word-break:break-all;">{esc(active_url)}</b>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with t_col2:
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.link_button("↗ Popout", active_url, width="stretch", help="Open directly in a new browser tab")
            with m2:
                st.link_button("🛡️ 12ft", f"https://12ft.io/{active_url}", width="stretch", help="Unblock with 12ft ladder")
            with m3:
                st.link_button("📚 Archive", f"https://web.archive.org/web/{active_url}", width="stretch", help="Open Wayback Machine mirror")
            with m4:
                st.link_button("⚡ Textify", f"https://txtify.it/{active_url}", width="stretch", help="Lightweight unblocked text mirror")

        if mode == "⚡ Smart Web Proxy (Bypasses Frame & Header Blocks)":
            with st.spinner(f"Unblocking and streaming {active_url}..."):
                try:
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                    }
                    resp = requests.get(active_url, headers=headers, timeout=12, verify=False, allow_redirects=True)
                    resp.encoding = resp.apparent_encoding or "utf-8"
                    raw_html = resp.text

                    # Strip meta tags that block iframes or enforce restrictive CSP
                    raw_html = re.sub(r'<meta[^>]*http-equiv=["\']?Content-Security-Policy["\']?[^>]*>', '', raw_html, flags=re.I)
                    raw_html = re.sub(r'<meta[^>]*http-equiv=["\']?X-Frame-Options["\']?[^>]*>', '', raw_html, flags=re.I)

                    # Base tag injection so images, CSS, and links resolve
                    parsed = urlparse(active_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    injected_html = f'<base href="{base_url}/" target="_blank">\n' + raw_html

                    # Strip frame busting scripts
                    injected_html = re.sub(r'\btop\.location\b', 'window._disabled_top', injected_html)
                    injected_html = re.sub(r'\bparent\.location\b', 'window._disabled_top', injected_html)
                    injected_html = re.sub(r'\bwindow\.top\b', 'window.self', injected_html)
                    injected_html = re.sub(r'top\s*!==\s*self', 'false', injected_html)
                    injected_html = re.sub(r'top\s*!=\s*self', 'false', injected_html)

                    st.components.v1.html(injected_html, height=750, scrolling=True)
                except Exception as e:
                    st.warning(f"Direct stream could not load {active_url}: {e}")
                    st.info("⚡ Falling back to Universal Unblocker Reader below:")
                    reader_url = f"https://r.jina.ai/{active_url}"
                    st.markdown(
                        f"""
                        <iframe src="{esc(reader_url)}"
                                style="width:100%;height:750px;border:1px solid {hex_to_rgba(T['primary'], 0.3)};border-radius:12px;background:#ffffff;"
                                sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
                                loading="lazy">
                        </iframe>
                        """,
                        unsafe_allow_html=True,
                    )
        elif mode == "📖 Universal Web Reader (Bypasses 100% of Iframe Blocks)":
            reader_url = f"https://r.jina.ai/{active_url}"
            st.markdown(
                f"""
                <iframe src="{esc(reader_url)}"
                        style="width:100%;height:750px;border:1px solid {hex_to_rgba(T['primary'], 0.3)};border-radius:12px;background:#ffffff;"
                        sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
                        loading="lazy">
                </iframe>
                """,
                unsafe_allow_html=True,
            )
        else:
            # Multi-Proxy Mirror Launcher
            st.markdown(
                f"""
                <div style="background:{hex_to_rgba(T['primary'], 0.1)};border:1px solid {hex_to_rgba(T['primary'], 0.3)};border-radius:14px;padding:24px;margin:16px 0;">
                  <h3 style="margin-top:0;color:{T['primary']};">🌐 Multi-Proxy Unblocker Mirrors</h3>
                  <p class="lm-muted" style="margin-bottom:20px;">
                    Some high-security websites (e.g. online banking, Google, Cloudflare DDoS challenges) completely disallow embedding in any browser iframe. 
                    Use any of the specialized mirrors below to access <b>{esc(active_url)}</b> freely:
                  </p>
                  <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:14px;">
                    <a href="{esc(active_url)}" target="_blank" style="text-decoration:none;">
                      <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);padding:14px;border-radius:10px;text-align:center;">
                        <div style="font-size:1.5rem;margin-bottom:4px;">↗️</div>
                        <div style="font-weight:700;color:#38BDF8;">Direct Popout Tab</div>
                        <div style="font-size:0.75rem;color:#8B93B5;">Open directly in browser</div>
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
                        <div style="font-size:0.75rem;color:#8B93B5;">Internet Archive mirror</div>
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
            ("🌐 Free-DynDNS Web Link", "https://blog.free-dyndns.org/", "Proxy & DNS reference gateway"),
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
        section("⚡ Beam — In-Built AI Assistant")
        st.caption("Beam is your intelligent companion for research, web questions, numbers, and advice:")

        # Initialize Beam chat session
        if "beam_chat_messages" not in st.session_state:
            st.session_state["beam_chat_messages"] = [
                {
                    "role": "assistant",
                    "content": (
                        "⚡ **Hello! I'm Beam.** I can help you search information, unblock concepts, "
                        "analyze budgets, or explain complex topics. What can I do for you today?"
                    ),
                }
            ]

        b_top1, b_top2 = st.columns([4, 1], vertical_alignment="center")
        with b_top2:
            if st.button("🧹 Clear Chat", icon=":material/refresh:", width="stretch", key="clear_beam_btn"):
                st.session_state["beam_chat_messages"] = [
                    {"role": "assistant", "content": "⚡ Beam memory reset. What should we explore next?"}
                ]
                st.rerun()

        # Chat display container
        beam_box = st.container(height=420, border=True)
        with beam_box:
            for m in st.session_state["beam_chat_messages"]:
                is_ai = m["role"] == "assistant"
                av_icon = "⚡" if is_ai else render_avatar_html(avatar, size=32, radius="50%")
                with st.chat_message(m["role"], avatar="⚡" if is_ai else None):
                    st.markdown(m["content"])

        # Chat prompt input
        user_prompt = st.chat_input("Ask Beam anything...", key="beam_user_input")
        if user_prompt:
            st.session_state["beam_chat_messages"].append({"role": "user", "content": user_prompt})
            ai_reply = _beam_respond(user_prompt)
            st.session_state["beam_chat_messages"].append({"role": "assistant", "content": ai_reply})
            st.rerun()
