
import pandas as pd
import re
import io
import pyarrow
import pyarrow.parquet as pq
from datetime import datetime
import tempfile
import joblib
import pickle
from mlflow.tracking import MlflowClient
from mlflow.entities import ViewType
from datetime import datetime
import mlflow
import boto3
import pickle
import os
import mlflow.sklearn
from sklearn.metrics import mean_squared_error
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from hyperopt import fmin, tpe, hp, STATUS_OK, Trials
from hyperopt.pyll import scope
import numpy as np
import warnings
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import LabelEncoder
from modules.process_rail_data import (
    load_all_processed_csvs,
    normalize_locations,
    preprocess_for_arrival_delay,
    prepare_features,
    find_best_model_params,
    train_model,
    manage_and_register_best_model
)


mlflow.set_tracking_uri("http://127.0.0.1:5000")
mlflow.set_experiment("Xgboost-hyperopt")
warnings.filterwarnings("ignore")

# Constant
BUCKET_NAME = 'darwin-raildata-mlops'
PROCESSED_PREFIX = 'darwin-kinesis-processed-rawdata'
LONG_DF_PREFIX = 'darwin-long-format-data'
MODEL_PREFIX = 'darwin-models'

s3 = boto3.client('s3')


PROCESSED_KEYS_FILE = "tracking/processed_keys.json"



def main():
    print("Loading CSVs...")
    full_df = load_all_processed_csvs(BUCKET_NAME, PROCESSED_PREFIX)
    if full_df.empty:
        print("No data after merge.")
        return

    print("Normalizing locations...")
    long_df = normalize_locations(full_df)

    print("Cleaning data...")
    long_df = preprocess_for_arrival_delay(long_df)

    # Save long_df to Parquet
    long_df_filename = f"{LONG_DF_PREFIX}/long_df_{datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S')}.parquet"
    parquet_buffer = io.BytesIO()
    long_df.to_parquet(parquet_buffer, engine='pyarrow', index=False)
    s3.put_object(Bucket=BUCKET_NAME, Key=long_df_filename, Body=parquet_buffer.getvalue())
    print(f"✅ Saved long_df to {long_df_filename}")

    # Prepare features
    print("Preparing features...")
    X_train, y_train, X_val, y_val, dv = prepare_features(long_df)

    if X_train.shape[0] == 0:
        print("❌ No data for model training.")
        return

    best_model, best_params, best_rmse = find_best_model_params(X_train, y_train, X_val, y_val)

    try:
        print("Training model...")
        model_class_map = {
            "RandomForest": RandomForestRegressor,
            "LinearRegression": LinearRegression,
            "XGBoost": XGBRegressor
        }

        model, rmse, run_id = train_model(
            X_train, y_train, X_val, y_val,
            model_class=model_class_map[best_model],
            best_params=best_params,
            bucket_name=BUCKET_NAME,
            model_key='models/best_model.pkl',
            dv=dv
        )

        run_id = manage_and_register_best_model(
            experiment_name="Xgboost-hyperopt",
            metric_threshold=7.0,
            top_k=5,
            model_name="arrival-delay-predictor",
            stage="Production"
        )

    except Exception as e:
        print(f"❌ Error during training or model registration: {e}")

    print("✅ Pipeline completed successfully.")

if __name__ == "__main__":
    main()