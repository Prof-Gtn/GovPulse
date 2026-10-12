"""
GovPulse — Shared authentication module.
Call require_login() at the top of each page.
"""

import os
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "app", "config.yaml")


def load_config():
    """Load users from app/config.yaml."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.load(f, Loader=SafeLoader)


def get_authenticator(config):
    """Build the Streamlit-Authenticator object."""
    return stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )


def require_login(page_title: str = "GovPulse"):
    """
    Enforce login on a page. Returns (config, authenticator, user_dict).
    Call at the very top of every page.
    """
    config = load_config()
    authenticator = get_authenticator(config)

    # Show login form in the sidebar
    try:
        authenticator.login(location="sidebar")
    except Exception as e:
        st.error(str(e))

    auth_status = st.session_state.get("authentication_status")

    if auth_status is None:
        # Not logged in — show welcome screen
        st.markdown(
            f"""
            <div style="background:linear-gradient(90deg,#0F2540 0%,#1A3556 100%);
                        padding:40px 30px; border-radius:12px; color:white;
                        max-width:560px; margin:80px auto; text-align:center;">
                <h1 style="color:white; margin:0 0 8px 0;">🛡️ GovPulse</h1>
                <p style="color:#B0C0D8; margin:0; font-size:14px;">
                    Government Media Intelligence Platform
                </p>
                <hr style="border-color:#1E3A5F; margin:24px 0;">
                <p style="color:#B0C0D8; margin:0; font-size:13px;">
                    Please log in from the sidebar to access <b>{page_title}</b>.
                </p>
                <div style="margin-top:24px; padding:14px; background:#1A3556;
                            border-radius:8px; font-size:12px; color:#8899B0;">
                    Demo credentials: <b>lucia</b> / <b>changeme123</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

    if auth_status is False:
        st.error("Username or password is incorrect.")
        st.stop()

    # Logged in
    username = st.session_state.get("username")
    user = dict(config["credentials"]["usernames"].get(username, {}))
    user["username"] = username

    return config, authenticator, user


def get_user_role(user: dict) -> str:
    """Returns 'admin', 'ministry', or 'viewer'."""
    return user.get("role", "viewer")


def get_user_ministry(user: dict) -> str:
    """Returns the ministry name for ministry-scoped users."""
    return user.get("ministry", "")


def is_admin(user: dict) -> bool:
    """Check if the user has admin permissions."""
    return get_user_role(user) == "admin"


def render_user_header(authenticator, user: dict):
    """
    Render the signed-in user + logout button in the sidebar.
    Call this inside `with st.sidebar:` at the top of each page.
    """
    st.markdown(
        f"""
        <div style="padding:12px 4px 16px 4px;">
            <div style="font-size:18px; font-weight:700; color:white;">
                🛡️ GovPulse
            </div>
            <div style="font-size:11px; color:#8899B0; margin-top:6px;">
                Signed in as <b>{user.get('name', 'User')}</b><br>
                Role: {get_user_role(user).title()}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    authenticator.logout("Logout", "sidebar")
    st.divider()