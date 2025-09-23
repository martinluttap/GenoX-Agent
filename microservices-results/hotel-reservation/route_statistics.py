#!/usr/bin/env python3
"""
Python script to analyze response time statistics by route from CSV file.
Provides detailed statistics, percentiles, and visualizations for each route.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import sys
import os
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

def read_csv_file(filepath):
    """Read the CSV file and return a pandas DataFrame filtered for successful requests only."""
    try:
        # Try reading with error handling for malformed rows
        try:
            df = pd.read_csv(filepath)
        except pd.errors.ParserError as e:
            print(f"⚠️  CSV parsing issue detected: {e}")
            print("Attempting to read with error handling...")
            try:
                df = pd.read_csv(filepath, on_bad_lines='skip')
            except TypeError:
                df = pd.read_csv(filepath, error_bad_lines=False, warn_bad_lines=True)
        
        print(f"Successfully loaded CSV file: {filepath}")
        print(f"Total records: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        
        # Filter for successful requests only if 'success' column exists
        if 'success' in df.columns:
            original_count = len(df)
            success_counts = df['success'].value_counts()
            
            print(f"\nSuccess Rate Analysis:")
            print(f"  ✅ Successful requests: {success_counts.get(True, 0)}")
            print(f"  ❌ Failed requests: {success_counts.get(False, 0)}")
            print(f"  Success rate: {success_counts.get(True, 0)/original_count*100:.1f}%")
            
            # Filter for successful requests only
            df_filtered = df[df['success'] == True].copy()
            print(f"\n🎯 Filtered to successful requests only: {len(df_filtered)} records")
            
            if len(df_filtered) == 0:
                print("❌ No successful requests found!")
                sys.exit(1)
            
            return df_filtered
        else:
            print("⚠️  No 'success' column found - using all records")
            return df
            
    except FileNotFoundError:
        print(f"Error: File {filepath} not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)

def calculate_route_statistics(df):
    """Calculate detailed statistics for each route."""
    # Filter out marker entries and non-numeric response times
    df_clean = df[
        (df['route_name'] != 'STEADY_STATE_START') & 
        (pd.to_numeric(df['response_time_ms'], errors='coerce').notna())
    ].copy()
    
    # Convert response_time_ms to numeric
    df_clean['response_time_ms'] = pd.to_numeric(df_clean['response_time_ms'])
    
    # Group by route
    route_stats = {}
    
    for route_name, group in df_clean.groupby('route_name'):
        response_times = group['response_time_ms'].values
        
        if len(response_times) == 0:
            continue
            
        # Calculate IQR outlier bounds
        Q1 = np.percentile(response_times, 25)
        Q3 = np.percentile(response_times, 75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # Count entries above P95
        p95_value = np.percentile(response_times, 95)
        above_p95 = np.sum(response_times > p95_value)
        above_p95_pct = (above_p95 / len(response_times)) * 100
        
        # Count IQR outliers
        iqr_outliers = np.sum((response_times < lower_bound) | (response_times > upper_bound))
        iqr_outliers_pct = (iqr_outliers / len(response_times)) * 100
        
        # Count entries that would be kept after IQR filtering
        kept_after_iqr = np.sum((response_times >= lower_bound) & (response_times <= upper_bound))
        kept_after_iqr_pct = (kept_after_iqr / len(response_times)) * 100

        stats_dict = {
            'route_name': route_name,
            'count': len(response_times),
            'mean': np.mean(response_times),
            'median': np.median(response_times),
            'std': np.std(response_times),
            'var': np.var(response_times),
            'min': np.min(response_times),
            'max': np.max(response_times),
            'range': np.max(response_times) - np.min(response_times),
            'p25': np.percentile(response_times, 25),
            'p50': np.percentile(response_times, 50),
            'p75': np.percentile(response_times, 75),
            'p90': np.percentile(response_times, 90),
            'p95': np.percentile(response_times, 95),
            'p99': np.percentile(response_times, 99),
            'p99.9': np.percentile(response_times, 99.9),
            'iqr': IQR,
            'cv': np.std(response_times) / np.mean(response_times) if np.mean(response_times) > 0 else 0,  # Coefficient of variation
            'skewness': stats.skew(response_times),
            'kurtosis': stats.kurtosis(response_times),
            # New outlier analysis fields
            'above_p95_count': above_p95,
            'above_p95_pct': above_p95_pct,
            'iqr_lower_bound': lower_bound,
            'iqr_upper_bound': upper_bound,
            'iqr_outliers_count': iqr_outliers,
            'iqr_outliers_pct': iqr_outliers_pct,
            'kept_after_iqr_count': kept_after_iqr,
            'kept_after_iqr_pct': kept_after_iqr_pct,
        }
        
        route_stats[route_name] = stats_dict
    
    return route_stats, df_clean

def print_route_statistics(route_stats):
    """Print formatted statistics for all routes."""
    print("\n" + "="*120)
    print("RESPONSE TIME STATISTICS BY ROUTE")
    print("="*120)
    
    # Create a summary table
    routes = list(route_stats.keys())
    
    # Header
    print(f"{'Route':<20} {'Count':<8} {'Mean':<8} {'Median':<8} {'P95':<8} {'P99':<8} {'Min':<8} {'Max':<8} {'Std':<8} {'CV':<6}")
    print("-" * 120)
    
    # Sort routes by mean response time (descending)
    sorted_routes = sorted(routes, key=lambda x: route_stats[x]['mean'], reverse=True)
    
    for route in sorted_routes:
        stats = route_stats[route]
        print(f"{route:<20} {stats['count']:<8} {stats['mean']:<8.1f} {stats['median']:<8.1f} "
              f"{stats['p95']:<8.1f} {stats['p99']:<8.1f} {stats['min']:<8.1f} {stats['max']:<8.1f} "
              f"{stats['std']:<8.1f} {stats['cv']:<6.2f}")
    
    print("\n" + "="*120)
    print("DETAILED PERCENTILE BREAKDOWN")
    print("="*120)
    
    for route in sorted_routes:
        stats = route_stats[route]
        print(f"\n📊 Route: {route}")
        print(f"   Requests: {stats['count']:,}")
        print(f"   Mean: {stats['mean']:.2f} ms | Median: {stats['median']:.2f} ms | Std: {stats['std']:.2f} ms")
        print(f"   Range: {stats['min']:.1f} - {stats['max']:.1f} ms (span: {stats['range']:.1f} ms)")
        print(f"   Percentiles: P25={stats['p25']:.1f} | P50={stats['p50']:.1f} | P75={stats['p75']:.1f} | P90={stats['p90']:.1f}")
        print(f"   High percentiles: P95={stats['p95']:.1f} | P99={stats['p99']:.1f} | P99.9={stats['p99.9']:.1f}")
        print(f"   Distribution: IQR={stats['iqr']:.1f} | CV={stats['cv']:.3f} | Skew={stats['skewness']:.2f} | Kurt={stats['kurtosis']:.2f}")
        print(f"   🔍 Above P95 ({stats['p95']:.1f}ms): {stats['above_p95_count']:,} entries ({stats['above_p95_pct']:.2f}%)")
        print(f"   🎯 IQR Bounds: [{stats['iqr_lower_bound']:.1f}, {stats['iqr_upper_bound']:.1f}] ms")
        print(f"   ❌ IQR Outliers (1.5×IQR): {stats['iqr_outliers_count']:,} entries ({stats['iqr_outliers_pct']:.2f}%)")
        print(f"   ✅ Kept after IQR filter: {stats['kept_after_iqr_count']:,} entries ({stats['kept_after_iqr_pct']:.2f}%)")

def create_route_visualizations(route_stats, df_clean, output_prefix='route_analysis'):
    """Create comprehensive visualizations for route analysis."""
    
    routes = list(route_stats.keys())
    n_routes = len(routes)
    
    if n_routes == 0:
        print("No routes to visualize")
        return
    
    # Set up the plotting style
    plt.style.use('default')
    sns.set_palette("husl")
    
    # Create a large figure with multiple subplots
    fig = plt.figure(figsize=(20, 16))
    
    # 1. Box Plot Comparison
    plt.subplot(3, 3, 1)
    route_data = []
    route_labels = []
    for route in routes:
        route_df = df_clean[df_clean['route_name'] == route]
        route_data.append(route_df['response_time_ms'].values)
        route_labels.append(route)
    
    plt.boxplot(route_data, labels=route_labels)
    plt.title('Response Time Distribution by Route')
    plt.ylabel('Response Time (ms)')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # 2. Mean Response Time Bar Chart
    plt.subplot(3, 3, 2)
    sorted_routes = sorted(routes, key=lambda x: route_stats[x]['mean'])
    means = [route_stats[route]['mean'] for route in sorted_routes]
    
    bars = plt.bar(range(len(sorted_routes)), means, color='skyblue', alpha=0.7)
    plt.title('Mean Response Time by Route')
    plt.ylabel('Mean Response Time (ms)')
    plt.xticks(range(len(sorted_routes)), sorted_routes, rotation=45)
    plt.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, mean in zip(bars, means):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{mean:.1f}', ha='center', va='bottom', fontsize=8)
    
    # 3. P95 Response Time Bar Chart
    plt.subplot(3, 3, 3)
    p95s = [route_stats[route]['p95'] for route in sorted_routes]
    
    bars = plt.bar(range(len(sorted_routes)), p95s, color='orange', alpha=0.7)
    plt.title('95th Percentile Response Time by Route')
    plt.ylabel('P95 Response Time (ms)')
    plt.xticks(range(len(sorted_routes)), sorted_routes, rotation=45)
    plt.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, p95 in zip(bars, p95s):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{p95:.1f}', ha='center', va='bottom', fontsize=8)
    
    # 4. Request Count by Route
    plt.subplot(3, 3, 4)
    counts = [route_stats[route]['count'] for route in sorted_routes]
    
    bars = plt.bar(range(len(sorted_routes)), counts, color='lightgreen', alpha=0.7)
    plt.title('Request Count by Route')
    plt.ylabel('Number of Requests')
    plt.xticks(range(len(sorted_routes)), sorted_routes, rotation=45)
    plt.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, count in zip(bars, counts):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{count:,}', ha='center', va='bottom', fontsize=8)
    
    # 5. Coefficient of Variation (CV) - measures relative variability
    plt.subplot(3, 3, 5)
    cvs = [route_stats[route]['cv'] for route in sorted_routes]
    
    bars = plt.bar(range(len(sorted_routes)), cvs, color='salmon', alpha=0.7)
    plt.title('Coefficient of Variation by Route')
    plt.ylabel('CV (Std/Mean)')
    plt.xticks(range(len(sorted_routes)), sorted_routes, rotation=45)
    plt.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, cv in zip(bars, cvs):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{cv:.2f}', ha='center', va='bottom', fontsize=8)
    
    # 6. Histogram overlay for all routes
    plt.subplot(3, 3, 6)
    colors = plt.cm.Set3(np.linspace(0, 1, len(routes)))
    
    for i, route in enumerate(routes):
        route_df = df_clean[df_clean['route_name'] == route]
        plt.hist(route_df['response_time_ms'], bins=50, alpha=0.6, 
                label=route, color=colors[i], density=True)
    
    plt.title('Response Time Distribution Overlay')
    plt.xlabel('Response Time (ms)')
    plt.ylabel('Density')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    
    # 7. Percentile comparison (P50, P90, P95, P99)
    plt.subplot(3, 3, 7)
    percentiles = ['p50', 'p90', 'p95', 'p99']
    x_pos = np.arange(len(sorted_routes))
    width = 0.2
    
    for i, p in enumerate(percentiles):
        values = [route_stats[route][p] for route in sorted_routes]
        plt.bar(x_pos + i * width, values, width, label=f'P{p[1:]}', alpha=0.8)
    
    plt.title('Percentile Comparison by Route')
    plt.ylabel('Response Time (ms)')
    plt.xlabel('Routes')
    plt.xticks(x_pos + width * 1.5, sorted_routes, rotation=45)
    plt.legend()
    plt.grid(True, alpha=0.3, axis='y')
    
    # 8. Scatter plot: Mean vs P95
    plt.subplot(3, 3, 8)
    means = [route_stats[route]['mean'] for route in routes]
    p95s = [route_stats[route]['p95'] for route in routes]
    counts = [route_stats[route]['count'] for route in routes]
    
    scatter = plt.scatter(means, p95s, s=[c/max(counts)*500 + 50 for c in counts], 
                         alpha=0.6, c=range(len(routes)), cmap='viridis')
    
    for i, route in enumerate(routes):
        plt.annotate(route, (means[i], p95s[i]), xytext=(5, 5), 
                    textcoords='offset points', fontsize=8, alpha=0.8)
    
    plt.title('Mean vs P95 Response Time\n(bubble size = request count)')
    plt.xlabel('Mean Response Time (ms)')
    plt.ylabel('P95 Response Time (ms)')
    plt.grid(True, alpha=0.3)
    
    # 9. Performance ranking table (as text)
    plt.subplot(3, 3, 9)
    plt.axis('off')
    
    # Create performance ranking
    performance_text = "🏆 PERFORMANCE RANKING\n\n"
    performance_text += "By Mean Response Time:\n"
    
    mean_ranking = sorted(routes, key=lambda x: route_stats[x]['mean'])
    for i, route in enumerate(mean_ranking[:5], 1):  # Top 5
        mean_val = route_stats[route]['mean']
        performance_text += f"{i}. {route}: {mean_val:.1f}ms\n"
    
    performance_text += "\nBy P95 Response Time:\n"
    p95_ranking = sorted(routes, key=lambda x: route_stats[x]['p95'])
    for i, route in enumerate(p95_ranking[:5], 1):  # Top 5
        p95_val = route_stats[route]['p95']
        performance_text += f"{i}. {route}: {p95_val:.1f}ms\n"
    
    plt.text(0.1, 0.8, performance_text, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(f'{output_prefix}.png', dpi=300, bbox_inches='tight')
    plt.show()
    print(f"Route analysis visualization saved as: {output_prefix}.png")

def save_route_statistics(route_stats, output_file='route_statistics.csv'):
    """Save route statistics to CSV file."""
    # Convert to DataFrame
    stats_df = pd.DataFrame(route_stats).T
    stats_df = stats_df.round(3)  # Round to 3 decimal places
    
    # Sort by mean response time
    stats_df = stats_df.sort_values('mean', ascending=False)
    
    # Save to CSV
    stats_df.to_csv(output_file, index=False)
    print(f"Route statistics saved to: {output_file}")
    
    return stats_df

def main():
    if len(sys.argv) < 2:
        print("Usage: python route_statistics.py <input_csv_file> [output_prefix]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_prefix = sys.argv[2] if len(sys.argv) > 2 else f"{os.path.splitext(input_file)[0]}_route_analysis"
    
    # Check if file exists
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        sys.exit(1)
    
    # Read the CSV file
    df = read_csv_file(input_file)
    
    # Check required columns
    required_columns = ['route_name', 'response_time_ms']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Error: Missing required columns: {missing_columns}")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)
    
    # Calculate route statistics
    print(f"\n📊 Analyzing response times by route...")
    route_stats, df_clean = calculate_route_statistics(df)
    
    if not route_stats:
        print("❌ No valid routes found for analysis!")
        sys.exit(1)
    
    # Print statistics
    print_route_statistics(route_stats)
    
    # Save statistics to CSV
    stats_df = save_route_statistics(route_stats, f"{output_prefix}_statistics.csv")
    
    # Create visualizations
    print(f"\n📈 Creating visualizations...")
    create_route_visualizations(route_stats, df_clean, output_prefix)
    
    # Print summary
    print(f"\n✅ Route analysis completed successfully!")
    print(f"📊 Analyzed {len(route_stats)} routes with {len(df_clean)} total requests")
    print(f"🏆 Best performing route (by mean): {min(route_stats.keys(), key=lambda x: route_stats[x]['mean'])}")
    print(f"🐌 Slowest route (by mean): {max(route_stats.keys(), key=lambda x: route_stats[x]['mean'])}")
    print(f"📁 Output files: {output_prefix}.png, {output_prefix}_statistics.csv")

if __name__ == "__main__":
    main()