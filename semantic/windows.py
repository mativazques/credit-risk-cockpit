"""The `window` enum contract.

A window scopes a metric to a maximum month-on-book (MOB). `lifetime` means "to the
2019-03 snapshot, no MOB cap". This enum is the single vocabulary the BI layer and the
copilot both speak; an unknown window is a contract violation, not a silent fallback.
"""
from __future__ import annotations

from enum import Enum


class Window(str, Enum):
    MOB_0_6 = "mob_0_6"
    MOB_0_12 = "mob_0_12"
    MOB_0_24 = "mob_0_24"
    MOB_0_36 = "mob_0_36"
    MOB_0_60 = "mob_0_60"
    LIFETIME = "lifetime"


# MOB cap per window; None = lifetime (no cap).
WINDOW_MOB: dict[Window, int | None] = {
    Window.MOB_0_6: 6,
    Window.MOB_0_12: 12,
    Window.MOB_0_24: 24,
    Window.MOB_0_36: 36,
    Window.MOB_0_60: 60,
    Window.LIFETIME: None,
}


def parse_window(value: str | Window) -> Window:
    """Coerce a string to a Window, raising KeyError-free ValueError on a bad value."""
    if isinstance(value, Window):
        return value
    try:
        return Window(value)
    except ValueError as exc:
        raise ValueError(
            f"unknown window '{value}'; allowed: {[w.value for w in Window]}"
        ) from exc
