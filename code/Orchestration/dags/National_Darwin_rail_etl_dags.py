from airflow import DAG
import pandas as pd
import json
import io
import uuid
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from modules.process_rail import (
    load_all_processed_csvs,
    normalize_locations,
    preprocess_for_arrival_delay,
    prepare_features,
    train_model,
    manage_and_register_best_model,
)
from modules.normalize_spark import normalize_data_spark
from airflow.decorators import task
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit
import re


# Constants — Safe at top level
BUCKET_NAME = 'darwin-raildata-mlops'
PROCESSED_PREFIX = 'darwin-kinesis-processed-rawdata'
MODEL_PREFIX = 'darwin-models'
MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"
MLFLOW_EXPERIMENT = "Xgboost-hyperopt"
TEMP_PREFIX = 'temp-data'

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2024, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=2),
}

# Define DAG
with DAG(
    dag_id='darwin_ml_training_pipeline',
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
    description="Train & register delay prediction ML model using MLflow",
) as dag:

    start = DummyOperator(task_id="start")

    def ingest_data(**kwargs):
        s3_hook = S3Hook(aws_conn_id="aws_keys")  # Keep hook
        s3_client = s3_hook.get_conn()  # boto3 client for reading
        df = load_all_processed_csvs(s3_client, BUCKET_NAME, PROCESSED_PREFIX)

        temp_key = f"{TEMP_PREFIX}/{uuid.uuid4()}.csv"
        s3_hook.load_string(  # hook method for writing
            string_data=df.to_csv(index=False),
            key=temp_key,
            bucket_name=BUCKET_NAME,
            replace=True
        )
        return temp_key


    

    ingest_task = PythonOperator(
        task_id='ingest_processed_csvs',
        python_callable=ingest_data,
    )


    def normalize_locations_task(**kwargs):
        ti = kwargs['ti']
        s3_key = ti.xcom_pull(task_ids='ingest_processed_csvs')

        s3_hook = S3Hook(aws_conn_id="aws_keys")
        s3_client = s3_hook.get_conn()

    # Read CSV from S3
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        df = pd.read_csv(obj['Body'])

    # Normalize
        normalized_df = normalize_locations(df)

    # Output paths
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S')
        parquet_key = f"{LONG_DF_PREFIX}/long_df_{timestamp}.parquet"
        csv_key = s3_key.replace(TEMP_PREFIX, "normalized-output").rsplit("/", 1)[0] + "/normalized.csv"

    # Save CSV to S3
        s3_hook.load_string(
            string_data=normalized_df.to_csv(index=False),
            key=csv_key,
            bucket_name=BUCKET_NAME,
            replace=True
        )

    # Save Parquet to S3 (write to temp local file first)
        local_parquet_path = f"/tmp/{uuid.uuid4()}.parquet"
        normalized_df.to_parquet(local_parquet_path, index=False)
        s3_hook.load_file(
            filename=local_parquet_path,
            key=parquet_key,
            bucket_name=BUCKET_NAME,
            replace=True
        )

        return {
            "csv_output": f"s3://{BUCKET_NAME}/{csv_key}",
            "parquet_output": f"s3://{BUCKET_NAME}/{parquet_key}"
        }
    
    normalize_task = PythonOperator(
        task_id='normalize_locations',
        python_callable=normalize_locations_task,
        provide_context=True
    )
       
    def preprocess_data(**kwargs):
        ti = kwargs['ti']
        df = ti.xcom_pull(task_ids='normalize_locations')
        return preprocess_for_arrival_delay(df)

    preprocess_task = PythonOperator(
        task_id='preprocess_for_delay',
        python_callable=preprocess_data,
    )

    def feature_engineering_task(**kwargs):
        ti = kwargs['ti']
        df = ti.xcom_pull(task_ids='preprocess_for_delay')
        return prepare_features(df)

    feature_task = PythonOperator(
        task_id='feature_engineering',
        python_callable=feature_engineering_task,
    )

    def train_model_task(**kwargs):
        import mlflow
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(MLFLOW_EXPERIMENT)

        ti = kwargs['ti']
        data = ti.xcom_pull(task_ids='feature_engineering')
        return train_model(*data, bucket_name=BUCKET_NAME, model_key=f"{MODEL_PREFIX}/best_model.pkl")

    train_task = PythonOperator(
        task_id='train_model',
        python_callable=train_model_task,
    )

    def register_model_task(**kwargs):
        import mlflow
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(MLFLOW_EXPERIMENT)

        return manage_and_register_best_model(
            experiment_name=MLFLOW_EXPERIMENT,
            metric_threshold=7.0,
            top_k=5,
            model_name="arrival-delay-predictor",
            stage="Production"
        )

    register_task = PythonOperator(
        task_id='register_best_model',
        python_callable=register_model_task,
    )

    end = DummyOperator(task_id="end")

    # DAG Execution Flow
    start >> ingest_task >> normalize_task >> preprocess_task >> feature_task >> train_task >> register_task >> end


 