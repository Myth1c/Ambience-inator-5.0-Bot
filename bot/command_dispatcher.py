# bot/command_dispatcher.py

import asyncio, time

from bot.playback import (
    play_music, skip, previous, toggle_shuffle, toggle_loop, set_volume,
    play_ambience, pause_track, resume_track, join_vc, leave_vc, load_playlist
)
from bot.ambience import return_ambience, save_ambience
from bot.playlists import return_playlists, save_playlist
from bot.state_manager import botStatus, get_playback_state
from bot.control import reboot_discord_bot, start_discord_bot, stop_discord_bot
from bot.instance import botConfig


# ========== MAIN DISPATCHER ==========
async def dispatch_command(data: dict):
    """Route commands from IPC or internal sources to their handlers."""

    command = data.get("command")
    
    # === Build args dynamically from all incoming keys except 'command' ===
    args = {}
    for key, value in data.items():
        if key != "command":
            args[key] = value
    
    print(f"[DISPATCH] Received command: {command}")
    print(f"[DISPATCH] Dispatcher received args: {args}")


    try:
        # ===== Setup / Config ===== #
        if command == "SETUP_SAVE":
            botConfig.save_bot_config(args)
            return success("SETUP_SAVE")

        elif command == "GET_PLAYBACK_STATE":
            state = get_playback_state()
            resp = {
                "type":"state_update", 
                "payload": state, 
                "ts": time.time()
            }
            return resp

        elif command == "GET_PLAYLISTS":
            playlists = return_playlists()
            return success("PLAYLISTS_DATA", {"playlists": playlists})

        elif command == "SAVE_PLAYLIST":
            await save_playlist(args)
            return success("SAVE_PLAYLIST", {"name": args.get("name")})

        elif command == "GET_AMBIENCE":
            ambience = return_ambience()
            return success("AMBIENCE_DATA", {"ambience": ambience})

        elif command == "SAVE_AMBIENCE":
            await save_ambience(args)
            return success("SAVE_AMBIENCE", {"name": "Ambience"})

        # ===== Music Controls ===== #
        elif command == "PLAY_PLAYLIST":
            await load_playlist(args.get("name"))
            await play_music()
            return success("PLAY_PLAYLIST")

        elif command == "NEXT_SONG":
            await skip()
            return success("NEXT_SONG")

        elif command == "PREVIOUS_SONG":
            await previous()
            return success("PREVIOUS_SONG")

        elif command == "SET_SHUFFLE":
            await toggle_shuffle()
            return success("SET_SHUFFLE")

        elif command == "SET_LOOP":
            await toggle_loop()
            return success("SET_LOOP")

        elif command == "SET_VOLUME_MUSIC":
            await set_volume("music", args.get("volume"))
            return success("SET_VOLUME_MUSIC")

        # ===== Ambience Controls ===== #
        elif command == "PLAY_AMBIENCE":
            await play_ambience(args.get("url"), args.get("title"))
            return success("PLAY_AMBIENCE")

        elif command == "SET_VOLUME_AMBIENCE":
            await set_volume("ambience", args.get("volume"))
            return success("SET_VOLUME_AMBIENCE")

        # ===== Pause / Resume ===== #
        elif command == "PAUSE":
            await pause_track(args.get("type"))
            return success("PAUSE")

        elif command == "RESUME":
            await resume_track(args.get("type"))
            return success("RESUME")

        # ===== Voice Control ===== #
        elif command == "JOINVC":
            vc_id = botConfig.voice_channel_id
            if not vc_id:
                return fail("JOINVC", "Voice channel ID missing")
            bot = args.get("bot_instance")
            await join_vc(bot, vc_id)
            return success("JOINEDVC")

        elif command == "LEAVEVC":
            await leave_vc()
            return success("LEFTVC")

        # ===== Bot Lifecycle ===== #
        elif command == "REBOOT":
            print("[CMD] Reboot requested.")
            botStatus.is_running = "booting"
            asyncio.create_task(reboot_discord_bot())
            return success("BOT_STATUS", {"online": botStatus.is_running})

        elif command == "START_BOT":
            print("[CMD] Start requested.")
            botStatus.is_running = "booting"
            asyncio.create_task(start_discord_bot())
            return success("BOT_STATUS", {"online": botStatus.is_running})

        elif command == "STOP_BOT":
            print("[CMD] Stop requested.")
            botStatus.is_running = "offline"
            await stop_discord_bot()
            return success("BOT_STATUS", {"online": botStatus.is_running})

        elif command == "GET_BOT_STATUS":
            return success("BOT_STATUS", {"online": botStatus.is_running})

        # ===== Discord Message Updates ===== #

        # ===== Default ===== #
        else:
            print(f"[DISPATCH] Unknown command: {command}")
            return fail(command, "Unknown command")

    except Exception as e:
        print(f"[DISPATCH] Error while handling {command}: {e}")
        return fail(command, str(e))


# ========== Response Helpers ==========
def success(command, data=None):
    """Return a standard success response."""
    return {"ok": True, "command": command, "data": data or {}}


def fail(command, error):
    """Return a standard error response."""
    return {"ok": False, "command": command, "error": error}
