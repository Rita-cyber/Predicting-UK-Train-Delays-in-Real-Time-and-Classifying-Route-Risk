import json
import xmltodict
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import re
import boto3
import io
import base64
import uuid
import tempfile
import joblib
from datetime import datetime
from collections.abc import MutableMapping
import mlflow
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

# S3 setup
s3 = boto3.client("s3")
BUCKET_NAME = 'darwin-raildata-mlops'
RAW_PREFIX = 'darwin-raildata-mlops/raw'
PROCESSED_PREFIX = 'darwin-kinesis-processed-rawdata'

mlflow.sklearn.autolog()


def store_raw_xml_to_s3(raw_xml: str, bucket: str, prefix: str, ts: str = None):
    try:
        timestamp = datetime.fromisoformat(ts).strftime("%Y-%m-%dT%H-%M-%S")
    except Exception:
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    unique_id = str(uuid.uuid4())[:8]
    date_path = datetime.utcnow().strftime("%Y/%m/%d")
    filename = f"{prefix}/{date_path}/darwin_raw_{timestamp}_{unique_id}.xml"
    s3.put_object(Bucket=bucket, Key=filename, Body=raw_xml.encode('utf-8'))
    return filename


def flatten_dict(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        clean_key = k.split(':')[-1]
        new_key = f"{parent_key}{sep}{clean_key}" if parent_key else clean_key
        if isinstance(v, MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, MutableMapping):
                    items.extend(flatten_dict(item, f"{new_key}_{i}", sep=sep).items())
                else:
                    items.append((f"{new_key}_{i}", item))
        else:
            items.append((new_key, v))
    return dict(items)


def load_all_processed_csvs(bucket: str, prefix: str):
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


def clean_long_df(df):
    df = df.copy()
    df = df.dropna(subset=[
        'Pport_uR_TS_@ssd',
        'Pport_uR_TS_Location_0_@tpl',
        'Pport_uR_TS_Location_0_dep_@et',
        'Pport_uR_TS_Location_0_@wtd'
    ])
    df['departure_delay_minutes'] = (
        pd.to_datetime(df['Pport_uR_TS_Location_0_dep_@et'], errors='coerce') -
        pd.to_datetime(df['Pport_uR_TS_Location_0_@wtd'], errors='coerce')
    ).dt.total_seconds() / 60.0
    df = df[df['departure_delay_minutes'].between(-5, 120)]
    return df


def prepare_features(df):
    df = df.copy()
    df['target_delay_class'] = df['departure_delay_minutes'].apply(lambda x: 1 if x >= 5 else 0)
    df['day_of_week'] = pd.to_datetime(df['Pport_uR_TS_@ssd'], errors='coerce').dt.dayofweek
    encoder = LabelEncoder()
    df['station_code'] = encoder.fit_transform(df['Pport_uR_TS_Location_0_@tpl'].astype(str))
    X = df[['day_of_week', 'station_code']]
    y = df['target_delay_class']
    return X, y, encoder


def lambda_handler(event, context):
    records_list = []

    for record in event['Records']:
        try:
            raw_data = base64.b64decode(record['kinesis']['data']).decode('utf-8')
        except Exception as e:
            print("Base64 decode error:", e)
            continue

        try:
            json_record = json.loads(raw_data)
            raw_xml = json_record.get("raw_xml", raw_data)
            ts = json_record.get("ts")
            store_raw_xml_to_s3(raw_xml, BUCKET_NAME, RAW_PREFIX, ts)
        except Exception as e:
            print("Error storing raw XML:", e)

        try:
            parsed = xmltodict.parse(raw_xml)
            flat_dict = flatten_dict(parsed)
            records_list.append(flat_dict)
        except Exception as e:
            print("XML parsing failed:", e)
            continue

    if not records_list:
        return {'statusCode': 204, 'message': 'No valid records to process.'}

    df = pd.DataFrame(records_list)
    filename = f"{PROCESSED_PREFIX}/events_snapshot_{datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S')}.csv"
    s3.put_object(Bucket=BUCKET_NAME, Key=filename, Body=df.to_csv(index=False))

    full_df = load_all_processed_csvs(BUCKET_NAME, PROCESSED_PREFIX)
    if full_df.empty:
        return {'statusCode': 204, 'message': 'No data after merge.'}

    long_df = normalize_locations(full_df)
    long_df = clean_long_df(long_df)

    # Save long_df as Parquet
    LONG_DF_PREFIX = 'darwin-long-format-data'
    long_df_filename = f"{LONG_DF_PREFIX}/long_df_{datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S')}.parquet"
    parquet_buffer = io.BytesIO()
    long_df.to_parquet(parquet_buffer, engine='pyarrow', index=False)
    s3.put_object(Bucket=BUCKET_NAME, Key=long_df_filename, Body=parquet_buffer.getvalue())

    X, y, encoder = prepare_features(long_df)
    if X.empty:
        return {'statusCode': 204, 'message': 'No data for model.'}

    try:
        with mlflow.start_run():
            model = RandomForestClassifier(n_estimators=10, random_state=42)
            model.fit(X, y)

            # Save model to S3
            with tempfile.NamedTemporaryFile(suffix='.joblib') as tmp:
                joblib.dump(model, tmp.name)
                tmp.seek(0)
                model_key = f"{PROCESSED_PREFIX}/models/random_forest_model_{datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S')}.joblib"
                s3.upload_fileobj(tmp, BUCKET_NAME, model_key)

    except Exception as e:
        return {'statusCode': 500, 'message': f'ML model failed: {e}'}

    return {
        'statusCode': 200,
        'message': f'{len(df)} new raw events processed. {len(X)} rows used for inference.'
    }
