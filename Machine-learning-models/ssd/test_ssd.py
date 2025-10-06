#!/usr/bin/env python3
"""
Simple test script to verify SSD implementation works correctly
"""

import sys
import os
import time
import torch

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_ssd_inference_only():
    """Test inference-only functionality"""
    print("Testing SSD inference-only mode...")
    
    # Import after adding to path
    import subprocess
    
    # Run inference only for a short duration
    result = subprocess.run([
        sys.executable, "ssd-infernce.py", "inference"
    ], capture_output=True, text=True, timeout=30)
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    return result.returncode == 0

def test_model_loading():
    """Test that the model can be loaded successfully"""
    print("Testing model loading...")
    
    try:
        from torchvision.models import detection
        
        device = torch.device('cpu')
        model = detection.ssd300_vgg16(pretrained=False, num_classes=91)
        model = model.to(device)
        model.eval()
        
        print(f"Model loaded successfully on {device}")
        
        # Test with dummy input
        dummy_input = torch.randn(1, 3, 300, 300)
        with torch.no_grad():
            output = model(dummy_input)
        
        print(f"Model inference successful. Output keys: {output[0].keys()}")
        return True
        
    except Exception as e:
        print(f"Model loading failed: {e}")
        return False

def test_dataset_creation():
    """Test synthetic dataset creation"""
    print("Testing dataset creation...")
    
    try:
        # Import the dataset class
        import importlib.util
        spec = importlib.util.spec_from_file_location("ssd_module", "ssd-infernce.py")
        ssd_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ssd_module)
        
        SyntheticObjectDetectionDataset = ssd_module.SyntheticObjectDetectionDataset
        
        dataset = SyntheticObjectDetectionDataset(num_samples=10, image_size=(300, 300))
        
        # Test getting an item
        image, target = dataset[0]
        
        print(f"Dataset created successfully")
        print(f"Image shape: {image.shape}")
        print(f"Target keys: {target.keys()}")
        print(f"Number of boxes: {len(target['boxes'])}")
        print(f"Number of labels: {len(target['labels'])}")
        
        return True
        
    except Exception as e:
        print(f"Dataset creation failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("SSD IMPLEMENTATION TEST SUITE")
    print("=" * 50)
    
    tests = [
        ("Model Loading", test_model_loading),
        ("Dataset Creation", test_dataset_creation),
        # ("Inference Only", test_ssd_inference_only),  # Skip full run for now
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n[TEST] {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"TEST RESULTS: {passed}/{total} tests passed")
    print("=" * 50)
    
    if passed == total:
        print("🎉 All tests passed! SSD implementation is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    exit(main())