import random

import pytest

import dice
import sheet as shm


def test_roll_simple_dice_and_modifier():
    rng = random.Random(1)
    result = dice.roll("2d6+3", rng=rng)

    rng2 = random.Random(1)
    expected_rolls = [rng2.randint(1, 6) for _ in range(2)]
    assert result.rolls == expected_rolls
    assert result.total == sum(expected_rolls) + 3
    assert result.detail.endswith(f"= {result.total}")


def test_roll_negative_modifier():
    rng = random.Random(3)
    result = dice.roll("1d4-1", rng=rng)

    rng2 = random.Random(3)
    expected = rng2.randint(1, 4) - 1
    assert result.total == expected


def test_roll_keep_highest():
    rng = random.Random(2)
    result = dice.roll("4d6kh3", rng=rng)

    rng2 = random.Random(2)
    rolls = [rng2.randint(1, 6) for _ in range(4)]
    kept = sorted(rolls, reverse=True)[:3]
    assert result.total == sum(kept)
    assert sorted(result.rolls) == sorted(kept)


def test_roll_keep_lowest():
    rng = random.Random(9)
    result = dice.roll("4d6kl2", rng=rng)

    rng2 = random.Random(9)
    rolls = [rng2.randint(1, 6) for _ in range(4)]
    kept = sorted(rolls)[:2]
    assert result.total == sum(kept)


def test_roll_implicit_single_die():
    rng = random.Random(4)
    result = dice.roll("d20", rng=rng)
    rng2 = random.Random(4)
    assert result.total == rng2.randint(1, 20)


def test_roll_rejects_invalid_expression():
    with pytest.raises(ValueError):
        dice.roll("not-dice")


def test_roll_rejects_zero_sides_or_count():
    with pytest.raises(ValueError):
        dice.roll("0d6")


def test_roll_d20_advantage_takes_higher():
    rng = random.Random(5)
    result = dice.roll_d20(modifier=2, advantage=True, rng=rng)

    rng2 = random.Random(5)
    a, b = rng2.randint(1, 20), rng2.randint(1, 20)
    assert result.total == max(a, b) + 2


def test_roll_d20_disadvantage_takes_lower():
    rng = random.Random(6)
    result = dice.roll_d20(modifier=-1, disadvantage=True, rng=rng)

    rng2 = random.Random(6)
    a, b = rng2.randint(1, 20), rng2.randint(1, 20)
    assert result.total == min(a, b) - 1


def test_roll_d20_advantage_and_disadvantage_cancel_out():
    rng = random.Random(7)
    result = dice.roll_d20(modifier=0, advantage=True, disadvantage=True, rng=rng)

    rng2 = random.Random(7)
    expected = rng2.randint(1, 20)
    assert result.total == expected
    assert len(result.rolls) == 1


def test_roll_saving_throw_uses_sheet_proficiency_and_level():
    s = shm.normalize_sheet({
        "abilities": {"str": 16},
        "saving_throw_proficiencies": ["str"],
        "level": 5,
    })
    rng = random.Random(8)
    result = dice.roll_saving_throw(s, "adventurer", "str", rng=rng)

    rng2 = random.Random(8)
    die = rng2.randint(1, 20)
    pb = shm.proficiency_bonus_for_level(5)
    assert result.total == die + 3 + pb


def test_roll_skill_check_uses_sheet_expertise():
    s = shm.normalize_sheet({
        "abilities": {"dex": 18},
        "skill_proficiencies": {"stealth": "expertise"},
        "level": 5,
    })
    rng = random.Random(10)
    result = dice.roll_skill_check(s, "adventurer", "stealth", rng=rng)

    rng2 = random.Random(10)
    die = rng2.randint(1, 20)
    pb = shm.proficiency_bonus_for_level(5)
    assert result.total == die + 4 + pb * 2


def test_roll_attack_and_damage():
    attack = {"name": "Shortsword", "bonus": 5, "damage": "1d6+3", "damage_type": "piercing"}

    rng = random.Random(11)
    hit = dice.roll_attack(attack, rng=rng)
    rng2 = random.Random(11)
    assert hit.total == rng2.randint(1, 20) + 5

    rng3 = random.Random(12)
    dmg = dice.roll_damage(attack, rng=rng3)
    rng4 = random.Random(12)
    assert dmg.total == rng4.randint(1, 6) + 3
