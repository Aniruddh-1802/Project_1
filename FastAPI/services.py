from sqlalchemy import text

from datetime import timedelta, datetime

from fastapi import HTTPException
from sqlalchemy import text


class NetworkService:

    def __init__(self, engine):
        self.engine = engine

    def get_network_summary(
        self,
        as_of=None
    ):

        with self.engine.connect() as connection:

            # ===================================
            # Effective AS_OF
            # ===================================

            if as_of is None:

                as_of = connection.execute(
                    text(
                        """
                        SELECT
                            MAX(t.timestamp_value)
                        FROM fact_network_activity f
                        JOIN dim_time t
                            ON f.time_key = t.time_key
                        """
                    )
                ).scalar()

            # ===================================
            # Total Activity
            # ===================================

            total_activity = connection.execute(
                text(
                    """
                    SELECT
                        SUM(f.total_activity)
                    FROM fact_network_activity f
                    JOIN dim_time t
                        ON f.time_key = t.time_key
                    WHERE t.timestamp_value <= :as_of
                    """
                ),
                {"as_of": as_of}
            ).scalar()

            # ===================================
            # Active Grids
            # ===================================

            active_grids = connection.execute(
                text(
                    """
                    SELECT
                        COUNT(DISTINCT f.grid_key)
                    FROM fact_network_activity f
                    JOIN dim_time t
                        ON f.time_key = t.time_key
                    WHERE t.timestamp_value <= :as_of
                    """
                ),
                {"as_of": as_of}
            ).scalar()

            # ===================================
            # Peak Hour
            # ===================================

            peak_hour = connection.execute(
                text(
                    """
                    SELECT
                        t.hour_of_day
                    FROM fact_network_activity f
                    JOIN dim_time t
                        ON f.time_key = t.time_key
                    WHERE t.timestamp_value <= :as_of
                    GROUP BY t.hour_of_day
                    ORDER BY
                        SUM(f.total_activity) DESC
                    LIMIT 1
                    """
                ),
                {"as_of": as_of}
            ).scalar()

            # ===================================
            # Top Grid
            # ===================================

            top_grid = connection.execute(
                text(
                    """
                    SELECT
                        g.grid_id
                    FROM fact_network_activity f
                    JOIN dim_time t
                        ON f.time_key = t.time_key
                    JOIN dim_grid g
                        ON f.grid_key = g.grid_key
                    WHERE t.timestamp_value <= :as_of
                    GROUP BY g.grid_id
                    ORDER BY
                        SUM(f.total_activity) DESC
                    LIMIT 1
                    """
                ),
                {"as_of": as_of}
            ).scalar()

        return {
            "total_activity": float(total_activity or 0),
            "active_grids": int(active_grids or 0),
            "peak_hour": int(peak_hour or 0),
            "top_grid": int(top_grid or 0),
            "as_of": as_of
        }

    def get_grid_activity(
        self,
        grid_id: int,
        date=None,
        hour=None,
        as_of=None
    ):

        if grid_id < 1 or grid_id > 10000:

            raise HTTPException(
                status_code=404,
                detail="Unknown grid"
            )

        with self.engine.connect() as connection:

            grid_exists = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM dim_grid
                    WHERE grid_id = :grid_id
                    """
                ),
                {
                    "grid_id": grid_id
                }
            ).scalar()

            if grid_exists == 0:

                raise HTTPException(
                    status_code=404,
                    detail="Unknown grid"
                )

            if as_of is None:

                as_of = connection.execute(
                    text(
                        """
                        SELECT
                            MAX(timestamp_value)
                        FROM dim_time
                        """
                    )
                ).scalar()

            start_time = (
                as_of - timedelta(hours=23)
            )

            sql = """
            SELECT
                t.timestamp_value,

                f.total_sms,
                f.total_calls,
                f.internet_activity,
                f.total_activity

            FROM fact_network_activity f

            JOIN dim_time t
                ON f.time_key = t.time_key

            JOIN dim_grid g
                ON f.grid_key = g.grid_key

            WHERE g.grid_id = :grid_id

            AND t.timestamp_value
                BETWEEN :start_time
                AND :as_of
            """

            params = {
                "grid_id": grid_id,
                "start_time": start_time,
                "as_of": as_of
            }

            if date:

                sql += """
                AND DATE(t.timestamp_value)
                    = :date
                """

                params["date"] = date

            if hour is not None:

                sql += """
                AND t.hour_of_day
                    = :hour
                """

                params["hour"] = hour

            sql += """
            ORDER BY t.timestamp_value
            """

            rows = connection.execute(
                text(sql),
                params
            ).mappings().all()

        return {
            "grid_id": grid_id,
            "as_of": as_of,
            "interval_count": len(rows),
            "activity": [
                {
                    "timestamp":
                        row["timestamp_value"],

                    "sms_activity":
                        float(
                            row["total_sms"] or 0
                        ),

                    "call_activity":
                        float(
                            row["total_calls"] or 0
                        ),

                    "internet_activity":
                        float(
                            row["internet_activity"] or 0
                        ),

                    "total_activity":
                        float(
                            row["total_activity"] or 0
                        )
                }
                for row in rows
            ]
        }
    def get_hotspots(
    self,
    limit=10,
    as_of=None
    ):

        with self.engine.connect() as connection:

            if as_of is None:

                as_of = connection.execute(
                    text(
                        """
                        SELECT
                            MAX(timestamp_value)
                        FROM dim_time
                        """
                    )
                ).scalar()

            rows = connection.execute(
                text(
                    """
                    SELECT

                        g.grid_id,

                        t.timestamp_value,

                        f.total_activity,

                        f.total_sms,

                        f.total_calls,

                        f.internet_activity

                    FROM fact_network_activity f

                    JOIN dim_time t
                        ON f.time_key = t.time_key

                    JOIN dim_grid g
                        ON f.grid_key = g.grid_key

                    WHERE t.timestamp_value = :as_of

                    ORDER BY
                        f.total_activity DESC

                    LIMIT :limit
                    """
                ),
                {
                    "as_of": as_of,
                    "limit": limit
                }
            ).mappings().all()

        return {
            "as_of": as_of,
            "count": len(rows),
            "hotspots": [
                {
                    "grid_id":
                        row["grid_id"],

                    "timestamp":
                        row["timestamp_value"],

                    "total_activity":
                        float(row["total_activity"]),

                    "sms_activity":
                        float(row["total_sms"]),

                    "call_activity":
                        float(row["total_calls"]),

                    "internet_activity":
                        float(
                            row["internet_activity"]
                        ),

                    "status":
                        "high_activity",

                    "reason":
                        "Grid ranked among highest activity levels for reporting interval."
                }
                for row in rows
            ]
        }
    def get_alerts(
    self,
    severity=None,
    limit=10,
    as_of=None
):

        with self.engine.connect() as connection:

            if as_of is None:

                as_of = connection.execute(
                    text(
                        """
                        SELECT MAX(timestamp_value)
                        FROM dim_time
                        """
                    )
                ).scalar()

            rows = connection.execute(
                text(
                    """
                    SELECT

                        g.grid_id,

                        t.timestamp_value,

                        f.total_activity,

                        f.total_sms,

                        f.total_calls,

                        f.internet_activity

                    FROM fact_network_activity f

                    JOIN dim_time t
                        ON f.time_key = t.time_key

                    JOIN dim_grid g
                        ON f.grid_key = g.grid_key

                    WHERE t.timestamp_value = :as_of

                    ORDER BY
                        f.total_activity DESC

                    LIMIT :limit
                    """
                ),
                {
                    "as_of": as_of,
                    "limit": limit
                }
            ).mappings().all()

        alerts = []

        for row in rows:

            activity = row["total_activity"]

            if activity >= 5000:

                row_severity = "critical"

            elif activity >= 3000:

                row_severity = "high"

            else:

                row_severity = "medium"

            if severity and severity.lower() != row_severity:

                continue

            alerts.append(
                {
                    "grid_id":
                        row["grid_id"],

                    "timestamp":
                        row["timestamp_value"],

                    "severity":
                        row_severity,

                    "status":
                        "open",

                    "total_activity":
                        float(activity),

                    "sms_activity":
                        float(row["total_sms"]),

                    "call_activity":
                        float(row["total_calls"]),

                    "internet_activity":
                        float(
                            row["internet_activity"]
                        ),

                    "reason":
                        f"Rule-based NP3 alert triggered due to elevated activity level."
                }
            )

        return {
            "as_of": as_of,
            "count": len(alerts),
            "alerts": alerts
        }

    def get_grid_features(
    self,
    grid_id: int
    ):

        if grid_id < 1 or grid_id > 10000:

            raise HTTPException(
                status_code=404,
                detail="Unknown grid"
            )

        with self.engine.connect() as connection:

            feature_row = connection.execute(
                text(
                    """
                    SELECT
                        grid_id,

                        avg_activity,

                        activity_growth,

                        active_hours,

                        peak_ratio,

                        variability,

                        internet_share,

                        feature_timestamp,

                        data_quality_status

                    FROM grid_features

                    WHERE grid_id = :grid_id
                    """
                ),
                {
                    "grid_id": grid_id
                }
            ).mappings().first()

        if feature_row is None:

            raise HTTPException(
                status_code=404,
                detail=
                "No stored features available "
                "for this grid"
            )

        required_features = [

            "avg_activity",

            "activity_growth",

            "active_hours",

            "peak_ratio",

            "variability",

            "internet_share"
        ]

        missing = [

            feature

            for feature

            in required_features

            if feature_row[feature] is None

        ]

        if missing:

            raise HTTPException(
                status_code=500,
                detail=
                f"Missing stored feature(s): "
                f"{', '.join(missing)}"
            )

        feature_timestamp = (
            feature_row["feature_timestamp"]
        )

        freshness_hours = (

            (
                datetime.utcnow()
                - feature_timestamp
            ).total_seconds()

            / 3600

        )

        return {

            "grid_id":
                feature_row["grid_id"],

            "avg_activity":
                float(
                    feature_row["avg_activity"]
                ),

            "activity_growth":
                float(
                    feature_row["activity_growth"]
                ),

            "active_hours":
                int(
                    feature_row["active_hours"]
                ),

            "peak_ratio":
                float(
                    feature_row["peak_ratio"]
                ),

            "variability":
                float(
                    feature_row["variability"]
                ),

            "internet_share":
                float(
                    feature_row["internet_share"]
                ),

            "feature_timestamp":
                feature_timestamp,

            "data_quality_status":
                feature_row[
                    "data_quality_status"
                ],

            "feature_freshness_hours":
                round(
                    freshness_hours,
                    2
                )
        }

    def predict_risk(
    self,
    request
    ):

        return {

            "risk_score": 0.72,

            "risk_level": "MEDIUM",

            "model_version":
                "stub-v1",

            "explanation_note":
                (
                    "Prediction endpoint currently "
                    "uses a stub implementation. "
                    "ML5 will replace the underlying "
                    "logic without changing the API "
                    "contract."
                )
        }

