"""Resume Viewer page for the Job Description Analyzer app."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from model_registry import build_model_manager  # noqa: E402
from resume_page import render_resume_page  # noqa: E402
from ui import render_sidebar  # noqa: E402

try:
    model_manager = build_model_manager(allow_empty=True)
except Exception as exc:
    st.error(f"Configuration error: {exc}")
    st.stop()

render_sidebar(model_manager)
render_resume_page()
