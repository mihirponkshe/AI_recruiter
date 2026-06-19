# scorer.py
"""
Core ranking logic — multi-signal weighted scoring.

Components (weights sum to 1.0):
    skill_score       0.25  — alias-normalized, proficiency × duration
    career_score      0.25  — product vs consulting, relevant titles, IR systems
    text_score        0.15  — headline + summary keyword analysis
    experience_score  0.10  — 6-8yr ideal band
    location_score    0.10  — India cities, relocation
    education_score   0.05  — institution tier, CS field
    salary_fit_score  0.05  — budget alignment
    assess_score      0.05  — platform skill assessments

Behavioral score is applied as a MULTIPLIER (not additive).
Honeypots are eliminated first (score → 0).
Hard disqualifiers applied post-scoring.
"""
import re
from jd_parser import JD_CONFIG
from signals import behavioral_score, location_score
from honeypot import is_honeypot

# ── Skill alias normalization ──────────────────────────────────────────────
# Map skill name variations to canonical names matching JD_CONFIG lists
SKILL_ALIASES = {
    # Embeddings
    "sentence transformer": "embeddings",
    "sentence-transformers": "embeddings",
    "sentence transformers": "embeddings",
    "openai embeddings": "embeddings",
    "text embeddings": "embeddings",
    "embedding": "embeddings",
    "word embeddings": "embeddings",
    "word2vec": "embeddings",
    "glove": "embeddings",
    "fasttext": "embeddings",
    "doc2vec": "embeddings",
    "text embedding": "embeddings",
    "embedding models": "embeddings",

    # Vector databases
    "vector search": "vector database",
    "vector db": "vector database",
    "vector store": "vector database",
    "chroma": "vector database",
    "chromadb": "vector database",
    "pgvector": "vector database",

    # Retrieval
    "semantic search": "retrieval",
    "dense retrieval": "retrieval",
    "bm25": "retrieval",
    "ir": "retrieval",
    "search engine": "retrieval",
    "search systems": "retrieval",
    "search relevance": "retrieval",
    "text retrieval": "retrieval",
    "document retrieval": "retrieval",
    "passage retrieval": "retrieval",
    "search ranking": "ranking",

    # Hybrid search
    "hybrid retrieval": "hybrid search",
    "hybrid search systems": "hybrid search",

    # Evaluation
    "ndcg": "evaluation",
    "mrr": "evaluation",
    "map": "evaluation",
    "a/b test": "evaluation",
    "a/b testing": "evaluation",
    "ab testing": "evaluation",
    "ranking evaluation": "evaluation",
    "offline evaluation": "evaluation",
    "precision@k": "evaluation",
    "recall@k": "evaluation",

    # Production ML
    "production deployment": "production ml",
    "mlops": "production ml",
    "ml engineering": "production ml",
    "model deployment": "production ml",
    "model serving": "production ml",
    "ml infrastructure": "production ml",
    "ml pipeline": "production ml",

    # Applied ML
    "machine learning": "applied ml",
    "applied machine learning": "applied ml",
    "deep learning": "applied ml",
    "neural networks": "applied ml",
    "supervised learning": "applied ml",

    # NLP
    "natural language processing": "applied ml",
    "nlp": "applied ml",
    "text classification": "applied ml",
    "text mining": "applied ml",
    "named entity recognition": "applied ml",
    "ner": "applied ml",
    "sentiment analysis": "applied ml",
    "tokenization": "applied ml",

    # Fine-tuning
    "fine-tuning llms": "fine-tuning",
    "fine tuning": "fine-tuning",
    "finetuning": "fine-tuning",
    "model fine-tuning": "fine-tuning",
    "instruction tuning": "fine-tuning",

    # LLM
    "large language model": "llm",
    "large language models": "llm",
    "gpt": "llm",
    "chatgpt": "llm",
    "openai": "llm",
    "claude": "llm",
    "gemini": "llm",
    "langchain": "llm",
    "llamaindex": "llm",
    "llama": "llm",

    # RAG
    "retrieval augmented generation": "rag",
    "retrieval-augmented generation": "rag",

    # PyTorch
    "torch": "pytorch",

    # Transformers
    "hugging face": "transformers",
    "huggingface": "transformers",
    "transformer models": "transformers",
    "attention mechanism": "transformers",

    # Learning to rank
    "ltr": "learning to rank",
    "lambdamart": "learning to rank",
    "ranknet": "learning to rank",

    # BERT variants
    "roberta": "bert",
    "albert": "bert",
    "distilbert": "bert",
    "sbert": "bert",
    "sentence-bert": "bert",

    # Distributed systems
    "apache spark": "distributed systems",
    "spark": "distributed systems",
    "hadoop": "distributed systems",
    "kafka": "distributed systems",
    "ray": "distributed systems",
    "dask": "distributed systems",

    # Recommendation
    "recommendation systems": "ranking",
    "recommender system": "ranking",
    "collaborative filtering": "ranking",
    "content-based filtering": "ranking",
}


def normalize_skill(name):
    """Normalize a skill name through the alias map."""
    n = name.lower().strip()
    return SKILL_ALIASES.get(n, n)


def skill_score(candidate, jd_config):
    """
    Returns 0.0–1.0 based on how well skills match the JD.
    Weights: proficiency level × duration × endorsements.
    """
    skills = candidate.get("skills", [])
    must_have = set(jd_config["must_have_skills"])
    nice_to_have = set(jd_config["nice_to_have_skills"])

    PROFICIENCY_MAP = {
        "beginner": 0.3,
        "intermediate": 0.6,
        "advanced": 0.85,
        "expert": 1.0,
    }

    must_score = 0.0
    nice_score = 0.0
    must_matched = set()
    nice_matched = set()

    for skill in skills:
        name = normalize_skill(skill.get("name", ""))
        prof = PROFICIENCY_MAP.get(skill.get("proficiency", "beginner"), 0.3)
        dur = min(skill.get("duration_months", 0) / 24, 1.0)  # normalize to 2 years
        endorse_bonus = min(skill.get("endorsements", 0) / 50, 0.2)

        skill_strength = prof * 0.6 + dur * 0.3 + endorse_bonus * 0.1

        # Check must-have (partial matching)
        for must in must_have:
            if must in name or name in must:
                must_matched.add(must)
                must_score += skill_strength
                break
        else:
            # Check nice-to-have only if not a must-have match
            for nice in nice_to_have:
                if nice in name or name in nice:
                    nice_matched.add(nice)
                    nice_score += skill_strength * 0.5
                    break

    # Normalize
    must_coverage = len(must_matched) / max(len(must_have), 1)
    must_final = min(must_score / max(len(must_have), 1), 1.0) * 0.7 + must_coverage * 0.3
    nice_final = min(nice_score / max(len(nice_to_have), 1), 1.0)

    return min(must_final * 0.80 + nice_final * 0.20, 1.0)


def text_score(candidate, jd_config):
    """
    Scores headline + summary text for domain-relevant keywords.
    Returns 0.0–1.0 based on presence of IR/search/ranking terms
    and production deployment language.
    """
    profile = candidate.get("profile", {})
    headline = (profile.get("headline") or "").lower()
    summary = (profile.get("summary") or "").lower()
    combined = headline + " " + summary

    if not combined.strip():
        return 0.1  # very low — no text to analyze

    high_terms = jd_config["text_high_signal_terms"]
    medium_terms = jd_config["text_medium_signal_terms"]
    prod_terms = jd_config["text_production_terms"]

    # Count distinct high-signal term matches
    high_count = sum(1 for t in high_terms if t in combined)
    medium_count = sum(1 for t in medium_terms if t in combined)
    prod_count = sum(1 for t in prod_terms if t in combined)

    # Scoring: diminishing returns on counts
    # high terms are worth the most
    high_score = min(high_count / 4, 1.0)     # 4+ high terms → maxed
    medium_score = min(medium_count / 5, 1.0)  # 5+ medium terms → maxed
    prod_score = min(prod_count / 3, 1.0)      # 3+ production terms → maxed

    # Also check for career descriptions mentioning search/ranking systems
    career_text_bonus = 0.0
    for job in candidate.get("career_history", []):
        desc = (job.get("description") or "").lower()
        ir_mentions = sum(1 for t in high_terms if t in desc)
        if ir_mentions >= 2:
            career_text_bonus = 0.15
            break
        elif ir_mentions >= 1:
            career_text_bonus = max(career_text_bonus, 0.08)

    raw = (
        high_score * 0.45
        + medium_score * 0.25
        + prod_score * 0.15
        + career_text_bonus
    )
    return min(raw, 1.0)


def career_score(candidate, jd_config):
    """
    Scores career history for product company experience, relevant titles,
    and absence of disqualifiers. Also checks profile.current_industry.
    """
    history = candidate.get("career_history", [])
    profile = candidate.get("profile", {})

    if not history:
        return 0.1

    disq_companies = set(jd_config["disqualifier_companies"])
    disq_industries = set(jd_config["disqualifier_industries"])
    disq_titles = set(jd_config["disqualifier_titles"])
    pos_titles = set(jd_config["positive_titles"])

    total_months = 0
    product_months = 0
    consulting_months = 0
    positive_title_months = 0
    disq_title_months = 0
    has_ranking_or_search_system = False
    startup_months = 0

    for job in history:
        months = job.get("duration_months", 0)
        company = (job.get("company") or "").lower()
        industry = (job.get("industry") or "").lower()
        title = (job.get("title") or "").lower()
        desc = (job.get("description") or "").lower()
        company_size = job.get("company_size", "1-10")

        total_months += months

        # Check disqualifiers
        is_consulting = (
            any(d in company for d in disq_companies)
            or any(d in industry for d in disq_industries)
        )
        if is_consulting:
            consulting_months += months
        else:
            product_months += months

        # Startup bonus (small company = startup-like)
        if company_size in ("1-10", "11-50", "51-200"):
            startup_months += months

        # Title scoring
        for pt in pos_titles:
            if pt in title:
                positive_title_months += months
                break
        for dt in disq_titles:
            if dt in title:
                disq_title_months += months
                break

        # Search for production ranking/retrieval systems in description
        ir_terms = [
            "ranking", "retrieval", "recommendation", "search engine",
            "vector", "embedding", "semantic", "matching", "scoring",
            "reranking", "re-ranking", "information retrieval",
            "search relevance", "query understanding", "search quality",
        ]
        if any(term in desc for term in ir_terms):
            has_ranking_or_search_system = True

    if total_months == 0:
        return 0.1

    # Also check current industry from profile
    current_industry = (profile.get("current_industry") or "").lower()
    if any(d in current_industry for d in disq_industries):
        consulting_months = max(consulting_months, total_months * 0.5)

    # Ratios
    consulting_ratio = consulting_months / total_months
    product_ratio = product_months / total_months
    positive_title_ratio = positive_title_months / total_months
    disq_title_ratio = disq_title_months / total_months
    startup_ratio = startup_months / total_months

    score = 0.0

    # Product company experience is the biggest signal
    score += product_ratio * 0.35

    # Positive title match
    score += positive_title_ratio * 0.25

    # Has built a search/ranking system
    if has_ranking_or_search_system:
        score += 0.20

    # Startup experience bonus (JD is Series A startup)
    if startup_ratio > 0.3:
        score += 0.10
    elif startup_ratio > 0.1:
        score += 0.05

    # Penalty for consulting-heavy career
    if consulting_ratio > 0.8:
        score *= 0.15  # career entirely in services → near-disqualifier
    elif consulting_ratio > 0.6:
        score *= 0.40
    elif consulting_ratio > 0.4:
        score *= 0.70

    # Penalty for completely wrong title domain
    if disq_title_ratio > 0.7:
        score *= 0.10
    elif disq_title_ratio > 0.5:
        score *= 0.30

    return min(score, 1.0)


def experience_score(candidate, jd_config):
    """Score based on years of experience hitting the 5-9 year band."""
    yoe = candidate.get("profile", {}).get("years_of_experience", 0)
    exp_min = jd_config["exp_min"]
    exp_max = jd_config["exp_max"]
    ideal_min = jd_config["exp_ideal_min"]
    ideal_max = jd_config["exp_ideal_max"]

    if ideal_min <= yoe <= ideal_max:
        return 1.0
    elif exp_min <= yoe <= exp_max:
        return 0.80
    elif exp_max < yoe <= exp_max + 3:
        return 0.65  # slightly over but ok
    elif yoe < exp_min and yoe >= exp_min - 1:
        return 0.60  # slightly under
    elif yoe < 3:
        return 0.20  # too junior
    else:
        return 0.40  # too senior (15+ years, may be overqualified)


def education_score(candidate, jd_config):
    """
    Score based on institution tier and field of study relevance.
    Returns 0.0–1.0.
    """
    education = candidate.get("education", [])
    if not education:
        return 0.30  # neutral — some strong candidates lack formal edu

    relevant_fields = jd_config["relevant_fields_of_study"]

    best_score = 0.0
    for edu in education:
        tier = (edu.get("tier") or "unknown").lower()
        field = (edu.get("field_of_study") or "").lower()
        degree = (edu.get("degree") or "").lower()

        # Field relevance
        is_relevant_field = any(rf in field for rf in relevant_fields)

        # Tier scoring
        tier_scores = {
            "tier_1": 1.0,
            "tier_2": 0.75,
            "tier_3": 0.55,
            "tier_4": 0.40,
            "unknown": 0.45,
        }
        tier_val = tier_scores.get(tier, 0.40)

        # Field bonus
        if is_relevant_field:
            field_val = 1.0
        else:
            field_val = 0.50  # non-CS field is a penalty

        # Degree bonus
        degree_bonus = 0.0
        if "ph.d" in degree or "phd" in degree or "doctorate" in degree:
            degree_bonus = 0.15
        elif "m.tech" in degree or "m.s" in degree or "master" in degree or "m.e" in degree:
            degree_bonus = 0.08

        edu_score = tier_val * 0.50 + field_val * 0.40 + degree_bonus
        best_score = max(best_score, min(edu_score, 1.0))

    return best_score


def salary_fit_score(candidate, jd_config):
    """
    Score based on salary expectation vs budget fit.
    Returns 0.0–1.0. Budget max is ~50 LPA for this Series A role.
    """
    signals = candidate.get("redrob_signals", {})
    salary = signals.get("expected_salary_range_inr_lpa", {})

    if not salary or not isinstance(salary, dict):
        return 0.50  # neutral if no data

    sal_min = salary.get("min", 0)
    sal_max = salary.get("max", 0)
    budget = jd_config["salary_budget_max_lpa"]

    if sal_max <= 0:
        return 0.50  # no meaningful data

    # Perfect: candidate's expected range overlaps with budget
    if sal_min <= budget:
        if sal_max <= budget * 1.1:
            return 1.0   # within budget
        elif sal_max <= budget * 1.3:
            return 0.80  # slightly over but negotiable
        elif sal_max <= budget * 1.5:
            return 0.60  # stretch
        else:
            return 0.35  # expecting much more than budget
    else:
        # Minimum expected salary is above budget
        if sal_min <= budget * 1.2:
            return 0.50  # might be negotiable
        elif sal_min <= budget * 1.5:
            return 0.30  # unlikely to accept
        else:
            return 0.15  # way over budget


def assess_score(candidate):
    """
    Bonus score from platform skill assessment results.
    Higher scores on relevant skills = credibility.
    """
    signals = candidate.get("redrob_signals", {})
    assessments = signals.get("skill_assessment_scores", {})
    if not assessments:
        return 0.50  # neutral, not penalized

    relevant_terms = [
        "python", "ml", "nlp", "retrieval", "ranking",
        "embedding", "data science", "machine learning",
        "deep learning", "ai", "search", "vector",
        "natural language", "transformers", "pytorch",
    ]
    relevant_scores = []
    for skill_name, score_val in assessments.items():
        if any(t in skill_name.lower() for t in relevant_terms):
            relevant_scores.append(score_val)

    if not relevant_scores:
        return 0.50
    avg = sum(relevant_scores) / len(relevant_scores)
    return min(avg / 100.0, 1.0)


def compute_final_score(candidate):
    """
    Master scoring function. Returns (final_score: float, debug_dict: dict).

    Weights:
        skill       0.25
        career      0.25
        text        0.15
        experience  0.10
        location    0.10
        education   0.05
        salary_fit  0.05
        assess      0.05
        ─────────────────
        total       1.00
        × behavioral multiplier
    """
    jd = JD_CONFIG

    # --- Honeypot check first ---
    honeypot, flags = is_honeypot(candidate)
    if honeypot:
        return 0.0, {"honeypot": True, "flags": flags}

    # --- Component scores ---
    s_skill   = skill_score(candidate, jd)
    s_career  = career_score(candidate, jd)
    s_text    = text_score(candidate, jd)
    s_exp     = experience_score(candidate, jd)
    s_loc     = location_score(candidate, jd)
    s_edu     = education_score(candidate, jd)
    s_salary  = salary_fit_score(candidate, jd)
    s_assess  = assess_score(candidate)

    # --- Behavioral multiplier ---
    b_mult = behavioral_score(candidate)

    # --- Weighted composite ---
    base = (
        s_skill   * 0.25
        + s_career * 0.25
        + s_text   * 0.15
        + s_exp    * 0.10
        + s_loc    * 0.10
        + s_edu    * 0.05
        + s_salary * 0.05
        + s_assess * 0.05
    )

    final = base * b_mult

    # --- Hard disqualifier check (post-scoring) ---
    profile = candidate.get("profile", {})
    current_title = (profile.get("current_title") or "").lower()

    for dt in jd["disqualifier_titles"]:
        if dt in current_title:
            final *= 0.05  # near-zero, not absolute zero
            break

    # --- Additional penalty: current industry is consulting ---
    current_industry = (profile.get("current_industry") or "").lower()
    if any(d in current_industry for d in jd["disqualifier_industries"]):
        final *= 0.60  # significant penalty if still in services

    debug = {
        "honeypot": False,
        "skill": round(s_skill, 3),
        "career": round(s_career, 3),
        "text": round(s_text, 3),
        "exp": round(s_exp, 3),
        "loc": round(s_loc, 3),
        "edu": round(s_edu, 3),
        "salary": round(s_salary, 3),
        "assess": round(s_assess, 3),
        "behavioral_mult": round(b_mult, 3),
        "final": round(final, 4),
    }
    # Return raw score — do NOT cap at 1.0 here.
    # Normalization to [0, 1] happens in rank.py to preserve
    # differentiation among top candidates (critical for NDCG@10).
    return final, debug
