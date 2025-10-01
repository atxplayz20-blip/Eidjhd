import os
import threading

def run_bot():
    """Run the Discord bot in a separate thread"""
    from bot import bot
    token = os.getenv('DISCORD_BOT_TOKEN')
    if token:
        bot.run(token)

if __name__ == '__main__':
    from database import init_database
    from app import app
    
    print("Initializing database...")
    init_database()
    
    print("Starting Discord bot in background...")
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    print("Starting web server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)
