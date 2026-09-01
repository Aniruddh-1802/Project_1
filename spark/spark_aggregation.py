from pyspark.sql import functions as F


def create_operational_kpis(clean_network_df):

    # ==================================================
    # COUNTRY-CODE -> GRID/TIMESTAMP COLLAPSE
    # ==================================================

    hourly_grid_summary = (

        clean_network_df

        .groupBy(
            "timestamp",
            "grid_id"
        )

        .agg(

            F.sum("sms_in")
            .alias("sms_in"),

            F.sum("sms_out")
            .alias("sms_out"),

            F.sum("call_in")
            .alias("call_in"),

            F.sum("call_out")
            .alias("call_out"),

            F.sum("internet_activity")
            .alias("internet_activity")

        )

        .withColumn(
            "total_sms",
            F.col("sms_in")
            +
            F.col("sms_out")
        )

        .withColumn(
            "total_calls",
            F.col("call_in")
            +
            F.col("call_out")
        )

        .withColumn(
            "total_activity",
            F.col("total_sms")
            +
            F.col("total_calls")
            +
            F.col("internet_activity")
        )

        .withColumn(
            "date",
            F.to_date("timestamp")
        )

        .withColumn(
            "hour",
            F.hour("timestamp")
        )

    )

    # ==================================================
    # DUPLICATE CHECK
    # ==================================================

    duplicate_count = (

        hourly_grid_summary

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
        f"FAIL: Found "
        f"{duplicate_count} duplicate "
        f"(grid_id,timestamp) records"
    )

    print(
        "PASS: No duplicate "
        "(grid_id,timestamp) records"
    )

    # ==================================================
    # DAILY TRAFFIC SUMMARY
    # ==================================================

    daily_traffic_summary = (

        hourly_grid_summary

        .groupBy("date")

        .agg(

            F.sum("total_sms")
            .alias("total_sms"),

            F.sum("total_calls")
            .alias("total_calls"),

            F.sum("internet_activity")
            .alias("internet_activity"),

            F.sum("total_activity")
            .alias("total_activity")

        )

    )

    # ==================================================
    # DAILY ACTIVITY BY GRID
    # ==================================================

    daily_activity_by_grid = (

        hourly_grid_summary

        .groupBy(
            "date",
            "grid_id"
        )

        .agg(

            F.sum(
                "total_activity"
            ).alias(
                "daily_activity"
            )

        )

    )

    # ==================================================
    # TOP 10 HOTSPOTS
    # ==================================================

    hotspot_ranking = (

        daily_activity_by_grid

        .orderBy(
            F.desc(
                "daily_activity"
            )
        )

        .limit(10)

    )

    # ==================================================
    # PEAK ACTIVITY HOUR
    # ==================================================

    peak_hour = (

        hourly_grid_summary

        .groupBy("date","hour")

        .agg(

            F.sum(
                "total_activity"
            ).alias(
                "hourly_activity"
            )

        )

        .orderBy(
            F.desc(
                "hourly_activity"
            )
        )

        .limit(1)

    )

    # ==================================================
    # INTERNET SHARE
    # ==================================================

    internet_share = (

        hourly_grid_summary

        .agg(

            (
                F.sum(
                    "internet_activity"
                )

                /

                F.sum(
                    "total_activity"
                )

            ).alias(
                "internet_share"
            )

        )

    )

    return (
        hourly_grid_summary,
        daily_traffic_summary,
        daily_activity_by_grid,
        hotspot_ranking,
        peak_hour,
        internet_share)