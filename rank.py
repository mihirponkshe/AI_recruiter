#!/usr/bin/env python3
"""
AI Recruiter — Redrob Hackathon submission ranker.
Usage: python rank.py --candidates candidates.jsonl --out submission.csv
Runtime target: <5 minutes on 16GB CPU.
"""
import argparse
import csv
import gzip
import json
import sys
from pathlib import Path

from scorer import compute_final_score
from reasoning import generate_reasoning


def load_candidates(path):
    p = Path(path)
    candidates = []
    opener = gzip.open if path.endswith(".gz") else open
    mode = "rt"
    with opener(p, mode, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    candidates.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return candidates


def normalize_scores(scored_list):
    """
    Normalize raw scores to [0, 1] range for the top 100.
    Preserves relative ordering and differentiation.
    Uses min-max normalization across the top candidates.
    """
    if not scored_list:
        return scored_list

    raw_scores = [s[1] for s in scored_list]
    max_score = max(raw_scores)
    min_score = min(raw_scores)

    if max_score == min_score:
        # All same score — assign linearly decreasing
        n = len(scored_list)
        return [
            (cid, round(1.0 - (i * 0.008), 6), debug, cand)
            for i, (cid, _, debug, cand) in enumerate(scored_list)
        ]

    score_range = max_score - min_score
    normalized = []
    for cid, raw, debug, cand in scored_list:
        norm = (raw - min_score) / score_range
        # Scale to [0.50, 1.0] range — keeps all scores meaningful
        norm = 0.50 + norm * 0.50
        normalized.append((cid, round(norm, 6), debug, cand))

    return normalized


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    print(f"Loading candidates from {args.candidates}...")
    candidates = load_candidates(args.candidates)
    print(f"Loaded {len(candidates)} candidates.")

    # Score all candidates
    print("Scoring...")
    scored = []
    honeypot_count = 0
    for i, c in enumerate(candidates):
        if i % 10000 == 0:
            print(f"  {i}/{len(candidates)}...")
        cid = c.get("candidate_id", "")
        final_score, debug = compute_final_score(c)
        scored.append((cid, final_score, debug, c))
        if debug.get("honeypot"):
            honeypot_count += 1

    print(f"Honeypots detected and eliminated: {honeypot_count}")

    # Sort descending by score, then ascending by candidate_id for tie-breaking
    scored.sort(key=lambda x: (-x[1], x[0]))

    # Take top 100
    top100_raw = scored[:100]

    # Normalize scores to [0.50, 1.00] range for submission
    top100 = normalize_scores(top100_raw)

    # Generate reasoning
    print("Generating reasoning for top 100...")
    rows = []
    for rank_pos, (cid, score, debug, candidate) in enumerate(top100, start=1):
        reason = generate_reasoning(candidate, rank_pos, score, debug)
        rows.append({
            "candidate_id": cid,
            "rank": rank_pos,
            "score": round(score, 6),
            "reasoning": reason,
        })

    # Write CSV
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["candidate_id", "rank", "score", "reasoning"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSubmission written to {args.out}")
    print(f"Top 5 scores: {[r['score'] for r in rows[:5]]}")
    print(f"Bottom 5 scores: {[r['score'] for r in rows[-5:]]}")

    # Quick quality check: print titles of top 10
    print("\n=== TOP 10 CANDIDATES ===")
    for r, (cid, sc, dbg, cand) in zip(rows[:10], top100[:10]):
        title = cand['profile']['current_title']
        company = cand['profile']['current_company']
        print(f"  Rank {r['rank']:>3}: {sc:.6f}  {title} at {company}")


if __name__ == "__main__":
    main()
