#!/usr/bin/env python3
"""
Improved throughput analysis that accounts for warm-up behavior.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def analyze_warmup_behavior():
    """Analyze throughput with consideration for warm-up behavior."""
    
    # File paths
    paths = {
        'default': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-hllwm/training_throughput-default.csv",
        'sw': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-fnh9z/training_throughput-sw.csv",
        'ec': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-nb2f5/training_throughput-ec.csv",
        'autopilot': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-nr2zj/training_throughput-autopilot.csv",
        'autothrottle': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-wqqn2/training_throughput-at.csv"
    }
    
    data = {}
    for config, path in paths.items():
        if os.path.exists(path):
            df = pd.read_csv(path)
            data[config] = df['training_throughput_examples_per_sec']
    
    # Analysis results
    results = []
    
    baseline_avg = data['default'].mean()
    
    for config, throughput in data.items():
        full_avg = throughput.mean()
        
        # Calculate steady-state (excluding first 5 measurements for warm-up)
        if len(throughput) > 5:
            steady_state_avg = throughput.iloc[5:].mean()
        else:
            steady_state_avg = throughput.mean()
        
        # Calculate last 5 measurements average
        last_5_avg = throughput.tail(5).mean()
        
        results.append({
            'Configuration': config,
            'Full Average (M/sec)': full_avg / 1e6,
            'Steady State Avg (M/sec)': steady_state_avg / 1e6,
            'Last 5 Avg (M/sec)': last_5_avg / 1e6,
            'Full Normalized': full_avg / baseline_avg,
            'Steady State Normalized': steady_state_avg / baseline_avg,
            'Last 5 Normalized': last_5_avg / baseline_avg,
            'Max Throughput (M/sec)': throughput.max() / 1e6,
            'Min Throughput (M/sec)': throughput.min() / 1e6
        })
    
    # Create DataFrame and display
    df_results = pd.DataFrame(results)
    
    print("Training Throughput Analysis - Accounting for Warm-up")
    print("=" * 80)
    print("\nBaseline (Default) Average: {:.1f} M examples/sec".format(baseline_avg / 1e6))
    print("\nDetailed Analysis:")
    print("-" * 80)
    
    for _, row in df_results.iterrows():
        print(f"\n{row['Configuration'].upper()}:")
        print(f"  Full Average:        {row['Full Average (M/sec)']:6.1f} M/sec (normalized: {row['Full Normalized']:5.3f})")
        print(f"  Steady State (>5th): {row['Steady State Avg (M/sec)']:6.1f} M/sec (normalized: {row['Steady State Normalized']:5.3f})")
        print(f"  Last 5 measurements: {row['Last 5 Avg (M/sec)']:6.1f} M/sec (normalized: {row['Last 5 Normalized']:5.3f})")
        print(f"  Range: {row['Min Throughput (M/sec)']:6.1f} - {row['Max Throughput (M/sec)']:6.1f} M/sec")
        
        if row['Configuration'] != 'default':
            if row['Steady State Normalized'] > 1.0:
                print(f"  *** BETTER than baseline in steady state! ***")
            elif row['Last 5 Normalized'] > 1.0:
                print(f"  *** BETTER than baseline in final measurements! ***")
    
    # Create visualization
    plt.figure(figsize=(15, 10))
    
    # Plot 1: Time series
    plt.subplot(2, 2, 1)
    for config, throughput in data.items():
        measurements = list(range(1, len(throughput) + 1))
        plt.plot(measurements, throughput / 1e6, marker='o', label=config, linewidth=2)
    
    plt.axhline(y=baseline_avg / 1e6, color='red', linestyle='--', alpha=0.7, label='Baseline Avg')
    plt.xlabel('Measurement Number')
    plt.ylabel('Throughput (M examples/sec)')
    plt.title('Training Throughput Over Time')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Plot 2: Comparison bars
    plt.subplot(2, 2, 2)
    configs = df_results['Configuration'].tolist()
    full_avgs = df_results['Full Normalized'].tolist()
    steady_avgs = df_results['Steady State Normalized'].tolist()
    last5_avgs = df_results['Last 5 Normalized'].tolist()
    
    x = np.arange(len(configs))
    width = 0.25
    
    plt.bar(x - width, full_avgs, width, label='Full Average', alpha=0.7)
    plt.bar(x, steady_avgs, width, label='Steady State', alpha=0.7)
    plt.bar(x + width, last5_avgs, width, label='Last 5', alpha=0.7)
    
    plt.axhline(y=1.0, color='red', linestyle='--', alpha=0.7, label='Baseline')
    plt.xlabel('Configuration')
    plt.ylabel('Normalized Throughput')
    plt.title('Normalized Training Throughput Comparison')
    plt.xticks(x, configs, rotation=45)
    plt.legend()
    plt.grid(True, alpha=0.3, axis='y')
    
    # Plot 3: Box plot of all measurements
    plt.subplot(2, 2, 3)
    box_data = [throughput / 1e6 for throughput in data.values()]
    box_labels = list(data.keys())
    
    plt.boxplot(box_data, labels=box_labels, patch_artist=True)
    plt.axhline(y=baseline_avg / 1e6, color='red', linestyle='--', alpha=0.7, label='Baseline Avg')
    plt.ylabel('Throughput (M examples/sec)')
    plt.title('Throughput Distribution')
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True, alpha=0.3, axis='y')
    
    # Plot 4: Performance improvement percentages
    plt.subplot(2, 2, 4)
    improvements_full = [(norm - 1) * 100 for norm in full_avgs]
    improvements_steady = [(norm - 1) * 100 for norm in steady_avgs]
    improvements_last5 = [(norm - 1) * 100 for norm in last5_avgs]
    
    x = np.arange(len(configs))
    plt.bar(x - width, improvements_full, width, label='Full Average', alpha=0.7)
    plt.bar(x, improvements_steady, width, label='Steady State', alpha=0.7)
    plt.bar(x + width, improvements_last5, width, label='Last 5', alpha=0.7)
    
    plt.axhline(y=0, color='black', linestyle='-', alpha=0.8)
    plt.xlabel('Configuration')
    plt.ylabel('Improvement (%)')
    plt.title('Performance Improvement vs Baseline')
    plt.xticks(x, configs, rotation=45)
    plt.legend()
    plt.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/warmup_analysis.png', 
                dpi=300, bbox_inches='tight')
    plt.show()
    
    return df_results

if __name__ == "__main__":
    analyze_warmup_behavior()