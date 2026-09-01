from PreProcessing.UsageProcessor import UsageProcessor

from spark.ingetision_module import raw_network_df

from spark.spark_cleaning import clean_network_data

from pyspark.sql.functions import col

single_day_df = raw_network_df.filter(
    col("source_file").contains("2013-11-01")
)

clean_network_df, rejected_df, null_profile = (
    clean_network_data(single_day_df)
)


# ==================================================
# Pandas path
# ==================================================

file_path = (
    r"C:\Users\aniruddh.singh"
    r"\Documents\Project_1\data\landing"
    r"\sms-call-internet-mi-2013-11-01.csv"
)

processor = UsageProcessor(
    file_path
)

processor.load_data()
processor.clean_data()
processor.derive_time_features()
processor.derive_activity_features()

pandas_result = (
    processor.aggregate_to_grid_time()
)

# ==================================================
# Spark path
# ==================================================

from pyspark.sql import functions as F


clean_network_df.select(
    F.sum(F.col("sms_in").isNull().cast("int")).alias("sms_in_nulls"),
    F.sum(F.col("sms_out").isNull().cast("int")).alias("sms_out_nulls"),
    F.sum(F.col("call_in").isNull().cast("int")).alias("call_in_nulls"),
    F.sum(F.col("call_out").isNull().cast("int")).alias("call_out_nulls"),
    F.sum(F.col("internet_activity").isNull().cast("int")).alias("internet_nulls")
).show()

spark_result = (

    clean_network_df

    .groupBy(
        "date",
        "hour",
        "grid_id"
    )

    .agg(
        F.sum("total_sms").alias(
            "total_sms"
        ),

        F.sum("total_calls").alias(
            "total_calls"
        ),

        F.sum("internet_activity").alias(
            "internet_activity"
        ),

        F.sum("total_activity").alias(
            "total_activity"
        )
    )
)

spark_pd = (
    spark_result
    .toPandas()
)

pandas_result = pandas_result.sort_values(
    ["date", "hour", "grid_id"]
).reset_index(drop=True)

spark_pd = spark_pd.sort_values(
    ["date", "hour", "grid_id"]
).reset_index(drop=True)

# ==================================================
# Validation
# ==================================================

assert (
    pandas_result["grid_id"].nunique()
    ==
    spark_pd["grid_id"].nunique()
), "Grid count mismatch"

assert round(
    pandas_result["total_sms"].sum(),
    5
) == round(
    spark_pd["total_sms"].sum(),
    5
), "SMS mismatch"

assert round(
    pandas_result["total_calls"].sum(),
    5
) == round(
    spark_pd["total_calls"].sum(),
    5
), "Calls mismatch"

assert round(
    pandas_result["total_activity"].sum(),
    5
) == round(
    spark_pd["total_activity"].sum(),
    5
), "Total activity mismatch"

print(
    "PASS: Spark and Pandas outputs match"
)