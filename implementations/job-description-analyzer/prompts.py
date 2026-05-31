from __future__ import annotations

_JD_PREAMBLE = "Here is a job description copied from LinkedIn:\n\n---\n{jd}\n---\n\n"


def _preamble(jd: str) -> str:
    return _JD_PREAMBLE.format(jd=jd)


def prompt_summary(jd: str) -> str:
    return (
        _preamble(jd)
        + "Write a concise 3-5 sentence summary of this role: what the company does, "
        "what the role is responsible for, and the type of candidate they're looking for."
    )


def prompt_requirements(jd: str) -> str:
    return (
        _preamble(jd)
        + "Extract and categorize all requirements from this job description. "
        "Present two separate bullet lists:\n"
        "**Must-have** — explicitly required or listed as mandatory.\n"
        "**Nice-to-have** — preferred, a plus, or desirable."
    )


def prompt_tech_stack(jd: str) -> str:
    return (
        _preamble(jd)
        + "List every technology, programming language, framework, platform, and tool "
        "mentioned in this job description. Group them by category (e.g. Languages, "
        "Frameworks, Cloud, Databases, DevOps, Other)."
    )


def prompt_red_flags(jd: str) -> str:
    return (
        _preamble(jd)
        + "Analyze this job description from a candidate's perspective. "
        "Identify any potential red flags or concerns (e.g. vague responsibilities, "
        "excessive requirements, signs of poor culture, unusual expectations). "
        "Be honest and specific."
    )


def prompt_interview_prep(jd: str) -> str:
    return (
        _preamble(jd)
        + "Generate 8-10 likely interview questions a hiring manager would ask for this role, "
        "based strictly on the job description. Include a mix of technical and behavioral questions. "
        "For each question, add a brief note on what the interviewer is probably trying to assess."
    )


def prompt_cover_letter(jd: str) -> str:
    return (
        _preamble(jd)
        + "Draft a compelling, professional cover letter for this role. "
        "Keep it to three paragraphs. Leave placeholder tags like [YOUR NAME], "
        "[YOUR EXPERIENCE], and [RELEVANT ACHIEVEMENT] where the candidate should "
        "personalise the text."
    )


def prompt_compensation(jd: str) -> str:
    return (
        _preamble(jd)
        + "Extract and analyze compensation and benefits information from this job description. "
        "Include salary ranges, bonus/equity details, health insurance/health benefits, paid time off, "
        "vacation, retirement benefits, and any other perks if mentioned. "
        "Return these sections:\n"
        "1) **Found Details**: bullet list of concrete details from the posting.\n"
        "2) **Missing or Unclear**: what compensation/benefit details are not specified.\n"
        "3) **Candidate Questions**: 4-6 focused questions to ask the recruiter."
    )


def prompt_custom(jd: str, question: str) -> str:
    return _preamble(jd) + question
