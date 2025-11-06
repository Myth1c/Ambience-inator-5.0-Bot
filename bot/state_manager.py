# bot/state.py

import os

AUTH_KEY = os.getenv("AUTH_KEY")
WEB_URL = os.getenv("WEB_URL")

class BotStatus:
    def __init__(self):
        self.voice_client = None
        self.is_music_playing = False
        self.is_ambience_playing = False
        self.shuffle_mode = True
        self.loop_mode = False
        self.in_vc = False
        self.is_running = "offline"
        self.queue_message_id = None
        self.ngrok_message_id = None


class PlaybackInfo:
    def __init__(self):
        self.playlist_name = "None"
        self.playlist = None
        self.playlist_current = { "url" : None, "name" : "None"}
        self.ambience_name = "None"
        self.ambience_url = None
        self.music_volume = 100
        self.ambience_volume = 25


botStatus = BotStatus()
playbackInfo = PlaybackInfo()

async def get_playback_state():
    """Return the current playback state in frontend-compatible format."""
    payload = {
        "music": {
            "playlist_name": playbackInfo.playlist_name,
            "track_name": playbackInfo.playlist_current["name"],
            "playing": botStatus.is_music_playing,
            "volume": playbackInfo.music_volume,
            "shuffle": botStatus.shuffle_mode,
            "loop": botStatus.loop_mode,
        },
        "ambience": {
            "name": playbackInfo.ambience_name,
            "playing": botStatus.is_ambience_playing,
            "volume": playbackInfo.ambience_volume,
        },
        "in_vc": botStatus.in_vc,
        "bot_online": botStatus.is_running
    }
    
    print(f"[IPC] Returning bot state as {payload}")
    
    return payload
