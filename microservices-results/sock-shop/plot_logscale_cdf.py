#!/usr/bin/env python3
"""
Script to plot CDF with log-scale and tail focus for better visualization of differences.
Usage: python plot_logscale_cdf.py file1.csv file2.csv ... fileN.csv
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


def plot_logscale_cdfs(csv_files, output_file=None, response_time_column='response_time_ms'):
    """
    Plot CDFs with log-scale and tail focus for better comparison.
    
    Args:
        csv_files (list): List of CSV file paths
        output_file (str): Output file path for saving the plot
        response_time_column (str): Name of the response time column
    """
    # Create figure with two subplots side by side
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Use different line styles for better distinction
    colors = plt.cm.Set1(np.linspace(0, 1, len(csv_files)))
    line_styles = ['-', '--', '-.', ':', '-', '--', '-.', ':']
    markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p']
    
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
        
        # Store statistics
        stats = {
            'label': file_label,
            'sorted_times': sorted_times,
            'cdf_values': cdf_values,
            'color': colors[i % len(colors)],
            'line_style': line_styles[i % len(line_styles)],
            'marker': markers[i % len(markers)],
            'p50': np.percentile(response_times, 50),
            'p95': np.percentile(response_times, 95),
            'p99': np.percentile(response_times, 99),
            'p999': np.percentile(response_times, 99.9),
            'count': len(response_times)
        }
        all_data.append(stats)
        
        # Print key statistics
        print(f"  - Dataset: {file_label}")
        print(f"  - Count: {stats['count']:,} requests")
        print(f"  - P50: {stats['p50']:.2f} ms")
        print(f"  - P95: {stats['p95']:.2f} ms")
        print(f"  - P99: {stats['p99']:.2f} ms")
        print(f"  - P99.9: {stats['p999']:.2f} ms")
        print()
    
    if not all_data:
        print("No valid data to plot!")
        return
    
    # Plot 1: Log-scale X-axis CDF
    for i, stats in enumerate(all_data):
        # Sample points for cleaner log-scale visualization
        sample_indices = np.logspace(0, np.log10(len(stats['sorted_times'])-1), 1000).astype(int)
        sample_indices = np.unique(sample_indices)
        
        ax1.semilogx(stats['sorted_times'][sample_indices], 
                    stats['cdf_values'][sample_indices],
                    color=stats['color'], 
                    linestyle=stats['line_style'],
                    linewidth=2.5, 
                    alpha=0.8,
                    label=f"{stats['label']} (n={stats['count']:,})",
                    marker=stats['marker'],
                    markersize=4,
                    markevery=50)
    
    ax1.set_xlabel('Response Time (ms) - Log Scale', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Cumulative Distribution Function (CDF)', fontsize=12, fontweight='bold')
    ax1.set_title('CDF with Log Scale X-axis\n(Better separation of overlapping curves)', 
                  fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3, which='both')
    ax1.legend(loc='lower right', frameon=True, fancybox=True, shadow=True)
    ax1.set_ylim(0, 1)
    
    # Add percentile reference lines
    ax1.axhline(y=0.5, color='gray', linestyle=':', alpha=0.7, linewidth=1)
    ax1.axhline(y=0.95, color='orange', linestyle=':', alpha=0.7, linewidth=1)
    ax1.axhline(y=0.99, color='red', linestyle=':', alpha=0.7, linewidth=1)
    ax1.axhline(y=0.999, color='darkred', linestyle=':', alpha=0.7, linewidth=1)
    
    # Add text labels for percentile lines
    ax1.text(ax1.get_xlim()[1] * 0.7, 0.51, 'P50', fontsize=9, alpha=0.7)
    ax1.text(ax1.get_xlim()[1] * 0.7, 0.96, 'P95', fontsize=9, alpha=0.7)
    ax1.text(ax1.get_xlim()[1] * 0.7, 1.00, 'P99', fontsize=9, alpha=0.7)
    
    # Plot 2: Tail CDF (95-100%) with linear scale for precise tail comparison
    for stats in all_data:
        # Filter data for 95-100% range
        mask = stats['cdf_values'] >= 0.95
        if np.any(mask):
            ax2.plot(stats['sorted_times'][mask], 
                    stats['cdf_values'][mask],
                    color=stats['color'], 
                    linestyle=stats['line_style'],
                    linewidth=3, 
                    alpha=0.9,
                    label=f"{stats['label']}",
                    marker=stats['marker'],
                    markersize=5,
                    markevery=max(1, len(stats['sorted_times'][mask])//20))
    
    ax2.set_xlabel('Response Time (ms)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('CDF', fontsize=12, fontweight='bold')
    ax2.set_title('Tail Latency Focus (95-100%)\n(Highlighting high-percentile differences)', 
                  fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='lower right', frameon=True, fancybox=True, shadow=True)
    ax2.set_ylim(0.95, 1.0)
    
    # Add percentile reference lines for tail plot
    ax2.axhline(y=0.95, color='orange', linestyle='--', alpha=0.5, linewidth=1)
    ax2.axhline(y=0.99, color='red', linestyle='--', alpha=0.5, linewidth=1)
    ax2.axhline(y=0.999, color='darkred', linestyle='--', alpha=0.5, linewidth=1)
    
    # Add percentile labels
    ax2.text(ax2.get_xlim()[0], 0.952, 'P95', fontsize=10, fontweight='bold')
    ax2.text(ax2.get_xlim()[0], 0.992, 'P99', fontsize=10, fontweight='bold')
    ax2.text(ax2.get_xlim()[0], 1.001, 'P99.9', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    
    # Print comparison table
    print("\n" + "="*85)
    print("TAIL LATENCY COMPARISON - Key Performance Indicators")
    print("="*85)
    print(f"{'Dataset':<15} {'Count':<10} {'P50':<8} {'P95':<8} {'P99':<8} {'P99.9':<8} {'P99/P95':<8}")
    print("-"*85)
    
    for stats in all_data:
        p99_p95_ratio = stats['p99'] / stats['p95'] if stats['p95'] > 0 else 0
        print(f"{stats['label']:<15} {stats['count']:<10,} {stats['p50']:<8.1f} "
              f"{stats['p95']:<8.1f} {stats['p99']:<8.1f} {stats['p999']:<8.1f} "
              f"{p99_p95_ratio:<8.2f}x")
    
    print("\nInterpretation:")
    print("- P99/P95 ratio > 2.0x indicates significant tail latency issues")
    print("- Look for datasets with higher P99 and P99.9 values")
    print("- Log-scale plot shows separation that linear scale hides")
    
    # Save plot if output file specified
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"\nPlot saved to: {output_file}")
    
    # Show plot
    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description='Plot CDF with log-scale and tail focus for better performance comparison',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python plot_logscale_cdf.py file1.csv file2.csv file3.csv
  python plot_logscale_cdf.py *.csv -o logscale_cdf.png
  python plot_logscale_cdf.py data/*.csv --column latency_ms
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
    
    print(f"Analyzing {len(valid_files)} CSV files with log-scale visualization...")
    print(f"Response time column: {args.column}")
    print()
    
    # Plot CDFs
    plot_logscale_cdfs(valid_files, args.output, args.column)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: python plot_logscale_cdf.py file1.csv file2.csv ... [options]")
        print("Use --help for more options")
        sys.exit(1)
    
    main()