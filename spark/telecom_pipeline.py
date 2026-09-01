import argparse
import logging
import os
import sys
from datetime import datetime

from pyspark.sql import SparkSession

import os

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

os.environ["HADOOP_HOME"] = r"C:\hadoop\hadoop-3.3.6"
os.environ["PATH"] += os.pathsep + r"C:\hadoop\hadoop-3.3.6\bin"

sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)

from ingetision_module import (
    load_raw_network_data
)

from spark_cleaning import (
    clean_network_data
)

from spark_aggregation import (
    create_operational_kpis
)

from spark_geo_enrichment import (
    load_grid_lookup,
    enrich_with_geography
)

from output_layer import (
    write_outputs,
    validate_outputs
)

# ==========================================
# Logging
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    )
)

logger = logging.getLogger(__name__)

# ==========================================
# Read Raw
# ==========================================


def read_raw(
    spark,
    input_path
):

    logger.info(
        "Reading files from %s",
        input_path
    )

    raw_network_df = (
        load_raw_network_data(
            spark,
            input_path
        )
    )

    input_rows = (
        raw_network_df.count()
    )

    logger.info(
        "Input Rows: %s",
        input_rows
    )

    return raw_network_df


# ==========================================
# Clean
# ==========================================

def clean(
    raw_network_df
):

    (
        clean_network_df,
        rejected_df,
        null_profile

    ) = clean_network_data(
        raw_network_df
    )

    rejected_rows = (
        rejected_df.count()
    )

    clean_rows = (
        clean_network_df.count()
    )

    logger.info(
        "Rejected Rows: %s",
        rejected_rows
    )

    logger.info(
        "Clean Rows: %s",
        clean_rows
    )

    logger.info(
        "Null Handling Summary"
    )

    null_profile.show(
        truncate=False
    )

    return (
        clean_network_df,
        rejected_df,
        null_profile
    )


# ==========================================
# Aggregate
# ==========================================

def aggregate(
    clean_network_df
):

    (
        hourly_grid_summary,
        daily_traffic_summary,
        daily_activity_by_grid,
        hotspot_ranking,
        peak_hour,
        internet_share

    ) = create_operational_kpis(
        clean_network_df
    )

    logger.info(
        "Hourly Grid Summary Rows: %s",
        hourly_grid_summary.count()
    )

    return (
        hourly_grid_summary,
        daily_traffic_summary,
        daily_activity_by_grid,
        hotspot_ranking,
        peak_hour,
        internet_share
    )


# ==========================================
# Enrich
# ==========================================

def enrich(
    spark,
    reference_path,
    hourly_grid_summary
):

    geojson_path = os.path.join(
        reference_path,
        "milano-grid.geojson"
    )

    if not os.path.exists(
        geojson_path
    ):

        raise FileNotFoundError(
            f"GeoJSON not found: "
            f"{geojson_path}"
        )

    grid_lookup_df = (
        load_grid_lookup(
            spark,
            geojson_path
        )
    )

    (
        grid_activity_geo_df,
        unmatched_grid_df,
        top_hotspots_geo

    ) = enrich_with_geography(
        hourly_grid_summary,
        grid_lookup_df
    )

    logger.info(
        "Unmatched Grid IDs: %s",
        unmatched_grid_df.count()
    )

    return (
        grid_activity_geo_df,
        unmatched_grid_df,
        top_hotspots_geo
    )


# ==========================================
# Write Outputs
# ==========================================

def save_outputs(
    spark,
    output_path,
    clean_network_df,
    hourly_grid_summary,
    daily_traffic_summary
):

    processed_activity_path = os.path.join(
        output_path,
        "processed",
        "activity"
    )

    hourly_summary_path = os.path.join(
        output_path,
        "analytics",
        "hourly_grid_summary"
    )

    dashboard_summary_path = os.path.join(
        output_path,
        "analytics",
        "dashboard_summary"
    )

    write_outputs(
        clean_network_df,
        hourly_grid_summary,
        daily_traffic_summary,
        processed_activity_path,
        hourly_summary_path,
        dashboard_summary_path
    )

    validate_outputs(
        spark,
        hourly_summary_path,
        hourly_grid_summary
    )

    logger.info(
        "Output validation successful."
    )


# ==========================================
# Main
# ==========================================

def main():

    parser = argparse.ArgumentParser(
        description="Telecom Processing Pipeline"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Landing data path"
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output root path"
    )

    parser.add_argument(
        "--reference",
        required=True,
        help="Reference data path"
    )

    args = parser.parse_args()

    start_time = datetime.now()

    logger.info(
        "Pipeline Started"
    )

    spark = (

        SparkSession.builder

        .appName(
            "TelecomPipeline"
        )

        .config(
            "spark.driver.memory",
            "4g"
        )

        .config(
            "spark.executor.memory",
            "4g"
        )

        .config(
            "spark.sql.shuffle.partitions",
            "50"
        )

        .getOrCreate()

    )

    try:

        # ==================================
        # READ
        # ==================================

        raw_network_df = (
            read_raw(
                spark,
                args.input
            )
        )

        # ==================================
        # CLEAN
        # ==================================

        (
            clean_network_df,
            rejected_df,
            null_profile

        ) = clean(
            raw_network_df
        )

        # ==================================
        # AGGREGATE
        # ==================================

        (
            hourly_grid_summary,
            daily_traffic_summary,
            daily_activity_by_grid,
            hotspot_ranking,
            peak_hour,
            internet_share

        ) = aggregate(
            clean_network_df
        )

        # ==================================
        # ENRICH
        # ==================================

        (
            grid_activity_geo_df,
            unmatched_grid_df,
            top_hotspots_geo

        ) = enrich(
            spark,
            args.reference,
            hourly_grid_summary
        )

        # ==================================
        # OUTPUTS
        # ==================================

        save_outputs(
            spark,
            args.output,
            clean_network_df,
            hourly_grid_summary,
            daily_traffic_summary
        )

        end_time = datetime.now()

        logger.info(
            "Pipeline Status: SUCCESS"
        )

        logger.info(
            "Start Time: %s",
            start_time
        )

        logger.info(
            "End Time: %s",
            end_time
        )

        logger.info(
            "Duration: %s",
            end_time - start_time
        )

    except Exception as ex:

        logger.exception(
            "Pipeline Failed"
        )

        logger.exception(
            str(ex)
        )

        sys.exit(1)

    finally:

        spark.stop()


if __name__ == "__main__":
    main()