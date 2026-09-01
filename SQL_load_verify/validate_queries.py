from sqlalchemy import create_engine
import pandas as pd

# ==========================================
# MySQL Connection
# ==========================================

engine = create_engine(
    "mysql+pymysql://root:root@localhost:3306/telecom_project_1"
)

# ==========================================
# Query 1
# Top Activity Grids
# ==========================================

top_grids_query = """
SELECT
    g.grid_id,
    SUM(f.total_activity) AS activity
FROM fact_network_activity f
JOIN dim_grid g
    ON f.grid_key = g.grid_key
GROUP BY g.grid_id
ORDER BY activity DESC
LIMIT 10;
"""

top_grids = pd.read_sql(
    top_grids_query,
    engine
)

print("\n" + "=" * 60)
print("TOP 10 HOTSPOT GRIDS")
print("=" * 60)

print(top_grids)

# ==========================================
# Query 2
# Hourly Trend
# ==========================================

hourly_trend_query = """
SELECT
    t.hour_of_day,
    SUM(f.total_activity) AS total_activity
FROM fact_network_activity f
JOIN dim_time t
    ON f.time_key = t.time_key
GROUP BY t.hour_of_day
ORDER BY t.hour_of_day;
"""

hourly_trend = pd.read_sql(
    hourly_trend_query,
    engine
)

print("\n" + "=" * 60)
print("HOURLY TREND")
print("=" * 60)

print(hourly_trend)

# ==========================================
# Query 3
# Internet Heavy Windows
# ==========================================

internet_heavy_query = """
SELECT
    t.timestamp_value,
    SUM(f.internet_activity) AS internet_usage
FROM fact_network_activity f
JOIN dim_time t
    ON f.time_key = t.time_key
GROUP BY t.timestamp_value
ORDER BY internet_usage DESC
LIMIT 20;
"""

internet_heavy = pd.read_sql(
    internet_heavy_query,
    engine
)

print("\n" + "=" * 60)
print("TOP INTERNET HEAVY WINDOWS")
print("=" * 60)

print(internet_heavy)

# ==========================================
# Extra Validation Counts
# ==========================================

fact_count = pd.read_sql(
    """
    SELECT COUNT(*) AS row_count
    FROM fact_network_activity
    """,
    engine
)

grid_count = pd.read_sql(
    """
    SELECT COUNT(*) AS row_count
    FROM dim_grid
    """,
    engine
)

time_count = pd.read_sql(
    """
    SELECT COUNT(*) AS row_count
    FROM dim_time
    """,
    engine
)

print("\n" + "=" * 60)
print("TABLE COUNTS")
print("=" * 60)

print(
    f"dim_time rows: "
    f"{time_count.iloc[0]['row_count']}"
)