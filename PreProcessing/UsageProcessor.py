import logging
from pathlib import Path
from typing import Union

import pandas as pd


class UsageProcessor:

    RAW_TO_CANONICAL = {
        'datetime': 'timestamp',
        'CellID': 'grid_id',
        'countrycode': 'country_code',
        'smsin': 'sms_in',
        'smsout': 'sms_out',
        'callin': 'call_in',
        'callout': 'call_out',
        'internet': 'internet_activity'
    }

    REQUIRED_COLUMNS = [
        'timestamp',
        'grid_id',
        'country_code',
        'sms_in',
        'sms_out',
        'call_in',
        'call_out',
        'internet_activity'
    ]

    ACTIVITY_COLUMNS = [
        'sms_in',
        'sms_out',
        'call_in',
        'call_out',
        'internet_activity'
    ]

    def __init__(self, source: Union[str, pd.DataFrame]):

        self.source = source
        self.df = None

        logging.basicConfig(
            filename="logs/usage_processor.log",
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

        self.logger = logging.getLogger(self.__class__.__name__)


    def load_data(self):

        if isinstance(self.source, pd.DataFrame):
            self.df = self.source.copy()

        elif isinstance(self.source, str):
            self.df = pd.read_csv(self.source)

        else:
            raise TypeError(
                "Source must be a DataFrame or CSV file path."
            )

        self.logger.info(
            "Loaded %s records",
            len(self.df)
        )

        self.df.rename(
            columns=self.RAW_TO_CANONICAL,
            inplace=True
        )

        return self.df


    def clean_data(self):

        missing_cols = (
            set(self.REQUIRED_COLUMNS)
            - set(self.df.columns)
        )

        if missing_cols:
            raise ValueError(
                f"Missing required columns: {missing_cols}"
            )

        initial_count = len(self.df)

        self.df['timestamp'] = pd.to_datetime(
            self.df['timestamp'],
            errors='coerce'
        )

        self.df = self.df.dropna(
            subset=['timestamp', 'grid_id']
        )

        dropped_rows = initial_count - len(self.df)

        self.logger.info(
            "Dropped %s rows due to missing timestamp/grid_id",
            dropped_rows
        )

        # Curated-layer null handling rule
        self.df[self.ACTIVITY_COLUMNS] = (
            self.df[self.ACTIVITY_COLUMNS]
            .fillna(0)
        )

        # Negative activity check
        negative_mask = (
            self.df[self.ACTIVITY_COLUMNS] < 0
        ).any(axis=1)

        if negative_mask.any():

            count = negative_mask.sum()

            raise ValueError(
                f"{count} rows contain negative activity values."
            )

        return self.df

    def derive_time_features(self):

        self.df['date'] = self.df['timestamp'].dt.date

        self.df['hour'] = self.df['timestamp'].dt.hour

        return self.df


    def derive_activity_features(self):

        self.df['total_sms'] = (
            self.df['sms_in']
            + self.df['sms_out']
        )

        self.df['total_calls'] = (
            self.df['call_in']
            + self.df['call_out']
        )

        self.df['total_activity'] = (
            self.df['total_sms']
            + self.df['total_calls']
            + self.df['internet_activity']
        )

        return self.df


    def aggregate_to_grid_time(self):

        analytics_df = (
            self.df.groupby(
                ['date', 'hour', 'grid_id'],
                as_index=False
            )
            .agg(
                total_sms=('total_sms', 'sum'),
                total_calls=('total_calls', 'sum'),
                internet_activity=('internet_activity', 'sum'),
                total_activity=('total_activity', 'sum')
            )
        )

        self.logger.info(
            "Created analytics dataset with %s rows",
            len(analytics_df)
        )

        return analytics_df


    def compute_kpis(self, analytics_df):

        kpis = pd.DataFrame([{

            "total_records":
                len(self.df),

            "distinct_grids":
                self.df['grid_id'].nunique(),

            "max_total_activity":
                analytics_df['total_activity'].max(),

            "avg_total_activity":
                analytics_df['total_activity'].mean(),

            "min_total_activity":
                analytics_df['total_activity'].min()

        }])

        return kpis

    def daily_summary(self):

        return (
            self.df.groupby(
                'date',
                as_index=False
            )
            .agg(
                total_sms=('total_sms', 'sum'),
                total_calls=('total_calls', 'sum'),
                internet_activity=('internet_activity', 'sum'),
                total_activity=('total_activity', 'sum')
            )
        )


    def grid_summary(self):

        return (
            self.df.groupby(
                'grid_id',
                as_index=False
            )
            .agg(
                total_sms=('total_sms', 'sum'),
                total_calls=('total_calls', 'sum'),
                internet_activity=('internet_activity', 'sum'),
                total_activity=('total_activity', 'sum')
            )
        )


    def export_summary(
        self,
        analytics_df,
        daily_df,
        grid_df
        ):

        Path("outputs").mkdir(exist_ok=True)

        daily_path = "outputs/daily_summary.csv"
        grid_path = "outputs/grid_summary.csv"

        daily_df.to_csv(
            daily_path,
            index=False
        )

        grid_df.to_csv(
            grid_path,
            index=False
        )

        self.logger.info(
            "Daily summary exported to %s",
            daily_path
        )

        self.logger.info(
            "Grid summary exported to %s",
            grid_path
        )

        analytics_path = "outputs/grid_hour_analytics.csv"

        analytics_df.to_csv(
            analytics_path,
            index=False
        )

        self.logger.info(
            "Analytics exported to %s",
            analytics_path
        )

if __name__ == "__main__":

    processor = UsageProcessor(
        "daily_usage.csv"
    )

    processor.load_data()
    processor.clean_data()
    processor.derive_time_features()
    processor.derive_activity_features()

    analytics_df = (
        processor.aggregate_to_grid_time()
    )

    daily_df = (
        processor.daily_summary()
    )

    grid_df = (
        processor.grid_summary()
    )

    kpis = (
        processor.compute_kpis(
            analytics_df
        )
    )

    processor.export_summary(analytics_df,daily_df, grid_df)
    print(kpis)