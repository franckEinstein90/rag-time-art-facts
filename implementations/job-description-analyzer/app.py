"""
Job Description Analyzer — entrypoint.

Left column  : analysis tools
Right column : paste area for the raw LinkedIn job description

Run with:
    streamlit run implementations/job-description-analyzer/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Ensure project root is on sys.path before local imports
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from model_registry import build_model_manager  # noqa: E402
from ui import render_left_col, render_right_col, render_sidebar  # noqa: E402

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Job Description Analyzer",
    page_icon="💼",
    layout="wide",
)

try:
    model_manager = build_model_manager(allow_empty=True)
except Exception as exc:
    st.error(f"Configuration error: {exc}")
    st.stop()


def _render_job_description_page() -> None:
    st.caption("Paste a LinkedIn job description on the right, then run any analysis tool on the left.")

    active_model = render_sidebar(model_manager)
    if active_model is None:
        st.error("No active models available. Add COHERE_API_KEY or OPENAI_API_KEY to enable the analyzer page.")
        st.stop()

    left_col, right_col = st.columns([1, 1], gap="large")

    with right_col:
        jd_text = render_right_col()

    with left_col:
        render_left_col(jd_text, active_model)


navigation = st.navigation(
    {
        "": [
            st.Page(_render_job_description_page, title="Job Description Analyzer", icon="💼"),
            st.Page("pages/1_Resume_Viewer.py", title="Resume Viewer", icon="📄"),
            st.Page("pages/2_Application_Viewer.py", title="Application Viewer", icon="📁"),
        ],
        " ": [
            st.Page("pages/0_Settings.py", title="Settings", icon=":material/settings:"),
        ],
    },
    position="top",
)

navigation.run()
