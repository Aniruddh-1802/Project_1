from spark.spark_aggregation import (
    create_operational_kpis
)

from spark.spark_cleaning import (
    clean_network_data
)

from spark.ingetision_module import (
    raw_network_df
)

(
    clean_network_df,
    rejected_df,
    null_profile

) = clean_network_data(
    raw_network_df
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

print("\nHOURLY GRID SUMMARY")

hourly_grid_summary.show(5)

print("\nDAILY TRAFFIC SUMMARY")

daily_traffic_summary.show()

print("\nTOP 10 HOTSPOTS")

hotspot_ranking.show()

print("\nPEAK HOUR")

peak_hour.show()

print("\nINTERNET SHARE")

internet_share.show()