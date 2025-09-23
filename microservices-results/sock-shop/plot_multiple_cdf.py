#!/usr/bin/env python3
"""
Script to plot Cumulative Distribution Function (CDF) for multiple CSV files.
Usage: python plot_multiple_cdf.py file1.csv file2.csv ... fileN.csv
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os
import argparse
from pathlib import Path


def read_csv_data(file_path, response_time_column='response_time_ms'):
    """
    Read CSV file and extract response time data.
    
    Args:
        file_path (str): Path to CSV file
        response_time_column (str): Name of the response time column
    
    Returns:
        numpy.ndarray: Array of response times
    """
    try:
        df = pd.read_csv(file_path)
        
        # Check if the specified column exists
        if response_time_column not in df.columns:
            print(f"Warning: Column '{response_time_column}' not found in {file_path}")
            print(f"Available columns: {list(df.columns)}")
            
            # Try common alternative column names
            alternative_names = ['response_time', 'latency', 'time', 'duration']
            for alt_name in alternative_names:
                if alt_name in df.columns:
                    response_time_column = alt_name
                    print(f"Using column '{alt_name}' instead")
                    break
            else:
                raise ValueError(f"No suitable response time column found in {file_path}")
        
        response_times = df[response_time_column].dropna()
        return response_times.values
    
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None


def calculate_cdf(data):
    """
    Calculate CDF for given data.
    
    Args:
        data (numpy.ndarray): Input data array
    
    Returns:
        tuple: (sorted_data, cdf_values)
    """
    sorted_data = np.sort(data)
    n = len(sorted_data)
    cdf_values = np.arange(1, n + 1) / n
    return sorted_data, cdf_values


def plot_multiple_cdfs(csv_files, output_file=None, response_time_column='response_time_ms'):
    """
    Plot CDFs for multiple CSV files with enhanced visualization for tail differences.
    
    Args:
        csv_files (list): List of CSV file paths
        output_file (str): Output file path for saving the plot
        response_time_column (str): Name of the response time column
    """
    # Create subplots for different views
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(csv_files)))
    all_data = []
    
    for i, csv_file in enumerate(csv_files):
        print(f"Processing {csv_file}...")
        
        # Read data
        response_times = read_csv_data(csv_file, response_time_column)
        
        if response_times is None or len(response_times) == 0:
            print(f"Skipping {csv_file} due to no valid data")
            continue
        
        # Calculate CDF
        sorted_times, cdf_values = calculate_cdf(response_times)
        
        # Get file name without extension for legend
        file_label = Path(csv_file).stem.replace('latency_logs-', '')
        
        # Store data for analysis
        stats = {
            'label': file_label,
            'data': response_times,
            'sorted_times': sorted_times,
            'cdf_values': cdf_values,
            'color': colors[i],
            'p50': np.percentile(response_times, 50),
            'p95': np.percentile(response_times, 95),
            'p99': np.percentile(response_times, 99),
            'p999': np.percentile(response_times, 99.9),
            'max': np.max(response_times),
            'mean': np.mean(response_times)
        }
        all_data.append(stats)
        
        # Print statistics
        print(f"  - Min: {np.min(response_times):.2f} ms")
        print(f"  - Max: {stats['max']:.2f} ms")
        print(f"  - Mean: {stats['mean']:.2f} ms")
        print(f"  - Median (P50): {stats['p50']:.2f} ms")
        print(f"  - 95th percentile: {stats['p95']:.2f} ms")
        print(f"  - 99th percentile: {stats['p99']:.2f} ms")
        print(f"  - 99.9th percentile: {stats['p999']:.2f} ms")
        print()
    
    if not all_data:
        print("No valid data to plot!")
        return
    
    # Plot 1: Full CDF (0-100%)
    for stats in all_data:
        ax1.plot(stats['sorted_times'], stats['cdf_values'], 
                color=stats['color'], label=f"{stats['label']}", 
                linewidth=2, alpha=0.8)
    
    ax1.set_xlabel('Response Time (ms)')
    ax1.set_ylabel('CDF')
    ax1.set_title('Full CDF (0-100%)')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.set_ylim(0, 1)
    
    # Plot 2: Zoomed CDF focusing on tail (90-100%)
    for stats in all_data:
        # Filter data for 90-100% range
        mask = stats['cdf_values'] >= 0.9
        if np.any(mask):
            ax2.plot(stats['sorted_times'][mask], stats['cdf_values'][mask], 
                    color=stats['color'], label=f"{stats['label']}", 
                    linewidth=2, alpha=0.8)
    
    ax2.set_xlabel('Response Time (ms)')
    ax2.set_ylabel('CDF')
    ax2.set_title('Tail CDF (90-100%) - Highlighting Differences')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    ax2.set_ylim(0.9, 1.0)
    
    # Add percentile reference lines
    ax2.axhline(y=0.95, color='red', linestyle='--', alpha=0.5, linewidth=1)
    ax2.axhline(y=0.99, color='darkred', linestyle='--', alpha=0.5, linewidth=1)
    ax2.axhline(y=0.999, color='maroon', linestyle='--', alpha=0.5, linewidth=1)
    
    # Plot 3: Log-scale x-axis for better separation
    for stats in all_data:
        ax3.semilogx(stats['sorted_times'], stats['cdf_values'], 
                    color=stats['color'], label=f"{stats['label']}", 
                    linewidth=2, alpha=0.8)
    
    ax3.set_xlabel('Response Time (ms) - Log Scale')
    ax3.set_ylabel('CDF')
    ax3.set_title('CDF with Log Scale X-axis')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    ax3.set_ylim(0, 1)
    
    # Plot 4: Percentile comparison bar chart
    percentiles = ['P50', 'P95', 'P99', 'P99.9']
    x_pos = np.arange(len(percentiles))
    width = 0.8 / len(all_data)
    
    for i, stats in enumerate(all_data):
        values = [stats['p50'], stats['p95'], stats['p99'], stats['p999']]
        ax4.bar(x_pos + i * width, values, width, 
               label=stats['label'], color=stats['color'], alpha=0.8)
    
    ax4.set_xlabel('Percentiles')
    ax4.set_ylabel('Response Time (ms)')
    ax4.set_title('Percentile Comparison')
    ax4.set_xticks(x_pos + width * (len(all_data) - 1) / 2)
    ax4.set_xticklabels(percentiles)
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for i, stats in enumerate(all_data):
        values = [stats['p50'], stats['p95'], stats['p99'], stats['p999']]
        for j, v in enumerate(values):
            ax4.text(x_pos[j] + i * width, v + max(values) * 0.01, 
                    f'{v:.1f}', ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    
    # Print summary comparison table
    print("\n" + "="*80)
    print("PERCENTILE COMPARISON SUMMARY")
    print("="*80)
    print(f"{'Dataset':<20} {'P50':<8} {'P95':<8} {'P99':<8} {'P99.9':<8} {'Max':<8}")
    print("-"*80)
    for stats in all_data:
        print(f"{stats['label']:<20} {stats['p50']:<8.1f} {stats['p95']:<8.1f} "
              f"{stats['p99']:<8.1f} {stats['p999']:<8.1f} {stats['max']:<8.1f}")
    
    # Save plot if output file specified
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"\nPlot saved to: {output_file}")
    
    # Show plot
    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description='Plot CDF for multiple CSV files containing response time data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python plot_multiple_cdf.py file1.csv file2.csv file3.csv
  python plot_multiple_cdf.py *.csv -o combined_cdf.png
  python plot_multiple_cdf.py data/*.csv --column latency_ms
        """
    )
    
    parser.add_argument('csv_files', nargs='+', help='CSV files to process')
    parser.add_argument('-o', '--output', help='Output file path for saving the plot')
    parser.add_argument('-c', '--column', default='response_time_ms',
                        help='Name of the response time column (default: response_time_ms)')
    
    args = parser.parse_args()
    
    # Validate input files
    valid_files = []
    for file_path in args.csv_files:
        if os.path.exists(file_path):
            valid_files.append(file_path)
        else:
            print(f"Warning: File not found: {file_path}")
    
    if not valid_files:
        print("Error: No valid CSV files found!")
        sys.exit(1)
    
    print(f"Processing {len(valid_files)} CSV files...")
    print(f"Response time column: {args.column}")
    print()
    
    # Plot CDFs
    plot_multiple_cdfs(valid_files, args.output, args.column)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: python plot_multiple_cdf.py file1.csv file2.csv ... [options]")
        print("Use --help for more options")
        sys.exit(1)
    
    main()