import boto3
import pandas as pd
import io
import joblib
from sklearn.feature_extraction import DictVectorizer
import sys
from awsglue.utils import getResolvedOptions

# Define expected arguments
args_list = ['JOB_NAME', 'INPUT_PATH', 'OUTPUT_PATH']
args = getResolvedOptions(sys.argv, args_list)

job_name = args['JOB_NAME']
input_path = args['INPUT_PATH']
output_path = args['OUTPUT_PATH']


def prepare_features(input_path, output_path, train_ratio=0.8):
    """
    Loads a preprocessed CSV from S3, prepares train/val datasets,
    and saves them to S3 as joblib files.
    """
    s3 = boto3.client("s3")

    # --- Read CSV from S3 ---
    #bucket_in, key_in = input_path.replace("s3://", "").split("/", 1)
    #obj = s3.get_object(Bucket=bucket_in, Key=key_in)
    df = pd.read_parquet(input_path, storage_options={"anon": False})

    # Ensure required columns exist
    if 'day_of_week' not in df.columns or 'Pport_uR_TS_Location_@tpl' not in df.columns:
        raise ValueError("Missing required columns in DataFrame")
        
    median_value = df["arrival_delay_minutes"].median()
    df["arrival_delay_minutes"].fillna(median_value, inplace=True)

    # --- Train/validation split ---
    split_index = int(len(df) * train_ratio)
    df_train = df.iloc[:split_index].copy()
    df_val = df.iloc[split_index:].copy()

    # Combined categorical feature
    df_train['day_of_week_Pport_uR_TS_Location_@tpl'] = (
        df_train['day_of_week'].astype(str) + '_' + df_train['Pport_uR_TS_Location_@tpl'].astype(str)
    )
    df_val['day_of_week_Pport_uR_TS_Location_@tpl'] = (
        df_val['day_of_week'].astype(str) + '_' + df_val['Pport_uR_TS_Location_@tpl'].astype(str)
    )

    categorical = ['day_of_week_Pport_uR_TS_Location_@tpl']
    target = 'arrival_delay_minutes'

    # Vectorize features
    dv = DictVectorizer()
    X_train = dv.fit_transform(df_train[categorical].to_dict(orient='records'))
    X_val = dv.transform(df_val[categorical].to_dict(orient='records'))
    y_train = df_train[target].values
    y_val = df_val[target].values

    # --- Extract output bucket and prefix ---
    bucket_out, key_prefix = output_path.replace("s3://", "").split("/", 1)

    # --- Save each object directly ---
    for obj, name in [
        (X_train, "X_train.joblib"),
        (y_train, "y_train.joblib"),
        (X_val, "X_val.joblib"),
        (y_val, "y_val.joblib"),
        (dv, "dict_vectorizer.joblib")
    ]:
        buffer = io.BytesIO()
        joblib.dump(obj, buffer)
        buffer.seek(0)
        s3.upload_fileobj(buffer, bucket_out, f"{key_prefix}/{name}")

    print(f"✅ Features saved to {output_path}")


# Run function

prepare_features(
    input_path=args['INPUT_PATH'],
    output_path=args['OUTPUT_PATH']
)