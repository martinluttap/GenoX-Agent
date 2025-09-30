#!/usr/bin/env python3
"""
Quick verification of throughput calculations.
"""

import pandas as pd

def check_throughput_averages():
    # Load default training data
    default_path = "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-hllwm/training_throughput-default.csv"
    sw_path = "/home/cc/Results/sep23/2024-biosys-ec-elasticcontainer/Machine-learning-models/xgboost/exported-csv/xgboost-benchmark-5f8895c8f8-fnh9z/training_throughput-sw.csv"
    
    default_df = pd.read_csv(default_path)
    sw_df = pd.read_csv(sw_path)
    
    default_avg = default_df['training_throughput_examples_per_sec'].mean()
    sw_avg = sw_df['training_throughput_examples_per_sec'].mean()
    
    print("Training Throughput Verification:")
    print("-" * 40)
    print(f"Default average: {default_avg:,.0f} examples/sec")
    print(f"SW average: {sw_avg:,.0f} examples/sec")
    print(f"SW vs Default ratio: {sw_avg/default_avg:.3f}")
    print(f"SW improvement: {(sw_avg/default_avg - 1)*100:+.1f}%")
    
    print("\nDefault values:")
    for i, val in enumerate(default_df['training_throughput_examples_per_sec'][:5]):
        print(f"  {i+1}: {val:,.0f}")
    
    print("\nSW values:")
    for i, val in enumerate(sw_df['training_throughput_examples_per_sec'][:5]):
        print(f"  {i+1}: {val:,.0f}")
        
    print(f"\nSW last 5 values:")
    for i, val in enumerate(sw_df['training_throughput_examples_per_sec'][-5:]):
        print(f"  {len(sw_df)-4+i}: {val:,.0f}")

if __name__ == "__main__":
    check_throughput_averages()