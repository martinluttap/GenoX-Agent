#!/usr/bin/env python3
"""
Calculate median throughput values for all configurations.
"""

import pandas as pd
import numpy as np
import os

def calculate_median_throughput():
    """Calculate median throughput for all configurations."""
    
    # Configuration paths
    config_paths = {
        'training': {
            'default': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-hllwm/training_throughput-default.csv",
            'sw': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-fnh9z/training_throughput-sw.csv",
            'ec': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-nb2f5/training_throughput-ec.csv",
            'autopilot': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-nr2zj/training_throughput-autopilot.csv",
            'autothrottle': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-wqqn2/training_throughput-at.csv"
        },
        'inference': {
            'default': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-hllwm/inference_throughput-default.csv",
            'sw': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-fnh9z/inference_throughput-sw.csv",
            'ec': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-nb2f5/inference_throughput-ec.csv",
            'autopilot': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-nr2zj/inference_throughput-autopilot.csv",
            'autothrottle': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-wqqn2/inference_throughput-at.csv"
        }
    }
    
    # Column names for throughput
    throughput_columns = {
        'training': 'training_throughput_examples_per_sec',
        'inference': 'inference_throughput_examples_per_sec'
    }
    
    results = {}
    
    for metric_type in ['training', 'inference']:
        results[metric_type] = {}
        
        print(f"{metric_type.upper()} THROUGHPUT MEDIAN ANALYSIS")
        print("=" * 60)
        
        for config, path in config_paths[metric_type].items():
            if os.path.exists(path):
                df = pd.read_csv(path)
                throughput = df[throughput_columns[metric_type]]
                
                median_val = throughput.median()
                mean_val = throughput.mean()
                std_val = throughput.std()
                min_val = throughput.min()
                max_val = throughput.max()
                
                results[metric_type][config] = {
                    'median': median_val,
                    'mean': mean_val,
                    'std': std_val,
                    'min': min_val,
                    'max': max_val,
                    'count': len(throughput)
                }
                
                print(f"{config.upper():<12}: Median = {median_val:>12,.0f} examples/sec")
                print(f"{'':12}  Mean   = {mean_val:>12,.0f} examples/sec")
                print(f"{'':12}  Std    = {std_val:>12,.0f} examples/sec")
                print(f"{'':12}  Range  = {min_val:>12,.0f} - {max_val:,.0f} examples/sec")
                print(f"{'':12}  Count  = {len(throughput):>12} measurements")
                print()
            else:
                print(f"{config.upper():<12}: FILE NOT FOUND")
                print()
        
        print("=" * 60)
        print()
    
    # Calculate normalized values against default baseline
    print("NORMALIZED MEDIAN ANALYSIS (vs Default Baseline)")
    print("=" * 80)
    
    # Get default baselines
    training_baseline = results['training']['default']['median'] if 'default' in results['training'] else None
    inference_baseline = results['inference']['default']['median'] if 'default' in results['inference'] else None
    
    if training_baseline and inference_baseline:
        print(f"Training Baseline (Default Median):  {training_baseline:,.0f} examples/sec")
        print(f"Inference Baseline (Default Median): {inference_baseline:,.0f} examples/sec")
        print("-" * 80)
        
        # Summary table
        print(f"{'Configuration':<15} {'Training':<25} {'Inference':<25}")
        print(f"{'':15} {'Median':<12} {'vs Default':<12} {'Median':<12} {'vs Default':<12}")
        print("-" * 80)
        
        for config in ['default', 'sw', 'ec', 'autopilot', 'autothrottle']:
            if config in results['training'] and config in results['inference']:
                t_median = results['training'][config]['median']
                i_median = results['inference'][config]['median']
                
                t_norm = t_median / training_baseline
                i_norm = i_median / inference_baseline
                
                print(f"{config.capitalize():<15} {t_median:>10,.0f} {t_norm:>10.3f} {i_median:>10,.0f} {i_norm:>10.3f}")
        
        print("-" * 80)
        
        # Analysis insights
        print("\nMEDIAN vs MEAN COMPARISON:")
        print("-" * 40)
        
        for metric_type in ['training', 'inference']:
            print(f"\n{metric_type.upper()}:")
            baseline_median = results[metric_type]['default']['median']
            baseline_mean = results[metric_type]['default']['mean']
            
            for config in ['default', 'sw', 'ec', 'autopilot', 'autothrottle']:
                if config in results[metric_type]:
                    data = results[metric_type][config]
                    median_norm = data['median'] / baseline_median
                    mean_norm = data['mean'] / baseline_median
                    difference = median_norm - mean_norm
                    
                    skew_indication = ""
                    if abs(difference) > 0.05:  # Significant difference
                        if difference > 0:
                            skew_indication = " (Median > Mean: Left-skewed)"
                        else:
                            skew_indication = " (Median < Mean: Right-skewed)"
                    
                    print(f"  {config.capitalize():<12}: Median={median_norm:.3f}, Mean={mean_norm:.3f}, Diff={difference:+.3f}{skew_indication}")
        
        print("\n" + "=" * 80)
        print("KEY INSIGHTS:")
        print("=" * 80)
        
        # Find configurations where median differs significantly from mean
        print("Configurations with significant median/mean differences (>5%):")
        for metric_type in ['training', 'inference']:
            baseline_median = results[metric_type]['default']['median']
            print(f"\n{metric_type.upper()}:")
            
            for config in ['sw', 'ec', 'autopilot', 'autothrottle']:
                if config in results[metric_type]:
                    data = results[metric_type][config]
                    median_norm = data['median'] / baseline_median
                    mean_norm = data['mean'] / baseline_median
                    difference = median_norm - mean_norm
                    
                    if abs(difference) > 0.05:
                        if difference > 0:
                            print(f"  {config.upper()}: Median is {difference:.1%} higher than mean - suggests outliers pull average DOWN")
                        else:
                            print(f"  {config.upper()}: Median is {abs(difference):.1%} lower than mean - suggests outliers pull average UP")
    
    return results

if __name__ == "__main__":
    results = calculate_median_throughput()