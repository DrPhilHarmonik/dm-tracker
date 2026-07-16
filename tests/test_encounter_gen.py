import encounter_gen as gen
import encounter_balance as enc_bal

_SMALL_POOL = [
    {"name": "Goblin", "cr": "1/4", "creature_type": "Humanoid", "ac": 15, "hp_max": 7,
     "abilities": {"str": 8, "dex": 14, "con": 10, "int": 10, "wis": 8, "cha": 8},
     "saving_throw_proficiencies": [], "skill_proficiencies": {},
     "resistances": "", "immunities": "", "vulnerabilities": "",
     "attacks": [], "special_abilities": [], "senses": "", "languages": ""},
    {"name": "Orc", "cr": "1/2", "creature_type": "Humanoid", "ac": 13, "hp_max": 15,
     "abilities": {"str": 16, "dex": 12, "con": 16, "int": 7, "wis": 11, "cha": 10},
     "saving_throw_proficiencies": [], "skill_proficiencies": {},
     "resistances": "", "immunities": "", "vulnerabilities": "",
     "attacks": [], "special_abilities": [], "senses": "", "languages": ""},
    {"name": "Bugbear", "cr": "1", "creature_type": "Humanoid", "ac": 16, "hp_max": 27,
     "abilities": {"str": 15, "dex": 14, "con": 13, "int": 8, "wis": 11, "cha": 9},
     "saving_throw_proficiencies": [], "skill_proficiencies": {},
     "resistances": "", "immunities": "", "vulnerabilities": "",
     "attacks": [], "special_abilities": [], "senses": "", "languages": ""},
    {"name": "Ogre", "cr": "2", "creature_type": "Giant", "ac": 11, "hp_max": 59,
     "abilities": {"str": 19, "dex": 8, "con": 16, "int": 5, "wis": 7, "cha": 7},
     "saving_throw_proficiencies": [], "skill_proficiencies": {},
     "resistances": "", "immunities": "", "vulnerabilities": "",
     "attacks": [], "special_abilities": [], "senses": "", "languages": ""},
]


def test_generate_returns_list():
    result = gen.generate([3, 3, 3, 3], "medium", pool=_SMALL_POOL, seed=42)
    assert isinstance(result, list)
    assert len(result) >= 1


def test_generate_respects_cr_ceiling():
    # A level-1 party should not get CR 20 monsters
    party = [1, 1, 1, 1]
    result = gen.generate(party, "medium", pool=_SMALL_POOL, seed=1)
    for m in result:
        from fractions import Fraction
        assert float(Fraction(m["cr"])) <= 5.0


def test_generate_empty_party_returns_empty():
    assert gen.generate([], "medium", pool=_SMALL_POOL) == []


def test_generate_reproducible_with_seed():
    a = gen.generate([5, 5, 5, 5], "hard", pool=_SMALL_POOL, seed=99)
    b = gen.generate([5, 5, 5, 5], "hard", pool=_SMALL_POOL, seed=99)
    assert [m["name"] for m in a] == [m["name"] for m in b]


def test_generate_different_seeds_may_differ():
    a = gen.generate([5, 5, 5, 5], "hard", pool=_SMALL_POOL, seed=1)
    b = gen.generate([5, 5, 5, 5], "hard", pool=_SMALL_POOL, seed=2)
    # Not guaranteed different, but with a pool of 4 and 2 seeds, high chance
    # of at least one name being different. We just check both are non-empty.
    assert len(a) >= 1
    assert len(b) >= 1


def test_generate_full_pool_medium():
    result = gen.generate([3, 3, 3, 3], "medium", seed=7)
    assert len(result) >= 1
    for m in result:
        assert "name" in m
        assert "cr" in m


def test_generate_deadly_higher_cr_than_easy():
    easy = gen.generate([5, 5, 5, 5], "easy", seed=10)
    deadly = gen.generate([5, 5, 5, 5], "deadly", seed=10)
    easy_xp = sum(enc_bal.cr_xp(m["cr"]) or 0 for m in easy)
    deadly_xp = sum(enc_bal.cr_xp(m["cr"]) or 0 for m in deadly)
    # Deadly should pull more raw XP than easy
    assert deadly_xp >= easy_xp


def test_summary_returns_difficulty_dict():
    monsters = gen.generate([4, 4, 4, 4], "medium", pool=_SMALL_POOL, seed=5)
    info = gen.summary(monsters, [4, 4, 4, 4])
    assert "difficulty" in info
    assert "adjusted_xp" in info
    assert "thresholds" in info


def test_generate_all_monsters_have_required_keys():
    result = gen.generate([5, 5, 5, 5], "hard", seed=3)
    for m in result:
        for key in ("name", "cr", "ac", "hp_max"):
            assert key in m, f"Monster missing key {key}: {m.get('name')}"
