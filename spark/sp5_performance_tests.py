import time

from pyspark.sql.functions import broadcast

from spark.spark_cleaning import clean_network_data
from spark.spark_aggregation import create_operational_kpis
from spark.spark_geo_enrichment import (
    load_grid_lookup
)

from spark.ingetision_module import raw_network_df


# =====================================================
# PREPARE DATA
# =====================================================

clean_network_df, _, _ = (
    clean_network_data(raw_network_df)
)

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

spark = hourly_grid_summary.sparkSession

grid_lookup_df = (
    load_grid_lookup(
        spark,
        r"C:\Users\aniruddh.singh\Documents\Project_1\data\reference\milano-grid.geojson"
    )
)

# =====================================================
# TEST 1 - CACHE TIMING
# =====================================================

print("\nTEST 1 - CACHE TIMING")

start = time.time()

clean_network_df.count()

run1 = time.time() - start

start = time.time()

clean_network_df.count()

run2 = time.time() - start

print(f"Run 1: {run1:.2f} sec")
print(f"Run 2: {run2:.2f} sec")


# =====================================================
# TEST 2 - PARTITION COUNTS
# =====================================================

print("\nTEST 2 - PARTITIONS")

print(
    "Clean DF Partitions:",
    clean_network_df.rdd.getNumPartitions()
)

print(
    "Hourly Summary Partitions:",
    hourly_grid_summary.rdd.getNumPartitions()
)


# =====================================================
# TEST 3 - HOTSPOT PLAN
# =====================================================

print("\nTEST 3 - HOTSPOT PHYSICAL PLAN")

hotspot_ranking.explain(True)


# =====================================================
# TEST 4 - STANDARD JOIN PLAN
# =====================================================

print("\nTEST 4 - STANDARD JOIN PLAN")

hourly_grid_summary.join(
    grid_lookup_df,
    "grid_id",
    "left"
).explain(True)


# =====================================================
# TEST 5 - BROADCAST JOIN PLAN
# =====================================================

print("\nTEST 5 - BROADCAST JOIN PLAN")

hourly_grid_summary.join(
    broadcast(grid_lookup_df),
    "grid_id",
    "left"
).explain(True)


# =====================================================
# TEST 6 - COLUMN PRUNING
# =====================================================

print("\nTEST 6 - COLUMN PRUNING")

(
    hourly_grid_summary

    .select(
        "grid_id",
        "date",
        "total_activity"
    )

    .groupBy(
        "date",
        "grid_id"
    )

    .sum(
        "total_activity"
    )

).explain(True)