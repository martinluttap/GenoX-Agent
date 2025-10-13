#!/usr/bin/env python3
print("Script started")
"""
Complete Jasper Speech Recognition Implementation
Based on NVIDIA DeepLearningExamples but optimized for CPU-only execution.

This script provides a complete implementation including:
- Model architecture (JasperBlock, JasperEncoder, JasperDecoder)
- Training pipeline with CTC loss
- Inference capabilities
- Audio processing with mel-spectrograms
- Data loading for LibriSpeech format
- Configuration management

Usage:
    # Training
    
    
    
    # Inference
    python jasper_complete.py --mode inference --checkpoint model.pt --audio_file test.wav
    
    # Test model
    python jasper_complete.py --mode test
"""

import os
import sys
import json
import yaml
import argparse
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
from collections import OrderedDict

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import torchaudio
import numpy as np
import librosa
import soundfile as sf
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ==============================================================================
# TEXT ENCODING
# ==============================================================================

class TextEncoder:
    """Text encoder for converting between text and token sequences"""
    
    def __init__(self):
        # Standard English alphabet + space + apostrophe + blank token for CTC
        self.labels = [
            ' ', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 
            'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', "'", '<BLANK>'
        ]
        self.label_to_id = {label: i for i, label in enumerate(self.labels)}
        self.id_to_label = {i: label for i, label in enumerate(self.labels)}
        self.blank_id = len(self.labels) - 1  # CTC blank token
    
    def encode(self, text: str) -> List[int]:
        """Convert text to list of token IDs"""
        text = text.lower().strip()
        tokens = []
        for char in text:
            if char in self.label_to_id:
                tokens.append(self.label_to_id[char])
            # Skip unknown characters
        return tokens
    
    def decode(self, tokens: List[int]) -> str:
        """Convert list of token IDs to text"""
        chars = []
        for token_id in tokens:
            if token_id < len(self.labels) and token_id != self.blank_id:
                chars.append(self.id_to_label[token_id])
        return ''.join(chars).strip()
    
    def vocab_size(self) -> int:
        """Return vocabulary size including blank token"""
        return len(self.labels)


# ==============================================================================
# AUDIO PROCESSING
# ==============================================================================

class MelSpectrogramFeatures(nn.Module):
    """Mel-scale spectrogram feature extraction"""
    
    def __init__(self, sample_rate: int = 16000, n_mels: int = 64, n_fft: int = 512, 
                 hop_length: int = 160, win_length: int = 320, f_min: float = 0.0, 
                 f_max: Optional[float] = None):
        super().__init__()
        self.sample_rate = sample_rate
        self.n_mels = n_mels
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.win_length = win_length
        self.f_min = f_min
        self.f_max = f_max or sample_rate // 2
        
        # Create mel filterbank
        self.mel_transform = torchaudio.transforms.MelSpectrogram(
            sample_rate=sample_rate,
            n_fft=n_fft,
            win_length=win_length,
            hop_length=hop_length,
            n_mels=n_mels,
            f_min=f_min,
            f_max=self.f_max,
            power=2.0,
            normalized=False
        )
        
    def forward(self, audio: torch.Tensor) -> torch.Tensor:
        """
        Args:
            audio: (batch_size, time) or (batch_size, 1, time)
        Returns:
            features: (batch_size, n_mels, time_frames)
        """
        if audio.dim() == 3:
            audio = audio.squeeze(1)  # Remove channel dimension if present
            
        # Compute mel spectrogram
        mel_spec = self.mel_transform(audio)
        
        # Convert to log scale
        mel_spec = torch.clamp(mel_spec, min=1e-10)
        log_mel = torch.log(mel_spec)
        
        return log_mel


class SpecAugment(nn.Module):
    """SpecAugment data augmentation for spectrograms"""
    
    def __init__(self, freq_masks: int = 2, freq_width: int = 5, 
                 time_masks: int = 2, time_width: int = 10):
        super().__init__()
        self.freq_masks = freq_masks
        self.freq_width = freq_width
        self.time_masks = time_masks
        self.time_width = time_width
        
    def forward(self, spectrogram: torch.Tensor) -> torch.Tensor:
        """
        Args:
            spectrogram: (batch_size, freq_bins, time_frames)
        Returns:
            Augmented spectrogram with same shape
        """
        if not self.training:
            return spectrogram
            
        batch_size, freq_bins, time_frames = spectrogram.shape
        augmented = spectrogram.clone()
        
        for batch_idx in range(batch_size):
            # Frequency masking
            for _ in range(self.freq_masks):
                f_start = torch.randint(0, max(1, freq_bins - self.freq_width), (1,)).item()
                f_end = min(f_start + self.freq_width, freq_bins)
                augmented[batch_idx, f_start:f_end, :] = 0
            
            # Time masking
            for _ in range(self.time_masks):
                t_start = torch.randint(0, max(1, time_frames - self.time_width), (1,)).item()
                t_end = min(t_start + self.time_width, time_frames)
                augmented[batch_idx, :, t_start:t_end] = 0
                
        return augmented


class AudioProcessor(nn.Module):
    """Complete audio processing pipeline"""
    
    def __init__(self, feature_config: Dict, augment_config: Optional[Dict] = None):
        super().__init__()
        self.mel_extractor = MelSpectrogramFeatures(**feature_config)
        
        # Optional augmentation
        if augment_config:
            self.augmentation = SpecAugment(**augment_config)
        else:
            self.augmentation = None
            
    def forward(self, audio: torch.Tensor, audio_lens: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            audio: (batch_size, max_time)
            audio_lens: (batch_size,) actual lengths of audio sequences
        Returns:
            features: (batch_size, n_mels, time_frames)
            feat_lens: (batch_size,) actual lengths of feature sequences
        """
        # Extract mel features
        features = self.mel_extractor(audio)
        
        # Calculate feature lengths
        feat_lens = torch.div(audio_lens, self.mel_extractor.hop_length, rounding_mode='floor')
        feat_lens = torch.clamp(feat_lens, max=features.shape[2])
        
        # Account for stride in first conv layer (reduces sequence length by factor of 2)
        feat_lens = torch.div(feat_lens, 2, rounding_mode='floor')
        feat_lens = torch.clamp(feat_lens, min=1)  # Ensure at least 1 frame
        
        # Apply augmentation if training
        if self.augmentation and self.training:
            features = self.augmentation(features)
            
        return features, feat_lens


def load_audio(file_path: str, sample_rate: int = 16000) -> torch.Tensor:
    """Load audio file and convert to tensor"""
    try:
        # Try with torchaudio first
        audio, sr = torchaudio.load(file_path)
        if sr != sample_rate:
            resampler = torchaudio.transforms.Resample(sr, sample_rate)
            audio = resampler(audio)
    except:
        # Fallback to librosa
        audio, sr = librosa.load(file_path, sr=sample_rate, mono=True)
        audio = torch.from_numpy(audio).float()
        if audio.dim() == 1:
            audio = audio.unsqueeze(0)
    
    # Ensure mono
    if audio.shape[0] > 1:
        audio = torch.mean(audio, dim=0, keepdim=True)
    
    return audio


# ==============================================================================
# MODEL ARCHITECTURE
# ==============================================================================

class JasperBlock(nn.Module):
    """Jasper convolutional block with residual connections"""
    
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 11,
                 stride: int = 1, dilation: int = 1, dropout: float = 0.1,
                 repeat: int = 3, separable: bool = False, residual: bool = True,
                 residual_dense: bool = False):
        super().__init__()
        
        self.repeat = repeat
        self.residual = residual
        self.residual_dense = residual_dense
        self.out_channels = out_channels
        
        # Padding to maintain sequence length (except for stride > 1)
        padding = (kernel_size - 1) // 2 * dilation
        
        # Repeated convolution blocks
        self.conv_layers = nn.ModuleList()
        self.bn_layers = nn.ModuleList()
        self.dropout_layers = nn.ModuleList()
        
        for i in range(repeat):
            conv_in_channels = in_channels if i == 0 else out_channels
            
            if separable and kernel_size > 1:
                # Depthwise separable convolution
                conv = nn.Sequential(
                    nn.Conv1d(conv_in_channels, conv_in_channels, kernel_size, 
                             stride=stride if i == 0 else 1, padding=padding, 
                             dilation=dilation, groups=conv_in_channels, bias=False),
                    nn.Conv1d(conv_in_channels, out_channels, 1, bias=False)
                )
            else:
                # Standard convolution
                conv = nn.Conv1d(conv_in_channels, out_channels, kernel_size,
                               stride=stride if i == 0 else 1, padding=padding,
                               dilation=dilation, bias=False)
            
            self.conv_layers.append(conv)
            self.bn_layers.append(nn.BatchNorm1d(out_channels))
            self.dropout_layers.append(nn.Dropout(dropout))
        
        # Residual connection projection if needed
        self.residual_projection = None
        if residual and (in_channels != out_channels or stride != 1):
            self.residual_projection = nn.Conv1d(in_channels, out_channels, 
                                               kernel_size=1, stride=stride, bias=False)
            self.residual_bn = nn.BatchNorm1d(out_channels)
        
        self.activation = nn.ReLU()
        
    def forward(self, x: torch.Tensor, dense_residuals: Optional[List[torch.Tensor]] = None) -> torch.Tensor:
        """
        Args:
            x: (batch_size, in_channels, time)
            dense_residuals: List of tensors for dense residual connections
        Returns:
            output: (batch_size, out_channels, time)
        """
        residual = x
        
        # Apply repeated convolutions
        for i in range(self.repeat):
            x = self.conv_layers[i](x)
            x = self.bn_layers[i](x)
            
            if i < self.repeat - 1:  # No activation after last layer
                x = self.activation(x)
                x = self.dropout_layers[i](x)
        
        # Residual connection
        if self.residual:
            if self.residual_projection is not None:
                residual = self.residual_projection(residual)
                residual = self.residual_bn(residual)
            
            # Add dense residuals if provided
            if self.residual_dense and dense_residuals:
                for dense_res in dense_residuals:
                    if dense_res.shape == residual.shape:
                        residual = residual + dense_res
            
            x = x + residual
        
        # Final activation
        x = self.activation(x)
        x = self.dropout_layers[-1](x)
        
        return x


class JasperEncoder(nn.Module):
    """Jasper encoder consisting of multiple JasperBlocks"""
    
    def __init__(self, in_channels: int = 64, init_norm: str = 'batch',
                 init_norm_params: Dict = None, blocks: List[Dict] = None):
        super().__init__()
        
        if init_norm_params is None:
            init_norm_params = {}
        if blocks is None:
            blocks = []
            
        self.in_channels = in_channels
        
        # Initial normalization
        if init_norm == 'batch':
            self.init_norm = nn.BatchNorm1d(in_channels, **init_norm_params)
        elif init_norm == 'layer':
            self.init_norm = nn.LayerNorm(in_channels, **init_norm_params)
        else:
            self.init_norm = nn.Identity()
        
        # Jasper blocks
        self.blocks = nn.ModuleList()
        current_channels = in_channels
        
        for i, block_config in enumerate(blocks):
            block = JasperBlock(
                in_channels=current_channels,
                out_channels=block_config['out_channels'],
                kernel_size=block_config.get('kernel_size', 11),
                stride=block_config.get('stride', 1),
                dilation=block_config.get('dilation', 1),
                dropout=block_config.get('dropout', 0.1),
                repeat=block_config.get('repeat', 3),
                separable=block_config.get('separable', False),
                residual=block_config.get('residual', True),
                residual_dense=block_config.get('residual_dense', False)
            )
            self.blocks.append(block)
            current_channels = block_config['out_channels']
        
        self.out_channels = current_channels
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch_size, in_channels, time)
        Returns:
            output: (batch_size, out_channels, time)
        """
        # Initial normalization
        x = self.init_norm(x)
        
        # Store outputs for dense residual connections
        dense_residuals = []
        
        # Apply Jasper blocks
        for block in self.blocks:
            # Dense residual: pass all previous outputs to residual_dense blocks
            if block.residual_dense:
                x = block(x, dense_residuals)
            else:
                x = block(x)
            
            # Store output for future dense residual connections
            dense_residuals.append(x)
        
        return x


class JasperDecoderForCTC(nn.Module):
    """Jasper decoder for CTC loss"""
    
    def __init__(self, in_channels: int, n_classes: int, init_norm: str = 'batch',
                 init_norm_params: Dict = None):
        super().__init__()
        
        if init_norm_params is None:
            init_norm_params = {}
            
        # Decoder layers
        layers = []
        
        # Optional normalization
        if init_norm == 'batch':
            layers.append(nn.BatchNorm1d(in_channels, **init_norm_params))
        elif init_norm == 'layer':
            layers.append(nn.LayerNorm(in_channels, **init_norm_params))
        
        # Final projection to vocabulary
        layers.append(nn.Conv1d(in_channels, n_classes, kernel_size=1, bias=True))
        
        self.decoder = nn.Sequential(*layers)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch_size, in_channels, time)
        Returns:
            logits: (batch_size, time, n_classes) - ready for CTC loss
        """
        x = self.decoder(x)  # (batch_size, n_classes, time)
        x = x.transpose(1, 2)  # (batch_size, time, n_classes)
        return x


class Jasper(nn.Module):
    """Complete Jasper model"""
    
    def __init__(self, encoder_kw: Dict, decoder_kw: Dict):
        super().__init__()
        
        self.encoder = JasperEncoder(**encoder_kw)
        self.decoder = JasperDecoderForCTC(
            in_channels=self.encoder.out_channels,
            **decoder_kw
        )
        
    def forward(self, features: torch.Tensor) -> torch.Tensor:
        """
        Args:
            features: (batch_size, n_mels, time)
        Returns:
            logits: (batch_size, time, n_classes)
        """
        x = self.encoder(features)
        logits = self.decoder(x)
        return logits


class GreedyCTCDecoder:
    """Greedy CTC decoder for inference"""
    
    def __init__(self):
        pass
        
    def __call__(self, log_probs: torch.Tensor) -> torch.Tensor:
        """
        Args:
            log_probs: (batch_size, time, n_classes)
        Returns:
            predictions: (batch_size, decoded_length)
        """
        # Get most likely tokens
        predictions = torch.argmax(log_probs, dim=-1)  # (batch_size, time)
        
        # Remove consecutive duplicates and blank tokens
        decoded_predictions = []
        for batch_idx in range(predictions.shape[0]):
            pred_seq = predictions[batch_idx]
            decoded = []
            prev_token = -1
            
            for token in pred_seq:
                token = token.item()
                if token != prev_token:  # Remove consecutive duplicates
                    decoded.append(token)
                prev_token = token
            
            decoded_predictions.append(torch.tensor(decoded))
        
        return decoded_predictions


# ==============================================================================
# DATA LOADING
# ==============================================================================

class JasperDataset(Dataset):
    """Dataset for Jasper training"""
    
    def __init__(self, manifest_path: str, text_encoder: TextEncoder, 
                 max_duration: float = 16.7, min_duration: float = 0.1,
                 sample_rate: int = 16000):
        self.text_encoder = text_encoder
        self.max_duration = max_duration
        self.min_duration = min_duration
        self.sample_rate = sample_rate
        self.manifest_dir = os.path.dirname(manifest_path)
        
        # Load manifest
        self.data = []
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                for line in f:
                    item = json.loads(line.strip())
                    duration = item.get('duration', 0)
                    if self.min_duration <= duration <= self.max_duration:
                        self.data.append(item)
        else:
            logger.warning(f"Manifest file not found: {manifest_path}")
        
        logger.info(f"Loaded {len(self.data)} audio samples from {manifest_path}")
        
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        
        # Load audio
        audio_path = item['audio_filepath']
        if not os.path.isabs(audio_path):
            # If relative path, make it relative to manifest directory
            audio_path = os.path.join(self.manifest_dir, audio_path)
            
        try:
            audio = load_audio(audio_path, self.sample_rate)
            audio = audio.squeeze()  # Remove channel dimension
        except Exception as e:
            logger.warning(f"Failed to load audio {audio_path}: {e}")
            # Return silence as fallback
            audio = torch.zeros(self.sample_rate)
        
        # Encode text
        text = item.get('text', '')
        tokens = self.text_encoder.encode(text)
        
        return {
            'audio': audio,
            'tokens': torch.tensor(tokens, dtype=torch.long),
            'audio_len': torch.tensor(len(audio), dtype=torch.long),
            'tokens_len': torch.tensor(len(tokens), dtype=torch.long),
            'text': text,
            'audio_path': audio_path
        }


def collate_fn(batch):
    """Collate function for DataLoader with padding"""
    # Sort by audio length (descending) for efficient packing
    batch = sorted(batch, key=lambda x: x['audio_len'], reverse=True)
    
    # Get dimensions
    batch_size = len(batch)
    max_audio_len = batch[0]['audio_len'].item()
    max_tokens_len = max(item['tokens_len'].item() for item in batch)
    
    # Initialize padded tensors
    audio_batch = torch.zeros(batch_size, max_audio_len)
    tokens_batch = torch.zeros(batch_size, max_tokens_len, dtype=torch.long)
    audio_lens = torch.zeros(batch_size, dtype=torch.long)
    tokens_lens = torch.zeros(batch_size, dtype=torch.long)
    
    texts = []
    audio_paths = []
    
    # Fill tensors
    for i, item in enumerate(batch):
        audio_len = item['audio_len'].item()
        tokens_len = item['tokens_len'].item()
        
        audio_batch[i, :audio_len] = item['audio']
        tokens_batch[i, :tokens_len] = item['tokens']
        audio_lens[i] = audio_len
        tokens_lens[i] = tokens_len
        
        texts.append(item['text'])
        audio_paths.append(item['audio_path'])
    
    return {
        'audio': audio_batch,
        'tokens': tokens_batch,
        'audio_lens': audio_lens,
        'tokens_lens': tokens_lens,
        'texts': texts,
        'audio_paths': audio_paths
    }


# ==============================================================================
# CONFIGURATION
# ==============================================================================

def create_jasper_5x3_config():
    """Create Jasper 5x3 configuration"""
    return {
        'model': {
            'encoder': {
                'in_channels': 64,
                'init_norm': 'batch',
                'init_norm_params': {},
                'blocks': [
                    {
                        'out_channels': 256,
                        'kernel_size': 11,
                        'stride': 2,
                        'dilation': 1,
                        'dropout': 0.2,
                        'repeat': 1,
                        'separable': True,
                        'residual': False,
                        'residual_dense': False
                    },
                    {
                        'out_channels': 256,
                        'kernel_size': 11,
                        'stride': 1,
                        'dilation': 1,
                        'dropout': 0.2,
                        'repeat': 3,
                        'separable': True,
                        'residual': True,
                        'residual_dense': True
                    },
                    {
                        'out_channels': 384,
                        'kernel_size': 11,
                        'stride': 1,
                        'dilation': 1,
                        'dropout': 0.2,
                        'repeat': 3,
                        'separable': True,
                        'residual': True,
                        'residual_dense': True
                    },
                    {
                        'out_channels': 512,
                        'kernel_size': 11,
                        'stride': 1,
                        'dilation': 1,
                        'dropout': 0.2,
                        'repeat': 3,
                        'separable': True,
                        'residual': True,
                        'residual_dense': True
                    },
                    {
                        'out_channels': 640,
                        'kernel_size': 39,
                        'stride': 1,
                        'dilation': 1,
                        'dropout': 0.3,
                        'repeat': 1,
                        'separable': False,
                        'residual': True,
                        'residual_dense': False
                    }
                ]
            },
            'decoder': {
                'n_classes': 29,  # Will be updated based on text encoder
                'init_norm': 'batch',
                'init_norm_params': {}
            }
        },
        'data': {
            'sample_rate': 16000,
            'n_mels': 64,
            'n_fft': 512,
            'hop_length': 160,
            'win_length': 320,
            'f_min': 0.0,
            'f_max': 8000.0
        },
        'augmentation': {
            'freq_masks': 2,
            'freq_width': 5,
            'time_masks': 2,
            'time_width': 10
        },
        'training': {
            'batch_size': 4,
            'learning_rate': 0.01,
            'weight_decay': 0.001,
            'epochs': 100,
            'warmup_epochs': 2,
            'save_frequency': 10,
            'eval_frequency': 500,
            'max_duration': 16.7,
            'min_duration': 0.1
        }
    }


def create_jasper_10x5_config():
    """Create larger Jasper 10x5 configuration"""
    config = create_jasper_5x3_config()
    
    # Modify for 10x5 architecture
    config['model']['encoder']['blocks'] = [
        {
            'out_channels': 256,
            'kernel_size': 11,
            'stride': 2,
            'dilation': 1,
            'dropout': 0.2,
            'repeat': 1,
            'separable': True,
            'residual': False,
            'residual_dense': False
        }
    ]
    
    # Add 10 blocks with 5 repeats each
    for i in range(10):
        out_channels = 256 + (i * 32)  # Gradually increase channels
        config['model']['encoder']['blocks'].append({
            'out_channels': out_channels,
            'kernel_size': 11,
            'stride': 1,
            'dilation': 1,
            'dropout': 0.2,
            'repeat': 5,
            'separable': True,
            'residual': True,
            'residual_dense': True
        })
    
    # Final epilogue blocks
    config['model']['encoder']['blocks'].extend([
        {
            'out_channels': 512,
            'kernel_size': 39,
            'stride': 1,
            'dilation': 1,
            'dropout': 0.3,
            'repeat': 1,
            'separable': False,
            'residual': True,
            'residual_dense': False
        },
        {
            'out_channels': 640,
            'kernel_size': 41,
            'stride': 1,
            'dilation': 1,
            'dropout': 0.3,
            'repeat': 1,
            'separable': False,
            'residual': True,
            'residual_dense': False
        }
    ])
    
    return config


# ==============================================================================
# TRAINING
# ==============================================================================

class JasperTrainer:
    """Training class for Jasper model"""
    
    def __init__(self, config: Dict, device: str = 'cpu'):
        self.config = config
        self.device = device
        
        # Initialize text encoder
        self.text_encoder = TextEncoder()
        
        # Update config with actual vocab size
        self.config['model']['decoder']['n_classes'] = self.text_encoder.vocab_size()
        
        # Create model
        self.model = Jasper(
            encoder_kw=config['model']['encoder'],
            decoder_kw=config['model']['decoder']
        ).to(device)
        
        # Create audio processor
        feature_config = config['data']
        augment_config = config.get('augmentation', None)
        self.audio_processor = AudioProcessor(feature_config, augment_config).to(device)
        
        # Loss function (CTC Loss)
        self.criterion = nn.CTCLoss(blank=self.text_encoder.blank_id, reduction='mean')
        
        # Optimizer
        self.optimizer = optim.SGD(
            self.model.parameters(),
            lr=config['training']['learning_rate'],
            weight_decay=config['training']['weight_decay'],
            momentum=0.9
        )
        
        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.ExponentialLR(self.optimizer, gamma=0.98)
        
        # Metrics
        self.train_losses = []
        self.val_losses = []
        
    def train_epoch(self, data_loader: DataLoader, epoch: int):
        """Train for one epoch"""
        self.model.train()
        self.audio_processor.train()
        
        total_loss = 0
        num_batches = 0
        
        pbar = tqdm(data_loader, desc=f'Epoch {epoch}')
        for batch_idx, batch in enumerate(pbar):
            # Move to device
            audio = batch['audio'].to(self.device)
            tokens = batch['tokens'].to(self.device)
            audio_lens = batch['audio_lens'].to(self.device)
            tokens_lens = batch['tokens_lens'].to(self.device)
            
            # Process audio to features
            features, feat_lens = self.audio_processor(audio, audio_lens)
            
            # Forward pass
            self.optimizer.zero_grad()
            log_probs = self.model(features)
            log_probs = F.log_softmax(log_probs, dim=-1)
            
            # Prepare for CTC loss
            # CTC expects: (time, batch, classes)
            log_probs_ctc = log_probs.transpose(0, 1)
            
            # Update feat_lens to match actual model output length
            actual_seq_len = log_probs_ctc.shape[0]
            feat_lens = torch.clamp(feat_lens, max=actual_seq_len)
            
            # Flatten targets for CTC
            targets = []
            target_lengths = []
            for i in range(tokens.shape[0]):
                target = tokens[i][:tokens_lens[i]]
                targets.append(target)
                target_lengths.append(tokens_lens[i])
            
            targets = torch.cat(targets)
            target_lengths = torch.stack(target_lengths)
            
            # Compute loss
            loss = self.criterion(log_probs_ctc, targets, feat_lens, target_lengths)
            
            # Backward pass
            loss.backward()
            
            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            
            self.optimizer.step()
            
            # Update metrics
            total_loss += loss.item()
            num_batches += 1
            
            # Update progress bar
            pbar.set_postfix({'loss': f'{loss.item():.4f}'})
        
        avg_loss = total_loss / num_batches
        self.train_losses.append(avg_loss)
        return avg_loss
    
    def evaluate(self, data_loader: DataLoader):
        """Evaluate model on validation set"""
        self.model.eval()
        self.audio_processor.eval()
        
        total_loss = 0
        num_batches = 0
        
        decoder = GreedyCTCDecoder()
        
        with torch.no_grad():
            for batch in tqdm(data_loader, desc='Evaluating'):
                # Move to device
                audio = batch['audio'].to(self.device)
                tokens = batch['tokens'].to(self.device)
                audio_lens = batch['audio_lens'].to(self.device)
                tokens_lens = batch['tokens_lens'].to(self.device)
                
                # Process audio to features
                features, feat_lens = self.audio_processor(audio, audio_lens)
                
                # Forward pass
                log_probs = self.model(features)
                log_probs = F.log_softmax(log_probs, dim=-1)
                
                # Prepare for CTC loss
                log_probs_ctc = log_probs.transpose(0, 1)
                
                # Flatten targets for CTC
                targets = []
                target_lengths = []
                for i in range(tokens.shape[0]):
                    target = tokens[i][:tokens_lens[i]]
                    targets.append(target)
                    target_lengths.append(tokens_lens[i])
                
                targets = torch.cat(targets)
                target_lengths = torch.stack(target_lengths)
                
                # Compute loss
                loss = self.criterion(log_probs_ctc, targets, feat_lens, target_lengths)
                
                total_loss += loss.item()
                num_batches += 1
        
        avg_loss = total_loss / num_batches
        self.val_losses.append(avg_loss)
        return avg_loss
    
    def train(self, train_loader: DataLoader, val_loader: Optional[DataLoader] = None, 
              save_dir: str = 'checkpoints'):
        """Main training loop"""
        os.makedirs(save_dir, exist_ok=True)
        
        epochs = self.config['training']['epochs']
        eval_frequency = self.config['training'].get('eval_frequency', 1)  # Default: every epoch for small runs
        save_frequency = self.config['training'].get('save_frequency', 10)

        best_val_loss = float('inf')

        logger.info(f"Starting training for {epochs} epochs")
        logger.info(f"Model parameters: {sum(p.numel() for p in self.model.parameters()):,}")

        for epoch in range(1, epochs + 1):
            # Train
            train_loss = self.train_epoch(train_loader, epoch)
            logger.info(f"Epoch {epoch}/{epochs} - Train Loss: {train_loss:.4f}")

            # Evaluate every eval_frequency epochs
            if val_loader and (epoch % eval_frequency == 0):
                val_loss = self.evaluate(val_loader)
                logger.info(f"Epoch {epoch}/{epochs} - Val Loss: {val_loss:.4f}")

                # Save best model
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    self.save_checkpoint(os.path.join(save_dir, 'best.pt'), epoch)
                    logger.info(f"New best model saved with val loss: {val_loss:.4f}")

            # Save regular checkpoint
            if epoch % save_frequency == 0:
                self.save_checkpoint(os.path.join(save_dir, f'epoch_{epoch}.pt'), epoch)

            # Update learning rate
            self.scheduler.step()

        logger.info("Training completed!")
        
    def save_checkpoint(self, path: str, epoch: int):
        """Save model checkpoint"""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'config': self.config,
            'train_losses': self.train_losses,
            'val_losses': self.val_losses
        }
        torch.save(checkpoint, path)
    
    def load_checkpoint(self, path: str):
        """Load model checkpoint"""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        return checkpoint['epoch']


# ==============================================================================
# INFERENCE
# ==============================================================================

class JasperInference:
    """Inference class for Jasper model"""
    
    def __init__(self, model_path: str, device: str = 'cpu'):
        self.device = device
        
        # Load checkpoint
        checkpoint = torch.load(model_path, map_location=device)
        self.config = checkpoint['config']
        
        # Initialize text encoder
        self.text_encoder = TextEncoder()
        
        # Create model
        self.model = Jasper(
            encoder_kw=self.config['model']['encoder'],
            decoder_kw=self.config['model']['decoder']
        ).to(device)
        
        # Load model weights
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        
        # Create audio processor (no augmentation for inference)
        feature_config = self.config['data']
        self.audio_processor = AudioProcessor(feature_config, augment_config=None).to(device)
        self.audio_processor.eval()
        
        # Decoder
        self.decoder = GreedyCTCDecoder()
        
        logger.info(f"Loaded model from {model_path}")
    
    def transcribe_file(self, audio_path: str) -> str:
        """Transcribe a single audio file"""
        # Load audio
        audio = load_audio(audio_path, self.config['data']['sample_rate'])
        audio = audio.unsqueeze(0).to(self.device)  # Add batch dimension
        audio_lens = torch.tensor([audio.shape[1]], device=self.device)
        
        return self.transcribe_batch(audio, audio_lens)[0]
    
    def transcribe_batch(self, audio: torch.Tensor, audio_lens: torch.Tensor) -> List[str]:
        """Transcribe a batch of audio"""
        with torch.no_grad():
            # Process audio to features
            features, feat_lens = self.audio_processor(audio, audio_lens)
            
            # Forward pass
            log_probs = self.model(features)
            log_probs = F.log_softmax(log_probs, dim=-1)
            
            # Decode predictions
            predictions = self.decoder(log_probs)
            
            # Convert to text
            transcripts = []
            for pred in predictions:
                text = self.text_encoder.decode(pred.tolist())
                transcripts.append(text)
            
            return transcripts


# ==============================================================================
# MAIN FUNCTIONS
# ==============================================================================

def create_synthetic_manifest(output_path: str, num_samples: int = 10):
    """Create a synthetic manifest file for testing"""
    import random
    import string
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    sample_texts = [
        "hello world",
        "this is a test",
        "speech recognition is working",
        "artificial intelligence",
        "deep learning model",
        "neural network training",
        "automatic speech recognition",
        "machine learning algorithm",
        "natural language processing",
        "computer vision system"
    ]
    
    with open(output_path, 'w') as f:
        for i in range(num_samples):
            # Create synthetic entry
            text = random.choice(sample_texts)
            duration = random.uniform(1.0, 5.0)
            
            entry = {
                'audio_filepath': f'synthetic_audio_{i}.wav',
                'duration': duration,
                'text': text
            }
            
            f.write(json.dumps(entry) + '\n')
    
    logger.info(f"Created synthetic manifest with {num_samples} samples: {output_path}")


def create_synthetic_audio(output_dir: str, manifest_path: str, sample_rate: int = 16000):
    """Create synthetic audio files based on manifest"""
    os.makedirs(output_dir, exist_ok=True)
    
    with open(manifest_path, 'r') as f:
        for line in f:
            item = json.loads(line.strip())
            audio_path = os.path.join(output_dir, item['audio_filepath'])
            duration = item['duration']
            
            # Generate synthetic audio (simple sine wave with noise)
            samples = int(duration * sample_rate)
            t = np.linspace(0, duration, samples)
            
            # Create a simple audio signal
            frequency = 440 + np.random.normal(0, 100)  # Random frequency around 440 Hz
            audio = 0.3 * np.sin(2 * np.pi * frequency * t) + 0.1 * np.random.randn(samples)
            
            # Save audio file
            sf.write(audio_path, audio, sample_rate)
    
    logger.info(f"Created synthetic audio files in {output_dir}")


def test_model():
    """Test the model with synthetic data"""
    logger.info("Testing Jasper model...")
    
    # Create test data
    test_dir = 'test_data'
    os.makedirs(test_dir, exist_ok=True)
    
    manifest_path = os.path.join(test_dir, 'test_manifest.json')
    create_synthetic_manifest(manifest_path, num_samples=5)
    create_synthetic_audio(test_dir, manifest_path)
    
    # Update manifest paths to be absolute (so dataset loader doesn't double-prefix)
    with open(manifest_path, 'r') as f:
        lines = f.readlines()

    with open(manifest_path, 'w') as f:
        for line in lines:
            item = json.loads(line.strip())
            abs_path = os.path.abspath(os.path.join(test_dir, item['audio_filepath']))
            item['audio_filepath'] = abs_path
            f.write(json.dumps(item) + '\n')
    
    # Test configuration
    config = create_jasper_5x3_config()
    config['training']['epochs'] = 2
    config['training']['batch_size'] = 2
    # During test runs ensure checkpoints are saved each epoch
    config['training']['save_frequency'] = 1
    
    # Test training
    logger.info("Testing training...")
    trainer = JasperTrainer(config)
    
    # Create dataset and dataloader
    text_encoder = TextEncoder()
    dataset = JasperDataset(manifest_path, text_encoder)
    data_loader = DataLoader(dataset, batch_size=2, shuffle=True, collate_fn=collate_fn)
    
    # Train for a few steps
    trainer.train(data_loader, save_dir='test_checkpoints')
    
    # Test inference
    logger.info("Testing inference...")
    checkpoint_path = 'test_checkpoints/epoch_2.pt'
    
    if os.path.exists(checkpoint_path):
        inferencer = JasperInference(checkpoint_path)
        
        # Test on synthetic audio
        audio_path = os.path.join(test_dir, 'synthetic_audio_0.wav')
        if os.path.exists(audio_path):
            transcript = inferencer.transcribe_file(audio_path)
            logger.info(f"Transcription: '{transcript}'")
        
        logger.info("Model test completed successfully!")
    else:
        logger.error("Checkpoint not found for inference test")


def train_model(args):
    """Train the Jasper model"""
    # Load configuration
    if args.config:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    else:
        config = create_jasper_5x3_config() if args.model == 'jasper_5x3' else create_jasper_10x5_config()
    
    # Update config with command line arguments
    if args.epochs:
        config['training']['epochs'] = args.epochs
    if args.batch_size:
        config['training']['batch_size'] = args.batch_size
    if args.lr:
        config['training']['learning_rate'] = args.lr
    
    # Initialize trainer
    trainer = JasperTrainer(config, device=args.device)
    
    # Create datasets
    text_encoder = TextEncoder()
    
    train_dataset = JasperDataset(
        args.train_manifest,
        text_encoder,
        max_duration=config['training']['max_duration'],
        min_duration=config['training']['min_duration'],
        sample_rate=config['data']['sample_rate']
    )
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=config['training']['batch_size'],
        shuffle=True,
        collate_fn=collate_fn,
        num_workers=args.num_workers
    )
    
    val_loader = None
    if args.val_manifest:
        val_dataset = JasperDataset(
            args.val_manifest,
            text_encoder,
            max_duration=config['training']['max_duration'],
            min_duration=config['training']['min_duration'],
            sample_rate=config['data']['sample_rate']
        )
        
        val_loader = DataLoader(
            val_dataset,
            batch_size=config['training']['batch_size'],
            shuffle=False,
            collate_fn=collate_fn,
            num_workers=args.num_workers
        )
    
    # Train model
    trainer.train(train_loader, val_loader, save_dir=args.save_dir)


def run_inference(args):
    """Run inference with the Jasper model"""
    # Initialize inference
    inferencer = JasperInference(args.checkpoint, device=args.device)
    
    if args.audio_file:
        # Single file inference
        transcript = inferencer.transcribe_file(args.audio_file)
        print(f"Transcript: {transcript}")
        
    elif args.manifest:
        # Batch inference on manifest
        with open(args.manifest, 'r') as f:
            for line in f:
                item = json.loads(line.strip())
                audio_path = item['audio_filepath']
                
                try:
                    transcript = inferencer.transcribe_file(audio_path)
                    print(f"{audio_path}: {transcript}")
                except Exception as e:
                    print(f"Error processing {audio_path}: {e}")
    
    else:
        print("Please provide either --audio_file or --manifest for inference")


def throughput_test(args):
    # Use all available CPU threads
    import os
    num_threads = os.cpu_count()
    torch.set_num_threads(num_threads)
    torch.set_num_interop_threads(num_threads)
    os.environ['OMP_NUM_THREADS'] = str(num_threads)
    os.environ['MKL_NUM_THREADS'] = str(num_threads)
    logger.info("Starting throughput_test mode: measuring training and inference throughput on small subset.")
    import csv
    import glob
    # Auto-select first two subfolders for training/inference subset
    import os
    base_dir = 'sample_data/train-clean-100-wav'
    all_folders = [name for name in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, name))]
    all_folders.sort()
    subset_folders = args.train_subset or all_folders[:2]
    train_files = []
    for folder in subset_folders:
        train_files.extend(glob.glob(f'{base_dir}/{folder}/*/*.wav'))
    # Create manifest for subset
    manifest_path = 'throughput_train_manifest.json'
    with open(manifest_path, 'w') as f:
        for wav_path in train_files:
            # Find corresponding text and duration (dummy for now)
            f.write(json.dumps({'audio_filepath': wav_path, 'duration': 3.0, 'text': 'dummy'}) + '\n')
    # Training config
    config = create_jasper_5x3_config()
    config['training']['epochs'] = 10
    config['training']['batch_size'] = 2
    config['training']['save_frequency'] = 1
    # Training throughput logging
    trainer = JasperTrainer(config)
    dataset = JasperDataset(manifest_path, TextEncoder())
    loader = DataLoader(dataset, batch_size=2, shuffle=True, collate_fn=collate_fn)
    training_csv = 'training_throughput.csv'
    fieldnames = ['epoch', 'samples', 'seconds', 'throughput', 'loss']
    with open(training_csv, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for epoch in range(1, 11):
            start = time.time()
            loss = trainer.train_epoch(loader, epoch)
            elapsed = time.time() - start
            samples = len(dataset)
            throughput = samples / elapsed if elapsed > 0 else 0
            row = {'epoch': epoch, 'samples': samples, 'seconds': elapsed, 'throughput': throughput, 'loss': loss}
            writer.writerow(row)
            csvfile.flush()
            print(f"Epoch {epoch}: {samples} samples in {elapsed:.2f}s, throughput={throughput:.2f} samples/sec")
            trainer.save_checkpoint(f'throughput_epoch_{epoch}.pt', epoch)
    print(f"Training throughput saved to {training_csv}")
    # Inference throughput logging
    import random
    subset_folders_inf = args.inference_subset or subset_folders
    inf_files = []
    for folder in subset_folders_inf:
        inf_files.extend(glob.glob(f'{base_dir}/{folder}/*/*.wav'))
    inferencer = JasperInference('throughput_epoch_10.pt')
    inference_csv = 'inference_throughput.csv'
    fieldnames_inf = ['batch', 'total_files', 'total_seconds', 'avg_files_per_sec']
    print("Starting endless inference throughput test. Press Ctrl+C to stop.")
    batch_num = 1
    with open(inference_csv, 'w', newline='') as csvfile:
        writer_inf = csv.DictWriter(csvfile, fieldnames=fieldnames_inf)
        writer_inf.writeheader()
        try:
            while True:
                # Select 100 random files for each batch
                batch_files = inf_files if len(inf_files) <= 100 else random.sample(inf_files, 100)
                start = time.time()
                for wav_path in batch_files:
                    _ = inferencer.transcribe_file(wav_path)
                total_time = time.time() - start
                avg_throughput = len(batch_files) / total_time if total_time > 0 else 0
                print(f"Batch {batch_num}: {len(batch_files)} files, {total_time:.2f}s, avg throughput {avg_throughput:.2f} files/sec")
                writer_inf.writerow({'batch': batch_num, 'total_files': len(batch_files), 'total_seconds': total_time, 'avg_files_per_sec': avg_throughput})
                csvfile.flush()
                batch_num += 1
        except KeyboardInterrupt:
            print("Endless inference stopped by user.")
    print(f"Inference throughput saved to {inference_csv}")


def main():
    parser = argparse.ArgumentParser(description='Jasper Speech Recognition')
    parser.add_argument('--mode', choices=['train', 'inference', 'test', 'throughput_test'], required=True,
                       help='Mode to run: train, inference, test, or throughput_test')
    parser.add_argument('--throughput_csv', default='throughput_results.csv', help='CSV file to save throughput logs')
    parser.add_argument('--train_subset', nargs='+', help='List of folders for small training subset (e.g. 4397 84)')
    parser.add_argument('--inference_subset', nargs='+', help='List of folders for small inference subset (e.g. 4397 84)')
    parser.add_argument('--device', default='cpu', help='Device to use (cpu or cuda)')
    parser.add_argument('--config', help='Path to config file')
    parser.add_argument('--train_manifest', help='Training manifest file')
    parser.add_argument('--val_manifest', help='Validation manifest file')
    parser.add_argument('--epochs', type=int, help='Number of training epochs')
    parser.add_argument('--batch_size', type=int, help='Batch size')
    parser.add_argument('--lr', type=float, help='Learning rate')
    parser.add_argument('--save_dir', default='checkpoints', help='Directory to save checkpoints')
    parser.add_argument('--num_workers', type=int, default=0, help='Number of data loader workers')
    parser.add_argument('--model', choices=['jasper_5x3', 'jasper_10x5'], default='jasper_5x3',
                       help='Model variant to use')
    parser.add_argument('--checkpoint', help='Path to model checkpoint')
    parser.add_argument('--audio_file', help='Audio file to transcribe')
    parser.add_argument('--manifest', help='Manifest file for batch inference')

    args = parser.parse_args()

    if args.mode == 'train':
        if not args.train_manifest:
            print("Error: --train_manifest is required for training")
            sys.exit(1)
        train_model(args)

    elif args.mode == 'inference':
        if not args.checkpoint:
            print("Error: --checkpoint is required for inference")
            sys.exit(1)
        run_inference(args)

    elif args.mode == 'test':
        test_model()

    elif args.mode == 'throughput_test':
        throughput_test(args)
    logger.info("Starting throughput_test mode: measuring training and inference throughput on small subset.")
    import csv
    import glob
    # Auto-select first two subfolders for training/inference subset
    import os
    base_dir = 'librispeech_data/train-clean-100-wav'
    all_folders = [name for name in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, name))]
    all_folders.sort()
    subset_folders = args.train_subset or all_folders[:2]
    train_files = []
    for folder in subset_folders:
        train_files.extend(glob.glob(f'{base_dir}/{folder}/*/*.wav'))
    # Create manifest for subset
    manifest_path = 'throughput_train_manifest.json'
    with open(manifest_path, 'w') as f:
        for wav_path in train_files:
            # Find corresponding text and duration (dummy for now)
            f.write(json.dumps({'audio_filepath': wav_path, 'duration': 3.0, 'text': 'dummy'}) + '\n')
    # Training config
    config = create_jasper_5x3_config()
    config['training']['epochs'] = 10
    config['training']['batch_size'] = 2
    config['training']['save_frequency'] = 1
    # Training throughput logging
    trainer = JasperTrainer(config)
    dataset = JasperDataset(manifest_path, TextEncoder())
    loader = DataLoader(dataset, batch_size=2, shuffle=True, collate_fn=collate_fn)
    train_throughput = []
    for epoch in range(1, 3):
        start = time.time()
        loss = trainer.train_epoch(loader, epoch)
        elapsed = time.time() - start
        samples = len(dataset)
        throughput = samples / elapsed if elapsed > 0 else 0
        train_throughput.append({'epoch': epoch, 'samples': samples, 'seconds': elapsed, 'samples_per_sec': throughput, 'loss': loss})
        print(f"Epoch {epoch}: {samples} samples in {elapsed:.2f}s, throughput={throughput:.2f} samples/sec")
        trainer.save_checkpoint(f'throughput_epoch_{epoch}.pt', epoch)
    # Inference throughput logging
    subset_folders_inf = args.inference_subset or subset_folders
    inf_files = []
    for folder in subset_folders_inf:
        inf_files.extend(glob.glob(f'{base_dir}/{folder}/*/*.wav'))
    inferencer = JasperInference('throughput_epoch_2.pt')
    inference_throughput = []
    print("Starting continuous inference. Press Ctrl+C to stop.")
    try:
        count = 0
        start = time.time()
        while True:
            for wav_path in inf_files:
                t0 = time.time()
                _ = inferencer.transcribe_file(wav_path)
                t1 = time.time()
                inference_throughput.append({'file': wav_path, 'seconds': t1-t0, 'files_per_sec': 1/(t1-t0) if t1>t0 else 0})
                count += 1
    except KeyboardInterrupt:
        total_time = time.time() - start
        print(f"Inference stopped after {count} files, total time {total_time:.2f}s")
    # Save throughput logs to CSV
    with open(args.throughput_csv, 'w', newline='') as csvfile:
        fieldnames = ['epoch', 'samples', 'seconds', 'samples_per_sec', 'loss']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in train_throughput:
            writer.writerow(row)
        writer.writerow({})
        fieldnames_inf = ['file', 'seconds', 'files_per_sec']
        writer_inf = csv.DictWriter(csvfile, fieldnames=fieldnames_inf)
        writer_inf.writeheader()
        for row in inference_throughput:
            writer_inf.writerow(row)
    print(f"Throughput results saved to {args.throughput_csv}")
    
    # Common arguments
    parser.add_argument('--device', default='cpu', help='Device to use (cpu or cuda)')
    parser.add_argument('--config', help='Path to config file')
    
    # Training arguments
    parser.add_argument('--train_manifest', help='Training manifest file')
    parser.add_argument('--val_manifest', help='Validation manifest file')
    parser.add_argument('--epochs', type=int, help='Number of training epochs')
    parser.add_argument('--batch_size', type=int, help='Batch size')
    parser.add_argument('--lr', type=float, help='Learning rate')
    parser.add_argument('--save_dir', default='checkpoints', help='Directory to save checkpoints')
    parser.add_argument('--num_workers', type=int, default=0, help='Number of data loader workers')
    parser.add_argument('--model', choices=['jasper_5x3', 'jasper_10x5'], default='jasper_5x3',
                       help='Model variant to use')
    
    # Inference arguments  
    parser.add_argument('--checkpoint', help='Path to model checkpoint')
    parser.add_argument('--audio_file', help='Audio file to transcribe')
    parser.add_argument('--manifest', help='Manifest file for batch inference')
    
    args = parser.parse_args()
    
    if args.mode == 'train':
        if not args.train_manifest:
            print("Error: --train_manifest is required for training")
            sys.exit(1)
        train_model(args)

    elif args.mode == 'inference':
        if not args.checkpoint:
            print("Error: --checkpoint is required for inference")
            sys.exit(1)
        run_inference(args)

    elif args.mode == 'test':
        test_model()

    elif args.mode == 'throughput_test':
        throughput_test(args)


if __name__ == '__main__':
    main()