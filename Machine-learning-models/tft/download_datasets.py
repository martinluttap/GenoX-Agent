#!/usr/bin/env python3
"""
Dataset Download and Preprocessing for TFT
Downloads and preprocesses electricity and traffic datasets for time series forecasting.

Usage:
    # Download electricity dataset
    python download_datasets.py --dataset electricity --data_dir ./data/processed/electricity

    # Download traffic dataset
    python download_datasets.py --dataset traffic --data_dir ./data/processed/traffic

    # Download both datasets
    python download_datasets.py --dataset all --data_dir ./data/processed
    
    # Download with preprocessing verification
    python download_datasets.py --dataset electricity --data_dir ./data --verify
"""

import os
import sys
import argparse
import logging
import urllib.request
import zipfile
import tarfile
import shutil
from pathlib import Path
from typing import Optional, Tuple
import tempfile

import pandas as pd
import numpy as np
from tqdm import tqdm
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Dataset URLs and information
DATASET_URLS = {
    'electricity': {
        'url': 'https://archive.ics.uci.edu/ml/machine-learning-databases/00321/LD2011_2014.txt.zip',
        'description': 'Electricity Consuming Load (ECL) dataset - 370 clients, hourly consumption from 2012-2014',
        'target_column': 'power_usage',
        'entity_column': 'client',
        'time_column': 'date',
        'freq': 'H'  # Hourly
    },
    'traffic': {
        'url': 'https://archive.ics.uci.edu/ml/machine-learning-databases/00204/PEMS-SF.zip',
        'description': 'Traffic dataset - 963 sensors, hourly occupancy rates from 2008-2009',
        'target_column': 'traffic_volume',
        'entity_column': 'sensor',
        'time_column': 'date',
        'freq': 'H'  # Hourly
    }
}

class DatasetDownloader:
    """Dataset downloader and preprocessor for TFT"""
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.raw_dir = self.data_dir / 'raw'
        self.processed_dir = self.data_dir / 'processed'
        self.raw_dir.mkdir(exist_ok=True)
        self.processed_dir.mkdir(exist_ok=True)
        
    def download_with_progress(self, url: str, filepath: Path) -> bool:
        """Download file with progress bar"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(filepath, 'wb') as f, tqdm(
                desc=f"Downloading {filepath.name}",
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    size = f.write(chunk)
                    pbar.update(size)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return False
    
    def download_electricity(self) -> bool:
        """Download and preprocess electricity dataset"""
        
        logger.info("Downloading electricity dataset...")
        
        dataset_info = DATASET_URLS['electricity']
        zip_file = self.raw_dir / 'LD2011_2014.txt.zip'
        raw_file = self.raw_dir / 'LD2011_2014.txt'
        
        # Download zip file if not exists
        if not zip_file.exists():
            if not self.download_with_progress(dataset_info['url'], zip_file):
                return False
        
        # Extract zip file if raw file doesn't exist
        if not raw_file.exists():
            logger.info("Extracting zip file...")
            import zipfile
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(self.raw_dir)
        
        # Load and preprocess data
        logger.info("Preprocessing electricity dataset...")
        
        # Read the data - it's a semicolon-separated file with header
        data = pd.read_csv(raw_file, sep=';')
        
        # The UCI electricity dataset has datetime as index and 370 client columns
        logger.info(f"Loaded data shape: {data.shape}")
        logger.info(f"Columns: {list(data.columns[:5])}...")  # Show first 5 columns
        
        # Convert to long format
        # Reset index to get datetime as a column if it's the index
        if data.index.name or isinstance(data.index, pd.DatetimeIndex):
            data = data.reset_index()
        
        # The first column should be datetime, rest are client power consumption
        datetime_col = data.columns[0]
        client_cols = data.columns[1:]
        
        # Melt to long format
        df = pd.melt(data, 
                    id_vars=[datetime_col], 
                    value_vars=client_cols,
                    var_name='id', 
                    value_name='power_usage')
        
        # Rename datetime column
        df = df.rename(columns={datetime_col: 'date'})
        
        # Convert date to datetime if it's not already
        df['date'] = pd.to_datetime(df['date'])
        
        # Create additional time features
        df['hour'] = df['date'].dt.hour
        df['day_of_week'] = df['date'].dt.dayofweek
        start_date = df['date'].min()
        df['days_from_start'] = (df['date'] - start_date).dt.days
        
        # Convert client names to numeric IDs
        unique_clients = df['id'].unique()
        client_mapping = {client: i for i, client in enumerate(unique_clients)}
        df['id'] = df['id'].map(client_mapping)
        
        # Sort by id and date
        df = df.sort_values(['id', 'date']).reset_index(drop=True)
        
        logger.info(f"Preprocessed dataset shape: {df.shape}")
        logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
        
        # Split into train/val/test (70/15/15 split by time)
        self._split_and_save_dataset(df, 'electricity')
        
        return True
    
    def download_traffic(self) -> bool:
        """Download and preprocess traffic dataset"""
        
        logger.info("Downloading traffic dataset...")
        
        dataset_info = DATASET_URLS['traffic']
        raw_file = self.raw_dir / 'traffic.txt'
        
        # Download if not exists
        if not raw_file.exists():
            if not self.download_with_progress(dataset_info['url'], raw_file):
                return False
        
        # Load and preprocess data
        logger.info("Preprocessing traffic dataset...")
        
        # Read the data - it's a space-separated file without header
        data = pd.read_csv(raw_file, sep=' ', header=None)
        
        # The traffic dataset has 963 sensors x 17544 time points
        # Each row is a sensor, each column is a time point
        n_sensors, n_timesteps = data.shape
        logger.info(f"Loaded data: {n_sensors} sensors, {n_timesteps} time points")
        
        # Reshape to long format
        rows = []
        for sensor_id in range(n_sensors):
            sensor_data = data.iloc[sensor_id].values
            for timestep in range(n_timesteps):
                rows.append({
                    'id': sensor_id,
                    'timestep': timestep,
                    'traffic_volume': float(sensor_data[timestep])
                })
        
        df = pd.DataFrame(rows)
        
        # Create time features - assuming hourly data starting from 2008-01-01
        start_date = pd.Timestamp('2008-01-01 00:00:00')
        df['date'] = start_date + pd.to_timedelta(df['timestep'], unit='H')
        df['hour'] = df['date'].dt.hour
        df['day_of_week'] = df['date'].dt.dayofweek
        df['days_from_start'] = (df['date'] - start_date).dt.days
        
        # Remove timestep column
        df = df.drop('timestep', axis=1)
        
        # Sort by id and date
        df = df.sort_values(['id', 'date']).reset_index(drop=True)
        
        logger.info(f"Preprocessed dataset shape: {df.shape}")
        logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
        
        # Split into train/val/test (70/15/15 split by time)
        self._split_and_save_dataset(df, 'traffic')
        
        return True
    
    def _split_and_save_dataset(self, df: pd.DataFrame, dataset_name: str):
        """Split dataset into train/val/test and save"""
        
        logger.info(f"Splitting {dataset_name} dataset...")
        
        # Create dataset directory
        dataset_dir = self.processed_dir / dataset_name
        dataset_dir.mkdir(exist_ok=True)
        
        # Sort by time to ensure chronological order
        df = df.sort_values('date').reset_index(drop=True)
        
        # Get unique dates for splitting
        unique_dates = df['date'].dt.date.unique()
        unique_dates = sorted(unique_dates)
        
        n_dates = len(unique_dates)
        train_end = int(n_dates * 0.7)
        val_end = int(n_dates * 0.85)
        
        train_dates = unique_dates[:train_end]
        val_dates = unique_dates[train_end:val_end]
        test_dates = unique_dates[val_end:]
        
        # Split data
        train_mask = df['date'].dt.date.isin(train_dates)
        val_mask = df['date'].dt.date.isin(val_dates)
        test_mask = df['date'].dt.date.isin(test_dates)
        
        train_df = df[train_mask].copy()
        val_df = df[val_mask].copy()
        test_df = df[test_mask].copy()
        
        # Save splits
        train_df.to_csv(dataset_dir / 'train.csv', index=False)
        val_df.to_csv(dataset_dir / 'val.csv', index=False)
        test_df.to_csv(dataset_dir / 'test.csv', index=False)
        
        # Save full dataset
        df.to_csv(dataset_dir / 'full.csv', index=False)
        
        # Save dataset statistics
        stats = {
            'dataset_name': dataset_name,
            'total_samples': len(df),
            'train_samples': len(train_df),
            'val_samples': len(val_df),
            'test_samples': len(test_df),
            'num_entities': df['id'].nunique(),
            'date_range': {
                'start': df['date'].min().isoformat(),
                'end': df['date'].max().isoformat()
            },
            'train_date_range': {
                'start': train_df['date'].min().isoformat(),
                'end': train_df['date'].max().isoformat()
            },
            'val_date_range': {
                'start': val_df['date'].min().isoformat(),
                'end': val_df['date'].max().isoformat()
            },
            'test_date_range': {
                'start': test_df['date'].min().isoformat(),
                'end': test_df['date'].max().isoformat()
            },
            'columns': list(df.columns),
            'target_column': 'traffic_volume' if dataset_name == 'traffic' else 'power_usage'
        }
        
        import json
        with open(dataset_dir / 'stats.json', 'w') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"Split summary for {dataset_name}:")
        logger.info(f"  Total samples: {len(df):,}")
        logger.info(f"  Train: {len(train_df):,} samples")
        logger.info(f"  Val: {len(val_df):,} samples")
        logger.info(f"  Test: {len(test_df):,} samples")
        logger.info(f"  Entities: {df['id'].nunique()}")
        logger.info(f"  Files saved to: {dataset_dir}")
    
    def verify_dataset(self, dataset_name: str) -> bool:
        """Verify dataset integrity"""
        
        logger.info(f"Verifying {dataset_name} dataset...")
        
        dataset_dir = self.processed_dir / dataset_name
        
        # Check if all files exist
        required_files = ['train.csv', 'val.csv', 'test.csv', 'full.csv', 'stats.json']
        for filename in required_files:
            filepath = dataset_dir / filename
            if not filepath.exists():
                logger.error(f"Missing file: {filepath}")
                return False
        
        try:
            # Load and check data
            train_df = pd.read_csv(dataset_dir / 'train.csv')
            val_df = pd.read_csv(dataset_dir / 'val.csv')
            test_df = pd.read_csv(dataset_dir / 'test.csv')
            
            # Check columns
            expected_cols = ['id', 'date', 'hour', 'day_of_week', 'days_from_start']
            if dataset_name == 'electricity':
                expected_cols.append('power_usage')
            else:
                expected_cols.append('traffic_volume')
            
            for df_name, df in [('train', train_df), ('val', val_df), ('test', test_df)]:
                missing_cols = set(expected_cols) - set(df.columns)
                if missing_cols:
                    logger.error(f"Missing columns in {df_name}: {missing_cols}")
                    return False
            
            # Check data consistency
            assert len(train_df) > 0, "Train set is empty"
            assert len(val_df) > 0, "Val set is empty"
            assert len(test_df) > 0, "Test set is empty"
            
            # Check no overlap in dates
            train_dates = set(pd.to_datetime(train_df['date']).dt.date)
            val_dates = set(pd.to_datetime(val_df['date']).dt.date)
            test_dates = set(pd.to_datetime(test_df['date']).dt.date)
            
            assert len(train_dates.intersection(val_dates)) == 0, "Train and val sets overlap"
            assert len(val_dates.intersection(test_dates)) == 0, "Val and test sets overlap"
            assert len(train_dates.intersection(test_dates)) == 0, "Train and test sets overlap"
            
            logger.info(f"✓ {dataset_name} dataset verification passed")
            return True
            
        except Exception as e:
            logger.error(f"Dataset verification failed: {e}")
            return False
    
    def download_all(self, datasets: list, verify: bool = False) -> bool:
        """Download multiple datasets"""
        
        success = True
        
        for dataset in datasets:
            if dataset == 'electricity':
                if not self.download_electricity():
                    success = False
                elif verify and not self.verify_dataset('electricity'):
                    success = False
                    
            elif dataset == 'traffic':
                if not self.download_traffic():
                    success = False
                elif verify and not self.verify_dataset('traffic'):
                    success = False
                    
            else:
                logger.error(f"Unknown dataset: {dataset}")
                success = False
        
        return success

def main():
    parser = argparse.ArgumentParser(description='Download and preprocess TFT datasets')
    
    parser.add_argument('--dataset', type=str, required=True,
                       choices=['electricity', 'traffic', 'all'],
                       help='Dataset to download')
    parser.add_argument('--data_dir', type=str, required=True,
                       help='Directory to store datasets')
    parser.add_argument('--verify', action='store_true',
                       help='Verify dataset integrity after download')
    
    args = parser.parse_args()
    
    # Create downloader
    downloader = DatasetDownloader(args.data_dir)
    
    # Determine datasets to download
    if args.dataset == 'all':
        datasets = ['electricity', 'traffic']
    else:
        datasets = [args.dataset]
    
    logger.info(f"Starting download for datasets: {datasets}")
    logger.info(f"Data directory: {args.data_dir}")
    
    # Download datasets
    success = downloader.download_all(datasets, verify=args.verify)
    
    if success:
        logger.info("✓ All datasets downloaded successfully!")
        
        # Print summary
        for dataset in datasets:
            dataset_dir = Path(args.data_dir) / 'processed' / dataset
            stats_file = dataset_dir / 'stats.json'
            
            if stats_file.exists():
                import json
                with open(stats_file, 'r') as f:
                    stats = json.load(f)
                
                print(f"\n{dataset.upper()} Dataset Summary:")
                print(f"  Total samples: {stats['total_samples']:,}")
                print(f"  Entities: {stats['num_entities']}")
                print(f"  Date range: {stats['date_range']['start']} to {stats['date_range']['end']}")
                print(f"  Train: {stats['train_samples']:,} samples")
                print(f"  Val: {stats['val_samples']:,} samples")
                print(f"  Test: {stats['test_samples']:,} samples")
        
        return 0
    else:
        logger.error("✗ Some datasets failed to download")
        return 1

if __name__ == '__main__':
    sys.exit(main())