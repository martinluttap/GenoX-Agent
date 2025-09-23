#!/usr/bin/env python3
"""
Python script to parse CSV file and generate CDF (Cumulative Distribution Function)
for response_time_ms column.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import sys
import os

def read_csv_file(filepath):
    """Read the CSV file and return a pandas DataFrame."""
    try:
        df = pd.read_csv(filepath)
        print(f"Successfully loaded CSV file: {filepath}")
        print(f"Total records: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        return df
    except FileNotFoundError:
        print(f"Error: File {filepath} not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)

def calculate_cdf(data):
    """Calculate the CDF for the given data."""
    # Sort the data
    sorted_data = np.sort(data)
    
    # Calculate the CDF values
    n = len(sorted_data)
    cdf_values = np.arange(1, n + 1) / n
    
    return sorted_data, cdf_values

def generate_statistics(data):
    """Generate basic statistics for the response time data."""
    stats_dict = {
        'count': len(data),
        'mean': np.mean(data),
        'median': np.median(data),
        'std': np.std(data),
        'min': np.min(data),
        'max': np.max(data),
        'p50': np.percentile(data, 50),
        'p90': np.percentile(data, 90),
        'p95': np.percentile(data, 95),
        'p99': np.percentile(data, 99),
        'p99.9': np.percentile(data, 99.9)
    }
    return stats_dict

def plot_cdf(sorted_data, cdf_values, output_file=sys.argv[2] if len(sys.argv) > 2 else 'cdf_plot.png'):
    """Plot the CDF and save to file."""
    plt.figure(figsize=(12, 8))
    
    # Main CDF plot
    plt.subplot(2, 2, 1)
    plt.plot(sorted_data, cdf_values, linewidth=2, color='blue')
    plt.xlabel('Response Time (ms)')
    plt.ylabel('Cumulative Probability')
    plt.title('Cumulative Distribution Function (CDF)')
    plt.grid(True, alpha=0.3)
    
    # Log scale CDF plot
    plt.subplot(2, 2, 2)
    plt.semilogx(sorted_data, cdf_values, linewidth=2, color='red')
    plt.xlabel('Response Time (ms) - Log Scale')
    plt.ylabel('Cumulative Probability')
    plt.title('CDF - Log Scale')
    plt.grid(True, alpha=0.3)
    
    # Histogram
    plt.subplot(2, 2, 3)
    plt.hist(sorted_data, bins=100, alpha=0.7, color='green', density=True)
    plt.xlabel('Response Time (ms)')
    plt.ylabel('Density')
    plt.title('Response Time Distribution')
    plt.grid(True, alpha=0.3)
    
    # Box plot
    plt.subplot(2, 2, 4)
    plt.boxplot(sorted_data, vert=True)
    plt.ylabel('Response Time (ms)')
    plt.title('Box Plot')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.show()
    print(f"CDF plot saved as: {output_file}")

def save_cdf_data(sorted_data, cdf_values, output_file=f'{sys.argv[2]}.csv' if len(sys.argv) > 2 else 'cdf_data.csv'):
    """Save CDF data to CSV file."""
    cdf_df = pd.DataFrame({
        'response_time_ms': sorted_data,
        'cumulative_probability': cdf_values
    })
    cdf_df.to_csv(output_file, index=False)
    print(f"CDF data saved as: {output_file}")

def main():
    # Define input file path

    input_file = sys.argv[1] if len(sys.argv) > 1 else sys.exit("Usage: python cdf_analysis.py <input_csv_file>")
    
    # Check if file exists
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found in current directory.")
        print("Please ensure the CSV file is in the same directory as this script.")
        sys.exit(1)
    
    # Read the CSV file
    df = read_csv_file(input_file)
    
    # Check if response_time_ms column exists
    if 'response_time_ms' not in df.columns:
        print("Error: 'response_time_ms' column not found in CSV file.")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)
    
    # Extract response time data and remove any NaN values
    response_times = df['response_time_ms'].dropna().values
    
    print(f"\nProcessing {len(response_times)} response time measurements...")
    
    # Calculate CDF
    sorted_data, cdf_values = calculate_cdf(response_times)
    
    # Generate statistics
    stats = generate_statistics(response_times)
    
    # Print statistics
    print("\n" + "="*50)
    print("RESPONSE TIME STATISTICS")
    print("="*50)
    print(f"Total requests: {stats['count']:,}")
    print(f"Mean response time: {stats['mean']:.2f} ms")
    print(f"Median response time: {stats['median']:.2f} ms")
    print(f"Standard deviation: {stats['std']:.2f} ms")
    print(f"Min response time: {stats['min']:.2f} ms")
    print(f"Max response time: {stats['max']:.2f} ms")
    print("\nPercentiles:")
    print(f"  50th percentile (P50): {stats['p50']:.2f} ms")
    print(f"  90th percentile (P90): {stats['p90']:.2f} ms")
    print(f"  95th percentile (P95): {stats['p95']:.2f} ms")
    print(f"  99th percentile (P99): {stats['p99']:.2f} ms")
    print(f"  99.9th percentile (P99.9): {stats['p99.9']:.2f} ms")
    
    # Save CDF data
    save_cdf_data(sorted_data, cdf_values)
    
    # Plot CDF
    plot_cdf(sorted_data, cdf_values)
    
    # Optional: Show some sample CDF values
    print("\n" + "="*50)
    print("SAMPLE CDF VALUES")
    print("="*50)
    print("Response Time (ms) | Cumulative Probability")
    print("-" * 40)
    
    # Show CDF values at key percentiles
    percentiles = [50, 90, 95, 99, 99.9]
    for p in percentiles:
        idx = int(p/100 * len(sorted_data)) - 1
        if idx >= 0 and idx < len(sorted_data):
            print(f"{sorted_data[idx]:>13.2f} | {cdf_values[idx]:>19.4f} ({p}%)")
    
    print("\nCDF analysis completed successfully!")

if __name__ == "__main__":
    main()