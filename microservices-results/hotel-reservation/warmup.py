"""
Hotel Reservation Service Warmup Module
=======================================

Standalone module to warm up the hotel reservation service by sending
initial requests to all endpoints to eliminate cold start performance issues.

Usage:
    python warmup.py [HOST_URL] [REQUESTS_PER_ROUTE]

Examples:
    python warmup.py                                    # Default: localhost:8080, 20 requests per route
    python warmup.py http://192.5.87.25:30001         # Custom host, 20 requests per route  
    python warmup.py http://192.5.87.25:30001 10      # Custom host, 10 requests per route

Environment Variables:
    WARMUP_REQUESTS=N    # Number of requests per route (default: 20)
    HOST=url            # Target host URL (default: http://localhost:8080)
"""

import requests
from requests.adapters import HTTPAdapter
import random
import time
import sys
import os

def get_user():
    """Generate random user credentials for testing."""
    user_id = random.randint(0, 500)
    user_name = 'Cornell_' + str(user_id)
    password = ""
    for i in range(0, 10):
        password = password + str(user_id)
    return user_name, password

def perform_warmup(host_url, requests_per_route=20):
    """
    Perform warm-up requests to all routes to eliminate cold start issues.
    
    Args:
        host_url (str): Base URL of the service
        requests_per_route (int): Number of requests to send to each route
    """
    print(f"🔥 Starting warm-up phase for: {host_url}")
    print(f"📊 Sending {requests_per_route} requests per route...")
    
    session = requests.Session()
    session.mount('http://', HTTPAdapter(max_retries=3))
    session.mount('https://', HTTPAdapter(max_retries=3))
    
    warmup_count = 0
    total_warmup_requests = requests_per_route * 4  # 4 different routes
    
    try:
        # Warm-up search_hotel route
        print("🏨 Warming up search_hotel route...")
        for i in range(requests_per_route):
            in_date = random.randint(9, 23)
            out_date = random.randint(in_date+1, 24)
            
            if in_date <= 9:
                in_date = "2015-04-0" + str(in_date)
            else:
                in_date = "2015-04-" + str(in_date)
            
            if out_date <= 9:
                out_date = "2015-04-0" + str(out_date)
            else:
                out_date = "2015-04-" + str(out_date)
            
            lat = 38.0235 + (random.randint(0, 481) - 240.5)/1000.0
            lon = -122.095 + (random.randint(0, 325) - 157.0)/1000.0
            
            path = f'{host_url}/hotels?inDate={in_date}&outDate={out_date}&lat={lat}&lon={lon}'
            
            try:
                response = session.get(path, timeout=30)
                warmup_count += 1
                if warmup_count % 5 == 0:
                    print(f"  Progress: {warmup_count}/{total_warmup_requests} ({warmup_count/total_warmup_requests*100:.1f}%)")
            except Exception as e:
                print(f"  Warning: Request failed - {e}")
        
        # Warm-up recommend route
        print("💡 Warming up recommend route...")
        for i in range(requests_per_route):
            coin = random.random()
            if coin < 0.33:
                req_param = 'dis'
            elif coin < 0.66:
                req_param = 'rate'
            else:
                req_param = 'price'
            
            lat = 38.0235 + (random.randint(0, 481) - 240.5)/1000.0
            lon = -122.095 + (random.randint(0, 325) - 157.0)/1000.0
            
            path = f'{host_url}/recommendations?require={req_param}&lat={lat}&lon={lon}'
            
            try:
                response = session.get(path, timeout=30)
                warmup_count += 1
                if warmup_count % 5 == 0:
                    print(f"  Progress: {warmup_count}/{total_warmup_requests} ({warmup_count/total_warmup_requests*100:.1f}%)")
            except Exception as e:
                print(f"  Warning: Request failed - {e}")
        
        # Warm-up reserve route
        print("🎫 Warming up reserve route...")
        for i in range(requests_per_route):
            in_date = random.randint(9, 23)
            out_date = in_date + random.randint(1, 5)
            
            if in_date <= 9:
                in_date = "2015-04-0" + str(in_date)
            else:
                in_date = "2015-04-" + str(in_date)
            
            if out_date <= 9:
                out_date = "2015-04-0" + str(out_date)
            else:
                out_date = "2015-04-" + str(out_date)
            
            lat = 38.0235 + (random.randint(0, 481) - 240.5)/1000.0
            lon = -122.095 + (random.randint(0, 325) - 157.0)/1000.0
            
            hotel_id = str(random.randint(1, 80))
            user_name, password = get_user()
            num_room = 1
            
            path = f'{host_url}/reservation?inDate={in_date}&outDate={out_date}&lat={lat}&lon={lon}&hotelId={hotel_id}&customerName={user_name}&username={user_name}&password={password}&number={num_room}'
            
            try:
                response = session.post(path, timeout=30)
                warmup_count += 1
                if warmup_count % 5 == 0:
                    print(f"  Progress: {warmup_count}/{total_warmup_requests} ({warmup_count/total_warmup_requests*100:.1f}%)")
            except Exception as e:
                print(f"  Warning: Request failed - {e}")
        
        # Warm-up user_login route
        print("👤 Warming up user_login route...")
        for i in range(requests_per_route):
            user_name, password = get_user()
            path = f'{host_url}/user?username={user_name}&password={password}'
            
            try:
                response = session.get(path, timeout=30)
                warmup_count += 1
                if warmup_count % 5 == 0:
                    print(f"  Progress: {warmup_count}/{total_warmup_requests} ({warmup_count/total_warmup_requests*100:.1f}%)")
            except Exception as e:
                print(f"  Warning: Request failed - {e}")
        
        print(f"\n🎯 Warm-up completed!")
        print(f"✅ Successfully sent {warmup_count}/{total_warmup_requests} requests")
        print(f"🚀 Service should now be warmed up and ready for load testing")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Warm-up phase encountered an error: {e}")
        print("⚠️  Service may not be fully warmed up")
        return False
    
    finally:
        session.close()

def main():
    """Main function to run warmup with command line arguments."""
    
    # Default values
    default_host = "http://localhost:8080"
    default_requests = 1000
    
    # Get configuration from command line or environment variables
    host_url = default_host
    requests_per_route = default_requests
    
    # Command line arguments
    if len(sys.argv) > 1:
        host_url = sys.argv[1]
    
    if len(sys.argv) > 2:
        try:
            requests_per_route = int(sys.argv[2])
        except ValueError:
            print(f"Warning: Invalid requests_per_route '{sys.argv[2]}', using default {default_requests}")
    
    # Environment variables override
    if os.environ.get('HOST'):
        host_url = os.environ.get('HOST')
    
    if os.environ.get('WARMUP_REQUESTS'):
        try:
            requests_per_route = int(os.environ.get('WARMUP_REQUESTS'))
        except ValueError:
            print(f"Warning: Invalid WARMUP_REQUESTS env var, using {requests_per_route}")
    
    print("=" * 60)
    print("🔥 HOTEL RESERVATION SERVICE WARMUP")
    print("=" * 60)
    print(f"Target URL: {host_url}")
    print(f"Requests per route: {requests_per_route}")
    print(f"Total requests: {requests_per_route * 4}")
    print("=" * 60)
    
    start_time = time.time()
    success = perform_warmup(host_url, requests_per_route)
    end_time = time.time()
    
    print("=" * 60)
    print(f"⏱️  Total warmup time: {end_time - start_time:.2f} seconds")
    
    if success:
        print("🎉 Warmup completed successfully!")
        return 0
    else:
        print("💥 Warmup completed with errors!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)