import json

from pyspark.sql import functions as F
from pyspark.sql.functions import broadcast

from spark.ingetision_module import raw_network_df

from spark.spark_cleaning import (
    clean_network_data
)

from spark.spark_aggregation import (
    create_operational_kpis
)

from spark.spark_geo_enrichment import (
    load_grid_lookup,
    enrich_with_geography,
    calculate_centroid
)


# =====================================================
# SP2 CLEANING
# =====================================================


(
    clean_network_df,
    rejected_df,
    null_profile

) = clean_network_data(
    raw_network_df
)


# =====================================================
# SP3 AGGREGATIONS
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
# LOAD GEOJSON LOOKUP
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

print("\nGRID LOOKUP")

grid_lookup_df.show(
    5,
    truncate=False
)


# =====================================================
# ENRICH ACTIVITY WITH GEOGRAPHY
# =====================================================

(
    grid_activity_geo_df,
    unmatched_grid_df,
    top_hotspots_geo

) = enrich_with_geography(
    hourly_grid_summary,
    grid_lookup_df
)


# =====================================================
# COVERAGE REPORT
# =====================================================

activity_grids = (

    hourly_grid_summary

    .select("grid_id")

    .distinct()

    .count()

)

matched_grids = (

    grid_activity_geo_df

    .filter(
        F.col("geometry")
        .isNotNull()
    )

    .select("grid_id")

    .distinct()

    .count()

)

unmatched_grids = (
    unmatched_grid_df.count()
)

coverage_pct = round(
    (
        matched_grids
        /
        activity_grids
    ) * 100,
    2
)

print("\nGRID ENRICHMENT COVERAGE REPORT")

print(
    f"Activity Grids: {activity_grids}"
)

print(
    f"Matched Grids: {matched_grids}"
)

print(
    f"Unmatched Grids: {unmatched_grids}"
)

print(
    f"Coverage %: {coverage_pct}"
)


# =====================================================
# UNMATCHED GRID IDS
# =====================================================

print("\nUNMATCHED GRID IDS")

unmatched_grid_df.show(
    truncate=False
)


# =====================================================
# ENRICHED DATA SAMPLE
# =====================================================

print("\nGRID ACTIVITY GEO DATA")

grid_activity_geo_df.select(
    "timestamp",
    "grid_id",
    "total_activity",
    "geometry"
).show(
    5,
    truncate=False
)


# =====================================================
# HOTSPOTS WITH GEOMETRY
# =====================================================

print("\nTOP HIGH ACTIVITY GRIDS WITH GEOMETRY")

top_hotspots_geo.show(
    truncate=False
)


# =====================================================
# CENTROID VALIDATION
# =====================================================

print("\nCENTROID VALIDATION")

validation_grids = [
    1,
    5161,
    5259
]

for grid_id in validation_grids:

    rows = (

        grid_lookup_df

        .filter(
            F.col("grid_id")
            == grid_id
        )

        .collect()

    )

    if not rows:

        print(
            f"Grid {grid_id}: NOT FOUND"
        )

        continue

    geometry_dict = json.loads(
        rows[0]["geometry"]
    )

    centroid_lon, centroid_lat = (
        calculate_centroid(
            geometry_dict
        )
    )

    print(

        f"Grid {grid_id}"

        f" | Longitude: {centroid_lon:.6f}"

        f" | Latitude: {centroid_lat:.6f}"

    )