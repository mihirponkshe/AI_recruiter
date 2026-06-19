# honeypot.py
"""
Honeypot detection — identifies fake/planted candidates with impossible profiles.

The dataset contains ~80 honeypots. They have mathematically impossible data:
date-math fraud, expert-with-zero-duration, career overflow beyond YoE, etc.

IMPORTANT: Only HARD IMPOSSIBLE indicators trigger honeypot elimination.
Soft signals (noisy data quality issues common across 100K candidates) are
returned separately for use as score penalties, NOT as honeypot flags.
"""
from datetime import date, datetime


def parse_date(d):
    if d is None:
        return None
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def is_honeypot(candidate):
    """
    Returns (is_honeypot: bool, flags: list[str]).

    Only mathematically impossible indicators count as honeypot flags.
    A candidate is eliminated if they have 1+ hard-impossible flags.
    """
    flags = []

    # ── 1. Duration mismatch: claimed months > actual date range ─────────
    #    This is mathematically impossible — dates don't lie.
    for job in candidate.get("career_history", []):
        start = parse_date(job.get("start_date"))
        end = parse_date(job.get("end_date")) or date.today()
        claimed_months = job.get("duration_months", 0)
        if start and end:
            actual_months = (end.year - start.year) * 12 + (end.month - start.month)
            if claimed_months > actual_months + 3:  # 3-month tolerance
                flags.append("duration_mismatch")

    # ── 2. Expert/advanced proficiency with 0 months duration ────────────
    #    Impossible to be expert with zero experience in the skill.
    skills = candidate.get("skills", [])
    for skill in skills:
        if skill.get("proficiency") in ["expert", "advanced"]:
            if skill.get("duration_months", 1) == 0:
                flags.append("expert_zero_duration")

    # ── 3. Unrealistic number of "expert" skills ─────────────────────────
    #    Nobody is legitimately "expert" in 8+ distinct technical skills.
    expert_count = sum(1 for s in skills if s.get("proficiency") == "expert")
    if expert_count > 8:
        flags.append("too_many_experts")

    # ── 4. Career timeline overflow ──────────────────────────────────────
    #    Total career months massively exceed claimed years of experience.
    #    E.g., claims 5 years but career history adds up to 15+ years.
    profile_yoe = candidate.get("profile", {}).get("years_of_experience", 0)
    total_career_months = sum(
        j.get("duration_months", 0) for j in candidate.get("career_history", [])
    )
    if profile_yoe > 0 and total_career_months > 0:
        career_years = total_career_months / 12
        if career_years > profile_yoe * 1.5 + 2:  # massive overclaim
            flags.append("career_overflow")

    # ── 5. Signup date in the future ─────────────────────────────────────
    signals = candidate.get("redrob_signals", {})
    signup = parse_date(signals.get("signup_date"))
    if signup and signup > date.today():
        flags.append("future_signup")

    # ── 6. Expert claims but fails own platform assessment badly ─────────
    #    Claims "expert" but scores <20/100 on the platform's own test.
    assessments = signals.get("skill_assessment_scores", {})
    for skill in skills:
        skill_name = skill.get("name", "")
        prof = skill.get("proficiency", "")
        if skill_name in assessments:
            score_val = assessments[skill_name]
            if prof == "expert" and score_val < 20:
                flags.append("expert_fails_assessment")
            elif prof == "advanced" and score_val < 10:
                flags.append("advanced_fails_assessment")

    # A single hard-impossible flag is enough to classify as honeypot
    return len(flags) >= 1, flags
