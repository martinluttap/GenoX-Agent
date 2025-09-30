#!/usr/bin/env python3
"""
Create focused normalized throughput graphs from exported CSV data.
Analyzes different configurations: default, showvar(sw), autopilot(ap), autothrottle(at), elasticcontainer(ec)
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
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
                    training_data[config_key] = df
                    print(f"Loaded training data for {config_mapping[config_key]}: {len(df)} measurements")
                
                if os.path.exists(inference_file):
                    df = pd.read_csv(inference_file)
                    # Convert to millions of examples per second  
                    df['throughput_M_per_sec'] = df['inference_throughput_examples_per_sec'] / 1e6
                    inference_data[config_key] = df
                    print(f"Loaded inference data for {config_mapping[config_key]}: {len(df)} measurements")
    
    return training_data, inference_data, config_mapping

def analyze_configuration(data, config_name):
    """Analyze throughput data for a configuration."""
    throughput = data['throughput_M_per_sec'].values
    
    analysis = {
        'config': config_name,
        'full_avg': np.mean(throughput),
        'full_std': np.std(throughput),
        'min_val': np.min(throughput),
        'max_val': np.max(throughput),
        'count': len(throughput),
        'cv': np.std(throughput) / np.mean(throughput) if np.mean(throughput) > 0 else 0
    }
    
    # Peak performance (best 5-measurement window)
    if len(throughput) >= 5:
        window_avgs = []
        for i in range(len(throughput) - 4):
            window_avg = np.mean(throughput[i:i+5])
            window_avgs.append(window_avg)
        analysis['peak_avg'] = max(window_avgs) if window_avgs else analysis['full_avg']
    else:
        analysis['peak_avg'] = analysis['full_avg']
    
    # Last 5 measurements
    if len(throughput) >= 5:
        analysis['last5_avg'] = np.mean(throughput[-5:])
    else:
        analysis['last5_avg'] = analysis['full_avg']
    
    # Trend analysis (improvement per measurement)
    if len(throughput) > 1:
        x = np.arange(len(throughput))
        slope, _ = np.polyfit(x, throughput, 1)
        analysis['trend_slope'] = slope
        analysis['trend_percent_per_measurement'] = (slope / analysis['full_avg']) * 100
    else:
        analysis['trend_slope'] = 0
        analysis['trend_percent_per_measurement'] = 0
    
    return analysis

def create_focused_graphs():
    """Create focused comparison graphs."""
    
    print("Loading CSV data from exported-csv directory...")
    training_data, inference_data, config_mapping = load_csv_data()
    
    if not training_data or not inference_data:
        print("Error: No data found in exported-csv directory!")
        return
    
    # Analyze all configurations
    training_analysis = {}
    inference_analysis = {}
    
    for config_key in config_mapping.keys():
        if config_key in training_data:
            training_analysis[config_key] = analyze_configuration(training_data[config_key], config_mapping[config_key])
        if config_key in inference_data:
            inference_analysis[config_key] = analyze_configuration(inference_data[config_key], config_mapping[config_key])
    
    # Get default baseline for normalization
    default_training_avg = training_analysis['default']['full_avg'] if 'default' in training_analysis else 1.0
    default_inference_avg = inference_analysis['default']['full_avg'] if 'default' in inference_analysis else 1.0
    
    print(f"\nBaseline Performance:")
    print(f"Training (Default): {default_training_avg:.2f} M examples/sec")
    print(f"Inference (Default): {default_inference_avg:.2f} M examples/sec")
    
    # Create visualization
    plt.style.use('default')
    sns.set_palette("husl")
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(18, 14))
    fig.suptitle('XGBoost Performance Analysis: All Configurations Comparison', 
                 fontsize=18, fontweight='bold', y=0.95)
    
    # Prepare data for plotting
    configs = []
    training_full_norm = []
    training_peak_norm = []
    training_last5_norm = []
    inference_full_norm = []
    inference_peak_norm = []
    inference_last5_norm = []
    
    for config_key in ['default', 'sw', 'ec', 'autopilot', 'at']:
        if config_key in training_analysis and config_key in inference_analysis:
            configs.append(config_mapping[config_key])
            
            # Training normalized values
            training_full_norm.append(training_analysis[config_key]['full_avg'] / default_training_avg)
            training_peak_norm.append(training_analysis[config_key]['peak_avg'] / default_training_avg)
            training_last5_norm.append(training_analysis[config_key]['last5_avg'] / default_training_avg)
            
            # Inference normalized values
            inference_full_norm.append(inference_analysis[config_key]['full_avg'] / default_inference_avg)
            inference_peak_norm.append(inference_analysis[config_key]['peak_avg'] / default_inference_avg)
            inference_last5_norm.append(inference_analysis[config_key]['last5_avg'] / default_inference_avg)
    
    x = np.arange(len(configs))
    width = 0.25
    
    # === TRAINING THROUGHPUT GRAPH ===
    bars1 = ax1.bar(x - width, training_full_norm, width, label='Full Average', 
                    alpha=0.8, color='skyblue', edgecolor='navy', linewidth=1.5)
    bars2 = ax1.bar(x, training_peak_norm, width, label='Peak Performance', 
                    alpha=0.8, color='lightgreen', edgecolor='darkgreen', linewidth=1.5)
    bars3 = ax1.bar(x + width, training_last5_norm, width, label='Last 5 Measurements', 
                    alpha=0.8, color='lightcoral', edgecolor='darkred', linewidth=1.5)
    
    # Add value labels on bars
    def add_value_labels(ax, bars, values):
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                   f'{value:.3f}', ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    add_value_labels(ax1, bars1, training_full_norm)
    add_value_labels(ax1, bars2, training_peak_norm)
    add_value_labels(ax1, bars3, training_last5_norm)
    
    ax1.axhline(y=1.0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Baseline (1.0)')
    ax1.set_title('Training Throughput (Normalized against Default)', fontweight='bold', fontsize=14)
    ax1.set_ylabel('Normalized Throughput', fontweight='bold')
    ax1.set_xlabel('Configuration', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(configs, fontsize=10, rotation=45, ha='right')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.set_ylim(0, max(max(training_full_norm), max(training_peak_norm), max(training_last5_norm)) * 1.15)
    
    # === TRAINING IMPROVEMENT PERCENTAGES ===
    training_full_improvement = [(x - 1) * 100 for x in training_full_norm]
    training_peak_improvement = [(x - 1) * 100 for x in training_peak_norm]
    training_last5_improvement = [(x - 1) * 100 for x in training_last5_norm]
    
    bars1 = ax2.bar(x - width, training_full_improvement, width, label='Full Average', 
                    alpha=0.8, color='skyblue', edgecolor='navy', linewidth=1.5)
    bars2 = ax2.bar(x, training_peak_improvement, width, label='Peak Performance', 
                    alpha=0.8, color='lightgreen', edgecolor='darkgreen', linewidth=1.5)
    bars3 = ax2.bar(x + width, training_last5_improvement, width, label='Last 5 Measurements', 
                    alpha=0.8, color='lightcoral', edgecolor='darkred', linewidth=1.5)
    
    # Add percentage labels
    def add_percent_labels(ax, bars, values):
        for bar, value in zip(bars, values):
            height = bar.get_height()
            y_pos = height + (2 if height >= 0 else -5)
            ax.text(bar.get_x() + bar.get_width()/2., y_pos,
                   f'{value:+.1f}%', ha='center', va='bottom' if height >= 0 else 'top',
                   fontweight='bold', fontsize=9)
    
    add_percent_labels(ax2, bars1, training_full_improvement)
    add_percent_labels(ax2, bars2, training_peak_improvement)
    add_percent_labels(ax2, bars3, training_last5_improvement)
    
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=2, alpha=0.8)
    ax2.set_title('Training Performance vs Baseline (%)', fontweight='bold', fontsize=14)
    ax2.set_ylabel('Performance Change (%)', fontweight='bold')
    ax2.set_xlabel('Configuration', fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(configs, fontsize=10, rotation=45, ha='right')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # === INFERENCE THROUGHPUT GRAPH ===
    bars1 = ax3.bar(x - width, inference_full_norm, width, label='Full Average', 
                    alpha=0.8, color='skyblue', edgecolor='navy', linewidth=1.5)
    bars2 = ax3.bar(x, inference_peak_norm, width, label='Peak Performance', 
                    alpha=0.8, color='lightgreen', edgecolor='darkgreen', linewidth=1.5)
    bars3 = ax3.bar(x + width, inference_last5_norm, width, label='Last 5 Measurements', 
                    alpha=0.8, color='lightcoral', edgecolor='darkred', linewidth=1.5)
    
    add_value_labels(ax3, bars1, inference_full_norm)
    add_value_labels(ax3, bars2, inference_peak_norm)
    add_value_labels(ax3, bars3, inference_last5_norm)
    
    ax3.axhline(y=1.0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Baseline (1.0)')
    ax3.set_title('Inference Throughput (Normalized against Default)', fontweight='bold', fontsize=14)
    ax3.set_ylabel('Normalized Throughput', fontweight='bold')
    ax3.set_xlabel('Configuration', fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(configs, fontsize=10, rotation=45, ha='right')
    ax3.legend(loc='upper right')
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.set_ylim(0, max(max(inference_full_norm), max(inference_peak_norm), max(inference_last5_norm)) * 1.15)
    
    # === INFERENCE IMPROVEMENT PERCENTAGES ===
    inference_full_improvement = [(x - 1) * 100 for x in inference_full_norm]
    inference_peak_improvement = [(x - 1) * 100 for x in inference_peak_norm]
    inference_last5_improvement = [(x - 1) * 100 for x in inference_last5_norm]
    
    bars1 = ax4.bar(x - width, inference_full_improvement, width, label='Full Average', 
                    alpha=0.8, color='skyblue', edgecolor='navy', linewidth=1.5)
    bars2 = ax4.bar(x, inference_peak_improvement, width, label='Peak Performance', 
                    alpha=0.8, color='lightgreen', edgecolor='darkgreen', linewidth=1.5)
    bars3 = ax4.bar(x + width, inference_last5_improvement, width, label='Last 5 Measurements', 
                    alpha=0.8, color='lightcoral', edgecolor='darkred', linewidth=1.5)
    
    add_percent_labels(ax4, bars1, inference_full_improvement)
    add_percent_labels(ax4, bars2, inference_peak_improvement)
    add_percent_labels(ax4, bars3, inference_last5_improvement)
    
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=2, alpha=0.8)
    ax4.set_title('Inference Performance vs Baseline (%)', fontweight='bold', fontsize=14)
    ax4.set_ylabel('Performance Change (%)', fontweight='bold')
    ax4.set_xlabel('Configuration', fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels(configs, fontsize=10, rotation=45, ha='right')
    ax4.legend(loc='upper right')
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    # Save the plot
    output_path = '/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/focused_performance_comparison.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nFocused performance comparison graph saved: {output_path}")
    
    plt.show()
    
    # Print summary table
    print_summary_table(training_analysis, inference_analysis, config_mapping, 
                        default_training_avg, default_inference_avg)

def print_summary_table(training_analysis, inference_analysis, config_mapping, 
                       default_training_avg, default_inference_avg):
    """Print detailed summary table."""
    
    print("\n" + "="*120)
    print("DETAILED PERFORMANCE ANALYSIS SUMMARY")
    print("="*120)
    print(f"Baseline: Default Training = {default_training_avg:.2f} M examples/sec, Default Inference = {default_inference_avg:.2f} M examples/sec")
    print("-"*120)
    
    # Headers
    print(f"{'Configuration':<20} {'Training Performance':<50} {'Inference Performance':<50}")
    print(f"{'':20} {'Full':<8} {'Peak':<8} {'Last5':<8} {'Peak%':<9} {'Trend':<9} {'Full':<8} {'Peak':<8} {'Last5':<8} {'Peak%':<9} {'Trend':<9}")
    print("-"*120)
    
    # Data rows
    for config_key in ['default', 'sw', 'ec', 'autopilot', 'at']:
        if config_key in training_analysis and config_key in inference_analysis:
            config_name = config_mapping[config_key]
            
            # Training data
            t_full_norm = training_analysis[config_key]['full_avg'] / default_training_avg
            t_peak_norm = training_analysis[config_key]['peak_avg'] / default_training_avg
            t_last5_norm = training_analysis[config_key]['last5_avg'] / default_training_avg
            t_peak_pct = (t_peak_norm - 1) * 100
            t_trend = training_analysis[config_key]['trend_percent_per_measurement']
            
            # Inference data
            i_full_norm = inference_analysis[config_key]['full_avg'] / default_inference_avg
            i_peak_norm = inference_analysis[config_key]['peak_avg'] / default_inference_avg
            i_last5_norm = inference_analysis[config_key]['last5_avg'] / default_inference_avg
            i_peak_pct = (i_peak_norm - 1) * 100
            i_trend = inference_analysis[config_key]['trend_percent_per_measurement']
            
            print(f"{config_name:<20} {t_full_norm:<8.3f} {t_peak_norm:<8.3f} {t_last5_norm:<8.3f} {t_peak_pct:<+8.1f}% {t_trend:<+8.2f}% {i_full_norm:<8.3f} {i_peak_norm:<8.3f} {i_last5_norm:<8.3f} {i_peak_pct:<+8.1f}% {i_trend:<+8.2f}%")
    
    print("-"*120)
    print("Legend: Full=Full Average, Peak=Best 5-measurement window, Last5=Final 5 measurements")
    print("        Peak%=Peak improvement vs baseline, Trend=Performance change % per measurement")
    print("="*120)

if __name__ == "__main__":
    create_focused_graphs()