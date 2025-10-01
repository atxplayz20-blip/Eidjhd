"""
Discord RPC Client Example

This script shows how users can run Discord RPC on their local machine
by fetching their custom RPC configuration from the website.

IMPORTANT: This must run on the user's computer where Discord is installed,
not on the web server. Discord RPC only works with local Discord clients.

Usage:
1. Get your user ID and API key from the dashboard
2. Run: python rpc_client_example.py YOUR_USER_ID YOUR_API_KEY
"""

import os
import sys
import time
import requests
from pypresence import Presence

WEBSITE_URL = os.getenv('WEBSITE_URL', 'http://localhost:5000')

def fetch_user_rpcs(user_id, api_key):
    """Fetch user's RPC configurations from the website"""
    try:
        headers = {'X-API-Key': api_key}
        response = requests.get(f'{WEBSITE_URL}/api/user/{user_id}/rpcs', headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch RPCs: {response.status_code}")
            if response.status_code == 401:
                print("Invalid API key. Please check your API key from the dashboard.")
            return None
    except Exception as e:
        print(f"Error fetching RPCs: {e}")
        return None

def start_rpc(rpc_config):
    """Start Discord RPC with given configuration"""
    try:
        app_id = rpc_config.get('app_id')
        if not app_id:
            print("No application ID found")
            return None
        
        RPC = Presence(app_id)
        RPC.connect()
        
        update_args = {}
        
        if rpc_config.get('details'):
            update_args['details'] = rpc_config['details']
        
        if rpc_config.get('state'):
            update_args['state'] = rpc_config['state']
        
        if rpc_config.get('timestamp_type') == 'live':
            update_args['start'] = int(time.time())
        elif rpc_config.get('custom_timestamp'):
            update_args['start'] = int(rpc_config['custom_timestamp'])
        
        if rpc_config.get('large_image_url'):
            update_args['large_image'] = rpc_config['large_image_url']
        if rpc_config.get('large_image_text'):
            update_args['large_text'] = rpc_config['large_image_text']
        
        if rpc_config.get('small_image_url'):
            update_args['small_image'] = rpc_config['small_image_url']
        if rpc_config.get('small_image_text'):
            update_args['small_text'] = rpc_config['small_image_text']
        
        if rpc_config.get('buttons'):
            import json
            buttons = json.loads(rpc_config['buttons']) if isinstance(rpc_config['buttons'], str) else rpc_config['buttons']
            if buttons:
                update_args['buttons'] = buttons
        
        RPC.update(**update_args)
        print(f"✓ RPC started for app {app_id}")
        return RPC
        
    except Exception as e:
        print(f"Error starting RPC: {e}")
        return None

def main():
    if len(sys.argv) < 3:
        print("Usage: python rpc_client_example.py YOUR_USER_ID YOUR_API_KEY")
        print("\nGet your User ID and API Key from the dashboard at:")
        print(f"  {WEBSITE_URL}")
        sys.exit(1)
    
    user_id = sys.argv[1]
    api_key = sys.argv[2]
    
    print(f"Fetching RPC configurations for user {user_id}...")
    rpcs_data = fetch_user_rpcs(user_id, api_key)
    
    if not rpcs_data or 'rpcs' not in rpcs_data:
        print("No RPC configurations found")
        return
    
    rpcs = rpcs_data['rpcs']
    default_rpc = rpcs_data.get('default_rpc')
    
    print(f"\nFound {len(rpcs)} custom RPC(s)")
    
    if rpcs:
        print("\nStarting first custom RPC...")
        rpc_instance = start_rpc(rpcs[0])
    elif default_rpc:
        print("\nNo custom RPCs, starting default RPC...")
        rpc_instance = start_rpc(default_rpc)
    else:
        print("No RPCs to start")
        return
    
    if rpc_instance:
        print("\n✓ RPC is now active on your Discord!")
        print("Press Ctrl+C to stop...")
        try:
            while True:
                time.sleep(15)
        except KeyboardInterrupt:
            print("\nStopping RPC...")
            rpc_instance.close()
            print("RPC stopped.")

if __name__ == '__main__':
    main()
