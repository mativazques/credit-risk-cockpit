"""Unit tests for the semantic-layer contract (no BigQuery — pure validation logic)."""
import pytest

from semantic import SemanticError, Window, list_metrics, query_metric
from semantic.metrics import METRICS


def test_catalog_has_the_seven_governed_metrics():
    ids = {m["id"] for m in list_metrics()}
    assert ids == {
        "cohort_size",
        "avg_dti",
        "default_rate",
        "cumulative_loss_rate",
        "charge_off_rate",
        "predicted_default_rate",
        "backtest_error",
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


# --- roll rates (Phase A) ---------------------------------------------------------
from semantic.roll import ROLL_BUCKETS, build_roll_rate_sql, validate_bucket


def test_roll_buckets_are_the_canonical_six():
    assert ROLL_BUCKETS == (
        "current", "dpd_30", "dpd_60", "dpd_90_plus", "charged_off", "paid",
    )


def test_validate_bucket_rejects_unknown():
    with pytest.raises(SemanticError) as exc:
        validate_bucket("dpd_120")
    assert exc.value.code == "bucket_unknown"


def test_roll_rate_sql_targets_the_mart_and_filters_both_buckets():
    sql = build_roll_rate_sql("current", "dpd_30", lambda n: f"`p.d.{n}`")
    assert "mart_roll_rates" in sql
    assert "from_bucket = 'current'" in sql
    assert "to_bucket = 'dpd_30'" in sql
    assert "issue_year_quarter" in sql and "value" in sql


def test_roll_rate_rejects_unknown_bucket_before_touching_bq():
    from semantic import roll_rate
    with pytest.raises(SemanticError) as exc:
        roll_rate("current", "dpd_999")
    assert exc.value.code == "bucket_unknown"


def test_roll_rate_is_exported_from_semantic_package():
    import semantic
    assert hasattr(semantic, "roll_rate")


# --- early-warning backtest (Phase B) ---------------------------------------------


def test_backtest_metrics_read_the_backtest_mart():
    for metric_id in ("predicted_default_rate", "backtest_error"):
        m = METRICS[metric_id]
        sql = m.build_sql(Window.MOB_0_36, lambda n: f"`p.d.{n}`")
        assert "mart_vintage_backtest" in sql


def test_backtest_metrics_are_mob_36_only():
    for metric_id in ("predicted_default_rate", "backtest_error"):
        with pytest.raises(SemanticError) as exc:
            query_metric(metric_id, window="lifetime")
        assert exc.value.code == "window_unsupported"


# --- affordability stress (Phase C) -----------------------------------------------
from semantic.affordability import (
    build_breach_rate_sql,
    validate_shock,
    validate_threshold,
)


def test_shock_outside_unit_interval_is_structured_error():
    for bad in (-0.1, 1.0, 1.5, "0.1", None, True):
        with pytest.raises(SemanticError) as exc:
            validate_shock(bad)
        assert exc.value.code == "shock_invalid"
    validate_shock(0)      # baseline (no shock) is legal
    validate_shock(0.30)   # 30% income drop is legal


def test_threshold_outside_percent_scale_is_structured_error():
    for bad in (0, -5, 101, "40", None, False):
        with pytest.raises(SemanticError) as exc:
            validate_threshold(bad)
        assert exc.value.code == "threshold_invalid"
    validate_threshold(40)     # DTI 40 percent points is legal
    validate_threshold(100)    # inclusive upper bound


def test_breach_sql_applies_the_closed_form_cutoff():
    # threshold 40, shock 10% -> cutoff = 40 * (1 - 0.10) = 36.0 on the original dti
    sql = build_breach_rate_sql(0.10, 40.0, lambda n: f"`p.d.{n}`")
    assert "mart_dti_histogram" in sql
    assert "36.0" in sql
    assert "issue_year_quarter" in sql and "value" in sql


def test_affordability_rejects_bad_params_before_touching_bq():
    from semantic import affordability_breach_rate

    with pytest.raises(SemanticError) as exc:
        affordability_breach_rate(1.2, 40.0)
    assert exc.value.code == "shock_invalid"
    with pytest.raises(SemanticError) as exc:
        affordability_breach_rate(0.1, 0)
    assert exc.value.code == "threshold_invalid"


def test_affordability_is_exported_from_semantic_package():
    import semantic

    assert callable(semantic.affordability_breach_rate)


# --- business-plan projection (Phase D) --------------------------------------------
from semantic.projection import (
    build_projection_sql,
    validate_stress_bp,
    validate_volume_growth,
)


def test_volume_growth_outside_band_is_structured_error():
    with pytest.raises(SemanticError) as e:
        validate_volume_growth(1.5)
    assert e.value.code == "volume_growth_invalid"
    with pytest.raises(SemanticError):
        validate_volume_growth(True)


def test_stress_bp_outside_band_is_structured_error():
    with pytest.raises(SemanticError) as e:
        validate_stress_bp(900, "macro_stress_bp")
    assert e.value.code == "stress_bp_invalid"
    assert "macro_stress_bp" in e.value.message


def test_projection_sql_applies_total_bp_shift():
    sql = build_projection_sql(20, 30, lambda n: f"p.d.{n}")
    assert "50.0 / 10000.0" in sql
    assert "p.d.mart_projection_base" in sql
    assert "greatest(" in sql


def test_projection_rejects_bad_params_before_touching_bq():
    from semantic import project_scenario

    with pytest.raises(SemanticError):
        project_scenario(5.0, 0, 0)
    with pytest.raises(SemanticError):
        project_scenario(0.1, 9999, 0)


def test_projection_is_exported_from_semantic_package():
    import semantic

    assert callable(semantic.project_scenario)
