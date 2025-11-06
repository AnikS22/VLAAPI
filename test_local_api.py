#!/usr/bin/env python3
"""
Test Local API Deployment
--------------------------
Simple test script for local mock deployment.

Usage:
    python test_local_api.py
"""

import requests
import time
import sys

# Configuration
API_URL = "http://localhost:8000"

# You'll get these from: cat test_api_keys.txt
# Replace with actual keys after running local_deploy.sh
FREE_TIER_KEY = "vla_local_YOUR_FREE_KEY_HERE"
PRO_TIER_KEY = "vla_local_YOUR_PRO_KEY_HERE"

# Test image (1x1 pixel PNG)
TEST_IMAGE = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


def print_header(title):
    """Print test section header."""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def test_health():
    """Test 1: Health check."""
    print_header("TEST 1: Health Check")
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is healthy!")
            print(f"   Status: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"❌ Unexpected status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {API_URL}")
        print(f"   Make sure services are running:")
        print(f"   ./scripts/local_deploy.sh")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_inference(api_key, tier_name):
    """Test 2: Inference request."""
    print_header(f"TEST 2: Inference Request ({tier_name})")
    
    if "YOUR_" in api_key:
        print(f"⚠️  Please edit this file and set {tier_name} API key")
        print(f"   Get keys from: cat test_api_keys.txt")
        return False
    
    try:
        response = requests.post(
            f"{API_URL}/v1/inference",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openvla-7b",
                "image": TEST_IMAGE,
                "instruction": "pick up the red cube",
                "robot_config": {"type": "franka_panda"}
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Inference successful!")
            print(f"   Request ID: {result['request_id']}")
            print(f"   Model: {result['model']}")
            print(f"   Action: {result['action']['values'][:3]}... (7-DoF)")
            print(f"   Safety Score: {result['safety']['overall_score']:.2f}")
            print(f"   Latency: {result['performance']['total_latency_ms']}ms")
            return True
        elif response.status_code == 401:
            print(f"❌ Authentication failed - invalid API key")
            return False
        elif response.status_code == 429:
            print(f"⚠️  Rate limited (this is normal behavior)")
            return True
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_metrics():
    """Test 3: Metrics collection."""
    print_header("TEST 3: Prometheus Metrics")
    
    try:
        response = requests.get(f"{API_URL}/metrics", timeout=5)
        
        if response.status_code == 200:
            metrics_text = response.text
            vla_metrics = [line for line in metrics_text.split('\n') 
                          if 'vla_' in line and not line.startswith('#')]
            
            print(f"✅ Metrics endpoint working!")
            print(f"   Total VLA metrics: {len(vla_metrics)}")
            print(f"\n   Sample metrics:")
            for metric in vla_metrics[:5]:
                print(f"      {metric}")
            if len(vla_metrics) > 5:
                print(f"      ... and {len(vla_metrics)-5} more")
            return True
        else:
            print(f"❌ Cannot access metrics: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_dashboards():
    """Test 4: Dashboard availability."""
    print_header("TEST 4: Dashboard Availability")
    
    services = {
        "Grafana": "http://localhost:3000",
        "Prometheus": "http://localhost:9090",
        "API Docs": f"{API_URL}/docs"
    }
    
    all_ok = True
    for name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name:12} available at {url}")
            else:
                print(f"⚠️  {name:12} returned {response.status_code}")
                all_ok = False
        except Exception as e:
            print(f"❌ {name:12} not accessible: {e}")
            all_ok = False
    
    return all_ok


def main():
    """Run all tests."""
    print("\n" + "🧪"*30)
    print("  VLA API Local Deployment Test Suite")
    print("🧪"*30)
    
    # Check if API keys are set
    if "YOUR_" in FREE_TIER_KEY or "YOUR_" in PRO_TIER_KEY:
        print("\n⚠️  API KEYS NOT SET!")
        print("\n  Please follow these steps:")
        print("  1. Run: ./scripts/local_deploy.sh")
        print("  2. Run: cat test_api_keys.txt")
        print("  3. Copy the keys and edit this file")
        print("  4. Replace FREE_TIER_KEY and PRO_TIER_KEY")
        print("  5. Run this test again\n")
        sys.exit(1)
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health()))
    
    if results[-1][1]:  # Only continue if health check passed
        results.append(("Free Tier Inference", test_inference(FREE_TIER_KEY, "Free")))
        results.append(("Pro Tier Inference", test_inference(PRO_TIER_KEY, "Pro")))
        results.append(("Metrics Collection", test_metrics()))
        results.append(("Dashboard Availability", test_dashboards()))
    
    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n" + "🎉"*30)
        print("\n✅ ALL TESTS PASSED!")
        print("\n📊 Your local deployment is working perfectly!")
        print("\n  Next steps:")
        print("  • Open Grafana:       http://localhost:3000")
        print("  • View API docs:      http://localhost:8000/docs")
        print("  • Check Prometheus:   http://localhost:9090")
        print("  • Read full guide:    docs/LOCAL_MOCK_DEPLOYMENT.md")
        print("\n  When you're ready:")
        print("  • Deploy to servers using docs/DEPLOYMENT_AND_OPERATIONS.md")
        print("\n" + "🎉"*30 + "\n")
        return 0
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        print("\nTroubleshooting:")
        print("  • Ensure services are running: docker-compose -f docker-compose.local.yml ps")
        print("  • Check logs: docker-compose -f docker-compose.local.yml logs")
        print("  • Restart: docker-compose -f docker-compose.local.yml restart")
        return 1


if __name__ == "__main__":
    sys.exit(main())

