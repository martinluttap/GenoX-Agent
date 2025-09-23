"""
Hotel Reservation Load Test (Optimized for Consistent Performance)
================================================================

This script sends 100 requests per second using 100 users for 15 minutes.
Optimized for minimal latency variation and consistent performance measurement.

Key Optimizations:
- Connection pooling and session reuse
- Consistent wait times with constant pacing
- Request timeouts to prevent hanging requests
- Gradual ramp-up to reduce system shock
- Enhanced error handling and monitoring

Usage:
    locust -f locustfile.py --host http://your-custom-url.com
"""

from locust import HttpUser, LoadTestShape, task, events, between, constant_pacing
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timedelta, date
from pathlib import Path
import random
import time
import logging
import uuid
import json
import locust.stats
import requests
import csv
import os

# Locust configuration for more stable performance
locust.stats.CONSOLE_STATS_INTERVAL_SEC = 600
locust.stats.HISTORY_STATS_INTERVAL_SEC = 60
locust.stats.CSV_STATS_INTERVAL_SEC = 60
locust.stats.CSV_STATS_FLUSH_INTERVAL_SEC = 60
locust.stats.CURRENT_RESPONSE_TIME_PERCENTILE_WINDOW = 60
locust.stats.PERCENTILES_TO_REPORT = [0.50, 0.80, 0.90, 0.95, 0.98, 0.99, 0.995, 0.999, 1.0]

LOG_STATISTICS_IN_HALF_MINUTE_CHUNKS = (1==0)
RETRY_ON_ERROR = True
MAX_RETRIES = 3  # Reduced from 10 for faster failure handling

# Request timeout configuration
CONNECT_TIMEOUT = 5    # Connection timeout in seconds
READ_TIMEOUT = 30      # Read timeout in seconds

# Load test configuration
TARGET_RPS = 100
TEST_DURATION_SECONDS = 900  # 15 minutes
NUM_USERS = 100
random.seed(42)  # Fixed seed for reproducible results
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

request_log_file = open('request.log', 'a')

# CSV logging setup - will only log after all users are spawned
csv_log_file = open('latency_per_route.csv', 'w', newline='')
csv_writer = csv.writer(csv_log_file)
csv_writer.writerow(['timestamp', 'route_name', 'url', 'method', 'response_time_ms', 'status_code', 'success'])
# Note: Data logging starts only AFTER all 100 users are spawned (no ramp-up data)
csv_log_file.flush()

def get_user():
    user_id = random.randint(0, 500)
    user_name = 'Cornell_' + str(user_id)
    password = str(user_id) * 10  # More efficient string creation
    return user_name, password

spawning_complete = False
ramp_up_complete_time = None
steady_state_requests_logged = 0

@events.spawning_complete.add_listener
def on_spawning_complete(user_count, **kwargs):
    global spawning_complete, ramp_up_complete_time
    
    # Add a brief delay to ensure all users are fully initialized
    time.sleep(5)  # 5 second buffer after spawning completes
    
    spawning_complete = True
    ramp_up_complete_time = time.time()
    
    print(f"🎯 Ramp-up complete! All {user_count} users spawned and initialized.")
    print(f"⏱️  Waiting 5 seconds for system to stabilize...")
    print(f"📊 Now starting CSV logging for CLEAN steady-state performance data...")
    print(f"🚫 NO ramp-up artifacts will be recorded!")
    
    # Add a clear marker row to CSV indicating when steady-state logging started
    csv_writer.writerow([
        datetime.now().isoformat(), 
        'STEADY_STATE_START', 
        f'All_{user_count}_users_active_and_stabilized', 
        'MARKER', 
        0, 
        'LOGGING_STARTED', 
        True
    ])
    csv_log_file.flush()

def get_name_suffix(name):
    if LOG_STATISTICS_IN_HALF_MINUTE_CHUNKS:
        now = datetime.now()
        now = datetime(now.year, now.month, now.day, now.hour, now.minute, 0 if now.second < 30 else 30, 0)
        now_as_timestamp = int(now.timestamp())
        return f"{name}@{now_as_timestamp}"
    else:
        return name

class HotelReservationUser(HttpUser):
    host = "http://localhost:8080"
    
    # Use constant pacing for consistent request timing (1 RPS per user)
    wait_time = constant_pacing(1.0)  # Exactly 1 request per second per user
    
    def on_start(self):
        """Initialize connection pooling and session optimization"""
        # Configure timeouts
        self.client.timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)
        
        # Disable SSL verification for performance (if using HTTPS)
        self.client.verify = False
        
        # Configure retry strategy (minimal retries for faster failure)
        retry_strategy = Retry(
            total=1,  # Only 1 retry
            backoff_factor=0.1,  # Quick backoff
            status_forcelist=[500, 502, 503, 504],  # Only retry server errors
        )
        
        # Configure HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=10,    # Number of connection pools
            pool_maxsize=20,       # Max connections per pool
            max_retries=retry_strategy,
            pool_block=False       # Don't block on pool exhaustion
        )
        
        # Mount adapters for both HTTP and HTTPS
        self.client.mount("http://", adapter)
        self.client.mount("https://", adapter)
        
        # Set keep-alive headers for connection reuse
        self.client.headers.update({
            'Connection': 'keep-alive',
            'Keep-Alive': 'timeout=60, max=1000'
        })
        
        logging.info(f"User {id(self)} initialized with optimized connection settings")

    @events.request.add_listener
    def on_request(name, request_type, response_time, response_length, response, context, exception, start_time, url, **kwargs):
        # CRITICAL: Only log requests AFTER all 100 users are spawned AND stabilization period is complete
        if not spawning_complete or ramp_up_complete_time is None:
            # Skip all logging during ramp-up phase
            return
            
        current_time = time.time()
        if current_time < ramp_up_complete_time:
            # Still in stabilization period, skip logging
            return
            
        # Log slow requests for debugging
        if response_time > 2000:  # Log requests slower than 2 seconds
            logging.warning(f"Slow request detected: {name} took {response_time:.2f}ms")
            
        # Original JSON logging (only steady-state data)
        request_log_file.write(json.dumps({
            'time': time.perf_counter(),
            'latency': response_time / 1e3,
            'context': context,
        }) + '\n')
        
        # CSV logging (only steady-state data)
        timestamp = datetime.now().isoformat()
        route_name = name if name else 'unknown'
        method = request_type if request_type else 'unknown'
        response_time_ms = response_time
        status_code = response.status_code if response and hasattr(response, 'status_code') else 'N/A'
        success = exception is None
        
        csv_writer.writerow([timestamp, route_name, url, method, response_time_ms, status_code, success])
        csv_log_file.flush()
        
        # Track steady-state logging progress
        global steady_state_requests_logged
        steady_state_requests_logged += 1
        if steady_state_requests_logged % 100 == 0:  # Log every 100 requests
            print(f"✓ Steady-state requests logged: {steady_state_requests_logged}")

    def make_request(self, method, path, name, context, **kwargs):
        """Optimized request method with error handling and monitoring"""
        try:
            start_time = time.time()
            
            if method.upper() == 'GET':
                response = self.client.get(
                    path, 
                    name=get_name_suffix(name),
                    context=context,
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                    stream=False,  # Don't stream responses for faster processing
                    **kwargs
                )
            elif method.upper() == 'POST':
                response = self.client.post(
                    path,
                    name=get_name_suffix(name),
                    context=context,
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                    stream=False,
                    **kwargs
                )
            
            end_time = time.time()
            
            # Log connection reuse for monitoring
            if hasattr(response, 'connection') and hasattr(response.connection, 'sock'):
                logging.debug(f"Request {name} reused connection: {response.connection.sock}")
            
            return response
            
        except requests.exceptions.Timeout as e:
            logging.warning(f"Request timeout for {name}: {str(e)}")
            raise
        except requests.exceptions.ConnectionError as e:
            logging.warning(f"Connection error for {name}: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error for {name}: {str(e)}")
            raise

    @task(25)  # Equal weights - 25% of traffic each
    def search_hotel(self):
        in_date = random.randint(9, 23)
        out_date = random.randint(in_date+1, 24)

        in_date_str = f"2015-04-{in_date:02d}"
        out_date_str = f"2015-04-{out_date:02d}"

        lat = 38.0235 + (random.randint(0, 481) - 240.5)/1000.0
        lon = -122.095 + (random.randint(0, 325) - 157.0)/1000.0

        path = f'/hotels?inDate={in_date_str}&outDate={out_date_str}&lat={lat}&lon={lon}'

        self.make_request('GET', path, 'search_hotel', {'type': 'search_hotel'})

    @task(25)  # Equal weights - 25% of traffic each
    def recommend(self):
        req_param = 'price'
        lat = 38.0235
        lon = -122.095

        path = f'/recommendations?require={req_param}&lat={lat}&lon={lon}'

        self.make_request('GET', path, 'recommend', {'type': 'recommend'})

    @task(25)  # Equal weights - 25% of traffic each
    def reserve(self):
        # Vary hotel IDs to reduce database lock contention
        hotel_id = str(random.randint(1, 20))  # Spread across 20 hotels instead of 1
        
        # Vary dates to reduce inventory conflicts
        base_date = random.randint(15, 25)
        in_date = f"2015-04-{base_date}"
        out_date = f"2015-04-{base_date + random.randint(1, 3)}"
        
        # Vary locations slightly
        lat = 38.0235 + (random.randint(0, 100) - 50) / 10000.0
        lon = -122.095 + (random.randint(0, 100) - 50) / 10000.0
        
        user_name, password = get_user()
        num_room = random.randint(1, 2)  # Vary room count

        path = f'/reservation?inDate={in_date}&outDate={out_date}&lat={lat}&lon={lon}&hotelId={hotel_id}&customerName={user_name}&username={user_name}&password={password}&number={num_room}'

        # Use longer timeout for reservation requests
        try:
            response = self.client.post(
                path, 
                name=get_name_suffix('reserve'),
                context={'type': 'reserve'},
                timeout=(CONNECT_TIMEOUT, 60),  # Extended timeout for complex operations
                catch_response=True
            )
            
            # Handle specific reservation errors
            if response.status_code == 409:  # Conflict - likely booking conflict
                response.success()  # Don't mark as failure, it's expected
                logging.info(f"Booking conflict for hotel {hotel_id} on {in_date}")
            elif response.status_code >= 500:
                response.failure(f"Server error: {response.status_code}")
                
        except requests.exceptions.Timeout:
            logging.warning(f"Reservation timeout for hotel {hotel_id}")
            # Don't re-raise, let Locust handle it

    @task(25)  # Equal weights - 25% of traffic each
    def user_login(self):
        user_name = "Cornell_123"
        password = "123123123123123123123123"
        path = f'/user?username={user_name}&password={password}'

        self.make_request('GET', path, 'user_login', {'type': 'user_login'})

class OptimizedLoadShape(LoadTestShape):
    """
    Optimized load shape with gradual ramp-up to reduce system shock
    """
    stages = [
        # Gradual ramp-up over 100 seconds
        {"duration": 20, "users": 20, "spawn_rate": 1},   # 20 users in 20s
        {"duration": 40, "users": 40, "spawn_rate": 1},   # 40 users in 40s  
        {"duration": 60, "users": 60, "spawn_rate": 1},   # 60 users in 60s
        {"duration": 80, "users": 80, "spawn_rate": 1},   # 80 users in 80s
        {"duration": 100, "users": 100, "spawn_rate": 1}, # 100 users in 100s
        {"duration": 900, "users": 100, "spawn_rate": 1}, # Hold steady for remaining time
    ]

    def tick(self):
        run_time = self.get_run_time()
        
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        
        return None