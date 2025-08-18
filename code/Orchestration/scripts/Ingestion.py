import io
import boto3
import pandas as pd


import sys
from awsglue.utils import getResolvedOptions

# Define the expected arguments
args_list = ['JOB_NAME', 'BUCKET', 'OUTPUT_BUCKET', 'PREFIX', 'OUTPUT_KEY']

# Retrieve the arguments
args = getResolvedOptions(sys.argv, args_list)

# Assign them to variables
job_name = args['JOB_NAME']
bucket = args['BUCKET']
output_bucket = args['OUTPUT_BUCKET']
prefix = args['PREFIX']
output_key = args['OUTPUT_KEY']
optional_setting = args.get('OPTIONAL_SETTING', 'default_value_if_not_provided')

# Use the parameters in your job logic
print(f"Running Glue job: {job_name}")
print(f"output_bucket: {output_bucket}")
print(f"bucket: {bucket}")
print(f"prefix: {prefix}")
print(f"output_key: {output_key}")
print(f"Optional setting: {optional_setting}")

# Your actual job logic would go here, using these parameters
# For example, reading data from source_path and writing to target_path
def load_all_processed_csvs(bucket,prefix,output_bucket,output_key):
    """
    Loads all CSVs from an S3 bucket/prefix, concatenates them into a single DataFrame,
    and optionally saves the combined DataFrame back to S3.
    """
    s3_client = boto3.client('s3')
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    dfs = []

    for obj in response.get('Contents', []):
        key = obj['Key']
        if key.endswith('.csv'):
            print(f"Reading {key} ...")
            csv_obj = s3_client.get_object(Bucket=bucket, Key=key)
            df = pd.read_csv(io.BytesIO(csv_obj['Body'].read()))
            dfs.append(df)

    combined_df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    if output_bucket and output_key:
        csv_buffer = io.StringIO()
        combined_df.to_csv(csv_buffer, index=False)
        s3_client.put_object(
            Bucket=output_bucket,
            Key=output_key,
            Body=csv_buffer.getvalue()
        )
        print(f"✅ Combined CSV saved to s3://{output_bucket}/{output_key}")

    return combined_df
    
# Call the function with Glue parameters
#df = load_all_processed_csvs(bucket, prefix, output_bucket, output_key)

# Run function with arguments from Glue
load_all_processed_csvs(
    bucket=args['BUCKET'],
    prefix=args['PREFIX'],
    output_bucket=args['OUTPUT_BUCKET'],
    output_key=args['OUTPUT_KEY']
)

