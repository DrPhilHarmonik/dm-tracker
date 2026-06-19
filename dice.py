"""Dice notation parsing/rolling, plus 5e stat-aware rolls built on top of
a normalized character sheet (see sheet.py).

Every public roll function accepts an optional ``rng`` (defaults to the
``random`` module) so tests can pass a seeded ``random.Random`` instance.
"""
import random
import re
from dataclasses import dataclass, field

import sheet as shm

DICE_TERM_RE = re.compile(r"^(\d*)d(\d+)(?:(kh|kl)(\d+))?$", re.IGNORECASE)


@dataclass
class RollResult:
    total: int
    detail: str
    rolls: list[int] = field(default_factory=list)


def _split_terms(expression: str) -> list[str]:
    expression = expression.replace(" ", "")
    if not expression:
        raise ValueError("Empty dice expression")
    if expression[0] not in "+-":
        expression = "+" + expression
    return re.findall(r"[+-][^+-]+", expression)


def _roll_dice_term(count: int, sides: int, keep_mode: str | None, keep_count: int | None, rng) -> tuple[int, str, list[int]]:
    if count < 1 or sides < 1:
        raise ValueError("Dice count and sides must be positive")
    rolls = [rng.randint(1, sides) for _ in range(count)]
    kept = rolls
    if keep_mode and keep_count:
        kept = sorted(rolls, reverse=(keep_mode == "kh"))[:keep_count]
    label = f"{count}d{sides}"
    if keep_mode:
        label += f"{keep_mode}{keep_count}"
    detail = f"{label}({','.join(str(r) for r in rolls)})"
    return sum(kept), detail, kept


def roll(expression: str, rng=random) -> RollResult:
    """Roll a dice expression like ``2d6+3`` or ``4d6kh3``."""
    terms = _split_terms(expression)
    total = 0
    parts = []
    all_rolls: list[int] = []

    for index, term in enumerate(terms):
        sign = -1 if term[0] == "-" else 1
        body = term[1:]
        match = DICE_TERM_RE.match(body)
        if match:
            count_str, sides_str, keep_mode, keep_count_str = match.groups()
            count = int(count_str) if count_str else 1
            sides = int(sides_str)
            keep_mode = keep_mode.lower() if keep_mode else None
            keep_count = int(keep_count_str) if keep_count_str else None
            value, detail, kept = _roll_dice_term(count, sides, keep_mode, keep_count, rng)
            all_rolls.extend(kept)
        else:
            try:
                value = int(body)
            except ValueError:
                raise ValueError(f"Invalid dice term: {term}")
            detail = str(value)

        total += sign * value
        if index == 0:
            parts.append(detail if sign > 0 else f"-{detail}")
        else:
            parts.append(f"{'+' if sign > 0 else '-'} {detail}")

    return RollResult(total=total, detail=" ".join(parts) + f" = {total}", rolls=all_rolls)


def roll_d20(modifier: int = 0, advantage: bool = False, disadvantage: bool = False, rng=random) -> RollResult:
    """Roll a single d20, or 2d20 keep best/worst for advantage/disadvantage."""
    if advantage and disadvantage:
        advantage = disadvantage = False

    if advantage or disadvantage:
        a, b = rng.randint(1, 20), rng.randint(1, 20)
        die = max(a, b) if advantage else min(a, b)
        mode = "adv" if advantage else "dis"
        rolls = [a, b]
        detail = f"d20({a},{b} {mode})"
    else:
        die = rng.randint(1, 20)
        rolls = [die]
        detail = f"d20({die})"

    total = die + modifier
    if modifier:
        detail += f" {'+' if modifier >= 0 else '-'} {abs(modifier)}"
    detail += f" = {total}"
    return RollResult(total=total, detail=detail, rolls=rolls)


def roll_ability_check(sheet: dict, ability: str, advantage: bool = False, disadvantage: bool = False, rng=random) -> RollResult:
    mod = shm.ability_modifier(sheet["abilities"][ability])
    return roll_d20(mod, advantage, disadvantage, rng)


def roll_saving_throw(sheet: dict, entity_type: str, ability: str, advantage: bool = False, disadvantage: bool = False, rng=random) -> RollResult:
    pb = shm.proficiency_bonus(entity_type, sheet)
    bonus = shm.saving_throw_bonus(sheet, ability, pb)
    return roll_d20(bonus, advantage, disadvantage, rng)


def roll_skill_check(sheet: dict, entity_type: str, skill: str, advantage: bool = False, disadvantage: bool = False, rng=random) -> RollResult:
    pb = shm.proficiency_bonus(entity_type, sheet)
    bonus = shm.skill_bonus(sheet, skill, pb)
    return roll_d20(bonus, advantage, disadvantage, rng)


def roll_attack(attack: dict, advantage: bool = False, disadvantage: bool = False, rng=random) -> RollResult:
    bonus = int(attack.get("bonus", 0) or 0)
    return roll_d20(bonus, advantage, disadvantage, rng)


def roll_damage(attack: dict, rng=random) -> RollResult:
    return roll(attack.get("damage") or "0", rng=rng)
