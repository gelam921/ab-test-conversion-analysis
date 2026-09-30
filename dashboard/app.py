import os
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
import statsmodels.formula.api as smf
from sqlalchemy import create_engine, text
from statsmodels.stats.proportion import proportions_ztest, confint_proportions_2indep

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_URL = (
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:"
    f"{os.getenv('POSTGRES_PASSWORD')}@{DB_HOST}:5432/"
    f"{os.getenv('POSTGRES_DB')}"
)

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@st.cache_resource
def get_engine():
    return create_engine(DB_URL)


def table_exists(table_name: str, schema: str = "public") -> bool:
    with get_engine().connect() as conn:
        result = conn.execute(
            text(f"select to_regclass('{schema}.{table_name}') is not null as exists")
        )
        return bool(result.scalar())


@st.cache_data(ttl=3600)
def get_group_stats():
    query = text("""
        SELECT test_group, count(*) AS total, sum(converted::int) AS conversions
        FROM ab_test GROUP BY test_group
    """)
    with get_engine().connect() as conn:
        rows = {row.test_group: (row.conversions, row.total) for row in conn.execute(query)}
    return rows


@st.cache_data(ttl=3600)
def run_z_test(_stats):
    ad_conv, ad_total = _stats["ad"]
    psa_conv, psa_total = _stats["psa"]
    counts = np.array([ad_conv, psa_conv])
    nobs = np.array([ad_total, psa_total])
    z_stat, p_value = proportions_ztest(counts, nobs, alternative="two-sided")
    ci_low, ci_high = confint_proportions_2indep(ad_conv, ad_total, psa_conv, psa_total, method="wald")
    return {
        "ad_rate": ad_conv / ad_total,
        "psa_rate": psa_conv / psa_total,
        "z_stat": z_stat,
        "p_value": p_value,
        "ci_low": ci_low,
        "ci_high": ci_high,
    }


@st.cache_data(ttl=3600)
def run_regression():
    # Slow step (logistic regression on ~588k rows) — cached for an hour
    # since the underlying data is static.
    df = pd.read_sql("SELECT test_group, converted, total_ads FROM ab_test", get_engine())
    df["converted"] = df["converted"].astype(int)
    df["is_ad"] = (df["test_group"] == "ad").astype(int)
    model = smf.logit("converted ~ is_ad + total_ads", data=df).fit(disp=0)
    conf = model.conf_int()
    conf["coef"] = model.params
    conf.columns = ["ci_low", "ci_high", "coef"]
    odds_ratios = np.exp(conf)
    odds_ratios["p_value"] = model.pvalues
    return odds_ratios


@st.cache_data(ttl=3600)
def get_decile_data():
    query = """
        WITH ad_group_deciles AS (
            SELECT converted, total_ads, NTILE(10) OVER (ORDER BY total_ads) AS ads_decile
            FROM ab_test WHERE test_group = 'ad'
        )
        SELECT ads_decile, min(total_ads) AS min_ads, max(total_ads) AS max_ads,
               round(100.0 * sum(converted::int) / count(*), 2) AS conversion_rate_pct
        FROM ad_group_deciles GROUP BY ads_decile ORDER BY ads_decile
    """
    return pd.read_sql(query, get_engine())


@st.cache_data(ttl=3600)
def get_day_of_week_data():
    query = """
        SELECT test_group, most_ads_day,
               round(100.0 * sum(converted::int) / count(*), 2) AS conversion_rate_pct
        FROM ab_test GROUP BY test_group, most_ads_day
    """
    return pd.read_sql(query, get_engine())


st.set_page_config(page_title="A/B Test: Ads vs. PSA", layout="wide")
st.title("Marketing A/B Test: Ads vs. PSA")
st.caption("588,101 users \u00b7 statistical analysis of a real marketing experiment")

if not table_exists("ab_test"):
    st.error("No data loaded yet. Run `docker compose run --rm analysis python analysis/load_data.py` first.")
    st.stop()

stats = get_group_stats()
z = run_z_test(stats)

st.subheader("Is the effect real?")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Ad conversion rate", f"{z['ad_rate']:.2%}")
c2.metric("PSA conversion rate", f"{z['psa_rate']:.2%}")
c3.metric("Absolute lift", f"{(z['ad_rate'] - z['psa_rate'])*100:.2f} pts")
c4.metric("P-value", f"{z['p_value']:.2e}")
st.success(
    f"Statistically significant (p < 0.001). 95% CI for the true lift: "
    f"[{z['ci_low']:.2%}, {z['ci_high']:.2%}]"
)

st.divider()

st.subheader("Does it hold up after controlling for ad exposure?")
with st.spinner("Fitting logistic regression on 588k rows (first load only)..."):
    odds = run_regression()
oc1, oc2 = st.columns(2)
is_ad_row = odds.loc["is_ad"]
oc1.metric(
    "Odds ratio: is_ad",
    f"{is_ad_row['coef']:.3f}",
    help=f"95% CI: [{is_ad_row['ci_low']:.2f}, {is_ad_row['ci_high']:.2f}]  \u00b7  p = {is_ad_row['p_value']:.1e}",
)
oc2.info(
    "OR > 1 and CI excludes 1 \u2192 the ad-vs-PSA effect survives controlling for "
    "total ad exposure. It's not just that the ad group saw more messaging."
)

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Conversion by ad exposure decile")
    st.caption("Correlational, not causal \u2014 exposure volume wasn't randomized")
    decile_df = get_decile_data()
    st.bar_chart(decile_df.set_index("ads_decile")["conversion_rate_pct"])

with right:
    st.subheader("Conversion rate by day of week")
    st.caption("Same pattern in both groups — likely general engagement, not an ad effect")
    day_df = get_day_of_week_data()
    chart = (
        alt.Chart(day_df)
        .mark_bar()
        .encode(
            x=alt.X("most_ads_day:N", sort=DAY_ORDER, title="Day of week"),
            y=alt.Y("conversion_rate_pct:Q", title="Conversion rate (%)"),
            color=alt.Color("test_group:N", title="Group"),
            xOffset="test_group:N",
        )
    )
    st.altair_chart(chart, use_container_width=True)

st.divider()
st.subheader("Recommendation")
st.markdown("""
Ads over PSA is well-supported \u2014 real effect, large enough to matter. Before scaling
spend, pair this with actual cost-per-ad and margin-per-conversion, since this dataset
can't speak to ROI alone. Exposure frequency (the decile chart above) is a candidate
for its own randomized experiment, not a green light to just max out ad frequency.

Full write-up with methodology: [`FINDINGS.md`](https://github.com/gelam921/ab-test-conversion-analysis/blob/main/FINDINGS.md)
""")
