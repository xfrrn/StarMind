"""Datetime utility functions."""

from datetime import datetime, timezone


def parse_iso_to_naive_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)
    except (ValueError, AttributeError):
        return None


def format_relative_time(dt: datetime | None) -> str:
    if not dt:
        return "Unknown"

    now = datetime.now(timezone.utc) if dt.tzinfo else datetime.utcnow()
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return f"{seconds} seconds ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} mins ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hours ago"
    days = hours // 24
    if days < 30:
        return f"{days} days ago"
    return dt.strftime("%Y-%m-%d")


def format_last_sync_time(last_sync_at: datetime | None) -> str | None:
    if not last_sync_at:
        return None

    diff = datetime.utcnow() - last_sync_at
    hours = int(diff.total_seconds() / 3600)
    if hours < 1:
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes}m ago"
    if hours < 24:
        return f"{hours}h ago"
    return last_sync_at.strftime("%Y-%m-%d %H:%M")
