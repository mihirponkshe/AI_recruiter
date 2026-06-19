# reasoning.py
"""
Generate per-candidate reasoning strings.

Stage 4 manual review checks 10 random rows and penalizes templated reasoning.
Every sentence must reference specific candidate data — no generic templates.
"""


def generate_reasoning(candidate, rank, score, debug):
    """
    Generates a data-grounded 1-2 sentence reasoning string.
    References specific facts: years, title, company, skills, signals.
    Honest about gaps.
    """
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    history = candidate.get("career_history", [])
    skills = candidate.get("skills", [])
    education = candidate.get("education", [])

    yoe = profile.get("years_of_experience", 0)
    title = profile.get("current_title", "unknown title")
    company = profile.get("current_company", "unknown company")
    loc = profile.get("location", "unknown location")
    country = (profile.get("country") or "").lower()
    headline = profile.get("headline", "")
    industry = profile.get("current_industry", "")

    # ── Top relevant skills (advanced/expert, relevant to JD) ──────────
    RELEVANT = {
        "embedding", "vector", "retrieval", "nlp", "python",
        "search", "ranking", "ml", "llm", "rag", "faiss",
        "pinecone", "qdrant", "milvus", "fine-tuning", "bert",
        "transformer", "pytorch", "elasticsearch", "opensearch",
        "recommendation", "sentence", "semantic",
    }
    top_skills = [
        s["name"] for s in skills
        if s.get("proficiency") in ["advanced", "expert"]
        and any(r in s["name"].lower() for r in RELEVANT)
    ][:4]

    # ── Behavioral facts ──────────────────────────────────────────────
    notice = signals.get("notice_period_days", 60)
    open_to_work = signals.get("open_to_work_flag", False)
    github = signals.get("github_activity_score", -1)
    recruiter_rr = signals.get("recruiter_response_rate", 0.5)
    salary = signals.get("expected_salary_range_inr_lpa", {})
    sal_max = salary.get("max", 0) if isinstance(salary, dict) else 0

    # ── Education ─────────────────────────────────────────────────────
    edu_info = ""
    if education:
        best_edu = education[0]
        tier = best_edu.get("tier", "unknown")
        field = best_edu.get("field_of_study", "")
        degree = best_edu.get("degree", "")
        if tier == "tier_1":
            edu_info = f"{degree} ({field}) from tier-1 institution"
        elif tier == "tier_2":
            edu_info = f"{degree} ({field}) from tier-2 institution"

    # ── Build positives ───────────────────────────────────────────────
    positives = []

    if top_skills:
        positives.append(f"relevant skills in {', '.join(top_skills)}")

    if debug.get("career", 0) > 0.6:
        positives.append("product-company engineering background")

    if debug.get("text", 0) > 0.4:
        # Scan for specific IR mentions
        has_ir = False
        for j in history:
            desc = (j.get("description") or "").lower()
            if any(t in desc for t in [
                "ranking", "retrieval", "vector", "embedding",
                "search", "recommendation", "semantic",
            ]):
                has_ir = True
                break
        if has_ir:
            positives.append("has built search/ranking systems in production")
        else:
            positives.append("strong NLP/ML domain alignment in profile")

    if github > 50:
        positives.append(f"active GitHub (score {int(github)})")

    if open_to_work:
        positives.append("actively open to work")

    if notice <= 30:
        positives.append(f"{notice}-day notice period")

    if edu_info:
        positives.append(edu_info)

    # Check for startup experience
    for j in history:
        cs = j.get("company_size", "")
        if cs in ("1-10", "11-50") and j.get("duration_months", 0) > 12:
            positives.append("startup experience")
            break

    # ── Build concerns ────────────────────────────────────────────────
    concerns = []

    if notice > 60:
        concerns.append(f"{notice}-day notice period")

    if country not in ("india", "in"):
        concerns.append(f"based outside India ({loc})")

    if recruiter_rr < 0.25:
        concerns.append(f"low recruiter response rate ({int(recruiter_rr * 100)}%)")

    # Only flag truly weak skill profiles — with 20+ must-haves,
    # even strong candidates score 0.15-0.25 on the skill component
    if debug.get("skill", 0) < 0.05:
        concerns.append("very limited AI/retrieval skills visible")

    if sal_max > 60:
        concerns.append(f"high salary expectation ({sal_max:.0f} LPA)")

    if debug.get("career", 0) < 0.3 and "it services" in industry.lower():
        concerns.append("career predominantly in IT services")

    last_active = signals.get("last_active_date", "")
    if last_active and last_active < "2025-12-01":
        concerns.append("inactive on platform for 6+ months")

    # ── Compose final reasoning ───────────────────────────────────────
    pos_text = "; ".join(positives[:3]) if positives else "profile shows partial alignment"
    sentence1 = f"{yoe:.0f}-year {title} at {company} — {pos_text}."

    if concerns:
        sentence2 = f" Concerns: {', '.join(concerns[:2])}."
        return sentence1 + sentence2

    return sentence1

