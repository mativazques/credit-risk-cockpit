"""Governed business-plan projection — scenario scaling of the mature loss curve.

Closed-form: the anchor is the cohort-size-weighted cumulative loss curve of mature
(fully-observed) 36-month vintages (mart_projection_base). A scenario shifts the
TERMINAL loss rate by (mix_shift_bp + macro_stress_bp) basis points, floored at 0,
and scales the whole curve shape-preservingly:

    stressed_terminal = max(anchor_terminal + total_bp / 10000, 0)
    projected(mob)    = anchor(mob) * stressed_terminal / anchor_terminal

Volume growth scales the originated amount only: projected_originated =
baseline_originated * (1 + volume_growth); expected_loss = projected_originated *
stressed_terminal.

HONESTY: a scenario tool on public LendingClub curves, not a forecast of a live
book. Assumes the historical curve shape holds and the bp stress is linear at the
terminal — both stated in the UI.

The parameters are validated NUMBERS interpolated into SQL — never strings — so
there is no injection surface.
"""
from __future__ import annotations

from typing import Callable

from .errors import SemanticError

PROJECTION_MART = "mart_projection_base"

MartTable = Callable[[str], str]  # name -> `project.dataset.name`


def validate_volume_growth(volume_growth: object) -> None:
    """Origination volume growth as a fraction in [-0.5, 1.0]: 0.10 = +10% volume."""
    if (
        isinstance(volume_growth, bool)
        or not isinstance(volume_growth, (int, float))
        or not -0.5 <= volume_growth <= 1.0
    ):
        raise SemanticError(
            "volume_growth_invalid",
            f"volume growth must be a number in [-0.5, 1.0] (fraction); got {volume_growth!r}",
        )


def validate_stress_bp(value: object, name: str) -> None:
    """A basis-point stress on the terminal loss rate, in [-500, 500]."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not -500 <= value <= 500
    ):
        raise SemanticError(
            "stress_bp_invalid",
            f"{name} must be a number in [-500, 500] basis points; got {value!r}",
        )


def build_projection_sql(mix_shift_bp: float, macro_stress_bp: float, mt: MartTable) -> str:
    """Projected cumulative loss per MOB under the bp stress. Params validated by the caller."""
    total_bp = float(mix_shift_bp) + float(macro_stress_bp)
    return f"""
        select mob,
               anchor_cumulative_loss_rate
                   * safe_divide(
                         greatest(anchor_terminal_loss_rate + {total_bp} / 10000.0, 0),
                         anchor_terminal_loss_rate
                     ) as value,
               anchor_terminal_loss_rate,
               baseline_originated
        from {mt(PROJECTION_MART)}
        order by mob
    """
