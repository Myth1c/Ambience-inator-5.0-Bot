# bot/display_manager.py

import asyncio

from utils import render_queue_embed


class DisplayManager:
    """
    Handles all Discord display output:
      - Queue message posting/editing
      - Pagination
      - Safe channel/message lookup
      - Integration with ConfigManager
    """
    def __init__(self, core):
        self.core = core
        self.page = 1               # default queue page
        self.per_page = 10
        self.lock = asyncio.Lock()  # ensure no double-writes

    # ======================================================================
    # CHANNEL RESOLUTION
    # ======================================================================
    async def _resolve_channel(self):
        """
        Get the configured text channel, fetching from API if needed.
        Returns discord.TextChannel or None.
        """
        bot = self.core.discord_bot
        cfg = self.core.botConfig.data

        channel_id = cfg.get("text_channel_id")
        if not channel_id:
            print("[DISPLAY] No text_channel_id set in config.")
            return None

        try:
            channel_id = int(channel_id)
        except ValueError:
            print("[DISPLAY] text_channel_id invalid:", channel_id)
            return None

        # Try cache
        channel = bot.get_channel(channel_id)
        if channel:
            return channel

        # Try fetch
        try:
            print(f"[DISPLAY] Fetching channel {channel_id}...")
            return await bot.fetch_channel(channel_id)
        except Exception as e:
            print(f"[DISPLAY] Failed to fetch channel {channel_id}: {e}")
            return None


    # ======================================================================
    # MESSAGE RESOLUTION
    # ======================================================================
    async def _resolve_message(self):
        """
        Fetch the queue message if it exists.
        Returns discord.Message or None.
        """
        channel = await self._resolve_channel()
        if not channel:
            return None

        msg_id = self.core.botConfig.data.get("queue_message_id")
        if not msg_id:
            return None

        try:
            msg_id = int(msg_id)
            return await channel.fetch_message(msg_id)
        except Exception as e:
            print(f"[DISPLAY] Failed to fetch queue message {msg_id}: {e}")
            return None


    # ======================================================================
    # QUEUE DISPLAY
    # ======================================================================
    async def update_queue_display(self, page: int = None):
        """
        High-level function:
          - Build embed
          - Resolve channel/message IDs
          - Use ControlManager to send or edit
        """
        async with self.lock:
            if page:
                self.page = max(1, int(page))

            bot = self.core.discord_bot
            if not bot or not bot.is_ready():
                print("[DISPLAY] Bot not ready — cannot update queue yet.")
                return

            # --- build new embed using queue snapshot ---
            queue_state = self.core.queue.get_state()
            embed = render_queue_embed(queue_state, page=self.page, per_page=self.per_page)
            
            cfg = self.core.botConfig.data
            text_id = cfg.get_int("text_channel_id")
            msg_id = cfg.get_int("queue_message_id")
            
            if not text_id:
                print("[DISPLAY] No text_channel_id in config -- Cannot display queue.")
            
            # Try editing the existing message before creating a new one
            if msg_id:
                edited = await self.core.control.edit_message(
                    message_id=msg_id,
                    embed=embed,
                    channel_id=text_id
                )
                
                if edited:
                    print("[DISPLAY] Queue message edited")
                    return
                else:
                    print("[DISPLAY] Could not edit queue message -- Creating a new one.")
                    
            # Create a new message
            new_msg = await self.core.control.send_message(
                embed=embed,
                channel_id=text_id
            )
            
            if new_msg:
                self.core.botConfig.save("queue_message_id", new_msg)
                print("[DISPLAY] Queue message created")


    # ======================================================================
    # MANUAL CONTROLS
    # ======================================================================
    async def set_page(self, page: int):
        """Set page and refresh the UI."""
        self.page = max(1, int(page))
        await self.update_queue_display()

    async def next_page(self):
        """Moves to next page and updates."""
        self.page += 1
        await self.update_queue_display()

    async def previous_page(self):
        """Moves to previous page and updates."""
        self.page = max(1, self.page - 1)
        await self.update_queue_display()
