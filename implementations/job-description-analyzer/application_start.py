from __future__ import annotations

import json
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import streamlit as st

_STATE_FILE = Path(__file__).resolve().parent / ".job_app_state.json"


def _to_win_path(wsl_path: str) -> str:
    try:
        return subprocess.run(
            ["wslpath", "-w", wsl_path], capture_output=True, text=True
        ).stdout.strip()
    except Exception:
        return ""


def _to_wsl_path(win_path: str) -> str:
    try:
        return subprocess.run(
            ["wslpath", "-u", win_path], capture_output=True, text=True
        ).stdout.strip()
    except Exception:
        return ""


def _pick_folder(initial_dir: str) -> str | None:
    win_initial = _to_win_path(initial_dir)
    set_path_line = f'$dialog.SelectedPath = "{win_initial}"' if win_initial else ""
    ps_script = f"""
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = 'Select storage location'
    $dialog.RootFolder = 'MyComputer'
    {set_path_line}
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
        $dialog.SelectedPath
    }}
    """
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", ps_script],
        capture_output=True,
        text=True,
    )
    win_path = result.stdout.strip()
    if not win_path:
        return None
    return _to_wsl_path(win_path) or None


_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def _load_last_base_path() -> str:
    if not _STATE_FILE.exists():
        return str(Path.home())
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        value = str(data.get("last_base_path", "")).strip()
        return value or str(Path.home())
    except Exception:
        return str(Path.home())


def _save_last_base_path(base_path: str) -> None:
    payload = {"last_base_path": base_path}
    _STATE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sanitize_windows_name(value: str, fallback: str) -> str:
    cleaned = _INVALID_CHARS.sub(" ", value).strip().rstrip(". ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        cleaned = fallback
    if cleaned.upper() in _RESERVED_NAMES:
        cleaned = f"{cleaned}_job"
    return cleaned


def _build_folder_name(title: str, company: str, status: str, posted_on: date) -> str:
    safe_title = _sanitize_windows_name(title, "Unknown Title")
    safe_company = _sanitize_windows_name(company, "Unknown Company")
    safe_status = _sanitize_windows_name(status, "Ongoing")
    safe_date = posted_on.isoformat()
    return f"{safe_title} - {safe_company} - {safe_status} - {safe_date}"


def _save_application_files(
    folder: Path,
    jd_text: str,
    source_url: str | None,
    title: str,
    company: str,
    posted_on: date,
    status: str,
) -> None:
    (folder / "original_description.txt").write_text(jd_text, encoding="utf-8")
    payload = {
        "title": title,
        "company": company,
        "posted_on": posted_on.isoformat(),
        "status": status,
        "source_url": source_url,
        "description_file": "original_description.txt",
    }
    (folder / "application_details.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def _create_unique_folder(base_path: Path, folder_name: str) -> Path:
    target = base_path / folder_name
    if not target.exists():
        target.mkdir(parents=True, exist_ok=False)
        return target
    for i in range(2, 1000):
        candidate = base_path / f"{folder_name} ({i})"
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
    raise RuntimeError("Could not create a unique application folder.")


def _default_draft() -> dict[str, Any]:
    return {
        "title": "",
        "company": "",
        "posted_on": date.today(),
        "status": "Ongoing",
        "base_path": _load_last_base_path(),
    }


def _extract_sentence_value(response: str, label: str) -> str | None:
    pattern = rf"{re.escape(label)}\s*(?:is|:)\s*(.+)"
    match = re.search(pattern, response, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    value = match.group(1).strip().strip('"').strip("'")
    value = re.sub(r"[\s\.]$", "", value)
    return value or None


def _extract_date_value(response: str) -> date | None:
    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", response)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def _extract_source_url(source_text: str) -> str | None:
    match = re.search(r"https?://\S+", source_text)
    if not match:
        return None
    return match.group(0).rstrip(".,) ]}\"'")


def _ask_llm_for_field(active_model: Any, jd_text: str, field_label: str, instruction: str) -> str:
    prompt = (
        f"{instruction}\n\n"
        "Return exactly one sentence and nothing else.\n"
        f"{field_label} application text:\n{jd_text}"
    )
    return "".join(active_model.stream_chat(prompt))


def _extract_application_metadata(jd_text: str, active_model: Any | None) -> tuple[dict[str, Any] | None, str | None]:
    if active_model is None:
        return None, "No active model is available for metadata extraction."
    if not jd_text.strip():
        return None, "Paste the application text first."

    try:
        title_response = _ask_llm_for_field(
            active_model,
            jd_text,
            "Job title",
            "Identify the exact job title from the application text. Answer in the form: The job title for this application is <title>.",
        )
        company_response = _ask_llm_for_field(
            active_model,
            jd_text,
            "Company",
            "Identify the exact company name from the application text. Answer in the form: The company for this application is <company>.",
        )
        posted_on_response = _ask_llm_for_field(
            active_model,
            jd_text,
            "Posting date",
            "Identify the posting date from the application text. Answer in the form: The posting date for this application is YYYY-MM-DD.",
        )
    except Exception as exc:
        return None, f"Metadata extraction failed: {exc}"

    title = _extract_sentence_value(title_response, "The job title for this application")
    company = _extract_sentence_value(company_response, "The company for this application")
    posted_on = _extract_date_value(posted_on_response)

    if not title:
        return None, "Metadata extraction failed: the model did not return a parsable job title."
    if not company:
        return None, "Metadata extraction failed: the model did not return a parsable company name."
    if posted_on is None:
        return None, "Metadata extraction failed: the model did not return a parsable posting date in YYYY-MM-DD format."

    return (
        {
            "title": title,
            "company": company,
            "posted_on": posted_on,
            "status": "Ongoing",
            "base_path": _load_last_base_path(),
        },
        None,
    )


def _open_application_dialog(jd_text: str, active_model: Any | None) -> None:
    draft, error = _extract_application_metadata(jd_text, active_model)
    if error is not None or draft is None:
        st.error(error or "Metadata extraction failed.")
        return
    st.session_state["application_draft"] = draft
    st.session_state["application_source_text"] = jd_text
    st.session_state["application_dialog_open"] = True
    st.session_state["application_title_input"] = draft["title"]
    st.session_state["application_company_input"] = draft["company"]
    st.session_state["application_posted_on_input"] = draft["posted_on"]
    st.session_state["application_status_input"] = draft["status"]
    st.session_state["application_base_path_input"] = draft["base_path"]
    st.rerun()


def _close_application_dialog() -> None:
    st.session_state.pop("application_dialog_open", None)


@st.dialog("Start application", width="large", icon="🚀", on_dismiss=_close_application_dialog)
def _render_application_dialog() -> None:
    draft = st.session_state.get("application_draft", _default_draft())
    st.write("Review the extracted metadata and adjust it before creating the folder.")

    title = st.text_input("Job title", key="application_title_input")
    company = st.text_input("Company", key="application_company_input")
    posted_on = st.date_input("Posting date", key="application_posted_on_input")
    status = st.selectbox(
        "Application status",
        ["Ongoing", "Completed", "Close"],
        key="application_status_input",
    )

    # Transfer any Browse selection into the widget key before it renders
    if "application_base_path_pending" in st.session_state:
        st.session_state["application_base_path_input"] = st.session_state.pop("application_base_path_pending")

    col_path, col_browse = st.columns([5, 1])
    with col_path:
        base_path = st.text_input("Storage location", key="application_base_path_input")
    with col_browse:
        st.write("&nbsp;", unsafe_allow_html=True)  # align button with input
        if st.button("Browse…", key="btn_browse_storage_path"):
            selected = _pick_folder(base_path or str(Path.home()))
            if selected:
                st.session_state["application_base_path_pending"] = selected
                st.rerun()

    st.caption(
        f"Preview: {_build_folder_name(title or draft['title'], company or draft['company'], status, posted_on)}"
    )

    create_clicked = st.button("Create folder", type="primary")
    cancel_clicked = st.button("Cancel")

    if cancel_clicked:
        _close_application_dialog()
        st.rerun()

    if create_clicked:
        if not (title.strip() and company.strip()):
            st.warning("Enter both Job title and Company.")
            return
        try:
            source_text = str(st.session_state.get("application_source_text", ""))
            source_url = _extract_source_url(source_text)
            base = Path(base_path).expanduser().resolve()
            base.mkdir(parents=True, exist_ok=True)
            folder_name = _build_folder_name(title, company, status, posted_on)
            created = _create_unique_folder(base, folder_name)
            _save_application_files(created, source_text, source_url, title, company, posted_on, status)
            _save_last_base_path(str(base))
            st.session_state["created_application_path"] = str(created)
            _close_application_dialog()
            st.success(f"Created: {created}")
            st.rerun()
        except Exception as exc:
            st.error(f"Failed to create folder: {exc}")


def render_start_application_section(jd_text: str, active_model: Any | None) -> None:
    st.divider()
    st.markdown("**🚀 Start Application**")

    start_disabled = not jd_text.strip()

    if st.button("Start application", key="btn_start_application", disabled=start_disabled):
        if start_disabled:
            st.warning("Paste the application text first.")
            return
        with st.spinner("Extracting application metadata..."):
            _open_application_dialog(jd_text, active_model)

    if start_disabled:
        st.caption("Paste the application text on the right to extract metadata automatically.")

    if created := st.session_state.get("created_application_path"):
        st.caption(f"Latest application folder: {created}")

    if st.session_state.get("application_dialog_open"):
        _render_application_dialog()
