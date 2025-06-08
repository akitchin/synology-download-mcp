#!/usr/bin/env python3
"""
Test creating a download task in Synology Download Station
"""

import urllib.request
import urllib.parse
import json
import sys
import ssl

# Configuration
SYNOLOGY_HOST = "hostname"
SYNOLOGY_PORT = 5000
USERNAME = "username"
PASSWORD = "password"
BASE_URL = f"http://{SYNOLOGY_HOST}:{SYNOLOGY_PORT}/webapi"

# Test file URL - a small public domain file
TEST_URL = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"

# Create SSL context
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def make_request(url, params=None):
    """Make HTTP request and return JSON response"""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(url, context=ssl_context) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Request failed: {e}")
        return {'success': False, 'error': str(e)}

def main():
    print("Synology Download Station - Create Task Test")
    print("===========================================")
    print(f"Host: {SYNOLOGY_HOST}:{SYNOLOGY_PORT}")
    print(f"Test URL: {TEST_URL}")
    print()
    
    # Step 1: Get API Info
    print("1. Getting API info...")
    params = {
        'api': 'SYNO.API.Info',
        'version': '1',
        'method': 'query',
        'query': 'SYNO.API.Auth,SYNO.DownloadStation.Task'
    }
    
    data = make_request(f"{BASE_URL}/query.cgi", params)
    if not data['success']:
        print("Failed to get API info!")
        return 1
    
    api_info = data['data']
    print("✓ API info retrieved")
    
    # Step 2: Login
    print("\n2. Logging in...")
    auth_info = api_info['SYNO.API.Auth']
    params = {
        'api': 'SYNO.API.Auth',
        'version': '3',
        'method': 'login',
        'account': USERNAME,
        'passwd': PASSWORD,
        'session': 'DownloadStation',
        'format': 'sid'
    }
    
    data = make_request(f"{BASE_URL}/{auth_info['path']}", params)
    if not data.get('success'):
        print("Failed to login!")
        return 1
    
    sid = data['data']['sid']
    print(f"✓ Logged in (Session: {sid[:10]}...)")
    
    # Step 3: Create download task
    print(f"\n3. Creating download task...")
    task_info = api_info['SYNO.DownloadStation.Task']
    params = {
        'api': 'SYNO.DownloadStation.Task',
        'version': '1',
        'method': 'create',
        'uri': TEST_URL,
        '_sid': sid
    }
    
    data = make_request(f"{BASE_URL}/{task_info['path']}", params)
    if data['success']:
        print("✓ Task created successfully!")
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
        error_value = data.get('error')
        if isinstance(error_value, dict):
            error_code = error_value.get('code', 0)
            error_msg = error_codes.get(error_code, f"Error: {json.dumps(error_value)}")
        else:
            error_msg = error_codes.get(error_value, f"Unknown error: {error_value}")
        print(f"✗ Failed to create task: {error_msg}")
    
    # Step 4: List tasks to verify
    print("\n4. Listing recent tasks...")
    params = {
        'api': 'SYNO.DownloadStation.Task',
        'version': '1',
        'method': 'list',
        'offset': 0,
        'limit': 5,
        'additional': 'detail,transfer',
        '_sid': sid
    }
    
    data = make_request(f"{BASE_URL}/{task_info['path']}", params)
    if data['success']:
        tasks = data['data']['tasks']
        print(f"✓ Found {len(tasks)} recent task(s):")
        for task in tasks:
            print(f"  - {task['title']} ({task['status']})")
    
    # Step 5: Logout
    print("\n5. Logging out...")
    params = {
        'api': 'SYNO.API.Auth',
        'version': '1',
        'method': 'logout',
        'session': 'DownloadStation',
        '_sid': sid
    }
    
    data = make_request(f"{BASE_URL}/{auth_info['path']}", params)
    if data['success']:
        print("✓ Logged out successfully")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
