import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_URL = (
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:"
    f"{os.getenv('POSTGRES_PASSWORD')}@{DB_HOST}:5432/"
    f"{os.getenv('POSTGRES_DB')}"
)


def load_ab_test_data():
    df = pd.read_csv("/app/data/marketing_AB.csv", index_col=0)
    df.columns = [
        "user_id",
        "test_group",
        "converted",
        "total_ads",
        "most_ads_day",
        "most_ads_hour",
    ]

    engine = create_engine(DB_URL)
    df.to_sql("ab_test", engine, schema="public", if_exists="replace", index=False)
    print(f"Loaded {len(df):,} rows into ab_test")
    print(df["test_group"].value_counts())


if __name__ == "__main__":
    load_ab_test_data()
