from pyspark.sql import functions as F


def write_outputs(
    clean_network_df,
    hourly_grid_summary,
    daily_traffic_summary,
    activity_output_path,
    hourly_output_path,
    dashboard_output_path
):

    # ==================================
    # CLEAN ACTIVITY
    # ==================================

    (
        clean_network_df

        .write

        .mode("overwrite")

        .partitionBy("date")

        .parquet(
            activity_output_path
        )
    )

    # ==================================
    # HOURLY GRID SUMMARY
    # ==================================

    (
        hourly_grid_summary

        .write

        .mode("overwrite")

        .parquet(
            hourly_output_path
        )
    )

    # ==================================
    # DASHBOARD CSV
    # ==================================

    (
        daily_traffic_summary

        .coalesce(1)

        .write

        .mode("overwrite")

        .option(
            "header",
            True
        )

        .csv(
            dashboard_output_path
        )
    )

    print(
        "\nOutputs Written Successfully"
    )

def validate_outputs(
    spark,
    hourly_output_path,
    hourly_grid_summary
):

    reloaded_df = (

        spark

        .read

        .parquet(
            hourly_output_path
        )

    )

    print(
        "\nROUND TRIP VALIDATION"
    )

    print(
        "Original Rows:",
        hourly_grid_summary.count()
    )

    print(
        "Reloaded Rows:",
        reloaded_df.count()
    )

    reloaded_df.printSchema()

    duplicate_count = (

        reloaded_df

        .groupBy(
            "grid_id",
            "timestamp"
        )

        .count()

        .filter(
            F.col("count") > 1
        )

        .count()

    )

    assert duplicate_count == 0, (
        f"Found {duplicate_count} duplicates"
    )

    print(
        "PASS: No duplicate "
        "(grid_id,timestamp) records"
    )
