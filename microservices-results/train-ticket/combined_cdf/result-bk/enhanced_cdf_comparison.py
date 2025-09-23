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
            'ap': 'Adaptive Policy',
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

                return 'autothrottle'    def detect_policy_from_columns(self, df):

            elif 'default' in col:        """Detect policy type from column names"""

                return 'default'        columns = [col.lower() for col in df.columns]

            elif 'showvar' in col:        for col in columns:

                return 'showvar'            if 'autothrottle' in col:

            elif 'captain' in col:                return 'autothrottle'

                return 'captain'            elif 'default' in col:

        return 'unknown'                return 'default'

                elif 'showvar' in col:

    def downsample_data(self, latency, cdf, max_points=2000):                return 'showvar'

        """Downsample data to reduce visual noise while preserving shape"""            elif 'captain' in col:

        if len(latency) <= max_points:                return 'captain'

            return latency, cdf        return 'unknown'

            

        # Use numpy linspace to get evenly spaced indices    def load_cdf_data(self, filepath, policy_hint=None):

        indices = np.linspace(0, len(latency)-1, max_points, dtype=int)        """Load CDF data from various file formats"""

        return latency[indices], cdf[indices]        try:

                # Read CSV with more robust settings

    def load_cdf_data(self, filepath, policy_hint=None, smooth=False):            df = pd.read_csv(filepath, encoding='utf-8')

        """Load CDF data from various file formats"""            

        try:            # Handle duplicate column names if they exist

            # Read CSV with more robust settings            if len(df.columns) != len(set(df.columns)):

            df = pd.read_csv(filepath, encoding='utf-8')                print(f"Warning: Duplicate column names found in {filepath}")

                            # Rename duplicate columns

            # Handle duplicate column names if they exist                cols = []

            if len(df.columns) != len(set(df.columns)):                for i, col in enumerate(df.columns):

                print(f"Warning: Duplicate column names found in {filepath}")                    if col in cols:

                # Rename duplicate columns                        cols.append(f"{col}_{i}")

                cols = []                    else:

                for i, col in enumerate(df.columns):                        cols.append(col)

                    if col in cols:                df.columns = cols

                        cols.append(f"{col}_{i}")            

                    else:            # Detect policy if not provided

                        cols.append(col)            if policy_hint is None:

                df.columns = cols                policy_hint = self.detect_policy_from_filename(filepath)

                            if policy_hint == 'unknown':

            # Detect policy if not provided                    policy_hint = self.detect_policy_from_columns(df)

            if policy_hint is None:            

                policy_hint = self.detect_policy_from_filename(filepath)            # Handle different column naming conventions

                if policy_hint == 'unknown':            latency_col = None

                    policy_hint = self.detect_policy_from_columns(df)            cdf_col = None

                        

            # Handle different column naming conventions            # Look for common column patterns

            latency_col = None            for col in df.columns:

            cdf_col = None                col_lower = col.lower()

                            if any(keyword in col_lower for keyword in ['response_time', 'latency', 'lat']):

            # Look for common column patterns                    latency_col = col

            for col in df.columns:                    break

                col_lower = col.lower()            

                if any(keyword in col_lower for keyword in ['response_time', 'latency', 'lat']):            for col in df.columns:

                    latency_col = col                col_lower = col.lower()

                    break                if any(keyword in col_lower for keyword in ['cumulative_prob', 'cdf', 'cumulative']):

                                cdf_col = col

            for col in df.columns:                    break

                col_lower = col.lower()            

                if any(keyword in col_lower for keyword in ['cumulative_prob', 'cdf', 'cumulative']):            # Fallback to first two columns if no specific match

                    cdf_col = col            if latency_col is None:

                    break                latency_col = df.columns[0]

                        if cdf_col is None:

            # Fallback to first two columns if no specific match                cdf_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]

            if latency_col is None:            

                latency_col = df.columns[0]            print(f"Loading {os.path.basename(filepath)}: using columns '{latency_col}' and '{cdf_col}'")

            if cdf_col is None:            

                cdf_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]            # Filter out NaN values and sort by latency

                        df_clean = df[[latency_col, cdf_col]].dropna().sort_values(by=latency_col)

            print(f"Loading {os.path.basename(filepath)}: using columns '{latency_col}' and '{cdf_col}'")            

                        if len(df_clean) == 0:

            # Filter out NaN values and sort by latency                print(f"Warning: No valid data found in {filepath}")

            df_clean = df[[latency_col, cdf_col]].dropna().sort_values(by=latency_col)                return None

                        

            if len(df_clean) == 0:            return {

                print(f"Warning: No valid data found in {filepath}")                'latency': df_clean[latency_col].values,

                return None                'cdf': df_clean[cdf_col].values,

                            'policy': policy_hint,

            latency = df_clean[latency_col].values                'file': os.path.basename(filepath)

            cdf = df_clean[cdf_col].values            }

                    except Exception as e:

            # Downsample for smoother plotting            print(f"Error loading {filepath}: {e}")

            if smooth:            # Try alternative loading method

                latency, cdf = self.downsample_data(latency, cdf)            try:

                            print(f"Trying alternative loading method for {filepath}")

            return {                df = pd.read_csv(filepath, header=0, names=['latency', 'cdf'])

                'latency': latency,                policy_hint = self.detect_policy_from_filename(filepath) if policy_hint is None else policy_hint

                'cdf': cdf,                

                'policy': policy_hint,                df_clean = df.dropna().sort_values(by='latency')

                'file': os.path.basename(filepath)                return {

            }                    'latency': df_clean['latency'].values,

        except Exception as e:                    'cdf': df_clean['cdf'].values,

            print(f"Error loading {filepath}: {e}")                    'policy': policy_hint,

            # Try alternative loading method                    'file': os.path.basename(filepath)

            try:                }

                print(f"Trying alternative loading method for {filepath}")            except Exception as e2:

                df = pd.read_csv(filepath, header=0, names=['latency', 'cdf'])                print(f"Alternative loading also failed for {filepath}: {e2}")

                policy_hint = self.detect_policy_from_filename(filepath) if policy_hint is None else policy_hint                return None

                    

                df_clean = df.dropna().sort_values(by='latency')    def smooth_cdf_data(self, latency, cdf, downsample_factor=10):

                        """Smooth and downsample CDF data to reduce waviness"""

                latency = df_clean['latency'].values        # Sort data to ensure proper ordering

                cdf = df_clean['cdf'].values        sorted_indices = np.argsort(latency)

                        latency_sorted = latency[sorted_indices]

                if smooth:        cdf_sorted = cdf[sorted_indices]

                    latency, cdf = self.downsample_data(latency, cdf)        

                        # Downsample the data to reduce density

                return {        if len(latency_sorted) > 1000:

                    'latency': latency,            step = max(1, len(latency_sorted) // 1000)  # Keep ~1000 points maximum

                    'cdf': cdf,            latency_downsampled = latency_sorted[::step]

                    'policy': policy_hint,            cdf_downsampled = cdf_sorted[::step]

                    'file': os.path.basename(filepath)        else:

                }            latency_downsampled = latency_sorted

            except Exception as e2:            cdf_downsampled = cdf_sorted

                print(f"Alternative loading also failed for {filepath}: {e2}")        

                return None        return latency_downsampled, cdf_downsampled

    

    def plot_combined_cdf(self, csv_directory=None, file_paths=None, output_file=None, title=None, app_name=None, smooth=False, xlim_percentile=99):    def plot_combined_cdf(self, csv_directory=None, file_paths=None, output_file=None, title=None, app_name=None, smooth=True, xlim_percentile=100):

        """Plot combined CDF from CSV files with distinct lines for each"""        """Plot combined CDF from CSV files with distinct lines for each"""

        plt.figure(figsize=(14, 10))        plt.figure(figsize=(14, 10))

                

        # Get list of CSV files        # Get list of CSV files

        if csv_directory:        if csv_directory:

            csv_files = glob.glob(os.path.join(csv_directory, "*.csv"))            csv_files = glob.glob(os.path.join(csv_directory, "*.csv"))

            csv_files.sort()  # Sort for consistent ordering            csv_files.sort()  # Sort for consistent ordering

        elif file_paths:        elif file_paths:

            csv_files = file_paths            csv_files = file_paths

        else:        else:

            print("Either csv_directory or file_paths must be provided!")            print("Either csv_directory or file_paths must be provided!")

            return            return

                

        if not csv_files:        if not csv_files:

            print(f"No CSV files found in {csv_directory}")            print(f"No CSV files found in {csv_directory}")

            return            return

                        

        print(f"Found {len(csv_files)} CSV files to plot:")        print(f"Found {len(csv_files)} CSV files to plot:")

        for f in csv_files:        for f in csv_files:

            print(f"  - {os.path.basename(f)}")            print(f"  - {os.path.basename(f)}")

                

        # Load all datasets        # Load all datasets

        datasets = []        datasets = []

        for i, filepath in enumerate(csv_files):        for i, filepath in enumerate(csv_files):

            data = self.load_cdf_data(filepath, smooth=smooth)            data = self.load_cdf_data(filepath)

            if data:            if data:

                # Assign color and style                # Smooth and downsample data to reduce waviness

                color_idx = i % len(self.colors)                if smooth:

                style_idx = i % len(self.linestyles)                    smooth_latency, smooth_cdf = self.smooth_cdf_data(data['latency'], data['cdf'])

                data['color'] = self.colors[color_idx]                    data['latency'] = smooth_latency

                data['linestyle'] = self.linestyles[style_idx]                    data['cdf'] = smooth_cdf

                datasets.append(data)                

                        # Assign color and style

        if not datasets:                color_idx = i % len(self.colors)

            print("No valid datasets found!")                style_idx = i % len(self.linestyles)

            return                data['color'] = self.colors[color_idx]

                        data['linestyle'] = self.linestyles[style_idx]

        # Plot each dataset with distinct styling                datasets.append(data)

        for i, data in enumerate(datasets):        

            policy = data['policy']        if not datasets:

                        print("No valid datasets found!")

            # Get display name for policy            return

            display_name = self.policy_names.get(policy, policy.capitalize())        

                    # Plot each dataset with distinct styling

            # Create plot arguments        for i, data in enumerate(datasets):

            plot_kwargs = {            policy = data['policy']

                'color': data['color'],            

                'linestyle': data['linestyle'],            # Get display name for policy

                'linewidth': 2.5,            display_name = self.policy_names.get(policy, policy.capitalize())

                'alpha': 0.8,            

                'label': f'{display_name}'            # Create plot arguments for smoother lines

            }            plot_kwargs = {

                            'color': data['color'],

            # Add markers for better distinction (every Nth point to avoid clutter)                'linestyle': data['linestyle'],

            if i < 4:  # Only first few get markers to avoid overcrowding                'linewidth': 2.0,  # Slightly thinner for cleaner look

                markers = ['o', 's', '^', 'D']                'alpha': 0.85,

                plot_kwargs['marker'] = markers[i % len(markers)]                'label': f'{display_name}',

                plot_kwargs['markersize'] = 4                'antialiased': True  # Enable antialiasing for smoother lines

                plot_kwargs['markevery'] = max(len(data['latency']) // 20, 1000)  # Show ~20 markers per line            }

                        

            plt.plot(data['latency'], data['cdf'], **plot_kwargs)            # Add markers sparingly for better distinction

                    if i < 4:  # Only first few get markers to avoid overcrowding

        # Calculate statistics                markers = ['o', 's', '^', 'D']

        all_latencies = np.concatenate([d['latency'] for d in datasets])                plot_kwargs['marker'] = markers[i % len(markers)]

        p50_lat = np.percentile(all_latencies, 50)                plot_kwargs['markersize'] = 3

        p95_lat = np.percentile(all_latencies, 95)                plot_kwargs['markevery'] = max(len(data['latency']) // 10, 50)  # Show ~10 markers per line

        p99_lat = np.percentile(all_latencies, 99)            

        max_lat = np.max(all_latencies)            plt.plot(data['latency'], data['cdf'], **plot_kwargs)

                

        # Customize plot appearance        # Customize plot appearance

        app_label = app_name if app_name else "Train Ticket"        app_label = app_name if app_name else "Train Ticket"

        plt.xlabel('Response Time (ms)', fontsize=12)        plt.xlabel('Response Time (ms)', fontsize=12)

        plt.ylabel('Cumulative Probability', fontsize=12)        plt.ylabel('Cumulative Probability', fontsize=12)

                

        if title:        if title:

            plt.title(title, fontsize=14, fontweight='bold')            plt.title(title, fontsize=14, fontweight='bold')

        else:        else:

            plt.title(f'{app_label} - Latency CDF Comparison', fontsize=14, fontweight='bold')            plt.title(f'{app_label} - Latency CDF Comparison', fontsize=14, fontweight='bold')

                

        # Improve legend        # Improve legend

        plt.legend(loc='lower right', fontsize=10, frameon=True, fancybox=True, shadow=True)        plt.legend(loc='lower right', fontsize=11, frameon=True, fancybox=True, shadow=True)

                

        # Add grid        # Add subtle grid

        plt.grid(True, alpha=0.3, linestyle='--')        plt.grid(True, alpha=0.25, linestyle='--', linewidth=0.5)

                

        # Set axis limits based on xlim_percentile        # Set axis limits for better view

        if xlim_percentile == 100:        all_latencies = np.concatenate([d['latency'] for d in datasets])

            xlim_max = max_lat        

        else:        # Calculate proper percentiles

            xlim_max = np.percentile(all_latencies, xlim_percentile)        p50_lat = np.percentile(all_latencies, 50)

                p95_lat = np.percentile(all_latencies, 95)

        plt.xlim(0, xlim_max * 1.05)        p99_lat = np.percentile(all_latencies, 99)

        plt.ylim(0, 1.02)        max_lat = np.max(all_latencies)

                

        # Format x-axis for better readability with large numbers        print(f"\nLatency Statistics:")

        ax = plt.gca()        print(f"  P50 (median): {p50_lat:.2f} ms")

        if xlim_max > 1000:        print(f"  P95: {p95_lat:.2f} ms") 

            # Use comma separators for thousands        print(f"  P99: {p99_lat:.2f} ms")

            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))        print(f"  Maximum: {max_lat:.2f} ms")

                

        # Add some statistics as text        # Set x-axis limit based on percentile parameter

        stats_text = f"Files analyzed: {len(datasets)}\n"        if xlim_percentile >= 100:

        stats_text += f"P50 latency: {p50_lat:.1f} ms\n"            x_limit = max_lat * 1.05

        stats_text += f"P95 latency: {p95_lat:.1f} ms\n"            print(f"  Showing full range up to {x_limit:.1f} ms")

        stats_text += f"P99 latency: {p99_lat:.1f} ms\n"        else:

        stats_text += f"Max latency: {max_lat:.1f} ms"            x_limit = np.percentile(all_latencies, xlim_percentile) * 1.05

                    print(f"  Showing P{xlim_percentile} range up to {x_limit:.1f} ms")

        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes,         

                fontsize=9, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))        plt.xlim(0, x_limit)

                plt.ylim(0, 1.01)

        plt.tight_layout()        

                # Improve tick formatting

        # Save plot        plt.gca().tick_params(axis='both', which='major', labelsize=10)

        if output_file is None:        

            output_file = f'combined_cdf_comparison_{app_name or "train_ticket"}.png'        # Format x-axis for better readability

                if x_limit > 1000:

        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')            # Use custom formatter for large values

        print(f"\nCombined CDF comparison plot saved as: {output_file}")            def format_latency(x, p):

                        if x >= 1000:

        # Show plot                    return f'{x/1000:.1f}k'

        plt.show()                else:

        return output_file                    return f'{x:.0f}'

            plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(format_latency))

def main():            plt.xlabel('Response Time (ms)', fontsize=12)

    plotter = CDFPlotter()        else:

                plt.xlabel('Response Time (ms)', fontsize=12)

    if len(sys.argv) < 2:        

        print("Usage:")        # Add some statistics as text

        print("  python3 enhanced_cdf_comparison.py --dir <csv_directory> [options]")        stats_text = f"Files analyzed: {len(datasets)}\n"

        print("  python3 enhanced_cdf_comparison.py <csv_file1> [csv_file2] ... [options]")        stats_text += f"P50: {p50_lat:.1f} ms\n"

        print("\nOptions:")        stats_text += f"P95: {p95_lat:.1f} ms\n" 

        print("  --dir <directory>    : Directory containing CSV files to plot")        stats_text += f"P99: {p99_lat:.1f} ms\n"

        print("  --output <file>      : Output PNG filename")        stats_text += f"Max: {max_lat:.1f} ms"

        print("  --title <title>      : Custom plot title")        

        print("  --app <app_name>     : Application name for default title")        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 

        print("  --smooth             : Apply data smoothing for cleaner curves")                fontsize=9, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        print("  --xlim <percentile>  : X-axis limit percentile (default: 99)")        

        print("\nExample usages:")        plt.tight_layout()

        print("  # Plot all CSV files in current directory")        

        print("  python3 enhanced_cdf_comparison.py --dir .")        # Save plot

        print("  # Plot with smoothing and show full range")        if output_file is None:

        print("  python3 enhanced_cdf_comparison.py --dir . --smooth --xlim 100")            output_file = f'combined_cdf_comparison_{app_name or "train_ticket"}.png'

        print("  # Plot specific files")        

        print("  python3 enhanced_cdf_comparison.py latency-default.png.csv latency-at.png.csv")        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')

        return        print(f"\nCombined CDF comparison plot saved as: {output_file}")

            

    # Parse arguments        # Show plot

    files = []        plt.show()

    csv_directory = None        return output_file

    output_file = None

    title = Nonedef main():

    app_name = None    plotter = CDFPlotter()

    smooth = False    

    xlim_percentile = 99    if len(sys.argv) < 2:

            print("Usage:")

    i = 1        print("  python3 enhanced_cdf_comparison.py --dir <csv_directory> [options]")

    while i < len(sys.argv):        print("  python3 enhanced_cdf_comparison.py <csv_file1> [csv_file2] ... [options]")

        if sys.argv[i] == '--dir' and i + 1 < len(sys.argv):        print("\nOptions:")

            csv_directory = sys.argv[i + 1]        print("  --dir <directory>    : Directory containing CSV files to plot")

            i += 2        print("  --output <file>      : Output PNG filename")

        elif sys.argv[i] == '--output' and i + 1 < len(sys.argv):        print("  --title <title>      : Custom plot title")

            output_file = sys.argv[i + 1]        print("  --app <app_name>     : Application name for default title")

            i += 2        print("  --xlim <percentile>  : Set x-axis limit to percentile (e.g., 95, 99, 100 for full range)")

        elif sys.argv[i] == '--title' and i + 1 < len(sys.argv):        print("  --no-smooth          : Disable data smoothing (may appear wavy)")

            title = sys.argv[i + 1]        print("\nExample usages:")

            i += 2        print("  # Plot all CSV files in current directory")

        elif sys.argv[i] == '--app' and i + 1 < len(sys.argv):        print("  python3 enhanced_cdf_comparison.py --dir .")

            app_name = sys.argv[i + 1]        print("  # Plot specific files")

            i += 2        print("  python3 enhanced_cdf_comparison.py latency-default.png.csv latency-at.png.csv")

        elif sys.argv[i] == '--smooth':        print("  # Use custom output and title")

            smooth = True        print("  python3 enhanced_cdf_comparison.py --dir . --output my_cdf.png --title 'My CDF Comparison'")

            i += 1        print("  # Disable smoothing to show raw data")

        elif sys.argv[i] == '--xlim' and i + 1 < len(sys.argv):        print("  python3 enhanced_cdf_comparison.py --dir . --no-smooth")

            xlim_percentile = float(sys.argv[i + 1])        return

            i += 2    

        elif sys.argv[i].startswith('--'):    # Parse arguments

            print(f"Unknown option: {sys.argv[i]}")    files = []

            return    csv_directory = None

        else:    output_file = None

            files.append(sys.argv[i])    title = None

            i += 1    app_name = None

        xlim_percentile = 100  # Default to full range

    # Determine what to plot    smooth = True  # Default to smoothing enabled

    if csv_directory:    

        # Plot all CSV files in directory    i = 1

        plotter.plot_combined_cdf(csv_directory=csv_directory, output_file=output_file, title=title, app_name=app_name, smooth=smooth, xlim_percentile=xlim_percentile)    while i < len(sys.argv):

    elif files:        if sys.argv[i] == '--dir' and i + 1 < len(sys.argv):

        # Check if files exist            csv_directory = sys.argv[i + 1]

        valid_files = []            i += 2

        for f in files:        elif sys.argv[i] == '--output' and i + 1 < len(sys.argv):

            if os.path.exists(f):            output_file = sys.argv[i + 1]

                valid_files.append(f)            i += 2

            else:        elif sys.argv[i] == '--title' and i + 1 < len(sys.argv):

                print(f"Warning: File not found: {f}")            title = sys.argv[i + 1]

                    i += 2

        if not valid_files:        elif sys.argv[i] == '--app' and i + 1 < len(sys.argv):

            print("No valid input files found!")            app_name = sys.argv[i + 1]

            return            i += 2

                elif sys.argv[i] == '--xlim' and i + 1 < len(sys.argv):

        # Plot specified files            xlim_percentile = float(sys.argv[i + 1])

        plotter.plot_combined_cdf(file_paths=valid_files, output_file=output_file, title=title, app_name=app_name, smooth=smooth, xlim_percentile=xlim_percentile)            i += 2

    else:        elif sys.argv[i] == '--no-smooth':

        print("No input specified! Use --dir <directory> or provide CSV file paths.")            smooth = False

        return            i += 1

        elif sys.argv[i].startswith('--'):

if __name__ == "__main__":            print(f"Unknown option: {sys.argv[i]}")

    main()            return
        else:
            files.append(sys.argv[i])
            i += 1
    
    # Determine what to plot
    if csv_directory:
        # Plot all CSV files in directory
        plotter.plot_combined_cdf(csv_directory=csv_directory, output_file=output_file, title=title, app_name=app_name, smooth=smooth)
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
        plotter.plot_combined_cdf(file_paths=valid_files, output_file=output_file, title=title, app_name=app_name, smooth=smooth)
    else:
        print("No input specified! Use --dir <directory> or provide CSV file paths.")
        return

if __name__ == "__main__":
    main()