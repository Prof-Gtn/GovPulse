"""
GovPulse — Streamlit Dashboard
The visual interface MICT staff use to review, approve, and respond.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
import streamlit as st


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
    """Safely load a JSON file."""
    if not os.path.exists(path):
        return default if default is not None else []
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        st.warning(f"Could not load {path}: {e}")
        return default if default is not None else []


def save_json(data, path):
    """Save data to JSON."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def run_pipeline():
    """Run the full GovPulse pipeline."""
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
            result = subprocess.run(
                [sys.executable, script],
                capture_output=True,
                text=True,
                timeout=180,
            )
            if result.returncode != 0:
                st.error(f"Error in {script}: {result.stderr[:500]}")
                return False
        except subprocess.TimeoutExpired:
            st.error(f"{script} timed out.")
            return False

    progress.progress(1.0, text="Pipeline complete.")
    st.success("Pipeline complete.")
    return True


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
    st.markdown("## 🛡️ GovPulse")
    st.caption("Government Media Intelligence Platform")
    st.divider()

    st.markdown("### Controls")
    if st.button("🔄 Run Full Pipeline", use_container_width=True):
        if run_pipeline():
            st.session_state.mapped = load_json(MAPPED_FILE)
            st.session_state.responses = load_json(RESPONSES_FILE)
            st.rerun()

    if st.button("📄 Regenerate Brief", use_container_width=True):
        subprocess.run([sys.executable, "src/report.py"], check=False)
        st.success("Brief regenerated.")

    st.divider()

    st.markdown("### Filters")
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
    oma_filter = st.multiselect(
        "Institution",
        options=sorted({m for s in st.session_state.mapped for m in s.get("oma", [])}),
        default=[],
    )

    st.divider()
    st.caption(f"Loaded: {len(st.session_state.mapped)} stories")
    drafts_ok = sum(1 for r in st.session_state.responses
                    if r.get("response", {}).get("status") == "ok")
    st.caption(f"Drafts: {drafts_ok}")


# ------------------------------------------------------------------
# HEADER
# ------------------------------------------------------------------
st.markdown(
    """
    <div style="background-color:#1F3864; padding:20px; border-radius:8px; margin-bottom:20px;">
        <h1 style="color:white; margin:0;">GovPulse Media Intelligence</h1>
        <p style="color:#D0D7E5; margin:5px 0 0 0;">
            Real-time sentiment monitoring and institutional impact analysis
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# SUMMARY STATS
# ------------------------------------------------------------------
stories = st.session_state.mapped

pos = sum(1 for s in stories if s.get("sentiment") == "Positive")
neu = sum(1 for s in stories if s.get("sentiment") == "Neutral")
neg = sum(1 for s in stories if s.get("sentiment") == "Negative")
total = len(stories)
mapped_count = sum(1 for s in stories if s.get("oma") and s["oma"] != ["Unmapped"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("🟢 Positive", pos)
col2.metric("⚫ Neutral",  neu)
col3.metric("🔴 Negative", neg)
col4.metric("📊 Total Stories", total)


# ------------------------------------------------------------------
# CRISIS ALERT
# ------------------------------------------------------------------
negatives_by_oma = {}
for s in stories:
    if s.get("sentiment") == "Negative":
        for m in s.get("oma", []):
            negatives_by_oma[m] = negatives_by_oma.get(m, 0) + 1

crisis_ministries = [m for m, c in negatives_by_oma.items() if c >= 3 and m != "Unmapped"]

if crisis_ministries:
    top_crisis = max(crisis_ministries, key=lambda m: negatives_by_oma[m])
    st.error(
        f"🚨 **Crisis Alert:** Negative coverage of **{top_crisis}** "
        f"has reached {negatives_by_oma[top_crisis]} stories in the current cycle. "
        f"Open the Response Desk below to review the draft response."
    )


# ------------------------------------------------------------------
# MAIN LAYOUT
# ------------------------------------------------------------------
left, right = st.columns([1.3, 1])


# ---------- LEFT: Review Queue ----------
with left:
    st.subheader("📋 Review Queue")

    filtered = stories
    if source_filter:
        filtered = [s for s in filtered if s.get("source") in source_filter]
    if sentiment_filter:
        filtered = [s for s in filtered if s.get("sentiment") in sentiment_filter]
    if oma_filter:
        filtered = [s for s in filtered if any(m in oma_filter for m in s.get("oma", []))]

    # Sort: Negative first, then Neutral, then Positive
    filtered = sorted(filtered, key=lambda s: (
        0 if s.get("sentiment") == "Negative" else
        1 if s.get("sentiment") == "Neutral" else 2
    ))

    for idx, story in enumerate(filtered):
        sentiment = story.get("sentiment", "Neutral")
        badge = {"Positive": "🟢", "Neutral": "⚫", "Negative": "🔴"}.get(sentiment, "⚫")
        oma_text = ", ".join(story.get("oma", ["Unmapped"]))

        # Colour-coded card
        bg = {"Positive": "#F0FDF4", "Neutral": "#F9FAFB", "Negative": "#FEF2F2"}.get(sentiment, "#FFFFFF")
        border = {"Positive": "#16A34A", "Neutral": "#9CA3AF", "Negative": "#DC2626"}.get(sentiment, "#E5E7EB")

        st.markdown(
            f"""
            <div style="background:{bg}; border-left:5px solid {border};
                        padding:12px; border-radius:6px; margin-bottom:8px;">
                <div style="font-size:12px; color:#6B7280;">{badge} {sentiment}</div>
                <div style="font-size:16px; font-weight:600; margin:4px 0; color:#111827;">
                    {story.get('headline', '')}
                </div>
                <div style="font-size:13px; color:#374151;">{oma_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Action row
        cols = st.columns([1, 1, 1, 4])
        if cols[0].button("✅", key=f"approve_{idx}", help="Approve"):
            st.success(f"Story approved: {story['headline'][:50]}...")
        if cols[1].button("✏️", key=f"edit_{idx}", help="Edit"):
            st.info("Edit mode not implemented in demo.")
        if cols[2].button("🚩", key=f"flag_{idx}", help="Flag for review"):
            st.warning("Story flagged for senior review.")

        # Response Desk trigger for negative + mapped stories
        if sentiment == "Negative" and story.get("oma") != ["Unmapped"]:
            if st.button("✍️ Open Response Desk", key=f"resp_{idx}"):
                st.session_state.selected_story_headline = story.get("headline", "")
                st.rerun()


# ---------- RIGHT: Response Desk ----------
with right:
    st.subheader("✍️ Response Desk")

    # ---- Determine which story to show ----
    selected_response = None

    # 1. Try the explicitly selected headline
    if st.session_state.selected_story_headline:
        for resp in st.session_state.responses:
            if resp["headline"] == st.session_state.selected_story_headline:
                if resp.get("response", {}).get("status") == "ok":
                    selected_response = resp
                    break

    # 2. Fall back to the first negative story with a successful draft
    if not selected_response:
        for resp in st.session_state.responses:
            if resp.get("response", {}).get("status") == "ok":
                selected_response = resp
                break

    # ---- Render the Response Desk ----
    if not selected_response:
        st.info(
            "No draft available. Click a negative story's "
            "'Open Response Desk' button, or run the pipeline."
        )
    else:
        r = selected_response["response"]
        st.markdown(f"**Story:** {selected_response['headline']}")
        st.markdown(f"**Ministry:** {r.get('ministry', 'Unknown')}")
        if r.get("precedents_used"):
            st.caption(f"Precedents used: {', '.join(r['precedents_used'])}")
        st.divider()

        st.markdown("**Suggested Response:**")
        edited = st.text_area(
            "Draft",
            value=r["draft"],
            height=280,
            label_visibility="collapsed",
            key=f"draft_{selected_response['headline']}",
        )

        key = selected_response["headline"]
        already_approved = key in st.session_state.approvals

        bcol1, bcol2, bcol3 = st.columns(3)

        if bcol1.button(
            "✅ Approve & Sync",
            use_container_width=True,
            disabled=already_approved,
        ):
            st.session_state.approvals[key] = {
                "approved_at": datetime.now().isoformat(),
                "ministry": r.get("ministry", ""),
                "final_text": edited,
            }
            save_json(st.session_state.approvals, APPROVALS_FILE)
            st.success("Response approved and logged.")
            st.rerun()

        if bcol2.button("✏️ Save Draft", use_container_width=True):
            for resp in st.session_state.responses:
                if resp["headline"] == key:
                    resp["response"]["draft"] = edited
                    break
            save_json(st.session_state.responses, RESPONSES_FILE)
            st.info("Draft saved.")

        if bcol3.button("❌ Reject", use_container_width=True):
            st.warning("Response rejected.")

        if already_approved:
            st.success(
                f"✅ Approved at "
                f"{st.session_state.approvals[key]['approved_at'][:19]}"
            )


# ------------------------------------------------------------------
# DAILY BRIEF DOWNLOAD
# ------------------------------------------------------------------
st.divider()
st.subheader("📄 Daily Brief")

bcol1, bcol2 = st.columns([1, 3])
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
    else:
        st.caption("No brief generated yet. Click 'Regenerate Brief' in the sidebar.")

with bcol2:
    approved_count = len(st.session_state.approvals)
    drafts_ok = sum(1 for r in st.session_state.responses
                    if r.get("response", {}).get("status") == "ok")
    st.caption(
        f"Stories: {total}  |  Mapped: {mapped_count}  |  "
        f"Drafts: {drafts_ok}  |  Approved: {approved_count}"
    )


# ------------------------------------------------------------------
# FOOTER
# ------------------------------------------------------------------
st.divider()
st.caption(
    f"GovPulse v1.0 — Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  "
    f"Team Binary — National ICT Summit Hackathon 2026"
)