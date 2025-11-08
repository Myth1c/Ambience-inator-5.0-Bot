# bot/queue_manager.py

import random

class QueueManager:
    """
    Queue/playlist logic.
    """
    def __init__(self):
        self.playlist_name = "None"
        self.tracks = []          # list of {"url": ..., "name": ...}
        self.current_index = 0

        # History stack so "previous" works as expected
        self.previous_stack = []

        # Looping
        self.loop_current = False   # loop current track
        self.loop_playlist = True   # loop playlist end→start

        # Shuffle
        self._original_order = []   # backup before shuffle


    # =====================================================================
    # BASIC SETUP
    # =====================================================================
    def set_tracks(self, track_list, playlist_name="None", shuffle=True):
        """Initialize queue with new tracks."""
        self.playlist_name = playlist_name
        self.tracks = list(track_list)
        self._original_order = list(track_list)
        self.previous_stack.clear()

        # Reset index and guard
        self.current_index = 0
        if len(self.tracks) == 0:
            self.current_index = 0
        else:
            self.current_index = min(self.current_index, len(self.tracks) - 1)
            
        if shuffle:
            self.shuffle()

    def get_current(self):
        """Return current track dict or None."""
        if not self.tracks:
            return None
        
        if self.current_index >= len(self.tracks):
            self.current_index = len(self.tracks) - 1
        
    
        return self.tracks[self.current_index]


    # =====================================================================
    # SHUFFLE / UNSHUFFLE
    # =====================================================================
    def shuffle(self):
        """Shuffle all tracks EXCEPT current track."""
        if len(self.tracks) <= 1:
            return

        current = self.tracks[self.current_index]

        remaining = [
            t for i, t in enumerate(self.tracks)
            if i != self.current_index
        ]

        random.shuffle(remaining)

        self.tracks = [current] + remaining

    def unshuffle(self):
        """Restore original list order while keeping current track index aligned."""
        if not self._original_order:
            return

        current = self.get_current()

        self.tracks = list(self._original_order)

        # Move current index to match track
        for i, t in enumerate(self.tracks):
            if t["url"] == current["url"]:
                self.current_index = i
                break
    
    def is_shuffled(self):
        return self.tracks != self._original_order

    # =====================================================================
    # LOOP CONTROL
    # =====================================================================
    def toggle_loop_current(self):
        """Toggle looping a single track."""
        self.loop_current = not self.loop_current
        self.loop_playlist = not self.loop_current

        return "current track" if self.loop_current else "playlist"


    # =====================================================================
    # TRACK NAVIGATION
    # =====================================================================
    def next_track(self):
        """Advance to next track and return it."""
        if not self.tracks:
            return None

        # loop current track
        if self.loop_current:
            return self.get_current()

        # push to history
        self.previous_stack.append(self.current_index)
        self.current_index += 1

        # end of playlist
        if self.current_index >= len(self.tracks):
            if self.loop_playlist:
                self.current_index = 0
            else:
                self.current_index = len(self.tracks) - 1

        return self.get_current()

    def previous_track(self):
        """Back up to the last track in the history stack."""
        if not self.previous_stack:
            return None

        self.current_index = self.previous_stack.pop()
        return self.get_current()

    def is_empty(self):
        return not self.tracks
    
    
    # =====================================================================
    # QUEUE EXPORT
    # =====================================================================
    def export(self):
        """Return a simplified dict for external inspection."""
        return {
            "playlist_name": self.playlist_name,
            "tracks": self.tracks,
            "current_index": self.current_index,
            "previous_stack": list(self.previous_stack),
            "loop_current": self.loop_current,
            "shuffle_mode": self.is_shuffled(),
        }
