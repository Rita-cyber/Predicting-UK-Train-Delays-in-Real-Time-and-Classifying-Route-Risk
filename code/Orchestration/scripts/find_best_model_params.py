import io
import joblib
import boto3
import numpy as np
from hyperopt import fmin, tpe, hp, Trials, STATUS_OK
from hyperopt.pyll import scope
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

import sys
from awsglue.utils import getResolvedOptions

# Define the expected arguments
args_list = ['JOB_NAME', 'BUCKET_NAME', 'X_TRAIN_PATH', 'Y_TRAIN_PATH', 'X_VAL_PATH', 'Y_VAL_PATH','DV_PATH','BEST_PARAMS_PREFIX']

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
best_params_prefix = args['BEST_PARAMS_PREFIX']
optional_setting = args.get('OPTIONAL_SETTING', 'default_value_if_not_provided')


def find_best_model_params(
    X_train_path, y_train_path, X_val_path, y_val_path,
    bucket_name,dv_path,best_params_prefix,filename_save="best_params.joblib",max_evals=30,verbose=True):
    
    
    """
    Load a joblib file from S3 directly into memory.
    """
    s3 = boto3.client("s3")
    # --- Parse input S3 path ---
    bucket_in, X_train_key = X_train_path.replace("s3://", "").split("/", 1)
    obj = s3.get_object(Bucket=bucket_in, Key=X_train_key)
    X_train = joblib.load(io.BytesIO(obj['Body'].read()))

    bucket_in, y_train_key = y_train_path.replace("s3://", "").split("/", 1)
    obj = s3_client.get_object(Bucket=bucket_name, Key=y_train_key)
    y_train = joblib.load(io.BytesIO(obj['Body'].read()))

    bucket_in, X_val_key = X_val_path.replace("s3://", "").split("/", 1)
    obj = s3_client.get_object(Bucket=bucket_name, Key=X_val_key)
    X_val = joblib.load(io.BytesIO(obj['Body'].read()))

    bucket_in, y_val_key = y_val_path.replace("s3://", "").split("/", 1)
    obj = s3_client.get_object(Bucket=bucket_name, Key=y_val_key)
    y_val = joblib.load(io.BytesIO(obj['Body'].read()))
    
    bucket_in, dv_key = dv_path.replace("s3://", "").split("/", 1)
    obj = s3_client.get_object(Bucket=bucket_name, Key=dv_key)
    dv = joblib.load(io.BytesIO(obj['Body'].read()))
    
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

    best_rmse = float("inf")
    best_model = None
    best_params = {}

    for model_name, model_class in model_classes.items():
        if verbose:
            print(f"\n🔍 Tuning {model_name}...")

        if model_name == "LinearRegression":
            model = model_class()
            model.fit(X_train, y_train)
            rmse = np.sqrt(mean_squared_error(y_val, model.predict(X_val)))

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
            rmse = np.sqrt(mean_squared_error(y_val, model.predict(X_val)))
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

        best_casted = {k: int(v) if k in ["n_estimators", "max_depth"] else v for k, v in best.items()}

        model = model_class(**best_casted)
        model.fit(X_train, y_train)
        rmse = np.sqrt(mean_squared_error(y_val, model.predict(X_val)))

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

    # Save best params to S3
    buffer = io.BytesIO()
    joblib.dump(best_params, buffer)
    buffer.seek(0)
    s3_client.put_object(
        Bucket=bucket_name,
        Key=f"{best_params_prefix}/{filename_save}",
        Body=buffer
    )

    return best_model, best_params, best_rmse

best_model, best_params, best_rmse = find_best_model_params(
    X_train_path=args['X_TRAIN'],
    y_train_path=args['Y_TRAIN'],
    X_val_path=args['X_VAL'],
    y_val_path=args['Y_VAL'],
    bucket_name=args['BUCKET_NAME'],
    best_params_prefix=args['BEST_PARAMS_PREFIX']
)