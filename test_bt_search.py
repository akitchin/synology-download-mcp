#!/usr/bin/env python3
"""
Test BT Search functionality in Synology Download Station
Search for "Vera" to validate search works
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
    print("Synology Download Station - BT Search Test")
    print("=========================================")
    print(f"Host: {SYNOLOGY_HOST}:{SYNOLOGY_PORT}")
    print(f"Search term: 'Vera'")
    print()
    
    # Get API Info
    params = {
        'api': 'SYNO.API.Info',
        'version': '1',
        'method': 'query',
        'query': 'SYNO.API.Auth,SYNO.DownloadStation.BTSearch'
    }
    
    data = make_request(f"{BASE_URL}/query.cgi", params)
    if not data['success']:
        print("Failed to get API info!")
        return 1
    
    api_info = data['data']
    
    # Login
    print("1. Logging in...")
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
    print("✓ Logged in successfully")
    
    try:
        # Check if BTSearch API is available
        if 'SYNO.DownloadStation.BTSearch' not in api_info:
            print("✗ BTSearch API not available!")
            return 1
        
        bt_info = api_info['SYNO.DownloadStation.BTSearch']
        
        # Get available modules first
        print("\n2. Getting available search modules...")
        params = {
            'api': 'SYNO.DownloadStation.BTSearch',
            'version': '1',
            'method': 'getModule',
            '_sid': sid
        }
        
        data = make_request(f"{BASE_URL}/{bt_info['path']}", params)
        if data['success']:
            modules = data['data']['modules']
            enabled_modules = [m for m in modules if m['enabled']]
            print(f"✓ Found {len(enabled_modules)} enabled modules:")
            for module in enabled_modules:
                print(f"  - {module['title']} ({module['id']})")
        
        # Get categories
        print("\n3. Getting search categories...")
        params = {
            'api': 'SYNO.DownloadStation.BTSearch',
            'version': '1',
            'method': 'getCategory',
            '_sid': sid
        }
        
        data = make_request(f"{BASE_URL}/{bt_info['path']}", params)
        if data['success']:
            categories = data['data']['categories']
            print(f"✓ Found {len(categories)} categories:")
            for cat in categories[:5]:  # Show first 5
                print(f"  - {cat['title']} (id: {cat['id']})")
        
        # Start search
        print("\n4. Starting search for 'Vera'...")
        params = {
            'api': 'SYNO.DownloadStation.BTSearch',
            'version': '1',
            'method': 'start',
            'keyword': 'Vera',
            'module': 'enabled',  # Use all enabled modules
            '_sid': sid
        }
        
        data = make_request(f"{BASE_URL}/{bt_info['path']}", params)
        if not data['success']:
            print(f"✗ Failed to start search: {data}")
            return 1
        
        task_id = data['data']['taskid']
        print(f"✓ Search started with task ID: {task_id}")
        
        # Wait a bit for search to process
        print("\n5. Waiting for search results...")
        time.sleep(3)
        
        # Get search results
        print("\n6. Retrieving search results...")
        params = {
            'api': 'SYNO.DownloadStation.BTSearch',
            'version': '1',
            'method': 'list',
            'taskid': task_id,
            'offset': 0,
            'limit': 20,
            'sort_by': 'seeds',
            'sort_direction': 'DESC',
            '_sid': sid
        }
        
        data = make_request(f"{BASE_URL}/{bt_info['path']}", params)
        if data['success']:
            results = data['data']
            print(f"✓ Search completed: {results['finished']}")
            print(f"✓ Total results: {results['total']}")
            
            if results['items']:
                print(f"\nTop {min(10, len(results['items']))} results:")
                for i, item in enumerate(results['items'][:10], 1):
                    size_mb = int(item['size']) / (1024 * 1024)
                    size_gb = size_mb / 1024
                    size_str = f"{size_gb:.2f} GB" if size_gb > 1 else f"{size_mb:.0f} MB"
                    
                    print(f"\n{i}. {item['title']}")
                    print(f"   Size: {size_str}")
                    print(f"   Seeds: {item['seeds']} | Leeches: {item['leechs']}")
                    print(f"   Date: {item['date']}")
                    print(f"   Module: {item['module_title']}")
                    if 'download_uri' in item:
                        print(f"   Download: {item['download_uri'][:50]}...")
            else:
                print("No results found!")
        else:
            print(f"✗ Failed to get results: {data}")
        
        # Clean up the search task
        print("\n7. Cleaning up search task...")
        params = {
            'api': 'SYNO.DownloadStation.BTSearch',
            'version': '1',
            'method': 'clean',
            'taskid': task_id,
            '_sid': sid
        }
        
        data = make_request(f"{BASE_URL}/{bt_info['path']}", params)
        if data['success']:
            print("✓ Search task cleaned up")
        
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
