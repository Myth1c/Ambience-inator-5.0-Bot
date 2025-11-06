# bot/instance.py

import discord, os, asyncio

from discord.ext import commands
from bot.state_manager import botStatus
from config.json_helper import load_json, save_json
from bot.ipc_bridge import IPCBridge

_bot_instance = None  # Singleton holder
_ipc_bridge = None
_ipc_task = None

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config/bot_config.json")

class BotConfig():
    def __init__(self):
        self.voice_channel_id = None,
        self.text_channel_id = None,
        self.queue_message_id = None
        
    async def load_bot_config(self):
        config = load_json(CONFIG_FILE, default_data={})
        
        self.voice_channel_id = config.get("voice_channel_id")
        self.text_channel_id = config.get("text_channel_id")
        self.queue_message_id = config.get("queue_message_id")
        
        bot = get_bot_instance()
        try:
                
            channel = bot.get_channel(int(self.text_channel_id))
            if channel is None:
                channel = await bot.fetch_channel(int(self.text_channel_id))
            
            if self.queue_message_id:
                try:
                    msg = await channel.fetch_message(int(self.queue_message_id))
                    botStatus.queue_message_id = msg.id
                    print(f"[BOT] Loaded queue message ID {botStatus.queue_message_id}")
                except Exception as e:
                    print(f"[BOT] Failed to fetch queue message {self.queue_message_id}: {e}")
                    botConfig.save_bot_config({"queue_message_id": "None"})
                except discord.NotFound:
                    print(f"[BOT] Message {self.queue_message_id} not found — clearing from config")
                    botConfig.save_bot_config({"queue_message_id": "None"})
                    
        except Exception as e:
            print(f"[BOT] Failed to load message IDs from config: {e}")
            

    
    @staticmethod
    def save_bot_config(data):
        """Safely merge and save bot configuration."""
        curConfig = load_json(CONFIG_FILE, default_data={})

        updated_config = curConfig.copy()
        for key in ["voice_channel_id", "text_channel_id", "ngrok_message_id", "queue_message_id"]:
            value = data.get(key)
            if value not in ("", None):
                updated_config[key] = str(value)

        save_json(CONFIG_FILE, updated_config)
        print(f"[CONFIG] Saved updated bot_config: {updated_config}")
        

def get_bot_instance():
    """Return the current bot instance, or create a new one if needed."""
    global _bot_instance
    if _bot_instance is None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.members = True
        intents.guilds = True

        _bot_instance = commands.Bot(command_prefix="!", intents=intents)
        
        @_bot_instance.event
        async def on_ready():
            global _ipc_bridge, _ipc_task
            
            print(f"[BOT] Logged in as {_bot_instance.user}")
            
            botStatus.is_running = "online"
            
            await botConfig.load_bot_config()
            # --- Post the "Online Status" Embed of the bot ---
            # If I make that, that is
            
            # Post the first queue message on startup
            from bot.control import post_queue_embed
            await post_queue_embed()
            
            # --- Start the IPC Bridge ---
            if _ipc_bridge is None:
                _ipc_bridge = IPCBridge()
                _ipc_task = asyncio.create_task(_ipc_bridge.listen_loop())
                print("[INSTANCE] IPC Bridge started")

    return _bot_instance


def set_bot_instance(bot):
    """Allow manual override if needed (rarely used)."""
    global _bot_instance
    _bot_instance = bot


def clear_bot_instance():
    """Clear the current bot instance so it can be recreated."""
    global _bot_instance
    _bot_instance = None

async def stop_ipc_bridge():
    global _ipc_bridge, _ipc_task
    
    if _ipc_bridge:
        await _ipc_bridge.close()
        _ipc_bridge = None
    if _ipc_task:
        _ipc_task.cancel()
        _ipc_task = None
        
    print("[INSTANCE] IPC Bridge Stopped")
       
botConfig = BotConfig()