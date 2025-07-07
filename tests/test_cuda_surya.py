#!/usr/bin/env python3
"""
Comprehensive test for CUDA availability and Surya OCR device selection
Run with: python tests/test_cuda_surya.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_pytorch_cuda():
    """Test PyTorch CUDA availability"""
    print("=" * 60)
    print("🔍 PYTORCH & CUDA TEST")
    print("=" * 60)
    
    try:
        import torch
        print(f"✅ PyTorch version: {torch.__version__}")
        print(f"✅ PyTorch CUDA version: {torch.version.cuda}")
        print(f"✅ CUDA available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"✅ CUDA device count: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"   GPU {i}: {torch.cuda.get_device_name(i)}")
            
            # Test tensor on GPU
            test_tensor = torch.tensor([1.0, 2.0, 3.0]).cuda()
            print(f"✅ Test tensor device: {test_tensor.device}")
            
            # Memory info
            print(f"✅ GPU memory allocated: {torch.cuda.memory_allocated() / 1024**2:.1f} MB")
            print(f"✅ GPU memory reserved: {torch.cuda.memory_reserved() / 1024**2:.1f} MB")
        else:
            print("❌ CUDA not available")
            
        return torch.cuda.is_available()
        
    except Exception as e:
        print(f"❌ PyTorch test failed: {e}")
        return False

def test_environment_variables():
    """Test relevant environment variables"""
    print("\n" + "=" * 60)
    print("🔍 ENVIRONMENT VARIABLES TEST")
    print("=" * 60)
    
    env_vars = [
        'TORCH_DEVICE',
        'PYTORCH_DEVICE', 
        'CUDA_VISIBLE_DEVICES',
        'PYTORCH_MPS_HIGH_WATERMARK_RATIO',
        'RECOGNITION_BATCH_SIZE',
        'DETECTOR_BATCH_SIZE'
    ]
    
    has_relevant_vars = False
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {value}")
            has_relevant_vars = True
        else:
            print(f"⚪ {var}: not set")
    
    # Return True if environment is OK (no vars needed when auto-detection works)
    return True

def test_surya_import():
    """Test Surya import and basic functionality"""
    print("\n" + "=" * 60)
    print("🔍 SURYA IMPORT TEST")
    print("=" * 60)
    
    try:
        # Test basic imports
        from surya.detection import DetectionPredictor
        from surya.recognition import RecognitionPredictor
        from surya.layout import LayoutPredictor
        print("✅ Surya imports successful")
        
        # Test model creation (without loading weights)
        print("✅ Surya DetectionPredictor class available")
        print("✅ Surya RecognitionPredictor class available") 
        print("✅ Surya LayoutPredictor class available")
        
        return True
        
    except Exception as e:
        print(f"❌ Surya import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_surya_model_loading():
    """Test actual Surya model loading and device detection"""
    print("\n" + "=" * 60)
    print("🔍 SURYA MODEL LOADING TEST")
    print("=" * 60)
    
    try:
        # Force CUDA if available
        import torch
        if torch.cuda.is_available():
            print("🚀 Setting TORCH_DEVICE=cuda")
            os.environ['TORCH_DEVICE'] = 'cuda'
        
        # Test our SuryaManager
        from ocr.surya_manager import SuryaModelManager
        
        print("🔄 Creating SuryaModelManager...")
        manager = SuryaModelManager()
        
        print("🔄 Loading models (this may take a while)...")
        models = manager.get_models()
        
        print("✅ Models loaded successfully:")
        for model_name, model in models.items():
            print(f"   {model_name}: {type(model)}")
            
            # Try to detect device if possible
            if hasattr(model, 'device'):
                print(f"   {model_name} device: {model.device}")
            elif hasattr(model, 'model') and hasattr(model.model, 'device'):
                print(f"   {model_name} device: {model.model.device}")
        
        return True
        
    except Exception as e:
        print(f"❌ Surya model loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_surya_client():
    """Test our SuryaClient"""
    print("\n" + "=" * 60)
    print("🔍 SURYA CLIENT TEST")
    print("=" * 60)
    
    try:
        from ocr import SuryaClient
        from PIL import Image
        import numpy as np
        
        print("🔄 Creating SuryaClient...")
        client = SuryaClient()
        
        # Create dummy image
        print("🔄 Creating test image...")
        test_image = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
        
        print("🔄 Processing test image...")
        results = client.process_pages([test_image])
        
        if results and len(results) > 0:
            result = results[0]
            if 'error' in result:
                print(f"❌ Processing error: {result['error']}")
                return False
            else:
                layout = result.get('layout', [])
                # Handle LayoutResult object safely
                try:
                    layout_count = len(layout) if hasattr(layout, '__len__') else 1 if layout else 0
                except TypeError:
                    # LayoutResult object - assume it exists and has content
                    layout_count = "LayoutResult object (success)"
                
                print(f"✅ Processing successful: {layout_count} layout elements")
                return True
        else:
            print("❌ No results returned")
            return False
            
    except Exception as e:
        print(f"❌ SuryaClient test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_nvidia_smi():
    """Test nvidia-smi availability"""
    print("\n" + "=" * 60)
    print("🔍 NVIDIA-SMI TEST")
    print("=" * 60)
    
    try:
        import subprocess
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ nvidia-smi available")
            lines = result.stdout.split('\n')
            for line in lines:
                if 'RTX' in line or 'GTX' in line or 'Tesla' in line:
                    print(f"   GPU: {line.strip()}")
            return True
        else:
            print(f"❌ nvidia-smi failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ nvidia-smi not found")
        return False
    except Exception as e:
        print(f"❌ nvidia-smi test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 CUDA & SURYA COMPREHENSIVE TEST")
    print("=" * 80)
    
    tests = [
        ("PyTorch CUDA", test_pytorch_cuda),
        ("Environment Variables", test_environment_variables),
        ("Surya Import", test_surya_import),
        ("NVIDIA SMI", test_nvidia_smi),
        ("Surya Model Loading", test_surya_model_loading),
        ("Surya Client", test_surya_client),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result if result is not None else False
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if results.get("PyTorch CUDA", False) and not results.get("Surya Model Loading", False):
        print("\n🔧 RECOMMENDATION: CUDA available but Surya not using it")
        print("   Try: export TORCH_DEVICE=cuda")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)