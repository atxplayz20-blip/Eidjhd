import json
import time
import threading
import sqlite3
from pypresence import Presence
from database import get_user_rpcs, get_db

class PersistentRPCManager:
    def __init__(self):
        self.active_rpcs = {}
        self.lock = threading.Lock()
        
    def _get_active_rpc_id(self, user_id):
        """Get the active RPC ID for a user from database"""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute('SELECT active_rpc_id FROM users WHERE id = ?', (user_id,))
            result = cur.fetchone()
            return result['active_rpc_id'] if result else None

    def _set_active_rpc_id(self, user_id, rpc_id):
        """Set the active RPC ID for a user in database"""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute('UPDATE users SET active_rpc_id = ? WHERE id = ?', (rpc_id, user_id))
            conn.commit()

    def _create_rpc_instance(self, app_id):
        """Create and connect a new RPC instance"""
        rpc = Presence(app_id)
        try:
            rpc.connect()
            return rpc
        except Exception as e:
            print(f"Failed to connect RPC: {e}")
            return None

    def activate_rpc(self, user_id, rpc_config):
        """Activate RPC for a user and persist the status"""
        with self.lock:
            try:
                app_id = rpc_config.get('app_id')
                if not app_id:
                    raise Exception("No application ID provided")

                # Deactivate existing RPC if any
                self.deactivate_rpc(user_id)

                # Create new RPC instance
                rpc = self._create_rpc_instance(app_id)
                if not rpc:
                    raise Exception("Failed to create RPC instance")

                # Prepare update arguments
                update_args = {
                    'details': rpc_config.get('details'),
                    'state': rpc_config.get('state')
                }

                # Handle timestamp
                if rpc_config.get('timestamp_type') == 'live':
                    update_args['start'] = int(time.time())
                elif rpc_config.get('custom_timestamp'):
                    update_args['start'] = int(rpc_config['custom_timestamp'])

                # Handle images
                if rpc_config.get('large_image_url'):
                    update_args['large_image'] = rpc_config['large_image_url']
                    if rpc_config.get('large_image_text'):
                        update_args['large_text'] = rpc_config['large_image_text']

                if rpc_config.get('small_image_url'):
                    update_args['small_image'] = rpc_config['small_image_url']
                    if rpc_config.get('small_image_text'):
                        update_args['small_text'] = rpc_config['small_image_text']

                # Handle buttons
                if rpc_config.get('buttons'):
                    buttons = json.loads(rpc_config['buttons']) if isinstance(rpc_config['buttons'], str) else rpc_config['buttons']
                    if buttons:
                        update_args['buttons'] = buttons

                # Update RPC
                rpc.update(**{k: v for k, v in update_args.items() if v is not None})
                
                # Store in memory
                self.active_rpcs[user_id] = rpc
                
                # Persist in database
                self._set_active_rpc_id(user_id, rpc_config.get('id'))
                
                print(f"✓ RPC activated and persisted for user {user_id} with app {app_id}")
                return True

            except Exception as e:
                print(f"Failed to activate RPC for user {user_id}: {e}")
                self.deactivate_rpc(user_id)
                raise e

    def deactivate_rpc(self, user_id):
        """Deactivate RPC for a user and remove persistent status"""
        with self.lock:
            if user_id in self.active_rpcs:
                try:
                    self.active_rpcs[user_id].close()
                except:
                    pass
                del self.active_rpcs[user_id]

            # Remove from database
            self._set_active_rpc_id(user_id, None)
            print(f"✓ RPC deactivated for user {user_id}")
            return True

    def restore_active_rpcs(self):
        """Restore active RPCs from database after restart"""
        print("Restoring active RPCs...")
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT users.id as user_id, custom_rpcs.* 
                FROM users 
                JOIN custom_rpcs ON users.active_rpc_id = custom_rpcs.id 
                WHERE users.active_rpc_id IS NOT NULL
            ''')
            active_rpcs = cur.fetchall()

        for rpc_data in active_rpcs:
            user_id = rpc_data['user_id']
            try:
                self.activate_rpc(user_id, rpc_data)
            except Exception as e:
                print(f"Failed to restore RPC for user {user_id}: {e}")

    def check_and_reconnect(self):
        """Periodically check and reconnect RPCs if needed"""
        while True:
            with self.lock:
                for user_id, rpc in list(self.active_rpcs.items()):
                    try:
                        # Try to update the presence to check connection
                        rpc.update(start=int(time.time()))
                    except:
                        # If failed, try to restore from database
                        active_rpc_id = self._get_active_rpc_id(user_id)
                        if active_rpc_id:
                            try:
                                with get_db() as conn:
                                    cur = conn.cursor()
                                    cur.execute('SELECT * FROM custom_rpcs WHERE id = ?', (active_rpc_id,))
                                    rpc_data = cur.fetchone()
                                    if rpc_data:
                                        self.activate_rpc(user_id, rpc_data)
                            except Exception as e:
                                print(f"Failed to reconnect RPC for user {user_id}: {e}")
            time.sleep(30)  # Check every 30 seconds

# Create a global instance
rpc_manager = PersistentRPCManager()

# Start background tasks
def start_background_tasks():
    # Start RPC check thread
    check_thread = threading.Thread(target=rpc_manager.check_and_reconnect, daemon=True)
    check_thread.start()
    
    # Restore active RPCs
    rpc_manager.restore_active_rpcs()

# Helper functions for the Flask app
def activate_user_rpc(user_id, rpc_config):
    return rpc_manager.activate_rpc(user_id, rpc_config)

def deactivate_user_rpc(user_id):
    return rpc_manager.deactivate_rpc(user_id)

def get_active_rpcs():
    return list(rpc_manager.active_rpcs.keys())