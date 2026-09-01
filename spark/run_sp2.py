import os

os.environ["HADOOP_HOME"] = r"C:\hadoop\hadoop-3.3.6"
os.environ["PATH"] += os.pathsep + r"C:\hadoop\hadoop-3.3.6\bin"

from spark.ingetision_module import load_raw_network_data

from spark.spark_cleaning import (
    clean_network_data
)

clean_network_df, rejected_df, null_profile = (
    clean_network_data(
        load_raw_network_data(
            r"C:\Users\aniruddh.singh\Documents\Project_1\data\landing"
        )
    )
)

print("\nSchema")
clean_network_df.printSchema()

print("\nRejected Rows")
print(
    rejected_df.count()
)

print("\nNull Handling Report")
null_profile.show()

# Optional Save

clean_network_df.write.mode(
    "overwrite"
).parquet(
    "output/clean_network_df"
)

print(
    "\nSaved clean_network_df"
)