#!/usr/bin/env python3
"""
Simple VLA API Test Script
---------------------------
This is the easiest way to test your VLA Inference API.

Usage:
    python examples/simple_api_test.py
"""

import requests
import sys

# ============================================================================
# CONFIGURATION - CHANGE THESE VALUES
# ============================================================================

API_URL = "http://localhost:8000"
API_KEY = "vla_live_YOUR_KEY_HERE"  # Replace with your actual API key

# ============================================================================


def test_health():
    """Test 1: Check if API is alive."""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        
        if response.status_code == 200:
            print("✅ SUCCESS: API is running!")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ FAILED: Got status code {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ FAILED: Cannot connect to API")
        print("   Make sure the server is running:")
        print("   python -m uvicorn src.api.main:app --port 8000")
        return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_api_docs():
    """Test 2: Check if API documentation is accessible."""
    print("\n" + "="*60)
    print("TEST 2: API Documentation")
    print("="*60)
    
    try:
        response = requests.get(f"{API_URL}/docs", timeout=5)
        
        if response.status_code == 200:
            print("✅ SUCCESS: API docs available!")
            print(f"   Open in browser: {API_URL}/docs")
            return True
        else:
            print(f"⚠️  Docs not available (status {response.status_code})")
            print("   This is OK if running in production mode")
            return True
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_inference():
    """Test 3: Make actual inference request."""
    print("\n" + "="*60)
    print("TEST 3: Inference Request")
    print("="*60)
    
    if API_KEY == "vla_live_YOUR_KEY_HERE":
        print("❌ FAILED: You need to set your API key!")
        print("   Edit this file and change API_KEY variable")
        print("   Or run: python scripts/setup_database.py")
        return False
    
    # Prepare request
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Use a tiny test image (1x1 pixel PNG in base64)
    # In real use, you'd load an actual camera image
    test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    data = {
        "model": "openvla-7b",
        "image": test_image,
        "instruction": "pick up the red cube",
        "robot_config": {
            "type": "franka_panda"
        }
    }
    
    try:
        print("   Sending request...")
        response = requests.post(
            f"{API_URL}/v1/inference",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Inference completed!")
            print(f"\n   Request ID: {result['request_id']}")
            print(f"   Model: {result['model']}")
            print(f"\n   Robot Action (7-DoF):")
            action = result['action']['values']
            print(f"      Position (XYZ): [{action[0]:.3f}, {action[1]:.3f}, {action[2]:.3f}]")
            print(f"      Rotation (RPY): [{action[3]:.3f}, {action[4]:.3f}, {action[5]:.3f}]")
            print(f"      Gripper: {action[6]:.3f} (1.0 = closed)")
            print(f"\n   Safety Score: {result['safety']['overall_score']:.2f}")
            print(f"   Safety Checks Passed: {result['safety']['checks_passed']}")
            if result['safety']['flags']:
                print(f"   ⚠️  Safety Flags: {result['safety']['flags']}")
            print(f"\n   Performance:")
            print(f"      Total Latency: {result['performance']['total_latency_ms']}ms")
            print(f"      Queue Wait: {result['performance']['queue_wait_ms']}ms")
            print(f"      Inference: {result['performance']['inference_ms']}ms")
            return True
            
        elif response.status_code == 401:
            print("❌ FAILED: Invalid API key")
            print("   Check that your API key is correct")
            print("   Run: python scripts/setup_database.py")
            return False
            
        elif response.status_code == 429:
            print("❌ FAILED: Rate limit exceeded")
            print("   Wait a moment and try again")
            return False
            
        else:
            print(f"❌ FAILED: Status code {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ FAILED: Request timed out (>30s)")
        print("   The server might be busy or having issues")
        return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "🤖 VLA Inference API - Simple Test Script")
    print("=" * 60)
    
    results = []
    
    # Test 1: Health check
    results.append(("Health Check", test_health()))
    
    # Test 2: API docs
    results.append(("API Docs", test_api_docs()))
    
    # Test 3: Inference
    results.append(("Inference", test_inference()))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your API is working correctly.")
        print(f"\n📖 Next steps:")
        print(f"   - Read docs/BEGINNERS_API_GUIDE.md for detailed usage")
        print(f"   - View interactive docs at {API_URL}/docs")
        print(f"   - Try examples/streaming_client.py for real-time control")
    else:
        print("\n⚠️  Some tests failed. Check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

