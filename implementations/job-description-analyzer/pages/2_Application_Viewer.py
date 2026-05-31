"""Application Viewer page for browsing and updating saved applications."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

import streamlit as st

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from model_registry import build_model_manager  # noqa: E402
from ui import render_sidebar  # noqa: E402

_STATUS_ONGOING = "Ongoing"
_STATUS_COMPLETED = "Completed"
_STATUS_CLOSE = "Close"
_STATE_FILE = Path(__file__).resolve().parents[1] / ".job_app_state.json"


def _load_last_base_path() -> str:
    if not _STATE_FILE.exists():
        return str(Path.home())
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        value = str(data.get("last_base_path", "")).strip()
        return value or str(Path.home())
    except Exception:
        return str(Path.home())


def _to_win_path(wsl_path: str) -> str:
    try:
        result = subprocess.run(
            ["wslpath", "-w", wsl_path],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _to_wsl_path(win_path: str) -> str:
    try:
        result = subprocess.run(
            ["wslpath", "-u", win_path],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _nearest_existing_dir(path_str: str) -> str:
    candidate = Path(path_str).expanduser()
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    if candidate.exists() and candidate.is_dir():
        return str(candidate)
    return str(Path.home())


def _pick_folder(initial_dir: str) -> str | None:
    win_initial = _to_win_path(_nearest_existing_dir(initial_dir))
    set_path_line = f'$dialog.SelectedPath = "{win_initial}"' if win_initial else ""
    ps_script = f"""
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = 'Select application folder'
    {set_path_line}
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
        $dialog.SelectedPath
    }}
    """

    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", ps_script],
        capture_output=True,
        text=True,
        check=False,
    )
    selected = result.stdout.strip()
    if not selected:
        return None
    return _to_wsl_path(selected) or None


def _normalize_status(raw_value: Any) -> str:
    value = str(raw_value or "").strip().lower()
    if value in {"completed", "complete"}:
        return _STATUS_COMPLETED
    if value in {"close", "closed"}:
        return _STATUS_CLOSE
    return _STATUS_ONGOING


def _status_options(current_status: str) -> list[str]:
    if current_status == _STATUS_ONGOING:
        return [_STATUS_ONGOING, _STATUS_COMPLETED]
    if current_status == _STATUS_COMPLETED:
        return [_STATUS_COMPLETED, _STATUS_CLOSE]
    return [_STATUS_CLOSE]


def _read_application_details(details_path: Path) -> dict[str, Any]:
    if not details_path.exists():
        return {"status": _STATUS_ONGOING}
    try:
        data = json.loads(details_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        return {"status": _STATUS_ONGOING}
    except Exception:
        return {"status": _STATUS_ONGOING}


def _write_application_details(details_path: Path, data: dict[str, Any]) -> None:
    details_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _parse_iso_date(raw_value: Any) -> date | None:
    if not raw_value:
        return None
    try:
        return date.fromisoformat(str(raw_value))
    except ValueError:
        return None


def _rename_folder_with_status(folder: Path, new_status: str) -> Path:
    suffix = ""
    match = re.search(r" \(\d+\)$", folder.name)
    if match:
        suffix = match.group(0)
    core_name = folder.name[: -len(suffix)] if suffix else folder.name

    parts = core_name.rsplit(" - ", 3)
    if len(parts) != 4:
        return folder

    title, company, _old_status, posted_on = parts
    base_name = f"{title} - {company} - {new_status} - {posted_on}"
    candidate = folder.with_name(base_name)

    if candidate == folder:
        return folder

    if candidate.exists():
        for i in range(2, 1000):
            option = folder.with_name(f"{base_name} ({i})")
            if not option.exists():
                candidate = option
                break

    folder.rename(candidate)
    return candidate


def _file_rows(folder: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for child in sorted(folder.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        stat = child.stat()
        rows.append(
            {
                "name": child.name,
                "type": "file" if child.is_file() else "folder",
                "size_bytes": stat.st_size if child.is_file() else "",
                "modified": stat.st_mtime,
            }
        )
    return rows


def _render_application_viewer() -> None:
    st.title("Application Viewer")
    st.caption("Open an application folder, inspect files, and update application status.")

    default_browse_dir = _load_last_base_path()

    if msg := st.session_state.pop("application_status_update_message", None):
        st.success(msg)

    if "application_folder_pending" in st.session_state:
        st.session_state["application_folder_input"] = st.session_state.pop("application_folder_pending")

    col_path, col_browse = st.columns([5, 1])
    with col_path:
        folder_input = st.text_input(
            "Application folder",
            key="application_folder_input",
            placeholder="Paste or browse to an existing application folder",
        )
    with col_browse:
        st.write("&nbsp;", unsafe_allow_html=True)
        if st.button("Browse…", key="btn_browse_application_folder"):
            selected = _pick_folder(folder_input or default_browse_dir)
            if selected:
                st.session_state["application_folder_pending"] = selected
                st.rerun()

    if not folder_input.strip():
        st.info("Choose an application folder to continue.")
        return

    folder = Path(folder_input).expanduser().resolve()
    if not folder.exists() or not folder.is_dir():
        st.error("The selected path is not a valid folder.")
        return

    st.success(f"Opened: {folder}")

    st.subheader("Files in folder")
    rows = _file_rows(folder)
    if rows:
        st.dataframe(rows, hide_index=True, use_container_width=True)
    else:
        st.caption("Folder is empty.")

    likely_docs = [
        item["name"]
        for item in rows
        if any(token in item["name"].lower() for token in ["resume", "cv", "cover", "application", "description"])
    ]
    if likely_docs:
        st.caption("Relevant documents: " + ", ".join(likely_docs))

    st.divider()
    st.subheader("Application status")

    details_path = folder / "application_details.json"
    details = _read_application_details(details_path)
    current_status = _normalize_status(details.get("status"))
    options = _status_options(current_status)

    selected_status = st.selectbox(
        "Set status",
        options=options,
        index=options.index(current_status) if current_status in options else 0,
        key="application_status_editor",
    )

    capture_completion = current_status == _STATUS_ONGOING and selected_status == _STATUS_COMPLETED
    submitted = True
    submitted_on = date.today()
    if capture_completion:
        completion = details.get("completion") if isinstance(details.get("completion"), dict) else {}
        default_submitted = str(completion.get("outcome", "submitted")).strip().lower() != "abandoned"
        parsed_submitted_on = _parse_iso_date(completion.get("submitted_on"))
        submitted = st.toggle("Application submitted", value=default_submitted, key="application_submitted_toggle")
        if submitted:
            submitted_on = st.date_input(
                "Submission date",
                value=parsed_submitted_on or date.today(),
                key="application_submitted_on_input",
            )

    if st.button("Update status", type="primary"):
        details["status"] = selected_status

        if capture_completion:
            details["completion"] = {
                "outcome": "submitted" if submitted else "abandoned",
                "submitted_on": submitted_on.isoformat() if submitted else None,
            }

        _write_application_details(details_path, details)

        renamed_folder = folder
        if current_status != selected_status:
            renamed_folder = _rename_folder_with_status(folder, selected_status)

        st.session_state["application_folder_pending"] = str(renamed_folder)
        st.session_state["application_status_update_message"] = f"Status updated to {selected_status}."
        st.rerun()

    st.caption(f"Metadata file: {details_path}")
    with st.expander("View metadata JSON", expanded=False):
        st.json(details)


try:
    model_manager = build_model_manager(allow_empty=True)
except Exception as exc:
    st.error(f"Configuration error: {exc}")
    st.stop()

render_sidebar(model_manager, show_clear_results=False)
_render_application_viewer()
