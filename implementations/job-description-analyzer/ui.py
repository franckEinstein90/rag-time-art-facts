from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.python.LLM.models import LLMModel  # noqa: E402
from src.python.LLM.LLM_Manager import LLMManager  # noqa: E402
from application_start import render_start_application_section  # noqa: E402
from prompts import prompt_custom  # noqa: E402
from tools import TOOLS  # noqa: E402


def _clear_analysis_outputs() -> None:
    for tool in TOOLS:
        result_key = f"result_{tool['id']}"
        st.session_state.pop(result_key, None)
        st.session_state.pop(f"{result_key}_source", None)
    st.session_state.pop("result_custom", None)
    st.session_state.pop("custom_question_input", None)


def render_sidebar(model_manager: LLMManager, *, show_clear_results: bool = True) -> LLMModel | None:
    """Render the shared sidebar. Returns the active model when available."""
    with st.sidebar:
        st.subheader("Job Description Analyzer")
        st.caption("Use the top navigation to switch pages.")

        st.divider()
        st.subheader("Model")
        models_by_id = {m.model_id: m for m in model_manager.active}
        if models_by_id:
            selected_id = st.selectbox(
                "Choose a model",
                options=list(models_by_id.keys()),
                format_func=lambda mid: f"{models_by_id[mid].display_name} [{mid}]",
                label_visibility="collapsed",
            )
            active_model = model_manager.find_one(selected_id)
            if active_model is None:
                st.error(f"Model not registered: {selected_id}")
                st.stop()
            st.caption(f"Provider: {active_model.provider}")
            st.caption(f"Context window: {active_model.token_limits.context_window:,} tokens")
        else:
            st.info("No API keys configured. The analyzer page will remain unavailable until one is added.")
            active_model = None

        if show_clear_results:
            st.divider()
            if st.button("🗑 Clear all results"):
                _clear_analysis_outputs()
                st.rerun()

    return active_model


def render_right_col() -> str:
    """Render the job-description paste area. Returns the current JD text."""
    if st.session_state.pop("clear_jd_and_analysis_pending", False):
        st.session_state["jd_input"] = ""
        _clear_analysis_outputs()

    jd_text: str = st.text_area(
        label="Paste the full job description here",
        placeholder="Copy the job post from LinkedIn and paste it here…",
        height=600,
        key="jd_input",
        label_visibility="collapsed",
    )
    word_count = len(jd_text.split()) if jd_text.strip() else 0
    st.caption(f"{word_count:,} words pasted" if word_count else "No job description pasted yet.")

    if st.button("🧹 Clear text and analysis", key="btn_clear_jd_and_analysis"):
        st.session_state["clear_jd_and_analysis_pending"] = True
        st.rerun()

    return jd_text


def _stream_into_placeholder(prompt: str, active_model: LLMModel, result_key: str) -> None:
    chunks: list[str] = []
    placeholder = st.empty()
    try:
        for chunk in active_model.stream_chat(prompt):
            chunks.append(chunk)
            placeholder.markdown("".join(chunks))
        st.session_state[result_key] = "".join(chunks)
    except Exception as exc:
        error_msg = f"Error: {exc}"
        placeholder.error(error_msg)
        st.session_state[result_key] = error_msg


def render_left_col(jd_text: str, active_model: LLMModel) -> None:
    """Render analysis tools and results panel."""

    if not jd_text.strip():
        st.info("Paste a job description on the right to enable the tools.")
        return

    for tool in TOOLS:
        result_key = f"result_{tool['id']}"
        source_key = f"{result_key}_source"
        expander_key = f"expander_{tool['id']}"
        with st.expander(
            tool["label"],
            expanded=bool(st.session_state.get(result_key)),
            key=expander_key,
            on_change="rerun",
        ):
            st.caption(tool["description"])
            is_open = bool(st.session_state.get(expander_key, False))
            source_text = st.session_state.get(source_key)
            should_run = is_open and source_text != jd_text
            ran_this_cycle = False
            if should_run:
                with st.spinner("Analysing…"):
                    _stream_into_placeholder(tool["prompt_fn"](jd_text), active_model, result_key)
                    st.session_state[source_key] = jd_text
                    ran_this_cycle = True
            if (not ran_this_cycle) and (cached := st.session_state.get(result_key)):
                st.markdown(cached)

    st.divider()
    st.markdown("**💬 Custom Question**")
    custom_question = st.text_area(
        "Ask anything about the job description",
        placeholder="e.g. What seniority level is this role targeting?",
        height=80,
        key="custom_question_input",
        label_visibility="collapsed",
    )
    if st.button("Ask", key="btn_custom"):
        if custom_question.strip():
            with st.spinner("Thinking…"):
                _stream_into_placeholder(
                    prompt_custom(jd_text, custom_question.strip()),
                    active_model,
                    "result_custom",
                )
        else:
            st.warning("Enter a question first.")
    if cached_custom := st.session_state.get("result_custom"):
        st.markdown(cached_custom)

    render_start_application_section(jd_text, active_model)
