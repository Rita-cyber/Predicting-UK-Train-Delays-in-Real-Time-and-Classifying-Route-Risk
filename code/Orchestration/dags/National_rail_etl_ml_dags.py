
from airflow import DAG
import pandas as pd
import json
import io
import uuid
from airflow.operators.dummy import DummyOperator
#from airflow.providers.amazon.aws.operators.ecs import ECSOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.decorators import task
import re


# Constants — Safe at top level
BUCKET_NAME = 'darwin-raildata-mlops'
PROCESSED_PREFIX = 'darwin-kinesis-processed-rawdata'
MODEL_PREFIX = 'darwin-models'
MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"
MLFLOW_EXPERIMENT = "Xgboost-hyperopt"
TEMP_PREFIX = 'temp-data'


AWS_CONN_ID = "aws_keys"          # or your conn ID
REGION_NAME = "eu-north-1"
CLUSTER = "my-ecs-cluster"
TASK_DEF = "darwin-producer-task"
SUBNETS = ["subnet-xxxxxxxx", "subnet-yyyyyyyy"]
SECURITY_GROUPS = ["sg-zzzzzzzz"]

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2024, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=2),
}

# Define DAG
with DAG(
    dag_id='darwin_etl_ml_pipeline',
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
    description="Train & register delay prediction ML model using MLflow",
) as dag:

    start = DummyOperator(task_id="start")


    ingest_data = GlueJobOperator(
    task_id="ingest_data_task",
    job_name="ingest_data_job",
    script_location="s3://darwin-raildata-mlops/scripts/Ingestion.py",
    script_args={
        "--prefix": f"{PROCESSED_PREFIX}/",        # just prefix inside bucket
        "--output_key": f"{TEMP_PREFIX}/combined.csv",  # path + filename inside bucket
        "--bucket": BUCKET_NAME,                    # bucket name only
        "--output_bucket": BUCKET_NAME              # bucket name only
    },
    iam_role_name="AWS-Glue-S3",  # Removed trailing space here
    region_name="eu-north-1",
    aws_conn_id="aws_keys"
    )

    
    transform_data = GlueJobOperator(
    task_id="transform_spark_data_task",
    job_name="transform_spark_data_job",
    script_location="s3://darwin-raildata-mlops/scripts/transformed_spark.py",
    script_args={
        "--input_path": "s3://darwin-raildata-mlops/temp-data/combined.csv",
        "--output_path": "s3://darwin-raildata-mlops/wide-to-long-transformation/"
    },
    iam_role_name="AWS-Glue-S3",  # Removed trailing space here
    region_name="eu-north-1",
    aws_conn_id="aws_keys"
    )
       
    preprocess_data = GlueJobOperator(
    task_id="preprocess_data_task",
    job_name="preprocess_data_job",
    script_location="s3://darwin-raildata-mlops/scripts/preprocess_data.py",
    script_args={
        "--input_path": "s3://darwin-raildata-mlops/wide-to-long-transformation/",
        "--output_path":  "s3://darwin-raildata-mlops/transformed-data/preprocessed-features-data/"
    },
    iam_role_name="AWS-Glue-S3",  # Removed trailing space here
    region_name="eu-north-1",
    aws_conn_id="aws_keys"
    )

    feature_engineering = GlueJobOperator(
    task_id="feature-engineering_task",
    job_name="feature-engineering_job",
    script_location="s3://darwin-raildata-mlops/scripts/feature_engineering.py",
    script_args={
        "--input_path": "s3://darwin-raildata-mlops/transformed-data/preprocessed-features-data/",
        "--output_path": "s3://darwin-raildata-mlops/feature-eng-data/"
    },
    iam_role_name="AWS-Glue-S3",  # Removed trailing space here
    region_name="eu-north-1",
    aws_conn_id="aws_keys"
    )

    find_best_model_params = GlueJobOperator(
    task_id="find_best_model_params_task",
    job_name="find_best_model_params_job",
    script_location="s3://darwin-raildata-mlops/scripts/find_best_model_params.py",
    script_args={
        "--X_train_path": "s3://darwin-raildata-mlops/feature-eng-data/X_train.joblib",
        "--y_train_path": "s3://darwin-raildata-mlops/feature-eng-data/y_train.joblib",
        "--X_val_path": "s3://darwin-raildata-mlops/feature-eng-data/X_val.joblib",
        "--y_val_path":"s3://darwin-raildata-mlops/feature-eng-data/y_val.joblib",
        "--dv_path": "s3://darwin-raildata-mlops/feature-eng-data/dict_vectorizer.joblib",
        "--bucket_name": "darwin-raildata-mlops",
        "--best_params_prefix": "best_params/"
    },
    iam_role_name="AWS-Glue-S3",  # Removed trailing space here
    region_name="eu-north-1",
    aws_conn_id="aws_keys"
    )


    train_model = GlueJobOperator(
    task_id="train_model_task",
    job_name="train_model_job",
    script_location="s3://darwin-raildata-mlops/scripts/train_model.py",
    script_args={
        "--X_train_path": "s3://darwin-raildata-mlops/feature-eng-data/X_train.joblib",
        "--y_train_path": "s3://darwin-raildata-mlops/feature-eng-data/y_train.joblib",
        "--X_val_path": "s3://darwin-raildata-mlops/feature-eng-data/X_val.joblib",
        "--y_val_path":"s3://darwin-raildata-mlops/feature-eng-data/y_val.joblib",
        "--dv_path": "s3://darwin-raildata-mlops/feature-eng-data/dict_vectorizer.joblib",
        "--bucket_name": "darwin-raildata-mlops",
        "--model_class": "XGBoost",
        "--model_key": "models/best_model.pkl",
        "--best_params": "best_params/"
    },
    iam_role_name="AWS-Glue-S3",  # Removed trailing space here
    region_name="eu-north-1",
    aws_conn_id="aws_keys"
    )


    register_model = GlueJobOperator(
    task_id="register_model",
    job_name="register_model_job",
    script_location="s3://darwin-raildata-mlops/scripts/register_model.py",
    script_args = {
        "--experiment_name": "Xgboost-hyperopt",
        "--metric_threshold": "7.0",   # Glue args are strings; cast later in script
        "--top_k": "5",
        "--model_name": "arrival-delay-predictor"
    },
    iam_role_name="AWS-Glue-S3",  # Removed trailing space here
    region_name="eu-north-1",
    aws_conn_id="aws_keys"
    )
    end = DummyOperator(task_id="end")

    # DAG Execution Flow
    start >> ingest_data>> transform_data >> preprocess_data >> feature_engineering >> find_best_model_params >> train_model >> register_model >> end


