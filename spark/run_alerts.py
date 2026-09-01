import pandas as pd

from spark.alert_generator import AlertGenerator

analytics_df = pd.read_csv(
    r"C:\Users\aniruddh.singh\Documents\Project_1\outputs"
)

generator = AlertGenerator(
    analytics_df
)

floor = generator.apply_activity_floor()

print(
    f"Activity Floor Chosen: {floor:.2f}"
)

generator.build_baseline()
print(generator.df.columns)

alerts_df = generator.generate_alerts()

generator.export_alerts(
    alerts_df
)

generator.operational_summary(
    alerts_df
)