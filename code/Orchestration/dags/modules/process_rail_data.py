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
import mlflow
import boto3
import pickle
import os
import numpy as np
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
import numpy as np
import warnings
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import LabelEncoder

mlflow.set_tracking_uri("http://127.0.0.1:5000")
mlflow.set_experiment("Xgboost-hyperopt")
warnings.filterwarnings("ignore")

BUCKET_NAME = 'darwin-raildata-mlops'
PROCESSED_PREFIX = 'darwin-kinesis-processed-rawdata'
LONG_DF_PREFIX = 'darwin-long-format-data'
MODEL_PREFIX = 'darwin-models'

s3 = boto3.client('s3')

import json

PROCESSED_KEYS_FILE = "tracking/processed_keys.json"

def load_all_processed_csvs(bucket: str, prefix: str,):
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    dfs = []
    for obj in response.get('Contents', []):
        key = obj['Key']
        if key.endswith('.csv'):
            csv_obj = s3.get_object(Bucket=bucket, Key=key)
            df = pd.read_csv(io.BytesIO(csv_obj['Body'].read()))
            dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()



def normalize_locations(df):
    location_indices = set()
    pattern = re.compile(r'Location_(\d+)_')
    for col in df.columns:
        match = pattern.search(col)
        if match:
            location_indices.add(int(match.group(1)))

    sorted_indices = sorted(location_indices)
    first_location_prefix = f"Location_{sorted_indices[0]}_@tpl" if sorted_indices else None
    base_index = df.columns.get_loc(first_location_prefix) if first_location_prefix in df.columns else len(df.columns)
    base_cols = list(df.columns[:base_index])

    normalized_rows = []
    for i in sorted_indices:
        location_cols = [col for col in df.columns if f"Location_{i}_" in col]
        if not location_cols:
            continue
        temp = df[base_cols + location_cols].copy()
        temp.columns = base_cols + [col.replace(f"Location_{i}_", "") for col in location_cols]
        temp["location_index"] = i
        normalized_rows.append(temp)

    return pd.concat(normalized_rows, ignore_index=True) if normalized_rows else pd.DataFrame()

    
def preprocess_for_arrival_delay(df):
    df = df.copy()

    # Drop rows where all columns are NaN or empty
    df = df.dropna(how='all')
    
    # Drop unwanted platform column
    df = df.drop(
    columns=[col for col in df.columns if col == 'Pport_uR_TS_Location_plat' or col.startswith('Pport_uR_TS_Location_plat_')],
    errors='ignore'
    )

    #Drop rows where both values are missing
    #df = df.dropna(subset=['@wta', 'arr_@et'], how='all')  # drop if both are missing


    # Drop rows with missing key fields needed for delay calculation
    #df = df.dropna(subset=[
        #'Pport_uR_TS_@ssd',
        #'arr_@et',
        #'@wta'
    #])

    # Parse service date
    df['service_date'] = pd.to_datetime(df['Pport_uR_TS_@ssd'], errors='coerce').dt.date

    # Combine date + time to compute full datetime
    df['scheduled_arrival_dt'] = pd.to_datetime(
        df['service_date'].astype(str) + ' ' + df['Pport_uR_TS_Location_@wta'],
        errors='coerce'
    )

    df['actual_arrival_dt'] = pd.to_datetime(
        df['service_date'].astype(str) + ' ' + df['Pport_uR_TS_Location_arr_@at'],
        errors='coerce'
    )

    # Calculate arrival delay in minutes
    df['arrival_delay_minutes'] = (
        df['actual_arrival_dt'] - df['scheduled_arrival_dt']
    ).dt.total_seconds() / 60.0


    df_filtered = df[
        (df['arrival_delay_minutes'].notna()) &
        (df['arrival_delay_minutes'] >= -5) &
        (df['arrival_delay_minutes'] <= 120)
    ].copy()

    # Create categorical label for arrival status
    #df_filtered['arrival_status'] = df_filtered['arrival_delay_minutes'].apply(
        #lambda x: 'early' if x < 0 else ('delayed' if x > 0 else 'on_time')
    #)

    # Extract day of week
    df_filtered['day_of_week'] = pd.to_datetime(df_filtered['Pport_uR_TS_@ssd'], errors='coerce').dt.dayofweek

    return df_filtered

    # Encode station code
    #if '@tpl' not in df.columns:
        #raise ValueError("Missing '@tpl' column for station encoding")

    #encoder = LabelEncoder()
    #df['station_code'] = encoder.fit_transform(df['@tpl'].astype(str))

    #return df



def prepare_features(df, train_ratio=0.8):
    
    """
        Prepares features for training and validation with a flexible train/val split.

        Args:
            df (pd.DataFrame): Full dataset.
            train_ratio (float): Ratio of data to use for training.

        Returns:
            X_train, y_train, X_val, y_val, dv: Transformed features/targets and fitted DictVectorizer.
    """
    
    df = df.copy().reset_index(drop=True)

    # Select only needed columns
    if 'day_of_week' not in df.columns or 'Pport_uR_TS_Location_@tpl' not in df.columns:
        raise ValueError("Missing required columns in DataFrame")

    # Train/val split by index
    # Split the data
    split_index = int(len(df) * train_ratio)
    df_train = df.iloc[:split_index].copy()
    df_val = df.iloc[split_index:].copy()

    # Create combined categorical feature
    df_train['day_of_week_Pport_uR_TS_Location_@tpl'] = (
        df_train['day_of_week'].astype(str) + '_' + df_train['Pport_uR_TS_Location_@tpl'].astype(str)
    )
    df_val['day_of_week_Pport_uR_TS_Location_@tpl'] = (
        df_val['day_of_week'].astype(str) + '_' + df_val['Pport_uR_TS_Location_@tpl'].astype(str)
    )

    # Define categorical and target columns
    categorical = ['day_of_week_Pport_uR_TS_Location_@tpl']
    target = 'arrival_delay_minutes'

    # Vectorize features
    dv = DictVectorizer()

    train_dicts = df_train[categorical].to_dict(orient='records')
    val_dicts = df_val[categorical].to_dict(orient='records')

    X_train = dv.fit_transform(train_dicts)
    X_val = dv.transform(val_dicts)

    y_train = df_train[target].values
    y_val = df_val[target].values

    return X_train, y_train, X_val, y_val, dv


def find_best_model_params(X_train, y_train, X_val, y_val, max_evals=30, verbose=True):
    model_classes = {
        "RandomForest": RandomForestRegressor,
        "XGBoost": XGBRegressor,
        "LinearRegression": LinearRegression
    }

    search_spaces = {
        "RandomForest": {
            "n_estimators": scope.int(hp.quniform("n_estimators", 50, 200, 10)),
            "max_depth": scope.int(hp.quniform("max_depth", 4, 30, 1)),
        },
        "XGBoost": {
            "n_estimators": scope.int(hp.quniform("n_estimators", 50, 200, 10)),
            "max_depth": scope.int(hp.quniform("max_depth", 3, 10, 1)),
            "learning_rate": hp.loguniform("learning_rate", -3, 0),
        },
        "LinearRegression": {}  # No hyperparameters to tune
    }

    best_rmse = float("inf")
    best_model = None
    best_params = {}

    for model_name, model_class in model_classes.items():
        if verbose:
            print(f"\n🔍 Tuning {model_name}...")

        if model_name == "LinearRegression":
            model = model_class()
            model.fit(X_train, y_train)
            y_pred = model.predict(X_val)
            mse = mean_squared_error(y_val, y_pred)
            rmse = np.sqrt(mse)


            if verbose:
                print(f"📊 RMSE for LinearRegression: {rmse:.4f}")

            if rmse < best_rmse:
                best_rmse = rmse
                best_model = model_name
                best_params = {}
            continue

        def objective(params):
            model = model_class(**params)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_val)
            mse = mean_squared_error(y_val, y_pred)
            rmse = np.sqrt(mse)
            return {"loss": rmse, "status": STATUS_OK}

        trials = Trials()
        best = fmin(
            fn=objective,
            space=search_spaces[model_name],
            algo=tpe.suggest,
            max_evals=max_evals,
            trials=trials,
            rstate=np.random.default_rng(42)
        )

        # Cast int-type hyperparams from float to int
        best_casted = {k: int(v) if k in ["n_estimators", "max_depth"] else v for k, v in best.items()}

        model = model_class(**best_casted)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_val)
        mse = mean_squared_error(y_val, y_pred)
        rmse = np.sqrt(mse)

        if verbose:
            print(f"📊 RMSE for {model_name}: {rmse:.4f} | Params: {best_casted}")

        if rmse < best_rmse:
            best_rmse = rmse
            best_model = model_name
            best_params = best_casted

    if verbose:
        print(f"\n✅ Best Model: {best_model}")
        print(f"✅ Best Params: {best_params}")
        print(f"✅ Best RMSE: {best_rmse:.4f}")

    return best_model, best_params, best_rmse


def train_model(X_train, y_train, X_val, y_val, model_class, best_params, bucket_name, model_key, dv):
    """
    Trains a model using best parameters, logs with MLflow, and uploads to S3.

    Args:
        X_train, y_train: Training data
        X_val, y_val: Validation data
        model_class (str or class): Model class name or class itself
        best_params (dict): Hyperparameters
        bucket_name (str): S3 bucket name
        model_key (str): Path to save model in S3
        dv (DictVectorizer): Fitted vectorizer to save with model

    Returns:
        model: Trained model
        rmse: Root Mean Squared Error on validation set
    """

    # Convert model name string to class if needed
    if isinstance(model_class, str):
        model_classes = {
            "RandomForest": RandomForestRegressor,
            "LinearRegression": LinearRegression,
            "XGBoost": XGBRegressor
        }
        model_class = model_classes[model_class]

    os.makedirs("/tmp", exist_ok=True)

    # Enable MLflow autologging for sklearn
    mlflow.sklearn.autolog()
    with mlflow.start_run():
        mlflow.set_tag("developer", "Rita")
        mlflow.log_param("model_class", model_class.__name__)
        mlflow.log_params(best_params)
        
        # Train
        model = model_class(**best_params)
        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_val)
        mse = mean_squared_error(y_val, y_pred)
        rmse = np.sqrt(mse)

        # Log the metric
        mlflow.log_metric("rmse", rmse)

        run_id = mlflow.active_run().info.run_id
        
        # Save model and preprocessor
        local_path = "/tmp/model.pkl"
        with open(local_path, "wb") as f_out:
            pickle.dump((dv, model), f_out)

        
        mlflow.sklearn.log_model(model, artifact_path="models_pickle")


        # Upload to S3
        s3 = boto3.client("s3")
        s3.upload_file(local_path, bucket_name, model_key)

        print(f"✅ Model uploaded to s3://{bucket_name}/{model_key}")
        print(f"📈 Validation RMSE: {rmse:.4f}")
        print(f"📈 run_id: {run_id}")

    return model, rmse, run_id



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


