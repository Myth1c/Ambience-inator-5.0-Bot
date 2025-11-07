# bot/state_manager.py

class StateManager:
    """
    Unified runtime state for the bot.
    All other systems (IPC, playback, queue, core) read from here.
    """
    def __init__(self, core=None):
        self.core = core

        # VOICE + PROCESS STATE
        self.voice_client = None
        self.in_vc = False
        self.bot_online = "online"

        # MUSIC STATE
        self.is_music_playing = False
        self.music_volume = 100
        self.playlist_name = "None"
        self.playlist = []
        self.playlist_current = { "url": None, "name": "None" }
        self.shuffle_mode = True
        self.loop_mode = False

        # AMBIENCE STATE
        self.is_ambience_playing = False
        self.ambience_name = "None"
        self.ambience_url = None
        self.ambience_volume = 25


    # =====================================================================
    # HELPERS
    # =====================================================================
    def reset_voice_state(self):
        """Called whenever the bot leaves the voice channel."""
        self.voice_client = None
        self.in_vc = False
        self.is_music_playing = False
        self.is_ambience_playing = False

    def set_playlist(self, name, tracks):
        self.playlist_name = name
        self.playlist = tracks
        self.playlist_current = tracks[0] if tracks else {"url": None, "name": "None"}
        
    def set_ambience(self, name, link):
        self.ambience_name = name
        self.ambience_url = link

    # =====================================================================
    # STATE PACKAGING FOR IPC
    # =====================================================================
    def to_dict(self):
        """Return state in serialized IPC-safe form."""
        return {
            "music": {
                "playlist_name": self.playlist_name,
                "track_name": self.playlist_current.get("name"),
                "playing": self.is_music_playing,
                "volume": self.music_volume,
                "shuffle": self.shuffle_mode,
                "loop": self.loop_mode,
            },
            "ambience": {
                "name": self.ambience_name,
                "playing": self.is_ambience_playing,
                "volume": self.ambience_volume,
            },
            "in_vc": self.in_vc,
            "bot_online": self.bot_online,
        }

    def get_state(self):
        """Convenience wrapper to standardize access."""
        return self.to_dict()

    def __repr__(self):
        return f"<StateManager music={self.is_music_playing} ambience={self.is_ambience_playing} vc={self.in_vc}>"
