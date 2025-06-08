#!/usr/bin/env python3
"""
Test various task operations in Synology Download Station
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
    print("Synology Download Station - Task Operations Test")
    print("===============================================")
    print(f"Host: {SYNOLOGY_HOST}:{SYNOLOGY_PORT}")
    print()
    
    # Get API Info
    params = {
        'api': 'SYNO.API.Info',
        'version': '1',
        'method': 'query',
        'query': 'SYNO.API.Auth,SYNO.DownloadStation.Task,SYNO.DownloadStation.BTSearch'
    }
    
    data = make_request(f"{BASE_URL}/query.cgi", params)
    if not data['success']:
        print("Failed to get API info!")
        return 1
    
    api_info = data['data']
    
    # Login
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
    print(f"✓ Logged in successfully")
    
    try:
        # Test 1: Get task info for a specific task
        print("\n1. Getting detailed info for task dbid_1...")
        task_info = api_info['SYNO.DownloadStation.Task']
        params = {
            'api': 'SYNO.DownloadStation.Task',
            'version': '1',
            'method': 'getinfo',
            'id': 'dbid_1',
            'additional': 'detail,transfer,file,tracker,peer',
            '_sid': sid
        }
        
        data = make_request(f"{BASE_URL}/{task_info['path']}", params)
        if data['success'] and data['data']['tasks']:
            task = data['data']['tasks'][0]
            print(f"✓ Task info retrieved:")
            print(f"  Title: {task['title']}")
            print(f"  Status: {task['status']}")
            print(f"  Size: {int(task['size']) / (1024*1024*1024):.2f} GB")
            
            if 'additional' in task:
                if 'detail' in task['additional']:
                    detail = task['additional']['detail']
                    print(f"  Destination: {detail['destination']}")
                    print(f"  Created: {detail['create_time']}")
                if 'transfer' in task['additional']:
                    transfer = task['additional']['transfer']
                    print(f"  Downloaded: {int(transfer['size_downloaded']) / (1024*1024):.2f} MB")
        
        # Test 2: Test BT Search API if available
        if 'SYNO.DownloadStation.BTSearch' in api_info:
            print("\n2. Testing BT Search API...")
            bt_info = api_info['SYNO.DownloadStation.BTSearch']
            
            # Get available modules
            params = {
                'api': 'SYNO.DownloadStation.BTSearch',
                'version': '1',
                'method': 'getModule',
                '_sid': sid
            }
            
            data = make_request(f"{BASE_URL}/{bt_info['path']}", params)
            if data['success']:
                modules = data['data']['modules']
                print(f"✓ Found {len(modules)} BT search modules:")
                for module in modules[:5]:  # Show first 5
                    status = "enabled" if module['enabled'] else "disabled"
                    print(f"  - {module['title']} ({module['id']}) - {status}")
        
        # Test 3: Get download statistics
        print("\n3. Getting download statistics...")
        params = {
            'api': 'SYNO.DownloadStation.Statistic',
            'version': '1',
            'method': 'getinfo',
            '_sid': sid
        }
        
        # Try to find the statistic API path
        stat_params = {
            'api': 'SYNO.API.Info',
            'version': '1',
            'method': 'query',
            'query': 'SYNO.DownloadStation.Statistic'
        }
        stat_data = make_request(f"{BASE_URL}/query.cgi", stat_params)
        
        if stat_data['success'] and 'SYNO.DownloadStation.Statistic' in stat_data['data']:
            stat_info = stat_data['data']['SYNO.DownloadStation.Statistic']
            params['_sid'] = sid
            
            data = make_request(f"{BASE_URL}/{stat_info['path']}", params)
            if data['success']:
                stats = data['data']
                print("✓ Download statistics:")
                print(f"  Download speed: {stats['speed_download'] / 1024:.2f} KB/s")
                print(f"  Upload speed: {stats['speed_upload'] / 1024:.2f} KB/s")
                print(f"  eMule download: {stats['emule_speed_download'] / 1024:.2f} KB/s")
                print(f"  eMule upload: {stats['emule_speed_upload'] / 1024:.2f} KB/s")
        
    finally:
        # Logout
        print("\nLogging out...")
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
