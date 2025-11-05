# bot/ambience.py

import os

from config.json_helper import load_json, save_json

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # /app
AMBIENCE_FILE = os.path.join(BASE_DIR, "data/ambience.json")

async def send_ambience():
    ambience_data = load_json(AMBIENCE_FILE, default_data={})
    
    return ambience_data

async def save_ambience(data):
    ambience = data.get("data")
    if not isinstance(ambience, dict):
        return {"command" : "ERROR", "message": "Invalid ambience data"}
    
    save_json(AMBIENCE_FILE, ambience)
    return len(ambience)
