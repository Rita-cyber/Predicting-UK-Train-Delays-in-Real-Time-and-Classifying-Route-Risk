import io
import os
import sys
import json
import boto3
import joblib
import boto3
import pickle
import io
import json
import numpy as np
from datetime import datetime

from hyperopt import fmin, tpe, hp, Trials, STATUS_OK
from hyperopt.pyll import scope

from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

import mlflow
import mlflow.sklearn

from awsglue.utils import getResolvedOptions

# ----------------------------
# Parse Glue job args
# ----------------------------
# Define the expected arguments
args_list = ['JOB_NAME', 'BUCKET_NAME', 'X_TRAIN_PATH', 'Y_TRAIN_PATH', 'X_VAL_PATH', 'Y_VAL_PATH','DV_PATH','BEST_PARAMS','MODEL_CLASS','MODEL_KEY']

# Retrieve the arguments
args = getResolvedOptions(sys.argv, args_list)

# Assign them to variables
job_name = args['JOB_NAME']
bucket_name = args['BUCKET_NAME']
X_train_path = args['X_TRAIN_PATH']
y_train_path = args['Y_TRAIN_PATH']
X_val_path = args['X_VAL_PATH']
y_val_path = args['Y_VAL_PATH']
dv_path = args['DV_PATH']
best_params = args['BEST_PARAMS']
model_key = args['MODEL_KEY']
model_class = args['MODEL_CLASS']
optional_setting = args.get('OPTIONAL_SETTING', 'default_value_if_not_provided')

def train_model(
    X_train_path,
    y_train_path,
    X_val_path,
    y_val_path,
    dv_path,
    model_class,
    best_params,
    bucket_name,
    model_key,
    experiment_name="Xgboost-hyperopt"
):
    s3 = boto3.client("s3")

    # --- Load datasets from S3 ---
    def load_joblib_from_s3(s3_path):
        bucket, key = s3_path.replace("s3://", "").split("/", 1)
        obj = s3.get_object(Bucket=bucket, Key=key)
        return joblib.load(io.BytesIO(obj["Body"].read()))

    X_train = load_joblib_from_s3(X_train_path)
    y_train = load_joblib_from_s3(y_train_path)
    X_val = load_joblib_from_s3(X_val_path)
    y_val = load_joblib_from_s3(y_val_path)
    dv = load_joblib_from_s3(dv_path)

    # --- Model selection ---
    model_map = {
        "RandomForest": RandomForestRegressor,
        "LinearRegression": LinearRegression,
        "XGBoost": XGBRegressor
    }
    model_cls = model_map[model_class] if isinstance(model_class, str) else model_class

    # --- MLflow setup ---
    mlflow.set_tracking_uri("http://127.0.0.1:5000")
    mlflow.set_experiment(experiment_name)
    mlflow.sklearn.autolog()

    with mlflow.start_run() as run:
        mlflow.log_param("model_class", model_cls.__name__)
        mlflow.log_params(best_params)

        model = model_cls(**best_params)
        model.fit(X_train, y_train)

        rmse = np.sqrt(mean_squared_error(y_val, model.predict(X_val)))
        mlflow.log_metric("rmse", rmse)

        run_id = run.info.run_id

    # --- Save trained model to S3 ---
    model_buffer = io.BytesIO()
    joblib.dump(model, model_buffer)
    model_buffer.seek(0)
    s3.upload_fileobj(model_buffer, bucket_name, model_key)

    # --- Save run metadata to S3 ---
    metadata = {
        "run_id": run_id,
        "rmse": rmse,
        "params": best_params,
        "timestamp": datetime.utcnow().isoformat()
    }
    s3.put_object(
        Bucket=bucket_name,
        Key=f"runs_metadata/{run_id}.json",
        Body=json.dumps(metadata)
    )

    return model, rmse, run_id
    
    
model, rmse, run_id = train_model(
    X_train_path=args['X_TRAIN'],
    y_train_path=args['Y_TRAIN'],
    X_val_path=args['X_VAL'],
    y_val_path=args['Y_VAL'],
    bucket_name=args['BUCKET_NAME'],
    best_params_prefix=args['BEST_PARAMS_PREFIX'],
    model_key = args['MODEL_KEY'],
    model_class = args['MODEL_CLASS']
)