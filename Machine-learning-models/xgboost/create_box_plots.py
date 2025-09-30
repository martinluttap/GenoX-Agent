#!/usr/bin/env python3
"""
Create box plots for XGBoost throughput analysis across different configurations.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob

def load_csv_data():
    """Load all CSV data from exported-csv directory."""
    
    base_path = "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv"
    
    # Configuration mapping
    config_mapping = {
        'default': 'Default',
        'sw': 'ShowVar (SW)', 
        'ec': 'Elastic Container (EC)',
        'autopilot': 'Autopilot (AP)',
        'at': 'Autothrottle (AT)'
    }
    
    training_data = {}
    inference_data = {}
    
    # Find all CSV files
    for pod_dir in glob.glob(os.path.join(base_path, "*")):
        if os.path.isdir(pod_dir):
            # Look for training and inference files
            for config_key in config_mapping.keys():
                training_file = os.path.join(pod_dir, f"training_throughput-{config_key}.csv")
                inference_file = os.path.join(pod_dir, f"inference_throughput-{config_key}.csv")
                
                if os.path.exists(training_file):
                    df = pd.read_csv(training_file)
                    # Convert to millions of examples per second
                    df['throughput_M_per_sec'] = df['training_throughput_examples_per_sec'] / 1e6
                    training_data[config_key] = df['throughput_M_per_sec'].values
                    print(f"Loaded training data for {config_mapping[config_key]}: {len(df)} measurements")
                
                if os.path.exists(inference_file):
                    df = pd.read_csv(inference_file)
                    # Convert to millions of examples per second  
                    df['throughput_M_per_sec'] = df['inference_throughput_examples_per_sec'] / 1e6
                    inference_data[config_key] = df['throughput_M_per_sec'].values
                    print(f"Loaded inference data for {config_mapping[config_key]}: {len(df)} measurements")
    
    return training_data, inference_data, config_mapping

def create_box_plots():
    """Create box plots for all configurations."""
    
    print("Loading CSV data from exported-csv directory...")
    training_data, inference_data, config_mapping = load_csv_data()
    
    if not training_data or not inference_data:
        print("Error: No data found in exported-csv directory!")
        return
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # === TRAINING THROUGHPUT BOX PLOTS ===
    
    # Prepare data for training box plot
    training_plot_data = []
    training_labels = []
    
    config_order = ['default', 'sw', 'ec', 'autopilot', 'at']
    
    for config_key in config_order:
        if config_key in training_data:
            training_plot_data.append(training_data[config_key])
            training_labels.append(config_mapping[config_key])
    
    # Create training box plot
    box_plot1 = ax1.boxplot(training_plot_data, labels=training_labels, patch_artist=True)
    
    # Customize training box plot
    colors = ['lightblue', 'lightgreen', 'lightcoral', 'lightyellow', 'lightpink']
    for patch, color in zip(box_plot1['boxes'], colors[:len(box_plot1['boxes'])]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax1.set_title('Training Throughput Distribution', fontweight='bold', fontsize=14)
    ax1.set_ylabel('Throughput (Million Examples/sec)', fontweight='bold')
    ax1.set_xlabel('Schedulers', fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.tick_params(axis='x', rotation=45)
    
    # Add mean values as points
    for i, data in enumerate(training_plot_data):
        mean_val = np.mean(data)
        ax1.plot(i+1, mean_val, 'ro', markersize=8, label='Mean' if i == 0 else "")
        ax1.text(i+1, mean_val + 1, f'{mean_val:.1f}', ha='center', va='bottom', 
                fontweight='bold', fontsize=10)
    
    if len(training_plot_data) > 0:
        ax1.legend()
    
    # === INFERENCE THROUGHPUT BOX PLOTS ===
    
    # Prepare data for inference box plot
    inference_plot_data = []
    inference_labels = []
    
    for config_key in config_order:
        if config_key in inference_data:
            inference_plot_data.append(inference_data[config_key])
            inference_labels.append(config_mapping[config_key])
    
    # Create inference box plot
    box_plot2 = ax2.boxplot(inference_plot_data, labels=inference_labels, patch_artist=True)
    
    # Customize inference box plot
    for patch, color in zip(box_plot2['boxes'], colors[:len(box_plot2['boxes'])]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax2.set_title('Inference Throughput Distribution', fontweight='bold', fontsize=14)
    ax2.set_ylabel('Throughput (Million Examples/sec)', fontweight='bold')
    ax2.set_xlabel('Configuration', fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.tick_params(axis='x', rotation=45)
    
    # Add mean values as points
    for i, data in enumerate(inference_plot_data):
        mean_val = np.mean(data)
        ax2.plot(i+1, mean_val, 'ro', markersize=8, label='Mean' if i == 0 else "")
        ax2.text(i+1, mean_val + 0.05, f'{mean_val:.2f}', ha='center', va='bottom', 
                fontweight='bold', fontsize=10)
    
    if len(inference_plot_data) > 0:
        ax2.legend()
    
    plt.tight_layout()
    
    # Add title at the bottom
    fig.suptitle('XGBoost Throughput Distribution: Box Plots by Configuration', 
                 fontsize=16, fontweight='bold', y=0.02)
    
    # Save the plot
    output_path = '/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/throughput_box_plots.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nBox plots saved: {output_path}")
    
    plt.show()
    
    # Print summary statistics
    print_box_plot_stats(training_data, inference_data, config_mapping)

def print_box_plot_stats(training_data, inference_data, config_mapping):
    """Print summary statistics for the box plots."""
    
    print("\n" + "="*80)
    print("BOX PLOT STATISTICS SUMMARY")
    print("="*80)
    
    config_order = ['default', 'sw', 'ec', 'autopilot', 'at']
    
    print("\nTRAINING THROUGHPUT (Million Examples/sec):")
    print("-"*60)
    print(f"{'Config':<15} {'Count':<6} {'Mean':<8} {'Median':<8} {'Min':<8} {'Max':<8} {'Std':<8}")
    print("-"*60)
    
    for config_key in config_order:
        if config_key in training_data:
            data = training_data[config_key]
            config_name = config_mapping[config_key]
            
            print(f"{config_name:<15} {len(data):<6} {np.mean(data):<8.2f} {np.median(data):<8.2f} "
                  f"{np.min(data):<8.2f} {np.max(data):<8.2f} {np.std(data):<8.2f}")
    
    print("\nINFERENCE THROUGHPUT (Million Examples/sec):")
    print("-"*60)
    print(f"{'Config':<15} {'Count':<6} {'Mean':<8} {'Median':<8} {'Min':<8} {'Max':<8} {'Std':<8}")
    print("-"*60)
    
    for config_key in config_order:
        if config_key in inference_data:
            data = inference_data[config_key]
            config_name = config_mapping[config_key]
            
            print(f"{config_name:<15} {len(data):<6} {np.mean(data):<8.2f} {np.median(data):<8.2f} "
                  f"{np.min(data):<8.2f} {np.max(data):<8.2f} {np.std(data):<8.2f}")
    
    print("="*80)

if __name__ == "__main__":
    create_box_plots()