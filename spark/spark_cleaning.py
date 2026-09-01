import os

os.environ["HADOOP_HOME"] = r"C:\hadoop\hadoop-3.3.6"
os.environ["PATH"] += os.pathsep + r"C:\hadoop\hadoop-3.3.6\bin"
from pyspark.sql.functions import (
    col,
    to_timestamp,
    to_date,
    hour,
    dayofweek,
    when,
    sum as spark_sum
)

COLUMN_MAPPING = {
    "datetime": "timestamp",
    "CellID": "grid_id",
    "countrycode": "country_code",
    "smsin": "sms_in",
    "smsout": "sms_out",
    "callin": "call_in",
    "callout": "call_out",
    "internet": "internet_activity"
}


def clean_network_data(raw_network_df):

    original_count = raw_network_df.count()

    df = raw_network_df

    # -----------------------------------------
    # Rename columns
    # -----------------------------------------

    for old_name, new_name in COLUMN_MAPPING.items():

        if (
            old_name in df.columns
            and new_name not in df.columns
        ):
            df = df.withColumnRenamed(
                old_name,
                new_name
            )

    # -----------------------------------------
    # Cast fields
    # -----------------------------------------

    df = (
        df
        .withColumn(
            "sms_in",
            col("sms_in").cast("double")
        )
        .withColumn(
            "sms_out",
            col("sms_out").cast("double")
        )
        .withColumn(
            "call_in",
            col("call_in").cast("double")
        )
        .withColumn(
            "call_out",
            col("call_out").cast("double")
        )
        .withColumn(
            "internet_activity",
            col("internet_activity")
            .cast("double")
        )
    )

    # -----------------------------------------
    # Verify hourly cadence
    # -----------------------------------------

    cadence_count = (
        df.select(
            hour("timestamp")
            .alias("hour")
        )
        .distinct()
        .count()
    )

    print(
        f"Distinct Hours Found: "
        f"{cadence_count}"
    )

    # -----------------------------------------
    # Null profile
    # -----------------------------------------

    null_profile = df.select(

        spark_sum(
            when(
                col("sms_in").isNull(),
                1
            ).otherwise(0)
        ).alias("sms_in_nulls"),

        spark_sum(
            when(
                col("sms_out").isNull(),
                1
            ).otherwise(0)
        ).alias("sms_out_nulls"),

        spark_sum(
            when(
                col("call_in").isNull(),
                1
            ).otherwise(0)
        ).alias("call_in_nulls"),

        spark_sum(
            when(
                col("call_out").isNull(),
                1
            ).otherwise(0)
        ).alias("call_out_nulls"),

        spark_sum(
            when(
                col("internet_activity").isNull(),
                1
            ).otherwise(0)
        ).alias("internet_activity_nulls")
    )

    # -----------------------------------------
    # Rejected rows
    # -----------------------------------------

    rejected_df = df.filter(

        col("grid_id").isNull()

        |

        col("timestamp").isNull()

        |

        (col("sms_in") < 0)

        |

        (col("sms_out") < 0)

        |

        (col("call_in") < 0)

        |

        (col("call_out") < 0)

        |

        (col("internet_activity") < 0)

    )

    rejected_count = rejected_df.count()

    # -----------------------------------------
    # Keep valid rows
    # -----------------------------------------

    clean_df = df.filter(

    col("grid_id").isNotNull()

    &

    col("timestamp").isNotNull()

    &

    (
        col("sms_in").isNull()
        | (col("sms_in") >= 0)
    )

    &

    (
        col("sms_out").isNull()
        | (col("sms_out") >= 0)
    )

    &

    (
        col("call_in").isNull()
        | (col("call_in") >= 0)
    )

    &

    (
        col("call_out").isNull()
        | (col("call_out") >= 0)
    )

    &

    (
        col("internet_activity").isNull()
        | (col("internet_activity") >= 0)
    )

)


    # -----------------------------------------
    # Curated layer null rule
    # -----------------------------------------

    clean_df = clean_df.fillna(
        0,
        subset=[
            "sms_in",
            "sms_out",
            "call_in",
            "call_out",
            "internet_activity"
        ]
    )

    # -----------------------------------------
    # Derived metrics
    # -----------------------------------------

    clean_df = (

        clean_df

        .withColumn(
            "total_sms",
            col("sms_in")
            + col("sms_out")
        )

        .withColumn(
            "total_calls",
            col("call_in")
            + col("call_out")
        )

        .withColumn(
            "total_activity",
            col("total_sms")
            + col("total_calls")
            + col("internet_activity")
        )
    )

    # -----------------------------------------
    # Date features
    # -----------------------------------------

    clean_df = (

        clean_df

        .withColumn(
            "date",
            to_date("timestamp")
        )

        .withColumn(
            "hour",
            hour("timestamp")
        )

        .withColumn(
            "day_of_week",
            dayofweek("timestamp")
        )
    )

    clean_count = clean_df.count()

    print("\nRECORD SUMMARY")
    print(f"Original Rows: {original_count}")
    print(f"Rejected Rows: {rejected_count}")
    print(f"Clean Rows: {clean_count}")
    print(
    "Grids in clean_df:",
    clean_df.select("grid_id")
    .distinct()
    .count()
)

    return (
        clean_df,
        rejected_df,
        null_profile
    )