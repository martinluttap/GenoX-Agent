#!/usr/bin/env python3
"""
Display the normalized throughput analysis results.
"""

import pandas as pd
import os

def display_results():
    """Display the normalized throughput analysis results."""
    
    results_dir = "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/normalized_analysis"
    summary_file = os.path.join(results_dir, "normalized_throughput_summary.csv")
    
    if os.path.exists(summary_file):
        print("XGBoost Normalized Throughput Analysis Results")
        print("=" * 60)
        print("\nMetric Used: throughput_examples_per_sec")
        print("Baseline: Default configuration (normalized to 1.0)")
        print("\nNormalized Throughput Summary:")
        print("-" * 60)
        
        df = pd.read_csv(summary_file)
        print(df.to_string(index=False))
        
        print("\n" + "=" * 60)
        print("Key Findings:")
        print("=" * 60)
        
        # Parse the data for analysis
        for _, row in df.iterrows():
            if row['Configuration'] != 'Default (Baseline)':
                inf_improvement = float(row['Inference Improvement (%)'].replace('%', '').replace('+', ''))
                train_improvement = float(row['Training Improvement (%)'].replace('%', '').replace('+', ''))
                
                print(f"\n{row['Configuration']}:")
                print(f"  - Inference: {inf_improvement:+.1f}% vs baseline")
                print(f"  - Training: {train_improvement:+.1f}% vs baseline")
                
                if inf_improvement < 0 and train_improvement < 0:
                    print(f"  - Overall: Performance degradation in both metrics")
                elif inf_improvement > 0 and train_improvement > 0:
                    print(f"  - Overall: Performance improvement in both metrics")
                else:
                    print(f"  - Overall: Mixed performance results")
        
        print("\nGenerated Files:")
        print("-" * 30)
        for filename in ["normalized_inference_throughput_analysis.png", 
                        "normalized_training_throughput_analysis.png",
                        "normalized_throughput_summary.csv"]:
            filepath = os.path.join(results_dir, filename)
            if os.path.exists(filepath):
                print(f"✓ {filepath}")
        
    else:
        print(f"Results file not found: {summary_file}")

if __name__ == "__main__":
    display_results()