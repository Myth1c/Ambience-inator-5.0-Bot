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
    async def start_bot(self):
        """
        Starts the Discord bot ONCE by calling bot.start().
        Should ONLY be called from outside the bot core.
        """
        token = os.getenv("BOT_TOKEN")
        if not token:
            raise RuntimeError("BOT_TOKEN environment variable missing")

        bot = self.core.discord_bot
        if not bot:
            raise RuntimeError("[CONTROL] Discord bot not created yet")

        try:
            print("[CONTROL] Starting bot...")
            await bot.start(token)

        except asyncio.CancelledError:
            print("[CONTROL] Bot start cancelled")

        except Exception as e:
            print(f"[CONTROL] Error starting bot: {e}")

    async def stop_bot(self):
        """
        Gracefully disconnect VC, stop audio playback, close WS,
        and shut down Discord bot.
        """
        bot = self.core.discord_bot

        print("[CONTROL] Stopping Discord bot...")

        try:
            # Disconnect from VC if needed
            if self.core.state.voice_client:
                vc = self.core.state.voice_client

                if vc.is_connected():
                    await vc.disconnect(force=True)

                self.core.state.reset_voice_state()
                print("[CONTROL] Voice client disconnected")

            # Stop IPC bridge
            if self.core.ipc:
                await self.core.ipc.close()

            # Close Discord bot
            if bot and not bot.is_closed():
                await bot.close()
                print("[CONTROL] Bot closed cleanly")

        except Exception as e:
            print(f"[CONTROL] Error while stopping bot: {e}")

        print("[CONTROL] Finished bot shutdown.")

    async def reboot_bot(self):
        """
        Fully restart Discord bot.
        """
        print("[CONTROL] Reboot requested...")
        await self.stop_bot()
        await asyncio.sleep(2)
        await self.start_bot()


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

    async def edit_message(self, message_id: int, content=None, embed=None):
        """
        Edits an existing message safely.
        """
        bot = self.core.discord_bot
        channel_id = self.core.botConfig.get("text_channel_id")

        if not channel_id:
            print("[CONTROL] No text_channel_id configured")
            return None

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
