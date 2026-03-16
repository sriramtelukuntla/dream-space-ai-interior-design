"""
Test Script for AI Interior Design Project
Verifies that all new components are working correctly
"""

import sys
import os

def test_imports():
    """Test if all required modules can be imported"""
    print("\n" + "="*60)
    print("🧪 Testing Module Imports")
    print("="*60)
    
    modules_to_test = [
        ('cv2', 'OpenCV'),
        ('PIL', 'Pillow'),
        ('numpy', 'NumPy'),
        ('flask', 'Flask'),
        ('three_d_converter', '3D Converter'),
        ('cost_estimator', 'Cost Estimator')  ]
    
    failed = []
    
    for module_name, display_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"  ✅ {display_name:<20} - OK")
        except ImportError as e:
            print(f"  ❌ {display_name:<20} - FAILED: {e}")
            failed.append(display_name)
    
    if failed:
        print(f"\n❌ Failed imports: {', '.join(failed)}")
        print("\nInstall missing packages:")
        if 'OpenCV' in failed:
            print("  pip install opencv-python opencv-python-headless")
        if 'Pillow' in failed:
            print("  pip install Pillow")
        if 'NumPy' in failed:
            print("  pip install numpy")
        return False
    else:
        print("\n✅ All imports successful!")
        return True

def test_3d_converter():
    """Test 3D converter initialization"""
    print("\n" + "="*60)
    print("🎥 Testing 3D Converter")
    print("="*60)
    
    try:
        from three_d_converter import ThreeDImageConverter
        
        # Test fast mode
        converter_fast = ThreeDImageConverter(mode='fast')
        print(f"  ✅ Fast mode initialized")
        print(f"     - Blur kernel: {converter_fast.blur_kernel}")
        print(f"     - Perspective strength: {converter_fast.perspective_strength}")
        
        # Test quality mode
        converter_quality = ThreeDImageConverter(mode='quality')
        print(f"  ✅ Quality mode initialized")
        print(f"     - Blur kernel: {converter_quality.blur_kernel}")
        print(f"     - Perspective strength: {converter_quality.perspective_strength}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_cost_estimator():
    """Test cost estimator functionality"""
    print("\n" + "="*60)
    print("💰 Testing Cost Estimator")
    print("="*60)
    
    try:
        from cost_estimator import CostEstimator
        
        estimator = CostEstimator()
        print(f"  ✅ Cost Estimator initialized")
        
        # Test with sample data
        sample_data = {
            'room_type': 'bedroom',
            'style': 'modern',
            'furniture': ['bed', 'wardrobe', 'nightstand'],
            'materials': ['wood'],
            'dimensions': {
                'width': 12,
                'length': 10,
                'unit': 'feet'
            }
        }
        
        cost_breakdown = estimator.estimate_cost(sample_data)
        
        print(f"  ✅ Sample estimation successful")
        print(f"     - Room: {cost_breakdown['room_details']['room_type']}")
        print(f"     - Area: {cost_breakdown['room_details']['area_sqft']} sqft")
        print(f"     - Tier: {cost_breakdown['room_details']['quality_tier']}")
        print(f"     - Total Cost: ₹{cost_breakdown['total_cost']:,.0f}")
        
        # Test report generation
        report = estimator.format_cost_report(cost_breakdown)
        print(f"  ✅ Cost report generation successful")
        print(f"     - Report length: {len(report)} characters")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_directories():
    """Test if required directories exist"""
    print("\n" + "="*60)
    print("📁 Testing Directory Structure")
    print("="*60)
    
    required_dirs = [
        'uploads',
        'outputs',
        'static/generated',
        'static',
        'templates'
    ]
    
    all_exist = True
    
    for directory in required_dirs:
        if os.path.exists(directory):
            print(f"  ✅ {directory}")
        else:
            print(f"  ❌ {directory} - NOT FOUND")
            all_exist = False
    
    if not all_exist:
        print("\n⚠️  Some directories are missing. They will be auto-created when the server starts.")
    
    return True

def test_flask_endpoints():
    """Test if app.py has all required endpoints"""
    print("\n" + "="*60)
    print("🔌 Testing Flask Endpoints")
    print("="*60)
    
    try:
        # Read app.py and check for endpoints
        with open('app.py', 'r') as f:
            content = f.read()
        
        required_endpoints = [
            ('/api/generate-3d-views', 'generate_3d_views'),
            ('/api/generate-3d-simple', 'generate_3d_simple'),
            ('/api/estimate-cost', 'estimate_cost'),
            ('/api/cost-comparison', 'cost_comparison'),
            ('/api/generate-design', 'generate_design'),
            ('/api/analyze-prompt', 'analyze_prompt')
        ]
        
        missing = []
        
        for endpoint, function in required_endpoints:
            if function in content:
                print(f"  ✅ {endpoint:<30} - Found")
            else:
                print(f"  ❌ {endpoint:<30} - Missing")
                missing.append(endpoint)
        
        if missing:
            print(f"\n❌ Missing endpoints: {', '.join(missing)}")
            print("Make sure you're using the updated app.py file!")
            return False
        else:
            print("\n✅ All endpoints found!")
            return True
            
    except FileNotFoundError:
        print("  ❌ app.py not found!")
        print("Make sure you're running this test from your project root directory.")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_file_existence():
    """Test if required files exist"""
    print("\n" + "="*60)
    print("📄 Testing Required Files")
    print("="*60)
    
    required_files = [
        ('app.py', 'Main Flask application'),
        ('three_d_converter.py', '3D View Generator'),
        ('cost_estimator.py', 'Cost Estimator'),
        ('.env', 'Environment variables (optional)')
    ]
    
    all_exist = True
    
    for filename, description in required_files:
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"  ✅ {filename:<25} - {description} ({size:,} bytes)")
        else:
            if filename == '.env':
                print(f"  ⚠️  {filename:<25} - {description} (optional)")
            else:
                print(f"  ❌ {filename:<25} - {description} - NOT FOUND")
                all_exist = False
    
    return all_exist

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("🚀 AI INTERIOR DESIGN PROJECT - TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Test 1: Module imports
    results['imports'] = test_imports()
    
    # Test 2: File existence
    results['files'] = test_file_existence()
    
    # Test 3: Directories
    results['directories'] = test_directories()
    
    # Test 4: Flask endpoints
    results['endpoints'] = test_flask_endpoints()
    
    # Test 5: 3D Converter
    results['3d_converter'] = test_3d_converter()
    
    # Test 6: Cost Estimator
    results['cost_estimator'] = test_cost_estimator()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name.upper():<20} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("\nYou're ready to run your server:")
        print("  python app.py")
    else:
        print("❌ SOME TESTS FAILED")
        print("\nPlease fix the issues above before running the server.")
        print("Check the INTEGRATION_GUIDE.md for detailed instructions.")
    
    print("="*60 + "\n")
    
    return all_passed

if __name__ == '__main__':
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)