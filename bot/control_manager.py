# bot/control_manager.py

import asyncio, os

class ControlManager:
    """
    Handles lifecycle controls (start/stop/reboot)
    and Discord message sending/editing utilities.
    """

    def __init__(self, core):
        self.core = core


    # =====================================================
    # BOT LIFECYCLE
    # =====================================================
    async def start_discord_bot(self):
        """
        Start the bot using the existing bot core
        """
        token = os.getenv("BOT_TOKEN")

        print("[CONTROL] Starting Discord bot...")

        if not self.core.discord_bot:
            # Re-create the bot if it was somehow destroyed
            self.core.create_discord_bot()

        await self.core.discord_bot.start(token)

    async def stop_discord_bot(self):
        """
        Gracefully disconnect VC, stop audio playback,
        and shut down Discord bot.
        """
        print("[CONTROL] Stopping Discord bot...")
        bot = self.core.discord_bot

        try:
            # Disconnect from VC if needed
            if self.core.state.voice_client and self.core.state.voice_client.is_connected():
                await self.core.state.voice_client.disconnect(force=True)
                self.core.state.reset_voice_state()
            
             # Close discord client
            if bot and not bot.is_closed():
                await bot.close()
                print("[CONTROL] Discord client closed")
            
            self.core.state.bot_online = "offline"

        except Exception as e:
            print(f"[CONTROL] Error while stopping bot: {e}")
            
        # Reset Core's ready-flag for next startup
        self.core._ready_event_fired = False
        self.core.ready = False
        
        # Remove the core's bot reference
        self.core.discord_bot = None

        print("[CONTROL] Finished bot shutdown.")

    async def reboot_discord_bot(self, delay: float = 5.0):
        """
        Fully restart the Discord client
        """
        print("[CONTROL] Rebooting Discord bot...")

        try:
            # Mark rebooting
            self.core.state.bot_online = "rebooting"

            # Stop Discord client (keeps IPC alive)
            await self.stop_discord_bot()

        except Exception as e:
            print(f"[CONTROL] Error during reboot (stop stage): {e}")
            return
            

        # Small delay before restart
        await asyncio.sleep(delay)

        try:
            await self.start_discord_bot()
            print("[CONTROL] Reboot complete.")

        except Exception as e:
            print(f"[CONTROL] Error restarting Discord bot: {e}")
            self.core.state.bot_online = "offline"
            return


    # =====================================================
    # MESSAGE SENDING
    # =====================================================
    async def send_message(self, content=None, embed=None, channel_id=None):
        """
        Sends a new message to a channel.
        """

        bot = self.core.discord_bot

        if not channel_id:
            channel_id = self.core.botConfig.get("text_channel_id")

        if not channel_id:
            print("[CONTROL] No channel ID provided")
            return None

        # Wait until bot is online
        try:
            if not bot.is_ready():
                print("[CONTROL] Waiting for bot readiness...")
                await bot.wait_until_ready()
        except Exception:
            pass

        try:
            channel = bot.get_channel(int(channel_id))

            if channel is None:
                channel = await bot.fetch_channel(int(channel_id))

            if embed:
                return await channel.send(embed=embed)
            else:
                return await channel.send(content)

        except Exception as e:
            print(f"[CONTROL] Failed to send message: {e}")
            return None

    async def edit_message(self, message_id: int, content=None, embed=None, channel_id=None):
        """
        Edits an existing message safely.
        """
        bot = self.core.discord_bot
        
        if not channel_id:
            channel_id = self.core.botConfig.get("text_channel_id")

        try:
            channel = bot.get_channel(int(channel_id))
            if channel is None:
                channel = await bot.fetch_channel(int(channel_id))

            msg = await channel.fetch_message(int(message_id))

        except Exception as e:
            print(f"[CONTROL] Failed to fetch message {message_id}: {e}")
            return None

        try:
            if embed:
                await msg.edit(embed=embed)
            elif content:
                await msg.edit(content=content)
            else:
                print("[CONTROL] Nothing to edit")
                return None

            return msg.id

        except Exception as e:
            print(f"[CONTROL] Error editing message: {e}")
            return None
