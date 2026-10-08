"""
GovPulse — Streamlit Dashboard
Matches the Visily mockup: institutional, clean, government-ready.
"""

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
MAPPED_FILE    = "data/processed/mapped.json"
RESPONSES_FILE = "data/processed/responses.json"
APPROVALS_FILE = "data/processed/approvals.json"


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
# GLOBAL STYLING
# ------------------------------------------------------------------
st.markdown(
    """
    <style>
        /* Base colours */
        html, body, [class*="css"] {
            font-family: 'Segoe UI', Roboto, sans-serif;
        }
        .stApp {
            background: #F5F6FA;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: #0F2540;
            color: white;
        }
        section[data-testid="stSidebar"] * {
            color: #E5EAF3 !important;
        }
        section[data-testid="stSidebar"] .stButton button {
            background: #1E3A5F;
            color: white !important;
            border: none;
            border-radius: 6px;
            width: 100%;
            text-align: left;
        }
        section[data-testid="stSidebar"] .stButton button:hover {
            background: #2A4A73;
        }
        section[data-testid="stSidebar"] hr {
            border-color: #1E3A5F;
        }

        /* Metric cards */
        .gp-metric {
            background: white;
            border-radius: 10px;
            padding: 16px 18px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            border-left: 4px solid #E5E7EB;
        }
        .gp-metric-label {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #6B7280;
            margin-bottom: 6px;
        }
        .gp-metric-value {
            font-size: 28px;
            font-weight: 700;
            color: #111827;
            line-height: 1.1;
        }
        .gp-metric-delta {
            font-size: 12px;
            color: #16A34A;
            margin-top: 4px;
        }

        /* Story cards */
        .gp-story {
            background: white;
            border-radius: 10px;
            padding: 14px 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 10px;
        }
        .gp-badge {
            display: inline-block;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .gp-headline {
            font-size: 15px;
            font-weight: 600;
            color: #111827;
            margin: 8px 0 4px 0;
        }
        .gp-oma {
            font-size: 11px;
            color: #6B7280;
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }

        /* Crisis alert */
        .gp-crisis {
            background: #FEE2E2;
            border-left: 4px solid #DC2626;
            border-radius: 8px;
            padding: 14px 16px;
            margin-bottom: 12px;
        }
        .gp-crisis-title {
            font-weight: 700;
            color: #991B1B;
            font-size: 14px;
            margin-bottom: 4px;
        }
        .gp-crisis-body {
            font-size: 12px;
            color: #7F1D1D;
        }

        /* Response panel */
        .gp-response {
            background: white;
            border-radius: 10px;
            padding: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .gp-panel-title {
            font-size: 14px;
            font-weight: 700;
            color: #111827;
            margin-bottom: 4px;
        }
        .gp-panel-sub {
            font-size: 11px;
            color: #6B7280;
            margin-bottom: 12px;
        }

        /* Header banner */
        .gp-banner {
            background: #0F2540;
            border-radius: 10px;
            padding: 24px 28px;
            color: white;
            margin-bottom: 20px;
        }
        .gp-banner h1 {
            color: white;
            font-size: 26px;
            margin: 0 0 6px 0;
        }
        .gp-banner p {
            color: #B0C0D8;
            font-size: 13px;
            margin: 0;
        }

        /* Dataframe override */
        .stDataFrame {
            background: white;
            border-radius: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# SESSION STATE
# ------------------------------------------------------------------
if "mapped" not in st.session_state:
    st.session_state.mapped = load_json(MAPPED_FILE)
if "responses" not in st.session_state:
    st.session_state.responses = load_json(RESPONSES_FILE)
if "approvals" not in st.session_state:
    st.session_state.approvals = load_json(APPROVALS_FILE, default={})
if "selected_story_headline" not in st.session_state:
    st.session_state.selected_story_headline = None


# ------------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div style="padding: 12px 4px 20px 4px;">
            <div style="font-size: 18px; font-weight: 700; color: white;">
                🛡️ GovPulse
            </div>
            <div style="font-size: 11px; color: #8899B0; margin-top: 4px;">
                Media Intelligence
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("##### NAVIGATION")
    st.button("📊  Dashboard", use_container_width=True)
    st.button("📡  Monitoring", use_container_width=True)
    st.button("🔔  Alerts", use_container_width=True)
    st.button("📄  Reports", use_container_width=True)
    st.button("⚙️  Settings", use_container_width=True)

    st.divider()
    st.markdown("##### PIPELINE")
    if st.button("🔄  Run Full Pipeline", use_container_width=True):
        if run_pipeline():
            st.session_state.mapped = load_json(MAPPED_FILE)
            st.session_state.responses = load_json(RESPONSES_FILE)
            st.rerun()

    if st.button("📄  Regenerate Brief", use_container_width=True):
        subprocess.run([sys.executable, "src/report.py"], check=False)
        st.success("Brief regenerated.")

    st.divider()
    st.markdown("##### FILTERS")
    source_filter = st.multiselect(
        "Source",
        options=sorted({s.get("source", "Unknown") for s in st.session_state.mapped}),
        default=[],
    )
    sentiment_filter = st.multiselect(
        "Sentiment",
        options=["Positive", "Neutral", "Negative"],
        default=[],
    )

    st.divider()
    st.caption(f"Loaded: {len(st.session_state.mapped)} stories")
    drafts_ok = sum(1 for r in st.session_state.responses
                    if r.get("response", {}).get("status") == "ok")
    st.caption(f"Drafts: {drafts_ok}")


# ------------------------------------------------------------------
# TOP BAR
# ------------------------------------------------------------------
top_l, top_r = st.columns([6, 1])
with top_l:
    st.markdown(
        """
        <div style="background:white; border-radius:8px; padding:10px 16px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            🔍 <span style="color:#9CA3AF; font-size:13px;">
                Search media, sentiments, or reports...
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
with top_r:
    st.markdown(
        """
        <div style="background:white; border-radius:8px; padding:10px 16px;
                    text-align:right; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            🔔 &nbsp; 👤
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------
# BANNER
# ------------------------------------------------------------------
st.markdown(
    """
    <div class="gp-banner">
        <h1>GovPulse Media Intelligence</h1>
        <p>Real-time sentiment monitoring and institutional impact analysis for the current briefing cycle.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# SUMMARY STATS
# ------------------------------------------------------------------
stories = st.session_state.mapped
total = len(stories) or 1
pos = sum(1 for s in stories if s.get("sentiment") == "Positive")
neu = sum(1 for s in stories if s.get("sentiment") == "Neutral")
neg = sum(1 for s in stories if s.get("sentiment") == "Negative")

c1, c2, c3, c4 = st.columns(4)

c1.markdown(f"""
    <div class="gp-metric" style="border-left-color:#16A34A;">
        <div class="gp-metric-label">🟢 Positive Sentiment</div>
        <div class="gp-metric-value">{pos / total * 100:.1f}%</div>
        <div class="gp-metric-delta">▲ {pos} stories</div>
    </div>
""", unsafe_allow_html=True)

c2.markdown(f"""
    <div class="gp-metric" style="border-left-color:#9CA3AF;">
        <div class="gp-metric-label">⚫ Neutral Sentiment</div>
        <div class="gp-metric-value">{neu / total * 100:.1f}%</div>
        <div class="gp-metric-delta" style="color:#6B7280;">▼ {neu} stories</div>
    </div>
""", unsafe_allow_html=True)

c3.markdown(f"""
    <div class="gp-metric" style="border-left-color:#DC2626;">
        <div class="gp-metric-label">🔴 Negative Sentiment</div>
        <div class="gp-metric-value">{neg / total * 100:.1f}%</div>
        <div class="gp-metric-delta" style="color:#DC2626;">▲ {neg} stories</div>
    </div>
""", unsafe_allow_html=True)

c4.markdown(f"""
    <div class="gp-metric" style="border-left-color:#1E5AA8;">
        <div class="gp-metric-label">📊 Total Mentions</div>
        <div class="gp-metric-value">{total}</div>
        <div class="gp-metric-delta">Current cycle</div>
    </div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ------------------------------------------------------------------
# MAIN LAYOUT
# ------------------------------------------------------------------
left, right = st.columns([1.5, 1])


# ---------- LEFT: Review Queue ----------
with left:
    st.markdown(
        "<div style='font-size:18px; font-weight:700; color:#111827; margin-bottom:4px;'>"
        "Review Queue</div>"
        f"<div style='font-size:12px; color:#6B7280; margin-bottom:12px;'>"
        f"{len(stories)} pending</div>",
        unsafe_allow_html=True,
    )

    filtered = stories
    if source_filter:
        filtered = [s for s in filtered if s.get("source") in source_filter]
    if sentiment_filter:
        filtered = [s for s in filtered if s.get("sentiment") in sentiment_filter]

    filtered = sorted(filtered, key=lambda s: (
        0 if s.get("sentiment") == "Negative" else
        1 if s.get("sentiment") == "Neutral" else 2
    ))

    for idx, story in enumerate(filtered[:6]):  # limit for demo
        sentiment = story.get("sentiment", "Neutral")
        text_c, bg_c = sentiment_color(sentiment)
        oma_text = ", ".join(story.get("oma", ["Unmapped"]))
        impact = 88 if sentiment == "Negative" else 60

        st.markdown(f"""
            <div class="gp-story">
                <span class="gp-badge" style="background:{bg_c}; color:{text_c};">
                    {sentiment.upper()}
                </span>
                <span style="font-size:10px; color:#9CA3AF; margin-left:8px;">
                    1h ago
                </span>
                <div class="gp-headline">{story.get('headline', '')}</div>
                <div class="gp-oma">{oma_text}</div>
                <div style="display:flex; align-items:center; margin-top:10px; font-size:11px;">
                    <span style="color:#6B7280; margin-right:8px;">IMPACT</span>
                    <div style="flex:1; height:5px; background:#E5E7EB; border-radius:3px; overflow:hidden;">
                        <div style="width:{impact}%; height:100%; background:#1E5AA8;"></div>
                    </div>
                    <span style="margin-left:8px; font-weight:600; color:#111827;">{impact}%</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        if sentiment == "Negative" and story.get("oma") != ["Unmapped"]:
            if st.button("✍️ Open Response Desk", key=f"resp_{idx}"):
                st.session_state.selected_story_headline = story.get("headline", "")
                st.rerun()


# ---------- RIGHT: Response Desk + Monitoring ----------
with right:
    # Crisis Alert
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

    # Response Desk
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
        st.markdown(f"""
            <div class="gp-response">
                <div style="font-size:11px; color:#6B7280;">For: <b>{r.get('ministry', 'Unknown')}</b></div>
                <div style="font-size:13px; color:#374151; margin-top:10px; line-height:1.5;">
                    {r['draft']}
                </div>
                <div style="font-size:10px; color:#9CA3AF; margin-top:10px;">
                    Drafted by AI Assistant • Precedents: {', '.join(r.get('precedents_used', []))}
                </div>
            </div>
        """, unsafe_allow_html=True)

        key = selected["headline"]
        approved = key in st.session_state.approvals
        bc1, bc2, bc3 = st.columns(3)
        if bc1.button("✅ Approve", use_container_width=True, disabled=approved):
            st.session_state.approvals[key] = {
                "approved_at": datetime.now().isoformat(),
                "ministry": r.get("ministry", ""),
                "final_text": r["draft"],
            }
            save_json(st.session_state.approvals, APPROVALS_FILE)
            st.rerun()
        bc2.button("✏️ Edit", use_container_width=True)
        bc3.button("❌ Reject", use_container_width=True)

        if approved:
            st.success(f"Approved at {st.session_state.approvals[key]['approved_at'][:19]}")

    # Monitoring Channels
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='gp-panel-title'>📡 Active Monitoring Channels</div>",
        unsafe_allow_html=True,
    )

    mc1, mc2, mc3 = st.columns(3)
    for col, (label, val) in zip(
        [mc1, mc2, mc3],
        [("RADIO", "142"), ("SOCIAL", "1.2K"), ("PRINT", "84")],
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
    "<div style='font-size:18px; font-weight:700; color:#111827; margin-bottom:4px;'>"
    "Recent National Coverage</div>"
    "<div style='font-size:12px; color:#6B7280; margin-bottom:12px;'>"
    "Latest media mentions across monitored sources</div>",
    unsafe_allow_html=True,
)

if stories:
    rows = []
    for s in stories[:10]:
        rows.append({
            "Source":      s.get("source", ""),
            "Media Headline": s.get("headline", ""),
            "Region":      "NA",
            "Sentiment":   s.get("sentiment", "Neutral"),
            "Reach":       f"{(idx+1)*2}.{(idx*3) % 10}M",
        })
    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )


# ------------------------------------------------------------------
# DAILY BRIEF + FOOTER
# ------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
bcol1, bcol2 = st.columns([1, 4])
with bcol1:
    brief_path = "data/processed/daily_brief.xlsx"
    if os.path.exists(brief_path):
        with open(brief_path, "rb") as f:
            st.download_button(
                label="⬇️ Download Daily Brief",
                data=f.read(),
                file_name=f"daily_brief_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
with bcol2:
    approved_count = len(st.session_state.approvals)
    drafts_ok = sum(1 for r in st.session_state.responses
                    if r.get("response", {}).get("status") == "ok")
    st.caption(
        f"Stories: {total} | Mapped: {sum(1 for s in stories if s.get('oma') and s['oma'] != ['Unmapped'])} | "
        f"Drafts: {drafts_ok} | Approved: {approved_count}"
    )

st.divider()
st.markdown(
    f"<div style='font-size:11px; color:#9CA3AF; padding:8px 0;'>"
    f"GOVPULSE V1.0  &nbsp;•&nbsp;  © 2026 GovPulse. All Rights Reserved.  &nbsp;•&nbsp;  "
    f"Team Binary — National ICT Summit Hackathon 2026"
    f"</div>",
    unsafe_allow_html=True,
)