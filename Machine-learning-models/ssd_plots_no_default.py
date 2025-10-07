#!/usr/bin/env python3
"""
Create box plots and bar plots for SSD throughput data excluding default configuration.
Shows only ec, sw, at, and ap configurations.

Configurations:
- ec: elastic container
- sw: showvar
- at: autothrottle
- ap: autopilot
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import glob
from pathlib import Path

def find_ssd_csv_files():
    """Find all SSD CSV files and organize by type and configuration (excluding default)."""
    base_dir = "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models"
    
    files_data = {
        'training': {},
        'inference': {}
    }
    
    # Search pattern for SSD CSV files
    pattern = f"{base_dir}/ssd/exported-csv/*/*.csv"
    csv_files = glob.glob(pattern)
    
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        
        # Only process SSD files
        if 'ssd' not in filename.lower():
            continue
        
        # Determine operation type
        operation = None
        if 'training' in filename.lower():
            operation = 'training'
        elif 'inference' in filename.lower():
            operation = 'inference'
        
        if operation is None:
            continue
        
        # Extract configuration from filename (excluding default)
        config = None
        if filename.endswith('-ec.csv'):
            config = 'ec'
        elif filename.endswith('-sw.csv'):
            config = 'sw'
        elif filename.endswith('-at.csv'):
            config = 'at'
        elif filename.endswith('-ap.csv'):
            config = 'ap'
        # Skip default files
        
        if config is not None:
            files_data[operation][config] = file_path
    
    return files_data

def load_throughput_data(files_data):
    """Load throughput data from CSV files."""
    throughput_data = {
        'training': {},
        'inference': {}
    }
    
    for operation in ['training', 'inference']:
        for config, file_path in files_data[operation].items():
            try:
                df = pd.read_csv(file_path)
                
                # For SSD, throughput column is 'throughput'
                if 'throughput' in df.columns:
                    # Remove any NaN values
                    throughput_values = df['throughput'].dropna()
                    if len(throughput_values) > 0:
                        throughput_data[operation][config] = throughput_values.tolist()
                    else:
                        print(f"Warning: No valid throughput data in {file_path}")
                else:
                    print(f"Warning: No 'throughput' column in {file_path}")
                    
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
    
    return throughput_data

def create_box_plots(throughput_data):
    """Create box plots for throughput data (excluding default)."""
    
    # Configuration labels and colors
    config_labels = {
        'ec': 'Elastic Container',
        'sw': 'Showvar',
        'at': 'Autothrottle',
        'ap': 'Autopilot'
    }
    
    config_colors = {
        'ec': '#ff7f0e',       # orange
        'sw': '#2ca02c',       # green
        'at': '#d62728',       # red
        'ap': '#9467bd'        # purple
    }
    
    for operation in ['training', 'inference']:
        if not throughput_data[operation]:
            print(f"No data available for {operation}")
            continue
        
        # Prepare data for box plot
        configs = sorted(throughput_data[operation].keys())
        plot_data = [throughput_data[operation][config] for config in configs]
        plot_labels = [config_labels.get(config, config) for config in configs]
        plot_colors = [config_colors.get(config, '#888888') for config in configs]
        
        if not plot_data:
            continue
        
        # Create figure
        plt.figure(figsize=(10, 6))
        
        # Create box plot with color coding
        box_plot = plt.boxplot(plot_data, labels=plot_labels, patch_artist=True)
        
        # Apply colors to each box
        for patch, color in zip(box_plot['boxes'], plot_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        # Labels and title
        plt.title(f'SSD {operation.title()} Throughput Distribution', fontsize=14, fontweight='bold')
        plt.ylabel('Throughput (samples/sec)', fontsize=12)
        plt.xlabel('Configuration', fontsize=12)
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Save the plot
        output_file = f'ssd_{operation}_boxplot_no_default.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Saved {output_file}")
        
        plt.show()

def create_bar_plots(throughput_data):
    """Create bar plots showing median throughput for each configuration (excluding default)."""
    
    # Configuration labels and colors
    config_labels = {
        'ec': 'Elastic Container',
        'sw': 'Showvar',
        'at': 'Autothrottle',
        'ap': 'Autopilot'
    }
    
    config_colors = {
        'ec': '#ff7f0e',       # orange
        'sw': '#2ca02c',       # green
        'at': '#d62728',       # red
        'ap': '#9467bd'        # purple
    }
    
    for operation in ['training', 'inference']:
        if not throughput_data[operation]:
            continue
        
        # Calculate median throughput for each configuration
        configs = sorted(throughput_data[operation].keys())
        medians = []
        labels = []
        colors = []
        
        for config in configs:
            data = throughput_data[operation][config]
            if data:
                medians.append(np.median(data))
                labels.append(config_labels.get(config, config))
                colors.append(config_colors.get(config, '#888888'))
        
        if not medians:
            continue
        
        # Create figure
        plt.figure(figsize=(10, 6))
        
        # Create bar plot
        bars = plt.bar(labels, medians, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
        
        # Add value labels on bars
        for bar, median in zip(bars, medians):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                    f'{median:.2f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        # Labels and title
        plt.title(f'SSD {operation.title()} Median Throughput Comparison', fontsize=14, fontweight='bold')
        plt.ylabel('Median Throughput (samples/sec)', fontsize=12)
        plt.xlabel('Configuration', fontsize=12)
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        # Add grid for better readability
        plt.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        # Save the plot
        output_file = f'ssd_{operation}_barplot_no_default.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Saved {output_file}")
        
        plt.show()

def print_statistics_summary(throughput_data):
    """Print detailed statistics for each configuration (excluding default)."""
    
    config_labels = {
        'ec': 'Elastic Container',
        'sw': 'Showvar',
        'at': 'Autothrottle',
        'ap': 'Autopilot'
    }
    
    for operation in ['training', 'inference']:
        if not throughput_data[operation]:
            continue
        
        print(f"\n{operation.upper()} THROUGHPUT STATISTICS (Excluding Default)")
        print("=" * 60)
        
        configs = sorted(throughput_data[operation].keys())
        
        for config in configs:
            data = throughput_data[operation][config]
            if data:
                config_name = config_labels.get(config, config)
                print(f"\n{config_name}:")
                print(f"  Count: {len(data)}")
                print(f"  Mean: {np.mean(data):.3f}")
                print(f"  Median: {np.median(data):.3f}")
                print(f"  Std Dev: {np.std(data):.3f}")
                print(f"  Min: {np.min(data):.3f}")
                print(f"  Max: {np.max(data):.3f}")

def main():
    """Main function to create SSD throughput plots excluding default."""
    print("Finding SSD CSV files (excluding default)...")
    files_data = find_ssd_csv_files()
    
    # Print found files for verification
    print("\nFound SSD files (excluding default):")
    for operation in files_data:
        if files_data[operation]:
            print(f"{operation}:")
            for config, path in files_data[operation].items():
                print(f"  {config}: {path}")
    
    print("\nLoading throughput data...")
    throughput_data = load_throughput_data(files_data)
    
    print("\nCreating box plots...")
    create_box_plots(throughput_data)
    
    print("\nCreating bar plots...")
    create_bar_plots(throughput_data)
    
    print_statistics_summary(throughput_data)

if __name__ == "__main__":
    main()