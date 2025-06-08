#!/usr/bin/env python3
"""
Test script for Synology Download Station API
Tests basic functionality: authentication, listing tasks, and creating tasks
"""

import requests
import json
import sys
from urllib.parse import quote

# Configuration
SYNOLOGY_HOST = "hostname"
SYNOLOGY_PORT = 5000
USERNAME = "username"
PASSWORD = "password"
BASE_URL = f"http://{SYNOLOGY_HOST}:{SYNOLOGY_PORT}/webapi"

# Disable SSL warnings for testing (remove in production)
requests.packages.urllib3.disable_warnings()

class SynologyDownloadStation:
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.base_url = f"http://{host}:{port}/webapi"
        self.sid = None
        self.api_info = {}
        
    def get_api_info(self):
        """Step 1: Get API Information"""
        print("Step 1: Getting API Information...")
        
        params = {
            'api': 'SYNO.API.Info',
            'version': '1',
            'method': 'query',
            'query': 'SYNO.API.Auth,SYNO.DownloadStation.Task,SYNO.DownloadStation.Info'
        }
        
        url = f"{self.base_url}/query.cgi"
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['success']:
            self.api_info = data['data']
            print("✓ API Information retrieved successfully")
            print(f"  Available APIs:")
            for api_name, api_data in self.api_info.items():
                print(f"    - {api_name}: {api_data['path']} (v{api_data['minVersion']}-{api_data['maxVersion']})")
            return True
        else:
            print(f"✗ Failed to get API info: Error {data.get('error', 'Unknown')}")
            return False
    
    def login(self):
        """Step 2: Session Login"""
        print("\nStep 2: Logging in...")
        
        if 'SYNO.API.Auth' not in self.api_info:
            print("✗ Auth API info not available")
            return False
            
        auth_info = self.api_info['SYNO.API.Auth']
        params = {
            'api': 'SYNO.API.Auth',
            'version': '2',
            'method': 'login',
            'account': self.username,
            'passwd': self.password,
            'session': 'DownloadStation',
            'format': 'sid'
        }
        
        url = f"{self.base_url}/{auth_info['path']}"
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['success']:
            self.sid = data['data']['sid']
            print(f"✓ Login successful! Session ID: {self.sid[:10]}...")
            return True
        else:
            error_codes = {
                400: "No such account or incorrect password",
                401: "Account disabled",
                402: "Permission denied",
                403: "2-step verification code required",
                404: "Failed to authenticate 2-step verification code"
            }
            error_msg = error_codes.get(data.get('error', 0), f"Unknown error: {data.get('error', 'Unknown')}")
            print(f"✗ Login failed: {error_msg}")
            return False
    
    def get_download_info(self):
        """Get Download Station Info"""
        print("\nGetting Download Station Info...")
        
        if 'SYNO.DownloadStation.Info' not in self.api_info:
            # Try to get it
            self.get_api_info()
            
        if 'SYNO.DownloadStation.Info' not in self.api_info:
            print("✗ Download Station Info API not available")
            return False
            
        info_api = self.api_info['SYNO.DownloadStation.Info']
        params = {
            'api': 'SYNO.DownloadStation.Info',
            'version': '1',
            'method': 'getinfo',
            '_sid': self.sid
        }
        
        url = f"{self.base_url}/{info_api['path']}"
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['success']:
            info = data['data']
            print("✓ Download Station Info:")
            print(f"  - Version: {info['version_string']} (build {info['version']})")
            print(f"  - Is Manager: {info['is_manager']}")
            return True
        else:
            print(f"✗ Failed to get info: Error {data.get('error', 'Unknown')}")
            return False
    
    def list_tasks(self):
        """Step 3: List Download Tasks"""
        print("\nStep 3: Listing download tasks...")
        
        if 'SYNO.DownloadStation.Task' not in self.api_info:
            print("✗ Task API info not available")
            return False
            
        task_info = self.api_info['SYNO.DownloadStation.Task']
        params = {
            'api': 'SYNO.DownloadStation.Task',
            'version': '1',
            'method': 'list',
            'additional': 'detail,transfer',
            '_sid': self.sid
        }
        
        url = f"{self.base_url}/{task_info['path']}"
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['success']:
            tasks = data['data']['tasks']
            total = data['data']['total']
            print(f"✓ Found {total} task(s)")
            
            if tasks:
                for i, task in enumerate(tasks):
                    print(f"\n  Task {i+1}:")
                    print(f"    - ID: {task['id']}")
                    print(f"    - Title: {task['title']}")
                    print(f"    - Type: {task['type']}")
                    print(f"    - Status: {task['status']}")
                    print(f"    - Size: {int(task['size']) / (1024*1024*1024):.2f} GB")
                    
                    if 'additional' in task and 'transfer' in task['additional']:
                        transfer = task['additional']['transfer']
                        downloaded = int(transfer['size_downloaded']) / (1024*1024*1024)
                        speed = int(transfer['speed_download']) / (1024*1024)
                        print(f"    - Downloaded: {downloaded:.2f} GB")
                        print(f"    - Speed: {speed:.2f} MB/s")
            else:
                print("  No tasks found")
            return True
        else:
            print(f"✗ Failed to list tasks: Error {data.get('error', 'Unknown')}")
            return False
    
    def create_test_task(self, uri):
        """Create a test download task"""
        print(f"\nCreating download task for: {uri}")
        
        if 'SYNO.DownloadStation.Task' not in self.api_info:
            print("✗ Task API info not available")
            return False
            
        task_info = self.api_info['SYNO.DownloadStation.Task']
        params = {
            'api': 'SYNO.DownloadStation.Task',
            'version': '1',
            'method': 'create',
            'uri': uri,
            '_sid': self.sid
        }
        
        url = f"{self.base_url}/{task_info['path']}"
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['success']:
            print("✓ Task created successfully!")
            return True
        else:
            error_codes = {
                400: "File upload failed",
                401: "Max number of tasks reached",
                402: "Destination denied",
                403: "Destination does not exist",
                404: "Invalid task id",
                405: "Invalid task action",
                406: "No default destination",
                407: "Set destination failed",
                408: "File does not exist"
            }
            error_msg = error_codes.get(data.get('error', 0), f"Unknown error: {data.get('error', 'Unknown')}")
            print(f"✗ Failed to create task: {error_msg}")
            return False
    
    def logout(self):
        """Step 4: Session Logout"""
        print("\nStep 4: Logging out...")
        
        if not self.sid:
            print("✗ No active session to logout")
            return False
            
        if 'SYNO.API.Auth' not in self.api_info:
            print("✗ Auth API info not available")
            return False
            
        auth_info = self.api_info['SYNO.API.Auth']
        params = {
            'api': 'SYNO.API.Auth',
            'version': '1',
            'method': 'logout',
            'session': 'DownloadStation',
            '_sid': self.sid
        }
        
        url = f"{self.base_url}/{auth_info['path']}"
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['success']:
            print("✓ Logout successful!")
            self.sid = None
            return True
        else:
            print(f"✗ Logout failed: Error {data.get('error', 'Unknown')}")
            return False


def main():
    print("Synology Download Station API Test")
    print("==================================")
    print(f"Host: {SYNOLOGY_HOST}:{SYNOLOGY_PORT}")
    print(f"User: {USERNAME}")
    print()
    
    # Create API client
    ds = SynologyDownloadStation(SYNOLOGY_HOST, SYNOLOGY_PORT, USERNAME, PASSWORD)
    
    try:
        # Step 1: Get API Info
        if not ds.get_api_info():
            print("Failed to get API info. Exiting.")
            return 1
        
        # Step 2: Login
        if not ds.login():
            print("Failed to login. Exiting.")
            return 1
        
        # Get Download Station Info
        ds.get_download_info()
        
        # Step 3: List tasks
        ds.list_tasks()
        
        # Optional: Create a test task
        # Uncomment the following lines to test creating a download task
        # test_uri = "http://www.example.com/test-file.zip"  # Replace with a real URL
        # ds.create_test_task(test_uri)
        
        # You can also test with a magnet link:
        # magnet_uri = "magnet:?xt=urn:btih:..."  # Replace with a real magnet link
        # ds.create_test_task(magnet_uri)
        
    finally:
        # Step 4: Always logout
        ds.logout()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
