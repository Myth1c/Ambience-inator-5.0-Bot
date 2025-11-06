# bot/playback.py

import asyncio, discord, yt_dlp

from pathlib import Path
from bot.state_manager import botStatus, playbackInfo, get_playback_state
from bot.queue import MusicQueue
from bot.audiomixer import audioMixer, audioSource
from config.json_helper import load_json
from bot.instance import _ipc_bridge

music_queue = MusicQueue()
song_monitor_task = None

async def join_vc(bot, channel_id):
    from bot.instance import get_bot_instance # Lazy import to prevent cyclical looping
    try:
        bot = get_bot_instance()
        channel_id = int(channel_id)
        channel = bot.get_channel(channel_id)

        # Retry up to 3 times if channel isn't cached yet
        for _ in range(3):
            if channel is None:
                print("[BOT] Channel not found in cache, retrying...")
                await asyncio.sleep(1)
                channel = bot.get_channel(channel_id)
            else:
                break

        if not channel or not isinstance(channel, discord.VoiceChannel):
            raise ValueError("Invalid voice channel ID")

        # Disconnect safely first
        if botStatus.voice_client and botStatus.voice_client.is_connected():
            await botStatus.voice_client.disconnect(force=True)

        botStatus.voice_client = await channel.connect()
        botStatus.in_vc = True
        print(f"[BOT] Connected to {channel.name}")

    except (discord.ClientException, asyncio.TimeoutError) as e:
        print(f"[BOT] Discord error joining VC: {e}")
        botStatus.in_vc = False

    except Exception as e:
        print(f"[BOT] Failed to join VC: {e}")
        botStatus.in_vc = False
        
        
    await _ipc_bridge.send_state(get_playback_state())
    
async def leave_vc():
    """Disconnect from the voice channel and stop all playback."""
    if botStatus.voice_client:
        try:
            print("[BOT] Leaving voice channel...")

            # Stop playback before disconnecting
            if audioMixer.proc_music:
                audioMixer.stop_music()
                print("[BOT] Stopped music playback")

            if audioMixer.proc_amb:
                audioMixer.stop_ambience()
                print("[BOT] Stopped ambience playback")

            await botStatus.voice_client.disconnect(force=True)

        except Exception as e:
            print(f"[BOT] Error while leaving VC: {e}")

        finally:
            botStatus.voice_client.stop()
            botStatus.voice_client = None
            botStatus.in_vc = False
            botStatus.is_music_playing = False
            botStatus.is_ambience_playing = False

            print("[BOT] VC disconnected successfully.")
        
    await _ipc_bridge.send_state(get_playback_state())
    
async def skip():
    next_track = music_queue.next_track()
    if next_track:
        await play_music()
    else:
        print("[BOT] End of playlist")
         
async def previous():
    prev_track = music_queue.previous_track()
    if prev_track:
        await play_music()
        
async def toggle_shuffle():
    if botStatus.shuffle_mode:
        music_queue.unshuffle()
    else:
        music_queue.shuffle()
        
    botStatus.shuffle_mode = not botStatus.shuffle_mode
    print(f"[BOT] Shuffle Mode: {botStatus.shuffle_mode}")
        
    await _ipc_bridge.send_state(get_playback_state())
    
async def toggle_loop():
    mode = music_queue.toggle_loop_current()
    botStatus.loop_mode = (mode == "current track")
    print(f"[BOT] Loop mode: {music_queue.loop_current}")
        
    await _ipc_bridge.send_state(get_playback_state())

async def load_playlist(name: str, file: str = "playlists.json"):
    playlists = load_json(Path("data") / file, default_data={})
    
    if not playlists:
        raise FileNotFoundError("No playlists found or file missing")
    
    if name not in playlists:
        raise ValueError(f"Playlist '{name}' not found")
    
    entries = playlists[name]
    track_list = [{"url": url, "name" : title} for url, title in entries.items()]
    
    # Fill queue and state
    music_queue.set_tracks(track_list, name)
    playbackInfo.playlist_name = name
    playbackInfo.playlist = track_list
    playbackInfo.playlist_current = track_list[0] if track_list else {"url" : None, "name" : "None"}
    botStatus.is_music_playing = False
    
    print(f"[BOT] Loaded playlist: {name} ({len(track_list)} tracks)")
        
    await _ipc_bridge.send_state(get_playback_state())

async def set_volume(track_type: str, volume: int):
    
    volume = max(0, min(volume, 100)) / 100
    
    if track_type == "music":
        audioMixer.set_music_volume(volume)
        playbackInfo.music_volume = int(volume * 100)
        print(f"[BOT] Music volume set to {int(volume * 100)}%")
        
    elif track_type == "ambience":
        audioMixer.set_ambience_volume(volume)
        playbackInfo.ambience_volume = int(volume * 100)
        print(f"[BOT] Ambience volume set to {int(volume * 100)}%")
        
    else:
        print(f"[BOT] Unknown track type '{track_type}'")
        
        
    await _ipc_bridge.send_state(get_playback_state())
        
async def pause_track(track_type: str):
    if track_type == "music":
        audioMixer.pause_music()
        botStatus.is_music_playing = False
        print("[BOT] Music paused")

    elif track_type == "ambience":
        audioMixer.pause_ambience()
        botStatus.is_ambience_playing = False
        print("[BOT] Ambience paused")

    else:
        print(f"[BOT] Unknown track type '{track_type}'")
        
        
    await _ipc_bridge.send_state(get_playback_state())

async def resume_track(track_type: str):
    if track_type == "music":
        audioMixer.resume_music()
        botStatus.is_music_playing = True
        print("[BOT] Music resumed")

    elif track_type == "ambience":
        audioMixer.resume_ambience()
        botStatus.is_ambience_playing = True
        print("[BOT] Ambience resumed")

    else:
        print(f"[BOT] Unknown track type '{track_type}'")
        
        
    await _ipc_bridge.send_state(get_playback_state())
        
async def play_ambience(url: str, title: str):
    if not botStatus.voice_client:
        print(f"[BOT] No voice client, cannot play ambience")
        return
    
    try:
        # Stop existing ambience first
        audioMixer.stop_ambience()
        
        stream_url = await get_youtube_stream(url)
        if not stream_url:
            print(f"[BOT] Failed to resolve stream for {title}")

        # Start new ambience loop
        audioMixer.start_ambience(stream_url, loop=True)
        playbackInfo.ambience_name = title
        playbackInfo.ambience_url = url
        botStatus.is_ambience_playing = True
        
        # If not already streaming, start the mixed audio output
        if not botStatus.voice_client.is_playing():
            print("[BOT] Starting mixed audio source stream...")
            botStatus.voice_client.play(audioSource)
        else:
            print("[BOT] Mixer already playing, ambience mixed in")
            
        print(f"[BOT] Ambience started: {title}")
        
    except Exception as e:
        print(f"[BOT] Failed to play ambience: {e}")
        
        
    await _ipc_bridge.send_state(get_playback_state())
               
async def play_music():
    global song_monitor_task
    
    if not botStatus.voice_client:
        print("[BOT] No voice client connected — cannot play music")
        return

    if not playbackInfo.playlist or not music_queue.tracks:
        print("[BOT] No playlist loaded — call load_playlist() first")
        return

    try:
        # Grab the current track
        current_track = music_queue.get_current()
        if not current_track:
            print("[BOT] No current track to play")
            return

        url = current_track["url"]
        title = current_track["name"]
        
        stream_url = await get_youtube_stream(url)
        if not stream_url:
            print(f"[BOT] Failed to resolve stream for {title}")

        # Start playback in mixer
        audioMixer.start_music(stream_url)
        playbackInfo.playlist_current = {"url": url, "name": title}
        botStatus.is_music_playing = True

        # If not already streaming, attach mixer to voice client
        if not botStatus.voice_client.is_playing():
            print("[BOT] Starting mixed audio stream...")
            botStatus.voice_client.play(audioSource)
        else:
            print("[BOT] Mixer already running — music track mixed in")

        print(f"[BOT] Now playing: {title}")

    except Exception as e:
        print(f"[BOT] Failed to play music: {e}")
        
    # start watcher task
    if song_monitor_task and not song_monitor_task.done():
        song_monitor_task.cancel()
    song_monitor_task = asyncio.create_task(monitor_song_end())
            
    await _ipc_bridge.send_state(get_playback_state())
        
        
        
async def get_youtube_stream(url: str) -> str:
    
    ydl_opts = {
        "format": "bestaudio[ext=webm][acodec=opus]/bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "default_search": "auto",
        "source_address": "0.0.0.0",
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info.get("url")
            
            return stream_url
    except Exception as e:
        print(f"[YTDLP] Error extracting audio: {e}")
        return None

async def monitor_song_end():
    """Watch the current ffmpeg music process and auto-advance when it finishes."""
    
    # Lazy imports to prevent cyclical imports
    
    while True:
        await asyncio.sleep(1)
        proc = audioMixer.proc_music
        if not proc:
            return  # nothing playing

        if proc.poll() is not None:
            print("[BOT] Track ended — advancing to next.")
            track = music_queue.next_track()

            if track:
                await play_music()
                botStatus.is_music_playing = True
            else:
                botStatus.is_music_playing = False
                print("[BOT] End of playlist reached.")

            return
    
    
    
    
    
    
    