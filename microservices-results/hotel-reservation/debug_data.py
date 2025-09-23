#!/usr/bin/env python3
"""
Debug script to check what data the route statistics is seeing vs CDF analysis
"""

import pandas as pd
import numpy as np
import sys

def debug_data_reading(filepath):
    """Debug function to see what data we're getting"""
    
    print("=== DEBUGGING DATA READING ===")
    
    # Read with same logic as route_statistics.py
    try:
        try:
            df = pd.read_csv(filepath)
        except pd.errors.ParserError as e:
            print(f"Parser error: {e}")
            try:
                df = pd.read_csv(filepath, on_bad_lines='skip')
            except TypeError:
                df = pd.read_csv(filepath, error_bad_lines=False, warn_bad_lines=True)
        
        print(f"Total records loaded: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        
        # Filter successful requests
        if 'success' in df.columns:
            df_success = df[df['success'] == True].copy()
            print(f"Successful requests: {len(df_success)}")
        else:
            df_success = df.copy()
        
        # Now apply the same filtering as route_statistics.py
        df_clean = df_success[
            (df_success['route_name'] != 'STEADY_STATE_START') & 
            (pd.to_numeric(df_success['response_time_ms'], errors='coerce').notna())
        ].copy()
        
        print(f"After filtering markers and invalid response times: {len(df_clean)}")
        
        # Convert to numeric
        df_clean['response_time_ms'] = pd.to_numeric(df_clean['response_time_ms'])
        
        print(f"Response time range: {df_clean['response_time_ms'].min():.2f} - {df_clean['response_time_ms'].max():.2f} ms")
        
        # Check high response times
        high_latency = df_clean[df_clean['response_time_ms'] > 1000]
        print(f"Records with >1000ms response time: {len(high_latency)}")
        
        if len(high_latency) > 0:
            print(f"High latency routes: {high_latency['route_name'].unique()}")
            print(f"Max response time per route:")
            for route in df_clean['route_name'].unique():
                route_data = df_clean[df_clean['route_name'] == route]
                max_time = route_data['response_time_ms'].max()
                count_high = len(route_data[route_data['response_time_ms'] > 1000])
                print(f"  {route}: max={max_time:.1f}ms, count>1000ms={count_high}")
        
        # Show overall stats by route
        print(f"\nRoute summary:")
        route_summary = df_clean.groupby('route_name')['response_time_ms'].agg(['count', 'mean', 'max']).round(2)
        print(route_summary)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_data.py <csv_file>")
        sys.exit(1)
    
    debug_data_reading(sys.argv[1])