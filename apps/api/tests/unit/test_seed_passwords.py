import pytest

from seed.passwords import MissingSeedPassword, hashes, role_passwords

GOOD = {"SEED_TEACHER_PASSWORD": "teacher-pass-0001", "SEED_REVIEWER_PASSWORD": "reviewer-pass-0002",
        "SEED_ADMIN_PASSWORD": "admin-pass-000003"}


def test_dev_keeps_one_shared_demo_password() -> None:
    assert set(role_passwords("development", {}).values()) == {"preclass-demo"}
    assert set(role_passwords("staging", {"SEED_PASSWORD": "ci-seed-pass"}).values()) == {"ci-seed-pass"}


def test_demo_requires_strong_per_role_passwords() -> None:
    for missing in GOOD:
        env = {k: v for k, v in GOOD.items() if k != missing}
        with pytest.raises(MissingSeedPassword, match=missing):
            role_passwords("demo", env)
    with pytest.raises(MissingSeedPassword, match="SEED_ADMIN_PASSWORD"):
        role_passwords("demo", {**GOOD, "SEED_ADMIN_PASSWORD": "short"})


def test_demo_never_uses_the_default_and_disables_student_passwords_unless_asked() -> None:
    p = role_passwords("demo", GOOD)
    assert "preclass-demo" not in p.values() and p["ADMIN"] == GOOD["SEED_ADMIN_PASSWORD"]
    a, b = role_passwords("demo", GOOD)["STUDENT"], role_passwords("demo", GOOD)["STUDENT"]
    assert a != b and a not in GOOD.values()  # random, thrown away: no password login for seed students
    assert role_passwords("demo", {**GOOD, "SEED_STUDENT_PASSWORD": "student-pass-0004"})["STUDENT"] == "student-pass-0004"


def test_hashes_are_argon2_per_role() -> None:
    h = hashes("demo", GOOD)
    assert set(h) == {"TEACHER", "REVIEWER", "ADMIN", "STUDENT"} and all(v.startswith("$argon2") for v in h.values())
