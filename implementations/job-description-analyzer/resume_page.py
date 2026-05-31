from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import streamlit as st

_DOCX_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def extract_resume_text(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    if not uploaded_file.name.lower().endswith(".docx"):
        return "Unsupported file type. Please upload a .docx Word resume."
    try:
        with zipfile.ZipFile(uploaded_file) as archive:
            xml = archive.read("word/document.xml")
        root = ET.fromstring(xml)
        paragraphs: list[str] = []
        for paragraph in root.findall(".//w:p", _DOCX_NS):
            parts = [node.text for node in paragraph.findall(".//w:t", _DOCX_NS) if node.text]
            text = "".join(parts).strip()
            if text:
                paragraphs.append(text)
        return "\n\n".join(paragraphs).strip()
    except Exception as exc:
        return f"Failed to read resume: {exc}"


def render_resume_page() -> None:
    st.subheader("Resume Viewer")
    uploaded = st.file_uploader("Upload a Word resume (.docx)", type=["docx"])
    resume_text = extract_resume_text(uploaded)

    if not uploaded:
        st.info("Upload a .docx resume to display its contents here.")
        return

    st.caption(f"File: {uploaded.name}")
    st.text_area("Extracted resume text", value=resume_text, height=600, label_visibility="collapsed")

    if resume_text.startswith("Failed to read resume") or resume_text.startswith("Unsupported file type"):
        st.warning(resume_text)
        return

    st.download_button(
        "Download extracted text",
        data=resume_text.encode("utf-8"),
        file_name=f"{Path(uploaded.name).stem}.txt",
        mime="text/plain",
    )
