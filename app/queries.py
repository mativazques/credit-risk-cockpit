"""Cached read access to the marts.

Every query is wrapped in `@st.cache_data(ttl=3600)`: the dataset is static, so a
1-hour cache eliminates repeated BigQuery scans (and the on-demand charges that come
with them) while a user explores the cockpit — the $0-cost control from the blueprint.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import get_client, marts_table

_TTL = 3600


@st.cache_data(ttl=_TTL)
def load_vintage_curves() -> pd.DataFrame:
    sql = f"""
        select
            issue_year_quarter,
            term_months,
            mob,
            cohort_size,
            cumulative_default_rate,
            cumulative_loss_rate,
            fully_observed
        from {marts_table('mart_vintage_curves')}
        order by issue_year_quarter, term_months, mob
    """
    return get_client().query(sql).to_dataframe()


@st.cache_data(ttl=_TTL)
def load_cohort_default() -> pd.DataFrame:
    sql = f"""
        select
            issue_year_quarter,
            grade,
            cohort_size,
            default_rate,
            share_still_current,
            avg_dti,
            originated_amount,
            lifetime_loss_rate
        from {marts_table('mart_cohort_default')}
        order by issue_year_quarter, grade
    """
    return get_client().query(sql).to_dataframe()


@st.cache_data(ttl=_TTL)
def load_roll_rates() -> pd.DataFrame:
    """Per-cohort delinquency roll-rate matrix (synthetic path — see the mart's docstring)."""
    sql = f"""
        select
            issue_year_quarter,
            from_bucket,
            to_bucket,
            roll_rate
        from {marts_table('mart_roll_rates')}
        order by issue_year_quarter, from_bucket, to_bucket
    """
    return get_client().query(sql).to_dataframe()
