"""Credit-Risk Cockpit — BI front-end (C1.6).

Two views over the governed marts:
  * Vintage curves   — how each origination cohort's risk develops as it ages (MOB).
  * Cohort heatmap   — lifetime default / DTI / loss by (issue cohort x credit grade).

Reads only the small aggregated marts, never the raw ~2.3M-loan table.
"""
from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

# Repo root on the path so BI reads the governed metric definitions (C2.1) — the
# single source of truth shared with the copilot — instead of redefining them here.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from queries import load_cohort_default, load_vintage_curves  # noqa: E402
from semantic import list_metrics  # noqa: E402

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


vintage_tab, cohort_tab = st.tabs(["Vintage curves", "Cohort heatmap"])

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
