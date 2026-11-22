"""Server-side cookie sessions (D-001 #4): random token in an HttpOnly cookie, only its sha256 stored."""

import hashlib
import logging
import secrets
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import urlparse
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import models as m
from app.db.session import get_db
from app.errors import ApiError, problem

COOKIE = "preclass_session"
CSRF_HEADER = "x-preclass-csrf"
_hasher = PasswordHasher()
_DUMMY_HASH = _hasher.hash("not-a-real-password")  # equalises timing for unknown users


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def create_session(db: AsyncSession, user_id: UUID, ttl_hours: int | None = None) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(hours=ttl_hours or get_settings().session_ttl_hours)
    db.add(m.Session(token_hash=token_hash(token), user_id=user_id, expires_at=expires))
    return token


class LoginLimiter:
    """shortcut: in-process sliding window (single API process in P0), move to the DB/Redis if scaled out."""

    def __init__(self, max_failures: int = 5, window_s: int = 300,
                 message: str = "Quá nhiều lần thử, vui lòng đợi ít phút") -> None:
        self.max, self.window, self.message = max_failures, window_s, message
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str) -> deque[float]:
        q, now = self.hits[key], time.monotonic()
        while q and now - q[0] > self.window:
            q.popleft()
        return q

    def check(self, key: str, limit: int | None = None) -> None:
        if len(self._prune(key)) >= (limit or self.max):
            raise ApiError(429, "RATE_LIMITED", self.message)

    def fail(self, key: str) -> None:
        self._prune(key).append(time.monotonic())

    def reset(self, key: str | None = None) -> None:
        if key is None:
            self.hits.clear()
        else:
            self.hits.pop(key, None)


WRONG_TOO_OFTEN = "Em nhập sai nhiều lần, thử lại sau ít phút nhé."
# Per account, never per IP: a classroom shares one Wi-Fi address (NAT).
login_limiter = LoginLimiter(message=WRONG_TOO_OFTEN)
# ADMIN accounts: 3 wrong passwords / 15 min
admin_login_limiter = LoginLimiter(max_failures=3, window_s=900, message=WRONG_TOO_OFTEN)


class CurrentUser:
    def __init__(self, user: m.AppUser, session: m.Session) -> None:
        self.user, self.session = user, session

    @property
    def id(self) -> UUID:
        return self.user.id

    @property
    def role(self) -> str:
        return self.user.role


async def current_user(request: Request, db: Annotated[AsyncSession, Depends(get_db)]) -> CurrentUser:
    token = request.cookies.get(COOKIE)
    if token:
        row = (
            await db.execute(
                select(m.Session, m.AppUser)
                .join(m.AppUser, m.AppUser.id == m.Session.user_id)
                .where(
                    m.Session.token_hash == token_hash(token),
                    m.Session.revoked_at.is_(None),
                    m.Session.expires_at > datetime.now(UTC),
                    m.AppUser.is_active.is_(True),
                )
            )
        ).first()
        if row:
            user = row[1]
            now = datetime.now(UTC)
            if user.is_guest and (user.last_seen_at is None or now - user.last_seen_at > timedelta(hours=1)):
                user.last_seen_at = now  # hourly: enough for "inactive for N days" purging
                await db.commit()
            return CurrentUser(user, row[0])
    raise ApiError(401, "UNAUTHENTICATED", "Chưa đăng nhập hoặc phiên đã hết hạn")


def require_role(*roles: str):  # type: ignore[no-untyped-def]
    """Dependency factory: wrong role → 403 FORBIDDEN_ROLE (not 404: the route exists for everyone)."""

    async def dep(user: Annotated[CurrentUser, Depends(current_user)]) -> CurrentUser:
        if user.role not in roles:
            raise ApiError(403, "FORBIDDEN_ROLE", "Không có quyền thực hiện thao tác này")
        return user

    return dep


async def csrf_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Cookie auth ⇒ CSRF defence: custom header on every non-GET plus an Origin check (D-001 #4)."""
    if request.method not in ("GET", "HEAD", "OPTIONS") and request.url.path.startswith("/v1/"):
        origin = request.headers.get("origin")
        origin_ok = (
            origin is None
            or origin == get_settings().frontend_origin
            or urlparse(origin).netloc == request.headers.get("host")
        )
        if request.headers.get(CSRF_HEADER) != "1" or not origin_ok:
            # No cookies/tokens: only what is needed to see why (usually FRONTEND_ORIGIN mismatch).
            logging.getLogger("preclass.csrf").warning(
                "CSRF rejected: %s %s origin=%r host=%r header=%r expected=%r", request.method, request.url.path,
                origin, request.headers.get("host"), request.headers.get(CSRF_HEADER), get_settings().frontend_origin)
            return problem(403, "CSRF", "Yêu cầu bị từ chối (CSRF)")
    return await call_next(request)
