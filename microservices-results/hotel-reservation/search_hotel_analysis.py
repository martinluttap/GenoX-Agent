#!/usr/bin/env python3
"""
Analysis script to investigate search_hotel route performance issues,
particularly focusing on initial requests taking too long.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import sys

def analyze_search_hotel_performance():
    # Read the latency data
    df = pd.read_csv('latency_per_route.csv')
    
    # Filter for search_hotel requests only
    search_hotel_df = df[df['route_name'] == 'search_hotel'].copy()
    
    print(f"Total search_hotel requests: {len(search_hotel_df)}")
    
    # Convert timestamp to datetime for analysis
    search_hotel_df['timestamp'] = pd.to_datetime(search_hotel_df['timestamp'])
    
    # Sort by timestamp to analyze chronological order
    search_hotel_df = search_hotel_df.sort_values('timestamp').reset_index(drop=True)
    
    # Add request order for each search_hotel request
    search_hotel_df['request_order'] = range(1, len(search_hotel_df) + 1)
    
    # Basic statistics
    print("\n" + "="*60)
    print("SEARCH_HOTEL PERFORMANCE ANALYSIS")
    print("="*60)
    
    print(f"Mean response time: {search_hotel_df['response_time_ms'].mean():.2f} ms")
    print(f"Median response time: {search_hotel_df['response_time_ms'].median():.2f} ms")
    print(f"95th percentile: {search_hotel_df['response_time_ms'].quantile(0.95):.2f} ms")
    print(f"99th percentile: {search_hotel_df['response_time_ms'].quantile(0.99):.2f} ms")
    print(f"Max response time: {search_hotel_df['response_time_ms'].max():.2f} ms")
    
    # Analyze first N requests vs later requests
    first_n = 20  # Look at first 20 requests
    
    first_requests = search_hotel_df.head(first_n)
    later_requests = search_hotel_df.iloc[first_n:]
    
    print(f"\n" + "="*60)
    print(f"COLD START ANALYSIS (First {first_n} requests vs Later)")
    print("="*60)
    
    if len(first_requests) > 0:
        print(f"First {len(first_requests)} requests:")
        print(f"  Mean: {first_requests['response_time_ms'].mean():.2f} ms")
        print(f"  Median: {first_requests['response_time_ms'].median():.2f} ms")
        print(f"  Max: {first_requests['response_time_ms'].max():.2f} ms")
        print(f"  Min: {first_requests['response_time_ms'].min():.2f} ms")
    
    if len(later_requests) > 0:
        print(f"\nLater {len(later_requests)} requests:")
        print(f"  Mean: {later_requests['response_time_ms'].mean():.2f} ms")
        print(f"  Median: {later_requests['response_time_ms'].median():.2f} ms")
        print(f"  Max: {later_requests['response_time_ms'].max():.2f} ms")
        print(f"  Min: {later_requests['response_time_ms'].min():.2f} ms")
        
        if len(first_requests) > 0:
            improvement = ((first_requests['response_time_ms'].mean() - 
                          later_requests['response_time_ms'].mean()) / 
                         first_requests['response_time_ms'].mean()) * 100
            print(f"\nPerformance improvement after initial requests: {improvement:.1f}%")
    
    # Time-based analysis - look at performance over time windows
    print(f"\n" + "="*60)
    print("TIME-BASED PERFORMANCE ANALYSIS")
    print("="*60)
    
    # Group by time windows (e.g., every 30 seconds)
    search_hotel_df['time_window'] = search_hotel_df['timestamp'].dt.floor('30S')
    time_analysis = search_hotel_df.groupby('time_window')['response_time_ms'].agg([
        'count', 'mean', 'median', 'max', 'min'
    ]).reset_index()
    
    print("Performance by 30-second windows:")
    print(time_analysis.head(10).to_string(index=False))
    
    # Show requests with highest latency
    print(f"\n" + "="*60)
    print("SLOWEST SEARCH_HOTEL REQUESTS")
    print("="*60)
    
    slowest_requests = search_hotel_df.nlargest(10, 'response_time_ms')[
        ['timestamp', 'request_order', 'response_time_ms', 'url']
    ]
    print(slowest_requests.to_string(index=False))
    
    # Create visualizations
    create_performance_plots(search_hotel_df, first_requests, later_requests)
    
    return search_hotel_df, first_requests, later_requests

def create_performance_plots(df, first_requests, later_requests):
    """Create plots to visualize the performance patterns."""
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    
    # Plot 1: Response time over request order
    ax1.plot(df['request_order'], df['response_time_ms'], 'b-', alpha=0.6, linewidth=0.5)
    ax1.scatter(first_requests['request_order'], first_requests['response_time_ms'], 
               color='red', s=20, alpha=0.7, label='First 20 requests')
    ax1.set_xlabel('Request Order')
    ax1.set_ylabel('Response Time (ms)')
    ax1.set_title('Search Hotel Response Time by Request Order')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Response time over actual time
    ax2.plot(df['timestamp'], df['response_time_ms'], 'g-', alpha=0.6, linewidth=0.5)
    ax2.scatter(first_requests['timestamp'], first_requests['response_time_ms'], 
               color='red', s=20, alpha=0.7, label='First 20 requests')
    ax2.set_xlabel('Time')
    ax2.set_ylabel('Response Time (ms)')
    ax2.set_title('Search Hotel Response Time Over Time')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    # Plot 3: Histogram comparison
    ax3.hist(first_requests['response_time_ms'], bins=20, alpha=0.7, 
             label='First 20 requests', color='red', density=True)
    ax3.hist(later_requests['response_time_ms'], bins=50, alpha=0.7, 
             label='Later requests', color='blue', density=True)
    ax3.set_xlabel('Response Time (ms)')
    ax3.set_ylabel('Density')
    ax3.set_title('Response Time Distribution Comparison')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Moving average
    window_size = 10
    if len(df) >= window_size:
        moving_avg = df['response_time_ms'].rolling(window=window_size).mean()
        ax4.plot(df['request_order'], df['response_time_ms'], 'lightblue', alpha=0.5, label='Individual requests')
        ax4.plot(df['request_order'], moving_avg, 'darkblue', linewidth=2, label=f'{window_size}-request moving average')
        ax4.set_xlabel('Request Order')
        ax4.set_ylabel('Response Time (ms)')
        ax4.set_title(f'Search Hotel Response Time with {window_size}-Request Moving Average')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('search_hotel_performance_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"\nPerformance analysis plots saved as: search_hotel_performance_analysis.png")

if __name__ == "__main__":
    try:
        search_df, first_reqs, later_reqs = analyze_search_hotel_performance()
        print("\nAnalysis completed successfully!")
    except FileNotFoundError:
        print("Error: latency_per_route.csv file not found.")
        print("Please ensure the CSV file exists in the current directory.")
        sys.exit(1)
    except Exception as e:
        print(f"Error during analysis: {e}")
        sys.exit(1)