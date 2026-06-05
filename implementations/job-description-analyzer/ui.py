from __future__ import annotations

import re
import sys
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.python.LLM.models import LLMModel  # noqa: E402
from src.python.LLM.LLM_Manager import LLMManager  # noqa: E402
from application_start import render_start_application_section  # noqa: E402
from prompts import prompt_custom, cover_letter_envelope  # noqa: E402
from resume_rag import query_resume, resume_fingerprint  # noqa: E402
from settings_db import load_user_profile  # noqa: E402
from tools import TOOLS  # noqa: E402


def _get_jd_meta_for_cl(jd_text: str, active_model) -> tuple[str, str]:
    """Return (title, company) for the cover letter Re: line.

    Prefers application_draft if already populated; otherwise asks the model
    with a single cheap call and caches the result per JD.
    """
    draft = st.session_state.get("application_draft") or {}
    title = draft.get("title", "").strip()
    company = draft.get("company", "").strip()
    if title and company:
        return title, company

    cached = st.session_state.get("_cl_meta_cache") or {}
    if cached.get("jd_prefix") == jd_text[:120]:
        return cached.get("title", ""), cached.get("company", "")

    if active_model is None:
        return "", ""

    prompt = (
        "From the job description below, extract exactly:\n"
        "Job title: <title>\n"
        "Company: <company name>\n\n"
        "Return only those two lines and nothing else.\n\n"
        + jd_text[:3000]
    )
    try:
        response = "".join(active_model.stream_chat(prompt))
        title_m = re.search(r"Job title:\s*(.+)", response, re.IGNORECASE)
        company_m = re.search(r"Company:\s*(.+)", response, re.IGNORECASE)
        title = title_m.group(1).strip().strip('*_"\'') if title_m else ""
        company = company_m.group(1).strip().strip('*_"\'') if company_m else ""
    except Exception:
        title = company = ""

    st.session_state["_cl_meta_cache"] = {
        "jd_prefix": jd_text[:120],
        "title": title,
        "company": company,
    }
    return title, company


def _clear_tool_cache(tool_id: str) -> None:
    result_key = f"result_{tool_id}"
    for suffix in ("", "_source", "_resume_fp", "_profile_fp", "_used_resume"):
        st.session_state.pop(f"{result_key}{suffix}", None)
    # Force next render to re-run regardless of fingerprint state
    st.session_state[f"force_rerun_{tool_id}"] = True


def _clear_analysis_outputs() -> None:
    for tool in TOOLS:
        _clear_tool_cache(tool["id"])
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


_JD_PERSIST_KEY = "_jd_text_persist"  # non-widget key — survives page navigation


def render_right_col() -> str:
    """Render the job-description paste area. Returns the current JD text."""
    if st.session_state.pop("clear_jd_and_analysis_pending", False):
        st.session_state["jd_input"] = ""
        st.session_state.pop(_JD_PERSIST_KEY, None)
        _clear_analysis_outputs()

    # Streamlit clears widget keys for widgets not rendered in the previous run
    # (i.e. when the user was on another page).  Restore from our persistent copy.
    if not st.session_state.get("jd_input") and st.session_state.get(_JD_PERSIST_KEY):
        st.session_state["jd_input"] = st.session_state[_JD_PERSIST_KEY]

    jd_text: str = st.text_area(
        label="Paste the full job description here",
        placeholder="Copy the job post from LinkedIn and paste it here…",
        height=600,
        key="jd_input",
        label_visibility="collapsed",
    )

    # Keep the persistent copy in sync
    if jd_text:
        st.session_state[_JD_PERSIST_KEY] = jd_text

    word_count = len(jd_text.split()) if jd_text.strip() else 0
    st.caption(f"{word_count:,} words pasted" if word_count else "No job description pasted yet.")

    if st.button("🧹 Clear text and analysis", key="btn_clear_jd_and_analysis"):
        st.session_state["clear_jd_and_analysis_pending"] = True
        st.rerun()

    return jd_text


_CLOSING_RE = re.compile(
    r"\n+\s*(sincerely|best regards?|kind regards?|yours (sincerely|truly|faithfully)|regards)[,\s].*",
    re.IGNORECASE | re.DOTALL,
)


def _strip_llm_closing(text: str) -> str:
    """Remove any closing signature the LLM generated so we can substitute our own."""
    return _CLOSING_RE.sub("", text).rstrip()


def _stream_into_placeholder(
    prompt: str,
    active_model: LLMModel,
    result_key: str,
    *,
    prefix: str = "",
    suffix: str = "",
) -> None:
    chunks: list[str] = []
    placeholder = st.empty()
    try:
        for chunk in active_model.stream_chat(prompt):
            chunks.append(chunk)
            placeholder.markdown(prefix + "".join(chunks))
        body = _strip_llm_closing("".join(chunks)) if suffix else "".join(chunks)
        final = prefix + body + suffix
        placeholder.markdown(final)
        st.session_state[result_key] = final
    except Exception as exc:
        error_msg = f"Error: {exc}"
        placeholder.error(error_msg)
        st.session_state[result_key] = error_msg


def render_left_col(jd_text: str, active_model: LLMModel) -> None:
    """Render analysis tools and results panel."""

    if not jd_text.strip():
        st.info("Paste a job description on the right to enable the tools.")
        return

    current_fp = resume_fingerprint()
    user_profile = load_user_profile()
    profile_fp = "|".join(f"{k}={v}" for k, v in sorted(user_profile.items()))

    for tool in TOOLS:
        result_key = f"result_{tool['id']}"
        source_key = f"{result_key}_source"
        fp_key = f"{result_key}_resume_fp"
        expander_key = f"expander_{tool['id']}"
        with st.expander(
            tool["label"],
            expanded=bool(st.session_state.get(result_key) or st.session_state.get(f"force_rerun_{tool['id']}")),
            key=expander_key,
            on_change="rerun",
        ):
            st.caption(tool["description"])
            is_open = bool(st.session_state.get(expander_key, False))
            source_text = st.session_state.get(source_key)
            saved_fp = st.session_state.get(fp_key)
            profile_fp_key = f"{result_key}_profile_fp"
            saved_profile_fp = st.session_state.get(profile_fp_key)
            force = st.session_state.pop(f"force_rerun_{tool['id']}", False)
            # Re-run if forced, JD changed, resume index changed, or (for cover letter) profile changed
            should_run = (is_open or force) and (
                force
                or source_text != jd_text
                or saved_fp != current_fp
                or (tool["id"] == "cover_letter" and saved_profile_fp != profile_fp)
            )
            ran_this_cycle = False
            if should_run:
                with st.spinner("Analysing…"):
                    resume_context, rag_error = query_resume(jd_text)
                    if rag_error:
                        st.warning(f"⚠️ {rag_error}")
                    extra = {"user_profile": user_profile} if tool["id"] == "cover_letter" else {}
                    if tool["id"] == "cover_letter":
                        _cl_title, _cl_company = _get_jd_meta_for_cl(jd_text, active_model)
                        cl_header, cl_footer = cover_letter_envelope(
                            user_profile,
                            title=_cl_title,
                            company=_cl_company,
                        )
                    else:
                        cl_header = cl_footer = ""
                    _stream_into_placeholder(
                        tool["prompt_fn"](jd_text, resume_context, **extra),
                        active_model,
                        result_key,
                        prefix=cl_header,
                        suffix=cl_footer,
                    )
                    st.session_state[source_key] = jd_text
                    st.session_state[fp_key] = current_fp
                    if tool["id"] == "cover_letter":
                        st.session_state[profile_fp_key] = profile_fp
                    st.session_state[f"{result_key}_used_resume"] = resume_context is not None
                    ran_this_cycle = True
            if (not ran_this_cycle) and (cached := st.session_state.get(result_key)):
                st.markdown(cached)
            col_meta, col_regen = st.columns([3, 1])
            with col_meta:
                if st.session_state.get(f"{result_key}_used_resume"):
                    st.caption("📄 Resume context included")
            with col_regen:
                if st.session_state.get(result_key) and st.button(
                    "↺ Regenerate", key=f"regen_{tool['id']}", use_container_width=True
                ):
                    _clear_tool_cache(tool["id"])
                    st.rerun()

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
                resume_context, rag_error = query_resume(custom_question.strip())
                if rag_error:
                    st.warning(f"⚠️ {rag_error}")
                _stream_into_placeholder(
                    prompt_custom(jd_text, custom_question.strip(), resume_context),
                    active_model,
                    "result_custom",
                )
                if resume_context:
                    st.caption("📄 Resume context included")
            st.session_state["_custom_just_ran"] = True
        else:
            st.warning("Enter a question first.")
    if not st.session_state.pop("_custom_just_ran", False):
        if cached_custom := st.session_state.get("result_custom"):
            st.markdown(cached_custom)

    render_start_application_section(jd_text, active_model)
