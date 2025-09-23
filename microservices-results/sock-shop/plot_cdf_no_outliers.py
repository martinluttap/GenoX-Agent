import pandas as pd
import numpy as np
import sys

# Load the CSV file
csv_file = sys.argv[1] if len(sys.argv) > 1 else 'latency_default.csv'
df = pd.read_csv(csv_file)


# Calculate Q1 and Q3
Q1 = df['response_time_ms'].quantile(0.25)
Q3 = df['response_time_ms'].quantile(0.75)
IQR = Q3 - Q1

# Define bounds
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

# Remove outliers
filtered_df = df[(df['response_time_ms'] >= lower_bound) & (df['response_time_ms'] <= upper_bound)]

# Calculate CDF
latencies = np.sort(filtered_df['response_time_ms'])
cdf = np.arange(1, len(latencies)+1) / len(latencies)
cdf = np.clip(cdf, 0.00, 1.0)

# Save CDF to CSV
cdf_df = pd.DataFrame({'latency': latencies, 'cdf': cdf})
cdf_df.to_csv(sys.argv[2] if len(sys.argv) > 2 else 'latency_default_no_outliers_cdf.csv', index=False)