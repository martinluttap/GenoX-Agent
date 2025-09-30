#!/bin/bash

# XGBoost Inference Benchmark Runner
echo "========================================"
echo "XGBoost Inference Throughput Benchmark"
echo "========================================"

# Install dependencies if needed
echo "Checking dependencies..."
pip install -r requirements.txt > /dev/null 2>&1

echo ""
echo "Available benchmark modes:"
echo "1. batch     - Test different batch sizes"
echo "2. continuous - Continuous inference for specified duration"  
echo "3. concurrent - Multi-threaded inference test"
echo "4. stress    - Stress test with increasing thread count"
echo "5. full      - Run all benchmarks (default)"
echo ""

# Check if argument provided
if [ $# -eq 0 ]; then
    echo "Running full benchmark suite..."
    python inference_benchmark.py
else
    case $1 in
        "batch")
            echo "Running batch size benchmark..."
            python inference_benchmark.py batch
            ;;
        "continuous")
            echo "Running continuous inference benchmark..."
            python inference_benchmark.py continuous
            ;;
        "concurrent")
            echo "Running concurrent inference benchmark..."
            python inference_benchmark.py concurrent
            ;;
        "stress")
            echo "Running stress test..."
            python inference_benchmark.py stress
            ;;
        "full")
            echo "Running full benchmark suite..."
            python inference_benchmark.py
            ;;
        *)
            echo "Invalid option. Available: batch, continuous, concurrent, stress, full"
            exit 1
            ;;
    esac
fi

echo ""
echo "Benchmark completed! Check inference_benchmark.log for detailed results."