
import json
import time
import threading
from pypresence import Presence
from database import get_user_rpcs

# Store active RPC instances
active_rpcs = {}

def activate_user_rpc(user_id, rpc_config):
    """Activate RPC for a user on the server"""
    try:
        app_id = rpc_config.get('app_id')
        if not app_id:
            raise Exception("No application ID provided")
        
        # Stop existing RPC if any
        if user_id in active_rpcs:
            try:
                active_rpcs[user_id].close()
            except:
                pass
            del active_rpcs[user_id]
        
        # Create new RPC instance
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
            buttons = json.loads(rpc_config['buttons']) if isinstance(rpc_config['buttons'], str) else rpc_config['buttons']
            if buttons:
                update_args['buttons'] = buttons
        
        RPC.update(**update_args)
        active_rpcs[user_id] = RPC
        
        print(f"✓ RPC activated for user {user_id} with app {app_id}")
        return True
        
    except Exception as e:
        print(f"Failed to activate RPC for user {user_id}: {e}")
        raise e

def deactivate_user_rpc(user_id):
    """Deactivate RPC for a user"""
    if user_id in active_rpcs:
        try:
            active_rpcs[user_id].close()
            del active_rpcs[user_id]
            print(f"✓ RPC deactivated for user {user_id}")
            return True
        except Exception as e:
            print(f"Failed to deactivate RPC for user {user_id}: {e}")
            return False
    return False

def get_active_rpcs():
    """Get list of users with active RPCs"""
    return list(active_rpcs.keys())

def restart_rpc_manager():
    """Restart all active RPCs (useful after server restart)"""
    print("Restarting RPC manager...")
    for user_id in list(active_rpcs.keys()):
        deactivate_user_rpc(user_id)
    
    # Auto-activate RPCs for users who have them configured
    # This would require storing active state in database
    print("RPC manager restarted")
