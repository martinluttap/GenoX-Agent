#!/usr/bin/env python3
"""
Create box plots for ML model throughput data across different configurations.
Shows the distribution of throughput values for each configuration.
Works for both SSD and ResNet models.

Configurations:
- default: baseline
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

def find_csv_files(model_name='ssd'):
    """Find CSV files for specified model and organize by type and configuration."""
    base_dir = "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models"
    
    files_data = {
        'training': {},
        'inference': {}
    }
    
    # Search pattern based on model
    if model_name.lower() == 'ssd':
        pattern = f"{base_dir}/ssd/exported-csv/*/*.csv"
    elif model_name.lower() == 'resnet':
        pattern = f"{base_dir}/resnet/exported-csv/*/*.csv"
    else:
        pattern = f"{base_dir}/{model_name}/exported-csv/*/*.csv"
    
    csv_files = glob.glob(pattern)
    
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        
        # Check if file matches the model
        if model_name.lower() not in filename.lower():
            continue
        
        # Determine operation type
        operation = None
        if 'training' in filename.lower():
            operation = 'training'
        elif 'inference' in filename.lower():
            operation = 'inference'
        
        # Special case for ResNet - only has inference data
        if model_name.lower() == 'resnet' and operation is None:
            # ResNet files don't have training/inference in filename, assume inference
            operation = 'inference'
        
        if operation is None:
            continue
        
        # Extract configuration from filename
        config = 'default'  # default value
        if filename.endswith('-ec.csv'):
            config = 'ec'
        elif filename.endswith('-sw.csv'):
            config = 'sw'
        elif filename.endswith('-at.csv'):
            config = 'at'
        elif filename.endswith('-ap.csv'):
            config = 'ap'
        elif filename.endswith('-default.csv'):
            config = 'default'
        
        files_data[operation][config] = file_path
    
    return files_data

def load_throughput_data(files_data, model_name='ssd'):
    """Load throughput data from CSV files and normalize against default."""
    throughput_data = {
        'training': {},
        'inference': {}
    }
    
    for operation in ['training', 'inference']:
        # First, load all raw data
        raw_data = {}
        
        for config, file_path in files_data[operation].items():
            try:
                df = pd.read_csv(file_path)
                
                # Determine throughput column based on model
                throughput_col = None
                if model_name.lower() == 'ssd':
                    throughput_col = 'throughput'
                elif model_name.lower() == 'resnet':
                    if operation == 'inference':
                        throughput_col = 'inference_throughput_examples_per_sec'
                
                if throughput_col and throughput_col in df.columns:
                    # Remove any NaN values
                    throughput_values = df[throughput_col].dropna()
                    if len(throughput_values) > 0:
                        raw_data[config] = throughput_values.tolist()
                    else:
                        print(f"Warning: No valid throughput data in {file_path}")
                else:
                    print(f"Warning: No '{throughput_col}' column in {file_path}")
                    
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
        
        # Normalize against default if default exists
        if 'default' in raw_data and raw_data['default']:
            default_median = np.median(raw_data['default'])
            print(f"{model_name.upper()} {operation} - Default baseline: {default_median:.3f}")
            
            # Normalize all configurations against default
            for config, values in raw_data.items():
                normalized_values = [val / default_median for val in values]
                throughput_data[operation][config] = normalized_values
        else:
            # If no default, use raw values
            print(f"Warning: No default configuration found for {model_name} {operation}, using raw values")
            throughput_data[operation] = raw_data
    
    return throughput_data

def create_box_plots(throughput_data, model_name='ssd', exclude_configs=None, output_suffix=''):
    """Create minimal box plots for throughput data with color coding."""
    
    # Simple configuration labels
    config_labels = {
        'default': 'Default',
        'ec': 'EC',
        'sw': 'SW',
        'at': 'AT',
        'ap': 'AP'
    }
    
    # Color coding for each configuration
    config_colors = {
        'default': '#1f77b4',  # blue
        'ec': '#ff7f0e',       # orange
        'sw': '#2ca02c',       # green
        'at': '#d62728',       # red
        'ap': '#9467bd'        # purple
    }
    
    if exclude_configs is None:
        exclude_configs = []
    
    for operation in ['training', 'inference']:
        if not throughput_data[operation]:
            continue
        
        # Filter out excluded configurations
        filtered_data = {k: v for k, v in throughput_data[operation].items() 
                        if k not in exclude_configs}
        
        if not filtered_data:
            continue
        
        # Prepare data for box plot
        configs = sorted(filtered_data.keys())
        plot_data = [filtered_data[config] for config in configs]
        plot_labels = [config_labels.get(config, config) for config in configs]
        plot_colors = [config_colors.get(config, '#888888') for config in configs]
        
        if not plot_data:
            continue
        
        # Create minimal figure
        plt.figure(figsize=(8, 6))
        
        # Create box plot with color coding
        box_plot = plt.boxplot(plot_data, labels=plot_labels, patch_artist=True)
        
        # Apply colors to each box
        for patch, color in zip(box_plot['boxes'], plot_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        # Minimal labels
        plt.title(f'{model_name.upper()} {operation.title()} (Normalized to Default)')
        plt.ylabel('Normalized Throughput (Default = 1.0)')
        
        # Add horizontal line at y=1 (baseline)
        plt.axhline(y=1, color='black', linestyle='--', alpha=0.5, linewidth=1)
        
        plt.tight_layout()
        
        # Save the plot
        if output_suffix:
            output_file = f'{model_name}_{operation}_{output_suffix}_normalized_boxplot.png'
        else:
            output_file = f'{model_name}_{operation}_normalized_boxplot.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Saved {output_file}")
        
        plt.show()

def print_statistics_summary(throughput_data, model_name='ssd'):
    """Print detailed statistics for each configuration."""
    
    config_labels = {
        'default': 'Default',
        'ec': 'Elastic Container',
        'sw': 'Showvar',
        'at': 'Autothrottle',
        'ap': 'Autopilot'
    }
    
    for operation in ['training', 'inference']:
        if not throughput_data[operation]:
            continue
        
        print(f"\n{model_name.upper()} {operation.upper()} NORMALIZED THROUGHPUT STATISTICS")
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
                print(f"  Q1: {np.percentile(data, 25):.3f}")
                print(f"  Q3: {np.percentile(data, 75):.3f}")

def main():
    """Main function to create box plots for specified model."""
    import sys
    import argparse
    
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Create normalized box plots for ML model throughput')
    parser.add_argument('model', nargs='?', default='ssd', help='Model name (ssd, resnet, etc.)')
    parser.add_argument('--exclude', '-e', nargs='+', help='Configurations to exclude from plots')
    parser.add_argument('--suffix', '-s', help='Suffix for output filename')
    
    args = parser.parse_args()
    
    model_name = args.model
    exclude_configs = args.exclude if args.exclude else []
    output_suffix = args.suffix if args.suffix else ''
    
    print(f"Finding {model_name.upper()} CSV files...")
    files_data = find_csv_files(model_name)
    
    # Print found files for verification
    print(f"\nFound {model_name.upper()} files:")
    for operation in files_data:
        if files_data[operation]:
            print(f"{operation}:")
            for config, path in files_data[operation].items():
                print(f"  {config}: {path}")
    
    print(f"\nLoading {model_name.upper()} throughput data...")
    throughput_data = load_throughput_data(files_data, model_name)
    
    if exclude_configs:
        print(f"\nExcluding configurations: {exclude_configs}")
    
    print(f"\nCreating {model_name.upper()} box plots...")
    create_box_plots(throughput_data, model_name, exclude_configs, output_suffix)
    
    print_statistics_summary(throughput_data, model_name)

if __name__ == "__main__":
    main()