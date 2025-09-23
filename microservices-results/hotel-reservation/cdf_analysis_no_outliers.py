#!/usr/bin/env python3
"""
Python script to parse CSV file and generate CDF (Cumulative Distribution Function)
for response_time_ms column after removing outliers using IQR method.
Automatically filters for successful requests only (success=True).
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import sys
import os

def read_csv_file(filepath):
    """Read the CSV file and return a pandas DataFrame filtered for successful requests only."""
    try:
        # Try reading with error handling for malformed rows
        try:
            df = pd.read_csv(filepath)
        except pd.errors.ParserError as e:
            print(f"⚠️  CSV parsing issue detected: {e}")
            print("Attempting to read with error handling...")
            # Try with error_bad_lines=False (pandas < 1.4) or on_bad_lines='skip' (pandas >= 1.4)
            try:
                df = pd.read_csv(filepath, on_bad_lines='skip')
            except TypeError:
                # Fallback for older pandas versions
                df = pd.read_csv(filepath, error_bad_lines=False, warn_bad_lines=True)
        
        print(f"Successfully loaded CSV file: {filepath}")
        print(f"Total records: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        
        # Filter for successful requests only if 'success' column exists
        if 'success' in df.columns:
            original_count = len(df)
            success_counts = df['success'].value_counts()
            
            print(f"\nSuccess Rate Analysis:")
            print(f"  ✅ Successful requests: {success_counts.get(True, 0)}")
            print(f"  ❌ Failed requests: {success_counts.get(False, 0)}")
            print(f"  Success rate: {success_counts.get(True, 0)/original_count*100:.1f}%")
            
            # Filter for successful requests only
            df_filtered = df[df['success'] == True].copy()
            print(f"\n🎯 Filtered to successful requests only: {len(df_filtered)} records")
            
            if len(df_filtered) == 0:
                print("❌ No successful requests found!")
                sys.exit(1)
            
            return df_filtered
        else:
            print("⚠️  No 'success' column found - using all records")
            return df
            
    except FileNotFoundError:
        print(f"Error: File {filepath} not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        print("Trying alternative parsing methods...")
        
        # Alternative parsing approach
        try:
            # Try reading line by line and handle malformed rows
            import csv
            rows = []
            expected_cols = None
            
            with open(filepath, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                header = next(reader)
                expected_cols = len(header)
                rows.append(header)
                
                for line_num, row in enumerate(reader, start=2):
                    if len(row) == expected_cols:
                        rows.append(row)
                    else:
                        print(f"Skipping malformed line {line_num}: expected {expected_cols} fields, got {len(row)}")
            
            # Create DataFrame from cleaned rows
            df = pd.DataFrame(rows[1:], columns=rows[0])
            print(f"Successfully parsed CSV with manual cleanup")
            print(f"Total valid records: {len(df)}")
            
            # Convert response_time_ms to numeric if it exists
            if 'response_time_ms' in df.columns:
                df['response_time_ms'] = pd.to_numeric(df['response_time_ms'], errors='coerce')
            
            # Convert success to boolean if it exists
            if 'success' in df.columns:
                df['success'] = df['success'].map({'True': True, 'False': False, True: True, False: False})
            
            return df
            
        except Exception as e2:
            print(f"Alternative parsing also failed: {e2}")
            sys.exit(1)

def remove_outliers_iqr(data, method='iqr', multiplier=1.5):
    """
    Remove outliers from data using different methods.
    
    Parameters:
    - data: numpy array of response times
    - method: 'iqr', 'zscore', or 'modified_zscore'
    - multiplier: multiplier for IQR method (default 1.5 is standard)
    
    Returns:
    - cleaned_data: data without outliers
    - outliers: the outliers that were removed
    - stats_dict: dictionary with outlier removal statistics
    """
    original_count = len(data)
    
    if method == 'iqr':
        # Interquartile Range (IQR) method
        Q1 = np.percentile(data, 25)
        Q3 = np.percentile(data, 75)
        IQR = Q3 - Q1
        
        # Define outlier bounds
        lower_bound = Q1 - multiplier * IQR
        upper_bound = Q3 + multiplier * IQR
        
        # Identify outliers
        outlier_mask = (data < lower_bound) | (data > upper_bound)
        outliers = data[outlier_mask]
        cleaned_data = data[~outlier_mask]
        
        method_info = f"IQR method (multiplier={multiplier})"
        bounds_info = f"Bounds: [{lower_bound:.2f}, {upper_bound:.2f}] ms"
        
    elif method == 'zscore':
        # Z-score method (remove data points > 3 standard deviations)
        z_scores = np.abs(stats.zscore(data))
        threshold = 3.0
        
        outlier_mask = z_scores > threshold
        outliers = data[outlier_mask]
        cleaned_data = data[~outlier_mask]
        
        method_info = f"Z-score method (threshold={threshold})"
        bounds_info = f"Mean ± {threshold}σ = [{np.mean(data) - threshold*np.std(data):.2f}, {np.mean(data) + threshold*np.std(data):.2f}] ms"
        
    elif method == 'modified_zscore':
        # Modified Z-score method using median absolute deviation
        median = np.median(data)
        mad = np.median(np.abs(data - median))
        modified_z_scores = 0.6745 * (data - median) / mad
        threshold = 3.5
        
        outlier_mask = np.abs(modified_z_scores) > threshold
        outliers = data[outlier_mask]
        cleaned_data = data[~outlier_mask]
        
        method_info = f"Modified Z-score method (threshold={threshold})"
        bounds_info = f"Based on median and MAD"
        
    else:
        raise ValueError("Method must be 'iqr', 'zscore', or 'modified_zscore'")
    
    outliers_count = len(outliers)
    outliers_percentage = (outliers_count / original_count) * 100
    
    stats_dict = {
        'original_count': original_count,
        'outliers_count': outliers_count,
        'cleaned_count': len(cleaned_data),
        'outliers_percentage': outliers_percentage,
        'method_info': method_info,
        'bounds_info': bounds_info,
        'outliers_min': np.min(outliers) if len(outliers) > 0 else None,
        'outliers_max': np.max(outliers) if len(outliers) > 0 else None
    }
    
    return cleaned_data, outliers, stats_dict

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

def plot_cdf_comparison(original_data, cleaned_data, outliers_stats, output_file='cdf_plot_no_outliers.png'):
    """Plot the CDF comparison between original and cleaned data."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    
    # Calculate CDFs
    orig_sorted, orig_cdf = calculate_cdf(original_data)
    clean_sorted, clean_cdf = calculate_cdf(cleaned_data)
    
    # 1. CDF Comparison
    axes[0, 0].plot(orig_sorted, orig_cdf, linewidth=2, color='red', alpha=0.7, label='Original Data')
    axes[0, 0].plot(clean_sorted, clean_cdf, linewidth=2, color='blue', label='Without Outliers')
    axes[0, 0].set_xlabel('Response Time (ms)')
    axes[0, 0].set_ylabel('Cumulative Probability')
    axes[0, 0].set_title('CDF Comparison')
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].legend()
    
    # 2. Log Scale CDF Comparison
    axes[0, 1].semilogx(orig_sorted, orig_cdf, linewidth=2, color='red', alpha=0.7, label='Original Data')
    axes[0, 1].semilogx(clean_sorted, clean_cdf, linewidth=2, color='blue', label='Without Outliers')
    axes[0, 1].set_xlabel('Response Time (ms) - Log Scale')
    axes[0, 1].set_ylabel('Cumulative Probability')
    axes[0, 1].set_title('CDF Comparison - Log Scale')
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].legend()
    
    # 3. Histogram Comparison
    axes[0, 2].hist(original_data, bins=100, alpha=0.5, color='red', density=True, label='Original Data')
    axes[0, 2].hist(cleaned_data, bins=100, alpha=0.7, color='blue', density=True, label='Without Outliers')
    axes[0, 2].set_xlabel('Response Time (ms)')
    axes[0, 2].set_ylabel('Density')
    axes[0, 2].set_title('Distribution Comparison')
    axes[0, 2].grid(True, alpha=0.3)
    axes[0, 2].legend()
    
    # 4. Box Plot Comparison
    box_data = [original_data, cleaned_data]
    box_labels = ['Original', 'No Outliers']
    axes[1, 0].boxplot(box_data, labels=box_labels)
    axes[1, 0].set_ylabel('Response Time (ms)')
    axes[1, 0].set_title('Box Plot Comparison')
    axes[1, 0].grid(True, alpha=0.3)
    
    # 5. Cleaned Data CDF (focused view)
    axes[1, 1].plot(clean_sorted, clean_cdf, linewidth=2, color='green')
    axes[1, 1].set_xlabel('Response Time (ms)')
    axes[1, 1].set_ylabel('Cumulative Probability')
    axes[1, 1].set_title('Cleaned Data CDF (Focused View)')
    axes[1, 1].grid(True, alpha=0.3)
    
    # 6. Statistics Text
    axes[1, 2].axis('off')
    stats_text = f"""Outlier Removal Statistics:
    
Method: {outliers_stats['method_info']}
{outliers_stats['bounds_info']}

Original Data Points: {outliers_stats['original_count']:,}
Outliers Removed: {outliers_stats['outliers_count']:,} ({outliers_stats['outliers_percentage']:.1f}%)
Cleaned Data Points: {outliers_stats['cleaned_count']:,}

Original Range: {np.min(original_data):.1f} - {np.max(original_data):.1f} ms
Cleaned Range: {np.min(cleaned_data):.1f} - {np.max(cleaned_data):.1f} ms
"""
    if outliers_stats['outliers_count'] > 0:
        stats_text += f"\nOutliers Range: {outliers_stats['outliers_min']:.1f} - {outliers_stats['outliers_max']:.1f} ms"
    
    axes[1, 2].text(0.1, 0.5, stats_text, fontsize=10, verticalalignment='center',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.5))
    axes[1, 2].set_title('Outlier Removal Summary')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.show()
    print(f"CDF comparison plot saved as: {output_file}")

def save_cdf_data(sorted_data, cdf_values, outliers_stats, output_file='cdf_data_no_outliers.csv'):
    """Save CDF data and outlier removal stats to CSV file."""
    cdf_df = pd.DataFrame({
        'response_time_ms': sorted_data,
        'cumulative_probability': cdf_values
    })
    cdf_df.to_csv(output_file, index=False)
    
    # Save outlier removal statistics
    stats_file = output_file.replace('.csv', '_stats.txt')
    with open(stats_file, 'w') as f:
        f.write("Outlier Removal Statistics\n")
        f.write("=" * 30 + "\n")
        f.write(f"Method: {outliers_stats['method_info']}\n")
        f.write(f"{outliers_stats['bounds_info']}\n")
        f.write(f"Original data points: {outliers_stats['original_count']:,}\n")
        f.write(f"Outliers removed: {outliers_stats['outliers_count']:,} ({outliers_stats['outliers_percentage']:.1f}%)\n")
        f.write(f"Cleaned data points: {outliers_stats['cleaned_count']:,}\n")
        if outliers_stats['outliers_count'] > 0:
            f.write(f"Outliers range: {outliers_stats['outliers_min']:.1f} - {outliers_stats['outliers_max']:.1f} ms\n")
    
    print(f"CDF data saved as: {output_file}")
    print(f"Outlier removal stats saved as: {stats_file}")

def main():
    # Define input file path and outlier removal method
    if len(sys.argv) < 2:
        print("Usage: python cdf_analysis_no_outliers.py <input_csv_file> [method] [multiplier]")
        print("Methods: iqr (default), zscore, modified_zscore")
        print("Multiplier: for IQR method only (default: 1.5)")
        sys.exit(1)
    
    input_file = sys.argv[1]
    method = sys.argv[2] if len(sys.argv) > 2 else 'iqr'
    multiplier = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5
    
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
    
    # Remove outliers
    print(f"\n🔧 Removing outliers using {method} method...")
    cleaned_response_times, outliers, outliers_stats = remove_outliers_iqr(
        original_response_times, method=method, multiplier=multiplier
    )
    
    # Print outlier removal results
    print("\n" + "="*60)
    print("OUTLIER REMOVAL RESULTS")
    print("="*60)
    print(f"Method: {outliers_stats['method_info']}")
    print(f"{outliers_stats['bounds_info']}")
    print(f"Original data points: {outliers_stats['original_count']:,}")
    print(f"Outliers removed: {outliers_stats['outliers_count']:,} ({outliers_stats['outliers_percentage']:.1f}%)")
    print(f"Cleaned data points: {outliers_stats['cleaned_count']:,}")
    if outliers_stats['outliers_count'] > 0:
        print(f"Outliers range: {outliers_stats['outliers_min']:.1f} - {outliers_stats['outliers_max']:.1f} ms")
    
    # Calculate CDF for cleaned data
    sorted_data, cdf_values = calculate_cdf(cleaned_response_times)
    
    # Generate statistics for both original and cleaned data
    original_stats = generate_statistics(original_response_times)
    cleaned_stats = generate_statistics(cleaned_response_times)
    
    # Print statistics comparison
    print("\n" + "="*60)
    print("STATISTICS COMPARISON")
    print("="*60)
    print(f"{'Metric':<20} {'Original':<15} {'No Outliers':<15} {'Difference':<15}")
    print("-" * 65)
    
    metrics = ['mean', 'median', 'std', 'min', 'max', 'p50', 'p90', 'p95', 'p99', 'p99.9']
    for metric in metrics:
        orig_val = original_stats[metric]
        clean_val = cleaned_stats[metric]
        diff = orig_val - clean_val
        diff_pct = (diff / orig_val * 100) if orig_val != 0 else 0
        
        print(f"{metric.upper():<20} {orig_val:<15.2f} {clean_val:<15.2f} {diff:>+7.2f} ({diff_pct:>+5.1f}%)")
    
    # Save CDF data
    output_base = os.path.splitext(input_file)[0] + "_no_outliers"
    save_cdf_data(sorted_data, cdf_values, outliers_stats, f"{output_base}.csv")
    
    # Plot CDF comparison
    plot_cdf_comparison(original_response_times, cleaned_response_times, 
                       outliers_stats, f"{output_base}.png")
    
    # Optional: Show some sample CDF values
    print("\n" + "="*60)
    print("SAMPLE CDF VALUES (CLEANED DATA)")
    print("="*60)
    print("Response Time (ms) | Cumulative Probability")
    print("-" * 40)
    
    # Show CDF values at key percentiles
    percentiles = [50, 90, 95, 99, 99.9]
    for p in percentiles:
        idx = int(p/100 * len(sorted_data)) - 1
        if idx >= 0 and idx < len(sorted_data):
            print(f"{sorted_data[idx]:>13.2f} | {cdf_values[idx]:>19.4f} ({p}%)")
    
    print(f"\n✅ CDF analysis with outlier removal completed successfully!")
    print(f"📊 Outlier removal method: {outliers_stats['method_info']}")
    print(f"🗂️  Output files: {output_base}.csv, {output_base}.png, {output_base}_stats.txt")

if __name__ == "__main__":
    main()