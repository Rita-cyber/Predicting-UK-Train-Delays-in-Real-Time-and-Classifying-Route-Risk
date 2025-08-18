# Refactored process_rail_data.py for fast DAG parsing

import pandas as pd
import re
import io
import json
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import mean_squared_error
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from xgboost import XGBRegressor
from hyperopt import fmin, tpe, hp, STATUS_OK, Trials
from hyperopt.pyll import scope


def load_all_processed_csvs(s3_client, bucket: str, prefix: str):
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    dfs = []
    for obj in response.get('Contents', []):
        key = obj['Key']
        if key.endswith('.csv'):
            csv_obj = s3_client.get_object(Bucket=bucket, Key=key)
            df = pd.read_csv(io.BytesIO(csv_obj['Body'].read()))
            dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

def normalize_locations(s3_client, bucket_name, key, chunksize=1000):
    obj = s3_client.get_object(Bucket=bucket_name, Key=key)
    
    # Read the CSV in chunks
    chunk_iter = pd.read_csv(
        io.BytesIO(obj['Body'].read()),
        low_memory=False,
        chunksize=chunksize
    )

    normalized_chunks = []
    pattern = re.compile(r'Location_(\d+)_')

    for chunk in chunk_iter:
        # Find location indices in the current chunk
        location_indices = set()
        for col in chunk.columns:
            match = pattern.search(col)
            if match:
                location_indices.add(int(match.group(1)))

        sorted_indices = sorted(location_indices)
        first_location_prefix = (
            f"Location_{sorted_indices[0]}_@tpl" if sorted_indices else None
        )
        base_index = (
            chunk.columns.get_loc(first_location_prefix)
            if first_location_prefix in chunk.columns
            else len(chunk.columns)
        )
        base_cols = list(chunk.columns[:base_index])

        # Normalize rows for each location index
        for i in sorted_indices:
            location_cols = [col for col in chunk.columns if f"Location_{i}_" in col]
            if not location_cols:
                continue
            temp = chunk[base_cols + location_cols].copy()
            temp.columns = base_cols + [
                col.replace(f"Location_{i}_", "") for col in location_cols
            ]
            temp["location_index"] = i
            normalized_chunks.append(temp)

    # Combine all normalized chunks
    return pd.concat(normalized_chunks, ignore_index=True) if normalized_chunks else pd.DataFrame()

def preprocess_for_arrival_delay(df):
    df = df.copy().dropna(how='all')

    df = df.drop(
        columns=[col for col in df.columns if col == 'Pport_uR_TS_Location_plat' or col.startswith('Pport_uR_TS_Location_plat_')],
        errors='ignore')

    df['service_date'] = pd.to_datetime(df['Pport_uR_TS_@ssd'], errors='coerce').dt.date

    df['scheduled_arrival_dt'] = pd.to_datetime(
        df['service_date'].astype(str) + ' ' + df['Pport_uR_TS_Location_@wta'], errors='coerce')

    df['actual_arrival_dt'] = pd.to_datetime(
        df['service_date'].astype(str) + ' ' + df['Pport_uR_TS_Location_arr_@at'], errors='coerce')

    df['arrival_delay_minutes'] = (df['actual_arrival_dt'] - df['scheduled_arrival_dt']).dt.total_seconds() / 60.0

    df_filtered = df[
        (df['arrival_delay_minutes'].notna()) &
        (df['arrival_delay_minutes'] >= -5) &
        (df['arrival_delay_minutes'] <= 120)
    ].copy()

    df_filtered['day_of_week'] = pd.to_datetime(df_filtered['Pport_uR_TS_@ssd'], errors='coerce').dt.dayofweek

    return df_filtered


def prepare_features(df, train_ratio=0.8):
    df = df.copy().reset_index(drop=True)

    split_index = int(len(df) * train_ratio)
    df_train = df.iloc[:split_index].copy()
    df_val = df.iloc[split_index:].copy()

    df_train['day_tpl'] = df_train['day_of_week'].astype(str) + '_' + df_train['Pport_uR_TS_Location_@tpl'].astype(str)
    df_val['day_tpl'] = df_val['day_of_week'].astype(str) + '_' + df_val['Pport_uR_TS_Location_@tpl'].astype(str)

    categorical = ['day_tpl']
    target = 'arrival_delay_minutes'

    dv = DictVectorizer()
    X_train = dv.fit_transform(df_train[categorical].to_dict(orient='records'))
    X_val = dv.transform(df_val[categorical].to_dict(orient='records'))

    y_train = df_train[target].values
    y_val = df_val[target].values

    return X_train, y_train, X_val, y_val, dv


def find_best_model_params(X_train, y_train, X_val, y_val, max_evals=30):
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
        "LinearRegression": {}
    }

    best_model = None
    best_params = {}
    best_rmse = float("inf")

    for name, cls in model_classes.items():
        if name == "LinearRegression":
            model = cls()
            model.fit(X_train, y_train)
            rmse = np.sqrt(mean_squared_error(y_val, model.predict(X_val)))
            if rmse < best_rmse:
                best_model, best_params, best_rmse = name, {}, rmse
            continue

        def objective(params):
            model = cls(**params)
            model.fit(X_train, y_train)
            rmse = np.sqrt(mean_squared_error(y_val, model.predict(X_val)))
            return {"loss": rmse, "status": STATUS_OK}

        trials = Trials()
        best = fmin(objective, space=search_spaces[name], algo=tpe.suggest, max_evals=max_evals, trials=trials)
        best_casted = {k: int(v) if k in ["n_estimators", "max_depth"] else v for k, v in best.items()}

        model = cls(**best_casted)
        model.fit(X_train, y_train)
        rmse = np.sqrt(mean_squared_error(y_val, model.predict(X_val)))

        if rmse < best_rmse:
            best_model, best_params, best_rmse = name, best_casted, rmse

    return best_model, best_params, best_rmse


def train_model(X_train, y_train, X_val, y_val, model_class, best_params, bucket_name, model_key, dv):
    import mlflow
    import mlflow.sklearn
    import boto3
    import pickle
    import os

    model_map = {
        "RandomForest": RandomForestRegressor,
        "LinearRegression": LinearRegression,
        "XGBoost": XGBRegressor
    }
    model_cls = model_map[model_class] if isinstance(model_class, str) else model_class

    mlflow.set_tracking_uri("http://127.0.0.1:5000")
    mlflow.set_experiment("Xgboost-hyperopt")
    mlflow.sklearn.autolog()

    with mlflow.start_run():
        mlflow.log_param("model_class", model_cls.__name__)
        mlflow.log_params(best_params)
        model = model_cls(**best_params)
        model.fit(X_train, y_train)
        rmse = np.sqrt(mean_squared_error(y_val, model.predict(X_val)))
        mlflow.log_metric("rmse", rmse)

        with open("/tmp/model.pkl", "wb") as f_out:
            pickle.dump((dv, model), f_out)

        mlflow.sklearn.log_model(model, artifact_path="models_pickle")

        boto3.client("s3").upload_file("/tmp/model.pkl", bucket_name, model_key)

        return model, rmse, mlflow.active_run().info.run_id


def manage_and_register_best_model(experiment_name, metric_threshold, top_k, model_name, stage="Production"):
    import mlflow
    from mlflow.tracking import MlflowClient
    from mlflow.entities import ViewType
    from datetime import datetime

    mlflow.set_tracking_uri("http://127.0.0.1:5000")
    mlflow.set_experiment(experiment_name)
    client = MlflowClient()
    experiment = client.get_experiment_by_name(experiment_name)
    if not experiment:
        raise ValueError(f"Experiment '{experiment_name}' not found")

    experiment_id = experiment.experiment_id
    runs = client.search_runs(
        [experiment_id],
        filter_string=f"metrics.rmse < {metric_threshold}",
        run_view_type=ViewType.ACTIVE_ONLY,
        order_by=["metrics.rmse ASC"],
        max_results=top_k
    ) or client.search_runs(
        [experiment_id],
        run_view_type=ViewType.ACTIVE_ONLY,
        order_by=["metrics.rmse ASC"],
        max_results=top_k
    )

    if not runs:
        raise ValueError("No valid runs found")

    best_run = runs[0]
    run_id = best_run.info.run_id
    model_uri = f"runs:/{run_id}/models_pickle"
    result = mlflow.register_model(model_uri=model_uri, name=model_name)

    client.transition_model_version_stage(
        name=model_name,
        version=result.version,
        stage=stage,
        archive_existing_versions=True
    )

    client.update_model_version(
        name=model_name,
        version=result.version,
        description=f"Promoted to {stage} on {datetime.today().date()}"
    )

    return run_id
