#!/usr/bin/env python3
"""
Normalize throughput analysis for XGBoost benchmark results.
This script processes training and inference throughput data across different configurations
and normalizes them against the baseline (default) configuration.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path
import seaborn as sns
from datetime import datetime

# Set style for better plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

def load_throughput_data(base_path, metric_type='inference'):
    """
    Load throughput data from CSV files for all configurations.
    
    Args:
        base_path (str): Base path to the exported-csv directory
        metric_type (str): 'inference' or 'training'
    
    Returns:
        dict: Dictionary containing throughput data for each configuration
    """
    configurations = {
        'default': 'xgboost-benchmark-5f8895c8f8-hllwm',
        'ec': 'xgboost-benchmark-5f8895c8f8-nb2f5',
        'sw': 'xgboost-benchmark-5f8895c8f8-fnh9z',
        'autopilot': 'xgboost-benchmark-5f8895c8f8-nr2zj',
        'autothrottle': 'xgboost-benchmark-5f8895c8f8-wqqn2'
    }
    
    data = {}
    
    for config_name, folder_name in configurations.items():
        csv_file = f"{metric_type}_throughput-{config_name}.csv" if config_name != 'autothrottle' else f"{metric_type}_throughput-at.csv"
        file_path = os.path.join(base_path, folder_name, csv_file)
        
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            data[config_name] = df
            print(f"Loaded {config_name} {metric_type} data: {len(df)} records")
        else:
            print(f"Warning: File not found: {file_path}")
    
    return data

def calculate_normalized_throughput(data, baseline_config='default'):
    """
    Calculate normalized throughput using the baseline configuration.
    
    Args:
        data (dict): Dictionary containing throughput data for each configuration
        baseline_config (str): Name of the baseline configuration
    
    Returns:
        dict: Dictionary containing normalized throughput data
    """
    if baseline_config not in data:
        raise ValueError(f"Baseline configuration '{baseline_config}' not found in data")
    
    baseline_data = data[baseline_config]
    throughput_col = 'inference_throughput_examples_per_sec' if 'inference_throughput_examples_per_sec' in baseline_data.columns else 'training_throughput_examples_per_sec'
    
    # Calculate baseline average throughput
    baseline_avg = baseline_data[throughput_col].mean()
    print(f"Baseline ({baseline_config}) average throughput: {baseline_avg:,.2f} examples/sec")
    
    normalized_data = {}
    
    for config_name, config_data in data.items():
        config_avg = config_data[throughput_col].mean()
        normalized_avg = config_avg / baseline_avg
        
        # Calculate normalized throughput for each measurement
        normalized_throughput = config_data[throughput_col] / baseline_avg
        
        normalized_data[config_name] = {
            'raw_throughput': config_data[throughput_col],
            'normalized_throughput': normalized_throughput,
            'avg_throughput': config_avg,
            'normalized_avg': normalized_avg,
            'timestamp': config_data['timestamp']
        }
        
        print(f"{config_name}: avg={config_avg:,.2f} examples/sec, normalized={normalized_avg:.3f}")
    
    return normalized_data, baseline_avg

def create_normalized_throughput_plots(normalized_data, metric_type, baseline_avg, output_dir):
    """
    Create visualization plots for normalized throughput data.
    
    Args:
        normalized_data (dict): Normalized throughput data
        metric_type (str): 'inference' or 'training'
        baseline_avg (float): Baseline average throughput
        output_dir (str): Output directory for plots
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Configuration display names and colors
    config_labels = {
        'default': 'Default (Baseline)',
        'ec': 'Elastic Container',
        'sw': 'Software',
        'autopilot': 'Autopilot',
        'autothrottle': 'Autothrottle'
    }
    
    # Create figure with subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(f'{metric_type.capitalize()} Throughput Analysis', fontsize=16, fontweight='bold')
    
    # 1. Time series plot of normalized throughput
    ax1.set_title('Normalized Throughput Over Time')
    for config_name, config_data in normalized_data.items():
        if config_name in config_labels:
            ax1.plot(config_data['timestamp'], config_data['normalized_throughput'], 
                    label=config_labels[config_name], marker='o', markersize=3, alpha=0.7)
    
    ax1.axhline(y=1.0, color='black', linestyle='--', alpha=0.5, label='Baseline')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Normalized Throughput (vs Default)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # 2. Bar chart of average normalized throughput
    configs = [config for config in normalized_data.keys() if config in config_labels]
    normalized_avgs = [normalized_data[config]['normalized_avg'] for config in configs]
    labels = [config_labels[config] for config in configs]
    
    colors = plt.cm.Set3(np.linspace(0, 1, len(configs)))
    bars = ax2.bar(labels, normalized_avgs, color=colors, alpha=0.8, edgecolor='black')
    
    # Add value labels on bars
    for bar, value in zip(bars, normalized_avgs):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{value:.3f}', ha='center', va='bottom', fontweight='bold')
    
    ax2.axhline(y=1.0, color='red', linestyle='--', alpha=0.7, label='Baseline (1.0)')
    ax2.set_title('Average Normalized Throughput')
    ax2.set_ylabel('Normalized Throughput (vs Default)')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')
    plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')
    
    # 3. Box plot of normalized throughput distribution
    box_data = []
    box_labels = []
    for config_name in configs:
        box_data.append(normalized_data[config_name]['normalized_throughput'])
        box_labels.append(config_labels[config_name])
    
    bp = ax3.boxplot(box_data, labels=box_labels, patch_artist=True, showmeans=True)
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax3.axhline(y=1.0, color='red', linestyle='--', alpha=0.7, label='Baseline (1.0)')
    ax3.set_title('Normalized Throughput Distribution')
    ax3.set_ylabel('Normalized Throughput (vs Default)')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')
    plt.setp(ax3.get_xticklabels(), rotation=45, ha='right')
    
    # 4. Performance improvement percentage
    improvements = [(normalized_data[config]['normalized_avg'] - 1) * 100 for config in configs]
    
    # Color bars based on improvement (green for positive, red for negative)
    bar_colors = ['green' if imp > 0 else 'red' if imp < 0 else 'gray' for imp in improvements]
    bars = ax4.bar(labels, improvements, color=bar_colors, alpha=0.7, edgecolor='black')
    
    # Add value labels on bars
    for bar, value in zip(bars, improvements):
        height = bar.get_height()
        y_pos = height + (1 if height > 0 else -3)
        ax4.text(bar.get_x() + bar.get_width()/2., y_pos,
                f'{value:+.1f}%', ha='center', va='bottom' if height > 0 else 'top', 
                fontweight='bold')
    
    ax4.axhline(y=0, color='black', linestyle='-', alpha=0.8)
    ax4.set_title('Performance Improvement vs Baseline')
    ax4.set_ylabel('Improvement (%)')
    ax4.grid(True, alpha=0.3, axis='y')
    plt.setp(ax4.get_xticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    
    # Save the plot
    plot_filename = f'normalized_{metric_type}_throughput_analysis.png'
    plot_path = os.path.join(output_dir, plot_filename)
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"Saved plot: {plot_path}")
    
    plt.show()
    
    return plot_path

def create_summary_table(inference_data, training_data, output_dir):
    """
    Create a summary table with normalized throughput results.
    """
    config_labels = {
        'default': 'Default (Baseline)',
        'ec': 'Elastic Container',
        'sw': 'Software',
        'autopilot': 'Autopilot',
        'autothrottle': 'Autothrottle'
    }
    
    # Prepare summary data
    summary_data = []
    
    for config in ['default', 'ec', 'sw', 'autopilot', 'autothrottle']:
        if config in inference_data and config in training_data:
            inference_norm = inference_data[config]['normalized_avg']
            training_norm = training_data[config]['normalized_avg']
            inference_improvement = (inference_norm - 1) * 100
            training_improvement = (training_norm - 1) * 100
            
            summary_data.append({
                'Configuration': config_labels[config],
                'Inference Normalized': f"{inference_norm:.3f}",
                'Inference Improvement (%)': f"{inference_improvement:+.1f}%",
                'Training Normalized': f"{training_norm:.3f}",
                'Training Improvement (%)': f"{training_improvement:+.1f}%"
            })
    
    # Create DataFrame and save as CSV
    summary_df = pd.DataFrame(summary_data)
    summary_path = os.path.join(output_dir, 'normalized_throughput_summary.csv')
    summary_df.to_csv(summary_path, index=False)
    
    print("\nSummary Table:")
    print(summary_df.to_string(index=False))
    print(f"\nSaved summary table: {summary_path}")
    
    return summary_df

def main():
    # Base configuration
    base_path = "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv"
    output_dir = "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/normalized_analysis"
    
    print("XGBoost Throughput Normalization Analysis")
    print("=" * 50)
    
    # Load inference data
    print("\nLoading inference throughput data...")
    inference_data = load_throughput_data(base_path, 'inference')
    
    # Load training data
    print("\nLoading training throughput data...")
    training_data = load_throughput_data(base_path, 'training')
    
    # Calculate normalized throughput for inference
    print("\nCalculating normalized inference throughput...")
    normalized_inference, inference_baseline = calculate_normalized_throughput(inference_data)
    
    # Calculate normalized throughput for training
    print("\nCalculating normalized training throughput...")
    normalized_training, training_baseline = calculate_normalized_throughput(training_data)
    
    # Create plots
    print("\nCreating visualization plots...")
    
    # Inference plots
    inference_plot = create_normalized_throughput_plots(
        normalized_inference, 'inference', inference_baseline, output_dir
    )
    
    # Training plots  
    training_plot = create_normalized_throughput_plots(
        normalized_training, 'training', training_baseline, output_dir
    )
    
    # Create summary table
    print("\nCreating summary table...")
    summary_df = create_summary_table(normalized_inference, normalized_training, output_dir)
    
    print(f"\nAnalysis complete! Results saved in: {output_dir}")

if __name__ == "__main__":
    main()