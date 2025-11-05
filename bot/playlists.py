# bot/playlists.py

import os

from config.json_helper import load_json, save_json

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # /app
PLAYLIST_FILE = os.path.join(BASE_DIR, "data/playlists.json")

async def send_playlists():
    playlists = load_json(PLAYLIST_FILE, default_data={})
    
    print(f"[IPC] Sending playlists: {playlists}")
    return playlists
    
async def save_playlist(data):
    name = data.get("name")
    playlist_data = data.get("data")
    
    if not name or not isinstance(playlist_data, dict):
        print("[WS] Invalid playlist save request")
        return {"command" : "ERROR", "message": "Invalid playlist data"}
    playlists = load_json(PLAYLIST_FILE, default_data={})
    playlists[name] = playlist_data
    
    save_json(PLAYLIST_FILE, playlists)
    return len(playlists)
