import requests
import unittest
import sys
import os
import json
from datetime import datetime

class DockerMonitorAPITester(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(DockerMonitorAPITester, self).__init__(*args, **kwargs)
        # Get the backend URL from frontend .env file
        self.base_url = "https://7df86c00-9eb7-4488-bc90-62b661914306.preview.emergentagent.com"
        self.container_id = None  # Will be set after getting containers

    def test_01_docker_status(self):
        """Test Docker status endpoint"""
        print("\n🔍 Testing Docker status API...")
        
        try:
            response = requests.get(f"{self.base_url}/api/docker/status")
            self.assertEqual(response.status_code, 200, "Expected status code 200")
            
            data = response.json()
            self.assertIn("status", data, "Response should contain 'status' field")
            self.assertEqual(data["status"], "connected", "Docker should be connected")
            
            # Check for required fields
            required_fields = ["containers_running", "containers_paused", 
                              "containers_stopped", "images", "server_version"]
            for field in required_fields:
                self.assertIn(field, data, f"Response should contain '{field}' field")
            
            print("✅ Docker status API test passed")
            print(f"   Docker version: {data.get('server_version')}")
            print(f"   Running containers: {data.get('containers_running')}")
            print(f"   Images: {data.get('images')}")
            return True
        
        except Exception as e:
            print(f"❌ Docker status API test failed: {str(e)}")
            return False

    def test_02_containers(self):
        """Test containers endpoint"""
        print("\n🔍 Testing containers API...")
        
        try:
            response = requests.get(f"{self.base_url}/api/containers")
            self.assertEqual(response.status_code, 200, "Expected status code 200")
            
            data = response.json()
            self.assertIn("containers", data, "Response should contain 'containers' field")
            self.assertIsInstance(data["containers"], list, "'containers' should be a list")
            
            # Store a container ID for later tests if containers exist
            if data["containers"]:
                self.container_id = data["containers"][0]["id"]
                print(f"   Found {len(data['containers'])} containers")
                print(f"   First container: {data['containers'][0]['name']} ({data['containers'][0]['status']})")
            else:
                print("   No containers found")
            
            print("✅ Containers API test passed")
            return True
        
        except Exception as e:
            print(f"❌ Containers API test failed: {str(e)}")
            return False

    def test_03_images(self):
        """Test images endpoint"""
        print("\n🔍 Testing images API...")
        
        try:
            response = requests.get(f"{self.base_url}/api/images")
            self.assertEqual(response.status_code, 200, "Expected status code 200")
            
            data = response.json()
            self.assertIn("images", data, "Response should contain 'images' field")
            self.assertIsInstance(data["images"], list, "'images' should be a list")
            
            if data["images"]:
                print(f"   Found {len(data['images'])} images")
                print(f"   First image: {data['images'][0]['tag']}")
            else:
                print("   No images found")
            
            print("✅ Images API test passed")
            return True
        
        except Exception as e:
            print(f"❌ Images API test failed: {str(e)}")
            return False

    def test_04_container_stats(self):
        """Test container stats endpoint"""
        if not self.container_id:
            print("\n⚠️ Skipping container stats test - no container ID available")
            return True
        
        print(f"\n🔍 Testing container stats API for container {self.container_id[:12]}...")
        
        try:
            response = requests.get(f"{self.base_url}/api/containers/{self.container_id}/stats")
            self.assertEqual(response.status_code, 200, "Expected status code 200")
            
            data = response.json()
            required_fields = ["container_id", "cpu_percent", "memory_usage", 
                              "memory_limit", "memory_percent", "network_rx", "network_tx"]
            
            for field in required_fields:
                self.assertIn(field, data, f"Response should contain '{field}' field")
            
            print(f"   CPU: {data.get('cpu_percent')}%")
            print(f"   Memory: {data.get('memory_percent')}%")
            print("✅ Container stats API test passed")
            return True
        
        except Exception as e:
            print(f"❌ Container stats API test failed: {str(e)}")
            return False

    def test_05_container_logs(self):
        """Test container logs endpoint"""
        if not self.container_id:
            print("\n⚠️ Skipping container logs test - no container ID available")
            return True
        
        print(f"\n🔍 Testing container logs API for container {self.container_id[:12]}...")
        
        try:
            response = requests.get(f"{self.base_url}/api/containers/{self.container_id}/logs")
            self.assertEqual(response.status_code, 200, "Expected status code 200")
            
            data = response.json()
            required_fields = ["container_id", "logs", "tail"]
            
            for field in required_fields:
                self.assertIn(field, data, f"Response should contain '{field}' field")
            
            log_lines = data.get("logs", "").count("\n")
            print(f"   Retrieved {log_lines} log lines")
            print("✅ Container logs API test passed")
            return True
        
        except Exception as e:
            print(f"❌ Container logs API test failed: {str(e)}")
            return False

    def test_06_background_image(self):
        """Test background image endpoint"""
        print("\n🔍 Testing background image API...")
        
        try:
            response = requests.get(f"{self.base_url}/api/background-image")
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
        print(f"Base URL: {self.base_url}")
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