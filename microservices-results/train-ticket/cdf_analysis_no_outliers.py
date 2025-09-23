#!/usr/bin/env python3
"""
Python script to parse CSV file, remove outliers using 1.5 IQR rule,
and generate CDF (Cumulative Distribution Function) for response_time_ms column.
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

def remove_outliers_iqr(data, multiplier=1.5):
    """
    Remove outliers using the IQR (Interquartile Range) method.
    
    Args:
        data: Array of numerical data
        multiplier: IQR multiplier (default 1.5 for standard outlier detection)
        
    Returns:
        filtered_data: Data with outliers removed
        outlier_info: Dictionary with outlier statistics
    """
    # Calculate quartiles and IQR
    Q1 = np.percentile(data, 25)
    Q3 = np.percentile(data, 75)
    IQR = Q3 - Q1
    
    # Calculate outlier bounds
    lower_bound = Q1 - multiplier * IQR
    upper_bound = Q3 + multiplier * IQR
    
    # Filter data to remove outliers
    mask = (data >= lower_bound) & (data <= upper_bound)
    filtered_data = data[mask]
    
    # Calculate outlier statistics
    outlier_info = {
        'original_count': len(data),
        'filtered_count': len(filtered_data),
        'outliers_removed': len(data) - len(filtered_data),
        'outlier_percentage': ((len(data) - len(filtered_data)) / len(data)) * 100,
        'Q1': Q1,
        'Q3': Q3,
        'IQR': IQR,
        'lower_bound': lower_bound,
        'upper_bound': upper_bound,
        'multiplier': multiplier
    }
    
    return filtered_data, outlier_info

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

def plot_comparison_cdf(original_data, filtered_data, output_file):
    """Plot comparison between original and filtered CDF data."""
    # Calculate CDFs for both datasets
    orig_sorted, orig_cdf = calculate_cdf(original_data)
    filt_sorted, filt_cdf = calculate_cdf(filtered_data)
    
    plt.figure(figsize=(16, 12))
    
    # Main CDF comparison plot
    plt.subplot(2, 3, 1)
    plt.plot(orig_sorted, orig_cdf, linewidth=2, color='red', alpha=0.7, label='With Outliers')
    plt.plot(filt_sorted, filt_cdf, linewidth=2, color='blue', label='Outliers Removed (1.5 IQR)')
    plt.xlabel('Response Time (ms)')
    plt.ylabel('Cumulative Probability')
    plt.title('CDF Comparison: Original vs Filtered')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Log scale CDF comparison
    plt.subplot(2, 3, 2)
    plt.semilogx(orig_sorted, orig_cdf, linewidth=2, color='red', alpha=0.7, label='With Outliers')
    plt.semilogx(filt_sorted, filt_cdf, linewidth=2, color='blue', label='Outliers Removed (1.5 IQR)')
    plt.xlabel('Response Time (ms) - Log Scale')
    plt.ylabel('Cumulative Probability')
    plt.title('CDF Comparison - Log Scale')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Histogram comparison
    plt.subplot(2, 3, 3)
    plt.hist(original_data, bins=100, alpha=0.5, color='red', density=True, label='With Outliers')
    plt.hist(filtered_data, bins=100, alpha=0.7, color='blue', density=True, label='Outliers Removed (1.5 IQR)')
    plt.xlabel('Response Time (ms)')
    plt.ylabel('Density')
    plt.title('Response Time Distribution Comparison')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Box plot comparison
    plt.subplot(2, 3, 4)
    plt.boxplot([original_data, filtered_data], labels=['With Outliers', 'Outliers Removed'])
    plt.ylabel('Response Time (ms)')
    plt.title('Box Plot Comparison')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # Filtered CDF only (main result)
    plt.subplot(2, 3, 5)
    plt.plot(filt_sorted, filt_cdf, linewidth=2, color='blue')
    plt.xlabel('Response Time (ms)')
    plt.ylabel('Cumulative Probability')
    plt.title('Final CDF (Outliers Removed)')
    plt.grid(True, alpha=0.3)
    
    # Filtered CDF log scale
    plt.subplot(2, 3, 6)
    plt.semilogx(filt_sorted, filt_cdf, linewidth=2, color='blue')
    plt.xlabel('Response Time (ms) - Log Scale')
    plt.ylabel('Cumulative Probability')
    plt.title('Final CDF - Log Scale (Outliers Removed)')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.show()
    print(f"Comparison CDF plot saved as: {output_file}")

def save_cdf_data(sorted_data, cdf_values, output_file):
    """Save CDF data to CSV file."""
    cdf_df = pd.DataFrame({
        'response_time_ms': sorted_data,
        'cumulative_probability': cdf_values
    })
    cdf_df.to_csv(output_file, index=False)
    print(f"CDF data saved as: {output_file}")

def main():
    # Define input file path
    if len(sys.argv) < 2:
        print("Usage: python cdf_analysis_no_outliers.py <input_csv_file> [output_plot_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_plot = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.csv', '_no_outliers_cdf.png')
    output_csv = output_plot.replace('.png', '.csv')
    
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
    original_response_times = df['response_time_ms'].dropna().values
    
    print(f"\nProcessing {len(original_response_times)} response time measurements...")
    
    # Remove outliers using 1.5 IQR rule
    filtered_response_times, outlier_info = remove_outliers_iqr(original_response_times, multiplier=1.5)
    
    # Print outlier removal statistics
    print("\n" + "="*60)
    print("OUTLIER REMOVAL STATISTICS (1.5 IQR Method)")
    print("="*60)
    print(f"Original data points: {outlier_info['original_count']:,}")
    print(f"Filtered data points: {outlier_info['filtered_count']:,}")
    print(f"Outliers removed: {outlier_info['outliers_removed']:,}")
    print(f"Percentage of data removed: {outlier_info['outlier_percentage']:.2f}%")
    print(f"\nIQR Statistics:")
    print(f"  Q1 (25th percentile): {outlier_info['Q1']:.2f} ms")
    print(f"  Q3 (75th percentile): {outlier_info['Q3']:.2f} ms")
    print(f"  IQR: {outlier_info['IQR']:.2f} ms")
    print(f"  Lower bound: {outlier_info['lower_bound']:.2f} ms")
    print(f"  Upper bound: {outlier_info['upper_bound']:.2f} ms")
    
    # Calculate CDF for filtered data
    sorted_data, cdf_values = calculate_cdf(filtered_response_times)
    
    # Generate statistics for both original and filtered data
    orig_stats = generate_statistics(original_response_times)
    filtered_stats = generate_statistics(filtered_response_times)
    
    # Print statistics comparison
    print("\n" + "="*60)
    print("STATISTICS COMPARISON")
    print("="*60)
    print(f"{'Metric':<20} {'Original':<15} {'Filtered':<15} {'Change':<15}")
    print("-" * 65)
    
    metrics = ['count', 'mean', 'median', 'std', 'min', 'max', 'p50', 'p90', 'p95', 'p99', 'p99.9']
    for metric in metrics:
        orig_val = orig_stats[metric]
        filt_val = filtered_stats[metric]
        
        if metric == 'count':
            change = f"{((filt_val - orig_val) / orig_val) * 100:+.1f}%"
        else:
            change = f"{((filt_val - orig_val) / orig_val) * 100:+.1f}%" if orig_val != 0 else "N/A"
        
        if metric == 'count':
            print(f"{metric:<20} {orig_val:<15,} {filt_val:<15,} {change:<15}")
        else:
            print(f"{metric:<20} {orig_val:<15.2f} {filt_val:<15.2f} {change:<15}")
    
    # Save filtered CDF data
    save_cdf_data(sorted_data, cdf_values, output_csv)
    
    # Plot comparison CDF
    plot_comparison_cdf(original_response_times, filtered_response_times, output_plot)
    
    # Show some sample CDF values for filtered data
    print("\n" + "="*60)
    print("FILTERED DATA - SAMPLE CDF VALUES")
    print("="*60)
    print("Response Time (ms) | Cumulative Probability")
    print("-" * 40)
    
    # Show CDF values at key percentiles
    percentiles = [50, 90, 95, 99, 99.9]
    for p in percentiles:
        idx = int(p/100 * len(sorted_data)) - 1
        if idx >= 0 and idx < len(sorted_data):
            print(f"{sorted_data[idx]:>13.2f} | {cdf_values[idx]:>19.4f} ({p}%)")
    
    print(f"\nCDF analysis with outlier removal completed successfully!")
    print(f"Output files:")
    print(f"  Plot: {output_plot}")
    print(f"  Data: {output_csv}")

if __name__ == "__main__":
    main()