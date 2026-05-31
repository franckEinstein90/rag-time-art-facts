from __future__ import annotations

from prompts import (
    prompt_compensation,
    prompt_cover_letter,
    prompt_interview_prep,
    prompt_red_flags,
    prompt_requirements,
    prompt_summary,
    prompt_tech_stack,
)

TOOLS: list[dict] = [
    {
        "id": "summary",
        "label": "📋 Role Summary",
        "description": "Concise overview of the role and company.",
        "prompt_fn": prompt_summary,
    },
    {
        "id": "requirements",
        "label": "✅ Requirements",
        "description": "Must-have vs nice-to-have requirements.",
        "prompt_fn": prompt_requirements,
    },
    {
        "id": "tech_stack",
        "label": "🛠 Tech Stack",
        "description": "All technologies grouped by category.",
        "prompt_fn": prompt_tech_stack,
    },
    {
        "id": "red_flags",
        "label": "🚩 Red Flags",
        "description": "Potential concerns from a candidate's perspective.",
        "prompt_fn": prompt_red_flags,
    },
    {
        "id": "interview_prep",
        "label": "🎤 Interview Prep",
        "description": "Likely interview questions with assessment notes.",
        "prompt_fn": prompt_interview_prep,
    },
    {
        "id": "cover_letter",
        "label": "✉️ Cover Letter Draft",
        "description": "A draft cover letter with placeholder tags.",
        "prompt_fn": prompt_cover_letter,
    },
    {
        "id": "compensation",
        "label": "💰 Compensation & Benefits",
        "description": "Salary, benefits, PTO, and other compensation details.",
        "prompt_fn": prompt_compensation,
    },
]
