"""
core/subscription.py
────────────────────
Centralised helpers for subscription / free-tier logic.

Rules
-----
* A user is "Pro" if their `subscription_status == 'active'` AND
  (subscription_end_date is None OR subscription_end_date > now).
* Free users are limited to FREE_MONTHLY_LIMIT complete analyses per
  calendar month.  The counter resets on the 1st of each month (UTC).
* The counter is stored on the User row so that it survives server restarts
  and cannot be bypassed by clearing cookies.
"""

from datetime import datetime, timezone
from typing import Optional

FREE_MONTHLY_LIMIT = 4


# ── Tier helpers ─────────────────────────────────────────────────────────────

def is_pro(user) -> bool:
    """Return True if *user* has an active paid subscription."""
    if user is None:
        return False
    if user.subscription_status != "active":
        return False
    # Grace: no end date means perpetual (e.g. manually granted)
    if user.subscription_end_date is None:
        return True
    return user.subscription_end_date > datetime.now(timezone.utc).replace(tzinfo=None)


# ── Free-tier counter ─────────────────────────────────────────────────────────

def _month_start(dt: datetime) -> datetime:
    """Return midnight UTC on the 1st of *dt*'s month."""
    return datetime(dt.year, dt.month, 1, 0, 0, 0)


def reset_if_new_month(user, db) -> None:
    """
    If the stored reset date is from a previous month, zero the counter and
    set reset_at to the 1st of the current month.  Commits the change.
    Called once per request for free users — cheap (1 row read, occasional write).
    """
    now = datetime.utcnow()
    current_month_start = _month_start(now)

    needs_reset = (
        user.free_analyses_reset_at is None
        or user.free_analyses_reset_at < current_month_start
    )

    if needs_reset:
        user.free_analyses_used = 0
        user.free_analyses_reset_at = current_month_start
        db.add(user)
        db.commit()
        db.refresh(user)


def get_remaining_analyses(user, db) -> int:
    """
    Return how many free analyses the user still has this month.
    Resets the counter if the month rolled over.
    Returns FREE_MONTHLY_LIMIT for pro users (effectively unlimited).
    """
    if is_pro(user):
        return FREE_MONTHLY_LIMIT  # doesn't matter — they see everything

    reset_if_new_month(user, db)
    remaining = max(0, FREE_MONTHLY_LIMIT - user.free_analyses_used)
    return remaining


def censor_match(match: dict) -> dict:
    """
    Strip sensitive prediction data from a match dict for locked (free-tier)
    users. Returns a shallow copy with the sensitive fields removed/nulled
    and `locked` set to True.

    The frontend receives only enough data to render the match header
    (teams, date) and the lock overlay.
    """
    return {
        "id": match.get("id"),
        "date": match.get("date"),
        "homeTeam": match.get("homeTeam"),
        "awayTeam": match.get("awayTeam"),
        "sport": match.get("sport"),
        "locked": True,
        # Deliberately omit: bestPick, topPicks, justification,
        # allCandidates, all_bookmakers, isSteam, etc.
    }
