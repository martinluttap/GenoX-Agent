#!/usr/bin/env python3
"""
Investigate the apparent contradiction in throughput vs performance.
"""

import pandas as pd
import numpy as np
import os

def investigate_throughput_contradiction():
    """Investigate why higher throughput can show as performance degradation."""
    
    # Load all configuration data
    config_paths = {
        'default': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-hllwm/training_throughput-default.csv",
        'sw': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-fnh9z/training_throughput-sw.csv",
        'ec': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-nb2f5/training_throughput-ec.csv",
        'autopilot': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-nr2zj/training_throughput-autopilot.csv",
        'autothrottle': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-wqqn2/training_throughput-at.csv"
    }
    
    # Load all data
    config_data = {}
    for config, path in config_paths.items():
        if os.path.exists(path):
            config_data[config] = pd.read_csv(path)
        else:
            print(f"Warning: {path} not found")
    
    default_df = config_data['default']
    
    print("INVESTIGATING THROUGHPUT PATTERNS ACROSS ALL CONFIGURATIONS")
    print("=" * 80)
    
    # Get default throughput for baseline
    default_throughput = default_df['training_throughput_examples_per_sec']
    default_avg = default_throughput.mean()
    
    print(f"Default (Baseline) Average: {default_avg:,.0f} examples/sec")
    print("=" * 80)
    
    # Analyze each configuration
    for config_name, df in config_data.items():
        if config_name == 'default':
            continue
            
        print(f"\n{config_name.upper()} ANALYSIS:")
        print("-" * 50)
        
        throughput = df['training_throughput_examples_per_sec']
        config_avg = throughput.mean()
        
        print(f"Average: {config_avg:,.0f} examples/sec ({config_avg/default_avg:.3f} vs default, {(config_avg/default_avg-1)*100:+.1f}%)")
        print(f"Peak:    {throughput.max():,.0f} examples/sec ({throughput.max()/default_avg:.3f} vs default, {(throughput.max()/default_avg-1)*100:+.1f}%)")
        print(f"Min:     {throughput.min():,.0f} examples/sec ({throughput.min()/default_avg:.3f} vs default, {(throughput.min()/default_avg-1)*100:+.1f}%)")
        print(f"Range:   {throughput.max() - throughput.min():,.0f} examples/sec")
        print(f"Std Dev: {throughput.std():,.0f} examples/sec (CV: {throughput.std()/config_avg:.3f})")
        
        # Count measurements better than default average
        better_than_default = (throughput > default_avg).sum()
        total_measurements = len(throughput)
        
        print(f"Measurements > default avg: {better_than_default}/{total_measurements} ({better_than_default/total_measurements*100:.1f}%)")
        
        # Show pattern over time
        first_half = throughput.iloc[:len(throughput)//2]
        second_half = throughput.iloc[len(throughput)//2:]
        
        print(f"First half avg:  {first_half.mean():,.0f} examples/sec")
        print(f"Second half avg: {second_half.mean():,.0f} examples/sec")
        print(f"Trend: {'Improving' if second_half.mean() > first_half.mean() else 'Declining'}")
        
        # Check for warm-up pattern (like SW)
        if throughput.std() / config_avg > 0.2:  # High coefficient of variation
            print("*** HIGH VARIABILITY - Possible warm-up/instability effects ***")
            
        if throughput.max() > default_avg:
            print(f"*** PEAK EXCEEDS DEFAULT BASELINE by {(throughput.max()/default_avg-1)*100:.1f}% ***")
    
    print("\n" + "=" * 80)
    
    # Detailed comparison for each configuration
    print("DETAILED MEASUREMENT-BY-MEASUREMENT ANALYSIS:")
    print("=" * 80)
    
    for config_name, df in config_data.items():
        if config_name == 'default':
            continue
            
        print(f"\n{config_name.upper()} vs DEFAULT:")
        print("-" * 60)
        
        throughput = df['training_throughput_examples_per_sec']
        
        print(f"{'#':<4} {'Default':<15} {config_name.upper():<15} {'Ratio':<8} {'Better?':<8} {'Trend'}")
        print("-" * 60)
        
        better_count = 0
        max_measurements = min(len(default_throughput), len(throughput))
        
        for i in range(max_measurements):
            default_val = default_throughput.iloc[i]
            config_val = throughput.iloc[i]
            ratio = config_val / default_val
            is_better = "YES" if ratio > 1.0 else "NO"
            
            if ratio > 1.0:
                better_count += 1
                
            # Simple trend indication
            if i > 0:
                prev_val = throughput.iloc[i-1]
                trend = "↑" if config_val > prev_val else "↓" if config_val < prev_val else "→"
            else:
                trend = "-"
                
            print(f"{i+1:<4} {default_val:>13,.0f} {config_val:>13,.0f} {ratio:>6.3f} {is_better:>6} {trend:>6}")
        
        # Handle remaining measurements if any
        for i in range(max_measurements, len(throughput)):
            config_val = throughput.iloc[i]
            ratio = config_val / default_avg
            is_better = "YES" if ratio > 1.0 else "NO"
            
            if ratio > 1.0:
                better_count += 1
                
            prev_val = throughput.iloc[i-1]
            trend = "↑" if config_val > prev_val else "↓" if config_val < prev_val else "→"
                
            print(f"{i+1:<4} {default_avg:>13,.0f} {config_val:>13,.0f} {ratio:>6.3f} {is_better:>6} {trend:>6}")
        
        print("-" * 60)
        print(f"Total measurements better than default: {better_count}/{len(throughput)} ({better_count/len(throughput)*100:.1f}%)")
        
        # Identify patterns
        if config_name == 'sw':
            print("*** SW shows classic warm-up pattern: starts low, peaks high, then settles ***")
        elif throughput.std() / throughput.mean() > 0.1:
            print(f"*** {config_name.upper()} shows high variability (CV: {throughput.std()/throughput.mean():.3f}) ***")
        else:
            print(f"*** {config_name.upper()} shows relatively stable performance ***")
    
    print("\n" + "=" * 80)
    print("ANALYSIS WITHOUT SW PEAK MEASUREMENTS (REMOVING WARMUP OUTLIERS):")
    print("=" * 80)
    
    # Special analysis for SW without the 3 peak measurements
    if 'sw' in config_data:
        sw_throughput = config_data['sw']['training_throughput_examples_per_sec']
        
        # Remove the 3 measurements that exceed baseline (measurements 5, 6, 7)
        sw_no_peaks = sw_throughput.drop([4, 5, 6])  # 0-indexed, so 4,5,6 = measurements 5,6,7
        
        print(f"SW WITHOUT PEAK MEASUREMENTS:")
        print(f"Original SW average:     {sw_throughput.mean():,.0f} examples/sec ({sw_throughput.mean()/default_avg:.3f})")
        print(f"SW without 3 peaks:     {sw_no_peaks.mean():,.0f} examples/sec ({sw_no_peaks.mean()/default_avg:.3f})")
        print(f"Improvement by removing peaks: {(sw_no_peaks.mean()/default_avg - sw_throughput.mean()/default_avg):.3f}")
        print(f"SW without peaks vs default: {(sw_no_peaks.mean()/default_avg-1)*100:+.1f}%")
        print()
        
        # Show the removed measurements
        removed_measurements = sw_throughput.iloc[[4, 5, 6]]
        print("REMOVED MEASUREMENTS (Peak Performance Period):")
        for i, (idx, val) in enumerate(removed_measurements.items(), 5):
            print(f"  Measurement #{i}: {val:,.0f} examples/sec ({val/default_avg:.3f} vs baseline)")
        print()
    
    print("SUMMARY OF KEY FINDINGS:")
    print("=" * 80)
    
    findings = []
    for config_name, df in config_data.items():
        if config_name == 'default':
            continue
            
        throughput = df['training_throughput_examples_per_sec']
        
        # Special handling for SW
        if config_name == 'sw':
            # Original SW stats
            config_avg = throughput.mean()
            peak = throughput.max()
            cv = throughput.std() / config_avg
            better_than_baseline = (throughput > default_avg).sum()
            
            # SW without peaks
            sw_no_peaks = throughput.drop([4, 5, 6])
            config_avg_no_peaks = sw_no_peaks.mean()
            
            finding = {
                'config': config_name,
                'avg_vs_default': config_avg / default_avg,
                'avg_no_peaks_vs_default': config_avg_no_peaks / default_avg,
                'peak_vs_default': peak / default_avg,
                'cv': cv,
                'better_measurements_pct': better_than_baseline / len(throughput) * 100,
                'can_exceed_baseline': peak > default_avg
            }
        else:
            config_avg = throughput.mean()
            peak = throughput.max()
            cv = throughput.std() / config_avg
            better_than_baseline = (throughput > default_avg).sum()
            
            finding = {
                'config': config_name,
                'avg_vs_default': config_avg / default_avg,
                'avg_no_peaks_vs_default': None,  # Not applicable
                'peak_vs_default': peak / default_avg,
                'cv': cv,
                'better_measurements_pct': better_than_baseline / len(throughput) * 100,
                'can_exceed_baseline': peak > default_avg
            }
        findings.append(finding)
    
    for f in findings:
        config = f['config'].upper()
        print(f"\n{config}:")
        print(f"  Average Performance:    {f['avg_vs_default']:.3f} ({(f['avg_vs_default']-1)*100:+.1f}%)")
        if f['avg_no_peaks_vs_default'] is not None:
            print(f"  Avg without peaks:      {f['avg_no_peaks_vs_default']:.3f} ({(f['avg_no_peaks_vs_default']-1)*100:+.1f}%)")
        print(f"  Peak Performance:       {f['peak_vs_default']:.3f} ({(f['peak_vs_default']-1)*100:+.1f}%)")
        print(f"  Variability (CV):       {f['cv']:.3f}")
        print(f"  % Measurements > Baseline: {f['better_measurements_pct']:.1f}%")
        print(f"  Can exceed baseline:    {'YES' if f['can_exceed_baseline'] else 'NO'}")
        
        if f['avg_no_peaks_vs_default'] is not None and f['avg_no_peaks_vs_default'] < f['avg_vs_default']:
            print(f"  *** REMOVING PEAK OUTLIERS MAKES PERFORMANCE WORSE! ***")
        elif f['can_exceed_baseline'] and f['avg_vs_default'] < 1.0:
            print(f"  *** CONTRADICTION: Peak exceeds baseline but average doesn't! ***")
        elif f['cv'] > 0.2:
            print(f"  *** HIGH VARIABILITY: Performance is inconsistent ***")
        elif f['avg_vs_default'] > 0.9:
            print(f"  *** CLOSE TO BASELINE: Within 10% of default performance ***")
    
    print("=" * 80)

if __name__ == "__main__":
    investigate_throughput_contradiction()