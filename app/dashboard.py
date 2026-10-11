"""
GovPulse — Streamlit Dashboard
MICT-styled institutional dashboard.
"""

import base64
import json
import os
import subprocess
import sys
from datetime import datetime
import streamlit as st
import pandas as pd


# ------------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------------
st.set_page_config(
    page_title="GovPulse — Media Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ------------------------------------------------------------------
# PATHS
# ------------------------------------------------------------------
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH      = os.path.join(BASE_DIR, "assets", "mict_logo.png")

MAPPED_FILE    = "data/processed/mapped.json"
RESPONSES_FILE = "data/processed/responses.json"
APPROVALS_FILE = "data/processed/approvals.json"


# ------------------------------------------------------------------
# LOGO — load once, reuse everywhere
# ------------------------------------------------------------------
def _logo_base64(path):
    """Return the logo as a base64 string so it can be inlined in HTML."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception as e:
        print(f"[GovPulse] Logo load failed: {e}")
        return None


logo_b64 = _logo_base64(LOGO_PATH)


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------
def load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else []
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else []


def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def run_pipeline():
    steps = [
        ("Scraping news sources",  "src/scraper.py"),
        ("Analyzing stories",      "src/analyzer.py"),
        ("Mapping to government",  "src/mapper.py"),
        ("Generating daily brief", "src/report.py"),
        ("Drafting responses",     "src/response_desk.py"),
    ]
    progress = st.progress(0, text="Starting pipeline...")
    for i, (label, script) in enumerate(steps):
        progress.progress((i) / len(steps), text=f"{label}...")
        try:
            r = subprocess.run(
                [sys.executable, script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
            )
            if r.returncode != 0:
                st.error(f"Error in {script}: {r.stderr[:500]}")
                return False
        except subprocess.TimeoutExpired:
            st.error(f"{script} timed out.")
            return False
    progress.progress(1.0, text="Pipeline complete.")
    st.success("Pipeline complete.")
    return True


def sentiment_color(s):
    return {
        "Positive": ("#16A34A", "#DCFCE7"),
        "Neutral":  ("#6B7280", "#F3F4F6"),
        "Negative": ("#DC2626", "#FEE2E2"),
    }.get(s, ("#6B7280", "#F3F4F6"))


# ------------------------------------------------------------------
# GLOBAL STYLING — MICT-website-inspired theme
# ------------------------------------------------------------------
st.markdown(
    """
    <style>
        :root {
            --mict-navy:   #0F2540;
            --mict-teal:   #0E8C8C;
            --mict-teal-d: #0A6E6E;
            --mict-blue:   #1E5AA8;
            --bg:          #FFFFFF;
            --page:        #F5F6FA;
            --card:        #FFFFFF;
            --text:        #111827;
            --body:        #374151;
            --muted:       #6B7280;
            --border:      #E5E7EB;
            --subtle:      #F9FAFB;
        }

        html, body, [class*="css"] { font-family: 'Segoe UI', Roboto, sans-serif; }
        .stApp { background: var(--page); }

        /* ---------------- SIDEBAR ---------------- */
        section[data-testid="stSidebar"] { background: var(--mict-navy); }
        section[data-testid="stSidebar"] * { color: #E5EAF3 !important; }
        section[data-testid="stSidebar"] hr { border-color: #1E3A5F; }
        section[data-testid="stSidebar"] .stButton > button {
            background: transparent !important;
            color: #E5EAF3 !important;
            border: none !important;
            border-radius: 0 !important;
            width: 100% !important;
            text-align: left !important;
            font-weight: 600 !important;
            letter-spacing: 0.4px;
            text-transform: uppercase;
            font-size: 12px !important;
            padding: 8px 12px !important;
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(255,255,255,0.08) !important;
            color: #FFFFFF !important;
        }

        /* ---------------- GLOBAL BUTTONS ---------------- */
        .stButton > button,
        .stDownloadButton > button,
        button[kind="secondary"],
        button[kind="primary"] {
            background: var(--mict-teal) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 4px !important;
            font-weight: 600 !important;
        }
        .stButton > button:hover,
        .stDownloadButton > button:hover,
        button[kind="secondary"]:hover,
        button[kind="primary"]:hover {
            background: var(--mict-teal-d) !important;
            color: #FFFFFF !important;
        }
        .stButton > button:disabled,
        .stDownloadButton > button:disabled {
            background: #D1D5DB !important;
            color: #6B7280 !important;
            cursor: not-allowed !important;
        }

        /* ---------------- SEARCH BAR ---------------- */
        div[data-testid="stTextInput"] div[data-baseweb="input"],
        div[data-testid="stTextInput"] div[data-baseweb="base-input"] {
            background: #FFFFFF !important;
            border: 1px solid var(--border) !important;
            border-radius: 4px !important;
        }
        div[data-testid="stTextInput"] input {
            background: #FFFFFF !important;
            color: #111827 !important;
            -webkit-text-fill-color: #111827 !important;
        }
        div[data-testid="stTextInput"] input::placeholder {
            color: #9CA3AF !important;
            -webkit-text-fill-color: #9CA3AF !important;
        }

        /* ---------------- TEXT AREA ---------------- */
        div[data-testid="stTextArea"] textarea {
            background: #FFFFFF !important;
            color: #111827 !important;
            border: 1px solid var(--border) !important;
            border-radius: 4px !important;
            font-family: 'Segoe UI', Roboto, sans-serif !important;
            font-size: 13px !important;
            line-height: 1.6 !important;
        }

        /* ---------------- MICT SECTION HEADING ---------------- */
        .mict-heading {
            color: var(--mict-teal);
            font-size: 15px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            text-align: center;
            margin: 0 0 14px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }
        .mict-heading-left {
            color: var(--mict-teal);
            font-size: 15px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            margin: 0 0 14px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }

        /* ---------------- MICT CARD ---------------- */
        .mict-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 18px 20px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
            margin-bottom: 16px;
            height: 100%;
        }
        .mict-card-title {
            color: var(--mict-blue);
            font-size: 14px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            text-align: center;
            margin-bottom: 12px;
        }
        .mict-card-body {
            color: var(--body);
            font-size: 13px;
            line-height: 1.55;
            text-align: center;
        }
        .mict-card-link {
            display: block;
            text-align: center;
            color: var(--mict-blue);
            font-size: 12px;
            font-weight: 600;
            margin-top: 12px;
            text-decoration: none;
        }

        /* ---------------- METRIC CARDS ---------------- */
        .gp-metric {
            background: var(--card);
            border-radius: 10px;
            padding: 17px 19px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
            border-left: 4px solid var(--border);
        }
        .gp-metric-label {
            font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;
            color: var(--muted); margin-bottom: 6px; font-weight: 600;
        }
        .gp-metric-value { font-size: 26px; font-weight: 700; color: var(--text); line-height: 1.1; }
        .gp-metric-delta { font-size: 12px; color: #16A34A; margin-top: 4px; }

        /* ---------------- STORY CARDS ---------------- */
        .gp-story {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 14px 16px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
            margin-bottom: 10px;
        }
        .gp-badge {
            display: inline-block; font-size: 10px; font-weight: 700;
            padding: 2px 8px; border-radius: 10px; text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .gp-headline {
            font-size: 15px; font-weight: 600; color: var(--text);
            margin: 8px 0 4px 0;
        }
        .gp-oma {
            font-size: 11px; color: var(--muted); text-transform: uppercase;
            letter-spacing: 0.4px;
        }

        /* ---------------- CRISIS ALERT ---------------- */
        .gp-crisis {
            background: #FEE2E2; border-left: 4px solid #DC2626;
            border-radius: 10px; padding: 14px 16px; margin-bottom: 12px;
        }
        .gp-crisis-title { font-weight: 700; color: #991B1B; font-size: 14px; margin-bottom: 4px; }
        .gp-crisis-body { font-size: 12px; color: #7F1D1D; }

        /* ---------------- RESPONSE PANEL ---------------- */
        .gp-response {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        }
        .gp-panel-title {
            font-size: 13px; font-weight: 700; color: var(--mict-teal);
            text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;
        }
        .gp-panel-sub { font-size: 11px; color: var(--muted); margin-bottom: 12px; }

        /* ---------------- HEADER ---------------- */
        .mict-header {
            background: #FFFFFF;
            border-bottom: 1px solid var(--border);
            padding: 10px 0 12px 0;
            margin: -10px 0 0 0;
        }
        .mict-header-title {
            color: #111827;
            font-size: 17px;
            font-weight: 700;
            line-height: 1.2;
            margin: 0;
        }
        .mict-header-sub {
            color: #374151;
            font-size: 13px;
            margin: 2px 0 0 0;
        }

        /* ---------------- BANNER ---------------- */
        .gp-banner {
            background: linear-gradient(90deg, #0F2540 0%, #1A3556 100%);
            border-radius: 10px;
            padding: 24px 28px;
            color: white;
            margin-bottom: 20px;
        }
        .gp-banner h1 { color: white; font-size: 24px; margin: 0 0 6px 0; font-weight: 700; }
        .gp-banner p { color: #B0C0D8; font-size: 13px; margin: 0; }

        .stDataFrame { background: var(--card); border-radius: 2px; }

        .block-container { padding-top: 3rem; max-width: 1200px; }
        header[data-testid="stHeader"] {
    background: transparent !important;
    height: 2.5rem;
}
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# SESSION STATE (always reload from disk)
# ------------------------------------------------------------------
st.session_state.mapped = load_json(MAPPED_FILE)
st.session_state.responses = load_json(RESPONSES_FILE)
st.session_state.approvals = load_json(APPROVALS_FILE, default={})

if "selected_story_headline" not in st.session_state:
    st.session_state.selected_story_headline = None
if "quick_filter" not in st.session_state:
    st.session_state.quick_filter = "All"
if "editing_headline" not in st.session_state:
    st.session_state.editing_headline = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"


# ------------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------------
with st.sidebar:
    if logo_b64:
        st.markdown(
            f"""
            <div style="padding: 12px 4px 16px 4px; text-align:center;">
                <img src="data:image/png;base64,{logo_b64}"
                     alt="MICT" style="max-width:180px;" />
                <div style="font-size:11px; color:#8899B0; margin-top:8px;
                            text-transform:uppercase; letter-spacing:0.6px;">
                    GovPulse Media Intelligence
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="padding: 12px 4px 20px 4px;">
                <div style="font-size: 18px; font-weight: 700; color: white;">
                    GovPulse
                </div>
                <div style="font-size: 11px; color: #8899B0; margin-top: 4px;">
                    Media Intelligence
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("##### NAVIGATION")

    nav_items = [
        ("📊  Dashboard",  "Dashboard"),
        ("📡  Monitoring", "Monitoring"),
        ("📄  Reports",    "Reports"),
        ("⚙️  Settings",   "Settings"),
    ]
    for label, page in nav_items:
        is_active = st.session_state.current_page == page
        # Visually highlight the active page
        if is_active:
            st.markdown(
                "<div style='background:rgba(255,255,255,0.12); "
                "border-left:3px solid #0E8C8C; padding:2px 0 2px 0; "
                "margin-bottom:-6px;'></div>",
                unsafe_allow_html=True,
            )
        if st.button(label, key=f"nav_{page}", use_container_width=True):
            st.session_state.current_page = page
            st.rerun()

    st.divider()
    st.markdown("##### PIPELINE")
    if st.button("🔄  Run Full Pipeline", use_container_width=True):
        if run_pipeline():
            st.rerun()

    if st.button("📄  Regenerate Brief", use_container_width=True):
        subprocess.run([sys.executable, "src/report.py"], check=False)
        st.success("Brief regenerated.")
        st.rerun()

    st.divider()
    st.markdown("##### FILTERS")
    source_filter = st.multiselect(
        "Source",
        options=sorted({s.get("source", "Unknown") for s in st.session_state.mapped}),
        default=[],
    )

    st.markdown("**Sentiment**")
    pos_on = st.checkbox("🟢 Positive", value=True, key="filter_pos")
    neu_on = st.checkbox("⚫ Neutral", value=True, key="filter_neu")
    neg_on = st.checkbox("🔴 Negative", value=True, key="filter_neg")

    sentiment_filter = []
    if pos_on:
        sentiment_filter.append("Positive")
    if neu_on:
        sentiment_filter.append("Neutral")
    if neg_on:
        sentiment_filter.append("Negative")

    st.divider()
    st.caption(f"Loaded: {len(st.session_state.mapped)} stories")
    drafts_ok = sum(1 for r in st.session_state.responses
                    if r.get("response", {}).get("status") == "ok")
    st.caption(f"Drafts: {drafts_ok}")


# ------------------------------------------------------------------
# MICT HEADER (logo + title + search)
# ------------------------------------------------------------------
head_l, head_r = st.columns([3, 1])
with head_l:
    if logo_b64:
        st.markdown(
            f"""
            <div class="mict-header" style="display:flex; align-items:center; gap:16px;">
                <img src="data:image/png;base64,{logo_b64}"
                     alt="MICT" style="height:60px;" />
                <div>
                    <div class="mict-header-title">
                        Ministry of Information &amp; Communication Technology
                    </div>
                    <div class="mict-header-sub">Republic of Namibia</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="mict-header">
                <div class="mict-header-title">
                    Ministry of Information &amp; Communication Technology
                </div>
                <div class="mict-header-sub">Republic of Namibia</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with head_r:
    search_query = st.text_input(
        "Search",
        placeholder="Search...",
        label_visibility="collapsed",
    )

if st.session_state.current_page == "Dashboard":
# ------------------------------------------------------------------
# BANNER
# ------------------------------------------------------------------
    st.markdown(
    """
    <div class="gp-banner">
        <h1>GovPulse Media Intelligence</h1>
        <p>Real-time sentiment monitoring and institutional impact analysis.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
elif st.session_state.current_page == "Monitoring":          # <-- HERE
    st.markdown("<div class='mict-heading-left'>📡 Monitoring</div>", unsafe_allow_html=True)
    st.info("Monitoring view coming soon.")

elif st.session_state.current_page == "Reports":
    st.markdown("<div class='mict-heading-left'>📄 Reports</div>", unsafe_allow_html=True)
    st.info("Reports archive coming soon.")

elif st.session_state.current_page == "Settings":
    st.markdown("<div class='mict-heading-left'>⚙️ Settings</div>", unsafe_allow_html=True)
    st.info("Settings panel coming soon.")

# ------------------------------------------------------------------
# SUMMARY STATS — MICT-style four-card row
# ------------------------------------------------------------------
stories = st.session_state.mapped
total = len(stories) or 1
pos = sum(1 for s in stories if s.get("sentiment") == "Positive")
neu = sum(1 for s in stories if s.get("sentiment") == "Neutral")
neg = sum(1 for s in stories if s.get("sentiment") == "Negative")

c1, c2, c3, c4 = st.columns(4)

c1.markdown(f"""
    <div class="mict-card">
        <div class="mict-card-title">Positive Sentiment</div>
        <div class="mict-card-body">
            <div style="font-size:30px; font-weight:700; color:#16A34A;">{pos/total*100:.1f}%</div>
            <div style="color:#6B7280; margin-top:6px;">{pos} stories in cycle</div>
        </div>
        <a class="mict-card-link" href="#">Read more</a>
    </div>
""", unsafe_allow_html=True)

c2.markdown(f"""
    <div class="mict-card">
        <div class="mict-card-title">Neutral Sentiment</div>
        <div class="mict-card-body">
            <div style="font-size:30px; font-weight:700; color:#6B7280;">{neu/total*100:.1f}%</div>
            <div style="color:#6B7280; margin-top:6px;">{neu} stories in cycle</div>
        </div>
        <a class="mict-card-link" href="#">Read more</a>
    </div>
""", unsafe_allow_html=True)

c3.markdown(f"""
    <div class="mict-card">
        <div class="mict-card-title">Negative Sentiment</div>
        <div class="mict-card-body">
            <div style="font-size:30px; font-weight:700; color:#DC2626;">{neg/total*100:.1f}%</div>
            <div style="color:#6B7280; margin-top:6px;">{neg} stories in cycle</div>
        </div>
        <a class="mict-card-link" href="#">Read more</a>
    </div>
""", unsafe_allow_html=True)

c4.markdown(f"""
    <div class="mict-card">
        <div class="mict-card-title">Total Mentions</div>
        <div class="mict-card-body">
            <div style="font-size:30px; font-weight:700; color:#1E5AA8;">{total}</div>
            <div style="color:#6B7280; margin-top:6px;">Current cycle</div>
        </div>
        <a class="mict-card-link" href="#">Read more</a>
    </div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ------------------------------------------------------------------
# MAIN LAYOUT
# ------------------------------------------------------------------
left, right = st.columns([1.5, 1])


# ---------- LEFT: Review Queue ----------
with left:
    qf_label_col, qf_all_col, qf_neg_col, qf_neu_col, qf_pos_col = st.columns([2, 1, 1, 1, 1])

    with qf_label_col:
        st.markdown(
            "<div class='mict-heading-left' style='margin:0;'>Review Queue</div>",
            unsafe_allow_html=True,
        )
    with qf_all_col:
        if st.button("All", key="qf_all", use_container_width=True):
            st.session_state.quick_filter = "All"
            st.rerun()
    with qf_neg_col:
        if st.button("🔴 Neg", key="qf_neg", use_container_width=True):
            st.session_state.quick_filter = "Negative"
            st.rerun()
    with qf_neu_col:
        if st.button("⚫ Neu", key="qf_neu", use_container_width=True):
            st.session_state.quick_filter = "Neutral"
            st.rerun()
    with qf_pos_col:
        if st.button("🟢 Pos", key="qf_pos", use_container_width=True):
            st.session_state.quick_filter = "Positive"
            st.rerun()

    st.markdown(
        f"<div style='font-size:12px; color:var(--muted); margin-bottom:12px;'>"
        f"{len(stories)} pending · showing: {st.session_state.quick_filter}</div>",
        unsafe_allow_html=True,
    )

    filtered = stories
    if source_filter:
        filtered = [s for s in filtered if s.get("source") in source_filter]
    if sentiment_filter and len(sentiment_filter) < 3:
        filtered = [s for s in filtered if s.get("sentiment") in sentiment_filter]
    if st.session_state.quick_filter != "All":
        filtered = [s for s in filtered if s.get("sentiment") == st.session_state.quick_filter]
    if search_query:
        q = search_query.lower()
        filtered = [
            s for s in filtered
            if q in s.get("headline", "").lower()
            or q in s.get("ai_summary", "").lower()
            or q in " ".join(s.get("oma", [])).lower()
        ]

    filtered = sorted(filtered, key=lambda s: (
        0 if s.get("sentiment") == "Negative" else
        1 if s.get("sentiment") == "Neutral" else 2
    ))

    if not filtered:
        st.info("No stories match the current filters.")

    for idx, story in enumerate(filtered[:8]):
        sentiment = story.get("sentiment", "Neutral")
        text_c, bg_c = sentiment_color(sentiment)
        oma_text = ", ".join(story.get("oma", ["Unmapped"]))
        conf_pct = int((story.get("sentiment_confidence", 0.5)) * 100)

        st.markdown(f"""
            <div class="gp-story" style="border-left:4px solid {text_c};">
                <span class="gp-badge" style="background:{bg_c}; color:{text_c};">
                    {sentiment.upper()}
                </span>
                <span style="font-size:10px; color:#9CA3AF; margin-left:8px;">
                    1h ago
                </span>
                <div class="gp-headline">{story.get('headline', '')}</div>
                <div class="gp-oma">{oma_text}</div>
                <div style="display:flex; align-items:center; margin-top:10px; font-size:11px;">
                    <span style="color:var(--muted); margin-right:8px;">CONFIDENCE</span>
                    <div style="flex:1; height:5px; background:var(--border); border-radius:3px; overflow:hidden;">
                        <div style="width:{conf_pct}%; height:100%; background:#1E5AA8;"></div>
                    </div>
                    <span style="margin-left:8px; font-weight:600; color:var(--text);">{conf_pct}%</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        if sentiment == "Negative" and story.get("oma") != ["Unmapped"]:
            if st.button("✍️ Open Response Desk", key=f"resp_{idx}"):
                st.session_state.selected_story_headline = story.get("headline", "")
                st.session_state.editing_headline = None
                st.rerun()


# ---------- RIGHT: Response Desk + Monitoring ----------
with right:
    neg_by_oma = {}
    for s in stories:
        if s.get("sentiment") == "Negative":
            for m in s.get("oma", []):
                neg_by_oma[m] = neg_by_oma.get(m, 0) + 1

    crisis = [m for m, c in neg_by_oma.items() if c >= 3 and m != "Unmapped"]

    if crisis:
        top = max(crisis, key=lambda m: neg_by_oma[m])
        st.markdown(f"""
            <div class="gp-crisis">
                <div class="gp-crisis-title">⚠️ CRISIS ALERT: {top}</div>
                <div class="gp-crisis-body">
                    Negative coverage has reached {neg_by_oma[top]} stories in the current cycle.
                    Review the Response Desk draft below.
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown(
        "<div class='gp-panel-title'>✍️ Strategic Response Draft</div>"
        "<div class='gp-panel-sub'>Suggested response based on institutional precedent</div>",
        unsafe_allow_html=True,
    )

    selected = None
    if st.session_state.selected_story_headline:
        for resp in st.session_state.responses:
            if resp["headline"] == st.session_state.selected_story_headline:
                if resp.get("response", {}).get("status") == "ok":
                    selected = resp
                    break
    if not selected:
        for resp in st.session_state.responses:
            if resp.get("response", {}).get("status") == "ok":
                selected = resp
                break

    if not selected:
        st.info("No draft available. Click 'Open Response Desk' on a negative story.")
    else:
        r = selected["response"]
        key = selected["headline"]
        approved = key in st.session_state.approvals
        editing = st.session_state.editing_headline == key

        # ---------- EDIT MODE ----------
        if editing:
            st.markdown(
                f"<div style='font-size:11px; color:var(--muted); margin-bottom:8px;'>"
                f"For: <b>{r.get('ministry', 'Unknown')}</b></div>",
                unsafe_allow_html=True,
            )
            edited_text = st.text_area(
                "Edit draft",
                value=r["draft"],
                height=260,
                label_visibility="collapsed",
                key=f"edit_{key}",
            )
            e1, e2 = st.columns(2)
            if e1.button("💾 Save Edit", use_container_width=True):
                for resp in st.session_state.responses:
                    if resp["headline"] == key:
                        resp["response"]["draft"] = edited_text
                        break
                save_json(st.session_state.responses, RESPONSES_FILE)
                st.session_state.editing_headline = None
                st.success("Draft saved.")
                st.rerun()
            if e2.button("Cancel", use_container_width=True):
                st.session_state.editing_headline = None
                st.rerun()

        # ---------- NORMAL VIEW ----------
        else:
            st.markdown(f"""
                <div class="gp-response">
                    <div style="font-size:11px; color:var(--muted);">For: <b>{r.get('ministry', 'Unknown')}</b></div>
                    <div style="font-size:13px; color:var(--body); margin-top:10px; line-height:1.5;">
                        {r['draft']}
                    </div>
                    <div style="font-size:10px; color:#9CA3AF; margin-top:10px;">
                        Drafted by AI Assistant • Precedents: {', '.join(r.get('precedents_used', []))}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        # ---------- PRECEDENT VIEWER ----------
        if r.get("precedents"):
            with st.expander("📄 View Precedent Statements"):
                for p in r["precedents"]:
                    st.markdown(
                        f"<div style='color:var(--text); font-weight:600; "
                        f"font-size:13px; margin-bottom:6px;'>"
                        f"{p['filename']}</div>",
                        unsafe_allow_html=True,
                    )
                    content = p["content"]
                    display = content[:800] + ("..." if len(content) > 800 else "")
                    st.markdown(
                        f"<div style='color:var(--body); font-size:12px; "
                        f"line-height:1.5; white-space:pre-wrap; "
                        f"background:var(--subtle); padding:12px; "
                        f"border-radius:6px;'>{display}</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown("<div style='height:8px;'></div>",
                                unsafe_allow_html=True)

        # ---------- ACTION BUTTONS ----------
        if not editing:
            bc1, bc2, bc3 = st.columns(3)
            if bc1.button("✅ Approve", use_container_width=True, disabled=approved):
                st.session_state.approvals[key] = {
                    "approved_at": datetime.now().isoformat(),
                    "ministry": r.get("ministry", ""),
                    "final_text": r["draft"],
                }
                save_json(st.session_state.approvals, APPROVALS_FILE)

                with st.spinner("Regenerating daily brief with approved response..."):
                    subprocess.run(
                        [sys.executable, "src/report.py"],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )
                st.rerun()

            if bc2.button("✏️ Edit", use_container_width=True, disabled=approved):
                st.session_state.editing_headline = key
                st.rerun()

            if bc3.button("❌ Reject", use_container_width=True, disabled=approved):
                if key in st.session_state.approvals:
                    del st.session_state.approvals[key]
                    save_json(st.session_state.approvals, APPROVALS_FILE)
                st.warning("Response rejected.")

            if approved:
                st.success(f"Approved at {st.session_state.approvals[key]['approved_at'][:19]}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='gp-panel-title'>📡 Active Monitoring Channels</div>",
        unsafe_allow_html=True,
    )

    mc1, mc2 = st.columns(2)
    for col, (label, val) in zip(
        [mc1, mc2],
        [("SOCIAL", "1.2K"), ("PRINT", "84")],
    ):
        col.markdown(f"""
            <div class="gp-metric" style="text-align:center; padding:12px;">
                <div class="gp-metric-value">{val}</div>
                <div class="gp-metric-label" style="margin-top:4px;">{label}</div>
            </div>
        """, unsafe_allow_html=True)


# ------------------------------------------------------------------
# RECENT NATIONAL COVERAGE
# ------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    "<div class='mict-heading-left'>Recent National Coverage</div>"
    "<div style='font-size:12px; color:var(--muted); margin-bottom:12px;'>"
    "Latest media mentions across monitored sources</div>",
    unsafe_allow_html=True,
)

if stories:
    rows = []
    for i, s in enumerate(stories[:10]):
        rows.append({
            "Source":          s.get("source", ""),
            "Media Headline":  s.get("headline", ""),
            "Region":          "NA",
            "Sentiment":       s.get("sentiment", "Neutral"),
            "Reach":           f"{(i+1)*2}.{(i*3) % 10}M",
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ------------------------------------------------------------------
# DAILY BRIEF — DUAL DOWNLOAD
# ------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
bcol1, bcol2, bcol3 = st.columns([1, 1, 3])

with bcol1:
    xlsx_path = "data/processed/daily_brief.xlsx"
    if os.path.exists(xlsx_path):
        with open(xlsx_path, "rb") as f:
            st.download_button(
                label="⬇️ Download Excel",
                data=f.read(),
                file_name=f"daily_brief_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

with bcol2:
    pdf_path = "data/processed/daily_brief.pdf"
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="⬇️ Download PDF",
                data=f.read(),
                file_name=f"daily_brief_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

with bcol3:
    approved_count = len(st.session_state.approvals)
    drafts_ok = sum(
        1 for r in st.session_state.responses
        if r.get("response", {}).get("status") == "ok"
    )
    st.caption(
        f"Stories: {total} | "
        f"Mapped: {sum(1 for s in stories if s.get('oma') and s['oma'] != ['Unmapped'])} | "
        f"Drafts: {drafts_ok} | Approved: {approved_count}"
    )

st.divider()
st.markdown(
    "<div style='font-size:11px; color:#9CA3AF; padding:8px 0;'>"
    "GOVPULSE V1.0 &nbsp;•&nbsp; © 2026 GovPulse. All Rights Reserved. &nbsp;•&nbsp; "
    " National ICT Summit Hackathon 2026"
    "</div>",
    unsafe_allow_html=True,
)
