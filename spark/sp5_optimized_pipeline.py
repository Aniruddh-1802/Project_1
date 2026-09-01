from pyspark.sql.functions import (
    broadcast
)

from spark.spark_cleaning import (
    clean_network_data
)

from spark.spark_aggregation import (
    create_operational_kpis
)

from spark.spark_geo_enrichment import (
    load_grid_lookup
)

from spark.ingetision_module import (
    raw_network_df
)

# =====================================================
# CLEAN + CACHE
# =====================================================

clean_network_df, _, _ = (
    clean_network_data(
        raw_network_df
    )
)

clean_network_df = (
    clean_network_df
    .cache()
)

# materialize cache

clean_network_df.count()

# =====================================================
# REPARTITION
# =====================================================

clean_network_df = (
    clean_network_df
    .repartition(
        24,
        "date"
    )
)

print(
    "Partitions:",
    clean_network_df.rdd.getNumPartitions()
)

# =====================================================
# AGGREGATIONS
# =====================================================

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

# =====================================================
# COLUMN PRUNING
# =====================================================

hotspot_source = (

    hourly_grid_summary

    .select(
        "grid_id",
        "date",
        "total_activity"
    )

)

top_hotspots = (

    hotspot_source

    .groupBy(
        "date",
        "grid_id"
    )

    .sum(
        "total_activity"
    )

)

# =====================================================
# GRID LOOKUP
# =====================================================

spark = (
    hourly_grid_summary.sparkSession
)

grid_lookup_df = (
    load_grid_lookup(
        spark,
        r"C:\Users\aniruddh.singh\Documents\Project_1\data\reference\milano-grid.geojson"
    )
)

# =====================================================
# BROADCAST JOIN
# =====================================================

grid_activity_geo_df = (

    hourly_grid_summary

    .join(
        broadcast(
            grid_lookup_df
        ),
        "grid_id",
        "left"
    )

)

print(
    "\nOptimized pipeline ready."
)