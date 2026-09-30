import os
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_URL = (
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:"
    f"{os.getenv('POSTGRES_PASSWORD')}@{DB_HOST}:5432/"
    f"{os.getenv('POSTGRES_DB')}"
)


def run_regression():
    engine = create_engine(DB_URL)
    df = pd.read_sql(
        "SELECT test_group, converted, total_ads FROM ab_test", engine
    )
    df["converted"] = df["converted"].astype(int)
    df["is_ad"] = (df["test_group"] == "ad").astype(int)

    # Logistic regression: converted ~ is_ad + total_ads
    # Controlling for total_ads lets us isolate the effect of *being
    # assigned to the ad group* from the effect of *ad exposure volume*,
    # which the decile analysis suggests may be a confound.
    model = smf.logit("converted ~ is_ad + total_ads", data=df).fit()
    print(model.summary())

    # Convert log-odds coefficients to odds ratios, which are far easier
    # to explain to a non-technical stakeholder than raw logit coefficients.
    conf = model.conf_int()
    conf["OR"] = model.params
    conf.columns = ["2.5%", "97.5%", "OR"]
    odds_ratios = np.exp(conf)

    print("\nOdds ratios (with 95% CI):")
    print(odds_ratios)


if __name__ == "__main__":
    run_regression()
