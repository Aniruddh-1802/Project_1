# Why de3_spark.py is here

`de3_spark.py` was a self-contained reimplementation of the Spark cleaning /
aggregation / enrichment logic, supplied from a different source than the
rest of this project.

The project already had a working, previously-run Spark job for this exact
purpose: `spark\telecom_pipeline.py`, built from `ingetision_module.py`,
`spark_cleaning.py`, `spark_aggregation.py`, `spark_geo_enrichment.py` and
`output_layer.py` in the `spark\` folder. Its output paths
(`processed\activity`, `analytics\hourly_grid_summary`,
`analytics\dashboard_summary`) match the data already sitting in
`data\processed` and `data\analytics` — this script produced that data.

Running both `de3_spark.py` and `telecom_pipeline.py` would give two
divergent Spark jobs writing similar-but-not-identical outputs. DE3 in the
trainer guide names `telecom_pipeline.py` directly ("Configure
telecom_pipeline.py to read data/raw/ and write data/processed/ and
data/analytics/"), so the Airflow DAG (`spark_proc.py`) now calls
`telecom_pipeline.py` instead.

`de3_spark.py` is kept here for reference only. It is not imported or
executed by anything.
