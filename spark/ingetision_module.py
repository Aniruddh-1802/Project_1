from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    input_file_name,
    col,
    hour,
    to_timestamp
)
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    DoubleType
)

import glob


# ==========================================
# Spark Session
# ==========================================

spark = (
    SparkSession.builder
    .appName("TelecomProject")
    .config(
        "spark.driver.memory",
        "4g"
    )
    .config(
        "spark.executor.memory",
        "4g"
    )
    .getOrCreate()
)


# ==========================================
# Manual Schema
# ==========================================

network_schema = StructType([
    StructField("datetime", StringType(), True),
    StructField("CellID", IntegerType(), True),
    StructField("countrycode", IntegerType(), True),
    StructField("smsin", DoubleType(), True),
    StructField("smsout", DoubleType(), True),
    StructField("callin", DoubleType(), True),
    StructField("callout", DoubleType(), True),
    StructField("internet", DoubleType(), True)
])


# ==========================================
# Reusable Function
# ==========================================

def load_raw_network_data(
    spark,
    input_path
):

    files = glob.glob(
        f"{input_path}/sms-call-internet-mi-*.csv"
    )

    if not files:

        raise FileNotFoundError(
            f"No telecom activity files found in {input_path}"
        )

    print(
        f"Found {len(files)} files"
    )

    for file in files:
        print(file)

    raw_network_df = (

        spark.read

        .option(
            "header",
            True
        )

        .schema(
            network_schema
        )

        .csv(
            files
        )

    )

    raw_network_df = (

        raw_network_df

        .withColumn(
            "source_file",
            input_file_name()
        )

        .withColumn(
            "timestamp",
            to_timestamp(
                col("datetime")
            )
        )

        .withColumn(
            "hour",
            hour(
                col("timestamp")
            )
        )

    )

    return raw_network_df


# ==========================================
# Legacy Behaviour
# ==========================================

# raw_network_df = load_raw_network_data(
#     r"C:\Users\aniruddh.singh\Documents\Project_1\data\landing"
# )