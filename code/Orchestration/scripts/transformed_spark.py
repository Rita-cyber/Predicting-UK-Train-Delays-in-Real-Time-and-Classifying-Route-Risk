import re
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, lit
from functools import reduce
from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
import sys

# Glue boilerplate
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

# Parameters
args = getResolvedOptions(sys.argv, ["INPUT_PATH", "OUTPUT_PATH"])
input_path = args["INPUT_PATH"]
output_path = args["OUTPUT_PATH"]



import re
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, lit
from functools import reduce

def normalize_locations_spark(spark, input_path: str) -> DataFrame:
    # Read CSV without inferring schema (faster for wide datasets)
    df = spark.read.option("header", True).csv(input_path)

    # Drop rows where all columns are null
    df = df.dropna(how="all")

    # Drop unwanted columns by regex
    drop_patterns = [
        r"^Pport_uR_TS_Location_plat$",
        r"^Pport_uR_TS_Location_\d+_plat$",
        r"^Pport_uR_TS_pass_@etmin$",
        r"^Pport_uR_TS_arr_@srcInst$"
    ]
    cols_to_drop = [c for c in df.columns if any(re.match(p, c) for p in drop_patterns)]
    if cols_to_drop:
        df = df.drop(*cols_to_drop)

    # Identify location indices
    sorted_indices = sorted(
        {int(m.group(1)) for c in df.columns for m in [re.search(r'Location_(\d+)_', c)] if m}
    )

    # Determine base columns
    first_location_prefix = f"Location_{sorted_indices[0]}_@tpl" if sorted_indices else None
    base_index = df.columns.index(first_location_prefix) if first_location_prefix in df.columns else len(df.columns)
    base_cols = df.columns[:base_index]

    # Build normalized DataFrames for each location index
    normalized_rows = []
    for i in sorted_indices:
        allowed_cols = [
            c for c in df.columns
            if f"Location_{i}_" in c
            and not re.search(r'(pass_@etmin|arr_@srcInst)$', c)
        ]
        if not allowed_cols:
            continue

        renamed_cols = [col(c).alias(c.replace(f"Location_{i}_", "")) for c in allowed_cols]
        temp_df = df.select(*[col(c) for c in base_cols if c in df.columns], *renamed_cols)
        temp_df = temp_df.withColumn("location_index", lit(i))
        normalized_rows.append(temp_df)

    # Combine all normalized DataFrames
    if normalized_rows:
        result_df = reduce(lambda a, b: a.unionByName(b, allowMissingColumns=True), normalized_rows)

        # Drop any unwanted leftover columns just in case
        bad_patterns = [
            r"^Pport_uR_TS_pass_@etmin$",
            r"^Pport_uR_TS_arr_@srcInst$"
        ]
        leftover_to_drop = [c for c in result_df.columns if any(re.match(p, c) for p in bad_patterns)]
        if leftover_to_drop:
            result_df = result_df.drop(*leftover_to_drop)

        return result_df
    else:
        return df.limit(0)

# Call normalization
normalized_df = normalize_locations_spark(spark, input_path)

# Write output to S3 as Parquet
normalized_df.write.mode("overwrite").parquet(output_path)
