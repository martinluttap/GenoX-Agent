#!/usr/bin/env python3
"""
LibriSpeech Dataset Downloader and Preprocessor
Based on NVIDIA DeepLearningExamples repository structure

This script downloads LibriSpeech dataset subsets and preprocesses them
into the format expected by the Jasper training script, creating manifest
files compatible with the NVIDIA repository structure.

Usage:
    python download_librispeech.py --data_dir /path/to/data --subsets train-clean-100,dev-clean
    
    # Download all standard subsets
    python download_librispeech.py --data_dir ./librispeech_data --all
    
    # Download only test sets for inference
    python download_librispeech.py --data_dir ./librispeech_data --inference_only
"""

import os
import sys
import json
import argparse
import tarfile
import zipfile
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from urllib.request import urlretrieve
from urllib.parse import urlparse
import subprocess

import librosa
import soundfile as sf
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# LibriSpeech dataset URLs
LIBRISPEECH_URLS = {
    'train-clean-100': 'http://www.openslr.org/resources/12/train-clean-100.tar.gz',
    'train-clean-360': 'http://www.openslr.org/resources/12/train-clean-360.tar.gz',
    'train-other-500': 'http://www.openslr.org/resources/12/train-other-500.tar.gz',
    'dev-clean': 'http://www.openslr.org/resources/12/dev-clean.tar.gz',
    'dev-other': 'http://www.openslr.org/resources/12/dev-other.tar.gz',
    'test-clean': 'http://www.openslr.org/resources/12/test-clean.tar.gz',
    'test-other': 'http://www.openslr.org/resources/12/test-other.tar.gz'
}

# Standard subset groups
SUBSET_GROUPS = {
    'all': list(LIBRISPEECH_URLS.keys()),
    'train': ['train-clean-100', 'train-clean-360', 'train-other-500'],
    'dev': ['dev-clean', 'dev-other'],
    'test': ['test-clean', 'test-other'],
    'inference_only': ['dev-clean', 'dev-other', 'test-clean', 'test-other'],
    'minimal': ['train-clean-100', 'dev-clean']  # For quick testing
}


def download_with_progress(url: str, output_path: str):
    """Download file with progress bar"""
    
    def progress_hook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100, downloaded * 100 / total_size)
            pbar.update(downloaded - pbar.n)
    
    # Get file size
    import urllib.request
    with urllib.request.urlopen(url) as response:
        total_size = int(response.headers.get('Content-Length', 0))
    
    # Download with progress bar
    with tqdm(total=total_size, unit='B', unit_scale=True, desc=os.path.basename(output_path)) as pbar:
        urlretrieve(url, output_path, reporthook=progress_hook)


def extract_archive(archive_path: str, extract_dir: str):
    """Extract tar.gz archive"""
    logger.info(f"Extracting {archive_path}...")
    
    with tarfile.open(archive_path, 'r:gz') as tar:
        # Get total number of files for progress
        members = tar.getmembers()
        
        with tqdm(total=len(members), desc='Extracting') as pbar:
            for member in members:
                tar.extract(member, extract_dir)
                pbar.update(1)


def find_audio_files(directory: str) -> List[Tuple[str, str]]:
    """Find all .flac audio files and their corresponding .txt transcript files"""
    audio_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.flac'):
                audio_path = os.path.join(root, file)
                
                # Find corresponding transcript file
                txt_file = file.replace('.flac', '.trans.txt')
                txt_path = os.path.join(root, txt_file)
                
                if not os.path.exists(txt_path):
                    # Look for chapter-level transcript file
                    parts = file.split('-')
                    if len(parts) >= 2:
                        chapter_txt = f"{parts[0]}-{parts[1]}.trans.txt"
                        txt_path = os.path.join(root, chapter_txt)
                
                if os.path.exists(txt_path):
                    audio_files.append((audio_path, txt_path))
                else:
                    logger.warning(f"No transcript found for {audio_path}")
    
    return audio_files


def parse_transcript_file(txt_path: str) -> Dict[str, str]:
    """Parse LibriSpeech transcript file"""
    transcripts = {}
    
    with open(txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split(' ', 1)
                if len(parts) >= 2:
                    utterance_id = parts[0]
                    transcript = parts[1].upper()  # LibriSpeech uses uppercase
                    transcripts[utterance_id] = transcript
    
    return transcripts


def convert_audio_to_wav(flac_path: str, wav_path: str, target_sr: int = 16000) -> float:
    """Convert FLAC to WAV and return duration"""
    try:
        # Load audio with librosa
        audio, sr = librosa.load(flac_path, sr=target_sr, mono=True)
        
        # Save as WAV
        sf.write(wav_path, audio, target_sr)
        
        # Return duration in seconds
        duration = len(audio) / target_sr
        return duration
        
    except Exception as e:
        logger.error(f"Error converting {flac_path}: {e}")
        return 0.0


def create_manifest_entry(wav_path: str, transcript: str, duration: float) -> Dict:
    """Create a manifest entry in NVIDIA format"""
    return {
        'audio_filepath': wav_path,
        'duration': duration,
        'text': transcript.strip()
    }


def process_subset(subset_name: str, librispeech_dir: str, output_dir: str, 
                  target_sr: int = 16000) -> str:
    """Process a LibriSpeech subset and create manifest"""
    
    logger.info(f"Processing subset: {subset_name}")
    
    # Paths
    subset_dir = os.path.join(librispeech_dir, 'LibriSpeech', subset_name)
    wav_output_dir = os.path.join(output_dir, f"{subset_name}-wav")
    manifest_path = os.path.join(output_dir, f"librispeech-{subset_name}-wav.json")
    
    # Create output directory
    os.makedirs(wav_output_dir, exist_ok=True)
    
    # Find all audio files
    audio_files = find_audio_files(subset_dir)
    logger.info(f"Found {len(audio_files)} audio files in {subset_name}")
    
    if not audio_files:
        logger.warning(f"No audio files found in {subset_dir}")
        return manifest_path
    
    # Process files
    manifest_entries = []
    
    for flac_path, txt_path in tqdm(audio_files, desc=f"Processing {subset_name}"):
        # Parse transcript file
        transcripts = parse_transcript_file(txt_path)
        
        # Get utterance ID from filename
        flac_filename = os.path.basename(flac_path)
        utterance_id = flac_filename.replace('.flac', '')
        
        if utterance_id not in transcripts:
            logger.warning(f"No transcript for utterance {utterance_id}")
            continue
        
        transcript = transcripts[utterance_id]
        
        # Convert to WAV
        wav_filename = flac_filename.replace('.flac', '.wav')
        wav_path = os.path.join(wav_output_dir, wav_filename)
        
        # Create subdirectory structure to avoid filename conflicts
        relative_dir = os.path.relpath(os.path.dirname(flac_path), subset_dir)
        wav_subdir = os.path.join(wav_output_dir, relative_dir)
        os.makedirs(wav_subdir, exist_ok=True)
        
        wav_path = os.path.join(wav_subdir, wav_filename)
        
        duration = convert_audio_to_wav(flac_path, wav_path, target_sr)
        
        if duration > 0:
            # Create manifest entry with relative path
            relative_wav_path = os.path.relpath(wav_path, output_dir)
            entry = create_manifest_entry(relative_wav_path, transcript, duration)
            manifest_entries.append(entry)
    
    # Write manifest file
    with open(manifest_path, 'w') as f:
        for entry in manifest_entries:
            f.write(json.dumps(entry) + '\n')
    
    logger.info(f"Created manifest with {len(manifest_entries)} entries: {manifest_path}")
    return manifest_path


def download_and_extract_subset(subset_name: str, data_dir: str, keep_archives: bool = False):
    """Download and extract a single LibriSpeech subset"""
    
    if subset_name not in LIBRISPEECH_URLS:
        raise ValueError(f"Unknown subset: {subset_name}")
    
    url = LIBRISPEECH_URLS[subset_name]
    archive_filename = os.path.basename(urlparse(url).path)
    archive_path = os.path.join(data_dir, archive_filename)
    
    # Download if not exists
    if not os.path.exists(archive_path):
        logger.info(f"Downloading {subset_name} from {url}")
        os.makedirs(data_dir, exist_ok=True)
        download_with_progress(url, archive_path)
    else:
        logger.info(f"Archive already exists: {archive_path}")
    
    # Extract
    extract_dir = data_dir
    subset_extracted_dir = os.path.join(extract_dir, 'LibriSpeech', subset_name)
    
    if not os.path.exists(subset_extracted_dir):
        extract_archive(archive_path, extract_dir)
    else:
        logger.info(f"Subset already extracted: {subset_extracted_dir}")
    
    # Optionally remove archive
    if not keep_archives and os.path.exists(archive_path):
        logger.info(f"Removing archive: {archive_path}")
        os.remove(archive_path)
    
    return subset_extracted_dir


def create_combined_manifests(data_dir: str):
    """Create combined manifest files for training"""
    
    manifest_dir = data_dir
    
    # Combine training manifests
    train_manifests = [
        'librispeech-train-clean-100-wav.json',
        'librispeech-train-clean-360-wav.json', 
        'librispeech-train-other-500-wav.json'
    ]
    
    combined_train_path = os.path.join(manifest_dir, 'librispeech-train-all-wav.json')
    combine_manifests(manifest_dir, train_manifests, combined_train_path)
    
    # Combine dev manifests
    dev_manifests = [
        'librispeech-dev-clean-wav.json',
        'librispeech-dev-other-wav.json'
    ]
    
    combined_dev_path = os.path.join(manifest_dir, 'librispeech-dev-all-wav.json')
    combine_manifests(manifest_dir, dev_manifests, combined_dev_path)
    
    # Combine test manifests
    test_manifests = [
        'librispeech-test-clean-wav.json',
        'librispeech-test-other-wav.json'
    ]
    
    combined_test_path = os.path.join(manifest_dir, 'librispeech-test-all-wav.json')
    combine_manifests(manifest_dir, test_manifests, combined_test_path)


def combine_manifests(base_dir: str, manifest_files: List[str], output_path: str):
    """Combine multiple manifest files into one"""
    
    total_entries = 0
    
    with open(output_path, 'w') as outf:
        for manifest_file in manifest_files:
            manifest_path = os.path.join(base_dir, manifest_file)
            
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as inf:
                    for line in inf:
                        outf.write(line)
                        total_entries += 1
                logger.info(f"Added {manifest_file} to combined manifest")
            else:
                logger.warning(f"Manifest file not found: {manifest_path}")
    
    logger.info(f"Created combined manifest with {total_entries} entries: {output_path}")


def create_dataset_info(data_dir: str):
    """Create dataset information file"""
    
    info_path = os.path.join(data_dir, 'dataset_info.json')
    
    # Collect statistics
    info = {
        'dataset': 'LibriSpeech',
        'sample_rate': 16000,
        'format': 'wav',
        'subsets': {},
        'total_duration': 0.0,
        'total_files': 0
    }
    
    # Process each manifest
    for filename in os.listdir(data_dir):
        if filename.startswith('librispeech-') and filename.endswith('-wav.json'):
            manifest_path = os.path.join(data_dir, filename)
            subset_name = filename.replace('librispeech-', '').replace('-wav.json', '')
            
            if os.path.exists(manifest_path):
                duration = 0.0
                file_count = 0
                
                with open(manifest_path, 'r') as f:
                    for line in f:
                        entry = json.loads(line.strip())
                        duration += entry.get('duration', 0.0)
                        file_count += 1
                
                info['subsets'][subset_name] = {
                    'duration_hours': duration / 3600,
                    'file_count': file_count,
                    'manifest_file': filename
                }
                
                info['total_duration'] += duration
                info['total_files'] += file_count
    
    info['total_duration_hours'] = info['total_duration'] / 3600
    
    # Save info
    with open(info_path, 'w') as f:
        json.dump(info, f, indent=2)
    
    logger.info(f"Created dataset info: {info_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("LIBRISPEECH DATASET SUMMARY")
    print("="*60)
    print(f"Total Duration: {info['total_duration_hours']:.1f} hours")
    print(f"Total Files: {info['total_files']:,}")
    print(f"Sample Rate: {info['sample_rate']} Hz")
    print("\nSubsets:")
    
    for subset_name, subset_info in info['subsets'].items():
        print(f"  {subset_name:20s}: {subset_info['duration_hours']:6.1f}h ({subset_info['file_count']:6,} files)")
    
    print("="*60)


def verify_dataset(data_dir: str, sample_count: int = 5):
    """Verify dataset by checking some random samples"""
    
    logger.info("Verifying dataset...")
    
    # Find a manifest file
    manifest_files = [f for f in os.listdir(data_dir) 
                     if f.startswith('librispeech-') and f.endswith('-wav.json')]
    
    if not manifest_files:
        logger.error("No manifest files found for verification")
        return False
    
    # Check samples from first manifest
    manifest_path = os.path.join(data_dir, manifest_files[0])
    
    with open(manifest_path, 'r') as f:
        lines = f.readlines()
    
    import random
    sample_lines = random.sample(lines, min(sample_count, len(lines)))
    
    for line in sample_lines:
        entry = json.loads(line.strip())
        audio_path = os.path.join(data_dir, entry['audio_filepath'])
        
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return False
        
        # Try to load audio
        try:
            audio, sr = librosa.load(audio_path, sr=None)
            actual_duration = len(audio) / sr
            expected_duration = entry['duration']
            
            if abs(actual_duration - expected_duration) > 0.1:
                logger.warning(f"Duration mismatch for {audio_path}: "
                             f"expected {expected_duration:.2f}s, got {actual_duration:.2f}s")
            
            logger.info(f"✓ Verified: {entry['audio_filepath']} - '{entry['text'][:50]}...'")
            
        except Exception as e:
            logger.error(f"Error loading {audio_path}: {e}")
            return False
    
    logger.info("Dataset verification completed successfully!")
    return True


def main():
    parser = argparse.ArgumentParser(description='Download and preprocess LibriSpeech dataset')
    
    parser.add_argument('--data_dir', required=True, 
                       help='Directory to store LibriSpeech data')
    
    # Subset selection
    subset_group = parser.add_mutually_exclusive_group()
    subset_group.add_argument('--subsets', 
                            help='Comma-separated list of subsets to download')
    subset_group.add_argument('--all', action='store_true',
                            help='Download all LibriSpeech subsets')
    subset_group.add_argument('--inference_only', action='store_true',
                            help='Download only dev and test sets for inference')
    subset_group.add_argument('--minimal', action='store_true',
                            help='Download minimal sets for testing (train-clean-100, dev-clean)')
    
    # Processing options
    parser.add_argument('--sample_rate', type=int, default=16000,
                       help='Target sample rate for audio files')
    parser.add_argument('--keep_archives', action='store_true',
                       help='Keep downloaded tar.gz archives')
    parser.add_argument('--skip_download', action='store_true',
                       help='Skip download, only process existing files')
    parser.add_argument('--verify', action='store_true',
                       help='Verify dataset after processing')
    
    args = parser.parse_args()
    
    # Determine subsets to process
    if args.all:
        subsets = SUBSET_GROUPS['all']
    elif args.inference_only:
        subsets = SUBSET_GROUPS['inference_only']
    elif args.minimal:
        subsets = SUBSET_GROUPS['minimal']
    elif args.subsets:
        subsets = [s.strip() for s in args.subsets.split(',')]
    else:
        print("Please specify which subsets to download (--all, --inference_only, --minimal, or --subsets)")
        sys.exit(1)
    
    # Validate subsets
    invalid_subsets = [s for s in subsets if s not in LIBRISPEECH_URLS]
    if invalid_subsets:
        print(f"Invalid subsets: {invalid_subsets}")
        print(f"Available subsets: {list(LIBRISPEECH_URLS.keys())}")
        sys.exit(1)
    
    logger.info(f"Processing subsets: {subsets}")
    logger.info(f"Data directory: {args.data_dir}")
    
    # Create data directory
    os.makedirs(args.data_dir, exist_ok=True)
    
    # Download and extract subsets
    if not args.skip_download:
        for subset in subsets:
            try:
                download_and_extract_subset(subset, args.data_dir, args.keep_archives)
            except Exception as e:
                logger.error(f"Failed to download {subset}: {e}")
                continue
    
    # Process subsets (convert to WAV and create manifests)
    manifest_paths = []
    for subset in subsets:
        try:
            manifest_path = process_subset(subset, args.data_dir, args.data_dir, args.sample_rate)
            manifest_paths.append(manifest_path)
        except Exception as e:
            logger.error(f"Failed to process {subset}: {e}")
            continue
    
    # Create combined manifests
    if len(manifest_paths) > 1:
        create_combined_manifests(args.data_dir)
    
    # Create dataset info
    create_dataset_info(args.data_dir)
    
    # Verify dataset
    if args.verify:
        verify_dataset(args.data_dir)
    
    logger.info("LibriSpeech dataset setup completed!")
    
    # Print usage instructions
    print("\n" + "="*60)
    print("USAGE INSTRUCTIONS")
    print("="*60)
    print("The dataset is now ready for training. Use these manifest files:")
    print()
    
    for manifest_path in manifest_paths:
        if os.path.exists(manifest_path):
            print(f"  {os.path.basename(manifest_path)}")
    
    print("\nTraining example:")
    print(f"  python jasper_complete.py --mode train \\")
    print(f"    --train_manifest {args.data_dir}/librispeech-train-clean-100-wav.json \\")
    print(f"    --val_manifest {args.data_dir}/librispeech-dev-clean-wav.json \\")
    print(f"    --epochs 50 --batch_size 8")
    
    print("\nInference example:")
    print(f"  python jasper_complete.py --mode inference \\")
    print(f"    --checkpoint checkpoints/best.pt \\")
    print(f"    --manifest {args.data_dir}/librispeech-test-clean-wav.json")
    print("="*60)


if __name__ == '__main__':
    main()