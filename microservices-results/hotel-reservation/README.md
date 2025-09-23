# Hotel Reservation Load Testing

This repository contains load testing scripts for the hotel reservation service, with separate warmup functionality to eliminate cold start performance issues.

## Files

- **`locustfile.py`** - Main Locust load test script (clean, without warmup)
- **`warmup.py`** - Standalone warmup module to prepare the service
- **`test_warmup.sh`** - Automated script that runs warmup + load test
- **`search_hotel_analysis.py`** - Performance analysis tool

## Quick Start

### Option 1: Automated Test with Warmup
```bash
# Run with defaults (20 warmup requests per route)
./test_warmup.sh

# Run with custom settings  
WARMUP_REQUESTS=10 HOST=http://192.5.87.25:30001 ./test_warmup.sh

# Run without warmup
ENABLE_WARMUP=false ./test_warmup.sh
```

### Option 2: Manual Warmup + Load Test
```bash
# Step 1: Warm up the service
python3 warmup.py http://192.5.87.25:30001 20

# Step 2: Run load test
python3 -m locust -f locustfile.py --host=http://192.5.87.25:30001 --headless --users=100 --spawn-rate=10 --run-time=900s
```

### Option 3: Warmup Only (for testing)
```bash
# Test warmup with just 2 requests per route
python3 warmup.py http://192.5.87.25:30001 2

# Use environment variables
WARMUP_REQUESTS=5 HOST=http://192.5.87.25:30001 python3 warmup.py
```

## Performance Impact

Based on analysis of cold start issues:

**Without Warmup:**
- First 20 requests: **2,515ms average response time** 
- Performance gradually improves over 3+ minutes
- 52% performance penalty initially

**With Warmup:**
- Eliminates 2.5+ second initial response times
- Achieves consistent ~50ms response times from start
- Prevents 8+ second worst-case scenarios

## Configuration

### Environment Variables
- `HOST` - Target service URL (default: http://localhost:8080)
- `WARMUP_REQUESTS` - Requests per route during warmup (default: 20)
- `ENABLE_WARMUP` - Enable/disable warmup phase (default: true)

### Load Test Parameters
- **Users**: 100 concurrent users
- **Spawn Rate**: 10 users/second  
- **Duration**: 15 minutes (900 seconds)
- **Target RPS**: 100 requests/second total

## Routes Tested

1. **search_hotel** (60% of traffic) - Hotel search by location/dates
2. **recommend** (39% of traffic) - Hotel recommendations
3. **reserve** (0.5% of traffic) - Make reservations  
4. **user_login** (0.5% of traffic) - User authentication

## Output Files

- `latency_per_route.csv` - Detailed request logs
- `loadtest_report.html` - Locust HTML report
- `loadtest_results_*.csv` - Locust CSV results
- `search_hotel_performance_analysis.png` - Performance analysis charts

## Analysis

Run performance analysis on results:
```bash
python3 search_hotel_analysis.py
python3 cdf_analysis.py latency_per_route.csv
```