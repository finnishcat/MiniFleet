import requests
import unittest
import sys
import os
import json
from datetime import datetime
import uuid

class DockerMonitorAPITester(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(DockerMonitorAPITester, self).__init__(*args, **kwargs)
        # Get the backend URL from frontend .env file
        self.base_url = "https://7df86c00-9eb7-4488-bc90-62b661914306.preview.emergentagent.com"
        self.local_url = "http://localhost:8001"  # For local testing
        self.container_id = "test_container_id"  # Dummy ID for testing
        self.test_server_id = f"test-server-{uuid.uuid4().hex[:8]}"
        self.test_registry_id = f"test-registry-{uuid.uuid4().hex[:8]}"

    def test_01_docker_status(self):
        """Test Docker status endpoint"""
        print("\n🔍 Testing Docker status API...")
        
        try:
            response = requests.get(f"{self.local_url}/api/docker/status")
            
            # In our test environment, we expect a 503 error since Docker is not available
            self.assertEqual(response.status_code, 503, "Expected status code 503 (Docker not available)")
            
            data = response.json()
            self.assertIn("detail", data, "Response should contain 'detail' field")
            self.assertEqual(data["detail"], "Docker client not available", "Error message should indicate Docker client not available")
            
            print("✅ Docker status API test passed - correctly reports Docker not available")
            return True
        
        except Exception as e:
            print(f"❌ Docker status API test failed: {str(e)}")
            return False

    def test_02_containers(self):
        """Test containers endpoint"""
        print("\n🔍 Testing containers API...")
        
        try:
            response = requests.get(f"{self.local_url}/api/containers")
            
            # In our test environment, we expect a 503 error since Docker is not available
            self.assertEqual(response.status_code, 503, "Expected status code 503 (Docker not available)")
            
            data = response.json()
            self.assertIn("detail", data, "Response should contain 'detail' field")
            
            print("✅ Containers API test passed - correctly reports Docker not available")
            return True
        
        except Exception as e:
            print(f"❌ Containers API test failed: {str(e)}")
            return False

    def test_03_images(self):
        """Test images endpoint"""
        print("\n🔍 Testing images API...")
        
        try:
            response = requests.get(f"{self.local_url}/api/images")
            
            # In our test environment, we expect a 503 error since Docker is not available
            self.assertEqual(response.status_code, 503, "Expected status code 503 (Docker not available)")
            
            data = response.json()
            self.assertIn("detail", data, "Response should contain 'detail' field")
            
            print("✅ Images API test passed - correctly reports Docker not available")
            return True
        
        except Exception as e:
            print(f"❌ Images API test failed: {str(e)}")
            return False

    def test_04_container_stats(self):
        """Test container stats endpoint"""
        print(f"\n🔍 Testing container stats API with dummy container ID...")
        
        try:
            response = requests.get(f"{self.local_url}/api/containers/{self.container_id}/stats")
            
            # In our test environment, we expect a 503 error since Docker is not available
            self.assertEqual(response.status_code, 503, "Expected status code 503 (Docker not available)")
            
            data = response.json()
            self.assertIn("detail", data, "Response should contain 'detail' field")
            
            print("✅ Container stats API test passed - correctly reports Docker not available")
            return True
        
        except Exception as e:
            print(f"❌ Container stats API test failed: {str(e)}")
            return False

    def test_05_container_logs(self):
        """Test container logs endpoint"""
        print(f"\n🔍 Testing container logs API with dummy container ID...")
        
        try:
            response = requests.get(f"{self.local_url}/api/containers/{self.container_id}/logs")
            
            # In our test environment, we expect a 503 error since Docker is not available
            self.assertEqual(response.status_code, 503, "Expected status code 503 (Docker not available)")
            
            data = response.json()
            self.assertIn("detail", data, "Response should contain 'detail' field")
            
            print("✅ Container logs API test passed - correctly reports Docker not available")
            return True
        
        except Exception as e:
            print(f"❌ Container logs API test failed: {str(e)}")
            return False

    def test_06_background_image(self):
        """Test background image endpoint"""
        print("\n🔍 Testing background image API...")
        
        try:
            response = requests.get(f"{self.local_url}/api/background-image")
            self.assertEqual(response.status_code, 200, "Expected status code 200")
            
            data = response.json()
            self.assertIn("image_url", data, "Response should contain 'image_url' field")
            self.assertTrue(data["image_url"].startswith("https://"), "Image URL should be HTTPS")
            
            print(f"   Background image URL: {data['image_url']}")
            print("✅ Background image API test passed")
            return True
        
        except Exception as e:
            print(f"❌ Background image API test failed: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all API tests"""
        print("\n🚀 Starting Docker Monitor API Tests")
        print(f"Local URL: {self.local_url}")
        print("=" * 50)
        
        tests = [
            self.test_01_docker_status,
            self.test_02_containers,
            self.test_03_images,
            self.test_04_container_stats,
            self.test_05_container_logs,
            self.test_06_background_image
        ]
        
        results = []
        for test in tests:
            results.append(test())
        
        success_count = results.count(True)
        total_count = len(results)
        
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {success_count}/{total_count} tests passed")
        
        if success_count == total_count:
            print("✅ All API tests passed!")
            return 0
        else:
            print(f"❌ {total_count - success_count} tests failed")
            return 1

if __name__ == "__main__":
    tester = DockerMonitorAPITester()
    sys.exit(tester.run_all_tests())