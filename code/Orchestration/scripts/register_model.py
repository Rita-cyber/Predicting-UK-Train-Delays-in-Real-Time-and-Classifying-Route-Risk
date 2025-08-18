import boto3
import pandas as pd
import re
import io
import pyarrow
import pyarrow.parquet as pq
from datetime import datetime
import tempfile
import joblib
import numpy as np
import mlflow
import pickle
import os
from mlflow.tracking import MlflowClient
from mlflow.entities import ViewType
from datetime import datetime
import mlflow.sklearn
from mlflow.tracking import MlflowClient
from mlflow.entities import ViewType
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import mean_squared_error
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from hyperopt import fmin, tpe, hp, STATUS_OK, Trials
from hyperopt.pyll import scope
import json
import warnings
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import LabelEncoder

mlflow.set_tracking_uri("http://127.0.0.1:5000")
mlflow.set_experiment("Xgboost-hyperopt")
warnings.filterwarnings("ignore")


s3 = boto3.client('s3')


PROCESSED_KEYS_FILE = "tracking/processed_keys.json"

args = getResolvedOptions(
    sys.argv,
    ["METRIC_THRESHOLD", "MODEL_NAME", "TOP_K","EXPERIMENT_NAME"]
)

metric_threshold = float(args["METRIC_THRESHOLD"])
model_name = args["MODEL_NAME"]
top_k = int(args["TOP_K"])
experiment_name = args["EXPERIMENT_NAME"]

def manage_and_register_best_model(experiment_name, metric_threshold, top_k, model_name, stage="Production"):
    """
    Finds best run under an RMSE threshold, registers it, and transitions it to the given stage.

    If no runs meet the RMSE threshold, fallback to top K best runs.

    Args:
        experiment_name (str): MLflow experiment name
        metric_threshold (float): RMSE threshold
        top_k (int): Max runs to consider if threshold not met
        model_name (str): Name for registered model
        stage (str): Target stage (e.g. 'Production', 'Staging')

    Returns:
        run_id (str): ID of best run
    """
    client = MlflowClient()
    mlflow.set_experiment(experiment_name)
    experiment = client.get_experiment_by_name(experiment_name)

    if experiment is None:
        raise ValueError(f"Experiment '{experiment_name}' not found.")
    experiment_id = experiment.experiment_id

    # First try to get runs below the threshold
    runs = client.search_runs(
        experiment_ids=[experiment_id],
        filter_string=f"metrics.rmse < {metric_threshold}",
        run_view_type=ViewType.ACTIVE_ONLY,
        max_results=top_k,
        order_by=["metrics.rmse ASC"]
    )

    # Fallback to top_k lowest RMSE runs if none meet the threshold
    if not runs:
        print("⚠️ No runs below threshold found. Falling back to top K lowest RMSE runs.")
        runs = client.search_runs(
            experiment_ids=[experiment_id],
            run_view_type=ViewType.ACTIVE_ONLY,
            max_results=top_k,
            order_by=["metrics.rmse ASC"]
        )

    if not runs:
        raise ValueError("❌ No runs found in the experiment at all.")

    # Get best run
    best_run = runs[0]
    run_id = best_run.info.run_id
    rmse = best_run.data.metrics.get("rmse")

    print(f"✅ Best run: {run_id} with RMSE: {rmse:.4f}")

    # Register the model
    model_uri = f"runs:/{run_id}/models_pickle"
    result = mlflow.register_model(model_uri=model_uri, name=model_name)
    model_version = result.version

    # Transition stage
    client.transition_model_version_stage(
        name=model_name,
        version=model_version,
        stage=stage,
        archive_existing_versions=True
    )

    # Update description
    today = datetime.today().date()
    client.update_model_version(
        name=model_name,
        version=model_version,
        description=f"Model version {model_version} transitioned to {stage} on {today}"
    )

    print(f"🚀 Model registered and promoted to '{stage}' stage: version {model_version}")

    return run_id


