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
import json
import pickle
from datetime import datetime
#import mlflow
import boto3
import pickle
import os
import numpy as np
import awswrangler as wr
import warnings
warnings.filterwarnings("ignore")

PROCESSED_KEYS_FILE = "tracking/processed_keys.json"

import sys
from awsglue.utils import getResolvedOptions

# Define the expected arguments
args_list = ['JOB_NAME', 'INPUT_PATH', 'OUTPUT_PATH']

# Retrieve the arguments
args = getResolvedOptions(sys.argv, args_list)

# Assign them to variables
job_name = args['JOB_NAME']
input_path = args['INPUT_PATH']
output_path = args['OUTPUT_PATH']
optional_setting = args.get('OPTIONAL_SETTING', 'default_value_if_not_provided')


import awswrangler as wr


def preprocess_for_arrival_delay(input_path, output_path):
    """
    Reads Parquet data from S3 with only required columns, calculates arrival delay,
    filters unreasonable values, adds day_of_week, and writes back to S3 as Parquet.
    """
    # Specify only the columns needed
    required_columns = [
        "Pport_uR_TS_@ssd",
        "Pport_uR_TS_Location_@wta",
        "Pport_uR_TS_Location_arr_@at"
    ]

    # --- Read only required columns from S3 ---
    df = wr.s3.read_parquet(path=input_path, columns=required_columns)

    # Drop completely empty rows
    df = df.dropna(how='all')

    # Parse service date
    df['service_date'] = pd.to_datetime(df['Pport_uR_TS_@ssd'], errors='coerce').dt.date

    # Scheduled and actual arrival datetime
    df['scheduled_arrival_dt'] = pd.to_datetime(
        df['service_date'].astype(str) + ' ' + df['Pport_uR_TS_Location_@wta'],
        errors='coerce'
    )
    df['actual_arrival_dt'] = pd.to_datetime(
        df['service_date'].astype(str) + ' ' + df['Pport_uR_TS_Location_arr_@at'],
        errors='coerce'
    )

    # Calculate delay in minutes
    df['arrival_delay_minutes'] = (
        df['actual_arrival_dt'] - df['scheduled_arrival_dt']
    ).dt.total_seconds() / 60.0

    # Filter by reasonable delays (-5 to 120 minutes)
    df_filtered = df[(df['arrival_delay_minutes'] >= -5) &
                     (df['arrival_delay_minutes'] <= 120)].copy()

    # Add day of week
    df_filtered['day_of_week'] = pd.to_datetime(df_filtered['Pport_uR_TS_@ssd'], errors='coerce').dt.dayofweek

    # Write cleaned data back to S3
    wr.s3.to_parquet(df=df_filtered, path=output_path, dataset=True, index=False)

    print(f"✅ Processed {len(df_filtered)} rows and saved to {output_path}")

    
# Run function with arguments from Glue
preprocess_for_arrival_delay(
    input_path=args['INPUT_PATH'],
    output_path=args['OUTPUT_PATH']
)

