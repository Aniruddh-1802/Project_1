import logging
from pathlib import Path

import pandas as pd


class AlertGenerator:

    def __init__(self, analytics_df):

        self.df = analytics_df.copy()

        Path("logs").mkdir(exist_ok=True)

        logging.basicConfig(
            filename="logs/alert_generator.log",
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

        self.logger = logging.getLogger(self.__class__.__name__)

    def apply_activity_floor(self):

        daily_totals = (
            self.df.groupby("grid_id")["total_activity"]
            .sum()
        )

        floor = daily_totals.quantile(0.25)

        valid_grids = (
            daily_totals[daily_totals >= floor]
            .index
        )

        self.df = self.df[
            self.df["grid_id"].isin(valid_grids)
        ]

        self.logger.info(
            "Activity floor applied: %.2f",
            floor
        )

        return floor

    def build_baseline(self):

        baselines = []

        for grid_id, group in self.df.groupby("grid_id"):

            activities = group["total_activity"]

            grid_baselines = []

            for idx in group.index:

                baseline = (
                    activities.drop(idx)
                    .median()
                )

                grid_baselines.append(baseline)

            temp = group.copy()

            temp["baseline_activity"] = grid_baselines

            baselines.append(temp)

        self.df = pd.concat(
            baselines,
            ignore_index=True
        )

        self.logger.info(
            "Baseline calculation completed"
        )

        return self.df

    def generate_alerts(self):

        self.df = self.df.sort_values(
            ["grid_id", "hour"]
        )

        self.df["prev_hour_activity"] = (
            self.df.groupby("grid_id")
            ["total_activity"]
            .shift(1)
        )

        alerts = []

        for _, row in self.df.iterrows():

            current = row["total_activity"]

            baseline = row["baseline_activity"]

            previous = row["prev_hour_activity"]

            timestamp = (
                f"{row['date']} "
                f"{int(row['hour']):02d}:00:00"
            )

            # HIGH_ACTIVITY
            if current > baseline * 2:

                alerts.append({
                    "grid_id": row["grid_id"],
                    "timestamp": timestamp,
                    "alert_type": "HIGH_ACTIVITY",
                    "current_activity": current,
                    "baseline_activity": baseline,
                    "reason": (
                        "Current activity exceeds "
                        "2x baseline"
                    )
                })

            # ACTIVITY_DROP
            if current < baseline * 0.5:

                alerts.append({
                    "grid_id": row["grid_id"],
                    "timestamp": timestamp,
                    "alert_type": "ACTIVITY_DROP",
                    "current_activity": current,
                    "baseline_activity": baseline,
                    "reason": (
                        "Current activity below "
                        "50% of baseline"
                    )
                })

            # ACTIVITY_SPIKE
            if pd.notna(previous):

                if current > previous * 1.5:

                    alerts.append({
                        "grid_id": row["grid_id"],
                        "timestamp": timestamp,
                        "alert_type": "ACTIVITY_SPIKE",
                        "current_activity": current,
                        "baseline_activity": baseline,
                        "reason": (
                            "Current activity increased "
                            "more than 50% from previous hour"
                        )
                    })

        alerts_df = pd.DataFrame(alerts)

        self.logger.info(
            "Generated %s alerts",
            len(alerts_df)
        )

        return alerts_df

    def export_alerts(self, alerts_df):

        Path("outputs").mkdir(exist_ok=True)

        alerts_df.to_csv(
            r"C:\Users\aniruddh.singh\Documents\Project_1\outputsnetwork_alerts.csv",
            index=False
        )

        alerts_df.to_json(
            r"C:\Users\aniruddh.singh\Documents\Project_1\outputs/network_alerts.json",
            orient="records"
        )

        self.logger.info(
            "Alerts written to outputs folder"
        )

    def operational_summary(self, alerts_df):

        print("\nAlerts by Type")
        print(
            alerts_df["alert_type"]
            .value_counts()
        )

        print("\nTop 10 Grids by Alert Count")
        print(
            alerts_df["grid_id"]
            .value_counts()
            .head(10)
        )

        alert_ratio = (
            len(alerts_df)
            /
            len(self.df)
        )

        print(
            f"\nProportion of Grid-Hours Alerted:"
            f" {alert_ratio:.2%}"
        )