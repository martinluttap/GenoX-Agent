import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

def main():
	if len(sys.argv) < 2:
		print("Usage: python plot_latency_cdf.py <csv_file>")
		sys.exit(1)

	csv_file = sys.argv[1]
	if not os.path.isfile(csv_file):
		print(f"File not found: {csv_file}")
		sys.exit(1)

	# Read the CSV file
	df = pd.read_csv(csv_file)

	# Extract the response_time_ms column
	if 'response_time_ms' not in df.columns:
		print("Column 'response_time_ms' not found in CSV.")
		sys.exit(1)
	latencies = df['response_time_ms'].dropna().values

	# Sort the latencies
	latencies_sorted = np.sort(latencies)

	# Compute the CDF values
	cdf = np.arange(1, len(latencies_sorted) + 1) / len(latencies_sorted)

	# Plot the CDF as a continuous line
	plt.figure(figsize=(8, 6))
	plt.plot(latencies_sorted, cdf, linestyle='-', color='blue')
	plt.xlabel('Response Time (ms)')
	plt.ylabel('CDF')
	plt.title('CDF of Response Time')
	plt.grid(True)

	# Save the plot as an image file
	out_file = os.path.splitext(csv_file)[0] + '_latency_cdf.png'
	plt.savefig(out_file)
	print(f"CDF plot saved as {out_file}")

	# Save the CDF data as a CSV file, rounding to 3 decimal places
	cdf_csv_file = os.path.splitext(csv_file)[0] + '_latency_cdf.csv'
	cdf_df = pd.DataFrame({
		'response_time_ms': np.round(latencies_sorted, 3),
		'cdf': np.round(cdf, 3)
	})
	cdf_df.to_csv(cdf_csv_file, index=False)
	print(f"CDF data saved as {cdf_csv_file}")

if __name__ == "__main__":
	main()
