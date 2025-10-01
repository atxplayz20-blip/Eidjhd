# Discord Custom RPC Website

## Overview
Full-featured Discord Custom Rich Presence (RPC) website built with Python Flask. Users can login with Discord OAuth2, create custom RPCs with full customization options, and manage multiple rich presence configurations.

## Key Features
- **Discord OAuth2 Login**: Secure authentication with Discord
- **Persistent Sessions**: Lifetime login (1 year session duration)
- **Auto Server Join**: Automatically joins users to Discord server (ID: 1036197746417340496) on login
- **Default RPC**: Always-active default RPC with DrakLeafX button (App ID: 1419030874640613446)
- **Custom RPC Creation**: Full customization with:
  - Activity types (Playing, Listening, Watching, Competing)
  - Details and state fields
  - Timestamp options (live count, custom time, or none)
  - Large and small images with tooltips
  - Multiple buttons (up to 2)
- **RPC Management**: User's custom RPCs displayed above default RPC
- **Discord Bot**: Includes `/userdatalist` command to fetch all user data in JSON format

## Technology Stack
- **Backend**: Flask (Python)
- **Database**: PostgreSQL (via Replit)
- **Discord Integration**: discord.py, OAuth2
- **RPC Library**: pypresence
- **Session Management**: Flask-Session (filesystem-based)
- **Frontend**: HTML5, CSS3, JavaScript (vanilla)

## Project Structure
```
├── main.py              # Entry point, starts both bot and web server
├── app.py               # Flask web application
├── bot.py               # Discord bot with slash commands
├── database.py          # Database operations and schema
├── templates/           # HTML templates
│   ├── index.html      # Login page
│   └── dashboard.html  # User dashboard
├── static/             # Static assets
│   ├── css/style.css  # Styling
│   └── js/dashboard.js # Frontend logic
└── .gitignore          # Git ignore rules
```

## Configuration
- **Discord App ID**: 1419030874640613446 (Default RPC)
- **Discord Server**: 1036197746417340496
- **Default Button**: DrakLeafX → https://discord.gg/9HC8RANtJ9
- **Port**: 5000

## Environment Variables
Required secrets (configured in Replit Secrets):
- `DISCORD_CLIENT_ID`: Discord OAuth2 client ID
- `DISCORD_CLIENT_SECRET`: Discord OAuth2 client secret  
- `DISCORD_BOT_TOKEN`: Discord bot token
- `DATABASE_URL`: PostgreSQL connection string (auto-configured)

## Database Schema
### users table
- User authentication and profile data
- Stores Discord user info and OAuth tokens
- Tracks login history

### custom_rpcs table
- User-created RPC configurations
- Stores all RPC parameters (type, details, images, buttons)
- Soft delete with is_active flag

## Discord Bot Commands
- `/userdatalist`: Returns JSON data of all registered users (ephemeral response)

## Recent Changes
- 2025-09-29: Initial project creation with full feature set
- Implemented OAuth2 login with auto-join
- Created custom RPC management system
- Built responsive UI with gradient design
- Integrated Discord bot with slash commands

## RPC Implementation
Discord RPC (Rich Presence) works by connecting to a **local Discord client** on the user's computer. The pypresence library cannot remotely set RPC on users' Discord accounts from a web server.

### How It Works:
1. Users create and configure custom RPCs on the website
2. RPC configurations are stored in the database
3. Users download the RPC client script (`rpc_client_example.py`)
4. They run the client script on their computer where Discord is installed
5. The script fetches their RPC config via API endpoint `/api/user/<user_id>/rpcs`
6. The script uses pypresence to set the RPC on their local Discord

### API Endpoint:
- `GET /api/user/<user_id>/rpcs` - Returns user's custom RPCs and default RPC config in JSON format
- Requires authentication via `X-API-Key` header or `api_key` query parameter
- API key displayed on user dashboard after login

### Security Updates:
- OAuth2 flow now includes state parameter for CSRF protection
- State is validated on callback to prevent authorization code interception
- API key authentication system for secure RPC configuration access
- API keys generated on login and required for API access
- Keys stored in database with user verification

## Notes
- Sessions persist for 1 year (lifetime login as requested)
- If user revokes Discord OAuth access, they need to re-authenticate
- Default RPC button is always present alongside user's custom RPCs
- User custom RPCs appear first, default RPC shown below
- Maximum 2 buttons per RPC (Discord limitation)
- RPC client must be run locally on user's machine, not on the server
