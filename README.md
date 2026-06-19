# AI Recruiter — Intelligent Candidate Ranking System

Multi-signal rule-based ranker for the Redrob Hackathon: ranks 100K candidates for a Senior AI Engineer role using career history, text analysis, skill matching, behavioral signals, and honeypot detection.

## Quick Start

```bash
# No dependencies to install — pure Python + standard lib

# Run the ranking pipeline
python rank.py --candidates data/candidates.jsonl --out output/submission.csv

# Validate the submission
python validate_submission.py output/submission.csv
```

## Architecture

```
rank.py                          Main entrypoint (CLI)
 ├── jd_parser.py                Hardcoded JD config (skills, disqualifiers, keywords)
 ├── scorer.py                   8-component weighted scoring engine
 │    ├── skill_score()          Alias-normalized skill matching (proficiency × duration)
 │    ├── career_score()         Product vs consulting, relevant titles, IR systems
 │    ├── text_score()           Headline + summary + career desc keyword analysis
 │    ├── experience_score()     5-9yr band fit (6-8 ideal)
 │    ├── education_score()      Institution tier + CS field relevance
 │    ├── salary_fit_score()     Budget alignment (50 LPA cap)
 │    ├── assess_score()         Platform skill assessment results
 │    └── compute_final_score()  Weighted composite × behavioral multiplier
 ├── signals.py                  Behavioral multiplier (recency, notice, GitHub, etc.)
 ├── honeypot.py                 Fraud detection (date math, career overflow, etc.)
 └── reasoning.py                Data-grounded per-candidate reasoning
```

## Scoring Weights

| Component | Weight | Signal |
|---|---|---|
| Skill match | 0.25 | Proficiency × duration, 100+ aliases |
| Career fit | 0.25 | Product company ratio, IR system experience |
| Text analysis | 0.15 | Headline + summary keyword density |
| Experience | 0.10 | 6-8yr ideal, penalties outside 5-9 |
| Location | 0.10 | India cities, relocation willingness |
| Education | 0.05 | Institution tier, CS/EE field |
| Salary fit | 0.05 | Expected vs 50 LPA budget |
| Assessment | 0.05 | Platform skill test scores |

**Behavioral multiplier** (0.4×–1.5×): recency, open-to-work, notice period, GitHub, response rate, profile completeness, recruiter saves, offer acceptance, verification.

## Anti-Gaming Design

- **Career history is the primary signal** — not skill keyword count
- **Disqualifiers**: TCS/Infosys/Wipro/consulting-heavy careers → near-zero score
- **Title checks**: HR Managers, Content Writers, Graphic Designers → disqualified
- **Honeypot detection**: catches ~80 fraudulent profiles via date-math contradictions
- **Industry check**: current_industry = "IT Services" → significant penalty

## Runtime

- **100K candidates in ~60 seconds** on CPU (16GB RAM)
- Zero external dependencies
- No network calls during ranking
- No GPU required
