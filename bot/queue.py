# bot/queue.py
import random

class MusicQueue:
    def __init__(self):
        self.playlist_name = "None"
        self.tracks = []          # full playlist as a list of {"url", "name"}
        self.current_index = 0
        self.previous_stack = []
        self.loop_current = False  # whether to loop the same track
        self.loop_playlist = True  # whether to restart at the beginning
        self._original_order = []  # to restore after shuffle

    def set_tracks(self, track_list):
        self.tracks = track_list
        self._original_order = list(track_list)  # store for unshuffle
        self.current_index = 0
        self.previous_stack.clear()

    def get_current(self):
        if not self.tracks:
            return None
        return self.tracks[self.current_index]

    def shuffle(self):
        if not self.tracks or len(self.tracks) <= 1:
            return

        current = self.tracks[self.current_index]
        remaining = [t for i, t in enumerate(self.tracks) if i != self.current_index]
        random.shuffle(remaining)
        self.tracks = [current] + remaining
        print("[BOT] Playlist shuffled")

    def unshuffle(self):
        if not self._original_order:
            return
        current_track = self.get_current()
        self.tracks = list(self._original_order)
        # Move current index to match current track position
        for i, t in enumerate(self.tracks):
            if t["url"] == current_track["url"]:
                self.current_index = i
                break
        print("[BOT] Playlist order restored")

    def next_track(self):
        if not self.tracks:
            return None

        if self.loop_current:
            return self.get_current()

        self.previous_stack.append(self.current_index)
        self.current_index += 1

        # If we reached end of list
        if self.current_index >= len(self.tracks):
            if self.loop_playlist:
                self.current_index = 0
            else:
                self.current_index = len(self.tracks) - 1  # stop at end

        return self.get_current()

    def previous_track(self):
        if not self.previous_stack:
            return None
        self.current_index = self.previous_stack.pop()
        return self.get_current()

    def toggle_loop_current(self):
        self.loop_current = not self.loop_current
        self.loop_playlist = not self.loop_current
        mode = "current track" if self.loop_current else "playlist"
        print(f"[BOT] Loop mode set to {mode}")
        return mode
    
    def get_queue(self) -> dict:
        return {
            "playlist_name": self.playlist_name,
            "tracks": self.tracks,
            "current_index" : self.current_index,
            "previous_stack" : self.previous_stack,
            "loop_current" : self.loop_current,
            "shuffle_mode" : (self.tracks != self._original_order)
        }