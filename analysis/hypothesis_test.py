import os
import numpy as np
from sqlalchemy import create_engine, text
from statsmodels.stats.proportion import proportions_ztest, confint_proportions_2indep
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_URL = (
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:"
    f"{os.getenv('POSTGRES_PASSWORD')}@{DB_HOST}:5432/"
    f"{os.getenv('POSTGRES_DB')}"
)


def get_group_stats():
    engine = create_engine(DB_URL)
    query = text("""
        SELECT test_group,
               count(*) AS total,
               sum(converted::int) AS conversions
        FROM ab_test
        GROUP BY test_group
    """)
    with engine.connect() as conn:
        return {row.test_group: (row.conversions, row.total) for row in conn.execute(query)}


def run_test():
    stats = get_group_stats()
    ad_conversions, ad_total = stats["ad"]
    psa_conversions, psa_total = stats["psa"]

    ad_rate = ad_conversions / ad_total
    psa_rate = psa_conversions / psa_total
    lift = ad_rate - psa_rate
    relative_lift = lift / psa_rate * 100

    print(f"Ad group:  {ad_conversions:,} / {ad_total:,} = {ad_rate:.4%}")
    print(f"PSA group: {psa_conversions:,} / {psa_total:,} = {psa_rate:.4%}")
    print(f"Absolute lift: {lift*100:.3f} percentage points")
    print(f"Relative lift: {relative_lift:.1f}%")

    # Two-proportion z-test
    counts = np.array([ad_conversions, psa_conversions])
    nobs = np.array([ad_total, psa_total])
    z_stat, p_value = proportions_ztest(counts, nobs, alternative="two-sided")

    print(f"\nZ-statistic: {z_stat:.3f}")
    print(f"P-value: {p_value:.2e}")

    # 95% confidence interval for the difference in conversion rates
    ci_low, ci_high = confint_proportions_2indep(
        ad_conversions, ad_total, psa_conversions, psa_total, method="wald"
    )
    print(f"95% CI for difference in conversion rate: [{ci_low:.4%}, {ci_high:.4%}]")

    alpha = 0.05
    verdict = "statistically significant" if p_value < alpha else "not statistically significant"
    print(f"\nResult at alpha=0.05: {verdict}")


if __name__ == "__main__":
    run_test()
