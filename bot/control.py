# bot/control.py
import asyncio, os, discord, time

from bot.state_manager import botStatus
from bot.instance import get_bot_instance, clear_bot_instance, botConfig, stop_ipc_bridge

# === START BOT ===
async def start_discord_bot():
    """Start the Discord bot using a fresh instance if needed."""
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("[CONTROL] BOT_TOKEN environment variable not set")

    bot = get_bot_instance()
    
    try:
        print("[CONTROL] Starting Discord bot...")
        await bot.start(token)
    except asyncio.CancelledError:
        print("[CONTROL] Bot start cancelled.")
    except Exception as e:
        print(f"[CONTROL] Failed to start bot: {e}")

# === STOP BOT ===
async def stop_discord_bot():
    """Gracefully disconnect from VC and close the Discord client."""
    bot = get_bot_instance()
    print("[CONTROL] Stopping Discord bot...")

    try:
        if botStatus.voice_client and botStatus.voice_client.is_connected():
            await botStatus.voice_client.disconnect(force=True)
            botStatus.in_vc = False
            print("[CONTROL] Disconnected from voice channel")

        if not bot.is_closed():
            await bot.close()
            print("[CONTROL] Discord bot stopped cleanly")

        clear_bot_instance()

    except Exception as e:
        print(f"[CONTROL] Error while stopping bot: {e}")
        
    await stop_ipc_bridge()

# === REBOOT BOT ===
async def reboot_discord_bot():
    """Fully restart the bot process."""
    print("[CONTROL] Rebooting Discord bot...")

    try:
        await stop_discord_bot()
    except Exception as e:
        print(f"[CONTROL] Error during reboot stop: {e}")

    await asyncio.sleep(2)
    
    await start_discord_bot()


# === EMBED POSTERS ===
async def post_queue_embed():
    DOMAIN = os.getenv("WS_DOMAIN")
    if not DOMAIN:
        print(f"[BOT] Domain env variable was never set!")
        return
    
    EMBED_LINK = f"https://{DOMAIN}/queue?format=image&ts={int(time.time())}"
    
    # Check if we've already posted the embed before posting a new one 
    msg = None
    if botStatus.queue_message_id:
        msg = await edit_message(botStatus.queue_message_id, message=EMBED_LINK)
        if msg == None:
            botStatus.queue_message_id = None
    
    # If the ID we have is invalid post a new message
    if not botStatus.queue_message_id:  
        msg = await send_message_to_channel_ID(message=EMBED_LINK)
    
    print(f"[BOT] Setting queue message id to {msg.id} and saving it")
    botStatus.queue_message_id = msg.id
    botConfig.save_bot_config({"queue_message_id": str(botStatus.queue_message_id)})
    
    

# === Message Helpers ===
async def send_message_to_channel_ID(message: str = None, embed=None, channel_id: int = None):
    """Safely send a message to the specified channel once the bot is ready."""
    bot = get_bot_instance()

    if not bot:
        print("[BOT] send_message_to_channel_ID: No bot instance available.")
        return

    # Wait until bot is ready
    if not bot.is_ready():
        print("[BOT] Waiting for bot to become ready before sending message...")
        try:
            await bot.wait_until_ready()
        except Exception as e:
            print(f"[BOT] wait_until_ready failed: {e}")
            return

    # Resolve channel ID from config if not provided

    if not channel_id:
        channel_id = int(botConfig.text_channel_id)
        if not channel_id:
            print("[BOT] No text_channel_id found in botConfig")
            return


    # Fetch channel safely
    try:
        channel = bot.get_channel(channel_id)
        if channel is None:
            print(f"[BOT] Channel {channel_id} not in cache, fetching...")
            channel = await bot.fetch_channel(channel_id)

        if not channel:
            print(f"[BOT] Could not resolve channel {channel_id}.")
            return

        # Finally send the message
        if embed:
            return await channel.send(embed=embed)
        else:     
            print(f"[BOT] Successfully sent message to channel {channel_id}")
            return await channel.send(message)

    except Exception as e:
        print(f"[BOT] Error sending message: {e}")

async def edit_message(message_id: int, message: str = None, embed: discord.Embed = None):
    if not message_id:
        raise ValueError("[BOT] No valid message reference provided")
    
    _message = None
    try:
        channel = get_bot_instance().get_channel(int(botConfig.text_channel_id))
        if channel is None:
            bot = get_bot_instance()
            channel = await bot.fetch_channel(int(botConfig.text_channel_id))
        _message = await channel.fetch_message(message_id)
    except Exception as e:
        print(f"[BOT] Failed to fetch message {message_id}: {e}")
        return None 
    
    try:
        if embed:
            await _message.edit(embed=embed)
        elif message:
            await _message.edit(content=message)
        else:
            raise ValueError("[BOT] No valid parameters to edit message were given")
        return message_id
        
    except discord.NotFound:
        print("[BOT] Message not found; cannot edit (likely deleted)")
    except discord.Forbidden:
        print("[BOT] Missing permissions to edit message")
    except Exception as e:
        print(f"[BOT] Error editing embed message: {e}")
        
    return None
    
