#!/bin/bash

# Hotel Reservation Load Test with Separate Warmup
# =================================================

# Set default values if not provided
export WARMUP_REQUESTS=${WARMUP_REQUESTS:-20}
export ENABLE_WARMUP=${ENABLE_WARMUP:-true}
export HOST=${HOST:-http://192.5.87.25:30001}

echo "🚀 Starting Hotel Reservation Load Test"
echo "========================================"
echo "   Host: $HOST"
echo "   Warm-up enabled: $ENABLE_WARMUP"
echo "   Warm-up requests per route: $WARMUP_REQUESTS"
echo ""

# Step 1: Run warmup if enabled
if [ "$ENABLE_WARMUP" = "true" ]; then
    echo "🔥 Step 1: Running service warmup..."
    python3 warmup.py "$HOST" "$WARMUP_REQUESTS"
    warmup_exit_code=$?
    
    if [ $warmup_exit_code -eq 0 ]; then
        echo "✅ Warmup completed successfully!"
    else
        echo "⚠️  Warmup completed with errors, continuing with load test..."
    fi
    echo ""
else
    echo "🚫 Warmup disabled - skipping to load test"
    echo ""
fi

# Step 2: Run the actual load test
echo "📊 Step 2: Running load test..."
python3 -m locust -f locustfile.py \
       --host="$HOST" \
       --users=100 \
       --spawn-rate=10 \
       --run-time=900s \
       --html=loadtest_report.html \
       --csv=loadtest_results \
       --headless

echo ""
echo "🎉 Load test completed!"
echo "📊 Results saved to:"
echo "   - HTML Report: loadtest_report.html"
echo "   - CSV Results: loadtest_results_*.csv"
echo "   - Detailed logs: latency_per_route.csv"