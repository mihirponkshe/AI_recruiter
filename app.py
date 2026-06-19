#!/usr/bin/env python3
"""
app.py — Streamlit sandbox for Redrob Hackathon submission.
Allows uploading candidates (JSONL) and viewing ranked output.
Deploy: push to GitHub → share.streamlit.io → connect repo.
"""
import streamlit as st
import json
import csv
import io
from scorer import compute_final_score
from reasoning import generate_reasoning

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Recruiter — Redrob Hackathon",
    page_icon="🧠",
    layout="wide",
)

# ── Header ───────────────────────────────────────────────────────────────────
st.title("🧠 AI Recruiter — Intelligent Candidate Ranking")
st.markdown("""
**Redrob Hackathon Submission** — Multi-signal rule-based ranker for the
Senior AI Engineer role. Upload candidates in JSONL format to see ranked results.
""")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ System Info")
    st.markdown("""
    **Scoring Components (8):**
    | Component | Weight |
    |---|---|
    | Skill Match | 0.25 |
    | Career Fit | 0.25 |
    | Text Analysis | 0.15 |
    | Experience | 0.10 |
    | Location | 0.10 |
    | Education | 0.05 |
    | Salary Fit | 0.05 |
    | Assessment | 0.05 |

    **+ Behavioral Multiplier** (0.4×–1.5×)

    **Anti-Gaming:**
    - Honeypot detection (6 checks)
    - Consulting career penalty
    - Title-domain disqualifiers
    - Keyword-stuffer immunity
    """)

# ── File Upload ──────────────────────────────────────────────────────────────
st.subheader("📤 Upload Candidates")

uploaded = st.file_uploader(
    "Upload a JSONL file (one JSON object per line, max 500 candidates for demo)",
    type=["jsonl", "json", "txt"],
)

# ── Also allow sample data ───────────────────────────────────────────────────
use_sample = st.checkbox("Or use built-in sample data (50 candidates)")

candidates = []

if uploaded:
    raw = uploaded.read().decode("utf-8").strip()
    # Handle both JSON array and JSONL formats
    if raw.startswith("["):
        candidates = json.loads(raw)
    else:
        for line in raw.split("\n"):
            line = line.strip()
            if line:
                try:
                    candidates.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    # Limit for demo
    if len(candidates) > 500:
        st.warning(f"Loaded {len(candidates)} candidates. Trimming to 500 for demo.")
        candidates = candidates[:500]

elif use_sample:
    import os
    sample_path = os.path.join(os.path.dirname(__file__), "data", "sample_candidates.json")
    if os.path.exists(sample_path):
        with open(sample_path, "r", encoding="utf-8") as f:
            candidates = json.load(f)
    else:
        st.error("sample_candidates.json not found in data/ folder.")

# ── Scoring ──────────────────────────────────────────────────────────────────
if candidates:
    st.subheader(f"📊 Scoring {len(candidates)} candidates...")

    progress = st.progress(0)
    scored = []
    honeypot_count = 0

    for i, c in enumerate(candidates):
        cid = c.get("candidate_id", f"UNKNOWN_{i}")
        final_score, debug = compute_final_score(c)
        scored.append((cid, final_score, debug, c))
        if debug.get("honeypot"):
            honeypot_count += 1
        progress.progress((i + 1) / len(candidates))

    progress.empty()

    # Sort
    scored.sort(key=lambda x: (-x[1], x[0]))
    top = scored[:min(100, len(scored))]

    # Normalize scores to [0.50, 1.00]
    if len(top) > 1:
        raw_scores = [s[1] for s in top]
        max_s, min_s = max(raw_scores), min(raw_scores)
        if max_s != min_s:
            top = [
                (cid, round(0.50 + (raw - min_s) / (max_s - min_s) * 0.50, 6), dbg, cand)
                for cid, raw, dbg, cand in top
            ]

    # ── Summary Stats ────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Candidates", len(candidates))
    col2.metric("Honeypots Detected", honeypot_count)
    col3.metric("Top Score", f"{top[0][1]:.4f}" if top else "N/A")
    col4.metric("Ranked Output", f"Top {len(top)}")

    # ── Build output table ───────────────────────────────────────────────
    rows = []
    for rank_pos, (cid, score, debug, c) in enumerate(top, start=1):
        reason = generate_reasoning(c, rank_pos, score, debug)
        profile = c.get("profile", {})
        rows.append({
            "candidate_id": cid,
            "rank": rank_pos,
            "score": round(score, 6),
            "title": profile.get("current_title", ""),
            "company": profile.get("current_company", ""),
            "yoe": profile.get("years_of_experience", 0),
            "location": profile.get("location", ""),
            "reasoning": reason,
        })

    # ── Results Table ────────────────────────────────────────────────────
    st.subheader("🏆 Ranked Results")

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📋 Rankings", "📊 Score Breakdown", "🔍 Candidate Detail"])

    with tab1:
        st.dataframe(
            rows,
            column_config={
                "rank": st.column_config.NumberColumn("Rank", width="small"),
                "score": st.column_config.NumberColumn("Score", format="%.4f"),
                "candidate_id": "Candidate ID",
                "title": "Current Title",
                "company": "Company",
                "yoe": st.column_config.NumberColumn("YoE", format="%.1f"),
                "location": "Location",
                "reasoning": st.column_config.TextColumn("Reasoning", width="large"),
            },
            width="stretch",
            hide_index=True,
        )

    with tab2:
        # Show score component breakdown for top 20
        st.markdown("**Score breakdown for top 20 candidates:**")
        breakdown_rows = []
        for rank_pos, (cid, score, debug, c) in enumerate(top[:20], start=1):
            if not debug.get("honeypot"):
                breakdown_rows.append({
                    "Rank": rank_pos,
                    "ID": cid,
                    "Skill": debug.get("skill", 0),
                    "Career": debug.get("career", 0),
                    "Text": debug.get("text", 0),
                    "Exp": debug.get("exp", 0),
                    "Location": debug.get("loc", 0),
                    "Edu": debug.get("edu", 0),
                    "Salary": debug.get("salary", 0),
                    "Assess": debug.get("assess", 0),
                    "Behavioral×": debug.get("behavioral_mult", 0),
                })
        st.dataframe(breakdown_rows, width="stretch", hide_index=True)

    with tab3:
        # Candidate detail viewer
        if top:
            selected_rank = st.selectbox(
                "Select candidate by rank:",
                range(1, len(top) + 1),
                format_func=lambda x: f"Rank {x}: {top[x-1][0]} — {top[x-1][3].get('profile', {}).get('current_title', '')}"
            )
            idx = selected_rank - 1
            cid, score, debug, cand = top[idx]
            profile = cand.get("profile", {})

            st.markdown(f"### {profile.get('current_title', '')} at {profile.get('current_company', '')}")
            st.markdown(f"**Headline:** {profile.get('headline', '')}")
            st.markdown(f"**Location:** {profile.get('location', '')} ({profile.get('country', '')})")
            st.markdown(f"**Experience:** {profile.get('years_of_experience', 0):.1f} years")
            st.markdown(f"**Industry:** {profile.get('current_industry', '')}")

            st.markdown("---")
            st.markdown("**Summary:**")
            st.markdown(profile.get("summary", ""))

            st.markdown("---")
            st.markdown("**Career History:**")
            for job in cand.get("career_history", []):
                st.markdown(
                    f"- **{job.get('title', '')}** at {job.get('company', '')} "
                    f"({job.get('duration_months', 0)} months) — {job.get('industry', '')}"
                )
                if job.get("description"):
                    st.caption(job["description"][:200] + "..." if len(job.get("description", "")) > 200 else job["description"])

            st.markdown("---")
            st.markdown("**Skills (Advanced/Expert):**")
            adv_skills = [
                f"{s['name']} ({s['proficiency']}, {s.get('duration_months', 0)}mo)"
                for s in cand.get("skills", [])
                if s.get("proficiency") in ["advanced", "expert"]
            ]
            st.markdown(", ".join(adv_skills) if adv_skills else "None at advanced/expert level")

            st.markdown("---")
            col_a, col_b = st.columns(2)
            signals = cand.get("redrob_signals", {})
            with col_a:
                st.markdown("**Behavioral Signals:**")
                st.markdown(f"- Open to work: {'✅' if signals.get('open_to_work_flag') else '❌'}")
                st.markdown(f"- Notice period: {signals.get('notice_period_days', 'N/A')} days")
                st.markdown(f"- GitHub score: {signals.get('github_activity_score', 'N/A')}")
                st.markdown(f"- Response rate: {signals.get('recruiter_response_rate', 0):.0%}")
            with col_b:
                st.markdown("**Score Breakdown:**")
                for k, v in debug.items():
                    if k != "honeypot":
                        st.markdown(f"- {k}: **{v}**")

    # ── Download CSV ─────────────────────────────────────────────────────
    st.subheader("💾 Download Submission")

    csv_rows = [
        {
            "candidate_id": r["candidate_id"],
            "rank": r["rank"],
            "score": r["score"],
            "reasoning": r["reasoning"],
        }
        for r in rows
    ]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["candidate_id", "rank", "score", "reasoning"])
    writer.writeheader()
    writer.writerows(csv_rows)

    st.download_button(
        "⬇️ Download submission.csv",
        buf.getvalue(),
        "submission.csv",
        "text/csv",
        width="stretch",
    )

else:
    st.info("👆 Upload a JSONL file or check 'use built-in sample data' to get started.")

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("AI Recruiter — Redrob Hackathon Submission | Pure Python, zero external ML dependencies, <60s for 100K candidates")
