from pyspark.sql import SparkSession
import re
from pyspark.sql.functions import col, lit
import boto3
import json

from airflow.hooks.base_hook import BaseHook

aws_conn = BaseHook.get_connection("aws_keys")
aws_access_key = aws_conn.login
aws_secret_key = aws_conn.password
extra = aws_conn.extra_dejson
region = extra.get("region_name", "eu-north-1")

BUCKET_NAME = 'darwin-raildata-mlops'
TEMP_PREFIX = 'temp-data'

from pyspark.sql import SparkSession
from pyspark.sql.functions import expr, col, lit
import re

def normalize_data_spark(**kwargs):
    ti = kwargs['ti']
    s3_key = ti.xcom_pull(task_ids='ingest_processed_csvs')
    s3_path = f"s3a://{BUCKET_NAME}/{s3_key}"

    spark = SparkSession.builder \
        .appName("NormalizeLocations") \
        .config("spark.driver.memory", "6g") \
        .config("spark.executor.memory", "6g") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.access.key", aws_access_key) \
        .config("spark.hadoop.fs.s3a.secret.key", aws_secret_key) \
        .config("spark.hadoop.fs.s3a.endpoint", f"s3.{region}.amazonaws.com") \
        .getOrCreate()

    df = spark.read.csv(s3_path, header=True, inferSchema=True)
    columns = df.columns

    # Identify location indices
    location_indices = sorted({
        int(m.group(1))
        for c in columns if (m := re.search(r"Location_(\d+)_", c))
    })

    # Base columns are everything before the first location_* group
    base_cols = []
    if location_indices:
        first_location_prefix = f"Location_{location_indices[0]}_@tpl"
        base_index = columns.index(first_location_prefix) if first_location_prefix in columns else len(columns)
        base_cols = columns[:base_index]

    # Find the suffixes (column names without Location_i_ prefix) by checking first group
    first_loc = location_indices[0] if location_indices else None
    loc_suffixes = []
    if first_loc is not None:
        loc_cols = [c for c in columns if c.startswith(f"Location_{first_loc}_")]
        loc_suffixes = [c.replace(f"Location_{first_loc}_", "") for c in loc_cols]

    # Build stack expression string
    # stack takes: n, (col1, col2, ..., col_m), (col1, col2, ..., col_m), ...
    # Each tuple corresponds to a location group.
    # First item is location_index (as string), followed by the columns for that location
    stack_expr_parts = []
    for i in location_indices:
        cols_for_i = [f"`Location_{i}_{suffix}`" for suffix in loc_suffixes]
        # Compose string: location_index, col1, col2, col3, ...
        part = f"'{i}', " + ", ".join(cols_for_i)
        stack_expr_parts.append(part)

    stack_expr = f"stack({len(location_indices)}, {', '.join(stack_expr_parts)}) as (location_index, {', '.join(loc_suffixes)})"

    # Select base columns + the stack expression
    select_exprs = base_cols + [expr(stack_expr)]

    # Run the query to normalize
    normalized_df = df.select(*base_cols, expr(stack_expr))

    # Write results
    parquet_output_path = (
        f"s3a://{BUCKET_NAME}/{LONG_DF_PREFIX}/"
        f"long_df_{datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S')}"
    )
    normalized_df.write.parquet(parquet_output_path, mode="overwrite")

    csv_output_path = s3_path.replace(TEMP_PREFIX, "normalized-output").rsplit("/", 1)[0]
    normalized_df.write.csv(csv_output_path, header=True, mode="overwrite")

    return {
        "csv_output": csv_output_path,
        "parquet_output": parquet_output_path
    }
