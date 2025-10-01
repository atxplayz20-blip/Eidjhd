import os
import json
import time
import secrets
from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from flask_session import Session
import requests
from datetime import datetime
from database import init_database, create_or_update_user, get_user, get_all_users, create_custom_rpc, get_user_rpcs, delete_custom_rpc, generate_api_key, verify_api_key
from rpc_persistent import activate_user_rpc, deactivate_user_rpc, start_background_tasks, rpc_manager

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 31536000  # 1 year
Session(app)

@app.template_filter('fromjson')
def fromjson_filter(value):
    if value:
        return json.loads(value)
    return []

DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID', '1419030874640613446')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = 'http://localhost:5000/api/auth/callback'
DISCORD_API_BASE = 'https://discord.com/api/v10'
DISCORD_OAUTH_URL = f'{DISCORD_API_BASE}/oauth2/authorize'
DISCORD_TOKEN_URL = f'{DISCORD_API_BASE}/oauth2/token'
GUILD_ID = '1036197746417340496'

# Debug information
print(f"Discord Client ID: {DISCORD_CLIENT_ID}")
print(f"Discord Redirect URI: {DISCORD_REDIRECT_URI}")
print("App running on: http://localhost:5000")

DEFAULT_RPC = {
    'app_id': '1419030874640613446',
    'button_name': 'DrakLeafX',
    'button_url': 'https://discord.gg/9HC8RANtJ9'
}

@app.route('/')
def index():
    if 'user_id' in session:
        user = get_user(session['user_id'])
        if user:
            return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login')
def login():
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    # Use urllib.parse.urlencode for proper URL encoding
    from urllib.parse import urlencode
    
    params = {
        'client_id': DISCORD_CLIENT_ID,
        'redirect_uri': DISCORD_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'identify email',
        'state': state
    }
    
    auth_url = f"{DISCORD_OAUTH_URL}?{urlencode(params)}"
    print(f"Discord OAuth URL: {auth_url}")
    return redirect(auth_url)

@app.route('/api/auth/callback')
def callback():
    try:
        print(f"Callback received with args: {dict(request.args)}")
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            print(f"OAuth error: {error}")
            return f'<h1>Discord OAuth Error</h1><p>Error: {error}</p><a href="/">Try Again</a>'
        
        if not code:
            print("Missing authorization code")
            return f'<h1>Missing Authorization Code</h1><p>Please try logging in again.</p><a href="/">Go Back</a>'
        
        if not state:
            print("Missing state parameter")
            return f'<h1>Missing State Parameter</h1><p>Security check failed.</p><a href="/">Go Back</a>'
        
        if state != session.get('oauth_state'):
            print(f"Invalid state. Expected: {session.get('oauth_state')}, Got: {state}")
            return f'<h1>Invalid State</h1><p>Security check failed. Please try again.</p><a href="/">Go Back</a>'
        
        session.pop('oauth_state', None)
        
        # Set default client secret if not provided
        DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET', 'your_client_secret_here')  # Replace with your client secret
        
        # Exchange code for token
        data = {
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': DISCORD_REDIRECT_URI
        }
        
        print(f"Exchanging code for token with Discord...")
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(DISCORD_TOKEN_URL, data=data, headers=headers)
        
        print(f"Discord token response: {response.status_code}")
        if response.status_code != 200:
            print(f"Failed to authenticate with Discord: {response.status_code} - {response.text}")
            return f'<h1>Discord Authentication Failed</h1><p>Status: {response.status_code}</p><p>Error: {response.text}</p><a href="/">Try Again</a>'
        
        tokens = response.json()
        access_token = tokens['access_token']
        
        # Get user info
        headers = {'Authorization': f'Bearer {access_token}'}
        user_response = requests.get(f'{DISCORD_API_BASE}/users/@me', headers=headers)
        
        if user_response.status_code != 200:
            print(f"Failed to get user info: {user_response.status_code} - {user_response.text}")
            return redirect(url_for('index'))
        
        user_data = user_response.json()
        
        # Add user to guild
        try:
            guild_url = f'{DISCORD_API_BASE}/guilds/{GUILD_ID}/members/{user_data["id"]}'
            guild_data = {'access_token': access_token}
            bot_headers = {
                'Authorization': f'Bot {os.getenv("DISCORD_BOT_TOKEN")}',
                'Content-Type': 'application/json'
            }
            requests.put(guild_url, json=guild_data, headers=bot_headers)
        except Exception as e:
            print(f"Failed to add user to guild: {e}")
        
        # Save to database
        create_or_update_user(user_data, tokens)
        
        # Generate API key for RPC client
        api_key = generate_api_key(int(user_data['id']))
        
        # Set session
        session['user_id'] = int(user_data['id'])
        session['access_token'] = access_token
        session['api_key'] = api_key
        session.permanent = True
        
        print(f"User {user_data['username']} logged in successfully")
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        print(f"Callback error: {str(e)}")
        return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user = get_user(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('index'))
    
    custom_rpcs = get_user_rpcs(session['user_id'])
    
    return render_template('dashboard.html', user=user, custom_rpcs=custom_rpcs, default_rpc=DEFAULT_RPC)

@app.route('/create_rpc', methods=['POST'])
def create_rpc():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json or {}
    buttons = []
    
    # Parse buttons
    if data.get('buttons'):
        for btn in data['buttons']:
            if btn.get('name') and btn.get('url'):
                buttons.append({'label': btn['name'], 'url': btn['url']})
    
    rpc_data = {
        'app_id': data.get('app_id'),
        'rpc_type': data.get('rpc_type', 'Playing'),
        'details': data.get('details'),
        'state': data.get('state'),
        'timestamp_type': data.get('timestamp_type', 'live'),
        'custom_timestamp': data.get('custom_timestamp'),
        'large_image_url': data.get('large_image_url'),
        'large_image_text': data.get('large_image_text'),
        'small_image_url': data.get('small_image_url'),
        'small_image_text': data.get('small_image_text'),
        'buttons': json.dumps(buttons) if buttons else None
    }
    
    rpc_id = create_custom_rpc(session['user_id'], rpc_data)
    
    # Try to activate RPC directly from server
    try:
        from rpc_manager import activate_user_rpc
        activate_user_rpc(session['user_id'], rpc_data)
        return jsonify({'success': True, 'rpc_id': rpc_id, 'activated': True})
    except Exception as e:
        print(f"Failed to activate RPC directly: {e}")
        return jsonify({'success': True, 'rpc_id': rpc_id, 'activated': False, 'message': 'RPC saved but requires client activation'})

@app.route('/delete_rpc/<int:rpc_id>', methods=['POST'])
def delete_rpc(rpc_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    delete_custom_rpc(rpc_id, session['user_id'])
    return jsonify({'success': True})

@app.route('/activate_rpc/<int:rpc_id>', methods=['POST'])
def activate_rpc_route(rpc_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from rpc_manager import activate_user_rpc
        from database import get_rpc_by_id
        
        rpc_config = get_rpc_by_id(rpc_id, session['user_id'])
        if not rpc_config:
            return jsonify({'error': 'RPC not found'}), 404
        
        activate_user_rpc(session['user_id'], rpc_config)
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/deactivate_rpcs', methods=['POST'])
def deactivate_rpcs_route():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        deactivate_user_rpc(session['user_id'])
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/user/<int:user_id>/rpcs')
def get_user_rpcs_api(user_id):
    """API endpoint to fetch user's RPC configurations for client-side application"""
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    
    if not api_key:
        return jsonify({'success': False, 'error': 'API key required'}), 401
    
    authenticated_user_id = verify_api_key(api_key)
    if not authenticated_user_id or authenticated_user_id != user_id:
        return jsonify({'success': False, 'error': 'Invalid API key'}), 401
    
    try:
        custom_rpcs = get_user_rpcs(user_id)
        
        rpcs_list = []
        for rpc in custom_rpcs:
            rpcs_list.append({
                'id': rpc['id'],
                'app_id': rpc['app_id'],
                'rpc_type': rpc['rpc_type'],
                'details': rpc['details'],
                'state': rpc['state'],
                'timestamp_type': rpc['timestamp_type'],
                'custom_timestamp': rpc['custom_timestamp'],
                'large_image_url': rpc['large_image_url'],
                'large_image_text': rpc['large_image_text'],
                'small_image_url': rpc['small_image_url'],
                'small_image_text': rpc['small_image_text'],
                'buttons': rpc['buttons']
            })
        
        default_rpc_config = {
            'app_id': DEFAULT_RPC['app_id'],
            'details': 'DrakLeafX Community',
            'state': 'Join us!',
            'buttons': json.dumps([{
                'label': DEFAULT_RPC['button_name'],
                'url': DEFAULT_RPC['button_url']
            }])
        }
        
        return jsonify({
            'success': True,
            'rpcs': rpcs_list,
            'default_rpc': default_rpc_config
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/test')
def test():
    return '<h1>Website is working!</h1><p>If you can see this, the Flask app is running correctly.</p>'

@app.errorhandler(404)
def not_found(error):
    return f'<h1>404 - Page Not Found</h1><p>Requested URL: {request.url}</p><p>Available routes: /, /login, /api/auth/callback, /dashboard, /logout, /test</p>', 404

@app.errorhandler(500)
def internal_error(error):
    return f'<h1>500 - Internal Server Error</h1><p>Error: {str(error)}</p>', 500

if __name__ == '__main__':
    init_database()
    start_background_tasks()
    app.run(host='0.0.0.0', port=5000, debug=True)
