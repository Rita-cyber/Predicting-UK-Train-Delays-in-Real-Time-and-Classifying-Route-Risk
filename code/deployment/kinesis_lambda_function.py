import os
import io
import re
import json
import uuid
import base64
import warnings
import pickle
from datetime import datetime
from collections.abc import MutableMapping

import boto3
import pandas as pd
import xmltodict
import joblib
from sklearn.feature_extraction import DictVectorizer

# --------------------
# AWS clients & config
# --------------------
s3 = boto3.client("s3")
kinesis_client = boto3.client("kinesis")

BUCKET_NAME = os.getenv("BUCKET_NAME", "darwin-raildata-mlops")

# Input/Output layout
bucket = "darwin-raildata-mlops"
key = "models/best_model.pkl"
RAW_PREFIX = os.getenv("RAW_PREFIX", "raw")
TEMP_PREFIX = os.getenv("TEMP_PREFIX", "temp")  # holds batch CSVs from each invocation
PROCESSED_PREFIX = os.getenv("PROCESSED_PREFIX", "processed")  # holds snapshots
LONG_DF_PREFIX = os.getenv("LONG_DF_PREFIX", "darwin-long-format-data")  # cleaned long-format data
CLEAN_DF_PREFIX =  os.getenv("CLEAN_DF_PREFIX", "darwin-clean-format-data")

# Model artifacts in S3
MODEL_KEY = os.getenv("MODEL_KEY", "models/best_model.pkl")
DV_KEY = os.getenv("DV_KEY", "feature-eng-data//dict_vectorizer.joblib")

# Streaming predictions
PREDICTIONS_STREAM_NAME = os.getenv("PREDICTIONS_STREAM_NAME", "arrival_delay_predictions")
TEST_RUN = os.getenv("TEST_RUN", "False") == "True"

# Optional limits
MAX_TEMP_FILES = int(os.getenv("MAX_TEMP_FILES", "100"))  # 0 = no limit
LIST_PAGE_SIZE = int(os.getenv("LIST_PAGE_SIZE", "1000"))  # S3 list pagination page size

# Parquet engine ("pyarrow" recommended; ensure your Lambda layer/container includes it)
PARQUET_ENGINE = os.getenv("PARQUET_ENGINE", "pyarrow")

warnings.filterwarnings("ignore")


# --------------------
# Utility functions
# --------------------
def safe_parse_ts(ts: str) -> str:
    """
    Try to parse incoming timestamp to a filesystem-safe format. Fall back to UTC now.
    """
    try:
        # Handle a variety of timestamp formats
        dt = pd.to_datetime(ts, utc=True, errors="raise").to_pydatetime()
    except Exception:
        dt = datetime.utcnow()
    return dt.strftime("%Y-%m-%dT%H-%M-%S")


def store_raw_xml_to_s3(raw_xml: str, bucket: str, prefix: str, ts: str | None = None) -> str:
    timestamp = safe_parse_ts(ts) if ts else datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    unique_id = str(uuid.uuid4())[:8]
    date_path = datetime.utcnow().strftime("%Y/%m/%d")
    key = f"{prefix}/{date_path}/darwin_raw_{timestamp}_{unique_id}.xml"
    s3.put_object(Bucket=bucket, Key=key, Body=raw_xml.encode("utf-8"))
    return key


def flatten_dict(d, parent_key: str = "", sep: str = "_"):
    items = []
    for k, v in d.items():
        clean_key = k.split(":")[-1]  # remove namespace
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


def list_all_keys(bucket: str, prefix: str, page_size: int = 1000):
    """
    Generator over all S3 keys under a prefix (paginated).
    """
    continuation_token = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": page_size}
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            yield obj["Key"]
        if resp.get("IsTruncated"):
            continuation_token = resp.get("NextContinuationToken")
        else:
            break


def load_all_processed_csvs(bucket: str, prefix: str, max_files: int = 0, include_snapshots: bool = True) -> pd.DataFrame:
    """
    Load all CSVs under 'prefix' and combine into a single DataFrame.
    max_files=0 means 'no limit'.
    """
    dfs = []
    count = 0
    for key in list_all_keys(bucket, prefix, page_size=LIST_PAGE_SIZE):
        if not key.endswith(".csv"):
            continue
        if not include_snapshots and "snapshot" in key:
            continue

        csv_obj = s3.get_object(Bucket=bucket, Key=key)
        df = pd.read_csv(io.BytesIO(csv_obj["Body"].read()))
        dfs.append(df)
        count += 1
        if max_files and count >= max_files:
            break

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()



def normalize_locations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand wide columns like Location_0_* or Pport_uR_TS_Location_0_* into rows.
    Works with or without the prefix.
    """
    # Regex matches both:
    # - Pport_uR_TS_Location_0_*
    # - Location_0_*
    pattern = re.compile(r"(?:Pport_uR_TS_)?Location_(\d+)_")

    # Extract all indices
    location_indices = set()
    for col in df.columns:
        match = pattern.search(col)
        if match:
            location_indices.add(int(match.group(1)))

    if not location_indices:
        print("⚠️ No Location_* columns found to normalize.")
        return pd.DataFrame()

    sorted_indices = sorted(location_indices)

    # Find where the first location column starts
    first_location_cols = [c for c in df.columns if pattern.search(c) and pattern.search(c).group(1) == str(sorted_indices[0])]
    base_index = df.columns.get_loc(first_location_cols[0]) if first_location_cols else 0
    base_cols = list(df.columns[:base_index])

    normalized_rows = []
    for i in sorted_indices:
        location_cols = [col for col in df.columns if f"Location_{i}_" in col or f"Pport_uR_TS_Location_{i}_" in col]
        if not location_cols:
            continue

        temp = df[base_cols + location_cols].copy()

        # Strip either prefix
        temp.columns = base_cols + [
            re.sub(r"^(?:Pport_uR_TS_)?Location_" + str(i) + "_", "", col)
            for col in location_cols
        ]

        temp["location_index"] = i
        normalized_rows.append(temp)

    return pd.concat(normalized_rows, ignore_index=True) if normalized_rows else pd.DataFrame()

def preprocess_for_arrival_delay(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.dropna(how="all")

    # Parse service date
    df["service_date"] = pd.to_datetime(df.get("Pport_uR_TS_@ssd"), errors="coerce").dt.date

    # Combine date + time to compute full datetime
    df["scheduled_arrival_dt"] = pd.to_datetime(
        df["service_date"].astype(str) + " " + df.get("Pport_uR_TS_Location_@wta", ""), errors="coerce"
    )
    df["actual_arrival_dt"] = pd.to_datetime(
        df["service_date"].astype(str) + " " + df.get("Pport_uR_TS_Location_arr_@at", ""), errors="coerce"
    )

    # Calculate arrival delay in minutes
    df["arrival_delay_minutes"] = (df["actual_arrival_dt"] - df["scheduled_arrival_dt"]).dt.total_seconds() / 60.0

    # Reasonable bounds filter
    df_filtered = df[
        (df["arrival_delay_minutes"].notna())
        & (df["arrival_delay_minutes"] >= -5)
        & (df["arrival_delay_minutes"] <= 120)
    ].copy()

    # Day of week
    df_filtered["day_of_week"] = pd.to_datetime(df_filtered.get("Pport_uR_TS_@ssd"), errors="coerce").dt.dayofweek

    return df_filtered


def transform_features_for_prediction(df: pd.DataFrame, dv: DictVectorizer):
    df = df.copy()
    df = df.dropna(how="all")
    # Drop any "plat" variations
    df = df.drop(columns=[c for c in df.columns if c.startswith("Pport_uR_TS_Location_plat")], errors="ignore")

    # Required columns
    req_cols = ["day_of_week", "Pport_uR_TS_Location_@tpl"]
    if any(col not in df.columns for col in req_cols):
        raise ValueError(f"Missing required columns for prediction: {req_cols}")

    # Composite categorical feature (as per model training)
    df["day_of_week_Pport_uR_TS_Location_@tpl"] = (
        df["day_of_week"].astype(str) + "_" + df["Pport_uR_TS_Location_@tpl"].astype(str)
    )

    input_dicts = df[["day_of_week_Pport_uR_TS_Location_@tpl"]].to_dict(orient="records")
    X = dv.transform(input_dicts)
    return X


# --------------------
# Load model/artifacts at init (cold start)
# --------------------
model_bytes = s3.get_object(Bucket=BUCKET_NAME, Key=MODEL_KEY)["Body"].read()
model = joblib.load(io.BytesIO(model_bytes))

dv_bytes = s3.get_object(Bucket=BUCKET_NAME, Key=DV_KEY)["Body"].read()
dv = joblib.load(io.BytesIO(dv_bytes))

#dv = DictVectorizer()


# --------------------
# Lambda entrypoint
# --------------------
def lambda_handler(event, context):
    prediction_events = []
    records_list = []

    # 1) Ingest & archive raw XML
    for record in event.get("Records", []):
        try:
            raw_data = base64.b64decode(record["kinesis"]["data"]).decode("utf-8", errors="ignore")
        except Exception as e:
            print("Base64 decode error:", e)
            continue

        # Try JSON payload first (containing raw_xml), otherwise treat as raw XML
        raw_xml, ts = None, None
        try:
            payload = json.loads(raw_data)
            raw_xml = payload.get("raw_xml")
            ts = payload.get("ts")
        except Exception:
            # Not JSON — assume raw XML string
            raw_xml = raw_data

        if not raw_xml:
            print("⚠️ Skipping record: no XML content.")
            continue

        try:
            store_raw_xml_to_s3(raw_xml, BUCKET_NAME, RAW_PREFIX, ts)
        except Exception as e:
            print("Error storing raw XML:", e)

        # Parse and flatten
        try:
            parsed = xmltodict.parse(raw_xml)
            flat = flatten_dict(parsed)
            records_list.append(flat)
        except Exception as e:
            print("XML parsing failed:", e)
            continue

    if not records_list:
        return {"statusCode": 204, "message": "No valid records to process."}

    # 2) Write current batch → TEMP (keep history of machine-flattened CSVs)
    batch_df = pd.DataFrame(records_list)
    temp_key = f"{TEMP_PREFIX}/{uuid.uuid4()}.csv"
    temp_buf = io.StringIO()
    batch_df.to_csv(temp_buf, index=False)
    s3.put_object(Bucket=BUCKET_NAME, Key=temp_key, Body=temp_buf.getvalue())

    # 3) Combine ALL temp CSVs
    full_df = load_all_processed_csvs(BUCKET_NAME, TEMP_PREFIX, max_files=MAX_TEMP_FILES)
    if full_df.empty:
        print("⚠️ No combined data found after loading all processed CSVs.")
        return {"statusCode": 204, "message": "No data after merge."}

    # --- Wide snapshot (CSV & Parquet) ---
    wide_csv_key = f"{PROCESSED_PREFIX}/events_snapshot.csv"
    #wide_parquet_key = f"{PROCESSED_PREFIX}/events_snapshot.parquet"

    wide_csv_buf = io.StringIO()
    full_df.to_csv(wide_csv_buf, index=False)
    s3.put_object(Bucket=BUCKET_NAME, Key=wide_csv_key, Body=wide_csv_buf.getvalue())

    #wide_parquet_buf = io.BytesIO()
    #full_df.to_parquet(wide_parquet_buf, engine=PARQUET_ENGINE, index=False)
    #s3.put_object(Bucket=BUCKET_NAME, Key=wide_parquet_key, Body=wide_parquet_buf.getvalue())

    # --- Long snapshot (CSV) ---
    # Only include id_vars if present (prevents KeyError)
    id_vars = [c for c in ["tag", "timestamp"] if c in full_df.columns]
    long_df = pd.melt(full_df, id_vars=id_vars, var_name="field", value_name="value")

    long_csv_key = f"{PROCESSED_PREFIX}/events_long_snapshot.csv"
    long_csv_buf = io.StringIO()
    long_df.to_csv(long_csv_buf, index=False)
    s3.put_object(Bucket=BUCKET_NAME, Key=long_csv_key, Body=long_csv_buf.getvalue())

    print(
        f"✅ Updated snapshots: {wide_csv_key}, {long_csv_key}"
    )

    # 4) Normalize + clean (for ML features)
    print("Normalizing + cleaning data...")
    norm_df = normalize_locations(full_df)
    if norm_df.empty:
        print("⚠️ No Location_* columns found to normalize — skipping ML step.")
        return {"statusCode": 200, "message": "Snapshots updated. No normalized data."}

    clean_df = preprocess_for_arrival_delay(norm_df)
    if clean_df.empty:
        print("⚠️ No rows after preprocessing — skipping ML step.")
        return {"statusCode": 200, "message": "Snapshots updated. No rows for prediction."}

    # Also persist a clean long-format Parquet (overwrite)
    norm_long_key = f"{LONG_DF_PREFIX}/events_long.csv"
    norm_csv_buf = io.BytesIO()
    norm_df.to_csv(norm_csv_buf, index=False)
    s3.put_object(Bucket=BUCKET_NAME, Key=norm_long_key, Body=norm_csv_buf.getvalue())
    print(f"✅ Saved cleaned long-format to {norm_long_key}")
    clean_long_key = f"{CLEAN_DF_PREFIX}/events_long_clean.csv"
    clean_csv_buf = io.BytesIO()
    clean_df.to_csv(clean_csv_buf, index=False)
    s3.put_object(Bucket=BUCKET_NAME, Key=clean_long_key, Body=clean_csv_buf.getvalue())
    print(f"✅ Saved cleaned clean-format to {clean_long_key}")


    obj = s3.get_object(Bucket=bucket, Key=key)
    bytestream = io.BytesIO(obj["Body"].read())

    dv, model = pickle.load(bytestream)   # <-- this sets both dv and model
 

    # 5) Predict + stream to Kinesis
    try:
        try:
            X = transform_features_for_prediction(clean_df, dv)
        except Exception as fe:
            print(f"Feature transform skipped: {fe}")
            return {"statusCode": 200, "message": "Snapshots updated. Missing features for prediction."}

          # after downloading from S3

          # this gives you the dictvectorizer and model


        #y_pred = model.predict(dv.transform(X_val))

        preds = model.predict(X)

        kinesis_batch = []
        station_col = "Pport_uR_TS_Location_@tpl" if "Pport_uR_TS_Location_@tpl" in clean_df.columns else None

        for idx, pred in enumerate(preds):
            station_id = str(clean_df.iloc[idx][station_col]) if station_col else "unknown"
            result = {
                "model": "arrival-delay-predictor",
                "version": "v1",
                "prediction": {
                    "arrival_delay_minutes": float(pred),
                    "Pport_uR_TS_Location_@tpl": station_id,
                },
                "ts": datetime.utcnow().isoformat() + "Z",
            }
            kinesis_batch.append({"Data": json.dumps(result), "PartitionKey": station_id})

        if not TEST_RUN and kinesis_batch:
            for i in range(0, len(kinesis_batch), 500):
                chunk = kinesis_batch[i : i + 500]
                resp = kinesis_client.put_records(StreamName=PREDICTIONS_STREAM_NAME, Records=chunk)
                if resp.get("FailedRecordCount", 0) > 0:
                    print(f"⚠️ {resp['FailedRecordCount']} prediction records failed to send.")

        return {"statusCode": 200, "predictions_sent": 0 if TEST_RUN else len(kinesis_batch)}

    except Exception as e:
        print(f"Prediction failed: {e}")
        return {"statusCode": 500, "error": str(e)}


if __name__ == "__main__":
    from kinesis_lambda_function import lambda_handler
    import boto3, base64, time

    stream_name = "kinesis-datanationalrail-events"   # 🔹 change this
    region = "eu-north-1"                 # 🔹 change this if needed

    kinesis = boto3.client("kinesis", region_name=region)
    shard_id = kinesis.describe_stream(StreamName=stream_name)["StreamDescription"]["Shards"][0]["ShardId"]

    shard_iterator = kinesis.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType="LATEST"
    )["ShardIterator"]

    print(f"🔄 Consuming from {stream_name}...")

    while True:
        response = kinesis.get_records(ShardIterator=shard_iterator, Limit=25)
        shard_iterator = response["NextShardIterator"]

        if response["Records"]:
            event = {"Records": []}
            for r in response["Records"]:
                event["Records"].append({
                    "kinesis": {"data": base64.b64encode(r["Data"]).decode("utf-8")}
                })

            # 🔹 Call your Lambda handler with real Kinesis records
            lambda_handler(event, None)

        time.sleep(2)

