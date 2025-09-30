#!/usr/bin/env python3
"""
Comprehensive analysis of all configurations including warm-up patterns.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def analyze_all_configurations():
    """Analyze all configurations for both training and inference with warm-up consideration."""
    
    # File paths for training
    training_paths = {
        'default': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-hllwm/training_throughput-default.csv",
        'sw': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-fnh9z/training_throughput-sw.csv",
        'ec': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-nb2f5/training_throughput-ec.csv",
        'autopilot': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-nr2zj/training_throughput-autopilot.csv",
        'autothrottle': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-wqqn2/training_throughput-at.csv"
    }
    
    # File paths for inference
    inference_paths = {
        'default': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-hllwm/inference_throughput-default.csv",
        'sw': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-fnh9z/inference_throughput-sw.csv",
        'ec': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-nb2f5/inference_throughput-ec.csv",
        'autopilot': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-nr2zj/inference_throughput-autopilot.csv",
        'autothrottle': "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-wqqn2/inference_throughput-at.csv"
    }

    def load_and_analyze(paths, metric_type, throughput_column):
        """Load and analyze data for a specific metric type."""
        data = {}
        
        for config, path in paths.items():
            if os.path.exists(path):
                df = pd.read_csv(path)
                data[config] = df[throughput_column]
                print(f"Loaded {config} {metric_type}: {len(df)} measurements")
            else:
                print(f"Warning: {path} not found")
        
        if 'default' not in data:
            print(f"Error: Default configuration not found for {metric_type}")
            return None
            
        baseline_avg = data['default'].mean()
        results = []
        
        print(f"\n{metric_type.upper()} THROUGHPUT ANALYSIS")
        print("=" * 80)
        print(f"Baseline (Default) Average: {baseline_avg/1e6:.1f} M examples/sec")
        print("\nDetailed Analysis:")
        print("-" * 80)
        
        for config, throughput in data.items():
            # Calculate various metrics
            full_avg = throughput.mean()
            
            # Steady state (skip first 3 measurements)
            if len(throughput) > 3:
                steady_state_avg = throughput.iloc[3:].mean()
            else:
                steady_state_avg = throughput.mean()
            
            # Last 5 measurements
            last_5_avg = throughput.tail(min(5, len(throughput))).mean()
            
            # Peak performance window (best 5 consecutive measurements)
            if len(throughput) >= 5:
                rolling_avg = throughput.rolling(window=5).mean()
                peak_avg = rolling_avg.max()
            else:
                peak_avg = throughput.max()
            
            min_val = throughput.min()
            max_val = throughput.max()
            std_dev = throughput.std()
            
            # Calculate improvement over time (slope)
            if len(throughput) > 1:
                x = np.arange(len(throughput))
                slope = np.polyfit(x, throughput, 1)[0]
                improvement_trend = slope / baseline_avg * 100  # % improvement per measurement
            else:
                improvement_trend = 0
            
            results.append({
                'Configuration': config,
                'Full Average': full_avg,
                'Steady State Avg': steady_state_avg,
                'Last 5 Avg': last_5_avg,
                'Peak 5-measurement Avg': peak_avg,
                'Min': min_val,
                'Max': max_val,
                'Std Dev': std_dev,
                'Coefficient of Variation': std_dev / full_avg,
                'Improvement Trend (%/measurement)': improvement_trend,
                'Full Normalized': full_avg / baseline_avg,
                'Steady State Normalized': steady_state_avg / baseline_avg,
                'Last 5 Normalized': last_5_avg / baseline_avg,
                'Peak Normalized': peak_avg / baseline_avg
            })
            
            print(f"\n{config.upper()}:")
            print(f"  Full Average:        {full_avg/1e6:6.1f} M/sec (norm: {full_avg/baseline_avg:5.3f}, {(full_avg/baseline_avg-1)*100:+5.1f}%)")
            print(f"  Steady State (>3rd): {steady_state_avg/1e6:6.1f} M/sec (norm: {steady_state_avg/baseline_avg:5.3f}, {(steady_state_avg/baseline_avg-1)*100:+5.1f}%)")
            print(f"  Last 5 measurements: {last_5_avg/1e6:6.1f} M/sec (norm: {last_5_avg/baseline_avg:5.3f}, {(last_5_avg/baseline_avg-1)*100:+5.1f}%)")
            print(f"  Peak 5-meas window:  {peak_avg/1e6:6.1f} M/sec (norm: {peak_avg/baseline_avg:5.3f}, {(peak_avg/baseline_avg-1)*100:+5.1f}%)")
            print(f"  Range: {min_val/1e6:6.1f} - {max_val/1e6:6.1f} M/sec (CV: {std_dev/full_avg:.3f})")
            print(f"  Trend: {improvement_trend:+.3f}% per measurement")
            
            # Highlight interesting patterns
            if config != 'default':
                if peak_avg / baseline_avg > 1.0:
                    print(f"  *** PEAK PERFORMANCE EXCEEDS BASELINE by {(peak_avg/baseline_avg-1)*100:.1f}% ***")
                if last_5_avg / baseline_avg > 1.0:
                    print(f"  *** FINAL PERFORMANCE EXCEEDS BASELINE by {(last_5_avg/baseline_avg-1)*100:.1f}% ***")
                if improvement_trend > 0.5:
                    print(f"  *** STRONG POSITIVE TREND - Performance improving over time ***")
                if std_dev / full_avg > 0.3:
                    print(f"  *** HIGH VARIABILITY - Consider warm-up effects ***")
        
        return data, results, baseline_avg
    
    # Analyze training throughput
    training_data, training_results, training_baseline = load_and_analyze(
        training_paths, 'training', 'training_throughput_examples_per_sec'
    )
    
    print("\n" + "="*80)
    
    # Analyze inference throughput  
    inference_data, inference_results, inference_baseline = load_and_analyze(
        inference_paths, 'inference', 'inference_throughput_examples_per_sec'
    )
    
    # Create comprehensive visualizations
    create_comprehensive_plots(training_data, inference_data, training_results, inference_results, 
                              training_baseline, inference_baseline)
    
    # Create summary tables
    create_comprehensive_summary(training_results, inference_results, training_baseline, inference_baseline)

def create_comprehensive_plots(training_data, inference_data, training_results, inference_results, 
                              training_baseline, inference_baseline):
    """Create comprehensive visualization plots."""
    
    fig = plt.figure(figsize=(20, 16))
    
    # Training plots
    plt.subplot(3, 3, 1)
    for config, throughput in training_data.items():
        measurements = list(range(1, len(throughput) + 1))
        plt.plot(measurements, throughput / 1e6, marker='o', label=config, linewidth=2, markersize=4)
    
    plt.axhline(y=training_baseline / 1e6, color='red', linestyle='--', alpha=0.7, label='Baseline Avg')
    plt.xlabel('Measurement Number')
    plt.ylabel('Throughput (M examples/sec)')
    plt.title('Training Throughput Over Time')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.subplot(3, 3, 2)
    configs = [r['Configuration'] for r in training_results]
    peak_norms = [r['Peak Normalized'] for r in training_results]
    last5_norms = [r['Last 5 Normalized'] for r in training_results]
    full_norms = [r['Full Normalized'] for r in training_results]
    
    x = np.arange(len(configs))
    width = 0.25
    
    plt.bar(x - width, full_norms, width, label='Full Average', alpha=0.7)
    plt.bar(x, last5_norms, width, label='Last 5', alpha=0.7)
    plt.bar(x + width, peak_norms, width, label='Peak 5-window', alpha=0.7)
    
    plt.axhline(y=1.0, color='red', linestyle='--', alpha=0.7, label='Baseline')
    plt.xlabel('Configuration')
    plt.ylabel('Normalized Throughput')
    plt.title('Training: Normalized Performance Comparison')
    plt.xticks(x, configs, rotation=45)
    plt.legend()
    plt.grid(True, alpha=0.3, axis='y')
    
    plt.subplot(3, 3, 3)
    cvs = [r['Coefficient of Variation'] for r in training_results]
    plt.bar(configs, cvs, alpha=0.7, color='orange')
    plt.xlabel('Configuration')
    plt.ylabel('Coefficient of Variation')
    plt.title('Training: Performance Variability')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3, axis='y')
    
    # Inference plots
    plt.subplot(3, 3, 4)
    for config, throughput in inference_data.items():
        measurements = list(range(1, len(throughput) + 1))
        plt.plot(measurements, throughput / 1e6, marker='o', label=config, linewidth=2, markersize=4)
    
    plt.axhline(y=inference_baseline / 1e6, color='red', linestyle='--', alpha=0.7, label='Baseline Avg')
    plt.xlabel('Measurement Number')
    plt.ylabel('Throughput (M examples/sec)')
    plt.title('Inference Throughput Over Time')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.subplot(3, 3, 5)
    configs = [r['Configuration'] for r in inference_results]
    peak_norms = [r['Peak Normalized'] for r in inference_results]
    last5_norms = [r['Last 5 Normalized'] for r in inference_results]
    full_norms = [r['Full Normalized'] for r in inference_results]
    
    x = np.arange(len(configs))
    
    plt.bar(x - width, full_norms, width, label='Full Average', alpha=0.7)
    plt.bar(x, last5_norms, width, label='Last 5', alpha=0.7)
    plt.bar(x + width, peak_norms, width, label='Peak 5-window', alpha=0.7)
    
    plt.axhline(y=1.0, color='red', linestyle='--', alpha=0.7, label='Baseline')
    plt.xlabel('Configuration')
    plt.ylabel('Normalized Throughput')
    plt.title('Inference: Normalized Performance Comparison')
    plt.xticks(x, configs, rotation=45)
    plt.legend()
    plt.grid(True, alpha=0.3, axis='y')
    
    plt.subplot(3, 3, 6)
    cvs = [r['Coefficient of Variation'] for r in inference_results]
    plt.bar(configs, cvs, alpha=0.7, color='purple')
    plt.xlabel('Configuration')
    plt.ylabel('Coefficient of Variation')
    plt.title('Inference: Performance Variability')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3, axis='y')
    
    # Combined analysis
    plt.subplot(3, 3, 7)
    training_peak_norms = [r['Peak Normalized'] for r in training_results]
    inference_peak_norms = [r['Peak Normalized'] for r in inference_results]
    
    plt.scatter(training_peak_norms, inference_peak_norms, s=100, alpha=0.7)
    for i, config in enumerate(configs):
        plt.annotate(config, (training_peak_norms[i], inference_peak_norms[i]), 
                    xytext=(5, 5), textcoords='offset points')
    
    plt.axhline(y=1.0, color='red', linestyle='--', alpha=0.7)
    plt.axvline(x=1.0, color='red', linestyle='--', alpha=0.7)
    plt.xlabel('Training Peak Normalized')
    plt.ylabel('Inference Peak Normalized')
    plt.title('Peak Performance: Training vs Inference')
    plt.grid(True, alpha=0.3)
    
    plt.subplot(3, 3, 8)
    training_trends = [r['Improvement Trend (%/measurement)'] for r in training_results]
    inference_trends = [r['Improvement Trend (%/measurement)'] for r in inference_results]
    
    plt.scatter(training_trends, inference_trends, s=100, alpha=0.7)
    for i, config in enumerate(configs):
        plt.annotate(config, (training_trends[i], inference_trends[i]), 
                    xytext=(5, 5), textcoords='offset points')
    
    plt.axhline(y=0, color='red', linestyle='--', alpha=0.7)
    plt.axvline(x=0, color='red', linestyle='--', alpha=0.7)
    plt.xlabel('Training Trend (%/measurement)')
    plt.ylabel('Inference Trend (%/measurement)')
    plt.title('Performance Trends Over Time')
    plt.grid(True, alpha=0.3)
    
    plt.subplot(3, 3, 9)
    # Summary heatmap of key metrics
    metrics = ['Full Normalized', 'Peak Normalized', 'Last 5 Normalized']
    training_matrix = [[r[metric] for r in training_results] for metric in metrics]
    inference_matrix = [[r[metric] for r in inference_results] for metric in metrics]
    
    # Create combined matrix
    combined_matrix = []
    for i, metric in enumerate(metrics):
        combined_matrix.append(training_matrix[i])
        combined_matrix.append(inference_matrix[i])
    
    combined_labels = []
    for metric in metrics:
        combined_labels.append(f'Train {metric.split()[0]}')
        combined_labels.append(f'Infer {metric.split()[0]}')
    
    im = plt.imshow(combined_matrix, cmap='RdYlGn', aspect='auto', vmin=0.2, vmax=1.8)
    plt.colorbar(im)
    plt.xticks(range(len(configs)), configs, rotation=45)
    plt.yticks(range(len(combined_labels)), combined_labels)
    plt.title('Performance Heatmap (Normalized)')
    
    # Add text annotations
    for i in range(len(combined_labels)):
        for j in range(len(configs)):
            text = plt.text(j, i, f'{combined_matrix[i][j]:.2f}', 
                           ha="center", va="center", color="black", fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/comprehensive_analysis.png', 
                dpi=300, bbox_inches='tight')
    plt.show()

def create_comprehensive_summary(training_results, inference_results, training_baseline, inference_baseline):
    """Create comprehensive summary tables."""
    
    output_dir = '/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost'
    
    # Training summary
    training_df = pd.DataFrame(training_results)
    training_df['Baseline (M/sec)'] = training_baseline / 1e6
    training_df['Full Avg (M/sec)'] = training_df['Full Average'] / 1e6
    training_df['Peak Avg (M/sec)'] = training_df['Peak 5-measurement Avg'] / 1e6
    training_df['Last 5 Avg (M/sec)'] = training_df['Last 5 Avg'] / 1e6
    training_df['Min (M/sec)'] = training_df['Min'] / 1e6
    training_df['Max (M/sec)'] = training_df['Max'] / 1e6
    
    training_summary = training_df[['Configuration', 'Full Avg (M/sec)', 'Peak Avg (M/sec)', 
                                   'Last 5 Avg (M/sec)', 'Full Normalized', 'Peak Normalized', 
                                   'Last 5 Normalized', 'Min (M/sec)', 'Max (M/sec)', 
                                   'Coefficient of Variation', 'Improvement Trend (%/measurement)']]
    
    training_summary.to_csv(f'{output_dir}/comprehensive_training_analysis.csv', index=False)
    
    # Inference summary
    inference_df = pd.DataFrame(inference_results)
    inference_df['Baseline (M/sec)'] = inference_baseline / 1e6
    inference_df['Full Avg (M/sec)'] = inference_df['Full Average'] / 1e6
    inference_df['Peak Avg (M/sec)'] = inference_df['Peak 5-measurement Avg'] / 1e6
    inference_df['Last 5 Avg (M/sec)'] = inference_df['Last 5 Avg'] / 1e6
    inference_df['Min (M/sec)'] = inference_df['Min'] / 1e6
    inference_df['Max (M/sec)'] = inference_df['Max'] / 1e6
    
    inference_summary = inference_df[['Configuration', 'Full Avg (M/sec)', 'Peak Avg (M/sec)', 
                                     'Last 5 Avg (M/sec)', 'Full Normalized', 'Peak Normalized', 
                                     'Last 5 Normalized', 'Min (M/sec)', 'Max (M/sec)', 
                                     'Coefficient of Variation', 'Improvement Trend (%/measurement)']]
    
    inference_summary.to_csv(f'{output_dir}/comprehensive_inference_analysis.csv', index=False)
    
    print(f"\n\nSUMMARY TABLES SAVED:")
    print(f"Training: {output_dir}/comprehensive_training_analysis.csv")
    print(f"Inference: {output_dir}/comprehensive_inference_analysis.csv")
    print(f"Plot: {output_dir}/comprehensive_analysis.png")

if __name__ == "__main__":
    analyze_all_configurations()