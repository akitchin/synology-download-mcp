#!/usr/bin/env python3
"""
Test creating a download task from BT search result
"""

import urllib.request
import urllib.parse
import json
import sys
import ssl
import time

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
    print("Synology Download Station - Search and Download Test")
    print("===================================================")
    print(f"Host: {SYNOLOGY_HOST}:{SYNOLOGY_PORT}")
    print()
    
    # Get API Info and login (simplified for brevity)
    params = {
        'api': 'SYNO.API.Info',
        'version': '1',
        'method': 'query',
        'query': 'SYNO.API.Auth,SYNO.DownloadStation.Task,SYNO.DownloadStation.BTSearch'
    }
    
    data = make_request(f"{BASE_URL}/query.cgi", params)
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
    sid = data['data']['sid']
    print("✓ Logged in successfully")
    
    try:
        # Search for a small torrent (Ubuntu)
        print("\n1. Searching for 'ubuntu 24.04'...")
        bt_info = api_info['SYNO.DownloadStation.BTSearch']
        params = {
            'api': 'SYNO.DownloadStation.BTSearch',
            'version': '1',
            'method': 'start',
            'keyword': 'ubuntu 24.04',
            'module': 'enabled',
            '_sid': sid
        }
        
        data = make_request(f"{BASE_URL}/{bt_info['path']}", params)
        task_id = data['data']['taskid']
        print(f"✓ Search started (ID: {task_id})")
        
        # Wait for results
        time.sleep(3)
        
        # Get results
        params = {
            'api': 'SYNO.DownloadStation.BTSearch',
            'version': '1',
            'method': 'list',
            'taskid': task_id,
            'offset': 0,
            'limit': 5,
            'sort_by': 'seeds',
            'sort_direction': 'DESC',
            '_sid': sid
        }
        
        data = make_request(f"{BASE_URL}/{bt_info['path']}", params)
        results = data['data']
        
        if results['items']:
            print(f"\n✓ Found {len(results['items'])} results")
            
            # Pick the first result with good seeds
            selected = results['items'][0]
            print(f"\n2. Selected torrent:")
            print(f"   Title: {selected['title']}")
            print(f"   Size: {int(selected['size']) / (1024*1024*1024):.2f} GB")
            print(f"   Seeds: {selected['seeds']}")
            
            # Create download task with the magnet link
            if 'download_uri' in selected and selected['download_uri'].startswith('magnet:'):
                print(f"\n3. Adding to download queue...")
                task_info = api_info['SYNO.DownloadStation.Task']
                params = {
                    'api': 'SYNO.DownloadStation.Task',
                    'version': '1',
                    'method': 'create',
                    'uri': selected['download_uri'],
                    '_sid': sid
                }
                
                data = make_request(f"{BASE_URL}/{task_info['path']}", params)
                if data['success']:
                    print("✓ Download task created successfully!")
                    
                    # Verify by listing recent tasks
                    print("\n4. Verifying download task...")
                    time.sleep(2)
                    
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
                        for task in data['data']['tasks']:
                            if selected['title'] in task['title']:
                                print(f"✓ Found new task: {task['title']}")
                                print(f"  Status: {task['status']}")
                                print(f"  Type: {task['type']}")
                                break
                else:
                    print(f"✗ Failed to create task: {data}")
            else:
                print("✗ No magnet link available for this result")
        
        # Clean up search
        params = {
            'api': 'SYNO.DownloadStation.BTSearch',
            'version': '1',
            'method': 'clean',
            'taskid': task_id,
            '_sid': sid
        }
        make_request(f"{BASE_URL}/{bt_info['path']}", params)
        
    finally:
        # Logout
        params = {
            'api': 'SYNO.API.Auth',
            'version': '1',
            'method': 'logout',
            'session': 'DownloadStation',
            '_sid': sid
        }
        make_request(f"{BASE_URL}/{auth_info['path']}", params)
        print("\n✓ Logged out")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
