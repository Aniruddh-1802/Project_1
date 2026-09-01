from UsageProcessor import UsageProcessor

processor = UsageProcessor(r"C:\Users\aniruddh.singh\Documents\Project_1\data\landing\sms-call-internet-mi-2013-11-01.csv")

# Run pipeline
processor.load_data()
processor.clean_data()
processor.derive_time_features()
processor.derive_activity_features()

# Generate analytics dataset
analytics_df = processor.aggregate_to_grid_time()

# Generate summaries
daily_df = processor.daily_summary()
grid_df = processor.grid_summary()

# Compute KPIs
kpi_df = processor.compute_kpis(analytics_df)

# Export outputs
processor.export_summary(
    analytics_df,
    daily_df,
    grid_df
)

# Display KPIs
print("\nKPI Summary:")
print(kpi_df)

# Optional: Preview outputs
print("\nDaily Summary:")
print(daily_df.head())

print("\nGrid Summary:")
print(grid_df.head())

print("\nGrid-Hour Analytics:")
print(analytics_df.head())