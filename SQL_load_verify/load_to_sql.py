import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
from sqlalchemy import create_engine

engine = create_engine(
    "mysql+pymysql://root:root@localhost:3306/telecom_project_1"
)

import pandas as pd

hourly_df = pd.read_parquet(
    "data/analytics/hourly_grid_summary"
)

dim_time = (

    hourly_df[
        [
            "timestamp",
            "date",
            "hour"
        ]
    ]

    .drop_duplicates()

    .copy()

)

dim_time["day_of_week"] = (
    pd.to_datetime(
        dim_time["date"]
    ).dt.dayofweek + 1
)

dim_time["month_number"] = (
    pd.to_datetime(
        dim_time["date"]
    ).dt.month
)

dim_time["year_number"] = (
    pd.to_datetime(
        dim_time["date"]
    ).dt.year
)

dim_time.rename(
    columns={
        "timestamp": "timestamp_value",
        "date": "date_value",
        "hour": "hour_of_day"
    },
    inplace=True
)

print("Loading dim_time...")

dim_time.to_sql(
    "dim_time",
    engine,
    if_exists="append",
    index=False
)

import json
import pandas as pd

with open(
    r"data\reference\milano-grid.geojson",
    "r",
    encoding="utf-8"
) as f:

    geojson = json.load(f)

grid_rows = []

for feature in geojson["features"]:

    grid_id = feature["properties"]["cellId"]

    coordinates = (
        feature["geometry"]["coordinates"][0]
    )

    longitudes = [
        point[0]
        for point in coordinates
    ]

    latitudes = [
        point[1]
        for point in coordinates
    ]

    centroid_longitude = (
        sum(longitudes)
        / len(longitudes)
    )

    centroid_latitude = (
        sum(latitudes)
        / len(latitudes)
    )

    grid_rows.append(
        {
            "grid_id": grid_id,
            "centroid_latitude":
                centroid_latitude,
            "centroid_longitude":
                centroid_longitude,
            "geometry_reference":
                f"milano-grid.geojson#{grid_id}"
        }
    )

print("Loading dim_grid...")

dim_grid = pd.DataFrame(
    grid_rows
)

dim_grid.to_sql(
    "dim_grid",
    engine,
    if_exists="append",
    index=False,
    chunksize=1000
)

print("Creating lookups...")

time_lookup = pd.read_sql(
    """
    SELECT
        time_key,
        timestamp_value
    FROM dim_time
    """,
    engine
)

grid_lookup = pd.read_sql(
    """
    SELECT
        grid_key,
        grid_id
    FROM dim_grid
    """,
    engine
)

fact_df = pd.read_parquet(
    "data/analytics/hourly_grid_summary"
)

fact_df = fact_df.merge(
    time_lookup,
    left_on="timestamp",
    right_on="timestamp_value",
    how="left"
)

fact_df = fact_df.merge(
    grid_lookup,
    on="grid_id",
    how="left"
)

fact_df = fact_df[
    [
        "time_key",
        "grid_key",
        "sms_in",
        "sms_out",
        "call_in",
        "call_out",
        "internet_activity",
        "total_sms",
        "total_calls",
        "total_activity"
    ]
]

print("Building fact table...")

fact_df.to_sql(
    "fact_network_activity",
    engine,
    if_exists="append",
    index=False,
    chunksize=50000,
    method="multi"
)

print("Load Complete")