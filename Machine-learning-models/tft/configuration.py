#!/usr/bin/env python3
"""
Configuration module for TFT implementation.
Contains model configurations for different datasets.
"""

import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum

class InputTypes(Enum):
    """Input feature types for TFT model"""
    STATIC = 'static'
    OBSERVED = 'observed' 
    KNOWN = 'known'
    TARGET = 'target'
    ID = 'id'
    TIME = 'time'

class DataTypes(Enum):
    """Data embedding types"""
    CATEGORICAL = 'categorical'
    CONTINUOUS = 'continuous'

@dataclass
class FeatureSpec:
    """Feature specification for TFT inputs"""
    name: str
    feature_type: InputTypes
    embed_type: DataTypes
    vocab_size: Optional[int] = None

class TFTConfig:
    """Base configuration for TFT model"""
    
    def __init__(self):
        # Model architecture
        self.hidden_size = 128
        self.num_heads = 4
        self.num_quantiles = 3  # 0.1, 0.5, 0.9
        self.dropout = 0.1
        self.attention_dropout = 0.1
        
        # Training settings
        self.batch_size = 64
        self.learning_rate = 1e-3
        self.epochs = 25
        self.gradient_clipping = 0.0
        self.early_stopping = 5
        
        # Data settings
        self.encoder_length = 168  # Historical timesteps
        self.decoder_length = 24   # Forecast horizon
        self.example_length = self.encoder_length + self.decoder_length
        self.stride = 1
        
        # Features (to be defined by subclasses)
        self.features = []
        self.static_features = []
        self.known_features = []
        self.observed_features = []
        
        # Quantiles for loss calculation
        self.quantiles = [0.1, 0.5, 0.9]
        
        # Data preprocessing
        self.normalize = True
        self.clip_targets = False
        self.target_range = None

class ElectricityConfig(TFTConfig):
    """Configuration for electricity dataset"""
    
    def __init__(self):
        super().__init__()
        self.dataset_name = 'electricity'
        self.encoder_length = 168  # 7 days of hourly data
        self.decoder_length = 24   # 1 day ahead prediction
        
        # Define features for electricity dataset
        self.features = [
            FeatureSpec('id', InputTypes.ID, DataTypes.CATEGORICAL, vocab_size=370),
            FeatureSpec('days_from_start', InputTypes.TIME, DataTypes.CONTINUOUS),
            FeatureSpec('hour', InputTypes.KNOWN, DataTypes.CATEGORICAL, vocab_size=24),
            FeatureSpec('day_of_week', InputTypes.KNOWN, DataTypes.CATEGORICAL, vocab_size=7),
            FeatureSpec('month', InputTypes.KNOWN, DataTypes.CATEGORICAL, vocab_size=12),
            FeatureSpec('power_usage', InputTypes.TARGET, DataTypes.CONTINUOUS),
        ]
        
        # Dataset specific settings
        self.target_column = 'power_usage'
        self.time_column = 'date'
        self.id_column = 'id'
        
        # Categorize features
        self._categorize_features()

    def _categorize_features(self):
        """Categorize features by type"""
        self.static_features = [f for f in self.features if f.feature_type == InputTypes.STATIC]
        self.known_features = [f for f in self.features if f.feature_type == InputTypes.KNOWN]
        self.observed_features = [f for f in self.features if f.feature_type == InputTypes.OBSERVED]

class TrafficConfig(TFTConfig):
    """Configuration for traffic dataset"""
    
    def __init__(self):
        super().__init__()
        self.dataset_name = 'traffic'
        self.encoder_length = 168  # 7 days of hourly data
        self.decoder_length = 24   # 1 day ahead prediction
        
        # Define features for traffic dataset
        self.features = [
            FeatureSpec('id', InputTypes.ID, DataTypes.CATEGORICAL, vocab_size=963),
            FeatureSpec('days_from_start', InputTypes.TIME, DataTypes.CONTINUOUS),
            FeatureSpec('hour', InputTypes.KNOWN, DataTypes.CATEGORICAL, vocab_size=24),
            FeatureSpec('day_of_week', InputTypes.KNOWN, DataTypes.CATEGORICAL, vocab_size=7),
            FeatureSpec('month', InputTypes.KNOWN, DataTypes.CATEGORICAL, vocab_size=12),
            FeatureSpec('traffic_volume', InputTypes.TARGET, DataTypes.CONTINUOUS),
        ]
        
        # Dataset specific settings
        self.target_column = 'traffic_volume'
        self.time_column = 'date'
        self.id_column = 'id'
        
        # Categorize features
        self._categorize_features()

    def _categorize_features(self):
        """Categorize features by type"""
        self.static_features = [f for f in self.features if f.feature_type == InputTypes.STATIC]
        self.known_features = [f for f in self.features if f.feature_type == InputTypes.KNOWN]
        self.observed_features = [f for f in self.features if f.feature_type == InputTypes.OBSERVED]

# Configuration factory
CONFIGS = {
    'electricity': ElectricityConfig,
    'traffic': TrafficConfig,
}

def get_config(dataset_name: str) -> TFTConfig:
    """Get configuration for a specific dataset"""
    if dataset_name not in CONFIGS:
        raise ValueError(f"Unknown dataset: {dataset_name}. Available: {list(CONFIGS.keys())}")
    return CONFIGS[dataset_name]()