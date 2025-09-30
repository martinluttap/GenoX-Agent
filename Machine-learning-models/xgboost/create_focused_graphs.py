#!/usr/bin/env python3
"""
Create focused normalized throughput graphs for training and inference.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

def create_focused_normalized_graphs():
    """Create clean, focused normalized throughput graphs."""
    
    # Load the comprehensive analysis data
    training_file = "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/comprehensive_training_analysis.csv"
    inference_file = "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/comprehensive_inference_analysis.csv"
    
    training_df = pd.read_csv(training_file)
    inference_df = pd.read_csv(inference_file)
    
    # Configuration mapping for better labels
    config_labels = {
        'default': 'Default\n(Baseline)',
        'ec': 'Elastic\nContainer (EC)',
        'sw': 'ShowVar\n(SW)',
        'autopilot': 'Autopilot\n(AP)',
        'autothrottle': 'Autothrottle\n(AT)'
    }
    
    # Set up the plot style
    plt.style.use('default')
    sns.set_palette("husl")
    
    # Create figure with subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('XGBoost Throughput Analysis: Normalized Against Default Baseline', 
                 fontsize=16, fontweight='bold', y=0.95)
    
    # === TRAINING THROUGHPUT ANALYSIS ===
    
    # 1. Training - Bar chart comparison (Full vs Peak vs Last 5)
    configs = [config_labels.get(config, config) for config in training_df['Configuration']]
    
    full_norm = training_df['Full Normalized'].values
    peak_norm = training_df['Peak Normalized'].values  
    last5_norm = training_df['Last 5 Normalized'].values
    
    x = np.arange(len(configs))
    width = 0.25
    
    bars1 = ax1.bar(x - width, full_norm, width, label='Full Average', alpha=0.8, color='skyblue', edgecolor='navy')
    bars2 = ax1.bar(x, peak_norm, width, label='Peak Performance', alpha=0.8, color='lightgreen', edgecolor='darkgreen')
    bars3 = ax1.bar(x + width, last5_norm, width, label='Last 5 Measurements', alpha=0.8, color='lightcoral', edgecolor='darkred')
    
    # Add value labels on bars
    def add_value_labels(ax, bars, values):
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                   f'{value:.2f}', ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    add_value_labels(ax1, bars1, full_norm)
    add_value_labels(ax1, bars2, peak_norm)
    add_value_labels(ax1, bars3, last5_norm)
    
    ax1.axhline(y=1.0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Baseline (1.0)')
    ax1.set_title('Training Throughput (Normalized)', fontweight='bold', fontsize=14)
    ax1.set_ylabel('Normalized Throughput', fontweight='bold')
    ax1.set_xlabel('Configuration', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(configs, fontsize=10)
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.set_ylim(0, 1.2)
    
    # Highlight SW's peak performance
    sw_idx = list(training_df['Configuration']).index('sw')
    ax1.annotate('SW Peak: 97.6% of baseline!', 
                xy=(sw_idx, peak_norm[sw_idx]), 
                xytext=(sw_idx-0.5, peak_norm[sw_idx]+0.15),
                arrowprops=dict(arrowstyle='->', color='green', lw=2),
                fontsize=11, fontweight='bold', color='green',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgreen", alpha=0.7))
    
    # 2. Training - Performance improvement percentages
    full_improvement = (full_norm - 1) * 100
    peak_improvement = (peak_norm - 1) * 100
    last5_improvement = (last5_norm - 1) * 100
    
    bars1 = ax2.bar(x - width, full_improvement, width, label='Full Average', alpha=0.8, color='skyblue', edgecolor='navy')
    bars2 = ax2.bar(x, peak_improvement, width, label='Peak Performance', alpha=0.8, color='lightgreen', edgecolor='darkgreen')
    bars3 = ax2.bar(x + width, last5_improvement, width, label='Last 5 Measurements', alpha=0.8, color='lightcoral', edgecolor='darkred')
    
    # Add value labels
    add_value_labels(ax2, bars1, full_improvement)
    add_value_labels(ax2, bars2, peak_improvement)
    add_value_labels(ax2, bars3, last5_improvement)
    
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=2, alpha=0.8)
    ax2.set_title('Training Performance vs Baseline (%)', fontweight='bold', fontsize=14)
    ax2.set_ylabel('Improvement (%)', fontweight='bold')
    ax2.set_xlabel('Configuration', fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(configs, fontsize=10)
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # === INFERENCE THROUGHPUT ANALYSIS ===
    
    # 3. Inference - Bar chart comparison
    full_norm_inf = inference_df['Full Normalized'].values
    peak_norm_inf = inference_df['Peak Normalized'].values
    last5_norm_inf = inference_df['Last 5 Normalized'].values
    
    bars1 = ax3.bar(x - width, full_norm_inf, width, label='Full Average', alpha=0.8, color='skyblue', edgecolor='navy')
    bars2 = ax3.bar(x, peak_norm_inf, width, label='Peak Performance', alpha=0.8, color='lightgreen', edgecolor='darkgreen')
    bars3 = ax3.bar(x + width, last5_norm_inf, width, label='Last 5 Measurements', alpha=0.8, color='lightcoral', edgecolor='darkred')
    
    add_value_labels(ax3, bars1, full_norm_inf)
    add_value_labels(ax3, bars2, peak_norm_inf)
    add_value_labels(ax3, bars3, last5_norm_inf)
    
    ax3.axhline(y=1.0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Baseline (1.0)')
    ax3.set_title('Inference Throughput (Normalized)', fontweight='bold', fontsize=14)
    ax3.set_ylabel('Normalized Throughput', fontweight='bold')
    ax3.set_xlabel('Configuration', fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(configs, fontsize=10)
    ax3.legend(loc='upper right')
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.set_ylim(0, 1.2)
    
    # 4. Inference - Performance improvement percentages
    full_improvement_inf = (full_norm_inf - 1) * 100
    peak_improvement_inf = (peak_norm_inf - 1) * 100
    last5_improvement_inf = (last5_norm_inf - 1) * 100
    
    bars1 = ax4.bar(x - width, full_improvement_inf, width, label='Full Average', alpha=0.8, color='skyblue', edgecolor='navy')
    bars2 = ax4.bar(x, peak_improvement_inf, width, label='Peak Performance', alpha=0.8, color='lightgreen', edgecolor='darkgreen')
    bars3 = ax4.bar(x + width, last5_improvement_inf, width, label='Last 5 Measurements', alpha=0.8, color='lightcoral', edgecolor='darkred')
    
    add_value_labels(ax4, bars1, full_improvement_inf)
    add_value_labels(ax4, bars2, peak_improvement_inf)
    add_value_labels(ax4, bars3, last5_improvement_inf)
    
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=2, alpha=0.8)
    ax4.set_title('Inference Performance vs Baseline (%)', fontweight='bold', fontsize=14)
    ax4.set_ylabel('Improvement (%)', fontweight='bold')
    ax4.set_xlabel('Configuration', fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels(configs, fontsize=10)
    ax4.legend(loc='upper right')
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    # Save the plot
    output_path = '/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/focused_normalized_throughput.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Focused normalized throughput graph saved: {output_path}")
    
    plt.show()
    
    # Also create a summary table for easy reference
    create_summary_table(training_df, inference_df)

def create_summary_table(training_df, inference_df):
    """Create a clean summary table."""
    
    print("\n" + "="*100)
    print("NORMALIZED THROUGHPUT SUMMARY TABLE")
    print("="*100)
    print("Note: All values normalized against Default baseline (1.0 = 100% of baseline performance)")
    print("-"*100)
    
    # Headers
    print(f"{'Configuration':<15} {'Training':<45} {'Inference':<45}")
    print(f"{'':15} {'Full':<8} {'Peak':<8} {'Last5':<8} {'Peak%':<8} {'Trend':<8} {'Full':<8} {'Peak':<8} {'Last5':<8} {'Peak%':<8} {'Trend':<8}")
    print("-"*100)
    
    # Data rows
    for i, config in enumerate(training_df['Configuration']):
        config_name = config.capitalize()
        
        # Training data
        t_full = training_df.iloc[i]['Full Normalized']
        t_peak = training_df.iloc[i]['Peak Normalized'] 
        t_last5 = training_df.iloc[i]['Last 5 Normalized']
        t_peak_pct = (t_peak - 1) * 100
        t_trend = training_df.iloc[i]['Improvement Trend (%/measurement)']
        
        # Inference data
        i_full = inference_df.iloc[i]['Full Normalized']
        i_peak = inference_df.iloc[i]['Peak Normalized']
        i_last5 = inference_df.iloc[i]['Last 5 Normalized'] 
        i_peak_pct = (i_peak - 1) * 100
        i_trend = inference_df.iloc[i]['Improvement Trend (%/measurement)']
        
        print(f"{config_name:<15} {t_full:<8.3f} {t_peak:<8.3f} {t_last5:<8.3f} {t_peak_pct:<+7.1f}% {t_trend:<+7.2f} {i_full:<8.3f} {i_peak:<8.3f} {i_last5:<8.3f} {i_peak_pct:<+7.1f}% {i_trend:<+7.2f}")
    
    print("-"*100)
    print("Key: Full=Full Average, Peak=Best 5-measurement window, Last5=Final 5 measurements")
    print("     Peak%=Peak improvement vs baseline, Trend=Performance change per measurement")
    print("="*100)

if __name__ == "__main__":
    create_focused_normalized_graphs()