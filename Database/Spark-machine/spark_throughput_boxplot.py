#!/usr/bin/env python3
"""
Script to create normalized throughput box plots for Spark machine workload.
Extracts Overall Throughput values from continuous-results.txt files and 
normalizes all baseline results with respect to the default baseline.

Usage: python3 spark_throughput_boxplot.py
"""

import matplotlib.pyplot as plt
import numpy as np
import os
import re
from pathlib import Path
import statistics

def find_spark_folders():
    """Find all Spark experiment folders across different baselines."""
    base_path = Path(".")
    
    # Define patterns for each baseline based on folder naming
    baseline_patterns = {
        'default': '*default*',
        'ec': '*ec*', 
        'at': '*at*',
        'ap': '*ap*',
        'sw': '*sw*'
    }
    
    folders_by_baseline = {}
    
    for baseline, pattern in baseline_patterns.items():
        matching_folders = list(base_path.glob(f"spark-continuous-export*{baseline.replace('default', 'default')}*"))
        if matching_folders:
            folders_by_baseline[baseline] = matching_folders[0]  # Take the first match
        else:
            print(f"Warning: No folder found for {baseline} baseline")
    
    return folders_by_baseline

def extract_throughput_from_file(file_path):
    """Extract all Overall Throughput values from a continuous-results.txt file."""
    throughput_values = []
    
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            
            # Find all lines containing "Overall Throughput"
            matches = re.findall(r'Overall Throughput:\s*([0-9.]+)\s*edges/second', content)
            
            for match in matches:
                throughput_values.append(float(match))
                
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return throughput_values

def process_spark_data(folders_by_baseline):
    """Process all Spark baseline data and extract throughput values."""
    baseline_data = {}
    
    print("Processing Spark throughput data:")
    print("="*50)
    
    for baseline, folder in folders_by_baseline.items():
        results_file = folder / "output" / "continuous-results.txt"
        
        print(f"\nProcessing {baseline} baseline:")
        print(f"  Folder: {folder}")
        print(f"  Results file: {results_file}")
        
        if results_file.exists():
            throughput_vals = extract_throughput_from_file(results_file)
            
            if throughput_vals:
                baseline_data[baseline] = throughput_vals
                print(f"  Found {len(throughput_vals)} throughput measurements")
                print(f"  Range: {min(throughput_vals):.2f} - {max(throughput_vals):.2f} edges/second")
                print(f"  Average: {statistics.mean(throughput_vals):.2f} edges/second")
            else:
                print(f"  No throughput data found")
        else:
            print(f"  Results file not found: {results_file}")
    
    return baseline_data

def normalize_spark_data(baseline_data):
    """Normalize all baselines with respect to the default baseline average."""
    if 'default' not in baseline_data:
        print("Error: No default baseline data found!")
        return None
    
    # Calculate default baseline average
    default_values = baseline_data['default']
    default_avg = statistics.mean(default_values)
    
    print(f"\nSpark Baseline Statistics:")
    print(f"Default baseline average throughput: {default_avg:.2f} edges/second")
    
    # Normalize all baselines
    normalized_data = {}
    
    for baseline, values in baseline_data.items():
        normalized_values = [v / default_avg for v in values]
        normalized_data[baseline] = normalized_values
        
        avg_normalized = statistics.mean(normalized_values)
        std_normalized = statistics.stdev(normalized_values) if len(normalized_values) > 1 else 0
        
        print(f"{baseline}: avg={statistics.mean(values):.2f} -> normalized avg={avg_normalized:.4f} (±{std_normalized:.4f})")
    
    return normalized_data

def create_spark_boxplot(normalized_data):
    """Create box plot for normalized Spark throughput data."""
    
    # Prepare data for plotting
    baseline_names = {
        'default': 'Default', 
        'ec': 'Elastic Container', 
        'at': 'AutoThrottle', 
        'ap': 'AutoPilot',
        'sw': 'Showvar'
    }
    
    # Prepare data for box plot
    plot_data = []
    labels = []
    
    for baseline, values in normalized_data.items():
        if baseline in baseline_names:
            labels.append(baseline_names[baseline])
            plot_data.append(values)
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    
    # Create box plot
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    # Create the box plot
    box_plot = plt.boxplot(plot_data, labels=labels, patch_artist=True,
                          boxprops=dict(linewidth=2),
                          medianprops=dict(linewidth=2, color='red'),
                          whiskerprops=dict(linewidth=2),
                          capprops=dict(linewidth=2),
                          flierprops=dict(marker='o', markerfacecolor='red', markersize=6))
    
    # Color the boxes
    for patch, color in zip(box_plot['boxes'], colors[:len(plot_data)]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # Customize the plot
    plt.title('Spark Machine Throughput Box Plot\n(Normalized w.r.t. Default Baseline)', 
              fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Baseline Method', fontsize=14, fontweight='bold')
    plt.ylabel('Normalized Throughput', fontsize=14, fontweight='bold')
    
    # Add horizontal line at y=1 (default baseline)
    plt.axhline(y=1, color='black', linestyle='--', alpha=0.7, linewidth=2)
    plt.text(0.02, 1.02, 'Default Baseline', transform=plt.gca().get_yaxis_transform(), 
             fontsize=11, alpha=0.8, fontweight='bold')
    
    # Add statistics annotations
    for i, (baseline_values, label) in enumerate(zip(plot_data, labels)):
        if baseline_values:
            median_val = np.median(baseline_values)
            mean_val = np.mean(baseline_values)
            std_val = np.std(baseline_values)
            count = len(baseline_values)
            
            # Add text annotation with statistics
            stats_text = f'n={count}\nμ={mean_val:.3f}\nσ={std_val:.3f}'
            plt.text(i+1, max(baseline_values) + 0.05, stats_text, 
                    ha='center', va='bottom', fontsize=9, 
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # Improve grid
    plt.grid(True, alpha=0.3, axis='y')
    
    # Set y-axis limits to show differences better
    all_values = [val for sublist in plot_data for val in sublist]
    min_val = min(all_values)
    max_val = max(all_values)
    margin = (max_val - min_val) * 0.1 if max_val != min_val else 0.1
    plt.ylim(min_val - margin, max_val + margin + 0.1)
    
    # Rotate x-axis labels if needed
    plt.xticks(rotation=0, fontsize=12)
    plt.yticks(fontsize=12)
    
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('spark_throughput_boxplot.png', dpi=300, bbox_inches='tight')
    
    print(f"\nPlot saved as 'spark_throughput_boxplot.png'")
    
    # Show the plot
    plt.show()

def print_spark_summary(baseline_data, normalized_data):
    """Print detailed summary statistics for Spark."""
    print("\n" + "="*60)
    print("SPARK MACHINE THROUGHPUT SUMMARY")
    print("="*60)
    
    print(f"\nAbsolute Throughput Statistics (edges/second):")
    for baseline, values in baseline_data.items():
        baseline_name = {'default': 'Default', 'ec': 'Elastic Container', 
                        'at': 'AutoThrottle', 'ap': 'AutoPilot', 'sw': 'Showvar'}.get(baseline, baseline)
        
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 0
        min_val = min(values)
        max_val = max(values)
        
        print(f"  {baseline_name}:")
        print(f"    Count: {len(values)}")
        print(f"    Mean: {mean_val:.2f} ± {std_val:.2f}")
        print(f"    Range: {min_val:.2f} - {max_val:.2f}")
    
    print(f"\nNormalized Throughput (relative to Default):")
    default_avg = statistics.mean(baseline_data['default'])
    
    for baseline, values in normalized_data.items():
        baseline_name = {'default': 'Default', 'ec': 'Elastic Container', 
                        'at': 'AutoThrottle', 'ap': 'AutoPilot', 'sw': 'Showvar'}.get(baseline, baseline)
        
        mean_normalized = statistics.mean(values)
        std_normalized = statistics.stdev(values) if len(values) > 1 else 0
        
        if baseline != 'default':
            improvement = (mean_normalized - 1) * 100
            print(f"  {baseline_name}: {mean_normalized:.4f} ± {std_normalized:.4f} ({improvement:+.2f}%)")
        else:
            print(f"  {baseline_name}: {mean_normalized:.4f} ± {std_normalized:.4f} (baseline)")

def save_spark_data(baseline_data, normalized_data):
    """Save Spark data to CSV file."""
    output_file = 'spark_throughput_data.csv'
    
    import csv
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Baseline', 'Measurement_Index', 'Absolute_Throughput_edges_sec', 
                        'Normalized_Throughput', 'Performance_vs_Default_percent'])
        
        default_avg = statistics.mean(baseline_data['default'])
        
        for baseline, values in baseline_data.items():
            normalized_values = normalized_data[baseline]
            
            for i, (abs_throughput, norm_throughput) in enumerate(zip(values, normalized_values)):
                performance_vs_default = (norm_throughput - 1) * 100 if baseline != 'default' else 0
                
                writer.writerow([baseline, i+1, abs_throughput, norm_throughput, performance_vs_default])
    
    print(f"\nDetailed data saved to '{output_file}'")

def main():
    """Main function to orchestrate the Spark throughput analysis."""
    print("Spark Machine Throughput Analysis")
    print("="*40)
    
    # Find all Spark folders
    print("\n1. Finding Spark experiment folders...")
    folders_by_baseline = find_spark_folders()
    
    if not folders_by_baseline:
        print("Error: No Spark experiment folders found!")
        return
    
    print(f"\nFound folders:")
    for baseline, folder in folders_by_baseline.items():
        print(f"  {baseline}: {folder}")
    
    # Process the data
    print("\n2. Processing Spark data...")
    baseline_data = process_spark_data(folders_by_baseline)
    
    if not baseline_data:
        print("Error: No throughput data found!")
        return
    
    # Normalize data
    print("\n3. Normalizing data...")
    normalized_data = normalize_spark_data(baseline_data)
    
    if not normalized_data:
        return
    
    # Create plots
    print("\n4. Creating box plot...")
    create_spark_boxplot(normalized_data)
    
    # Print summary statistics
    print_spark_summary(baseline_data, normalized_data)
    
    # Save data to CSV
    save_spark_data(baseline_data, normalized_data)

if __name__ == "__main__":
    main()