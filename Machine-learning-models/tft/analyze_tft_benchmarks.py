#!/usr/bin/env python3
"""
TFT (Temporal Fusion Transformer) Benchmark Analysis
----------------------------------------------------
1. Finds throughput CSVs in tft/benchmark_results/
2. Normalizes baselines against the Default baseline
3. Produces clean seaborn boxplots for training & inference throughput
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os, glob, warnings
warnings.filterwarnings('ignore')

# -------------------------------------------------------------
# 1. Find CSV files
# -------------------------------------------------------------
def find_csv_files(base_path):
    """Find all CSV files in benchmark_results baseline folders."""
    csv_files = {}
    baseline_folders = {
        'ap': 'ap',
        'at': 'at',
        'default': 'default',
        'ec': 'ec',
        'showvar': 'sw'
    }
    for folder_name, baseline_code in baseline_folders.items():
        folder_path = os.path.join(base_path, "benchmark_results", folder_name)
        if not os.path.exists(folder_path):
            continue

        csv_patterns = [
            f"throughput_metrics_training*{baseline_code}.csv",
            f"throughput_metrics_inference*{baseline_code}.csv"
        ]
        if baseline_code == "default":
            csv_patterns.extend([
                "throughput_metrics_training_default.csv",
                "throughput_metrics_inference_default.csv"
            ])

        for pattern in csv_patterns:
            for csv_path in glob.glob(os.path.join(folder_path, pattern)):
                filename = os.path.basename(csv_path)
                if "training" in filename and "inference" not in filename:
                    mode = "training"
                elif "inference" in filename:
                    mode = "inference"
                else:
                    continue
                baseline = 'sw' if baseline_code == 'sw' else baseline_code
                csv_files.setdefault(mode, {})[baseline] = csv_path
    return csv_files

# -------------------------------------------------------------
# 2. Load and filter CSV data
# -------------------------------------------------------------
def load_and_process_data(csv_files):
    data = {}
    for mode, baselines in csv_files.items():
        data[mode] = {}
        for baseline, csv_path in baselines.items():
            try:
                df = pd.read_csv(csv_path)
                if 'throughput' not in df.columns:
                    print(f"[WARN] {csv_path} missing 'throughput'")
                    continue
                vals = df['throughput'].dropna()
                mean, std = vals.mean(), vals.std()
                filtered = vals[(vals >= mean - 3*std) & (vals <= mean + 3*std)].values
                data[mode][baseline] = filtered
                print(f"Loaded {mode} {baseline}: {len(filtered)} samples")
            except Exception as e:
                print(f"Error loading {csv_path}: {e}")
    return data

# -------------------------------------------------------------
# 3. Normalize vs Default
# -------------------------------------------------------------
def normalize_against_default(data):
    normalized = {}
    for mode, baselines in data.items():
        normalized[mode] = {}
        if 'default' not in baselines:
            print(f"No default baseline found for {mode}")
            continue
        default_mean = np.mean(baselines['default'])
        print(f"\n[{mode.upper()}] Default mean = {default_mean:.4f}")
        for base, vals in baselines.items():
            if len(vals) == 0: continue
            normalized_vals = vals / default_mean
            normalized[mode][base] = normalized_vals
            print(f"{base:10s} mean={np.mean(vals):.4f} normalized_mean={np.mean(normalized_vals):.4f}")
    return normalized

# -------------------------------------------------------------
# 4. Clean Boxplots with Custom Colors
# -------------------------------------------------------------
def create_box_plots(normalized_data, output_dir, include_default=True):
    """Generate clean boxplots with custom colors for each baseline."""
    os.makedirs(output_dir, exist_ok=True)
    sns.set_theme(style="whitegrid")

    label_map = {
        'default': 'Default',
        'ap': 'Autopilot',
        'at': 'Autothrottle',
        'ec': 'Elastic Container',
        'sw': 'Showvar'
    }

    # Custom colors for each baseline - distinctly different colors
    custom_colors = {
        'Default': '#1f77b4',          # Bright Blue
        'Autopilot': '#ff7f0e',       # Bright Orange  
        'Autothrottle': '#2ca02c',    # Bright Green
        'Elastic Container': '#d62728', # Bright Red
        'Showvar': '#9467bd'          # Bright Purple
    }

    for mode in ['inference', 'training']:
        if mode not in normalized_data: 
            continue
        # Flatten to long-form DataFrame
        records = []
        for base, vals in normalized_data[mode].items():
            for v in vals:
                records.append({"Baseline": label_map.get(base, base), "Throughput": v})
        df = pd.DataFrame(records)
        if df.empty:
            continue

        # Order x-axis labels
        order = ['Default', 'Autopilot', 'Autothrottle', 'Elastic Container', 'Showvar']
        if not include_default:
            order = [o for o in order if o != 'Default']

        # Filter order to only include baselines that exist in data
        order = [o for o in order if o in df['Baseline'].values]

        plt.figure(figsize=(12,8))
        
        # Create boxplot with custom colors
        ax = sns.boxplot(
            data=df, x="Baseline", y="Throughput", order=order,
            palette=[custom_colors[baseline] for baseline in order],
            showmeans=True, 
            meanprops={"marker":"D","markerfacecolor":"white","markeredgecolor":"black", "markersize":8}
        )

        ax.axhline(1.0, color="red", linestyle="--", linewidth=2, label="Default Baseline Mean = 1.0")
        ax.legend()

        ax.set_title(f"TFT {mode.title()} Throughput\n(Normalized against Default Baseline)",
                     fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel("Normalized Throughput\n(Default = 1.0)", fontsize=13)
        ax.set_xlabel("Baseline Configuration", fontsize=13)
        plt.xticks(rotation=25, ha='right')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        save_name = f"tft_{mode}_normalized_boxplot_{'with_default' if include_default else 'no_default'}.png"
        out_path = os.path.join(output_dir, save_name)
        plt.savefig(out_path, dpi=300, bbox_inches='tight')
        print(f"Saved plot: {out_path}")
        plt.close()

# -------------------------------------------------------------
# 5. Summary stats
# -------------------------------------------------------------
def print_summary_statistics(normalized):
    print("\n" + "="*60)
    print("SUMMARY STATISTICS (Normalized Throughput)")
    print("="*60)
    for mode, baselines in normalized.items():
        print(f"\n{mode.upper()} MODE:")
        for base, vals in baselines.items():
            if len(vals)==0: continue
            stats = {
                'count': len(vals),
                'mean': np.mean(vals),
                'median': np.median(vals),
                'std': np.std(vals),
                'min': np.min(vals),
                'max': np.max(vals)
            }
            print(f"{base:10s} | n={stats['count']:3d} | "
                  f"mean={stats['mean']:.3f} | med={stats['median']:.3f} | "
                  f"std={stats['std']:.3f} | range=[{stats['min']:.3f}, {stats['max']:.3f}]")

# -------------------------------------------------------------
# 6. Main
# -------------------------------------------------------------
def main():
    base = os.path.dirname(os.path.abspath(__file__))
    print(f"Analyzing TFT benchmark data in {base}")

    csvs = find_csv_files(base)
    if not csvs:
        print("No CSVs found in benchmark_results/")
        return

    data = load_and_process_data(csvs)
    normalized = normalize_against_default(data)
    print_summary_statistics(normalized)

    output_dir = os.path.join(base, "analysis_results")
    create_box_plots(normalized, output_dir, include_default=True)
    print("\n✅ Analysis complete! Results saved in:", output_dir)

if __name__ == "__main__":
    main()
