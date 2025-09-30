import time
import polars as pl
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import numpy as np
import multiprocessing
import logging
import zipfile
import os
import csv
from datetime import datetime
import signal
import sys

# ------------------------
# Global variables for graceful shutdown
# ------------------------
running = True

def signal_handler(sig, frame):
    global running
    print("\nReceived shutdown signal. Stopping gracefully...")
    logging.info("Received shutdown signal. Stopping gracefully...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ------------------------
# Logging setup
# ------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="xgboost_performance.log",
    filemode="a"  # Changed to append mode for continuous logging
)

# ------------------------
# CSV files for throughput logging
# ------------------------
training_csv = "training_throughput.csv"
inference_csv = "inference_throughput.csv"

def initialize_csv_files():
    """Initialize CSV files with headers if they don't exist"""
    if not os.path.exists(training_csv):
        with open(training_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'training_time_sec', 'training_throughput_examples_per_sec', 'num_examples', 'num_rounds'])
    
    if not os.path.exists(inference_csv):
        with open(inference_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'inference_time_sec', 'inference_throughput_examples_per_sec', 'num_examples', 'accuracy'])

def log_training_throughput(timestamp, train_time, throughput, num_examples, num_rounds):
    """Log training throughput to CSV"""
    with open(training_csv, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, train_time, throughput, num_examples, num_rounds])

def log_inference_throughput(timestamp, inf_time, throughput, num_examples, accuracy):
    """Log inference throughput to CSV"""
    with open(inference_csv, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, inf_time, throughput, num_examples, accuracy])

# ------------------------
# Unzip dataset if needed
# ------------------------
def unzip_dataset():
    """Unzip the HIGGS dataset if it doesn't exist"""
    if not os.path.exists("HIGGS.csv") and not os.path.exists("HIGGS.csv.gz"):
        if os.path.exists("higgs.zip"):
            logging.info("Unzipping higgs.zip...")
            print("Unzipping higgs.zip...")
            with zipfile.ZipFile("higgs.zip", 'r') as zip_ref:
                zip_ref.extractall(".")
            logging.info("Dataset unzipped successfully")
            print("Dataset unzipped successfully")
        else:
            logging.error("No higgs.zip file found!")
            print("Error: No higgs.zip file found!")
            sys.exit(1)
    else:
        logging.info("Dataset already exists")
        print("Dataset already exists")

def load_and_prepare_data():
    """Load and prepare the dataset"""
    logging.info("Loading HIGGS dataset...")
    print("Loading HIGGS dataset...")
    
    # Try to load from different possible file names
    dataset_file = None
    if os.path.exists("HIGGS.csv.gz"):
        dataset_file = "HIGGS.csv.gz"
    elif os.path.exists("HIGGS.csv"):
        dataset_file = "HIGGS.csv"
    else:
        logging.error("No HIGGS dataset found!")
        print("Error: No HIGGS dataset found!")
        sys.exit(1)
    
    df = pl.read_csv(dataset_file, has_header=False)
    y = df[:, 0].to_numpy()
    X = df[:, 1:].to_numpy()
    
    logging.info("Splitting train/test...")
    print("Splitting train/test...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    return X_train, X_test, y_train, y_test

def run_training(X_train, y_train, iteration):
    """Run one training iteration and return throughput metrics"""
    logging.info(f"Starting training iteration {iteration}...")
    print(f"Starting training iteration {iteration}...")
    
    # Create DMatrix
    dtrain = xgb.DMatrix(X_train, label=y_train)
    
    # Parameters for CPU training
    params = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "max_depth": 10,
        "eta": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "tree_method": "hist",   # CPU histogram algorithm
        "nthread": multiprocessing.cpu_count()  # use all CPU cores
    }
    
    num_round = 500
    
    # Measure training throughput
    start_train = time.time()
    bst = xgb.train(params, dtrain, num_boost_round=num_round)
    end_train = time.time()
    
    train_time = end_train - start_train
    examples = dtrain.num_row() * num_round
    train_throughput = examples / train_time
    
    timestamp = datetime.now().isoformat()
    
    logging.info(f"Training iteration {iteration} completed")
    logging.info(f"Training time: {train_time:.2f} sec")
    logging.info(f"Training throughput: {train_throughput:.2f} examples/sec on {params['nthread']} threads")
    
    print(f"Training iteration {iteration} completed - Throughput: {train_throughput:.2f} examples/sec")
    
    # Log to CSV
    log_training_throughput(timestamp, train_time, train_throughput, dtrain.num_row(), num_round)
    
    return bst, train_throughput

def run_inference(bst, X_test, y_test, iteration):
    """Run one inference iteration and return throughput metrics"""
    logging.info(f"Starting inference iteration {iteration}...")
    print(f"Starting inference iteration {iteration}...")
    
    dtest = xgb.DMatrix(X_test, label=y_test)
    batch_size = 100000
    num_batches = int(np.ceil(len(X_test) / batch_size))
    
    # Measure inference throughput
    start_inf = time.time()
    predictions = []
    for i in range(num_batches):
        batch = X_test[i*batch_size:(i+1)*batch_size]
        batch_pred = bst.predict(xgb.DMatrix(batch))
        predictions.extend(batch_pred)
    end_inf = time.time()
    
    inf_time = end_inf - start_inf
    inf_throughput = len(X_test) / inf_time
    
    # Calculate accuracy
    y_pred = (np.array(predictions) > 0.5).astype(int)
    acc = accuracy_score(y_test, y_pred)
    
    timestamp = datetime.now().isoformat()
    
    logging.info(f"Inference iteration {iteration} completed")
    logging.info(f"Inference time: {inf_time:.2f} sec")
    logging.info(f"Inference throughput: {inf_throughput:.2f} examples/sec")
    logging.info(f"Test Accuracy: {acc:.4f}")
    
    print(f"Inference iteration {iteration} completed - Throughput: {inf_throughput:.2f} examples/sec, Accuracy: {acc:.4f}")
    
    # Log to CSV
    log_inference_throughput(timestamp, inf_time, inf_throughput, len(X_test), acc)
    
    return inf_throughput

def main():
    """Main execution loop"""
    global running
    
    print("Starting XGBoost continuous training and inference benchmark...")
    logging.info("Starting XGBoost continuous training and inference benchmark...")
    
    # Step 1: Unzip dataset
    unzip_dataset()
    
    # Step 2: Initialize CSV files
    initialize_csv_files()
    
    # Step 3: Load and prepare data (once)
    X_train, X_test, y_train, y_test = load_and_prepare_data()
    
    # Step 4: Continuous loop
    iteration = 1
    while running:
        try:
            print(f"\n--- Starting Iteration {iteration} ---")
            logging.info(f"Starting iteration {iteration}")
            
            # Run training
            bst, train_throughput = run_training(X_train, y_train, iteration)
            
            if not running:
                break
                
            # Run inference
            inf_throughput = run_inference(bst, X_test, y_test, iteration)
            
            print(f"--- Iteration {iteration} Complete ---")
            print(f"Training Throughput: {train_throughput:.2f} examples/sec")
            print(f"Inference Throughput: {inf_throughput:.2f} examples/sec")
            
            iteration += 1
            
            # Small pause between iterations
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received. Stopping...")
            break
        except Exception as e:
            logging.error(f"Error in iteration {iteration}: {str(e)}")
            print(f"Error in iteration {iteration}: {str(e)}")
            time.sleep(5)  # Wait before retrying
    
    print("Benchmark stopped. Data saved to training_throughput.csv and inference_throughput.csv")
    logging.info("Benchmark stopped. Data saved to CSV files.")

if __name__ == "__main__":
    main()
