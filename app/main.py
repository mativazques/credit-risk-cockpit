"""Credit-Risk Cockpit — front-end (C1.6 BI + C3.4 copilot chat).

Three views, all over the same governed layer:
  * Vintage curves   — how each origination cohort's risk develops as it ages (MOB).
  * Cohort heatmap   — lifetime default / DTI / loss by (issue cohort x credit grade).
  * Ask the copilot  — natural-language Q&A via the governed metrics (FastAPI /ask).

BI reads only the small aggregated marts, never the raw ~2.3M-loan table.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Repo root on the path so BI reads the governed metric definitions (C2.1) — the
# single source of truth shared with the copilot — instead of redefining them here.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chat  # noqa: E402
from queries import (  # noqa: E402
    load_cohort_default,
    load_roll_rates,
    load_vintage_backtest,
    load_vintage_curves,
)
from semantic import affordability_breach_rate, list_metrics, project_scenario  # noqa: E402

st.set_page_config(page_title="Credit-Risk Cockpit", page_icon=None, layout="wide")

st.title("Credit-Risk Cockpit")
st.caption(
    "Vintage & cohort analytics over the public LendingClub accepted-loans book "
    "(2007–2018, snapshot 2019-03). Public data — see the repo's data footer."
)

with st.expander("Governed metric definitions (semantic layer)"):
    st.caption(
        "These come from the shared semantic layer — the same definitions the copilot "
        "uses, so a metric means one thing everywhere."
    )
    st.dataframe(
        [
            {
                "Metric": m["label"],
                "Definition": m["description"],
                "Unit": m["unit"],
                "Valid windows": ", ".join(m["valid_windows"]),
            }
            for m in list_metrics()
        ],
        hide_index=True,
        use_container_width=True,
    )

VINTAGE_METRICS = {
    "Cumulative default rate": "cumulative_default_rate",
    "Cumulative loss rate": "cumulative_loss_rate",
}
COHORT_METRICS = {
    "Default rate": "default_rate",
    "Average DTI": "avg_dti",
    "Lifetime loss rate": "lifetime_loss_rate",
    "Share still current (seasoning)": "share_still_current",
}


def _fmt_pct(x: float) -> str:
    return f"{x:.1%}" if x is not None else "—"


@st.cache_data(ttl=3600)
def _breach_curve(shock: float, threshold: float) -> "pd.DataFrame":
    """Governed breach rate per cohort — same semantic function the copilot uses."""
    res = affordability_breach_rate(shock, threshold)["results"]
    return pd.DataFrame(res)


@st.cache_data(ttl=3600)
def _scenario(volume_growth: float, mix_shift_bp: float, macro_stress_bp: float) -> dict:
    """Governed projection via the semantic layer (same definition the copilot uses)."""
    return project_scenario(volume_growth, mix_shift_bp, macro_stress_bp)


vintage_tab, cohort_tab, roll_tab, afford_tab, plan_tab, chat_tab = st.tabs(
    ["Vintage curves", "Cohort heatmap", "Roll rates", "Affordability stress",
     "Business plan", "Ask the copilot"]
)

with vintage_tab:
    df = load_vintage_curves()

    left, right = st.columns([1, 3])
    with left:
        term = st.selectbox("Loan term (months)", sorted(df["term_months"].unique()))
        metric_label = st.radio("Metric", list(VINTAGE_METRICS), index=0)
        observed_only = st.checkbox(
            "Only fully-observed points", value=True,
            help="Hide right-censored MOBs where part of the cohort hasn't aged that "
                 "far by the 2019-03 snapshot.",
        )
        all_cohorts = sorted(df["issue_year_quarter"].unique())
        default_cohorts = [c for c in all_cohorts if c.startswith(("2013", "2014", "2015"))]
        cohorts = st.multiselect(
            "Cohorts", all_cohorts, default=default_cohorts or all_cohorts[:6],
        )

    metric = VINTAGE_METRICS[metric_label]
    view = df[(df["term_months"] == term) & (df["issue_year_quarter"].isin(cohorts))]
    if observed_only:
        view = view[view["fully_observed"]]

    with right:
        if view.empty:
            st.info("No data for the current selection.")
        else:
            fig = px.line(
                view, x="mob", y=metric, color="issue_year_quarter",
                labels={"mob": "Month on book", metric: metric_label,
                        "issue_year_quarter": "Cohort"},
                title=f"{metric_label} by month on book — {term}-month loans",
            )
            fig.update_yaxes(tickformat=".0%")
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Charge-off month is approximated from last_pymnt_date (±1–3 months). "
                "Right-censored points are hidden unless you uncheck the box."
            )

    st.divider()
    st.subheader("Early warning — 36-MOB backtest")
    st.caption(
        "Predicts each cohort's mature (36-MOB) cumulative default from its early "
        "(12-MOB) rate × a median seasoning multiplier learned on pre-2014 cohorts "
        "(train) and applied out-of-sample to 2014+ (holdout). A calibrated ratio on "
        "public, fully-observed cohorts — it demonstrates detection lead time, not a "
        "production model."
    )
    bdf = load_vintage_backtest()
    holdout = bdf[bdf["split"] == "holdout"]
    med_abs = float(holdout["backtest_error"].abs().median()) if not holdout.empty else None
    k1, k2 = st.columns(2)
    k1.metric(
        "Seasoning multiplier (train median)",
        f"{float(bdf['seasoning_multiplier'].iloc[0]):.2f}×" if not bdf.empty else "—",
    )
    k2.metric("Median |error| on holdout", _fmt_pct(med_abs))
    long = bdf.melt(
        id_vars=["issue_year_quarter", "split"],
        value_vars=["mature_cdr", "predicted_mature_cdr"],
        var_name="series",
        value_name="rate",
    ).replace(
        {"series": {"mature_cdr": "Actual 36-MOB", "predicted_mature_cdr": "Predicted 36-MOB"}}
    )
    fig_pv = px.line(
        long, x="issue_year_quarter", y="rate", color="series", line_dash="series",
        markers=True,
        labels={"issue_year_quarter": "Issue cohort",
                "rate": "Cumulative default at 36 MOB", "series": ""},
        title="Predicted vs actual mature default per cohort",
    )
    fig_pv.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig_pv, use_container_width=True)
    fig_err = px.bar(
        bdf, x="issue_year_quarter", y="backtest_error", color="split",
        labels={"issue_year_quarter": "Issue cohort",
                "backtest_error": "Predicted − actual", "split": "Split"},
        title="Backtest error per cohort (positive = over-predicted)",
    )
    fig_err.update_yaxes(tickformat=".1%")
    st.plotly_chart(fig_err, use_container_width=True)

with cohort_tab:
    cdf = load_cohort_default()

    total_loans = int(cdf["cohort_size"].sum())
    overall_default = (
        (cdf["default_rate"] * cdf["cohort_size"]).sum() / total_loans
        if total_loans else 0.0
    )
    k1, k2, k3 = st.columns(3)
    k1.metric("Loans in book", f"{total_loans:,}")
    k2.metric("Overall default rate", _fmt_pct(overall_default))
    k3.metric("Cohorts × grades", f"{len(cdf):,}")

    metric_label = st.selectbox("Heatmap metric", list(COHORT_METRICS))
    metric = COHORT_METRICS[metric_label]

    pivot = cdf.pivot(index="issue_year_quarter", columns="grade", values=metric)
    pivot = pivot.sort_index()

    is_pct = metric != "avg_dti"
    fig = px.imshow(
        pivot,
        labels={"x": "Credit grade", "y": "Issue cohort", "color": metric_label},
        color_continuous_scale="Reds",
        aspect="auto",
        text_auto=".1%" if is_pct else ".1f",
        title=f"{metric_label} by cohort × grade",
    )
    if is_pct:
        fig.update_coloraxes(colorbar_tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Recent cohorts (2017–2018) are still seasoning at the snapshot — their rates "
        "are floors, not final (see 'Share still current')."
    )

_BUCKET_ORDER = ["current", "dpd_30", "dpd_60", "dpd_90_plus", "charged_off", "paid"]

with roll_tab:
    rdf = load_roll_rates()
    st.subheader("Delinquency roll rates")
    st.caption(
        "Probability of moving from one DPD bucket to another the next month, per cohort. "
        "**Transitions are synthetic** — LendingClub carries only each loan's terminal "
        "status, so the 30/60/90 path is generated while the terminal state (charged-off / "
        "paid) matches the real observed outcome. Read as an illustrative transition "
        "structure, not observed servicing data."
    )
    cohort = st.selectbox("Issue cohort", sorted(rdf["issue_year_quarter"].unique()))
    view = rdf[rdf["issue_year_quarter"] == cohort]
    pivot = (
        view.pivot(index="from_bucket", columns="to_bucket", values="roll_rate")
        .reindex(index=_BUCKET_ORDER, columns=_BUCKET_ORDER)
        .fillna(0.0)
    )
    fig = px.imshow(
        pivot,
        labels={"x": "To bucket (next month)", "y": "From bucket (this month)",
                "color": "Roll rate"},
        color_continuous_scale="Reds", aspect="auto", text_auto=".1%",
        title=f"Monthly delinquency transition matrix — {cohort}",
    )
    fig.update_coloraxes(colorbar_tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

with afford_tab:
    st.subheader("Affordability stress — hypothetical income shock")
    st.caption(
        "Share of each issue cohort whose debt-to-income breaches the threshold when "
        "income drops by the chosen shock (debt held fixed: stressed DTI = "
        "DTI / (1 − shock)). **The shock is a hypothetical scenario** on "
        "origination-time DTI — an illustrative affordability stress on the public "
        "LendingClub book, not a live affordability model."
    )
    c1, c2 = st.columns(2)
    with c1:
        shock_pct = st.slider("Income shock (%)", min_value=0, max_value=30, value=10, step=1)
    with c2:
        threshold = st.number_input(
            "DTI breach threshold (percent points)", min_value=1.0, max_value=100.0,
            value=40.0, step=1.0,
        )
    shock = shock_pct / 100.0
    base = _breach_curve(0.0, float(threshold)).rename(columns={"value": "Baseline (no shock)"})
    stressed = _breach_curve(shock, float(threshold)).rename(
        columns={"value": f"Shock {shock_pct}%"}
    )
    curve = base.merge(stressed, on="cohort")
    long = curve.melt(id_vars="cohort", var_name="scenario", value_name="breach_rate")
    fig = px.line(
        long, x="cohort", y="breach_rate", color="scenario", markers=True,
        labels={"cohort": "Issue cohort", "breach_rate": f"Share with stressed DTI > {threshold:.0f}",
                "scenario": ""},
        title="DTI breach rate per cohort — baseline vs stressed",
    )
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Bucket resolution is 1 DTI point; the bucket containing the stressed cutoff "
        "counts as breaching (≤1pp conservative)."
    )

with plan_tab:
    st.subheader("Business plan — scenario projection")
    st.caption(
        "Projects the mature (fully-observed) 36-month cumulative loss curve under a "
        "scenario: volume growth scales originations; the mix-shift and macro stresses "
        "shift the terminal loss rate in basis points, scaling the curve "
        "shape-preservingly. **A hypothetical scenario tool on public-data curves, not "
        "a forecast of a live book.**"
    )
    left, right = st.columns([1, 3])
    with left:
        growth_pct = st.slider("Origination volume growth (%)", -50, 100, 10, step=5)
        mix_bp = st.slider("Credit-mix shift (bp on terminal loss)", -200, 200, 0, step=10)
        macro_bp = st.slider("Macro stress (bp on terminal loss)", -200, 200, 50, step=10)

    scenario = _scenario(growth_pct / 100.0, float(mix_bp), float(macro_bp))
    baseline = _scenario(0.0, 0.0, 0.0)

    base_df = pd.DataFrame(baseline["curve"]).rename(columns={"value": "Baseline"})
    scen_df = pd.DataFrame(scenario["curve"]).rename(columns={"value": "Scenario"})
    with right:
        curve = base_df.merge(scen_df, on="mob").melt(
            id_vars="mob", var_name="series", value_name="rate"
        )
        fig = px.line(
            curve, x="mob", y="rate", color="series",
            labels={"mob": "Month on book", "rate": "Cumulative loss rate",
                    "series": ""},
            title="Projected cumulative loss curve — baseline vs scenario",
        )
        fig.update_yaxes(tickformat=".1%")
        st.plotly_chart(fig, use_container_width=True)

    k1, k2, k3 = st.columns(3)
    k1.metric(
        "Projected origination",
        f"${scenario['projected_originated']:,.0f}",
        delta=f"{growth_pct:+d}% vs latest mature cohort",
    )
    k2.metric(
        "Terminal loss rate",
        _fmt_pct(scenario["projected_terminal_loss_rate"]),
        delta=f"{mix_bp + macro_bp:+d} bp",
        delta_color="inverse",
    )
    k3.metric("Expected lifetime loss", f"${scenario['expected_loss']:,.0f}")

    st.download_button(
        "Download scenario table (CSV)",
        base_df.merge(scen_df, on="mob").to_csv(index=False).encode("utf-8"),
        file_name="business_plan_scenario.csv",
        mime="text/csv",
    )
    st.caption(
        "Anchor: cohort-size-weighted mature 36-month vintages; volume anchor = the "
        "most recent fully-observed cohort's originated amount. Assumes the historical "
        "curve shape holds and the bp stress is linear at the terminal."
    )

with chat_tab:
    chat.render()
