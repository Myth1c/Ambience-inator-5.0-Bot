# bot/content_manager.py

import os

from config import load_json, save_json


class ContentManager:
    """
    Loads and saves user playlists + ambience libraries.
    This is the persistent library separate from the active queue.
    """

    def __init__(self, base_dir):
        self.playlist_file = os.path.join(base_dir, "data/playlists.json")
        self.ambience_file = os.path.join(base_dir, "data/ambience.json")

        # Auto-create empty files if missing
        self._ensure_file(self.playlist_file)
        self._ensure_file(self.ambience_file)


    # =====================================================================
    # INTERNAL HELPERS
    # =====================================================================
    def _ensure_file(self, path):
        """Create file if missing."""
        if not os.path.exists(path):
            save_json(path, {})
            print(f"[CONTENT] Created missing file: {path}")

    def playlist_to_tracklist(self, playlist_dict):
        return [{"url": u, "name": t} for u, t in playlist_dict.items()]

    # =====================================================================
    # PLAYLIST ACCESS
    # =====================================================================
    def get_playlists(self):
        """Return dict: {playlistName: {url: title, ...}}"""
        playlists = load_json(self.playlist_file, default_data={})
        return playlists

    def get_playlist(self, name):
        """Return a single playlist dict or None."""
        playlists = self.get_playlists()
        return playlists.get(name)

    async def save_playlist(self, name, playlist_data):
        """
        Save a playlist (dict of url → title).
        """
        playlists = load_json(self.playlist_file, default_data={})
        playlists[name] = playlist_data
        save_json(self.playlist_file, playlists)

        print(f"[CONTENT] Saved playlist '{name}' ({len(playlist_data)} tracks)")


    # =====================================================================
    # AMBIENCE ACCESS
    # =====================================================================
    def get_ambience(self):
        """Return ambience dict."""
        return load_json(self.ambience_file, default_data={})

    async def save_ambience(self, ambience_dict):
        """Save ambience (dict of ambienceName → url)."""
        if not isinstance(ambience_dict, dict):
            print("[CONTENT] Invalid ambience save request")
            return

        save_json(self.ambience_file, ambience_dict)
        print(f"[CONTENT] Saved ambience list ({len(ambience_dict)} entries)")        
