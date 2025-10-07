#!/usr/bin/env python3
"""
Create normalized throughput bar graphs for different ML models and configurations.
Uses default configuration as baseline (normalized to 1.0).

Configurations:
- default: baseline (1.0)
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
import re

def find_csv_files():
    """Find all CSV files and organize by model and type."""
    base_dir = "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models"
    
    files_data = {
        'ssd': {'training': {}, 'inference': {}}
    }
    
    # Search pattern for CSV files - focus only on SSD directory
    patterns = [
        f"{base_dir}/ssd/exported-csv/*/*.csv"
    ]
    
    for pattern in patterns:
        csv_files = glob.glob(pattern)
        
        for file_path in csv_files:
            filename = os.path.basename(file_path)
            
            # Only process SSD files
            model = None
            if 'ssd' in filename.lower():
                model = 'ssd'
            
            if model is None:
                continue
            
            # Determine operation type
            operation = None
            if 'training' in filename.lower():
                operation = 'training'
            elif 'inference' in filename.lower():
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
            elif filename.endswith('-ap.csv') or filename.endswith('-autopilot.csv'):
                config = 'ap'
            elif filename.endswith('-default.csv'):
                config = 'default'
            
            files_data[model][operation][config] = file_path
    
    return files_data

def calculate_median_throughput(file_path, model, operation):
    """Calculate median throughput from CSV file."""
    try:
        df = pd.read_csv(file_path)
        
        # For SSD model, throughput column is always 'throughput'
        throughput_col = 'throughput'
        
        if throughput_col and throughput_col in df.columns:
            # Remove any NaN values and calculate median
            throughput_values = df[throughput_col].dropna()
            if len(throughput_values) > 0:
                return throughput_values.median()
        
        return None
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def create_normalized_data(files_data):
    """Create normalized throughput data using default as baseline."""
    normalized_data = {
        'training': {},
        'inference': {}
    }
    
    for operation in ['training', 'inference']:
        for model in ['ssd']:
            model_data = {}
            
            # Get default (baseline) throughput
            default_config = files_data[model][operation].get('default')
            if default_config:
                baseline_throughput = calculate_median_throughput(default_config, model, operation)
                
                if baseline_throughput is not None and baseline_throughput > 0:
                    # Calculate normalized throughput for all configurations
                    for config, file_path in files_data[model][operation].items():
                        throughput = calculate_median_throughput(file_path, model, operation)
                        if throughput is not None:
                            model_data[config] = throughput / baseline_throughput
                        else:
                            print(f"Warning: Could not calculate throughput for {model} {operation} {config}")
            
            if model_data:
                normalized_data[operation][model] = model_data
    
    return normalized_data

def create_bar_graphs(normalized_data):
    """Create normalized throughput bar graphs."""
    
    # Configuration labels and colors
    config_labels = {
        'default': 'Default',
        'ec': 'Elastic Container',
        'sw': 'Showvar',
        'at': 'Autothrottle',
        'ap': 'Autopilot'
    }
    
    config_colors = {
        'default': '#1f77b4',  # blue
        'ec': '#ff7f0e',       # orange
        'sw': '#2ca02c',       # green
        'at': '#d62728',       # red
        'ap': '#9467bd'        # purple
    }
    
    for operation in ['training', 'inference']:
        if not normalized_data[operation]:
            print(f"No data available for {operation}")
            continue
            
        # For SSD only, we'll create a single bar chart with configurations
        ssd_data = normalized_data[operation].get('ssd', {})
        if not ssd_data:
            continue
            
        # Prepare data for plotting
        configs = sorted(list(ssd_data.keys()))
        values = [ssd_data[config] for config in configs]
        labels = [config_labels.get(config, config) for config in configs]
        colors = [config_colors.get(config, '#888888') for config in configs]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create bars
        bars = ax.bar(labels, values, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
        
        # Add value labels on bars
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                   f'{height:.3f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        # Customize the plot
        ax.set_xlabel('Configuration', fontsize=12, fontweight='bold')
        ax.set_ylabel('Normalized Throughput (Default = 1.0)', fontsize=12, fontweight='bold')
        ax.set_title(f'SSD {operation.title()} Throughput - Normalized Performance Comparison', 
                    fontsize=14, fontweight='bold')
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        # Add horizontal line at y=1 (baseline)
        ax.axhline(y=1, color='black', linestyle='--', alpha=0.5, linewidth=1)
        
        # Set y-axis to start from 0
        ax.set_ylim(bottom=0)
        
        # Add grid for better readability
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        # Save the plot
        output_file = f'ssd_normalized_{operation}_throughput_comparison.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Saved {output_file}")
        
        plt.show()

def print_summary_table(normalized_data):
    """Print a summary table of the normalized throughput data."""
    
    config_labels = {
        'default': 'Default',
        'ec': 'Elastic Container',
        'sw': 'Showvar',
        'at': 'Autothrottle',
        'ap': 'Autopilot'
    }
    
    for operation in ['training', 'inference']:
        if not normalized_data[operation]:
            continue
            
        print(f"\n{operation.upper()} THROUGHPUT SUMMARY (Normalized to Default = 1.0)")
        print("=" * 70)
        
        # Get all models and configs
        models = list(normalized_data[operation].keys())
        all_configs = set()
        for model_data in normalized_data[operation].values():
            all_configs.update(model_data.keys())
        all_configs = sorted(list(all_configs))
        
        # Print header
        header = f"{'Model':<10}"
        for config in all_configs:
            header += f"{config_labels.get(config, config):<16}"
        print(header)
        print("-" * len(header))
        
        # Print data for each model
        for model in models:
            row = f"{model.upper():<10}"
            model_data = normalized_data[operation][model]
            for config in all_configs:
                value = model_data.get(config, 0)
                if value > 0:
                    row += f"{value:<16.3f}"
                else:
                    row += f"{'N/A':<16}"
            print(row)

def main():
    """Main function to create normalized throughput graphs."""
    print("Finding CSV files...")
    files_data = find_csv_files()
    
    # Print found files for verification
    print("\nFound files:")
    for model in files_data:
        for operation in files_data[model]:
            if files_data[model][operation]:
                print(f"{model} {operation}:")
                for config, path in files_data[model][operation].items():
                    print(f"  {config}: {path}")
    
    print("\nCalculating normalized throughput data...")
    normalized_data = create_normalized_data(files_data)
    
    print("\nCreating bar graphs...")
    create_bar_graphs(normalized_data)
    
    print_summary_table(normalized_data)

if __name__ == "__main__":
    main()