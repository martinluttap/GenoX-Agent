#!/usr/bin/env python3
"""
Real-time XGBoost Inference Throughput Monitor
Continuously sends examples and measures throughput in real-time
"""

import time
import threading
import signal
import sys
import os
import numpy as np
import xgboost as xgb
from collections import deque
import statistics

class InferenceThroughputMonitor:
    def __init__(self, model_path=None, data_size=10000, batch_size=100):
        self.running = True
        self.model_path = model_path
        self.batch_size = batch_size
        
        # Generate synthetic data if no real data available
        print("Initializing inference monitor...")
        self.test_data = np.random.randn(data_size, 28)  # HIGGS has 28 features
        
        # Load or create a simple model
        self.model = self._load_model()
        
        # Throughput tracking
        self.throughput_window = deque(maxlen=50)  # Last 50 measurements
        self.total_examples = 0
        self.start_time = time.time()
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def _load_model(self):
        """Load existing model or create a simple one"""
        if self.model_path and os.path.exists(self.model_path):
            print(f"Loading model from {self.model_path}")
            model = xgb.Booster()
            model.load_model(self.model_path)
            return model
        
        # Create a simple model for demonstration
        print("Creating simple model for benchmarking...")
        # Create dummy training data
        X_dummy = np.random.randn(1000, 28)
        y_dummy = np.random.randint(0, 2, 1000)
        
        dtrain = xgb.DMatrix(X_dummy, label=y_dummy)
        params = {
            'objective': 'binary:logistic',
            'max_depth': 3,
            'eta': 0.1,
            'eval_metric': 'logloss'
        }
        
        model = xgb.train(params, dtrain, num_boost_round=10)
        return model
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print("\nShutting down gracefully...")
        self.running = False
    
    def run_inference_batch(self):
        """Run inference on a random batch"""
        # Get random batch
        start_idx = np.random.randint(0, len(self.test_data) - self.batch_size)
        batch = self.test_data[start_idx:start_idx + self.batch_size]
        
        # Create DMatrix and predict
        dmatrix = xgb.DMatrix(batch)
        
        start_time = time.time()
        _ = self.model.predict(dmatrix)
        end_time = time.time()
        
        inference_time = end_time - start_time
        throughput = len(batch) / inference_time if inference_time > 0 else 0
        
        return throughput, len(batch), inference_time
    
    def monitor_continuous_inference(self, report_interval=2.0):
        """Continuously run inference and report throughput"""
        print(f"\nStarting continuous inference monitoring...")
        print(f"Batch size: {self.batch_size}")
        print(f"Report interval: {report_interval}s")
        print("Press Ctrl+C to stop\n")
        
        print(f"{'Time':>8} | {'Current':>12} | {'Average':>12} | {'Total':>10} | {'Latency':>10}")
        print(f"{'(s)':>8} | {'(ex/s)':>12} | {'(ex/s)':>12} | {'Examples':>10} | {'(ms)':>10}")
        print("-" * 70)
        
        last_report_time = time.time()
        last_report_examples = 0
        
        while self.running:
            try:
                # Run inference
                throughput, batch_examples, latency = self.run_inference_batch()
                
                self.throughput_window.append(throughput)
                self.total_examples += batch_examples
                
                current_time = time.time()
                
                # Report at intervals
                if current_time - last_report_time >= report_interval:
                    elapsed = current_time - self.start_time
                    
                    # Calculate current throughput (examples in this interval)
                    examples_this_interval = self.total_examples - last_report_examples
                    interval_throughput = examples_this_interval / (current_time - last_report_time)
                    
                    # Calculate average throughput
                    avg_throughput = self.total_examples / elapsed
                    
                    # Calculate average recent throughput
                    recent_avg = statistics.mean(self.throughput_window) if self.throughput_window else 0
                    
                    print(f"{elapsed:8.1f} | {interval_throughput:12.0f} | {avg_throughput:12.0f} | {self.total_examples:10d} | {latency*1000:10.2f}")
                    
                    last_report_time = current_time
                    last_report_examples = self.total_examples
                
                # Small sleep to prevent 100% CPU usage
                time.sleep(0.001)
                
            except Exception as e:
                print(f"Error during inference: {e}")
                break
        
        # Final report
        total_time = time.time() - self.start_time
        final_throughput = self.total_examples / total_time
        
        print("\n" + "="*70)
        print("FINAL RESULTS:")
        print(f"Total runtime: {total_time:.2f} seconds")
        print(f"Total examples processed: {self.total_examples:,}")
        print(f"Average throughput: {final_throughput:.2f} examples/sec")
        if self.throughput_window:
            print(f"Recent throughput (avg): {statistics.mean(self.throughput_window):.2f} examples/sec")
            print(f"Throughput std dev: {statistics.stdev(self.throughput_window):.2f}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="XGBoost Inference Throughput Monitor")
    parser.add_argument("--model", help="Path to XGBoost model file")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for inference")
    parser.add_argument("--data-size", type=int, default=50000, help="Size of test dataset")
    parser.add_argument("--interval", type=float, default=2.0, help="Reporting interval in seconds")
    
    args = parser.parse_args()
    
    # Check for existing model files
    model_path = args.model
    if not model_path:
        # Check for common model files
        for candidate in ["benchmark_model.json", "xgboost_model.json", "model.json"]:
            if os.path.exists(candidate):
                model_path = candidate
                break
    
    monitor = InferenceThroughputMonitor(
        model_path=model_path,
        data_size=args.data_size,
        batch_size=args.batch_size
    )
    
    monitor.monitor_continuous_inference(report_interval=args.interval)

if __name__ == "__main__":
    main()