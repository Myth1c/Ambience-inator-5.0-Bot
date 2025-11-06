# bot/ambience.py

import os, json

from config.json_helper import load_json, save_json

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # /app
AMBIENCE_FILE = os.path.join(BASE_DIR, "data/ambience.json")

def return_ambience():
    ambience_data = load_json(AMBIENCE_FILE, default_data={})
    
    return ambience_data

async def save_ambience(data):
    ambience = data.get("data")
    
    # --- Parse ambience data back into a dict ---
    if isinstance(ambience, str):
        try:
            playlist_data = json.loads(playlist_data)
            print(f"[BOT] Parsed playlist data from string for 'Ambience'")
        except Exception as e:
            print(f"[BOT] Failed to parse playlist JSON string for 'Ambience': {e}")
        return 
        
    # --- Validate ambience data ---
    if not isinstance(ambience, dict):
        print("[BOT] Invalid ambience save request")
        return 
    # --- Save ambience data ---
    save_json(AMBIENCE_FILE, ambience)
    print(f"[BOT] Ambience saved with {len(ambience)} entries")

