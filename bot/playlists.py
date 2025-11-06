# bot/playlists.py

import os, json

from config.json_helper import load_json, save_json

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # /app
PLAYLIST_FILE = os.path.join(BASE_DIR, "data/playlists.json")

def return_playlists():
    playlists = load_json(PLAYLIST_FILE, default_data={})
    
    print(f"[BOT] Fetching playlists: {playlists}")
    return playlists
    
async def save_playlist(data):
    name = data.get("name")
    playlist_data = data.get("data")
    
    # --- Parse playlist_data back into a dict ---
    if isinstance(playlist_data, str):
        try:
            playlist_data = json.loads(playlist_data)
            print(f"[BOT] Parsed playlist data from string for {name}")
        except Exception as e:
            print(f"[BOT] Failed to parse playlist JSON string for '{name}': {e}")
            return 
    
    # -- Validate playlist data --
    if not name or not isinstance(playlist_data, dict):
        print("[BOT] Invalid playlist save request")
        return
    
    # -- Load existing playlists for saving
    playlists = load_json(PLAYLIST_FILE, default_data={})
    playlists[name] = playlist_data
    
    save_json(PLAYLIST_FILE, playlists)
