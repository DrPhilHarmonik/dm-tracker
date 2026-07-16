"""Encounter generator: given party composition and target difficulty,
return a list of SRD monster dicts that fit the XP budget.

All functions are pure (no DB access). The caller decides what to do with
the returned monster list.
"""
import random as _random
from fractions import Fraction

import encounter_balance as enc_bal
import srd


def _cr_float(cr_str: str) -> float:
    try:
        return float(Fraction(cr_str))
    except (ValueError, ZeroDivisionError):
        return 0.0


def generate(
    party_levels: list[int],
    difficulty: str = "medium",
    pool: list[dict] | None = None,
    seed: int | None = None,
) -> list[dict]:
    """Return a list of monster dicts for a balanced encounter.

    difficulty: 'easy', 'medium', 'hard', or 'deadly'.
    pool: override the SRD monster list (useful for tests).
    seed: set for reproducible output.
    """
    rng = _random.Random(seed)
    pool = pool if pool is not None else srd.MONSTERS
    difficulty = difficulty.lower()

    if not party_levels:
        return []

    thresholds = enc_bal.party_thresholds(party_levels)
    target_xp = thresholds.get(difficulty, thresholds["medium"])
    if target_xp <= 0:
        return []

    avg_level = sum(party_levels) / len(party_levels)
    max_cr = min(avg_level + 4, 30.0)

    eligible = [
        m for m in pool
        if enc_bal.cr_xp(m["cr"]) is not None
        and _cr_float(m["cr"]) <= max_cr
        and _cr_float(m["cr"]) > 0
    ]
    if not eligible:
        return []

    best: list[dict] = []
    best_score = float("inf")

    # Try several monster counts and pick whichever gets closest to target XP
    for count in (1, 2, 3, 3, 4, 4, 5, 6):
        mult = enc_bal.encounter_multiplier(count)
        raw_budget = target_xp / mult
        per_monster = raw_budget / count

        # Candidates within a generous band around per-monster budget
        candidates = [
            m for m in eligible
            if per_monster * 0.15 <= (enc_bal.cr_xp(m["cr"]) or 0) <= per_monster * 3.0
        ]
        if not candidates:
            # Fall back to monsters closest in XP to per-monster budget
            candidates = sorted(eligible, key=lambda m: abs((enc_bal.cr_xp(m["cr"]) or 0) - per_monster))[:10]

        group = [rng.choice(candidates) for _ in range(count)]
        raw = sum(enc_bal.cr_xp(m["cr"]) or 0 for m in group)
        adj = int(raw * enc_bal.encounter_multiplier(count))
        score = abs(adj - target_xp)
        if score < best_score:
            best_score = score
            best = group

    return best


def summary(monsters: list[dict], party_levels: list[int]) -> dict:
    """Return difficulty info for a generated monster list."""
    crs = [m["cr"] for m in monsters]
    return enc_bal.calculate_difficulty(crs, party_levels)
