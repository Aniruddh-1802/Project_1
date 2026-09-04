-- DE6 validation queries
-- Run against telecom_warehouse_de6, loaded by de6_warehouse.py.
-- These are the "validated sample queries" named as DE6's expected output.
--
-- Verified against a real load (2026-09-04):
--   dim_grid: 10000 rows, 10000 distinct grid_id (matches DE6 spec exactly)
--   fact_network_activity: 1,679,994 rows == hourly_grid_summary row count (no fan-out)
--   0 duplicate (grid_id, time_key) pairs
--   Query 1's top row (grid_id 5161, total_activity 1789842.579) was hand-checked
--   against SUM(total_activity) for grid_id 5161 read directly from the
--   hourly_grid_summary parquet output - both give 1789842.579.

-- ------------------------------------------------------------------
-- 1. Top grids by total activity
-- ------------------------------------------------------------------
SELECT
    f.grid_id,
    g.centroid_latitude,
    g.centroid_longitude,
    SUM(f.total_activity) AS total_activity
FROM fact_network_activity f
JOIN dim_grid g ON g.grid_id = f.grid_id
GROUP BY f.grid_id, g.centroid_latitude, g.centroid_longitude
ORDER BY total_activity DESC
LIMIT 10;

-- ------------------------------------------------------------------
-- 2. Hourly trend: total activity by hour of day, across all grids
-- ------------------------------------------------------------------
SELECT
    t.hour,
    SUM(f.total_activity) AS total_activity
FROM fact_network_activity f
JOIN dim_time t ON t.time_key = f.time_key
GROUP BY t.hour
ORDER BY t.hour;

-- ------------------------------------------------------------------
-- 3. Internet-heavy windows: hours where internet activity makes up
--    more than half of total activity, by grid
-- ------------------------------------------------------------------
SELECT
    f.grid_id,
    t.timestamp,
    f.internet_activity,
    f.total_activity,
    ROUND(f.internet_activity / f.total_activity, 4) AS internet_share
FROM fact_network_activity f
JOIN dim_time t ON t.time_key = f.time_key
WHERE f.total_activity > 0
  AND (f.internet_activity / f.total_activity) > 0.5
ORDER BY internet_share DESC
LIMIT 20;

-- ------------------------------------------------------------------
-- 4. Row-count sanity checks (DE6 acceptance criteria)
-- ------------------------------------------------------------------

-- dim_grid must have no duplicate grid_id and (if fully populated) 10000 rows
SELECT COUNT(*) AS dim_grid_rows, COUNT(DISTINCT grid_id) AS distinct_grid_ids
FROM dim_grid;

-- fact_network_activity row count must equal hourly_grid_summary row count
-- (no fan-out from the dim_time join) - compare this against the Spark
-- count logged by de6_warehouse.py ("fact_network_activity rows: N")
SELECT COUNT(*) AS fact_rows FROM fact_network_activity;

-- fact_network_activity must contain no duplicate (grid_id, time_key) pairs
SELECT grid_id, time_key, COUNT(*) AS n
FROM fact_network_activity
GROUP BY grid_id, time_key
HAVING COUNT(*) > 1;
