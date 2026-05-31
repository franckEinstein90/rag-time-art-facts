"""Settings page — stores user profile information in the app's SQLite database."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from model_registry import build_model_manager  # noqa: E402
from settings_db import load_user_profile, save_user_profile  # noqa: E402
from ui import render_sidebar  # noqa: E402

_PROFILE_FIELDS: list[tuple[str, str, str]] = [
    ("user.name",     "Full Name",        "Jane Smith"),
    ("user.email",    "Email Address",    "jane@example.com"),
    ("user.linkedin", "LinkedIn URL",     "https://linkedin.com/in/janesmith"),
    ("user.github",   "GitHub URL",       "https://github.com/janesmith"),
    ("user.phone",    "Phone Number",     "+1 (555) 000-1234"),
]


# ── page ──────────────────────────────────────────────────────────────────────

try:
    model_manager = build_model_manager(allow_empty=True)
except Exception as exc:
    st.error(f"Configuration error: {exc}")
    st.stop()

render_sidebar(model_manager, show_clear_results=False)

st.subheader("⚙️ Settings")
st.caption("Your profile information is used to personalise cover letters and other outputs.")

current = load_user_profile()

with st.form("profile_form"):
    inputs: dict[str, str] = {}
    for key, label, placeholder in _PROFILE_FIELDS:
        inputs[key] = st.text_input(
            label,
            value=current.get(key, ""),
            placeholder=placeholder,
        )

    submitted = st.form_submit_button("💾 Save", use_container_width=True)

if submitted:
    save_user_profile(inputs)
    st.success("Profile saved.")
