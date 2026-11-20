"""Seed passwords per role. Development/staging/CI keep one shared demo password; a deployed demo never does.

APP_ENV=demo (public cloud): TEACHER/REVIEWER/ADMIN passwords come from SEED_TEACHER_PASSWORD, SEED_REVIEWER_PASSWORD and
SEED_ADMIN_PASSWORD (>= 12 characters, otherwise accounts are NOT created and a warning is logged). Seed students get SEED_STUDENT_PASSWORD if set, else a
random secret that is thrown away: they cannot log in with a password at all (the public demo uses anonymous guests).
"""
import os
import secrets
from collections.abc import Mapping

from argon2 import PasswordHasher

DEPLOYED = ("demo", "production", "prod")


class MissingSeedPassword(Exception):
    """A required SEED_*_PASSWORD is missing or too short. The seed scripts catch it, log a warning and skip creating
    accounts (a missing variable must never crash-loop the service); rotate_passwords.py turns it into a hard error."""
MIN_LENGTH = 12
ROLE_ENV = {"TEACHER": "SEED_TEACHER_PASSWORD", "REVIEWER": "SEED_REVIEWER_PASSWORD", "ADMIN": "SEED_ADMIN_PASSWORD"}
ROLES = ("TEACHER", "REVIEWER", "ADMIN", "STUDENT")


def is_deployed(app_env: str) -> bool:
    return app_env.lower() in DEPLOYED


def role_passwords(app_env: str, env: Mapping[str, str] | None = None) -> dict[str, str]:
    """role -> plaintext password (only ever hashed by the caller, never printed)."""
    env = os.environ if env is None else env
    if not is_deployed(app_env):
        shared = env.get("SEED_PASSWORD", "preclass-demo")
        return dict.fromkeys(ROLES, shared)
    out: dict[str, str] = {}
    for role, name in ROLE_ENV.items():
        value = env.get(name, "")
        if len(value) < MIN_LENGTH:
            raise MissingSeedPassword(f"set {name} (at least {MIN_LENGTH} characters) when APP_ENV={app_env}")
        out[role] = value
    out["STUDENT"] = env.get("SEED_STUDENT_PASSWORD") or secrets.token_urlsafe(32)
    return out


def hashes(app_env: str, env: Mapping[str, str] | None = None) -> dict[str, str]:
    """role -> argon2 hash; one hash per distinct password (argon2 is deliberately slow)."""
    hasher, cache = PasswordHasher(), {}
    out = {}
    for role, plain in role_passwords(app_env, env).items():
        if plain not in cache:
            cache[plain] = hasher.hash(plain)
        out[role] = cache[plain]
    return out
