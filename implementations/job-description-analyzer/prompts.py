from __future__ import annotations

import re

_JD_PREAMBLE = (
    "Respond directly and concisely — do not start with phrases like 'Certainly!', "
    "'Great question', 'Sure!', 'Of course', 'Thank you', or any similar filler. "
    "When referring to the person reading this, use 'you' and 'your', not 'the candidate'.\n\n"
    "Here is a job description copied from LinkedIn:\n\n---\n{jd}\n---\n\n"
)

_RESUME_PREAMBLE = (
    "You have also uploaded your resume. "
    "Here are the most relevant excerpts from it for this analysis:\n\n"
    "---\n{resume_context}\n---\n\n"
    "Where appropriate, reference these resume excerpts to make the analysis "
    "specific and personally relevant — linking your actual experience, "
    "skills, or achievements to the job description.\n\n"
)


def _preamble(jd: str) -> str:
    return _JD_PREAMBLE.format(jd=jd)


def _resume_section(resume_context: str | None) -> str:
    if not resume_context:
        return ""
    return _RESUME_PREAMBLE.format(resume_context=resume_context)


def prompt_summary(jd: str, resume_context: str | None = None) -> str:
    return (
        _preamble(jd)
        + _resume_section(resume_context)
        + "Write a concise 3-5 sentence summary of this role: what the company does, "
        "what the role is responsible for, and the type of person they're looking for."
        + (
            " Where the resume excerpts are available, add one sentence on how well "
            "your background aligns with the role."
            if resume_context
            else ""
        )
    )


def prompt_requirements(jd: str, resume_context: str | None = None) -> str:
    recruiter_framing = (
        "You are writing a technical requirements accounting document addressed to the recruiter. "
        "Start with a short introductory paragraph (2–3 sentences) that summarises how your "
        "overall profile aligns with the role — speak in first person ('I', 'my'). "
        "Then produce exactly two sections:\n\n"
        "## Must-Have\n"
        "Bullet list of every explicitly required or mandatory requirement from the job description."
        + (
            " For each bullet, add a brief parenthetical noting your evidence "
            "(\u2705 met / \u26a0\ufe0f partial / \u274c not evident) based on the resume."
            if resume_context
            else ""
        )
        + "\n\n## Nice-to-Have\n"
        "Bullet list of every preferred, desirable, or 'a plus' requirement."
        + (
            " Same evidence notation as above."
            if resume_context
            else ""
        )
    )
    return (
        _preamble(jd)
        + _resume_section(resume_context)
        + recruiter_framing
    )


def prompt_tech_stack(jd: str, resume_context: str | None = None) -> str:
    return (
        _preamble(jd)
        + _resume_section(resume_context)
        + "List every technology, programming language, framework, platform, and tool "
        "mentioned in this job description. Group them by category (e.g. Languages, "
        "Frameworks, Cloud, Databases, DevOps, Other)."
        + (
            "\n\nFor each item, also note whether the resume excerpts confirm you "
            "have experience with it (\u2705 confirmed / \u274c not mentioned in resume)."
            if resume_context
            else ""
        )
    )


def prompt_red_flags(jd: str, resume_context: str | None = None) -> str:
    return (
        _preamble(jd)
        + _resume_section(resume_context)
        + "Analyze this job description from a candidate's perspective. "
        "Identify any potential red flags or concerns (e.g. vague responsibilities, "
        "excessive requirements, signs of poor culture, unusual expectations). "
        "Be honest and specific."
        + (
            "\n\nAlso note any red flags that are particularly relevant given "
            "your background shown in the resume excerpts."
            if resume_context
            else ""
        )
    )


def prompt_interview_prep(jd: str, resume_context: str | None = None) -> str:
    return (
        _preamble(jd)
        + _resume_section(resume_context)
        + "Generate 8-10 likely interview questions a hiring manager would ask for this role, "
        "based strictly on the job description. Include a mix of technical and behavioral questions. "
        "For each question, add a brief note on what the interviewer is probably trying to assess."
        + (
            "\n\nWhere the resume excerpts are available, tailor 3-4 of the questions "
            "to your specific background and suggest talking points from your "
            "experience that would make strong answers."
            if resume_context
            else ""
        )
    )


def _format_phone(raw: str) -> str:
    """Format a raw phone string to a human-readable number."""
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits[0] == "1":
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return raw  # unrecognised format — return as-is


def cover_letter_envelope(
    user_profile: dict[str, str] | None,
    title: str = "",
    company: str = "",
) -> tuple[str, str]:
    """Return (header, footer) composed entirely in Python from settings.

    The LLM never sees or writes these — we build them here so no placeholder
    leaks through regardless of model behaviour.
    """
    p = user_profile or {}
    name  = p.get("user.name")  or "[Your Name]"
    email = p.get("user.email") or "[Your Email]"
    raw_phone = p.get("user.phone") or ""
    phone = _format_phone(raw_phone) if raw_phone else ""

    re_position = title.strip() or "[Position]"
    re_company  = company.strip() or "[Company]"

    contact_lines = [name, email]
    if phone:
        contact_lines.append(phone)

    header = (
        "\n".join(f"*{line}*" for line in contact_lines)
        + f"\n\n*Re: {re_position} at {re_company}*\n\n"
    )
    footer = "\n\nSincerely,  \n" + name
    return header, footer


def prompt_cover_letter(
    jd: str,
    resume_context: str | None = None,
    user_profile: dict[str, str] | None = None,
) -> str:
    """Return a prompt that asks the LLM for the body paragraphs ONLY.

    The header and footer are composed separately by cover_letter_envelope()
    and stitched around the LLM output in ui.py — the model never writes them.
    """
    body_instruction = (
        "Write ONLY the body of a professional cover letter for this role — "
        "three focused paragraphs. "
        "Start directly with the salutation line (e.g. 'Dear Hiring Manager,'). "
        "Do NOT include any address block, date, sender details, or closing signature; "
        "those will be added separately."
    )

    if resume_context:
        return (
            _preamble(jd)
            + _resume_section(resume_context)
            + body_instruction
            + " Use the resume excerpts to make the letter specific — reference your "
            "actual job title, skills, and achievements."
        )
    return _preamble(jd) + body_instruction


def prompt_compensation(jd: str, resume_context: str | None = None) -> str:
    return (
        _preamble(jd)
        + _resume_section(resume_context)
        + "Extract and analyze compensation and benefits information from this job description. "
        "Include salary ranges, bonus/equity details, health insurance/health benefits, paid time off, "
        "vacation, retirement benefits, and any other perks if mentioned. "
        "Return these sections:\n"
        "1) **Found Details**: bullet list of concrete details from the posting.\n"
        "2) **Missing or Unclear**: what compensation/benefit details are not specified.\n"
        "3) **Candidate Questions**: 4-6 focused questions to ask the recruiter."
        + (
            "\n\nIf the resume excerpts suggest your seniority level or prior "
            "compensation context, factor that into the questions to ask."
            if resume_context
            else ""
        )
    )


def prompt_custom(jd: str, question: str, resume_context: str | None = None) -> str:
    return _preamble(jd) + _resume_section(resume_context) + question
