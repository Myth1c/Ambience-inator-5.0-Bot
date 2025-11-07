# bot/config_manager.py

import os, discord

from config import load_json, save_json

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "config",
    "bot_config.json"
)

class ConfigManager:
    """
    Environment-aware config manager.
    Loads and saves bot configuration from:
        - ENV CONFIG_PATH if set
        - otherwise /config/bot_config.json
    """
    def __init__(self):
        # Allow override via environment variable
        self.path = os.getenv("CONFIG_PATH", DEFAULT_CONFIG_PATH)

        # Runtime copy of config values
        self.data = {
            "voice_channel_id": None,
            "text_channel_id": None,
            "queue_message_id": None,
        }

    # =======================================================================
    # FILE INITIALIZATION
    # =======================================================================
    def _ensure_file_exists(self):
        """If config file does not exist, create a minimal empty one."""
        if not os.path.exists(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)

            # Create empty config file
            save_json(self.path, {})
            print(f"[CONFIG] Created new config file at: {self.path}")

    # ============================================================
    # LOAD CONFIG
    # ============================================================
    async def load(self):
        """Load config JSON and populate internal data."""
        
        self._ensure_file_exists()
        
        config = load_json(self.path, default_data={})

        for key in self.data.keys():
            raw = config.get(key)
            self.data[key] = self._parse_value(raw)

        print(f"[CONFIG] Loaded from {self.path}: {self.data}")

    def _parse_value(self, raw):
        """
        Convert raw saved string into value:
            - None or ""  → None
            - int-like   → int
            - bool-like  → bool
            - else       → string
        """

        if raw in (None, ""):
            return None

        # Try int
        if str(raw).isdigit():
            return int(raw)

        # Try bool
        if isinstance(raw, str):
            lowered = raw.lower()
            if lowered in ("true", "yes", "on"):
                return True
            if lowered in ("false", "no", "off"):
                return False

        # Default: keep as string
        return str(raw)

    # ============================================================
    # SAVE CONFIG
    # ============================================================
    def save(self, key, value):
        """
        Save one key/value pair as a string into the JSON.
        """
        self._ensure_file_exists()

        config = load_json(self.path, default_data={})

        if value is None:
            # Remove value entirely from config
            config.pop(key, None)
        else:
            config[key] = str(value)

        save_json(self.path, config)
        self.data[key] = self._parse_value(value)

        print(f"[CONFIG] Saved {key} = {value}")

    # ============================================================
    # GETTERS
    # ============================================================
    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.save(key, value)
    
        # Typed getters
    
    # Typed Getters
    def get_int(self, key, default=None):
        val = self.get(key)
        return val if isinstance(val, int) else default

    def get_bool(self, key, default=None):
        val = self.get(key)
        return val if isinstance(val, bool) else default
    
    # ============================================================
    # MESSAGE RESTORATION
    # ============================================================
    async def restore_message_refs(self, core):
        """
        Validate all saved message references (queue messages, status messages, etc).
        If a saved message no longer exists, remove it from config.
        """
        bot = core.discord_bot

        for key in ("queue_message_id"):
            raw_id = self.get(key)

            if not raw_id:
                continue

            try:
                channel_id = int(self.get("text_channel_id") or 0)
                if not channel_id:
                    print(f"[CONFIG] Cannot restore {key}: missing text_channel_id")
                    self.delete(key)
                    continue

                channel = bot.get_channel(channel_id)
                if channel is None:
                    channel = await bot.fetch_channel(channel_id)

                msg = await channel.fetch_message(int(raw_id))

                # If message fetch succeeded
                print(f"[CONFIG] Restored saved message for {key}: {msg.id}")

            except discord.NotFound:
                print(f"[CONFIG] Message ID {raw_id} for '{key}' not found — clearing config")
                self.delete(key)

            except Exception as e:
                print(f"[CONFIG] Failed to restore {key}: {e}")
                self.delete(key)