"""Theme system for Lumen.

Each theme drives three layers at once:
1. Streamlit's native theme config (widgets, menus, data grid) via ``sync_native_theme``.
2. A custom CSS layer (glassmorphism cards, animated aurora background, nav, buttons).
3. Plotly chart styling via ``plotly_layout``.
"""

from __future__ import annotations

THEMES: dict[str, dict] = {
    "Midnight": {
        "emoji": "🌌", "base": "dark", "tagline": "Deep indigo night sky",
        "bg": "#070B1A", "bg2": "#141B3A", "sidebar": "#0A0F24",
        "blobs": ["#3B4CCA", "#7C3AED", "#0EA5E9"],
        "primary": "#7C9CFF", "accent": "#A78BFA", "accent2": "#38BDF8",
        "text": "#E6E9F5", "muted": "#8B93B5",
        "surface": "rgba(20, 27, 58, 0.55)", "surface_solid": "#121936",
        "border": "rgba(124, 156, 255, 0.16)",
        "income": "#34D399", "expense": "#FB7185", "warn": "#FBBF24",
        "palette": ["#7C9CFF", "#A78BFA", "#38BDF8", "#F472B6", "#34D399", "#FBBF24",
                    "#FB7185", "#22D3EE", "#C084FC", "#60A5FA", "#F59E0B", "#4ADE80"],
    },
    "Sunset": {
        "emoji": "🌅", "base": "dark", "tagline": "Warm dusk over the ocean",
        "bg": "#1A0B16", "bg2": "#2E1324", "sidebar": "#1F0C1A",
        "blobs": ["#FF6B3D", "#D6336C", "#7B2CBF"],
        "primary": "#FF8A5B", "accent": "#FF5E8A", "accent2": "#FFC46B",
        "text": "#FFEDE4", "muted": "#C99A9A",
        "surface": "rgba(58, 20, 38, 0.55)", "surface_solid": "#2C1222",
        "border": "rgba(255, 138, 91, 0.20)",
        "income": "#7EE0A6", "expense": "#FF6B81", "warn": "#FFC46B",
        "palette": ["#FF8A5B", "#FF5E8A", "#FFC46B", "#C77DFF", "#FF9E9E", "#F9C74F",
                    "#F3722C", "#E56B6F", "#B5838D", "#FFD6A5", "#90BE6D", "#F8961E"],
    },
    "Dream": {
        "emoji": "🦄", "base": "light", "tagline": "Soft pastel cotton-candy clouds",
        "bg": "#FBF4FF", "bg2": "#F1E8FF", "sidebar": "#F7EEFF",
        "blobs": ["#F9A8D4", "#A5B4FC", "#99F6E4"],
        "primary": "#A855F7", "accent": "#EC4899", "accent2": "#60A5FA",
        "text": "#2E1F47", "muted": "#7A6A96",
        "surface": "rgba(255, 255, 255, 0.62)", "surface_solid": "#FFFFFF",
        "border": "rgba(168, 85, 247, 0.18)",
        "income": "#10B981", "expense": "#E11D74", "warn": "#D97706",
        "palette": ["#A855F7", "#EC4899", "#60A5FA", "#2DD4BF", "#F59E0B", "#F472B6",
                    "#818CF8", "#34D399", "#FB7185", "#C084FC", "#38BDF8", "#FACC15"],
    },
    "Aurora": {
        "emoji": "🌿", "base": "dark", "tagline": "Northern lights in emerald & teal",
        "bg": "#04131A", "bg2": "#0B2730", "sidebar": "#051820",
        "blobs": ["#10B981", "#06B6D4", "#8B5CF6"],
        "primary": "#34D399", "accent": "#22D3EE", "accent2": "#A78BFA",
        "text": "#E3FBF4", "muted": "#86ABA6",
        "surface": "rgba(10, 42, 50, 0.55)", "surface_solid": "#0A2229",
        "border": "rgba(52, 211, 153, 0.18)",
        "income": "#34D399", "expense": "#F87171", "warn": "#FCD34D",
        "palette": ["#34D399", "#22D3EE", "#A78BFA", "#FCD34D", "#F472B6", "#60A5FA",
                    "#4ADE80", "#2DD4BF", "#C084FC", "#FB923C", "#A3E635", "#F87171"],
    },
    "Ocean": {
        "emoji": "🌊", "base": "dark", "tagline": "Calm deep-sea blues",
        "bg": "#031527", "bg2": "#0A2A47", "sidebar": "#04192E",
        "blobs": ["#0EA5E9", "#2563EB", "#14B8A6"],
        "primary": "#38BDF8", "accent": "#2DD4BF", "accent2": "#818CF8",
        "text": "#E0F2FE", "muted": "#7FA3C0",
        "surface": "rgba(10, 40, 70, 0.55)", "surface_solid": "#0A2440",
        "border": "rgba(56, 189, 248, 0.18)",
        "income": "#2DD4BF", "expense": "#FB7185", "warn": "#FBBF24",
        "palette": ["#38BDF8", "#2DD4BF", "#818CF8", "#F472B6", "#FBBF24", "#34D399",
                    "#60A5FA", "#A78BFA", "#22D3EE", "#FB923C", "#4ADE80", "#FB7185"],
    },
    "Dark": {
        "emoji": "🌑", "base": "dark", "tagline": "Sleek, minimal dark mode",
        "bg": "#0C0C0F", "bg2": "#1A1A20", "sidebar": "#101014",
        "blobs": ["#6366F1", "#A855F7", "#0EA5E9"],
        "primary": "#8B5CF6", "accent": "#22D3EE", "accent2": "#F472B6",
        "text": "#EDEDF0", "muted": "#8A8A96",
        "surface": "rgba(28, 28, 34, 0.62)", "surface_solid": "#18181D",
        "border": "rgba(255, 255, 255, 0.08)",
        "income": "#4ADE80", "expense": "#F87171", "warn": "#FACC15",
        "palette": ["#8B5CF6", "#22D3EE", "#F472B6", "#4ADE80", "#FACC15", "#60A5FA",
                    "#FB923C", "#A78BFA", "#2DD4BF", "#F87171", "#C084FC", "#A3E635"],
    },
    "Light": {
        "emoji": "☀️", "base": "light", "tagline": "Crisp & clean daylight",
        "bg": "#F5F7FB", "bg2": "#E9EDF5", "sidebar": "#FFFFFF",
        "blobs": ["#C7D2FE", "#BAE6FD", "#FBCFE8"],
        "primary": "#4F46E5", "accent": "#0EA5E9", "accent2": "#F59E0B",
        "text": "#111827", "muted": "#6B7280",
        "surface": "rgba(255, 255, 255, 0.78)", "surface_solid": "#FFFFFF",
        "border": "rgba(17, 24, 39, 0.08)",
        "income": "#059669", "expense": "#E11D48", "warn": "#D97706",
        "palette": ["#4F46E5", "#0EA5E9", "#F59E0B", "#10B981", "#EC4899", "#8B5CF6",
                    "#14B8A6", "#F97316", "#6366F1", "#EF4444", "#84CC16", "#06B6D4"],
    },
}

DEFAULT_THEME = "Midnight"


def get_theme(name: str | None) -> dict:
    t = dict(THEMES.get(name or DEFAULT_THEME, THEMES[DEFAULT_THEME]))
    t["name"] = name if name in THEMES else DEFAULT_THEME
    t["is_dark"] = t["base"] == "dark"
    return t


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


# --------------------------------------------------------------------------- native theme
def sync_native_theme(t: dict) -> bool:
    """Push the theme into Streamlit's config. Returns True if anything changed.

    Streamlit re-reads ``theme.*`` options at the start of every script run, so
    a change made here takes effect after one ``st.rerun()``.
    """
    try:
        from streamlit import config as st_config
    except Exception:  # pragma: no cover
        return False

    desired = {
        "theme.base": t["base"],
        "theme.primaryColor": t["primary"],
        "theme.backgroundColor": t["bg"],
        "theme.secondaryBackgroundColor": t["bg2"],
        "theme.textColor": t["text"],
        "theme.linkColor": t["accent"],
        "theme.borderColor": hex_to_rgba(t["primary"], 0.22),
        "theme.dataframeHeaderBackgroundColor": t["bg2"],
        "theme.sidebar.backgroundColor": t["sidebar"],
        "theme.sidebar.secondaryBackgroundColor": t["bg2"],
    }
    changed = False
    for key, value in desired.items():
        try:
            if st_config.get_option(key) != value:
                st_config.set_option(key, value)
                changed = True
        except Exception:
            continue  # option not supported in this Streamlit version
    return changed


# --------------------------------------------------------------------------- plotly
def plotly_layout(t: dict, **overrides) -> dict:
    grid = hex_to_rgba(t["primary"], 0.10)
    layout = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, sans-serif", color=t["text"], size=13),
        colorway=t["palette"],
        margin=dict(l=10, r=10, t=30, b=10),
        hoverlabel=dict(bgcolor=t["surface_solid"], bordercolor=t["primary"],
                        font=dict(family="Outfit, sans-serif", color=t["text"])),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=t["muted"]),
                    orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        xaxis=dict(gridcolor=grid, zerolinecolor=grid, linecolor=grid,
                   tickfont=dict(color=t["muted"])),
        yaxis=dict(gridcolor=grid, zerolinecolor=grid, linecolor=grid,
                   tickfont=dict(color=t["muted"])),
    )
    layout.update(overrides)
    return layout


# --------------------------------------------------------------------------- css
def build_css(t: dict) -> str:
    p, a, a2 = t["primary"], t["accent"], t["accent2"]
    b1, b2, b3 = t["blobs"]
    blob_alpha = 0.55 if t["is_dark"] else 0.65
    shadow = "0 10px 40px rgba(0,0,0,0.35)" if t["is_dark"] else "0 10px 30px rgba(80,60,140,0.10)"
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

:root {{
  --lm-primary: {p}; --lm-accent: {a}; --lm-accent2: {a2};
  --lm-text: {t['text']}; --lm-muted: {t['muted']};
  --lm-surface: {t['surface']}; --lm-surface-solid: {t['surface_solid']};
  --lm-border: {t['border']};
  --lm-income: {t['income']}; --lm-expense: {t['expense']}; --lm-warn: {t['warn']};
  --lm-grad: linear-gradient(135deg, {p} 0%, {a} 55%, {a2} 100%);
  --lm-shadow: {shadow};
  --lm-glow: 0 0 0 1px {hex_to_rgba(p, 0.35)}, 0 12px 40px {hex_to_rgba(p, 0.25)};
}}

html, body, .stApp, .stMarkdown, p, li, label, input, textarea, button,
h1, h2, h3, h4, h5, h6, [data-testid="stWidgetLabel"] {{
  font-family: 'Outfit', sans-serif !important;
}}
[data-testid="stIconMaterial"], span[class*="material-symbols"] {{
  font-family: 'Material Symbols Rounded' !important;
}}

/* ---------- canvas & animated aurora background ---------- */
.stApp {{
  background: radial-gradient(1200px 800px at 0% 0%, {hex_to_rgba(b1, 0.18)}, transparent 60%),
              radial-gradient(1000px 700px at 100% 0%, {hex_to_rgba(b2, 0.16)}, transparent 60%),
              linear-gradient(180deg, {t['bg']} 0%, {t['bg2']} 140%) !important;
  background-attachment: fixed !important;
}}
.stApp::before {{
  content: ""; position: fixed; inset: -25%; z-index: 0; pointer-events: none;
  background:
    radial-gradient(circle at 20% 25%, {hex_to_rgba(b1, blob_alpha)} 0, transparent 28%),
    radial-gradient(circle at 80% 20%, {hex_to_rgba(b2, blob_alpha)} 0, transparent 26%),
    radial-gradient(circle at 55% 85%, {hex_to_rgba(b3, blob_alpha)} 0, transparent 30%);
  filter: blur(70px); opacity: {0.45 if t['is_dark'] else 0.55};
  animation: lm-drift 28s ease-in-out infinite alternate;
}}
@keyframes lm-drift {{
  0%   {{ transform: translate3d(0,0,0) rotate(0deg) scale(1); }}
  50%  {{ transform: translate3d(4%, -3%, 0) rotate(8deg) scale(1.08); }}
  100% {{ transform: translate3d(-3%, 4%, 0) rotate(-6deg) scale(1.02); }}
}}
[data-testid="stAppViewContainer"], [data-testid="stMain"] {{ background: transparent !important; position: relative; z-index: 1; }}
[data-testid="stHeader"] {{ background: transparent !important; backdrop-filter: none; }}
[data-testid="stMainBlockContainer"], .block-container {{ padding-top: 2.2rem !important; max-width: 1280px; }}
#MainMenu, footer, [data-testid="stDecoration"] {{ visibility: hidden; height: 0; }}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {{
  background: {hex_to_rgba(t['sidebar'], 0.82)} !important;
  backdrop-filter: blur(22px) saturate(140%);
  border-right: 1px solid var(--lm-border);
}}
[data-testid="stSidebarNav"] a, [data-testid="stSidebarNavLink"] {{
  border-radius: 12px !important; margin: 2px 6px; transition: all .25s ease;
}}
[data-testid="stSidebarNavLink"]:hover {{ background: {hex_to_rgba(p, 0.12)} !important; transform: translateX(3px); }}
[data-testid="stSidebarNavLink"][aria-current="page"] {{
  background: linear-gradient(90deg, {hex_to_rgba(p, 0.28)}, {hex_to_rgba(a, 0.10)}) !important;
  box-shadow: inset 3px 0 0 {p};
}}

/* ---------- typography ---------- */
h1, h2, h3 {{ color: var(--lm-text) !important; letter-spacing: -0.02em; }}
.lm-hero-title {{
  font-size: 2.35rem; font-weight: 800; line-height: 1.1; margin: 0;
  background: var(--lm-grad); -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; background-size: 200% 200%;
  animation: lm-shimmer 8s ease infinite;
}}
@keyframes lm-shimmer {{ 0%,100% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} }}
.lm-hero-sub {{ color: var(--lm-muted); font-size: 1.02rem; margin-top: .35rem; }}
.lm-section {{ font-size: 1.15rem; font-weight: 700; color: var(--lm-text); margin: 1.2rem 0 .6rem;
  display: flex; align-items: center; gap: .5rem; }}
.lm-section::after {{ content: ""; flex: 1; height: 1px; background: linear-gradient(90deg, var(--lm-border), transparent); }}
.lm-muted {{ color: var(--lm-muted); }}
.lm-num {{ font-family: 'JetBrains Mono', monospace !important; font-variant-numeric: tabular-nums; }}

/* ---------- glass cards ---------- */
.lm-card {{
  background: var(--lm-surface); border: 1px solid var(--lm-border); border-radius: 20px;
  padding: 1.1rem 1.25rem; backdrop-filter: blur(18px) saturate(140%);
  box-shadow: var(--lm-shadow); transition: transform .3s ease, box-shadow .3s ease, border-color .3s ease;
  animation: lm-rise .6s cubic-bezier(.2,.8,.2,1) both; position: relative; overflow: hidden;
}}
.lm-card:hover {{ transform: translateY(-4px); box-shadow: var(--lm-glow); border-color: {hex_to_rgba(p, 0.45)}; }}
@keyframes lm-rise {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}

.lm-kpi .lm-kpi-top {{ display: flex; align-items: center; justify-content: space-between; }}
.lm-kpi .lm-kpi-label {{ color: var(--lm-muted); font-size: .85rem; font-weight: 500; text-transform: uppercase; letter-spacing: .08em; }}
.lm-kpi .lm-kpi-icon {{ width: 40px; height: 40px; border-radius: 12px; display: grid; place-items: center; font-size: 1.2rem; }}
.lm-kpi .lm-kpi-value {{ font-size: 1.75rem; font-weight: 700; color: var(--lm-text); margin-top: .5rem; white-space: nowrap; }}
.lm-kpi .lm-kpi-foot {{ margin-top: .35rem; font-size: .82rem; color: var(--lm-muted); }}
.lm-kpi::after {{ content: ""; position: absolute; right: -40px; bottom: -40px; width: 120px; height: 120px;
  border-radius: 50%; background: var(--kpi-color, {p}); opacity: .10; filter: blur(8px); }}

.lm-chip {{ display: inline-flex; align-items: center; gap: .25rem; padding: .12rem .55rem; border-radius: 999px;
  font-size: .78rem; font-weight: 600; }}
.lm-chip.up {{ background: {hex_to_rgba(t['expense'], 0.15)}; color: var(--lm-expense); }}
.lm-chip.down {{ background: {hex_to_rgba(t['income'], 0.15)}; color: var(--lm-income); }}
.lm-chip.good {{ background: {hex_to_rgba(t['income'], 0.15)}; color: var(--lm-income); }}
.lm-chip.bad {{ background: {hex_to_rgba(t['expense'], 0.15)}; color: var(--lm-expense); }}
.lm-chip.neutral {{ background: {hex_to_rgba(p, 0.15)}; color: var(--lm-primary); }}

/* ---------- transaction rows ---------- */
.lm-tx {{ display: flex; align-items: center; gap: .9rem; padding: .7rem .4rem; border-bottom: 1px dashed var(--lm-border);
  transition: background .2s ease, padding .2s ease; border-radius: 12px; }}
.lm-tx:last-child {{ border-bottom: none; }}
.lm-tx:hover {{ background: {hex_to_rgba(p, 0.07)}; padding-left: .8rem; }}
.lm-tx-icon {{ width: 42px; height: 42px; border-radius: 14px; display: grid; place-items: center; font-size: 1.25rem; flex-shrink: 0; }}
.lm-tx-main {{ flex: 1; min-width: 0; }}
.lm-tx-title {{ font-weight: 600; color: var(--lm-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.lm-tx-sub {{ font-size: .8rem; color: var(--lm-muted); }}
.lm-tx-amt {{ font-weight: 700; white-space: nowrap; }}
.lm-tx-amt.inc {{ color: var(--lm-income); }} .lm-tx-amt.exp {{ color: var(--lm-text); }}

/* ---------- progress bars ---------- */
.lm-bar {{ height: 10px; border-radius: 999px; background: {hex_to_rgba(p, 0.12)}; overflow: hidden; margin: .55rem 0 .35rem; }}
.lm-bar > span {{ display: block; height: 100%; border-radius: 999px; background: var(--lm-grad);
  animation: lm-grow 1.1s cubic-bezier(.2,.8,.2,1) both; transform-origin: left; }}
.lm-bar.warn > span {{ background: linear-gradient(90deg, var(--lm-warn), {t['expense']}); }}
.lm-bar.over > span {{ background: linear-gradient(90deg, {t['expense']}, {hex_to_rgba(t['expense'], 0.7)}); }}
@keyframes lm-grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}

/* ---------- insights ---------- */
.lm-insight {{ display: flex; gap: .75rem; align-items: flex-start; padding: .75rem .9rem; border-radius: 14px;
  background: {hex_to_rgba(p, 0.07)}; border: 1px solid var(--lm-border); margin-bottom: .55rem; color: var(--lm-text);
  animation: lm-rise .6s both; }}
.lm-insight .ico {{ font-size: 1.25rem; line-height: 1.4; }}

/* ---------- empty state ---------- */
.lm-empty {{ text-align: center; padding: 3rem 1rem; }}
.lm-empty .big {{ font-size: 3.5rem; animation: lm-float 4s ease-in-out infinite; display: inline-block; }}
@keyframes lm-float {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-10px); }} }}

/* ---------- theme gallery ---------- */
.lm-swatch {{ height: 96px; border-radius: 16px; position: relative; overflow: hidden; border: 1px solid var(--lm-border); }}
.lm-swatch .dots {{ position: absolute; bottom: 10px; left: 12px; display: flex; gap: 6px; }}
.lm-swatch .dots i {{ width: 16px; height: 16px; border-radius: 50%; display: block; box-shadow: 0 2px 8px rgba(0,0,0,.25); }}
.lm-swatch .lbl {{ position: absolute; top: 10px; left: 12px; font-weight: 700; font-size: 1rem; }}
.lm-swatch .tick {{ position: absolute; top: 10px; right: 12px; font-size: .75rem; padding: .1rem .5rem; border-radius: 999px;
  background: rgba(255,255,255,.85); color: #111; font-weight: 700; }}

/* ---------- goal rings ---------- */
.lm-ring-wrap {{ display: flex; align-items: center; gap: 1rem; }}
.lm-ring circle.fg {{ transition: stroke-dashoffset 1.2s cubic-bezier(.2,.8,.2,1); }}

/* ---------- native widget polish ---------- */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {{
  border-radius: 12px !important; font-weight: 600 !important; transition: all .25s ease !important;
  border: 1px solid var(--lm-border) !important;
}}
.stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {{
  transform: translateY(-2px); box-shadow: var(--lm-glow); border-color: {hex_to_rgba(p, 0.5)} !important;
}}
button[kind="primary"], button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"] {{
  background: var(--lm-grad) !important; color: #fff !important; border: none !important;
  background-size: 160% 160% !important; text-shadow: 0 1px 2px rgba(0,0,0,.2);
}}
button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover,
button[data-testid="stBaseButton-primaryFormSubmit"]:hover {{ background-position: 100% 50% !important; }}

[data-testid="stForm"], [data-testid="stExpander"] details, [data-testid="stVerticalBlockBorderWrapper"] {{
  background: var(--lm-surface) !important; border: 1px solid var(--lm-border) !important;
  border-radius: 20px !important; backdrop-filter: blur(18px) saturate(140%);
}}
[data-testid="stForm"] {{ padding: 1.4rem !important; box-shadow: var(--lm-shadow); }}

[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"], [data-testid="stNumberInputContainer"] {{
  border-radius: 12px !important; transition: box-shadow .2s ease, border-color .2s ease;
}}
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within, [data-baseweb="textarea"]:focus-within {{
  box-shadow: 0 0 0 3px {hex_to_rgba(p, 0.25)} !important;
}}

.stTabs [data-baseweb="tab-list"] {{ gap: .4rem; background: var(--lm-surface); padding: .35rem; border-radius: 14px;
  border: 1px solid var(--lm-border); width: fit-content; }}
.stTabs [data-baseweb="tab"] {{ border-radius: 10px; padding: .45rem 1rem; height: auto; transition: all .2s ease; }}
.stTabs [aria-selected="true"] {{ background: var(--lm-grad) !important; color: #fff !important; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display: none; }}

[data-testid="stDataFrame"], [data-testid="stDataEditor"] {{ border-radius: 16px; overflow: hidden; border: 1px solid var(--lm-border); }}
[data-testid="stPlotlyChart"] {{ animation: lm-rise .7s both; }}
[data-testid="stAlert"] {{ border-radius: 14px; }}
[data-testid="stDialog"] [role="dialog"] {{ border-radius: 22px; border: 1px solid var(--lm-border);
  background: var(--lm-surface-solid) !important; box-shadow: var(--lm-glow); }}

::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-thumb {{ background: {hex_to_rgba(p, 0.35)}; border-radius: 999px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
</style>
"""


def logo_svg(t: dict) -> str:
    p, a, a2 = t["primary"], t["accent"], t["accent2"]
    text_color = t["text"]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="220" height="56" viewBox="0 0 220 56">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{p}"/><stop offset=".55" stop-color="{a}"/><stop offset="1" stop-color="{a2}"/></linearGradient></defs>
<rect x="4" y="6" width="44" height="44" rx="14" fill="url(#g)"/>
<path d="M18 17v22h16" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
<circle cx="35" cy="20" r="4" fill="#fff" opacity=".9"/>
<text x="60" y="38" font-family="Outfit, Segoe UI, sans-serif" font-size="28" font-weight="800" fill="{text_color}">Lumen</text>
</svg>"""
