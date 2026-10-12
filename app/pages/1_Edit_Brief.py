"""
GovPulse — Edit Brief
Full-page editable view of today's daily brief.
"""

import json
import os
import subprocess
import sys
from datetime import datetime

import streamlit as st
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.auth import require_login, render_user_header, get_user_role



# ------------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------------
st.set_page_config(
    page_title="GovPulse — Edit Brief",
    page_icon="📝",
    layout="wide",
)
config, authenticator, current_user = require_login("Edit Brief")
user_role = get_user_role(current_user)


# ------------------------------------------------------------------
# PATHS
# ------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAPPED_FILE = os.path.join(PROJECT_ROOT, "data", "processed", "mapped.json")
REPORT_SCRIPT = os.path.join(PROJECT_ROOT, "src", "report.py")


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------
def load_stories():
    with open(MAPPED_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_stories(stories):
    with open(MAPPED_FILE, "w", encoding="utf-8-sig") as f:
        json.dump(stories, f, indent=2, ensure_ascii=False)


def build_dataframe(stories):
    rows = []
    for s in stories:
        rows.append({
            "Headline":       s.get("headline", ""),
            "Brief Summary":  s.get("ai_summary", ""),
            "Sentiment":      s.get("sentiment", "Neutral"),
            "O/M/A":          "; ".join(s.get("oma", [])),
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------
# STYLING
# ------------------------------------------------------------------
st.markdown(
    """
    <style>
        :root {
            --bg: #F5F6FA;
            --card: #FFFFFF;
            --text: #111827;
            --muted: #6B7280;
            --border: #E5E7EB;
        }
        html, body, [class*="css"] {
            font-family: 'Segoe UI', Roboto, sans-serif;
        }
        .stApp { background: var(--bg); }

        /* Sidebar */
        section[data-testid="stSidebar"] { background: #0F2540; }
        section[data-testid="stSidebar"] * { color: #E5EAF3 !important; }
        section[data-testid="stSidebar"] hr { border-color: #1E3A5F; }
        section[data-testid="stSidebar"] a {
            color: #E5EAF3 !important;
            text-decoration: none !important;
        }
        section[data-testid="stSidebar"] a:hover {
            background: #1E3A5F !important;
        }

        /* Buttons */
        .stButton > button,
        .stDownloadButton > button {
            background: #1E3A5F !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 6px !important;
            font-weight: 500 !important;
        }
        .stButton > button:hover,
        .stDownloadButton > button:hover {
            background: #2A4A73 !important;
            color: #FFFFFF !important;
        }

        /* Banner */
        .gp-banner {
            background: linear-gradient(90deg, #0F2540 0%, #1A3556 100%);
            border-radius: 10px;
            padding: 20px 26px;
            color: white;
            margin-bottom: 20px;
        }
        .gp-banner h1 { color: white; font-size: 24px; margin: 0; }
        .gp-banner p { color: #B0C0D8; font-size: 13px; margin: 6px 0 0 0; }

        /* Data editor */
        [data-testid="stDataFrame"] {
            background: white;
            border-radius: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# SIDEBAR HEADER
# ------------------------------------------------------------------
with st.sidebar:
    render_user_header(authenticator, current_user)

    st.markdown("##### NAVIGATION")
    st.page_link("dashboard.py", label="📊  Dashboard")
    st.page_link("pages/1_Edit_Brief.py", label="📝  Edit Brief")
# ------------------------------------------------------------------
# BANNER
# ------------------------------------------------------------------
st.markdown(
    """
    <div class="gp-banner">
        <h1>📝 Edit Today's Brief</h1>
        <p>Review and edit any field below. Changes are saved when you click Save.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------------
if not os.path.exists(MAPPED_FILE):
    st.error(
        "No brief data found. Go to the Dashboard and click "
        "'Generate Today's Brief' first."
    )
    st.stop()

stories = load_stories()

# Only mapped stories appear in the brief
mapped_only = [
    s for s in stories
    if s.get("oma") and s["oma"] != ["Unmapped"]
]

# Stats row
col1, col2, col3 = st.columns(3)
col1.markdown(
    f"<div style='background:white; padding:12px 16px; border-radius:8px;"
    f"border-left:4px solid #1E5AA8;'>"
    f"<div style='font-size:11px; color:#6B7280; text-transform:uppercase;'>"
    f"Stories in Brief</div>"
    f"<div style='font-size:24px; font-weight:700; color:#111827;'>"
    f"{len(mapped_only)}</div></div>",
    unsafe_allow_html=True,
)
col2.markdown(
    f"<div style='background:white; padding:12px 16px; border-radius:8px;"
    f"border-left:4px solid #16A34A;'>"
    f"<div style='font-size:11px; color:#6B7280; text-transform:uppercase;'>"
    f"Positive</div>"
    f"<div style='font-size:24px; font-weight:700; color:#111827;'>"
    f"{sum(1 for s in mapped_only if s.get('sentiment') == 'Positive')}"
    f"</div></div>",
    unsafe_allow_html=True,
)
col3.markdown(
    f"<div style='background:white; padding:12px 16px; border-radius:8px;"
    f"border-left:4px solid #DC2626;'>"
    f"<div style='font-size:11px; color:#6B7280; text-transform:uppercase;'>"
    f"Negative</div>"
    f"<div style='font-size:24px; font-weight:700; color:#111827;'>"
    f"{sum(1 for s in mapped_only if s.get('sentiment') == 'Negative')}"
    f"</div></div>",
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)


# ------------------------------------------------------------------
# BUILD DATAFRAME
# ------------------------------------------------------------------
df = build_dataframe(mapped_only)


# ------------------------------------------------------------------
# EDITABLE TABLE
# ------------------------------------------------------------------
edited = st.data_editor(
    df,
    column_config={
        "Headline": st.column_config.TextColumn(
            "Headline",
            width="large",
            required=True,
        ),
        "Brief Summary": st.column_config.TextColumn(
            "Brief Summary",
            width="large",
        ),
        "Sentiment": st.column_config.SelectboxColumn(
            "Sentiment",
            options=["Positive", "Neutral", "Negative"],
            required=True,
        ),
        "O/M/A": st.column_config.TextColumn(
            "O/M/A",
            width="medium",
            help="Separate multiple institutions with a semicolon (;)",
        ),
    },
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    key="brief_editor",
)


# ------------------------------------------------------------------
# SAVE / CANCEL
# ------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
scol1, scol2, scol3 = st.columns([1, 1, 4])

with scol1:
    if st.button("💾 Save Changes", use_container_width=True):
        headline_to_story = {s.get("headline", ""): s for s in stories}
        changes = 0

        for _, row in edited.iterrows():
            headline = str(row["Headline"]).strip()
            if headline not in headline_to_story:
                continue

            story = headline_to_story[headline]

            new_summary = str(row["Brief Summary"]).strip()
            new_sentiment = str(row["Sentiment"]).strip()
            new_oma_str = str(row["O/M/A"]).strip()

            if new_summary and new_summary != story.get("ai_summary"):
                story["ai_summary"] = new_summary
                changes += 1

            if new_sentiment in ("Positive", "Neutral", "Negative"):
                if new_sentiment != story.get("sentiment"):
                    story["sentiment"] = new_sentiment
                    changes += 1

            if new_oma_str:
                if new_oma_str == "Unmapped":
                    new_oma_list = ["Unmapped"]
                else:
                    new_oma_list = [
                        x.strip() for x in new_oma_str.split(";") if x.strip()
                    ]
                if new_oma_list != story.get("oma"):
                    story["oma"] = new_oma_list
                    changes += 1

        save_stories(stories)

        with st.spinner("Regenerating brief with your edits..."):
            subprocess.run(
                [sys.executable, REPORT_SCRIPT],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=PROJECT_ROOT,
            )

        # Clear the editor's cached state so it rebuilds from disk
        if "brief_editor" in st.session_state:
            del st.session_state["brief_editor"]

        st.success(f"✅ Saved {changes} changes. Brief regenerated.")
        st.rerun()

with scol2:
    if st.button("↩️ Cancel Changes", use_container_width=True):
        # Discard any pending edits by clearing the editor's cached state
        if "brief_editor" in st.session_state:
            del st.session_state["brief_editor"]

        st.info("Pending changes discarded. Reloaded from disk.")
        st.rerun()

with scol3:
    st.caption(
        "💾 **Save** writes your edits to the brief (Excel + PDF). "
        "↩️ **Cancel** discards any unsaved edits and reloads the current brief."
    )


# ------------------------------------------------------------------
# FOOTER
# ------------------------------------------------------------------
st.divider()
st.markdown(
    f"<div style='font-size:11px; color:#9CA3AF; padding:8px 0;'>"
    f"GOVPULSE V1.0  •  © 2026 GovPulse. All Rights Reserved.  •  "
    f"Team Binary — National ICT Summit Hackathon 2026"
    f"</div>",
    unsafe_allow_html=True,
)