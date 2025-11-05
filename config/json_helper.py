# config.py

import json
import os

def load_json(path, default_data=None):
    if not os.path.exists(path):
        if default_data is None:
            with open(path, "w") as f:
                json.dump(default_data, f, indent=4)
        return default_data or {}
    
    
    with open(path, "r") as f:
        return json.load(f)
    
    
def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)
