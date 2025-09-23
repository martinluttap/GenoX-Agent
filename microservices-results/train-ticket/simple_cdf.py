#!/usr/bin/env python3
"""
Simple Python script to generate CDF from CSV response_time_ms data.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def main():
    # Read CSV file
    df = pd.read_csv('latency_per_route_20250921_191126.csv')
    
    # Extract response times
    response_times = df['response_time_ms'].values
    
    # Sort the data
    sorted_times = np.sort(response_times)
    
    # Calculate CDF
    n = len(sorted_times)
    cdf_values = np.arange(1, n + 1) / n
    
    # Print some statistics
    print(f"Total samples: {n}")
    print(f"Mean: {np.mean(response_times):.2f} ms")
    print(f"Median: {np.median(response_times):.2f} ms")
    print(f"95th percentile: {np.percentile(response_times, 95):.2f} ms")
    print(f"99th percentile: {np.percentile(response_times, 99):.2f} ms")
    
    # Plot CDF
    plt.figure(figsize=(10, 6))
    plt.plot(sorted_times, cdf_values)
    plt.xlabel('Response Time (ms)')
    plt.ylabel('Cumulative Probability')
    plt.title('CDF of Response Times')
    plt.grid(True)
    plt.show()
    
    # Save CDF data
    cdf_df = pd.DataFrame({
        'response_time_ms': sorted_times,
        'cumulative_probability': cdf_values
    })
    cdf_df.to_csv('cdf_output.csv', index=False)
    print("CDF data saved to cdf_output.csv")

if __name__ == "__main__":
    main()