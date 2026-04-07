"""Simple in-memory rate limiter for guest users on Streamlit Cloud."""

import time
from collections import defaultdict

_REQUEST_LOG: dict[str, list[float]] = defaultdict(list)

MAX_REQUESTS = 20
WINDOW_SECONDS = 3600  # 1 hour


def check_rate_limit(session_id: str) -> bool:
    """Return True if the request is allowed, False if rate-limited."""
    now = time.time()
    log = _REQUEST_LOG[session_id]
    # Prune old entries
    _REQUEST_LOG[session_id] = [t for t in log if now - t < WINDOW_SECONDS]
    if len(_REQUEST_LOG[session_id]) >= MAX_REQUESTS:
        return False
    _REQUEST_LOG[session_id].append(now)
    return True


def remaining(session_id: str) -> int:
    now = time.time()
    log = _REQUEST_LOG.get(session_id, [])
    active = [t for t in log if now - t < WINDOW_SECONDS]
    return max(0, MAX_REQUESTS - len(active))
