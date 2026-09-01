import json

from pyspark.sql import Row
from pyspark.sql import functions as F
from pyspark.sql.functions import broadcast


def load_grid_lookup(
    spark,
    geojson_path
):
    """
    Flatten GeoJSON into:

    grid_id
    geometry
    """

    with open(
        geojson_path,
        "r",
        encoding="utf-8"
    ) as f:

        geojson = json.load(f)

    rows = []

    for feature in geojson["features"]:

        rows.append(

            Row(

                grid_id=int(
                    feature["properties"]["cellId"]
                ),

                feature_id=int(
                    feature["id"]
                ),

                geometry=json.dumps(
                    feature["geometry"]
                )

            )

        )

    grid_lookup_df = spark.createDataFrame(
        rows
    )

    return grid_lookup_df


def enrich_with_geography(
    hourly_grid_summary,
    grid_lookup_df
):

    # ==================================
    # BEFORE JOIN METRICS
    # ==================================

    activity_grids = (

        hourly_grid_summary

        .select("grid_id")

        .distinct()

        .count()

    )

    print(
        f"Activity Grids: "
        f"{activity_grids}"
    )

    # ==================================
    # BROADCAST LEFT JOIN
    # ==================================

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

    # ==================================
    # COVERAGE
    # ==================================

    matched_grids = (

        grid_activity_geo_df

        .filter(
            F.col(
                "geometry"
            ).isNotNull()
        )

        .select("grid_id")
        .distinct()

        .count()

    )

    unmatched_grid_df = (

        grid_activity_geo_df

        .filter(
            F.col(
                "geometry"
            ).isNull()
        )

        .select("grid_id")
        .distinct()

    )

    unmatched_count = (
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

    print(
        "\nGRID ENRICHMENT REPORT"
    )

    print(
        f"Matched Grids: "
        f"{matched_grids}"
    )

    print(
        f"Unmatched Grids: "
        f"{unmatched_count}"
    )

    print(
        f"Coverage %: "
        f"{coverage_pct}"
    )

    # ==================================
    # HOTSPOTS WITH GEOMETRY
    # ==================================

    top_hotspots = (

        grid_activity_geo_df

        .groupBy(
            "grid_id",
            "geometry"
        )

        .agg(

            F.sum(
                "total_activity"
            ).alias(
                "total_activity"
            )

        )

        .orderBy(
            F.desc(
                "total_activity"
            )
        )

        .limit(10)

    )

    return (
        grid_activity_geo_df,
        unmatched_grid_df,
        top_hotspots
    )

def calculate_centroid(
    geometry_dict
):

    coords = geometry_dict[
        "coordinates"
    ][0]

    lons = [
        p[0]
        for p in coords
    ]

    lats = [
        p[1]
        for p in coords
    ]

    centroid_lon = (
        sum(lons)
        /
        len(lons)
    )

    centroid_lat = (
        sum(lats)
        /
        len(lats)
    )

    return (
        centroid_lon,
        centroid_lat
    )