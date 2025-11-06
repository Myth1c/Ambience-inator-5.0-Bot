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
        
    async def get_bot_status(self) -> dict:
        return {
            "music": {
                "playing": self.is_music_playing,
                "shuffle": self.shuffle_mode,
                "loop": self.loop_mode
            },
            "ambience": {
                "playing": self.is_ambience_playing
            },
            "in_vc": self.in_vc
        },


class PlaybackInfo:
    def __init__(self):
        self.playlist_name = "None"
        self.playlist = None
        self.playlist_current = { "url" : None, "name" : "None"}
        self.ambience_name = "None"
        self.ambience_url = None
        self.music_volume = 100
        self.ambience_volume = 25
        
    async def get_playback_info(self) -> dict:
        return {
            "music": {
                "playlist_name": self.playlist_name,
                "track_name": self.playlist_current["name"],
                "volume": self.music_volume,
            },
            "ambience": {
                "name": self.ambience_name,
                "volume": self.ambience_volume,
            }
        },


botStatus = BotStatus()
playbackInfo = PlaybackInfo()

async def get_playback_state():
    """Return the current playback state in frontend-compatible format."""
    
    _bot_status = botStatus.get_bot_status()
    _playback_info = playbackInfo.get_playback_info()
    
    fullState = {**_bot_status, **_playback_info}
    
    return fullState
