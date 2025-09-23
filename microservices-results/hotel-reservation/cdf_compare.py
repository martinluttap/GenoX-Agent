#!/usr/bin/env python3

import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob
from pathlib import Path


class CDFPlotter:
    def __init__(self):
        # Define distinct colors and line styles
        self.colors = [
            '#1f77b4',  # Blue
            '#ff7f0e',  # Orange
            '#2ca02c',  # Green
            '#d62728',  # Red
            '#9467bd',  # Purple
            '#8c564b',  # Brown
            '#e377c2',  # Pink
            '#7f7f7f',  # Gray
            '#bcbd22',  # Olive
            '#17becf'   # Cyan
        ]
        
        self.linestyles = ['-', '--', '-.', ':', '-', '--', '-.', ':', '-', '--']
        
        # Policy name mapping for better display
        self.policy_names = {
            'default': 'Default',
            'at': 'AutoThrottle', 
            'autothrottle': 'AutoThrottle',
            'sw': 'ShowVar',
            'showvar': 'ShowVar',
            'ap': 'AutoPilot',
            'captain': 'Captain',
        }

    def detect_policy_from_filename(self, filename):
        """Detect policy type from filename"""
        filename = filename.lower()
        if 'autothrottle' in filename or '-at' in filename:
            return 'at'        
        elif 'default' in filename:
            return 'default'
        elif 'showvar' in filename or 'show_var' in filename or '-sw' in filename:
            return 'sw'
        elif 'captain' in filename:
            return 'captain'
        elif '-ap' in filename:
            return 'ap'
        else:
            # Extract policy from filename pattern like latency-{policy}.csv
            parts = os.path.basename(filename).replace('.csv', '').replace('.png', '').split('-')
            if len(parts) >= 2:
                return parts[-1]  # Last part after dash
            return 'unknown'

    def detect_policy_from_columns(self, df):
        """Detect policy type from column names"""
        columns = [col.lower() for col in df.columns]
        for col in columns:
            if 'autothrottle' in col:
                return 'autothrottle'
            elif 'default' in col:
                return 'default'
            elif 'showvar' in col:
                return 'showvar'
            elif 'captain' in col:
                return 'captain'
        return 'unknown'

    def load_cdf_data(self, filepath, policy_hint=None):
        """Load CDF data from various file formats"""
        try:
            # Read CSV with more robust settings
            df = pd.read_csv(filepath, encoding='utf-8')
            
            # Handle duplicate column names if they exist
            if len(df.columns) != len(set(df.columns)):
                print(f"Warning: Duplicate column names found in {filepath}")
                # Rename duplicate columns
                cols = []
                for i, col in enumerate(df.columns):
                    if col in cols:
                        cols.append(f"{col}_{i}")
                    else:
                        cols.append(col)
                df.columns = cols
            
            # Detect policy if not provided
            if policy_hint is None:
                policy_hint = self.detect_policy_from_filename(filepath)
                if policy_hint == 'unknown':
                    policy_hint = self.detect_policy_from_columns(df)
            
            # Handle different column naming conventions
            latency_col = None
            cdf_col = None
            
            # Look for common column patterns
            for col in df.columns:
                col_lower = col.lower()
                if any(keyword in col_lower for keyword in ['response_time', 'latency', 'lat']):
                    latency_col = col
                    break
            
            for col in df.columns:
                col_lower = col.lower()
                if any(keyword in col_lower for keyword in ['cumulative_prob', 'cdf', 'cumulative']):
                    cdf_col = col
                    break
            
            # Fallback to first two columns if no specific match
            if latency_col is None:
                latency_col = df.columns[0]
            if cdf_col is None:
                cdf_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
            
            print(f"Loading {os.path.basename(filepath)}: using columns '{latency_col}' and '{cdf_col}'")
            
            # Filter out NaN values and sort by latency
            df_clean = df[[latency_col, cdf_col]].dropna().sort_values(by=latency_col)
            
            if len(df_clean) == 0:
                print(f"Warning: No valid data found in {filepath}")
                return None
            
            return {
                'latency': df_clean[latency_col].values,
                'cdf': df_clean[cdf_col].values,
                'policy': policy_hint,
                'file': os.path.basename(filepath)
            }
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            # Try alternative loading method
            try:
                print(f"Trying alternative loading method for {filepath}")
                df = pd.read_csv(filepath, header=0, names=['latency', 'cdf'])
                policy_hint = self.detect_policy_from_filename(filepath) if policy_hint is None else policy_hint
                
                df_clean = df.dropna().sort_values(by='latency')
                return {
                    'latency': df_clean['latency'].values,
                    'cdf': df_clean['cdf'].values,
                    'policy': policy_hint,
                    'file': os.path.basename(filepath)
                }
            except Exception as e2:
                print(f"Alternative loading also failed for {filepath}: {e2}")
                return None

    def smooth_cdf_data(self, latency, cdf, downsample_factor=10):
        """Smooth and downsample CDF data to reduce waviness"""
        # Sort data to ensure proper ordering
        sorted_indices = np.argsort(latency)
        latency_sorted = latency[sorted_indices]
        cdf_sorted = cdf[sorted_indices]
        
        # Downsample the data to reduce density
        if len(latency_sorted) > 1000:
            step = max(1, len(latency_sorted) // 1000)  # Keep ~1000 points maximum
            latency_downsampled = latency_sorted[::step]
            cdf_downsampled = cdf_sorted[::step]
        else:
            latency_downsampled = latency_sorted
            cdf_downsampled = cdf_sorted
        
        return latency_downsampled, cdf_downsampled

    def plot_combined_cdf(self, csv_directory=None, file_paths=None, output_file=None, title=None, app_name=None, smooth=True, xlim_percentile=100):
        """Plot combined CDF from CSV files with distinct lines for each"""
        plt.figure(figsize=(14, 10))
        
        # Get list of CSV files
        if csv_directory:
            csv_files = glob.glob(os.path.join(csv_directory, "*.csv"))
            csv_files.sort()  # Sort for consistent ordering
        elif file_paths:
            csv_files = file_paths
        else:
            print("Either csv_directory or file_paths must be provided!")
            return
        
        if not csv_files:
            print(f"No CSV files found in {csv_directory}")
            return
                
        print(f"Found {len(csv_files)} CSV files to plot:")
        for f in csv_files:
            print(f"  - {os.path.basename(f)}")
        
        # Load all datasets
        datasets = []
        for i, filepath in enumerate(csv_files):
            data = self.load_cdf_data(filepath)
            if data:
                # Smooth and downsample data to reduce waviness
                if smooth:
                    smooth_latency, smooth_cdf = self.smooth_cdf_data(data['latency'], data['cdf'])
                    data['latency'] = smooth_latency
                    data['cdf'] = smooth_cdf
                
                # Assign color and style
                color_idx = i % len(self.colors)
                style_idx = i % len(self.linestyles)
                data['color'] = self.colors[color_idx]
                data['linestyle'] = self.linestyles[style_idx]
                datasets.append(data)
        
        if not datasets:
            print("No valid datasets found!")
            return
        
        # Plot each dataset with distinct styling
        for i, data in enumerate(datasets):
            policy = data['policy']
            
            # Get display name for policy
            display_name = self.policy_names.get(policy, policy.capitalize())
            
            # Create plot arguments for smoother lines
            plot_kwargs = {
                'color': data['color'],
                'linestyle': data['linestyle'],
                'linewidth': 2.0,  # Slightly thinner for cleaner look
                'alpha': 0.85,
                'label': f'{display_name}',
                'antialiased': True  # Enable antialiasing for smoother lines
            }
            
            # Add markers sparingly for better distinction
            if i < 4:  # Only first few get markers to avoid overcrowding
                markers = ['o', 's', '^', 'D']
                plot_kwargs['marker'] = markers[i % len(markers)]
                plot_kwargs['markersize'] = 3
                plot_kwargs['markevery'] = max(len(data['latency']) // 10, 50)  # Show ~10 markers per line
            
            plt.plot(data['latency'], data['cdf'], **plot_kwargs)
        
        # Customize plot appearance
        app_label = app_name if app_name else "Train Ticket"
        plt.xlabel('Response Time (ms)', fontsize=12)
        plt.ylabel('Cumulative Probability', fontsize=12)
        
        if title:
            plt.title(title, fontsize=14, fontweight='bold')
        else:
            plt.title(f'{app_label} - Latency CDF Comparison', fontsize=14, fontweight='bold')
        
        # Improve legend
        plt.legend(loc='lower right', fontsize=11, frameon=True, fancybox=True, shadow=True)
        
        # Add subtle grid
        plt.grid(True, alpha=0.25, linestyle='--', linewidth=0.5)
        
        # Set axis limits for better view
        all_latencies = np.concatenate([d['latency'] for d in datasets])
        
        # Calculate proper percentiles
        p50_lat = np.percentile(all_latencies, 50)
        p95_lat = np.percentile(all_latencies, 95)
        p99_lat = np.percentile(all_latencies, 99)
        max_lat = np.max(all_latencies)
        
        print(f"\nLatency Statistics:")
        print(f"  P50 (median): {p50_lat:.2f} ms")
        print(f"  P95: {p95_lat:.2f} ms") 
        print(f"  P99: {p99_lat:.2f} ms")
        print(f"  Maximum: {max_lat:.2f} ms")
        
        # Set x-axis limit based on percentile parameter
        if xlim_percentile >= 100:
            x_limit = max_lat * 1.05
            print(f"  Showing full range up to {x_limit:.1f} ms")
        else:
            x_limit = np.percentile(all_latencies, xlim_percentile) * 1.05
            print(f"  Showing P{xlim_percentile} range up to {x_limit:.1f} ms")
        
        plt.xlim(0, x_limit)
        plt.ylim(0, 1.01)
        
        # Improve tick formatting
        plt.gca().tick_params(axis='both', which='major', labelsize=10)
        
        # Format x-axis for better readability
        if x_limit > 1000:
            # Use custom formatter for large values
            def format_latency(x, p):
                return f'{x:.0f}'
            plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(format_latency))
            plt.xlabel('Response Time (ms)', fontsize=12)
        else:
            plt.xlabel('Response Time (ms)', fontsize=12)
        
        # Add some statistics as text
        stats_text = f"Files analyzed: {len(datasets)}\n"
        stats_text += f"P50: {p50_lat:.1f} ms\n"
        stats_text += f"P95: {p95_lat:.1f} ms\n" 
        stats_text += f"P99: {p99_lat:.1f} ms\n"
        stats_text += f"Max: {max_lat:.1f} ms"
        
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
                fontsize=9, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        
        # Save plot
        if output_file is None:
            output_file = f'combined_cdf_comparison_{app_name or "train_ticket"}.png'
        
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"\nCombined CDF comparison plot saved as: {output_file}")
        
        # Show plot
        plt.show()
        return output_file


def main():
    plotter = CDFPlotter()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 enhanced_cdf_comparison.py --dir <csv_directory> [options]")
        print("  python3 enhanced_cdf_comparison.py <csv_file1> [csv_file2] ... [options]")
        print("\nOptions:")
        print("  --dir <directory>    : Directory containing CSV files to plot")
        print("  --output <file>      : Output PNG filename")
        print("  --title <title>      : Custom plot title")
        print("  --app <app_name>     : Application name for default title")
        print("  --xlim <percentile>  : Set x-axis limit to percentile (e.g., 95, 99, 100 for full range)")
        print("  --no-smooth          : Disable data smoothing (may appear wavy)")
        print("\nExample usages:")
        print("  # Plot all CSV files in current directory")
        print("  python3 enhanced_cdf_comparison.py --dir .")
        print("  # Plot specific files")
        print("  python3 enhanced_cdf_comparison.py latency-default.png.csv latency-at.png.csv")
        print("  # Use custom output and title")
        print("  python3 enhanced_cdf_comparison.py --dir . --output my_cdf.png --title 'My CDF Comparison'")
        print("  # Disable smoothing to show raw data")
        print("  python3 enhanced_cdf_comparison.py --dir . --no-smooth")
        return
    
    # Parse arguments
    files = []
    csv_directory = None
    output_file = None
    title = None
    app_name = None
    xlim_percentile = 100  # Default to full range
    smooth = True  # Default to smoothing enabled
    
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--dir' and i + 1 < len(sys.argv):
            csv_directory = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--output' and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--title' and i + 1 < len(sys.argv):
            title = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--app' and i + 1 < len(sys.argv):
            app_name = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--xlim' and i + 1 < len(sys.argv):
            xlim_percentile = float(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--no-smooth':
            smooth = False
            i += 1
        elif sys.argv[i].startswith('--'):
            print(f"Unknown option: {sys.argv[i]}")
            return
        else:
            files.append(sys.argv[i])
            i += 1
    
    # Determine what to plot
    if csv_directory:
        # Plot all CSV files in directory
        plotter.plot_combined_cdf(csv_directory=csv_directory, output_file=output_file, title=title, app_name=app_name, smooth=smooth, xlim_percentile=xlim_percentile)
    elif files:
        # Check if files exist
        valid_files = []
        for f in files:
            if os.path.exists(f):
                valid_files.append(f)
            else:
                print(f"Warning: File not found: {f}")
        
        if not valid_files:
            print("No valid input files found!")
            return
        
        # Plot specified files
        plotter.plot_combined_cdf(file_paths=valid_files, output_file=output_file, title=title, app_name=app_name, smooth=smooth, xlim_percentile=xlim_percentile)
    else:
        print("No input specified! Use --dir <directory> or provide CSV file paths.")
        return


if __name__ == "__main__":
    main()