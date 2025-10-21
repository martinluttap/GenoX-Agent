#!/usr/bin/env python3
"""
Script to create normalized throughput box plots specifically for Cassandra workload.
Normalizes all baseline results (ec, at, ap, sw) with respect to the default baseline.

Usage: python3 cassandra_throughput_boxplot.py
"""

import csv
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path

def find_cassandra_files():
    """Find all Cassandra throughput CSV files across different baselines."""
    cassandra_path = Path(".")  # Current directory (Cassandra folder)
    
    # Define folder patterns for each baseline
    baseline_folders = {
        'default': 'pod-logs_20251017_000634-default',
        'ec': 'pod-logs_20251017_010137-ec', 
        'at': 'pod-logs_20251017_025221-at',
        'ap': 'pod-logs_20251017_023650-ap',
        'sw': 'pod-logs_20251017_013203-sw'  # Additional baseline found
    }
    
    files_by_baseline = {}
    
    for baseline, folder in baseline_folders.items():
        file_path = cassandra_path / folder / "throughput-data.csv"
        if file_path.exists():
            files_by_baseline[baseline] = str(file_path)
        else:
            print(f"Warning: File not found for {baseline}: {file_path}")
    
    return files_by_baseline

def extract_cassandra_throughput(file_path):
    """Extract throughput values from Cassandra CSV file."""
    throughput_values = []
    
    try:
        with open(file_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if 'throughput_ops_sec' in row:
                    throughput_values.append(float(row['throughput_ops_sec']))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return throughput_values

def process_cassandra_data(files_by_baseline):
    """Process all Cassandra baseline data and extract throughput values."""
    baseline_data = {}
    
    print("Processing Cassandra throughput data:")
    print("="*50)
    
    for baseline, file_path in files_by_baseline.items():
        print(f"\nProcessing {baseline} baseline:")
        print(f"  Reading: {file_path}")
        
        throughput_vals = extract_cassandra_throughput(file_path)
        
        if throughput_vals:
            baseline_data[baseline] = throughput_vals
            print(f"  Found {len(throughput_vals)} throughput values")
            print(f"  Throughput: {throughput_vals[0]:.2f} ops/sec")
        else:
            print(f"  No throughput data found")
    
    return baseline_data

def normalize_cassandra_data(baseline_data):
    """Normalize all baselines with respect to the default baseline."""
    if 'default' not in baseline_data:
        print("Error: No default baseline data found!")
        return None
    
    # Get default baseline value
    default_throughput = baseline_data['default'][0]  # Single value per baseline
    
    print(f"\nCassandra Baseline Statistics:")
    print(f"Default baseline throughput: {default_throughput:.2f} ops/sec")
    
    # Normalize all baselines
    normalized_data = {}
    
    for baseline, values in baseline_data.items():
        normalized_values = [v / default_throughput for v in values]
        normalized_data[baseline] = normalized_values
        
        print(f"{baseline}: {values[0]:.2f} ops/sec -> {normalized_values[0]:.4f} (normalized)")
    
    return normalized_data

def create_cassandra_boxplot(normalized_data):
    """Create bar chart for normalized Cassandra throughput data."""
    
    # Prepare data for plotting
    baseline_names = {
        'default': 'Default', 
        'ec': 'Elastic Container', 
        'at': 'AutoThrottle', 
        'ap': 'AutoPilot',
        'sw': 'Showvar' 
    }
    
    # Extract data for plotting
    baselines = []
    throughput_values = []
    
    for baseline, values in normalized_data.items():
        if baseline in baseline_names:
            baselines.append(baseline_names[baseline])
            throughput_values.append(values[0])  # Single value per baseline
    
    # Create the plot
    plt.figure(figsize=(10, 8))
    
    # Create a bar plot since we have single values
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    bars = plt.bar(baselines, throughput_values, color=colors[:len(baselines)], 
                   alpha=0.7, edgecolor='black', linewidth=1.5)
    
    # Customize the plot
    plt.title('Cassandra Throughput Performance\n(Normalized w.r.t. Default Baseline)', 
              fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Baseline Method', fontsize=14, fontweight='bold')
    plt.ylabel('Normalized Throughput', fontsize=14, fontweight='bold')
    
    # Add horizontal line at y=1 (default baseline)
    plt.axhline(y=1, color='black', linestyle='--', alpha=0.7, linewidth=2)
    plt.text(0.02, 1.02, 'Default Baseline', transform=plt.gca().get_yaxis_transform(), 
             fontsize=11, alpha=0.8, fontweight='bold')
    
    # Add value labels on bars
    for bar, value in zip(bars, throughput_values):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.001,
                f'{value:.4f}', ha='center', va='bottom', 
                fontsize=12, fontweight='bold')
    
    # Improve grid
    plt.grid(True, alpha=0.3, axis='y')
    
    # Set y-axis limits to show differences better
    min_val = min(throughput_values)
    max_val = max(throughput_values)
    margin = (max_val - min_val) * 0.1 if max_val != min_val else 0.1
    plt.ylim(min_val - margin, max_val + margin + 0.02)
    
    # Rotate x-axis labels if needed
    plt.xticks(rotation=45, fontsize=12)
    plt.yticks(fontsize=12)
    
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('cassandra_throughput_comparison.png', dpi=300, bbox_inches='tight')
    
    print(f"\nPlot saved as 'cassandra_throughput_comparison.png'")
    
    # Show the plot
    plt.show()

def print_cassandra_summary(baseline_data, normalized_data):
    """Print detailed summary statistics for Cassandra."""
    print("\n" + "="*60)
    print("CASSANDRA THROUGHPUT SUMMARY")
    print("="*60)
    
    print(f"\nAbsolute Throughput (ops/sec):")
    for baseline, values in baseline_data.items():
        baseline_name = {'default': 'Default', 'ec': 'Elastic Container', 
                        'at': 'AutoThrottle', 'ap': 'AutoPilot', 'sw': 'SockShop'}.get(baseline, baseline)
        print(f"  {baseline_name}: {values[0]:.2f}")
    
    print(f"\nNormalized Throughput (relative to Default):")
    default_throughput = baseline_data['default'][0]
    
    for baseline, values in normalized_data.items():
        baseline_name = {'default': 'Default', 'ec': 'Elastic Container', 
                        'at': 'AutoThrottle', 'ap': 'AutoPilot', 'sw': 'SockShop'}.get(baseline, baseline)
        normalized_val = values[0]
        
        if baseline != 'default':
            improvement = (normalized_val - 1) * 100
            print(f"  {baseline_name}: {normalized_val:.4f} ({improvement:+.2f}%)")
        else:
            print(f"  {baseline_name}: {normalized_val:.4f} (baseline)")

def save_cassandra_data(baseline_data, normalized_data):
    """Save Cassandra data to CSV file."""
    output_file = 'cassandra_throughput_data.csv'
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Baseline', 'Absolute_Throughput_ops_sec', 'Normalized_Throughput', 'Performance_vs_Default_percent'])
        
        default_throughput = baseline_data['default'][0]
        
        for baseline, values in baseline_data.items():
            abs_throughput = values[0]
            normalized_throughput = normalized_data[baseline][0]
            performance_vs_default = (normalized_throughput - 1) * 100 if baseline != 'default' else 0
            
            writer.writerow([baseline, abs_throughput, normalized_throughput, performance_vs_default])
    
    print(f"\nData saved to '{output_file}'")

def main():
    """Main function to orchestrate the Cassandra throughput analysis."""
    print("Cassandra Throughput Analysis")
    print("="*40)
    
    # Find all Cassandra files
    print("\n1. Finding Cassandra throughput CSV files...")
    files_by_baseline = find_cassandra_files()
    
    if not files_by_baseline:
        print("Error: No Cassandra throughput files found!")
        return
    
    print(f"\nFound files:")
    for baseline, file_path in files_by_baseline.items():
        print(f"  {baseline}: {file_path}")
    
    # Process the data
    print("\n2. Processing Cassandra data...")
    baseline_data = process_cassandra_data(files_by_baseline)
    
    if not baseline_data:
        print("Error: No throughput data found!")
        return
    
    # Normalize data
    print("\n3. Normalizing data...")
    normalized_data = normalize_cassandra_data(baseline_data)
    
    if not normalized_data:
        return
    
    # Create plots
    print("\n4. Creating throughput comparison plot...")
    create_cassandra_boxplot(normalized_data)
    
    # Print summary statistics
    print_cassandra_summary(baseline_data, normalized_data)
    
    # Save data to CSV
    save_cassandra_data(baseline_data, normalized_data)

if __name__ == "__main__":
    main()