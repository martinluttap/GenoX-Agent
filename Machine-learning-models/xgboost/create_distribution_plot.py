#!/usr/bin/env python3
"""
Create normalized throughput distribution plots (box plots only).
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def create_normalized_distribution_plots():
    """Create box plots showing normalized throughput distributions."""
    
    # File paths
    training_paths = {
        'Default': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-hllwm/training_throughput-default.csv",
        'Showvar': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-fnh9z/training_throughput-sw.csv",
        'Elastic Container': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-nb2f5/training_throughput-ec.csv",
        'Autopilot': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-nr2zj/training_throughput-autopilot.csv",
        'Autothrottle': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-wqqn2/training_throughput-at.csv"
    }
    
    inference_paths = {
        'Default': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-hllwm/inference_throughput-default.csv",
        'Showvar': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-fnh9z/inference_throughput-sw.csv",
        'Elastic Container': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-nb2f5/inference_throughput-ec.csv",
        'Autopilot': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-nr2zj/inference_throughput-autopilot.csv",
        'Autothrottle': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-wqqn2/inference_throughput-at.csv"
    }
    
    def load_and_normalize_data(paths, throughput_column):
        """Load data and normalize against default baseline."""
        data = {}
        
        # Load default first to get baseline
        default_df = pd.read_csv(paths['Default'])
        baseline_avg = default_df[throughput_column].mean()
        
        normalized_data = {}
        labels = []
        box_data = []
        
        for config_name, path in paths.items():
            if os.path.exists(path):
                df = pd.read_csv(path)
                throughput = df[throughput_column]
                normalized = throughput / baseline_avg
                
                normalized_data[config_name] = normalized
                labels.append(config_name)
                box_data.append(normalized.values)
                
                print(f"Loaded {config_name}: {len(df)} measurements, avg normalized = {normalized.mean():.3f}")
        
        return box_data, labels, baseline_avg, normalized_data
    
    # Load training data
    print("Loading Training Data:")
    training_box_data, training_labels, training_baseline, training_norm_data = load_and_normalize_data(
        training_paths, 'training_throughput_examples_per_sec'
    )
    
    print("\nLoading Inference Data:")
    inference_box_data, inference_labels, inference_baseline, inference_norm_data = load_and_normalize_data(
        inference_paths, 'inference_throughput_examples_per_sec'
    )
    
    # Create the plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    fig.suptitle('Normalized Throughput Distribution\n(Baseline: Default Configuration = 1.0)', 
                 fontsize=16, fontweight='bold')
    
    # Training box plot
    bp1 = ax1.boxplot(training_box_data, labels=training_labels, patch_artist=True, 
                      showmeans=True, meanline=True)
    
    # Color the boxes
    colors = ['lightblue', 'lightgreen', 'lightcoral', 'lightyellow', 'lightpink']
    for patch, color in zip(bp1['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # Style the plot
    ax1.axhline(y=1.0, color='red', linestyle='--', linewidth=2, alpha=0.8, label='Baseline (1.0)')
    ax1.set_title('Training Throughput Distribution', fontweight='bold', fontsize=14)
    ax1.set_ylabel('Normalized Throughput\n(Relative to Default Baseline)', fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.legend()
    
    # Rotate x-axis labels for better readability
    ax1.tick_params(axis='x', rotation=45)
    
    # Add statistics annotations for training
    for i, (config, data) in enumerate(training_norm_data.items()):
        avg = data.mean()
        std = data.std()
        ax1.text(i+1, avg + std + 0.05, f'μ={avg:.2f}\nσ={std:.2f}', 
                ha='center', va='bottom', fontsize=9, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    
    # Inference box plot
    bp2 = ax2.boxplot(inference_box_data, labels=inference_labels, patch_artist=True,
                      showmeans=True, meanline=True)
    
    # Color the boxes
    for patch, color in zip(bp2['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # Style the plot
    ax2.axhline(y=1.0, color='red', linestyle='--', linewidth=2, alpha=0.8, label='Baseline (1.0)')
    ax2.set_title('Inference Throughput Distribution', fontweight='bold', fontsize=14)
    ax2.set_ylabel('Normalized Throughput\n(Relative to Default Baseline)', fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.legend()
    
    # Rotate x-axis labels for better readability
    ax2.tick_params(axis='x', rotation=45)
    
    # Add statistics annotations for inference
    for i, (config, data) in enumerate(inference_norm_data.items()):
        avg = data.mean()
        std = data.std()
        ax2.text(i+1, avg + std + 0.05, f'μ={avg:.2f}\nσ={std:.2f}', 
                ha='center', va='bottom', fontsize=9, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    
    plt.tight_layout()
    
    # Save the plot
    output_path = '/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/normalized_throughput_distribution.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nNormalized throughput distribution plot saved: {output_path}")
    
    plt.show()
    
    # Print summary statistics
    print("\n" + "="*80)
    print("NORMALIZED THROUGHPUT DISTRIBUTION SUMMARY")
    print("="*80)
    print(f"Training Baseline: {training_baseline/1e6:.1f} M examples/sec")
    print(f"Inference Baseline: {inference_baseline/1e6:.1f} M examples/sec")
    print("-"*80)
    
    print("\nTRAINING STATISTICS:")
    for config, data in training_norm_data.items():
        print(f"{config:15}: Mean={data.mean():.3f}, Std={data.std():.3f}, Min={data.min():.3f}, Max={data.max():.3f}")
    
    print("\nINFERENCE STATISTICS:")
    for config, data in inference_norm_data.items():
        print(f"{config:15}: Mean={data.mean():.3f}, Std={data.std():.3f}, Min={data.min():.3f}, Max={data.max():.3f}")
    
    print("="*80)

if __name__ == "__main__":
    create_normalized_distribution_plots()