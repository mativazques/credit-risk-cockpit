"""Unit tests for the semantic-layer contract (no BigQuery — pure validation logic)."""
import pytest

from semantic import SemanticError, Window, list_metrics, query_metric
from semantic.metrics import METRICS


def test_catalog_has_the_five_governed_metrics():
    ids = {m["id"] for m in list_metrics()}
    assert ids == {
        "cohort_size",
        "avg_dti",
        "default_rate",
        "cumulative_loss_rate",
        "charge_off_rate",
    }


def test_unknown_metric_is_structured_error():
    with pytest.raises(SemanticError) as exc:
        query_metric("made_up_metric")
    assert exc.value.code == "metric_unknown"
    assert "error" in exc.value.as_dict()


def test_unknown_window_is_structured_error():
    with pytest.raises(SemanticError) as exc:
        query_metric("default_rate", window="mob_0_99")
    assert exc.value.code == "window_unknown"


def test_window_not_valid_for_metric_is_rejected():
    # avg_dti is an application-time attribute: lifetime only.
    with pytest.raises(SemanticError) as exc:
        query_metric("avg_dti", window="mob_0_12")
    assert exc.value.code == "window_unsupported"


def test_charge_off_rate_rejects_short_and_lifetime_windows():
    for bad in ("mob_0_6", "lifetime"):
        with pytest.raises(SemanticError) as exc:
            query_metric("charge_off_rate", window=bad)
        assert exc.value.code == "window_unsupported"


def test_charge_off_rate_accepts_from_mob_0_12():
    m = METRICS["charge_off_rate"]
    assert m.supports(Window.MOB_0_12)
    assert m.supports(Window.MOB_0_60)


def test_windowed_metric_sql_filters_on_observed_points():
    m = METRICS["default_rate"]
    sql = m.build_sql(Window.MOB_0_12, lambda n: f"`p.d.{n}`")
    assert "mob = 12" in sql and "fully_observed" in sql


def test_default_rate_lifetime_uses_cohort_mart():
    m = METRICS["default_rate"]
    sql = m.build_sql(Window.LIFETIME, lambda n: f"`p.d.{n}`")
    assert "mart_cohort_default" in sql
