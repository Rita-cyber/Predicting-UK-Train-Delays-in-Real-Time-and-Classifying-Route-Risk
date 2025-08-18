import json
import xmltodict
import pandas as pd
import boto3
from collections.abc import MutableMapping
import os
import base64
import uuid
from datetime import datetime

s3 = boto3.client("s3")
BUCKET_NAME = 'darwin-raildata-mlops'  # ← make sure this is set in IAM role permissions
RAW_PREFIX = 'darwin-raildata-mlops/raw'              # ← S3 folder path for raw XML
PROCESSED_PREFIX = 'darwin-kinesis-processed-rawdata'

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
        # Strip namespaces like "ns5:Location" → "Location"
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

def process_kinesis_from_stream(**kwargs):
    from datetime import datetime
    import base64, boto3, pandas as pd, xmltodict, json

    stream_name = 'kinesis-datanationalrail-events'
    shard_id = 'shardId-000000000000'  # You should dynamically fetch this
    kinesis = boto3.client('kinesis')

    # Get shard iterator
    iterator = kinesis.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType='LATEST'
    )['ShardIterator']

    records = kinesis.get_records(ShardIterator=iterator, Limit=10)['Records']

    records_list = []
    for record in records:
        try:
            raw_data = base64.b64decode(record['Data']).decode('utf-8')
            json_record = json.loads(raw_data)
            raw_xml = json_record.get("raw_xml", raw_data)
            ts = json_record.get("ts")
            store_raw_xml_to_s3(raw_xml, BUCKET_NAME, RAW_PREFIX, ts)

            parsed = xmltodict.parse(raw_xml)
            flat_dict = flatten_dict(parsed)
            records_list.append(flat_dict)

        except Exception as e:
            print("Processing error:", e)

    if records_list:
        df = pd.DataFrame(records_list)
        filename = f"{PROCESSED_PREFIX}/events_snapshot_{datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S')}.csv"
        s3.put_object(Bucket=BUCKET_NAME, Key=filename, Body=df.to_csv(index=False))
        print(f"✅ {len(df)} records written to S3: {filename}")
    else:
        print("⚠️ No valid records")

