# bot/core.py

import asyncio, discord, os
from discord.ext import commands

from bot import IPCBridge, PlaybackManager, StateManager, ConfigManager, MixedAudio, MixedAudioSource, QueueManager, ContentManager, ControlManager, DisplayManager


class BotCore:
    """
    Central controller for all bot systems.
    """
    def __init__(self):

        # ---------- IPC BRIDGE ----------
        self.ipc = IPCBridge(self)
        
        # ---------- CONFIG MANAGER ----------
        self.botConfig = ConfigManager()

        # ---------- STATE MANAGER ----------
        self.state = StateManager(self)

        # ---------- DISCORD CLIENT ----------
        self.discord_bot = None

        # ---------- AUDIO MANAGERS ----------
        self.mixer = MixedAudio()
        self.audioSource = MixedAudioSource(self.mixer)

        # ---------- QUEUE MANAGER ----------
        self.queue = QueueManager()
        
        # ---------- PLAYBACK MANAGER ----------
        self.playback = PlaybackManager(self)
        
        # ---------- CONTENT MANAGER ----------
        base_dir= os.path.dirname(os.path.dirname(__file__))
        self.content = ContentManager(base_dir)
        
        # ---------- DISPLAY MANAGER ----------
        self.display = DisplayManager(self)

        # ---------- BOT CONTROL MANAGER ----------
        self.control = ControlManager(self)

        # ---------- INTERNAL FLAGS ----------
        self._ready_event_fired = False
        self.ready = False

        # ---------- EVENT LOOP ----------
        self.loop = asyncio.get_event_loop()


    # =====================================================
    # DISCORD BOT SETUP
    # =====================================================
    def create_discord_bot(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.members = True
        intents.guilds = True

        bot = commands.Bot(command_prefix="!", intents=intents)
        self.discord_bot = bot

        bot.core = self

        @bot.event
        async def on_ready():
            await self._on_discord_ready()

        return bot

    async def _on_discord_ready(self):
        if self._ready_event_fired:
            return
        self._ready_event_fired = True

        print(f"[CORE] Discord logged in as {self.discord_bot.user}")

        # Load config IDs
        await self.load_saved_ids()

        # Start IPC
        asyncio.create_task(self.ipc.listen_loop())
        print("[CORE] IPC Bridge started")

        # Allow playback manager to broadcast initial state
        await self.playback.send_state()

        self.ready = True
        print("[CORE] BotCore is fully initialized.")


    # =====================================================
    # CONFIG MANAGEMENT
    # =====================================================
    async def load_saved_ids(self):
        await self.botConfig.load()
        await self.botConfig.restore_message_refs(self)

    def save_id(self, key, value):
        self.botConfig.save(key, value)


    # =====================================================
    # START ENTRY POINT
    # =====================================================
    async def start(self, token: str):
        print("[CORE] Starting bot system initialization...")

        # Build Discord bot
        self.create_discord_bot()

        # Start bot
        await self.discord_bot.start(token)
