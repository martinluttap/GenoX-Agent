#!/usr/bin/env python3
"""
Script to analyze Jasper benchmark results and create normalized box plots.

This script:
1. Searches for CSV files in jasper/benchmark-results/
2. Identifies baselines: ec, sw, at, ap, default
3. Normalizes all baselines against the default baseline
4. Creates box plots for training and inference throughput
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import glob
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def find_csv_files(base_path):
    """Find all CSV files in benchmark-results folders."""
    csv_files = {}
    
    # Search for all CSV files in benchmark-results subdirectories
    search_pattern = os.path.join(base_path, "benchmark-results", "*", "*.csv")
    csv_paths = glob.glob(search_pattern)
    
    for csv_path in csv_paths:
        filename = os.path.basename(csv_path)
        
        # Extract mode and baseline from filename
        # Expected format: {mode}_throughput-{baseline}.csv
        if "_throughput-" in filename and filename.endswith(".csv"):
            parts = filename.replace(".csv", "").split("_throughput-")
            if len(parts) == 2:
                mode = parts[0]  # 'training' or 'inference'
                baseline = parts[1]  # 'ec', 'sw', 'at', 'ap', 'default'
                
                if mode not in csv_files:
                    csv_files[mode] = {}
                
                csv_files[mode][baseline] = csv_path
    
    return csv_files

def load_and_process_data(csv_files):
    """Load CSV data and organize by mode and baseline."""
    data = {}
    
    for mode, baselines in csv_files.items():
        data[mode] = {}
        
        for baseline, csv_path in baselines.items():
            try:
                df = pd.read_csv(csv_path)
                
                # Extract throughput column (handle different column names)
                throughput_col = None
                if 'throughput' in df.columns:
                    throughput_col = 'throughput'
                elif 'avg_files_per_sec' in df.columns:
                    throughput_col = 'avg_files_per_sec'
                
                if throughput_col:
                    data[mode][baseline] = df[throughput_col].values
                    print(f"Loaded {mode} data for {baseline}: {len(df)} samples (using '{throughput_col}' column)")
                else:
                    print(f"Warning: No throughput column found in {csv_path}. Available columns: {list(df.columns)}")
                    
            except Exception as e:
                print(f"Error loading {csv_path}: {e}")
    
    return data

def normalize_against_default(data):
    """Normalize all baselines against the default baseline."""
    normalized_data = {}
    
    for mode, baselines in data.items():
        normalized_data[mode] = {}
        
        if 'default' not in baselines:
            print(f"Warning: No 'default' baseline found for {mode} mode")
            continue
        
        default_throughput = baselines['default']
        default_mean = np.mean(default_throughput)
        
        print(f"\n{mode.upper()} Mode:")
        print(f"Default baseline mean throughput: {default_mean:.4f}")
        
        for baseline, throughput_values in baselines.items():
            if len(throughput_values) > 0:
                # Normalize: (baseline_value / default_mean)
                normalized_values = throughput_values / default_mean
                normalized_data[mode][baseline] = normalized_values
                
                baseline_mean = np.mean(throughput_values)
                normalized_mean = np.mean(normalized_values)
                
                print(f"{baseline}: mean={baseline_mean:.4f}, normalized_mean={normalized_mean:.4f}")
        
    return normalized_data

def create_box_plots(normalized_data, output_dir, include_default=True):
    """Create box plots for normalized throughput data."""
    
    # Set up the plotting style
    plt.style.use('default')
    sns.set_palette("husl")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Define baseline labels and colors
    baseline_labels = {
        'default': 'Default',
        'ec': 'Elastic Container',
        'sw': 'Showvar',
        'at': 'Autothrottle', 
        'ap': 'Autopilot'
    }
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    for mode in ['inference', 'training']:
        if mode not in normalized_data:
            print(f"No data available for {mode} mode")
            continue
            
        # Prepare data for plotting
        plot_data = []
        labels = []
        
        # Order baselines based on include_default parameter
        if include_default:
            ordered_baselines = ['default'] + sorted([b for b in normalized_data[mode].keys() if b != 'default'])
        else:
            ordered_baselines = sorted([b for b in normalized_data[mode].keys() if b != 'default'])
        
        for baseline in ordered_baselines:
            if baseline in normalized_data[mode]:
                plot_data.append(normalized_data[mode][baseline])
                labels.append(baseline_labels.get(baseline, baseline.upper()))
        
        if not plot_data:
            print(f"No data to plot for {mode} mode")
            continue
        
        # Create the box plot
        fig, ax = plt.subplots(figsize=(12, 8))
        
        box_plot = ax.boxplot(plot_data, 
                             labels=labels,
                             patch_artist=True,
                             notch=True,
                             showmeans=True)
        
        # Color the boxes
        for patch, color in zip(box_plot['boxes'], colors[:len(plot_data)]):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        # Customize the plot
        title_suffix = "(Normalized against Default Baseline)"
        if not include_default:
            title_suffix = "(Normalized against Default, Default Excluded)"
        
        ax.set_title(f'Jasper {mode.title()} Throughput\n{title_suffix}', 
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel('Normalized Throughput\n(Relative to Default)', fontsize=14)
        ax.set_xlabel('Baseline Configuration', fontsize=14)
        
        # Add horizontal line at y=1 (default baseline) - always show for reference
        ax.axhline(y=1, color='red', linestyle='--', alpha=0.7, linewidth=2, label='Default Baseline (Reference)')
        ax.legend()
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        # Add grid
        ax.grid(True, alpha=0.3)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save the plot
        suffix = "_with_default" if include_default else "_no_default"
        output_path = os.path.join(output_dir, f'jasper_{mode}_normalized_boxplot{suffix}.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved {mode} box plot: {output_path}")
        
        plt.show()
    
    # Create combined plots (called at the end for both versions)

def create_combined_plot(normalized_data, output_dir, baseline_labels, include_default=True):
    """Create a combined plot showing both training and inference."""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    for idx, mode in enumerate(['inference', 'training']):
        ax = ax1 if idx == 0 else ax2
        
        if mode not in normalized_data:
            continue
            
        # Prepare data for plotting
        plot_data = []
        labels = []
        
        # Order baselines based on include_default parameter
        if include_default:
            ordered_baselines = ['default'] + sorted([b for b in normalized_data[mode].keys() if b != 'default'])
        else:
            ordered_baselines = sorted([b for b in normalized_data[mode].keys() if b != 'default'])
        
        for baseline in ordered_baselines:
            if baseline in normalized_data[mode]:
                plot_data.append(normalized_data[mode][baseline])
                labels.append(baseline_labels.get(baseline, baseline.upper()))
        
        if not plot_data:
            continue
        
        # Create the box plot
        box_plot = ax.boxplot(plot_data, 
                             labels=labels,
                             patch_artist=True,
                             notch=True,
                             showmeans=True)
        
        # Color the boxes
        for patch, color in zip(box_plot['boxes'], colors[:len(plot_data)]):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        # Customize the subplot
        ax.set_title(f'Jasper {mode.title()} Throughput', fontsize=14, fontweight='bold')
        ax.set_ylabel('Normalized Throughput\n(Relative to Default)', fontsize=12)
        ax.set_xlabel('Baseline Configuration', fontsize=12)
        
        # Add horizontal line at y=1 (default baseline)
        ax.axhline(y=1, color='red', linestyle='--', alpha=0.7, linewidth=2)
        
        # Rotate x-axis labels
        ax.tick_params(axis='x', rotation=45)
        
        # Add grid
        ax.grid(True, alpha=0.3)
    
    # Add overall title
    title_suffix = "Normalized Throughput Analysis"
    if not include_default:
        title_suffix = "Normalized Throughput Analysis (Default Excluded)"
    fig.suptitle(f'Jasper Benchmark Results - {title_suffix}', 
                fontsize=16, fontweight='bold', y=1.02)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the combined plot
    suffix = "_with_default" if include_default else "_no_default"
    output_path = os.path.join(output_dir, f'jasper_combined_normalized_boxplot{suffix}.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved combined box plot: {output_path}")
    
    plt.show()

def print_summary_statistics(normalized_data):
    """Print summary statistics for the normalized data."""
    
    print("\n" + "="*60)
    print("SUMMARY STATISTICS (Normalized Throughput)")
    print("="*60)
    
    for mode, baselines in normalized_data.items():
        print(f"\n{mode.upper()} MODE:")
        print("-" * 40)
        
        for baseline, values in baselines.items():
            if len(values) > 0:
                stats = {
                    'count': len(values),
                    'mean': np.mean(values),
                    'median': np.median(values),
                    'std': np.std(values),
                    'min': np.min(values),
                    'max': np.max(values)
                }
                
                print(f"{baseline.upper():12} | "
                      f"Count: {stats['count']:3d} | "
                      f"Mean: {stats['mean']:6.3f} | "
                      f"Median: {stats['median']:6.3f} | "
                      f"Std: {stats['std']:6.3f} | "
                      f"Range: [{stats['min']:6.3f}, {stats['max']:6.3f}]")

def main():
    """Main function to run the analysis."""
    
    # Get the current script directory and construct jasper path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    jasper_path = script_dir  # Since we're in the jasper folder
    
    print("Jasper Benchmark Analysis")
    print("=" * 50)
    print(f"Analyzing data in: {jasper_path}")
    
    # Find CSV files
    csv_files = find_csv_files(jasper_path)
    
    if not csv_files:
        print("No CSV files found in benchmark-results directories!")
        return
    
    print(f"\nFound CSV files for modes: {list(csv_files.keys())}")
    for mode, baselines in csv_files.items():
        print(f"  {mode}: {list(baselines.keys())}")
    
    # Load and process data
    print("\nLoading data...")
    data = load_and_process_data(csv_files)
    
    # Normalize against default
    print("\nNormalizing data against default baseline...")
    normalized_data = normalize_against_default(data)
    
    # Print summary statistics
    print_summary_statistics(normalized_data)
    
    # Create output directory
    output_dir = os.path.join(jasper_path, "analysis_results")
    
    # Define baseline labels
    baseline_labels = {
        'default': 'Default',
        'ec': 'Elastic Container',
        'sw': 'Showvar',
        'at': 'Autothrottle', 
        'ap': 'Autopilot'
    }
    
    # Create box plots - both with and without default
    print(f"\nCreating box plots with default baseline...")
    create_box_plots(normalized_data, output_dir, include_default=True)
    
    print(f"\nCreating box plots without default baseline (for comparison)...")
    create_box_plots(normalized_data, output_dir, include_default=False)
    
    # Create combined plots
    print(f"\nCreating combined plots...")
    create_combined_plot(normalized_data, output_dir, baseline_labels, include_default=True)
    create_combined_plot(normalized_data, output_dir, baseline_labels, include_default=False)
    
    print(f"\nAnalysis complete! Results saved in: {output_dir}")

if __name__ == "__main__":
    main()