import os
import discord
from discord import app_commands
from discord.ext import commands
import json
from database import get_all_users

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} is ready!')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')

@bot.tree.command(name="userdatalist", description="Get all registered users data in JSON format")
async def userdatalist(interaction: discord.Interaction):
    try:
        users = get_all_users()
        
        if not users:
            await interaction.response.send_message("No users found in database.", ephemeral=True)
            return
        
        user_data_list = []
        for user in users:
            user_dict = {
                'id': str(user['id']),
                'username': user['username'],
                'discriminator': user['discriminator'],
                'avatar': user['avatar'],
                'email': user['email'],
                'created_at': str(user['created_at']),
                'last_login': str(user['last_login'])
            }
            user_data_list.append(user_dict)
        
        # Split into multiple messages if needed (Discord has 2000 char limit)
        formatted_json = json.dumps(user_data_list, indent=2)
        
        if len(formatted_json) > 1900:
            # Send as file if too long
            with open('users_data.json', 'w') as f:
                json.dump(user_data_list, f, indent=2)
            
            await interaction.response.send_message(
                f"Found {len(user_data_list)} users. Data attached as JSON file.",
                file=discord.File('users_data.json'),
                ephemeral=True
            )
            os.remove('users_data.json')
        else:
            await interaction.response.send_message(
                f"```json\n{formatted_json}\n```",
                ephemeral=True
            )
    
    except Exception as e:
        await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)
        print(f"Error in userdatalist command: {e}")

if __name__ == '__main__':
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        raise ValueError('DISCORD_BOT_TOKEN environment variable is not set')
    bot.run(token)
