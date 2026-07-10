import time
from collections import defaultdict

import bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

SESSION_COOKIE_NAME = "sitewatch_session"
SESSION_MAX_AGE_SECONDS = 7 * 24 * 3600

_serializer = URLSafeTimedSerializer(settings.session_secret, salt="sitewatch-session")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_session_cookie(user_id: int) -> str:
    return _serializer.dumps({"user_id": user_id})


def read_session_cookie(cookie_value: str) -> int | None:
    try:
        data = _serializer.loads(cookie_value, max_age=SESSION_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    return data.get("user_id")


class LoginRateLimiter:
    """In-memory sliding-window limiter. Single-process deployment, so no shared store needed."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def is_blocked(self, key: str) -> bool:
        self._prune(key)
        return len(self._attempts[key]) >= self.max_attempts

    def record_failure(self, key: str) -> None:
        self._prune(key)
        self._attempts[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)

    def _prune(self, key: str) -> None:
        cutoff = time.monotonic() - self.window_seconds
        self._attempts[key] = [t for t in self._attempts[key] if t > cutoff]


login_rate_limiter = LoginRateLimiter()
