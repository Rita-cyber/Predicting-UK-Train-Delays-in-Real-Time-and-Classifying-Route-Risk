import datetime
import time
import random
import logging 
import uuid
import pytz
import pandas as pd
import io
import psycopg
import joblib

from prefect import task, flow

from evidently.report import Report
from evidently import ColumnMapping
from evidently.metrics import ColumnDriftMetric, DatasetDriftMetric, DatasetMissingValuesMetric

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")

SEND_TIMEOUT = 10
rand = random.Random()

create_table_statement = '''
drop table if exists raildata_metrics;
create table raildata_metrics(
	timestamp timestamp,
	prediction_drift float,
	num_drifted_columns integer,
	share_missing_values float
)
'''

reference_data = pd.read_parquet('data/reference.parquet')
with open('models/xgboost.bin', 'rb') as f_in:
	model = joblib.load(f_in)

raw_data = pd.read_parquet('data/wide-to-long-transformation.parquet')

begin = datetime.datetime(2025, 7, 22, 0, 0)
cat_features = ["day_of_week", "Pport_uR_TS_Location_@tpl"]
column_mapping = ColumnMapping(
    prediction='prediction',
    categorical_features=cat_features,
    target=None
)

report = Report(metrics = [
    ColumnDriftMetric(column_name='prediction'),
    DatasetDriftMetric(),
    DatasetMissingValuesMetric()
])

@task
def prep_db():
	with psycopg.connect("host=localhost port=5433 user=postgres password=darwin", autocommit=True) as conn:
		res = conn.execute("SELECT 1 FROM pg_database WHERE datname='test'")
		if len(res.fetchall()) == 0:
			conn.execute("create database test;")
		with psycopg.connect("host=localhost port=5433 dbname=test user=postgres password=darwin") as conn:
			conn.execute(create_table_statement)

@task
def calculate_metrics_postgresql(curr, i):
    """
    Calculate drift metrics for a given time window and insert into PostgreSQL.
    """

    # Ensure datetime conversion is done
    raw_data["Pport_uR_TS_@ssd"] = pd.to_datetime(
        raw_data["Pport_uR_TS_@ssd"], errors="coerce"
    )

    # Filter data for this day/hour depending on i
    current_data = raw_data[
        (raw_data["Pport_uR_TS_@ssd"] >= (begin + datetime.timedelta(i))) &
        (raw_data["Pport_uR_TS_@ssd"] < (begin + datetime.timedelta(i + 1)))
    ].copy()

    # Handle missing values before prediction
    current_data["prediction"] = model.predict(
        current_data[cat_features].fillna(0)
    )

    # Run Evidently report
    report.run(
        reference_data=reference_data,
        current_data=current_data,
        column_mapping=column_mapping
    )
    result = report.as_dict()

    prediction_drift = result["metrics"][0]["result"]["drift_score"]
    num_drifted_columns = result["metrics"][1]["result"]["number_of_drifted_columns"]
    share_missing_values = result["metrics"][2]["result"]["current"]["share_of_missing_values"]

    # Insert into PostgreSQL
    curr.execute(
        """
        INSERT INTO raildata_metrics(timestamp, prediction_drift, num_drifted_columns, share_missing_values) 
        VALUES (%s, %s, %s, %s)
        """,
        (begin + datetime.timedelta(i), prediction_drift, num_drifted_columns, share_missing_values)
    )

@flow
def batch_monitoring_backfill():
	prep_db()
	last_send = datetime.datetime.now() - datetime.timedelta(seconds=10)
	with psycopg.connect("host=localhost port=5433 dbname=test user=postgres password=darwin", autocommit=True) as conn:
		for i in range(0, 1):
			with conn.cursor() as curr:
				calculate_metrics_postgresql(curr, i)

			new_send = datetime.datetime.now()
			seconds_elapsed = (new_send - last_send).total_seconds()
			if seconds_elapsed < SEND_TIMEOUT:
				time.sleep(SEND_TIMEOUT - seconds_elapsed)
			while last_send < new_send:
				last_send = last_send + datetime.timedelta(seconds=10)
			logging.info("data sent")

if __name__ == '__main__':
	batch_monitoring_backfill()