def run_throughput_mode(args):
    """Train the model, then run endless inference (throughput mode)"""
    # Get configuration
    if args.dataset not in CONFIGS:
        raise ValueError(f"Unknown dataset: {args.dataset}")
    config = CONFIGS[args.dataset]()
    # Override config with command line arguments
    if args.batch_size:
        config.batch_size = args.batch_size
    if args.epochs:
        config.epochs = args.epochs
    if args.lr:
        config.learning_rate = args.lr
    logger.info(f"[THROUGHPUT MODE] Training TFT model on {args.dataset} dataset")
    logger.info(f"Configuration: {config.__dict__}")
    # Create data loaders
    train_loader, val_loader, test_loader = create_data_loaders(args, config)
    # Initialize trainer
    device = 'cuda' if torch.cuda.is_available() and not args.cpu_only else 'cpu'
    logger.info(f"Using device: {device}")
    trainer = TFTTrainer(config, device=device)
    # Train model
    trainer.train(train_loader, val_loader, save_dir=args.save_dir)
    # Test final model
    logger.info("Evaluating on test set...")
    test_loss, test_qrisk = trainer.validate_epoch(test_loader)
    logger.info(f"Test Loss: {test_loss:.4f}, Test Q-Risk: {test_qrisk:.4f}")
    # Run endless inference
    best_checkpoint = os.path.join(args.save_dir, 'best.pt')
    if os.path.exists(best_checkpoint):
        inferencer = TFTInference(best_checkpoint, device=device)
        logger.info("[THROUGHPUT MODE] Starting endless inference loop...")
        metrics_path = os.path.join(args.save_dir, 'throughput_metrics_inference.csv')
        while True:
            predictions, targets = inferencer.predict(test_loader)
            # Fix ambiguous boolean error robustly
            if targets is not None and torch.is_tensor(targets):
                qrisk = qrisk_metric(predictions, targets.unsqueeze(-1), inferencer.config.quantiles)
                logger.info(f"Q-Risk: {qrisk:.4f}")
            # Save throughput metrics after each inference loop
            throughput_tracker.save_metrics(metrics_path)
            logger.info(f"Endless inference completed on {len(test_loader.dataset)} samples (looping)")
    else:
        logger.warning(f"Best checkpoint not found at {best_checkpoint}, skipping endless inference")
#!/usr/bin/env python3
"""
Complete Temporal Fusion Transformer (TFT) Implementation
Based on NVIDIA DeepLearningExamples but optimized for CPU-only execution.

This script provides a complete implementation including:
- Model architecture (TFT, Variable Selection Network, Multi-Head Attention)
- Training pipeline with quantile loss
- Inference capabilities for time series forecasting
- Data loading for electricity and traffic datasets
- Configuration management

Usage:
    # Training
    python tft_complete.py --mode train --dataset electricity --data_path ./data/processed/electricity --epochs 25 --batch_size 64
    
    # Inference
    python tft_complete.py --mode inference --checkpoint checkpoints/best.pt --data ./data/processed/electricity/test.csv
    
    # Test model
    python tft_complete.py --mode test
"""

import os
import sys
import json
import yaml
import argparse
import time
import logging
import pickle
import warnings
import threading
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torch.cuda import amp
import numpy as np
import pandas as pd
from tqdm import tqdm
from sklearn.preprocessing import StandardScaler, LabelEncoder

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==============================================================================
# THROUGHPUT TRACKING
# ==============================================================================

class ThroughputTracker:
    """Track training and inference throughput metrics"""
    
    def __init__(self):
        self.training_metrics = []
        self.inference_metrics = []
        self.start_time = None
        self.samples_processed = 0
        
    def start_timing(self):
        """Start timing for throughput calculation"""
        self.start_time = time.time()
        self.samples_processed = 0
        
    def record_samples(self, num_samples):
        """Record number of samples processed"""
        self.samples_processed += num_samples
        
    def get_throughput(self):
        """Calculate current throughput (samples/second)"""
        if self.start_time is None:
            return 0.0
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0.0
        return self.samples_processed / elapsed
        
    def record_training_epoch(self, epoch, samples, duration, loss):
        """Record training epoch metrics"""
        throughput = samples / duration if duration > 0 else 0
        self.training_metrics.append({
            'epoch': epoch,
            'samples': samples,
            'duration': duration,
            'throughput': throughput,
            'loss': loss,
            'timestamp': time.time()
        })
        
    def record_inference_batch(self, batch_size, duration):
        """Record inference batch metrics"""
        throughput = batch_size / duration if duration > 0 else 0
        self.inference_metrics.append({
            'batch_size': batch_size,
            'duration': duration,
            'throughput': throughput,
            'timestamp': time.time()
        })
        
    def get_average_training_throughput(self):
        """Get average training throughput across all epochs"""
        if not self.training_metrics:
            return 0.0
        total_samples = sum(m['samples'] for m in self.training_metrics)
        total_duration = sum(m['duration'] for m in self.training_metrics)
        return total_samples / total_duration if total_duration > 0 else 0.0
        
    def get_average_inference_throughput(self):
        """Get average inference throughput"""
        if not self.inference_metrics:
            return 0.0
        throughputs = [m['throughput'] for m in self.inference_metrics]
        return sum(throughputs) / len(throughputs)
        
    def save_metrics(self, filepath):
        """Append metrics to CSV file (does not overwrite)"""
        # Save training metrics
        if self.training_metrics:
            train_df = pd.DataFrame(self.training_metrics)
            for col in train_df.columns:
                if train_df[col].dtype == object:
                    train_df[col] = train_df[col].apply(lambda x: x.replace(',', '.') if isinstance(x, str) else x)
            train_path = filepath.replace('.csv', '_training.csv')
            # Append to file if exists
            if os.path.exists(train_path):
                train_df.to_csv(train_path, mode='a', header=False, index=False)
            else:
                train_df.to_csv(train_path, index=False)
            logger.info(f"Training metrics appended to {train_path}")
        # Save inference metrics
        if self.inference_metrics:
            inf_df = pd.DataFrame(self.inference_metrics)
            for col in inf_df.columns:
                if inf_df[col].dtype == object:
                    inf_df[col] = inf_df[col].apply(lambda x: x.replace(',', '.') if isinstance(x, str) else x)
            inf_path = filepath.replace('.csv', '_inference.csv')
            # Append to file if exists
            if os.path.exists(inf_path):
                inf_df.to_csv(inf_path, mode='a', header=False, index=False)
            else:
                inf_df.to_csv(inf_path, index=False)
            logger.info(f"Inference metrics appended to {inf_path}")
            
    def print_summary(self):
        """Print throughput summary"""
        logger.info("=== THROUGHPUT SUMMARY ===")
        
        if self.training_metrics:
            avg_train_throughput = self.get_average_training_throughput()
            logger.info(f"Training throughput: {avg_train_throughput:.2f} samples/second")
            
            for i, metric in enumerate(self.training_metrics[-5:]):  # Show last 5 epochs
                logger.info(f"  Epoch {metric['epoch']}: {metric['throughput']:.2f} samples/s, "
                          f"Loss: {metric['loss']:.4f}")
                          
        if self.inference_metrics:
            avg_inf_throughput = self.get_average_inference_throughput()
            logger.info(f"Inference throughput: {avg_inf_throughput:.2f} samples/second")
            logger.info(f"Total inference batches: {len(self.inference_metrics)}")

# Global throughput tracker
throughput_tracker = ThroughputTracker()

print("TFT script started")

# Set number of threads to use all available cores
num_cores = mp.cpu_count()
print(f"Setting up to use all {num_cores} CPU cores")

# Configure PyTorch to use all cores
torch.set_num_threads(num_cores)
torch.set_num_interop_threads(num_cores)

# For OpenMP (if available)
os.environ['OMP_NUM_THREADS'] = str(num_cores)
os.environ['MKL_NUM_THREADS'] = str(num_cores)
os.environ['OPENBLAS_NUM_THREADS'] = str(num_cores)
os.environ['VECLIB_MAXIMUM_THREADS'] = str(num_cores)
os.environ['NUMEXPR_NUM_THREADS'] = str(num_cores)

print(f"PyTorch threads: {torch.get_num_threads()}")
print(f"PyTorch interop threads: {torch.get_num_interop_threads()}")

# ==============================================================================
# CONSTANTS AND ENUMS
# ==============================================================================

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

# ==============================================================================
# CONFIGURATION CLASSES
# ==============================================================================

class TFTConfig:
    """Base configuration for TFT model"""
    def __init__(self):
        # Model architecture - optimized for CPU
        self.hidden_size = 64   # Reduced for better CPU performance
        self.num_heads = 2      # Reduced from 4
        self.num_quantiles = 3  # 0.1, 0.5, 0.9
        self.dropout = 0.1
        self.attention_dropout = 0.1
        
        # Training settings - optimized for CPU
        self.batch_size = 32     # Reduced from 64
        self.learning_rate = 1e-3
        self.epochs = 25
        self.gradient_clipping = 0.0
        self.early_stopping = 5
        
        # Data settings - reduced for faster training
        self.encoder_length = 48   # Historical timesteps (reduced from 168)
        self.decoder_length = 12   # Forecast horizon (reduced from 24)
        self.example_length = self.encoder_length + self.decoder_length
        self.stride = 1
        
        # Features (to be defined by subclasses)
        self.features = []
        self.static_features = []
        self.known_features = []
        self.observed_features = []
        
        # Quantiles for loss calculation
        self.quantiles = [0.1, 0.5, 0.9]

class ElectricityConfig(TFTConfig):
    """Configuration for electricity dataset - optimized for CPU performance"""
    
    def __init__(self):
        super().__init__()
        self.dataset_name = 'electricity'
        
        # Electricity-specific features - simplified set
        self.features = [
    FeatureSpec('id', InputTypes.STATIC, DataTypes.CATEGORICAL, vocab_size=370),
    FeatureSpec('hour', InputTypes.KNOWN, DataTypes.CATEGORICAL),
    FeatureSpec('day_of_week', InputTypes.KNOWN, DataTypes.CATEGORICAL),
    FeatureSpec('days_from_start', InputTypes.KNOWN, DataTypes.CONTINUOUS),
    FeatureSpec('power_usage', InputTypes.TARGET, DataTypes.CONTINUOUS),
]
# ==============================================================================
# LOSS FUNCTIONS
# ==============================================================================

class QuantileLoss(nn.Module):
    """Quantile loss for TFT training"""
    
    def __init__(self, config):
        super().__init__()
        self.quantiles = torch.tensor(config.quantiles, dtype=torch.float32)
        self.num_quantiles = len(self.quantiles)
        
    def forward(self, predictions, targets):
        """
        Args:
            predictions: [batch_size, seq_len, num_quantiles]
            targets: [batch_size, seq_len, 1]
        """
        # Expand targets to match prediction dimensions
        targets = targets.expand(-1, -1, self.num_quantiles)
        
        # Move quantiles to same device as predictions
        quantiles = self.quantiles.to(predictions.device)
        
        # Calculate quantile loss
        errors = targets - predictions
        losses = torch.max(
            (quantiles - 1.0) * errors,
            quantiles * errors
        )
        
        return losses.mean(dim=[0, 1])  # Return per-quantile losses

def qrisk_metric(predictions, targets, quantiles):
    """Q-Risk metric for evaluation"""
    predictions = predictions.detach().cpu().numpy()
    targets = targets.detach().cpu().numpy()

    # Ensure targets shape matches predictions[:, :, i]
    if targets.ndim == 3 and targets.shape[-1] == 1:
        targets = targets.squeeze(-1)
    # Now targets: (batch_size, decoder_length) or (batch_size, decoder_length, num_quantiles)

    total_loss = 0
    total_weight = 0
    for i, q in enumerate(quantiles):
        # predictions[:, :, i]: (batch_size, decoder_length)
        if targets.ndim == 3 and targets.shape[2] == len(quantiles):
            target_q = targets[:, :, i]
        else:
            target_q = targets
        errors = target_q - predictions[:, :, i]
        loss = 2 * np.sum(np.maximum(q * errors, (q - 1) * errors))
        weight = np.sum(np.abs(target_q))
        if weight > 0:
            total_loss += loss
            total_weight += weight

    return total_loss / total_weight if total_weight > 0 else 0.0

# ==============================================================================
# MODEL COMPONENTS
# ==============================================================================

class GatedLinearUnit(nn.Module):
    """Gated Linear Unit for TFT"""
    
    def __init__(self, input_size, hidden_size=None, dropout=0.0):
        super().__init__()
        if hidden_size is None:
            hidden_size = input_size
            
        self.linear = nn.Linear(input_size, 2 * hidden_size)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x):
        # Split into two parts for gating
        x = self.linear(x)
        x = self.dropout(x)
        a, b = torch.chunk(x, 2, dim=-1)
        return a * torch.sigmoid(b)

class GatedResidualNetwork(nn.Module):
    """Gated Residual Network (GRN) component"""
    
    def __init__(self, input_size, hidden_size=None, output_size=None, 
                 dropout=0.0, context_size=None):
        super().__init__()
        # Always use input_size for hidden_size and output_size unless explicitly specified
        if hidden_size is None:
            hidden_size = input_size
        if output_size is None:
            output_size = input_size
        self.input_size = input_size
        self.output_size = output_size
        self.context_size = context_size
        # Primary processing
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.elu = nn.ELU()
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.dropout = nn.Dropout(dropout)
        # Gating
        self.gate = GatedLinearUnit(hidden_size, hidden_size, dropout)
        # Context integration if available
        if context_size is not None:
            self.context_projection = nn.Linear(context_size, hidden_size, bias=False)
        # Skip connection
        if input_size != output_size:
            self.skip_projection = nn.Linear(input_size, output_size)
        else:
            self.skip_projection = None
        # Layer normalization
        self.layer_norm = nn.LayerNorm(output_size)
        
    def forward(self, x, context=None):
        # Skip connection
        skip = x
        if self.skip_projection is not None:
            skip = self.skip_projection(skip)
        
        # Primary path
        x = self.fc1(x)
        x = self.elu(x)
        x = self.fc2(x)
        x = self.dropout(x)
        
        # Add context if provided
        if context is not None and self.context_size is not None:
            context_proj = self.context_projection(context)
            # Expand context_proj to match x if needed
            if x.dim() == 3 and context_proj.dim() == 2:
                context_proj = context_proj.unsqueeze(1).expand(-1, x.size(1), -1)
            x = x + context_proj
        
        # Gating
        x = self.gate(x)
        
        # Residual connection and normalization
        x = x + skip
        x = self.layer_norm(x)
        
        return x

class VariableSelectionNetwork(nn.Module):
    """Variable Selection Network for input feature selection"""
    
    def __init__(self, input_size, num_inputs, hidden_size, dropout=0.0):
        super().__init__()
        
        self.input_size = input_size
        self.num_inputs = num_inputs
        self.hidden_size = hidden_size
        
        # Flattened input processing
        self.flattened_grn = GatedResidualNetwork(
            input_size * num_inputs,
            hidden_size,
            input_size * num_inputs,
            dropout
        )
        
        # Individual input processing
        self.single_variable_grns = nn.ModuleList([
            GatedResidualNetwork(input_size, hidden_size, hidden_size, dropout)
            for _ in range(num_inputs)
        ])
        
        self.softmax = nn.Softmax(dim=-1)
        
    def forward(self, flattened_embedding, static_context=None):
        # Variable selection weights
        mlp_inputs = flattened_embedding
        sparse_weights = self.flattened_grn(mlp_inputs, static_context)
        sparse_weights = self.softmax(sparse_weights).unsqueeze(-1)
        
        # Process individual variables
        var_outputs = []
        for i, grn in enumerate(self.single_variable_grns):
            # Extract single variable
            start_idx = i * self.input_size
            end_idx = (i + 1) * self.input_size
            single_var = flattened_embedding[..., start_idx:end_idx]
            
            # Process through GRN
            processed = grn(single_var, static_context)
            var_outputs.append(processed)
        
        # Stack and apply weights
        var_outputs = torch.stack(var_outputs, dim=-2)
        # Ensure sparse_weights has correct dimensions for broadcasting
        # For non-sequence (row-based) data, add sequence dimension if needed
        if sparse_weights.dim() == 3:
            # Add sequence dimension for broadcasting
            sparse_weights = sparse_weights.unsqueeze(1)
        
        # Weighted combination
        # Broadcasting works for elementwise multiplication
        outputs = var_outputs * sparse_weights
        outputs = outputs.sum(dim=-2)
        
        return outputs, sparse_weights.squeeze(-1)

class StaticCovariateEncoder(nn.Module):
    """Static covariate encoder for TFT"""
    
    def __init__(self, config):
        super().__init__()
        
        self.hidden_size = config.hidden_size
        
        # Context vectors
        self.context_grns = nn.ModuleList([
            GatedResidualNetwork(self.hidden_size, hidden_size=self.hidden_size, output_size=self.hidden_size, dropout=config.dropout)
            for _ in range(4)  # cs, ce, ch, cc
        ])
        
    def forward(self, static_embedding):
        # Generate context vectors
        contexts = []
        for grn in self.context_grns:
            context = grn(static_embedding)
            contexts.append(context)
            
        return contexts  # [cs, ce, ch, cc]

class InterpretableMultiHeadAttention(nn.Module):
    """Multi-head attention with shared value matrices for interpretability"""
    
    def __init__(self, d_model, num_heads, dropout=0.0):
        super().__init__()
        
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads
        
        assert d_model % num_heads == 0
        
        # Shared value matrix for interpretability
        self.W_v = nn.Linear(d_model, d_model, bias=False)
        
        # Separate query and key matrices for each head
        self.W_q = nn.ModuleList([
            nn.Linear(d_model, self.d_k, bias=False)
            for _ in range(num_heads)
        ])
        self.W_k = nn.ModuleList([
            nn.Linear(d_model, self.d_k, bias=False)
            for _ in range(num_heads)
        ])
        
        # Output projection
        self.W_o = nn.Linear(d_model, d_model)
        
        # Dropout
        self.dropout = nn.Dropout(dropout)
        
        # Scaling factor
        self.scale = 1.0 / (self.d_k ** 0.5)
        
    def forward(self, query, key, value, mask=None):
        batch_size, seq_len, _ = query.size()
        
        # Shared value transformation
        V = self.W_v(value)  # [batch, seq, d_model]
        V = V.view(batch_size, seq_len, self.num_heads, self.d_k)
        V = V.transpose(1, 2)  # [batch, num_heads, seq, d_k]
        
        # Multi-head attention
        attention_outputs = []
        attention_weights = []
        
        for i in range(self.num_heads):
            # Query and Key for this head
            Q = self.W_q[i](query)  # [batch, seq, d_k]
            K = self.W_k[i](key)    # [batch, seq, d_k]
            
            # Attention scores
            scores = torch.matmul(Q, K.transpose(-2, -1)) * self.scale
            
            # Apply mask if provided
            if mask is not None:
                scores.masked_fill_(mask == 0, -1e9)
            
            # Softmax
            attn_weights = F.softmax(scores, dim=-1)
            attn_weights = self.dropout(attn_weights)
            
            # Apply attention to values
            V_head = V[:, i, :, :]  # [batch, seq, d_k]
            attn_output = torch.matmul(attn_weights, V_head)
            
            attention_outputs.append(attn_output)
            attention_weights.append(attn_weights)
        
        # Concatenate heads
        attention_output = torch.cat(attention_outputs, dim=-1)
        
        # Final projection
        output = self.W_o(attention_output)
        
        # Stack attention weights
        attention_weights = torch.stack(attention_weights, dim=1)
        
        return output, attention_weights

class TFTEmbedding(nn.Module):
    """TFT input embedding layer"""
    
    def __init__(self, config):
        super().__init__()
        
        self.config = config
        self.hidden_size = config.hidden_size
        
        # Categorical embeddings
        self.categorical_embeddings = nn.ModuleDict()
        
        # Continuous embeddings (learned scaling vectors)
        self.continuous_embeddings = nn.ModuleDict()
        
        # Initialize embeddings based on features
        for feature in config.features:
            if feature.embed_type == DataTypes.CATEGORICAL:
                vocab_size = feature.vocab_size or 1000  # Default vocab size
                self.categorical_embeddings[feature.name] = nn.Embedding(
                    vocab_size, self.hidden_size
                )
            else:
                self.continuous_embeddings[feature.name] = nn.Linear(1, self.hidden_size)
        
        # Calculate projection sizes for each feature type
        static_features = [f for f in config.features if f.feature_type == InputTypes.STATIC]
        known_features = [f for f in config.features if f.feature_type == InputTypes.KNOWN]
        observed_features = [f for f in config.features if f.feature_type == InputTypes.OBSERVED]
        target_features = [f for f in config.features if f.feature_type == InputTypes.TARGET]
        
        # Create projection layers if needed
        if len(static_features) > 1:
            self.static_projection = nn.Linear(len(static_features) * self.hidden_size, self.hidden_size)
        
        if len(known_features) > 1:
            self.known_projection = nn.Linear(len(known_features) * self.hidden_size, self.hidden_size)
            
        if len(observed_features) > 1:
            self.observed_projection = nn.Linear(len(observed_features) * self.hidden_size, self.hidden_size)
            
        if len(target_features) > 1:
            self.target_projection = nn.Linear(len(target_features) * self.hidden_size, self.hidden_size)
    
    def forward(self, inputs):
        """
        Args:
            inputs: Dict containing input tensors for each feature
        
        Returns:
            Embedded features organized by type
        """
        static_embeddings = []
        known_embeddings = []
        observed_embeddings = []
        target_embeddings = []
        
        for feature in self.config.features:
            if feature.name not in inputs:
                continue
            x = inputs[feature.name]
            # Apply embedding
            if feature.embed_type == DataTypes.CATEGORICAL:
                embedded = self.categorical_embeddings[feature.name](x.long())
            else:
                # Ensure x is always 2D: [seq_len, 1]
                if x.dim() == 1:
                    x = x.unsqueeze(-1)
                elif x.dim() == 2:
                    x = x.unsqueeze(-1) if x.size(-1) != 1 else x
                embedded = self.continuous_embeddings[feature.name](x)
            
            # Organize by feature type
            if feature.feature_type == InputTypes.STATIC:
                static_embeddings.append(embedded)
            elif feature.feature_type == InputTypes.KNOWN:
                known_embeddings.append(embedded)
            elif feature.feature_type == InputTypes.OBSERVED:
                observed_embeddings.append(embedded)
            elif feature.feature_type == InputTypes.TARGET:
                target_embeddings.append(embedded)
        
        # Project concatenated embeddings to consistent hidden_size
        static_output = None
        if static_embeddings:
            static_concat = torch.cat(static_embeddings, dim=-1)
            if hasattr(self, 'static_projection'):
                static_output = self.static_projection(static_concat)
            else:
                static_output = static_concat
        
        known_output = None
        if known_embeddings:
            known_concat = torch.cat(known_embeddings, dim=-1)
            if hasattr(self, 'known_projection'):
                known_output = self.known_projection(known_concat)
            else:
                known_output = known_concat
        
        observed_output = None
        if observed_embeddings:
            observed_concat = torch.cat(observed_embeddings, dim=-1)
            if hasattr(self, 'observed_projection'):
                observed_output = self.observed_projection(observed_concat)
            else:
                observed_output = observed_concat
        
        target_output = None
        if target_embeddings:
            target_concat = torch.cat(target_embeddings, dim=-1)
            if hasattr(self, 'target_projection'):
                target_output = self.target_projection(target_concat)
            else:
                target_output = target_concat

        return {
            'static': static_output,
            'known': known_output,
            'observed': observed_output,
            'target': target_output,
        }

class TemporalFusionTransformer(nn.Module):
    """Complete TFT model implementation"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.hidden_size = config.hidden_size
        self.encoder_length = config.encoder_length
        self.decoder_length = config.decoder_length
        self.num_quantiles = config.num_quantiles

        # Input embeddings
        self.embeddings = TFTEmbedding(config)
        # Static encoder
        self.static_encoder = StaticCovariateEncoder(config)
        # Variable selection networks
        self.historical_vsn = VariableSelectionNetwork(
            input_size=self.hidden_size,
            num_inputs=1,
            hidden_size=self.hidden_size,
            dropout=config.dropout
        )
        self.future_vsn = VariableSelectionNetwork(
            input_size=self.hidden_size,
            num_inputs=1,
            hidden_size=self.hidden_size,
            dropout=config.dropout
        )
        # LSTM layers (input_size=hidden_size, output_size=hidden_size)
        self.historical_lstm = nn.LSTM(self.hidden_size, self.hidden_size, batch_first=True)
        self.future_lstm = nn.LSTM(self.hidden_size, self.hidden_size, batch_first=True)
        # Gating and normalization (input_size=hidden_size*2)
        self.gating_layer = nn.Linear(self.hidden_size * 2, self.hidden_size * 2)
        self.gating_layer_norm = nn.LayerNorm(self.hidden_size * 2)
        # Static enrichment (input_size=hidden_size*2)
        self.enrichment_grn = GatedResidualNetwork(
            input_size=self.hidden_size * 2,
            hidden_size=self.hidden_size * 2,
            output_size=self.hidden_size * 2,
            dropout=config.dropout,
            context_size=self.hidden_size
        )
        # Multi-head attention (d_model=hidden_size*2)
        self.attention = InterpretableMultiHeadAttention(
            d_model=self.hidden_size * 2,
            num_heads=config.num_heads,
            dropout=config.attention_dropout
        )
        self.attention_layer_norm = nn.LayerNorm(self.hidden_size * 2)
        # Position-wise GRN (input_size=hidden_size*2)
        self.position_wise_grn = GatedResidualNetwork(
            input_size=self.hidden_size * 2,
            hidden_size=self.hidden_size * 2,
            output_size=self.hidden_size * 2,
            dropout=config.dropout
        )
        # Output projection (input_size=hidden_size*2)
        self.output_projection = nn.Linear(self.hidden_size * 2, self.num_quantiles)

    def forward(self, inputs):
        """Forward pass of TFT model"""
        # Embed inputs
        embeddings = self.embeddings(inputs)

        # Static context - handle case when no static features exist
        batch_size = list(inputs.values())[0].size(0)
        device = list(inputs.values())[0].device

        if embeddings['static'] is not None:
            # For non-sequence data, static_embedding is [batch_size, hidden_size]
            static_embedding = embeddings['static']
            static_context = self.static_encoder(static_embedding)
            cs, ce, ch, cc = static_context
        else:
            # Create dummy static context
            dummy_static = torch.zeros(batch_size, self.hidden_size, device=device)
            static_context = self.static_encoder(dummy_static)
            cs, ce, ch, cc = static_context

        # For non-sequence data, use the full tensor
        if embeddings['target'] is not None:
            historical_features = embeddings['target']
        else:
            historical_features = torch.zeros(batch_size, self.hidden_size, device=device)

        if embeddings['known'] is not None:
            future_features = embeddings['known']
        else:
            future_features = torch.zeros(batch_size, self.hidden_size, device=device)

        # Ensure tensors are contiguous before passing to VSN and LSTM
        historical_features = historical_features.contiguous()
        future_features = future_features.contiguous()

        # Variable selection - single features
        selected_historical, _ = self.historical_vsn(
            historical_features,
            cs
        )
        selected_future, _ = self.future_vsn(
            future_features,
            cs
        )
        selected_historical = selected_historical.contiguous()
        selected_future = selected_future.contiguous()

        # LSTM encoding
        batch_size = selected_historical.size(0)
        # If ch/cc are [batch, seq_len, hidden_size], select last time step
        if ch.dim() == 3:
            ch_lstm = ch[:, -1, :]
            cc_lstm = cc[:, -1, :]
        else:
            ch_lstm = ch
            cc_lstm = cc
        h0 = ch_lstm.unsqueeze(0).contiguous()  # [1, batch_size, hidden_size]
        c0 = cc_lstm.unsqueeze(0).contiguous()  # [1, batch_size, hidden_size]

        historical_lstm_out, _ = self.historical_lstm(selected_historical, (h0, c0))
        future_lstm_out, _ = self.future_lstm(selected_future, (h0, c0))
        historical_lstm_out = historical_lstm_out.contiguous()
        future_lstm_out = future_lstm_out.contiguous()

        # Combine temporal features along feature dimension (dim=2)
        # historical_lstm_out and future_lstm_out: [batch, seq, hidden_size]
        temporal_features = torch.cat([historical_lstm_out, future_lstm_out], dim=2).contiguous()  # [batch, seq, hidden_size*2]

        # Gating and skip connection
        input_embeddings = torch.cat([selected_historical, selected_future], dim=2).contiguous()  # [batch, seq, hidden_size*2]
        gated_temporal = self.gating_layer(temporal_features)
        gated_temporal = gated_temporal + input_embeddings
        gated_temporal = self.gating_layer_norm(gated_temporal)

        # Static enrichment
        enriched = self.enrichment_grn(gated_temporal, ce)

        # Self-attention
        attention_output, attention_weights = self.attention(enriched, enriched, enriched)

        # Residual connection and layer norm
        attention_output = attention_output + enriched
        attention_output = self.attention_layer_norm(attention_output)

        # Position-wise processing
        position_wise_output = self.position_wise_grn(attention_output)

        # Final residual connection
        final_output = position_wise_output + attention_output

        # Extract decoder part and project to quantiles
        decoder_output = final_output[:, -self.decoder_length:, :].contiguous()
        quantile_outputs = self.output_projection(decoder_output)

        return quantile_outputs

# ==============================================================================
# DATASET AND DATALOADER
# ==============================================================================

class TFTDataset(Dataset):
    """Dataset for TFT training and inference"""
    
    def __init__(self, data_path, config, scalers=None, encoders=None, split='train'):
        super().__init__()
        
        self.config = config
        self.data_path = data_path
        self.split = split
        self.example_length = config.example_length
        self.stride = config.stride
        
        # Load data
        if isinstance(data_path, str):
            self.data = pd.read_csv(data_path)
        else:
            self.data = data_path
        
        # Initialize scalers and encoders if not provided
        if scalers is None:
            self.scalers = {}
            self.fit_scalers = True
        else:
            self.scalers = scalers
            self.fit_scalers = False
            
        if encoders is None:
            self.encoders = {}
            self.fit_encoders = True
        else:
            self.encoders = encoders
            self.fit_encoders = False
        
        # Preprocess data
        self._preprocess_data()
        
    def _preprocess_data(self):
        """Preprocess the dataset"""
        # Fix column names and delimiter for electricity dataset
        if isinstance(self.data, pd.DataFrame) and '.' in self.data.columns[0]:
            # Reload with correct delimiter and robust parsing
            self.data = pd.read_csv(self.data_path, delimiter='.', quotechar='"', engine='python', on_bad_lines='skip')
            # Rename columns for compatibility if needed
            self.data.rename(columns={
                'date': 'date',
                'id': 'id',
                'power_usage': 'power_usage',
                'hour': 'hour',
                'day_of_week': 'day_of_week',
                'days_from_start': 'days_from_start'
            }, inplace=True)
        # Remove quotes and convert power_usage to float
        if 'power_usage' in self.data.columns:
            self.data['power_usage'] = (
                self.data['power_usage']
                .astype(str)
                .str.replace('"', '')
                .str.replace(',', '.')
                .astype(float)
            )
        # Handle time features
        if 'hour' not in self.data.columns and 'date' in self.data.columns:
            self.data['date'] = pd.to_datetime(self.data['date'])
            self.data['hour'] = self.data['date'].dt.hour
            self.data['day_of_week'] = self.data['date'].dt.dayofweek
        # Add days_from_start if not present
        if 'days_from_start' not in self.data.columns:
            if 'date' in self.data.columns:
                start_date = self.data['date'].min()
                self.data['days_from_start'] = (self.data['date'] - start_date).dt.days
            else:
                self.data['days_from_start'] = np.arange(len(self.data))
        # Fit scalers and encoders if needed
        for feature in self.config.features:
            if feature.name not in self.data.columns:
                continue
            if feature.embed_type == DataTypes.CONTINUOUS:
                if self.fit_scalers and feature.name not in self.scalers:
                    scaler = StandardScaler()
                    values = self.data[feature.name].values.reshape(-1, 1)
                    scaler.fit(values)
                    self.scalers[feature.name] = scaler
                if feature.name in self.scalers:
                    values = self.data[feature.name].values.reshape(-1, 1)
                    scaled_values = self.scalers[feature.name].transform(values)
                    self.data[feature.name] = scaled_values.flatten()
            elif feature.embed_type == DataTypes.CATEGORICAL:
                if self.fit_encoders and feature.name not in self.encoders:
                    encoder = LabelEncoder()
                    encoder.fit(self.data[feature.name].astype(str))
                    self.encoders[feature.name] = encoder
                if feature.name in self.encoders:
                    encoded_values = self.encoders[feature.name].transform(self.data[feature.name].astype(str))
                    self.data[feature.name] = encoded_values
        # Sort by id and time
        if 'id' in self.data.columns and 'days_from_start' in self.data.columns:
            self.data = self.data.sort_values(['id', 'days_from_start'])
    

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        # Get a window of length example_length ending at idx
        start_idx = max(0, idx - self.example_length + 1)
        end_idx = idx + 1
        window = self.data.iloc[start_idx:end_idx]
        # If window is shorter than example_length, pad at the beginning
        if len(window) < self.example_length:
            pad_len = self.example_length - len(window)
            pad = pd.DataFrame(0, index=range(pad_len), columns=window.columns)
            window = pd.concat([pad, window], ignore_index=True)
        inputs = {}
        for feature in self.config.features:
            values = window[feature.name].values
            if feature.embed_type == DataTypes.CATEGORICAL:
                inputs[feature.name] = torch.tensor(values, dtype=torch.long)
            else:
                inputs[feature.name] = torch.tensor(values, dtype=torch.float32)
        return inputs
    

# Add CONFIGS mapping after config classes
CONFIGS = {
    'electricity': ElectricityConfig,
}

# Add CONFIGS mapping after config classes
CONFIGS = {
    'electricity': ElectricityConfig,
}

# ==============================================================================
# TRAINER CLASS
# ==============================================================================

class TFTTrainer:
    """TFT model trainer"""
    
    def __init__(self, config, device='cpu'):
        self.config = config
        self.device = device
        
        # Initialize model
        self.model = TemporalFusionTransformer(config).to(device)
        
        # Try to compile model for better performance (PyTorch 2.0+)
        try:
            if hasattr(torch, 'compile') and device == 'cpu':
                logger.info("Compiling model for better CPU performance...")
                self.model = torch.compile(self.model, mode='max-autotune')
        except Exception as e:
            logger.warning(f"Model compilation failed: {e}")
        
        # Loss function and optimizer
        self.criterion = QuantileLoss(config).to(device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=config.learning_rate)
        
        # Training state
        self.current_epoch = 0
        self.best_val_loss = float('inf')
        self.patience_counter = 0
        
        # Loss tracking
        self.train_losses = []
        self.val_losses = []
        
    def train_epoch(self, train_loader):
        """Train for one epoch"""
        
        self.model.train()
        total_loss = 0
        num_batches = 0
        total_samples = 0
        
        # Start timing for throughput tracking
        epoch_start_time = time.time()
        
        pbar = tqdm(train_loader, desc=f'Epoch {self.current_epoch}')
        
        for batch_idx, batch in enumerate(pbar):
            batch_start_time = time.time()
            
            # Move to device
            batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v 
                    for k, v in batch.items()}
            
            # Get batch size
            batch_size = list(batch.values())[0].size(0)
            total_samples += batch_size
            
            # Forward pass
            predictions = self.model(batch)
            
            # Get targets
            target_feature = None
            for feature in self.config.features:
                if feature.feature_type == InputTypes.TARGET:
                    target_feature = feature.name
                    break
            
            if target_feature and target_feature in batch:
                target_tensor = batch[target_feature]
                if target_tensor.dim() == 1:
                    target_tensor = target_tensor.unsqueeze(1)
                target_tensor = target_tensor.clone().contiguous()
                targets = target_tensor[:, -self.config.decoder_length:]
                if targets.dim() == 2:
                    targets = targets.unsqueeze(-1)
                targets = targets.expand(-1, -1, self.config.num_quantiles).clone().contiguous()
                print(f"[TRAIN] predictions shape: {predictions.shape}, stride: {predictions.stride()}")
                print(f"[TRAIN] targets shape: {targets.shape}, stride: {targets.stride()}")
                # Calculate loss
                losses = self.criterion(predictions, targets)
                loss = losses.sum()
                # Backward pass
                self.optimizer.zero_grad()
                loss.backward()
                # Gradient clipping
                if self.config.gradient_clipping > 0:
                    metrics_path = os.path.join(args.save_dir, 'throughput_metrics_training.csv')
                    throughput_tracker.save_metrics(metrics_path)
                self.optimizer.step()
                total_loss += loss.item()
                num_batches += 1
                # Calculate batch throughput
                batch_duration = time.time() - batch_start_time
                batch_throughput = batch_size / batch_duration if batch_duration > 0 else 0
                # Update progress bar with throughput
                pbar.set_postfix({
                    'loss': f'{loss.item():.4f}',
                    'throughput': f'{batch_throughput:.1f} samples/s'
                })
        
        # Calculate epoch metrics
        epoch_duration = time.time() - epoch_start_time
        avg_loss = total_loss / num_batches if num_batches > 0 else 0
        
        # Record epoch throughput
        throughput_tracker.record_training_epoch(
            self.current_epoch, total_samples, epoch_duration, avg_loss
        )
        
        logger.info(f"Epoch {self.current_epoch} throughput: "
                   f"{total_samples / epoch_duration:.2f} samples/second "
                   f"({total_samples} samples in {epoch_duration:.2f}s)")

        # Continuously write training metrics after each epoch
        metrics_path = os.path.join('checkpoints', 'throughput_metrics_training.csv')
        throughput_tracker.save_metrics(metrics_path)

        return avg_loss
    
    def validate_epoch(self, val_loader):
        """Validate for one epoch"""
        
        self.model.eval()
        total_loss = 0
        total_qrisk = 0
        num_batches = 0
        
        with torch.no_grad():
            for batch in val_loader:
                # Move to device
                batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v 
                        for k, v in batch.items()}
                
                # Forward pass
                predictions = self.model(batch)
                
                # Get targets
                target_feature = None
                for feature in self.config.features:
                    if feature.feature_type == InputTypes.TARGET:
                        target_feature = feature.name
                        break
                
                if target_feature and target_feature in batch:
                    target_tensor = batch[target_feature]
                    if target_tensor.dim() == 1:
                        target_tensor = target_tensor.unsqueeze(1)
                    target_tensor = target_tensor.clone().contiguous()
                    targets = target_tensor[:, -self.config.decoder_length:]
                    if targets.dim() == 2:
                        targets = targets.unsqueeze(-1)
                    targets = targets.expand(-1, -1, self.config.num_quantiles).clone().contiguous()
                    print(f"[VAL] predictions shape: {predictions.shape}, stride: {predictions.stride()}")
                    print(f"[VAL] targets shape: {targets.shape}, stride: {targets.stride()}")
                    # Calculate losses
                    losses = self.criterion(predictions, targets)
                    loss = losses.sum()
                    # Calculate Q-Risk
                    qrisk = qrisk_metric(predictions, targets, self.config.quantiles)
                    total_loss += loss.item()
                    total_qrisk += qrisk
                    num_batches += 1
        
        avg_loss = total_loss / num_batches if num_batches > 0 else 0
        avg_qrisk = total_qrisk / num_batches if num_batches > 0 else 0
        
        return avg_loss, avg_qrisk
    
    def train(self, train_loader, val_loader, save_dir='checkpoints'):
        """Complete training loop"""
        
        os.makedirs(save_dir, exist_ok=True)
        
        logger.info(f"Starting training for {self.config.epochs} epochs")
        logger.info(f"Model parameters: {sum(p.numel() for p in self.model.parameters())}")
        
        for epoch in range(self.config.epochs):
            self.current_epoch = epoch + 1
            
            # Train
            train_loss = self.train_epoch(train_loader)
            self.train_losses.append(train_loss)
            
            # Validate
            val_loss, val_qrisk = self.validate_epoch(val_loader)
            self.val_losses.append(val_loss)
            
            logger.info(f'Epoch {self.current_epoch}/{self.config.epochs} - '
                       f'Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}, '
                       f'Val Q-Risk: {val_qrisk:.4f}')
            
            # Save checkpoint
            checkpoint_path = os.path.join(save_dir, f'epoch_{self.current_epoch}.pt')
            self.save_checkpoint(checkpoint_path)
            
            # Early stopping
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.patience_counter = 0
                
                # Save best model
                best_path = os.path.join(save_dir, 'best.pt')
                self.save_checkpoint(best_path)
                logger.info(f'✓ New best model saved with val loss: {val_loss:.4f}')
            else:
                self.patience_counter += 1
                
            if self.patience_counter >= self.config.early_stopping:
                logger.info(f'Early stopping at epoch {self.current_epoch}')
                break
        
        logger.info('Training completed!')
        
    def save_checkpoint(self, path):
        """Save model checkpoint"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'config': self.config,
            'epoch': self.current_epoch,
            'best_val_loss': self.best_val_loss,
            'train_losses': self.train_losses,
            'val_losses': self.val_losses,
        }, path)
    
    def load_checkpoint(self, path):
        """Load model checkpoint"""
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        # Handle _orig_mod. prefix in state_dict keys
        state_dict = checkpoint['model_state_dict']
        if any(k.startswith('_orig_mod.') for k in state_dict.keys()):
            new_state_dict = {k.replace('_orig_mod.', ''): v for k, v in state_dict.items()}
            self.model.load_state_dict(new_state_dict)
        else:
            self.model.load_state_dict(state_dict)
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.current_epoch = checkpoint.get('epoch', 0)
        self.best_val_loss = checkpoint.get('best_val_loss', float('inf'))
        self.train_losses = checkpoint.get('train_losses', [])
        self.val_losses = checkpoint.get('val_losses', [])
        return checkpoint['config']

# ==============================================================================
# INFERENCE CLASS
# ==============================================================================

class TFTInference:
    """TFT model inference"""
    
    def __init__(self, checkpoint_path, device='cpu'):
        self.device = device
        
    # Load checkpoint
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
        self.config = checkpoint['config']
        
        # Initialize and load model
        self.model = TemporalFusionTransformer(self.config).to(device)
        # Handle _orig_mod. prefix in state_dict keys
        state_dict = checkpoint['model_state_dict']
        if any(k.startswith('_orig_mod.') for k in state_dict.keys()):
            new_state_dict = {k.replace('_orig_mod.', ''): v for k, v in state_dict.items()}
            self.model.load_state_dict(new_state_dict)
        else:
            self.model.load_state_dict(state_dict)
        self.model.eval()
        
        logger.info(f"Loaded model from {checkpoint_path}")
    
    def predict(self, data_loader):
        """Make predictions on a dataset"""
        
        predictions = []
        targets = []
        
        self.model.eval()
        with torch.no_grad():
            for batch in tqdm(data_loader, desc='Making predictions'):
                # Move to device
                batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v 
                        for k, v in batch.items()}
                
                # Forward pass
                pred = self.model(batch)
                predictions.append(pred.cpu())
                
                # Extract targets
                target_feature = None
                for feature in self.config.features:
                    if feature.feature_type == InputTypes.TARGET:
                        target_feature = feature.name
                        break
                
                if target_feature and target_feature in batch:
                    target = batch[target_feature][:, -self.config.decoder_length:]
                    targets.append(target.cpu())
        
            predictions = torch.cat(predictions, dim=0)
            if len(targets) > 0:
                targets = torch.cat(targets, dim=0)
                return predictions, targets
            else:
                return predictions, None
    
    def predict_single(self, inputs):
        """Make prediction on a single input"""
        
        self.model.eval()
        with torch.no_grad():
            # Move inputs to device
            inputs = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v 
                     for k, v in inputs.items()}
            
            # Add batch dimension if needed
            for k, v in inputs.items():
                if isinstance(v, torch.Tensor) and v.dim() == 1:
                    inputs[k] = v.unsqueeze(0)
            
            # Forward pass
            prediction = self.model(inputs)
            
        return prediction.cpu()
    
    def continuous_inference_benchmark(self, data_loader, num_samples=100, num_runs=10):
        """Run continuous inference benchmark measuring throughput"""
        
        logger.info(f"Starting continuous inference benchmark...")
        logger.info(f"Target samples per run: {num_samples}, Number of runs: {num_runs}")
        
        self.model.eval()
        
        # Collect sample batches
        sample_batches = []
        samples_collected = 0
        
        for batch in data_loader:
            if samples_collected >= num_samples:
                break
                
            batch_size = list(batch.values())[0].size(0)
            remaining_samples = num_samples - samples_collected
            
            if batch_size > remaining_samples:
                # Take only the needed samples from this batch
                truncated_batch = {}
                for k, v in batch.items():
                    if isinstance(v, torch.Tensor):
                        truncated_batch[k] = v[:remaining_samples]
                    else:
                        truncated_batch[k] = v
                sample_batches.append(truncated_batch)
                samples_collected += remaining_samples
            else:
                sample_batches.append(batch)
                samples_collected += batch_size
        
        logger.info(f"Collected {samples_collected} samples in {len(sample_batches)} batches")
        
        # Run continuous inference
        run_throughputs = []
        
        for run_idx in range(num_runs):
            logger.info(f"Starting inference run {run_idx + 1}/{num_runs}")
            
            run_start_time = time.time()
            total_predictions = 0
            
            with torch.no_grad():
                for batch_idx, batch in enumerate(sample_batches):
                    batch_start_time = time.time()
                    
                    # Move to device
                    batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v 
                            for k, v in batch.items()}
                    
                    # Get batch size
                    batch_size = list(batch.values())[0].size(0)
                    
                    # Forward pass
                    predictions = self.model(batch)
                    
                    # Wait for completion (synchronize)
                    if self.device.startswith('cuda'):
                        torch.cuda.synchronize()
                    
                    total_predictions += batch_size
                    
                    # Record batch throughput
                    batch_duration = time.time() - batch_start_time
                    throughput_tracker.record_inference_batch(batch_size, batch_duration)

                    # Continuously write inference metrics after each batch
                    metrics_path = os.path.join('checkpoints', 'throughput_metrics_inference.csv')
                    throughput_tracker.save_metrics(metrics_path)

                    # Progress update every 10 batches
                    if (batch_idx + 1) % 10 == 0:
                        batch_throughput = batch_size / batch_duration
                        logger.info(f"  Batch {batch_idx + 1}/{len(sample_batches)}: "
                                  f"{batch_throughput:.2f} samples/s")
            
            run_duration = time.time() - run_start_time
            run_throughput = total_predictions / run_duration
            run_throughputs.append(run_throughput)
            
            logger.info(f"Run {run_idx + 1} completed: {run_throughput:.2f} samples/second "
                       f"({total_predictions} samples in {run_duration:.2f}s)")
        
        # Calculate statistics
        avg_throughput = sum(run_throughputs) / len(run_throughputs)
        min_throughput = min(run_throughputs)
        max_throughput = max(run_throughputs)
        
        logger.info("=== CONTINUOUS INFERENCE RESULTS ===")
        logger.info(f"Average throughput: {avg_throughput:.2f} samples/second")
        logger.info(f"Min throughput: {min_throughput:.2f} samples/second")
        logger.info(f"Max throughput: {max_throughput:.2f} samples/second")
        logger.info(f"Total runs: {num_runs}")
        logger.info(f"Samples per run: {samples_collected}")
        
        return {
            'avg_throughput': avg_throughput,
            'min_throughput': min_throughput,
            'max_throughput': max_throughput,
            'run_throughputs': run_throughputs,
            'total_samples': samples_collected,
            'num_runs': num_runs
        }

# ==============================================================================
# MAIN TRAINING/INFERENCE FUNCTIONS
# ==============================================================================

def create_data_loaders(args, config):
    # Load all splits for fitting encoders
    train_path = os.path.join(args.data_path, 'train_small.csv')
    val_path = os.path.join(args.data_path, 'val_small.csv')
    test_path = os.path.join(args.data_path, 'test_small.csv')
    train_df = pd.read_csv(train_path, delimiter='.', quotechar='"', engine='python', on_bad_lines='skip')
    val_df = pd.read_csv(val_path, delimiter='.', quotechar='"', engine='python', on_bad_lines='skip')
    test_df = pd.read_csv(test_path, delimiter='.', quotechar='"', engine='python', on_bad_lines='skip')

    # Concatenate for fitting encoders
    all_df = pd.concat([train_df, val_df, test_df], axis=0, ignore_index=True)

    # Fit encoders and scalers on all data
    encoders = {}
    scalers = {}
    for feature in config.features:
        if feature.embed_type == DataTypes.CATEGORICAL:
            encoder = LabelEncoder()
            encoder.fit(all_df[feature.name].astype(str))
            encoders[feature.name] = encoder
        elif feature.embed_type == DataTypes.CONTINUOUS:
            scaler = StandardScaler()
            scaler.fit(all_df[feature.name].values.reshape(-1, 1))
            scalers[feature.name] = scaler

    train_dataset = TFTDataset(train_df, config, scalers=scalers, encoders=encoders, split='train')
    val_dataset = TFTDataset(val_df, config, scalers=scalers, encoders=encoders, split='val')
    test_dataset = TFTDataset(test_df, config, scalers=scalers, encoders=encoders, split='test')

    train_loader = DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True, num_workers=0, drop_last=True)
    val_loader = DataLoader(val_dataset, batch_size=config.batch_size, shuffle=False, num_workers=0, drop_last=True)
    test_loader = DataLoader(test_dataset, batch_size=config.batch_size, shuffle=False, num_workers=0, drop_last=True)

    return train_loader, val_loader, test_loader

def train_model(args):
    """Main training function"""
    
    # Get configuration
    if args.dataset not in CONFIGS:
        raise ValueError(f"Unknown dataset: {args.dataset}")
    
    config = CONFIGS[args.dataset]()
    
    # Override config with command line arguments
    if args.batch_size:
        config.batch_size = args.batch_size
    if args.epochs:
        config.epochs = args.epochs
    if args.lr:
        config.learning_rate = args.lr
    
    logger.info(f"Training TFT model on {args.dataset} dataset")
    logger.info(f"Configuration: {config.__dict__}")
    
    # Create data loaders
    train_loader, val_loader, test_loader = create_data_loaders(args, config)
    
    # Initialize trainer
    device = 'cuda' if torch.cuda.is_available() and not args.cpu_only else 'cpu'
    logger.info(f"Using device: {device}")
    
    trainer = TFTTrainer(config, device=device)
    
    # Train model
    trainer.train(train_loader, val_loader, save_dir=args.save_dir)
    
    # Test final model
    logger.info("Evaluating on test set...")
    test_loss, test_qrisk = trainer.validate_epoch(test_loader)
    logger.info(f"Test Loss: {test_loss:.4f}, Test Q-Risk: {test_qrisk:.4f}")
    
    # Run continuous inference benchmark
    logger.info("Starting continuous inference benchmark...")
    best_checkpoint = os.path.join(args.save_dir, 'best.pt')
    if os.path.exists(best_checkpoint):
        # Create inference object
        inferencer = TFTInference(best_checkpoint, device=device)
        
        # Run continuous inference with 100 samples, 10 runs
        inference_results = inferencer.continuous_inference_benchmark(
            test_loader, num_samples=100, num_runs=10
        )
        
        # Save results
        results_dir = os.path.join(args.save_dir, 'benchmark_results')
        os.makedirs(results_dir, exist_ok=True)
        
        # Save inference benchmark results
        inference_results_path = os.path.join(results_dir, 'inference_benchmark.json')
        with open(inference_results_path, 'w') as f:
            json.dump(inference_results, f, indent=2)
        
        # Save all throughput metrics
        metrics_path = os.path.join(results_dir, 'throughput_metrics.csv')
        throughput_tracker.save_metrics(metrics_path)
        
        # Print summary
        throughput_tracker.print_summary()
        
        logger.info(f"Benchmark results saved to: {results_dir}")
    else:
        logger.warning(f"Best checkpoint not found at {best_checkpoint}, skipping inference benchmark")

def run_inference(args):
    """Main inference function"""
    
    while True:
        if not os.path.exists(args.checkpoint):
            logger.error(f"Checkpoint not found: {args.checkpoint}")
            time.sleep(10)
            continue
        # Initialize inference
        device = 'cuda' if torch.cuda.is_available() and not args.cpu_only else 'cpu'
        logger.info(f"Using device: {device}")
        inferencer = TFTInference(args.checkpoint, device=device)
        if args.data:
            # Load data
            if args.scalers and args.encoders:
                with open(args.scalers, 'rb') as f:
                    scalers = pickle.load(f)
                with open(args.encoders, 'rb') as f:
                    encoders = pickle.load(f)
            else:
                scalers = None
                encoders = None
            dataset = TFTDataset(args.data, inferencer.config,
                               scalers=scalers, encoders=encoders, split='test')
            data_loader = DataLoader(dataset, batch_size=args.batch_size or 64,
                       shuffle=False, num_workers=0, drop_last=True)
            # Make predictions
            predictions, targets = inferencer.predict(data_loader)
            # Calculate metrics if targets available
            if targets is not None:
                qrisk = qrisk_metric(predictions, targets.unsqueeze(-1), inferencer.config.quantiles)
                logger.info(f"Q-Risk: {qrisk:.4f}")
            # Save predictions if requested
            if args.save_predictions:
                pred_path = os.path.join(args.results or '.', 'predictions.pt')
                torch.save({'predictions': predictions, 'targets': targets}, pred_path)
                logger.info(f"Predictions saved to {pred_path}")
            logger.info(f"Inference completed on {len(dataset)} samples (looping)")
        else:
            logger.info("No data provided for inference")

def run_benchmark(args):
    """Run continuous inference benchmark on pre-trained model"""
    
    if not args.checkpoint:
        raise ValueError("Benchmark mode requires --checkpoint")
    
    if not args.data:
        raise ValueError("Benchmark mode requires --data")
    
    logger.info("Running continuous inference benchmark...")
    
    # Initialize inference
    device = 'cuda' if torch.cuda.is_available() and not args.cpu_only else 'cpu'
    logger.info(f"Using device: {device}")
    
    inferencer = TFTInference(args.checkpoint, device=device)
    
    # Load data
    if args.scalers and args.encoders:
        with open(args.scalers, 'rb') as f:
            scalers = pickle.load(f)
        with open(args.encoders, 'rb') as f:
            encoders = pickle.load(f)
    else:
        scalers = None
        encoders = None
    
    dataset = TFTDataset(args.data, inferencer.config,
                       scalers=scalers, encoders=encoders, split='test')
    
    # Use all cores for data loading
    num_workers = num_cores  # Limit to 8 to avoid too many file handles
    data_loader = DataLoader(dataset, batch_size=args.batch_size or 64,
                           shuffle=False, num_workers=num_workers,
                           pin_memory=False, persistent_workers=True, drop_last=True)
    
    while True:
        # Run benchmark
        num_samples = args.benchmark_samples or 100
        num_runs = args.benchmark_runs or 10
        
        inference_results = inferencer.continuous_inference_benchmark(
            data_loader, num_samples=num_samples, num_runs=num_runs
        )
        
        # Save results
        results_dir = args.results or './benchmark_results'
        os.makedirs(results_dir, exist_ok=True)
        
        # Save inference benchmark results
        inference_results_path = os.path.join(results_dir, 'inference_benchmark.json')
        with open(inference_results_path, 'w') as f:
            json.dump(inference_results, f, indent=2)
        
        # Save throughput metrics
        metrics_path = os.path.join(results_dir, 'throughput_metrics.csv')
        throughput_tracker.save_metrics(metrics_path)
        
        # Print summary
        throughput_tracker.print_summary()
        
        logger.info(f"Benchmark results saved to: {results_dir}")

def test_model():
    """Test model creation and forward pass"""
    
    logger.info("Testing TFT model...")
    
    # Create test configuration
    config = ElectricityConfig()
    config.batch_size = 2
    
    # Create dummy data matching the electricity feature set
    batch_size = config.batch_size
    seq_len = config.example_length
    
    dummy_inputs = {
        'id': torch.randint(0, 370, (batch_size, seq_len)),           # Client IDs (0-369)
        'hour': torch.randint(0, 24, (batch_size, seq_len)),          # Hour of day (0-23)
        'day_of_week': torch.randint(0, 7, (batch_size, seq_len)),    # Day of week (0-6)
        'power_usage': torch.randn(batch_size, seq_len),              # Target variable
    }
    
    # Create model
    model = TemporalFusionTransformer(config)
    
    # Test forward pass
    try:
        with torch.no_grad():
            outputs = model(dummy_inputs)
        
        logger.info(f"✓ Model forward pass successful!")
        logger.info(f"  Input shape: {dummy_inputs['power_usage'].shape}")
        logger.info(f"  Output shape: {outputs.shape}")
        logger.info(f"  Expected output shape: [batch_size, decoder_length, num_quantiles]")
        logger.info(f"  Model parameters: {sum(p.numel() for p in model.parameters())}")
        
    except Exception as e:
        logger.error(f"✗ Model test failed: {e}")
        raise

# ==============================================================================
# COMMAND LINE INTERFACE
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description='TFT Training and Inference')
    
    # Mode selection
    parser.add_argument('--mode', type=str, required=True,
                       choices=['train', 'inference', 'test', 'benchmark', 'throughput'],
                       help='Mode: train, inference, test, benchmark, or throughput')
    
    # Training arguments
    parser.add_argument('--dataset', type=str, choices=['electricity'], default='electricity',
                       help='Dataset name (only electricity supported)')
    parser.add_argument('--data_path', type=str,
                       help='Path to dataset directory')
    parser.add_argument('--epochs', type=int,
                       help='Number of training epochs')
    parser.add_argument('--batch_size', type=int,
                       help='Batch size')
    parser.add_argument('--lr', type=float,
                       help='Learning rate')
    parser.add_argument('--save_dir', type=str, default='checkpoints',
                       help='Directory to save checkpoints')
    
    # Inference arguments
    parser.add_argument('--checkpoint', type=str,
                       help='Path to model checkpoint')
    parser.add_argument('--data', type=str,
                       help='Path to inference data CSV')
    parser.add_argument('--scalers', type=str,
                       help='Path to scalers pickle file')
    parser.add_argument('--encoders', type=str,
                       help='Path to encoders pickle file')
    parser.add_argument('--save_predictions', action='store_true',
                       help='Save predictions to file')
    parser.add_argument('--results', type=str,
                       help='Directory to save results')
    
    # Benchmark arguments
    parser.add_argument('--benchmark_samples', type=int, default=100,
                       help='Number of samples for inference benchmark')
    parser.add_argument('--benchmark_runs', type=int, default=10,
                       help='Number of benchmark runs')
    
    # General arguments
    parser.add_argument('--cpu_only', action='store_true',
                       help='Force CPU usage even if CUDA is available')
    
    args = parser.parse_args()
    while True:
        try:
            if args.mode == 'train':
                if not args.dataset or not args.data_path:
                    raise ValueError("Training mode requires --dataset and --data_path")
                train_model(args)
            elif args.mode == 'inference':
                if not args.checkpoint:
                    raise ValueError("Inference mode requires --checkpoint")
                run_inference(args)
            elif args.mode == 'test':
                test_model()
            elif args.mode == 'benchmark':
                run_benchmark(args)
            elif args.mode == 'throughput':
                run_throughput_mode(args)
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(10)
            continue

if __name__ == '__main__':
    sys.exit(main())