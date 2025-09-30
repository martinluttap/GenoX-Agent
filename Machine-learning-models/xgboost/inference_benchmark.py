import time
import threading
import queue
import statistics
import polars as pl
import xgboost as xgb
import numpy as np
import multiprocessing
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
import psutil
import os

# ------------------------
# Enhanced Logging setup
# ------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

# Also log to file
file_handler = logging.FileHandler("inference_benchmark.log", mode="w")
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)

class XGBoostInferenceBenchmark:
    def __init__(self, model_path=None, data_path="HIGGS.csv.gz"):
        """
        Initialize the benchmark with either a trained model or train a new one
        """
        self.model_path = model_path
        self.data_path = data_path
        self.model = None
        self.test_data = None
        self.throughput_history = deque(maxlen=100)  # Keep last 100 measurements
        
        logger.info("Initializing XGBoost Inference Benchmark...")
        self._load_data()
        self._load_or_train_model()
        
    def _load_data(self):
        """Load and prepare test data"""
        logger.info("Loading HIGGS dataset...")
        df = pl.read_csv(self.data_path, has_header=False)
        
        # Use a subset for testing to have manageable memory usage
        # Take 10% of the data for inference testing
        sample_size = min(100000, len(df))
        df_sample = df.sample(n=sample_size, seed=42)
        
        y = df_sample[:, 0].to_numpy()
        X = df_sample[:, 1:].to_numpy()
        
        # Store test data
        self.test_data = X
        self.test_labels = y
        logger.info(f"Loaded {len(X)} samples for inference testing")
        
    def _load_or_train_model(self):
        """Load existing model or train a new one"""
        if self.model_path and os.path.exists(self.model_path):
            logger.info(f"Loading model from {self.model_path}")
            self.model = xgb.Booster()
            self.model.load_model(self.model_path)
        else:
            logger.info("Training new model...")
            self._train_model()
            
    def _train_model(self):
        """Train a simple XGBoost model for benchmarking"""
        # Use same data for training (in real scenario, you'd use separate training data)
        from sklearn.model_selection import train_test_split
        
        X_train, _, y_train, _ = train_test_split(
            self.test_data, self.test_labels, test_size=0.2, random_state=42
        )
        
        dtrain = xgb.DMatrix(X_train, label=y_train)
        
        params = {
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "max_depth": 6,
            "eta": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "tree_method": "hist",
            "nthread": multiprocessing.cpu_count()
        }
        
        self.model = xgb.train(params, dtrain, num_boost_round=100)
        
        # Save the model
        self.model.save_model("benchmark_model.json")
        logger.info("Model trained and saved as benchmark_model.json")
    
    def single_batch_inference(self, batch_data, batch_size_label=""):
        """Perform inference on a single batch and return timing info"""
        dmatrix = xgb.DMatrix(batch_data)
        
        start_time = time.time()
        predictions = self.model.predict(dmatrix)
        end_time = time.time()
        
        inference_time = end_time - start_time
        throughput = len(batch_data) / inference_time if inference_time > 0 else 0
        
        return {
            'batch_size': len(batch_data),
            'inference_time': inference_time,
            'throughput': throughput,
            'batch_label': batch_size_label
        }
    
    def batch_size_benchmark(self, batch_sizes=[1, 10, 100, 1000, 10000], num_iterations=10):
        """Test inference performance across different batch sizes"""
        logger.info("Starting batch size benchmark...")
        results = {}
        
        for batch_size in batch_sizes:
            if batch_size > len(self.test_data):
                continue
                
            logger.info(f"Testing batch size: {batch_size}")
            times = []
            throughputs = []
            
            for i in range(num_iterations):
                # Get random batch
                start_idx = np.random.randint(0, len(self.test_data) - batch_size)
                batch = self.test_data[start_idx:start_idx + batch_size]
                
                result = self.single_batch_inference(batch, f"batch_{batch_size}")
                times.append(result['inference_time'])
                throughputs.append(result['throughput'])
            
            results[batch_size] = {
                'avg_time': statistics.mean(times),
                'std_time': statistics.stdev(times) if len(times) > 1 else 0,
                'avg_throughput': statistics.mean(throughputs),
                'std_throughput': statistics.stdev(throughputs) if len(throughputs) > 1 else 0,
                'min_time': min(times),
                'max_time': max(times)
            }
            
            logger.info(f"Batch size {batch_size}: Avg throughput = {results[batch_size]['avg_throughput']:.2f} ± {results[batch_size]['std_throughput']:.2f} examples/sec")
        
        return results
    
    def continuous_inference_benchmark(self, duration_seconds=60, batch_size=1000, report_interval=5):
        """Continuously perform inference for a specified duration"""
        logger.info(f"Starting continuous inference for {duration_seconds} seconds...")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        total_examples = 0
        total_batches = 0
        throughputs = []
        latencies = []
        
        last_report = start_time
        
        while time.time() < end_time:
            # Get random batch
            start_idx = np.random.randint(0, len(self.test_data) - batch_size)
            batch = self.test_data[start_idx:start_idx + batch_size]
            
            result = self.single_batch_inference(batch)
            
            total_examples += result['batch_size']
            total_batches += 1
            throughputs.append(result['throughput'])
            latencies.append(result['inference_time'])
            self.throughput_history.append(result['throughput'])
            
            # Report progress
            current_time = time.time()
            if current_time - last_report >= report_interval:
                elapsed = current_time - start_time
                current_throughput = total_examples / elapsed
                logger.info(f"Progress: {elapsed:.1f}s elapsed, Current throughput: {current_throughput:.2f} examples/sec")
                last_report = current_time
        
        total_time = time.time() - start_time
        
        results = {
            'total_time': total_time,
            'total_examples': total_examples,
            'total_batches': total_batches,
            'avg_throughput': total_examples / total_time,
            'avg_latency': statistics.mean(latencies),
            'min_latency': min(latencies),
            'max_latency': max(latencies),
            'std_latency': statistics.stdev(latencies) if len(latencies) > 1 else 0,
            'throughput_std': statistics.stdev(throughputs) if len(throughputs) > 1 else 0
        }
        
        logger.info(f"Continuous inference completed:")
        logger.info(f"  Total examples processed: {results['total_examples']}")
        logger.info(f"  Average throughput: {results['avg_throughput']:.2f} examples/sec")
        logger.info(f"  Average latency: {results['avg_latency']*1000:.2f} ms")
        
        return results
    
    def concurrent_inference_benchmark(self, num_threads=4, duration_seconds=30, batch_size=1000):
        """Test concurrent inference with multiple threads"""
        logger.info(f"Starting concurrent inference with {num_threads} threads...")
        
        results_queue = queue.Queue()
        
        def worker_thread(thread_id, duration):
            thread_start = time.time()
            thread_end = thread_start + duration
            
            thread_examples = 0
            thread_throughputs = []
            
            while time.time() < thread_end:
                start_idx = np.random.randint(0, len(self.test_data) - batch_size)
                batch = self.test_data[start_idx:start_idx + batch_size]
                
                result = self.single_batch_inference(batch)
                thread_examples += result['batch_size']
                thread_throughputs.append(result['throughput'])
            
            thread_time = time.time() - thread_start
            results_queue.put({
                'thread_id': thread_id,
                'examples': thread_examples,
                'time': thread_time,
                'throughput': thread_examples / thread_time,
                'avg_batch_throughput': statistics.mean(thread_throughputs)
            })
        
        # Start threads
        threads = []
        start_time = time.time()
        
        for i in range(num_threads):
            t = threading.Thread(target=worker_thread, args=(i, duration_seconds))
            t.start()
            threads.append(t)
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        total_time = time.time() - start_time
        
        # Collect results
        thread_results = []
        total_examples = 0
        
        while not results_queue.empty():
            result = results_queue.get()
            thread_results.append(result)
            total_examples += result['examples']
        
        overall_throughput = total_examples / total_time
        
        logger.info(f"Concurrent inference completed:")
        logger.info(f"  Total examples processed: {total_examples}")
        logger.info(f"  Overall throughput: {overall_throughput:.2f} examples/sec")
        logger.info(f"  Throughput per thread: {overall_throughput/num_threads:.2f} examples/sec")
        
        for result in thread_results:
            logger.info(f"  Thread {result['thread_id']}: {result['throughput']:.2f} examples/sec")
        
        return {
            'total_examples': total_examples,
            'total_time': total_time,
            'overall_throughput': overall_throughput,
            'per_thread_throughput': overall_throughput / num_threads,
            'thread_results': thread_results
        }
    
    def stress_test(self, max_threads=None, duration_per_test=20):
        """Stress test by gradually increasing concurrent load"""
        if max_threads is None:
            max_threads = multiprocessing.cpu_count()
        
        logger.info(f"Starting stress test up to {max_threads} threads...")
        
        stress_results = {}
        
        for num_threads in [1, 2, 4, 8, min(16, max_threads), max_threads]:
            if num_threads > max_threads:
                continue
                
            logger.info(f"Testing with {num_threads} threads...")
            
            # Monitor system resources
            cpu_before = psutil.cpu_percent()
            memory_before = psutil.virtual_memory().percent
            
            result = self.concurrent_inference_benchmark(
                num_threads=num_threads, 
                duration_seconds=duration_per_test
            )
            
            cpu_after = psutil.cpu_percent()
            memory_after = psutil.virtual_memory().percent
            
            stress_results[num_threads] = {
                **result,
                'cpu_usage': (cpu_before + cpu_after) / 2,
                'memory_usage': (memory_before + memory_after) / 2
            }
        
        # Find optimal thread count
        best_threads = max(stress_results.keys(), 
                          key=lambda x: stress_results[x]['overall_throughput'])
        
        logger.info(f"Stress test completed. Optimal thread count: {best_threads}")
        logger.info(f"Best throughput: {stress_results[best_threads]['overall_throughput']:.2f} examples/sec")
        
        return stress_results
    
    def run_full_benchmark(self):
        """Run all benchmark tests"""
        logger.info("=" * 60)
        logger.info("STARTING FULL XGBOOST INFERENCE BENCHMARK")
        logger.info("=" * 60)
        
        # 1. Batch size benchmark
        logger.info("\n" + "="*40)
        logger.info("1. BATCH SIZE BENCHMARK")
        logger.info("="*40)
        batch_results = self.batch_size_benchmark()
        
        # 2. Continuous inference
        logger.info("\n" + "="*40)
        logger.info("2. CONTINUOUS INFERENCE BENCHMARK")
        logger.info("="*40)
        continuous_results = self.continuous_inference_benchmark(duration_seconds=30)
        
        # 3. Concurrent inference
        logger.info("\n" + "="*40)
        logger.info("3. CONCURRENT INFERENCE BENCHMARK")
        logger.info("="*40)
        concurrent_results = self.concurrent_inference_benchmark(num_threads=4, duration_seconds=30)
        
        # 4. Stress test
        logger.info("\n" + "="*40)
        logger.info("4. STRESS TEST")
        logger.info("="*40)
        stress_results = self.stress_test(duration_per_test=15)
        
        logger.info("\n" + "="*60)
        logger.info("BENCHMARK SUMMARY")
        logger.info("="*60)
        
        # Print summary
        logger.info(f"Best batch size throughput: {max(batch_results.values(), key=lambda x: x['avg_throughput'])['avg_throughput']:.2f} examples/sec")
        logger.info(f"Continuous inference throughput: {continuous_results['avg_throughput']:.2f} examples/sec")
        logger.info(f"Concurrent inference throughput: {concurrent_results['overall_throughput']:.2f} examples/sec")
        logger.info(f"Peak stress test throughput: {max(stress_results.values(), key=lambda x: x['overall_throughput'])['overall_throughput']:.2f} examples/sec")
        
        return {
            'batch_size_results': batch_results,
            'continuous_results': continuous_results,
            'concurrent_results': concurrent_results,
            'stress_results': stress_results
        }

def main():
    """Main function to run the benchmark"""
    # Check if model file exists from previous training
    model_path = "benchmark_model.json"
    if not os.path.exists(model_path) and os.path.exists("xg-model.py"):
        logger.info("No existing model found. Training one first...")
        # You might want to run the existing training script first
    
    # Initialize and run benchmark
    benchmark = XGBoostInferenceBenchmark(model_path=model_path if os.path.exists(model_path) else None)
    
    # Run individual tests or full benchmark
    import sys
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        
        if test_type == "batch":
            benchmark.batch_size_benchmark()
        elif test_type == "continuous":
            benchmark.continuous_inference_benchmark(duration_seconds=3600)
        elif test_type == "concurrent":
            benchmark.concurrent_inference_benchmark(num_threads=8, duration_seconds=60)
        elif test_type == "stress":
            benchmark.stress_test()
        else:
            logger.info("Available test types: batch, continuous, concurrent, stress, full")
    else:
        # Run full benchmark by default
        benchmark.run_full_benchmark()

if __name__ == "__main__":
    main()