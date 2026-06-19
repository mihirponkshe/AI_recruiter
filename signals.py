# signals.py
"""
Behavioral signal processing and location scoring.

behavioral_score() returns a 0.4–1.5 MULTIPLIER applied on top of the
base composite score. It captures availability, engagement, and trust.

location_score() returns 0.0–1.0 based on location fit and relocation.
"""
from datetime import date, datetime


def parse_date(d):
    if d is None:
        return None
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def behavioral_score(candidate):
    """
    Returns a float 0.4–1.5 representing candidate availability + engagement.
    This is used as a MULTIPLIER on top of the skill/career score.
    """
    s = candidate.get("redrob_signals", {})
    today = date.today()
    score = 1.0

    # 1. Recency (last active) — most important behavioral signal
    last_active = parse_date(s.get("last_active_date"))
    if last_active:
        days_ago = (today - last_active).days
        if days_ago > 180:
            score *= 0.4    # very stale — probably not looking
        elif days_ago > 90:
            score *= 0.65
        elif days_ago > 30:
            score *= 0.85
        # else: active recently, no penalty

    # 2. Open to work
    if s.get("open_to_work_flag") is True:
        score *= 1.15   # boost availability signal
    elif s.get("open_to_work_flag") is False:
        score *= 0.80

    # 3. Recruiter response rate
    rrr = s.get("recruiter_response_rate", 0.5)
    if rrr < 0.2:
        score *= 0.6
    elif rrr < 0.4:
        score *= 0.8
    elif rrr > 0.7:
        score *= 1.1

    # 4. Notice period
    notice = s.get("notice_period_days", 60)
    if notice <= 30:
        score *= 1.1    # JD says "sub-30 preferred"
    elif notice <= 60:
        score *= 0.95
    elif notice <= 90:
        score *= 0.85
    else:
        score *= 0.70   # 90+ days is a real friction

    # 5. Interview completion rate (reliability signal)
    icr = s.get("interview_completion_rate", 0.5)
    if icr < 0.3:
        score *= 0.75
    elif icr > 0.8:
        score *= 1.05

    # 6. Verification (trust)
    verified_email = s.get("verified_email", False)
    verified_phone = s.get("verified_phone", False)
    linkedin = s.get("linkedin_connected", False)
    if not verified_email and not verified_phone:
        score *= 0.85
    if linkedin:
        score *= 1.03   # slight trust bonus

    # 7. GitHub activity (meaningful for this technical role)
    gh = s.get("github_activity_score", -1)
    if gh > 60:
        score *= 1.12
    elif gh > 30:
        score *= 1.05
    elif gh == -1:
        score *= 0.95   # slight penalty for no GitHub linked

    # 8. Profile completeness (platform engagement signal)
    pcs = s.get("profile_completeness_score", 50)
    if pcs >= 90:
        score *= 1.05
    elif pcs < 50:
        score *= 0.90

    # 9. Saved by recruiters (market validation)
    saved = s.get("saved_by_recruiters_30d", 0)
    if saved >= 10:
        score *= 1.08
    elif saved >= 5:
        score *= 1.04

    # 10. Offer acceptance rate (reliability)
    oar = s.get("offer_acceptance_rate", -1)
    if oar >= 0:  # -1 means no history
        if oar < 0.3:
            score *= 0.85   # frequently declines offers
        elif oar > 0.7:
            score *= 1.05

    # 11. Average response time (responsiveness)
    avg_resp = s.get("avg_response_time_hours", 48)
    if avg_resp <= 12:
        score *= 1.05   # very responsive
    elif avg_resp > 120:
        score *= 0.90   # slow responder

    # Cap the multiplier to prevent extreme values
    return max(min(score, 1.5), 0.4)


def location_score(candidate, jd_config):
    """Scores 0.0–1.0 based on location match and relocation willingness."""
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    loc = (profile.get("location") or "").lower()
    country = (profile.get("country") or "").lower()
    willing = signals.get("willing_to_relocate", False)

    top_locs = jd_config["top_locations"]

    if any(t in loc for t in top_locs):
        return 1.0   # already in the right city
    if country == "india" and willing:
        return 0.75  # in India, willing to relocate
    if country == "india" and not willing:
        return 0.45  # in India but won't relocate
    # Outside India — JD says case-by-case, but no visa sponsorship
    if willing:
        return 0.30
    return 0.10
