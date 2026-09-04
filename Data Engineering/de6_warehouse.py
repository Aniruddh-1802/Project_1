"""
DE6 - Warehouse modelling for network analytics.

Reads the DE3 analytics layer, builds the star schema
(dim_grid, dim_time, fact_network_activity) and loads it into MySQL.

Writes go through SQLAlchemy + PyMySQL rather than Spark JDBC, because
no MySQL Connector/J jar is installed on this machine.

Target database is telecom_warehouse_de6, deliberately separate from
telecom_project_1 so the star schema loaded by
SQL_load_verify\\load_to_sql.py is left intact.

Run on Windows (Java 17 + pyspark live there, not in WSL):

    python "C:\\Users\\aniruddh.singh\\Documents\\Project_1\\Data Engineering\\de6_warehouse.py"
"""

import json
import logging
import os
import sys


# ---------------------------------------------------------
# Spark-on-Windows environment (set before SparkSession)
# ---------------------------------------------------------

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

os.environ["HADOOP_HOME"] = r"C:\hadoop\hadoop-3.3.6"
os.environ["PATH"] += os.pathsep + r"C:\hadoop\hadoop-3.3.6\bin"


from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    year,
    month,
    dayofmonth,
    hour,
    dayofweek,
    date_format,
    row_number
)
from pyspark.sql.window import Window

from sqlalchemy import create_engine, text


# ---------------------------------------------------------
# ABSOLUTE PATHS AND CONNECTION SETTINGS
#
# ANALYTICS_PATH must match the hourly_grid_summary OUTPUT of DE3
# (spark/telecom_pipeline.py --output <data>). This folder already
# exists with real Milan activity data.
# ---------------------------------------------------------

ANALYTICS_PATH = r"C:\Users\aniruddh.singh\Documents\Project_1\data\analytics\hourly_grid_summary"

REFERENCE_PATH = r"C:\Users\aniruddh.singh\Documents\Project_1\data\reference\milano-grid.geojson"

LOG_DIR = r"C:\Users\aniruddh.singh\Documents\Project_1\logs"

MYSQL_HOST = "localhost"
MYSQL_PORT = 3306
MYSQL_DATABASE = "telecom_warehouse_de6"
MYSQL_USER = "root"
MYSQL_PASSWORD = "root"

SERVER_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}"
)

DATABASE_URL = f"{SERVER_URL}/{MYSQL_DATABASE}"


# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# ---------------------------------------------------------
# Warehouse Processor
# ---------------------------------------------------------

class NetworkWarehouse:

    def __init__(
        self,
        spark,
        analytics_path,
        reference_path,
        database_url
    ):

        self.spark = spark
        self.analytics_path = analytics_path
        self.reference_path = reference_path
        self.engine = create_engine(database_url)

        self.analytics_df = None
        self.dim_grid = None
        self.dim_time = None
        self.fact_network_activity = None

    # -----------------------------------------------------
    # Read DE3 analytics output
    # -----------------------------------------------------

    def read_analytics(self):

        logging.info(
            f"Reading analytics data from: {self.analytics_path}"
        )

        if not os.path.exists(self.analytics_path):
            raise FileNotFoundError(
                f"Analytics path does not exist: {self.analytics_path}. "
                "Run de3_spark.py first."
            )

        self.analytics_df = (
            self.spark.read
            .parquet(self.analytics_path)
        )

        row_count = self.analytics_df.count()

        logging.info(
            f"Analytics rows loaded: {row_count}"
        )

        logging.info(
            f"Analytics schema:\n{self.analytics_df.schema}"
        )

        if row_count == 0:
            raise ValueError(
                "Analytics output is empty."
            )

        return self.analytics_df

    # -----------------------------------------------------
    # Create dimension: dim_grid
    # -----------------------------------------------------

    def create_dim_grid(self):

        logging.info("Creating dim_grid")

        if not os.path.exists(self.reference_path):
            raise FileNotFoundError(
                f"Reference file does not exist: {self.reference_path}"
            )

        with open(
            self.reference_path,
            "r",
            encoding="utf-8"
        ) as file:

            geojson = json.load(file)

        features = geojson.get("features", [])

        if not features:
            raise ValueError(
                "No features found in GeoJSON reference."
            )

        grid_rows = []

        for feature in features:

            properties = feature.get(
                "properties",
                {}
            )

            geometry = feature.get(
                "geometry"
            )

            grid_id = properties.get(
                "cellId"
            )

            if grid_id is None:
                continue

            geometry_reference = (
                f"milano-grid.geojson#{int(grid_id)}"
            )

            centroid_latitude = None
            centroid_longitude = None

            if geometry is not None:

                coordinates = geometry.get("coordinates")

                if coordinates:

                    ring = coordinates[0]

                    longitudes = [point[0] for point in ring]
                    latitudes = [point[1] for point in ring]

                    centroid_longitude = (
                        sum(longitudes) / len(longitudes)
                    )

                    centroid_latitude = (
                        sum(latitudes) / len(latitudes)
                    )

            grid_rows.append(
                (
                    int(grid_id),
                    centroid_latitude,
                    centroid_longitude,
                    geometry_reference
                )
            )

        if not grid_rows:
            raise ValueError(
                "No valid grid records found in GeoJSON."
            )

        self.dim_grid = self.spark.createDataFrame(
            grid_rows,
            [
                "grid_id",
                "centroid_latitude",
                "centroid_longitude",
                "geometry_reference"
            ]
        )

        # Remove duplicate grid IDs if present
        self.dim_grid = (
            self.dim_grid
            .dropDuplicates(["grid_id"])
        )

        logging.info(
            f"dim_grid rows: {self.dim_grid.count()}"
        )

        return self.dim_grid

    # -----------------------------------------------------
    # Create dimension: dim_time
    # -----------------------------------------------------

    def create_dim_time(self):

        logging.info("Creating dim_time")

        timestamps = (
            self.analytics_df
            .select("timestamp")
            .where(col("timestamp").isNotNull())
            .distinct()
        )

        window = Window.orderBy("timestamp")

        self.dim_time = (
            timestamps
            .withColumn(
                "time_key",
                row_number().over(window)
            )
            .withColumn(
                "date",
                col("timestamp").cast("date")
            )
            .withColumn(
                "year",
                year(col("timestamp"))
            )
            .withColumn(
                "month",
                month(col("timestamp"))
            )
            .withColumn(
                "day",
                dayofmonth(col("timestamp"))
            )
            .withColumn(
                "hour",
                hour(col("timestamp"))
            )
            .withColumn(
                "day_of_week",
                dayofweek(col("timestamp"))
            )
            .withColumn(
                "day_name",
                date_format(
                    col("timestamp"),
                    "EEEE"
                )
            )
            .select(
                "time_key",
                "timestamp",
                "date",
                "year",
                "month",
                "day",
                "hour",
                "day_of_week",
                "day_name"
            )
        )

        # Materialise once: the row_number() window is expensive and the
        # same DataFrame is reused by the fact-table join below.
        self.dim_time = self.dim_time.cache()

        logging.info(
            f"dim_time rows: {self.dim_time.count()}"
        )

        return self.dim_time

    # -----------------------------------------------------
    # Create fact table
    # -----------------------------------------------------

    def create_fact_network_activity(self):

        logging.info(
            "Creating fact_network_activity"
        )

        # Create lookup from timestamp -> time_key
        time_lookup = self.dim_time.select(
            "time_key",
            "timestamp"
        )

        # Only activity measures belong in the fact table.
        # Geometry is intentionally NOT included.

        self.fact_network_activity = (
            self.analytics_df
            .join(
                time_lookup,
                on="timestamp",
                how="inner"
            )
            .select(
                "time_key",
                col("grid_id").alias("grid_id"),
                "sms_in",
                "sms_out",
                "call_in",
                "call_out",
                "internet_activity",
                "total_sms",
                "total_calls",
                "total_activity"
            )
        )

        logging.info(
            "Fact table schema:"
        )

        logging.info(
            f"\n{self.fact_network_activity.schema}"
        )

        logging.info(
            f"fact_network_activity rows: "
            f"{self.fact_network_activity.count()}"
        )

        return self.fact_network_activity

    # -----------------------------------------------------
    # Write DataFrame to MySQL
    # -----------------------------------------------------

    def write_table(
        self,
        dataframe,
        table_name
    ):

        logging.info(
            f"Writing {table_name} to MySQL"
        )

        pandas_df = dataframe.toPandas()

        pandas_df.to_sql(
            table_name,
            self.engine,
            if_exists="replace",
            index=False,
            chunksize=50000,
            method="multi"
        )

        logging.info(
            f"{table_name} successfully written "
            f"({len(pandas_df)} rows)."
        )

    # -----------------------------------------------------
    # Create indexes
    # -----------------------------------------------------

    def create_indexes(self):

        logging.info(
            "Creating warehouse indexes"
        )

        indexes = [
            "CREATE INDEX idx_fact_grid "
            "ON fact_network_activity(grid_id)",

            "CREATE INDEX idx_fact_time "
            "ON fact_network_activity(time_key)",

            "CREATE INDEX idx_time_timestamp "
            "ON dim_time(`timestamp`)",

            "CREATE INDEX idx_grid_grid_id "
            "ON dim_grid(grid_id)"
        ]

        with self.engine.begin() as connection:

            for statement in indexes:

                try:
                    connection.execute(text(statement))

                except Exception as error:

                    # MySQL reports a duplicate index if the script
                    # is run again against existing tables.
                    logging.warning(
                        f"Index creation skipped: {error}"
                    )

        logging.info(
            "Indexes created successfully."
        )

    # -----------------------------------------------------
    # Validate warehouse
    # -----------------------------------------------------

    def validate(self):

        logging.info(
            "Validating warehouse tables"
        )

        tables = [
            "dim_grid",
            "dim_time",
            "fact_network_activity"
        ]

        with self.engine.connect() as connection:

            for table in tables:

                count = connection.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                ).scalar()

                logging.info(
                    f"{table}: {count} rows"
                )

                if count == 0:
                    raise ValueError(
                        f"{table} is empty."
                    )

    # -----------------------------------------------------
    # Run complete warehouse pipeline
    # -----------------------------------------------------

    def run(self):

        logging.info(
            "========== DE6 WAREHOUSE START =========="
        )

        self.read_analytics()

        self.create_dim_grid()

        self.create_dim_time()

        self.create_fact_network_activity()

        self.write_table(
            self.dim_grid,
            "dim_grid"
        )

        self.write_table(
            self.dim_time,
            "dim_time"
        )

        self.write_table(
            self.fact_network_activity,
            "fact_network_activity"
        )

        self.create_indexes()

        self.validate()

        logging.info(
            "========== DE6 WAREHOUSE COMPLETE =========="
        )


# ---------------------------------------------------------
# Ensure the target database exists
# ---------------------------------------------------------

def ensure_database():

    logging.info(
        f"Ensuring database exists: {MYSQL_DATABASE}"
    )

    server_engine = create_engine(SERVER_URL)

    with server_engine.begin() as connection:

        connection.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE} "
                "CHARACTER SET utf8mb4"
            )
        )

    server_engine.dispose()


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

if __name__ == "__main__":

    os.makedirs(LOG_DIR, exist_ok=True)

    ensure_database()

    spark = (
        SparkSession.builder
        .appName("NetworkWarehouseDE6")
        .master("local[4]")
        .config(
            "spark.driver.memory",
            "4g"
        )
        .config(
            "spark.sql.shuffle.partitions",
            "8"
        )
        .config(
            "spark.sql.execution.arrow.pyspark.enabled",
            "true"
        )
        .getOrCreate()
    )

    try:

        warehouse = NetworkWarehouse(
            spark=spark,
            analytics_path=ANALYTICS_PATH,
            reference_path=REFERENCE_PATH,
            database_url=DATABASE_URL
        )

        warehouse.run()

    finally:

        spark.stop()
