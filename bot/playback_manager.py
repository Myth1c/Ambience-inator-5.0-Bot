# bot/playback_manager.py

import asyncio, discord, yt_dlp


class PlaybackManager:
    """
    Handles *all* audio playback:
      - joining VC
      - playing / pausing / resuming audio
      - playlist management
      - ambience + music control
      - volume
      - IPC state updates
    """
    def __init__(self, core):
        self.core = core

        self.monitor_task = None                 # For song auto-advance


    # =====================================================================
    # VOICE CONNECTION
    # =====================================================================
    async def join_vc(self, channel_id):
        bot = self.core.discord_bot
        channel_id = int(channel_id)

        try:
            channel = bot.get_channel(channel_id)

            # Retry if cache is cold
            for _ in range(3):
                if channel is None:
                    await asyncio.sleep(1)
                    channel = bot.get_channel(channel_id)
                else:
                    break

            if not isinstance(channel, discord.VoiceChannel):
                raise ValueError("Invalid voice channel ID")

            # Disconnect existing VC
            if self.core.state.voice_client and self.core.state.voice_client.is_connected():
                await self.core.state.voice_client.disconnect(force=True)

            # Connect new VC
            self.core.state.voice_client = await channel.connect()
            self.core.state.in_vc = True

            print(f"[BOT] Connected to VC: {channel.name}")

        except Exception as e:
            print(f"[BOT] Could not join VC: {e}")
            self.core.state.in_vc = False

        await self.send_state()
        await self.core.display.update_queue_display()

    async def leave_vc(self):
        vc = self.core.state.voice_client
        if not vc:
            return

        try:
            print("[BOT] Leaving voice channel...")

            # Stop all audio
            self.core.mixer.stop_music()
            self.core.mixer.stop_ambience()

            await vc.disconnect(force=True)

        except Exception as e:
            print(f"[BOT] Error leaving VC: {e}")

        # Reset state
        self.core.state.reset_voice_state()

        await self.send_state()
        await self.core.display.update_queue_display()


    # =====================================================================
    # PLAYLIST CONTROL
    # =====================================================================
    async def load_playlist(self, name):
        # Pull from ContentManager instead of reading files directly
        playlists = self.core.content.get_playlists()
        if name not in playlists:
            raise ValueError(f"Playlist '{name}' not found")

        entries = playlists[name]
        tracks = self.core.content.playlist_to_tracklist(entries)

        # Fill queue
        self.core.queue.set_tracks(tracks, name)

        # Update state (always a dict for current)
        self.core.state.playlist_name = name
        self.core.state.playlist = tracks
        self.core.state.playlist_current = tracks[0] if tracks else {"url": None, "name": "None"}
        self.core.state.is_music_playing = False
        self.core.state.shuffle_mode = False  # optional, reset

        print(f"[BOT] Playlist loaded: {name} ({len(tracks)} tracks)")
        await self.send_state()
        await self.core.display.update_queue_display()


    # =====================================================================
    # PLAYBACK CONTROLS
    # =====================================================================
    async def skip(self):
        if self.core.queue.next_track():
            await self.play_music()
        else:
            self.core.state.is_music_playing = False
            await self.send_state()
            
        await self.core.display.update_queue_display()

    async def previous(self):
        if self.core.queue.previous_track():
            await self.play_music()
        else:
            await self.send_state()

    async def toggle_shuffle(self):
        if self.core.state.shuffle_mode:
            self.core.queue.unshuffle()
        else:
            self.core.queue.shuffle()

        self.core.state.shuffle_mode = not self.core.state.shuffle_mode
        print(f"[BOT] Shuffle mode: {self.core.state.shuffle_mode}")
        await self.send_state()
        await self.core.display.update_queue_display()

    async def toggle_loop(self):
        mode = self.core.queue.toggle_loop_current()
        self.core.state.loop_mode = (mode == "current track")

        print(f"[BOT] Loop mode: {self.core.state.loop_mode}")
        await self.send_state()
        await self.core.display.update_queue_display()
    
    async def pause(self, track_type: str):
        if track_type == "music":
            self.core.mixer.pause_music()
            self.core.state.is_music_playing = False
        elif track_type == "ambience":
            self.core.mixer.pause_ambience()
            self.core.state.is_ambience_playing = False
        else:
            print(f"[BOT] Unknown track type for pause: {track_type}")
            return
        await self.send_state()

    async def resume(self, track_type: str):
        if track_type == "music":
            self.core.mixer.resume_music()
            self.core.state.is_music_playing = True
        elif track_type == "ambience":
            self.core.mixer.resume_ambience()
            self.core.state.is_ambience_playing = True
        else:
            print(f"[BOT] Unknown track type for resume: {track_type}")
            return

        # If nothing is driving the VC, (re)attach the mixed source
        vc = self.core.state.voice_client
        if vc and not vc.is_playing():
            vc.play(self.core.audioSource)

        await self.send_state()


    # =====================================================================
    # VOLUME
    # =====================================================================
    async def set_volume(self, track_type, volume):
        volume = max(0, min(volume, 100)) / 100

        if track_type == "music":
            self.core.mixer.set_music_volume(volume)
            self.core.state.music_volume = int(volume * 100)

        elif track_type == "ambience":
            self.core.mixer.set_ambience_volume(volume)
            self.core.state.ambience_volume = int(volume * 100)

        print(f"[BOT] {track_type.capitalize()} volume: {int(volume * 100)}%")
        await self.send_state()


    # =====================================================================
    # INITIALIZE PLAYBACK
    # =====================================================================
    async def play_music(self):
        vc = self.core.state.voice_client
        if not vc:
            print("[BOT] VC not connected.")
            return

        track = self.core.queue.get_current()
        if not track:
            print("[BOT] No track loaded.")
            return

        try:
            url = track["url"]
            title = track["name"]

            # Stop existing
            self.core.mixer.stop_music()

            stream_url = await self.get_stream(url)
            if not stream_url:
                print(f"[BOT] Failed to stream: {title}")
                return

            # Start new track
            self.core.mixer.start_music(stream_url)

            self.core.state.playlist_current = track
            self.core.state.is_music_playing = True

            if not vc.is_playing():
                vc.play(self.core.audioSource)

            print(f"[BOT] Now playing: {title}")

        except Exception as e:
            print(f"[BOT] Error playing music: {e}")

        # Start monitor
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()

        self.monitor_task = asyncio.create_task(self._monitor_end())

        await self.send_state()
    
    async def play_ambience(self, url, title):
        vc = self.core.state.voice_client
        if not vc:
            print("[BOT] VC not connected.")
            return

        try:
            self.core.mixer.stop_ambience()

            stream_url = await self.get_stream(url)
            if not stream_url:
                print(f"[BOT] Failed ambience stream: {title}")
                return

            self.core.mixer.start_ambience(stream_url, loop=True)

            self.core.state.ambience_name = title
            self.core.state.ambience_url = url
            self.core.state.is_ambience_playing = True

            if not vc.is_playing():
                vc.play(self.core.audioSource)

        except Exception as e:
            print(f"[BOT] Failed ambience: {e}")

        await self.send_state()


    # =====================================================================
    # STREAM RESOLVER
    # =====================================================================
    async def get_stream(self, url):
        opts = {
            "format": "bestaudio[ext=webm][acodec=opus]/bestaudio/best",
            "quiet": True,
            "noplaylist": True,
            "default_search": "auto",
            "skip_download": True,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get("url")
        except Exception:
            return None


    # =====================================================================
    # SONG MONITOR
    # =====================================================================
    async def _monitor_end(self):
        while True:
            await asyncio.sleep(1)

            proc = self.core.mixer.proc_music
            if proc and proc.poll() is None:
                continue  # still playing
            
            # Once the current song has ended, start the next song by "skipping" the current song since it'd be playing empty audio
            self.skip()
            
            await self.send_state()
            return


    # =====================================================================
    # IPC STATE UPDATES
    # =====================================================================
    async def send_state(self):
        if not self.core.ipc.connected:
            print("[IPC] Not connected, skipping state update.")
            return

        await self.core.ipc.send_state(self.core.state.to_dict())
