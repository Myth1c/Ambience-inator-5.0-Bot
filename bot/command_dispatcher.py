# bot/command_dispatcher.py

import asyncio

from bot.playback import (
    play_music, skip, previous, toggle_shuffle, toggle_loop, set_volume,
    play_ambience, pause_track, resume_track, join_vc, leave_vc, load_playlist
)
from bot.ambience import send_ambience, save_ambience
from bot.playlists import send_playlists, save_playlist
from bot.state_manager import botStatus, get_playback_state
from bot.control import reboot_discord_bot, start_discord_bot, stop_discord_bot, embed_generator, send_message_to_channel_ID, edit_message
from bot.instance import botConfig


# ========== MAIN DISPATCHER ==========
async def dispatch_command(data: dict):
    """Route commands from IPC or internal sources to their handlers."""

    command = data.get("command")
    args = data.get("args", {}) or {}

    print(f"[DISPATCH] Received command: {command}")

    try:
        # ===== Setup / Config ===== #
        if command == "SETUP_SAVE":
            botConfig.save_bot_config(args)
            return success("SETUP_SAVE")

        elif command == "GET_PLAYBACK_STATE":
            state = await get_playback_state()
            return success("PLAYBACK_STATE", {"state": state})

        elif command == "GET_PLAYLISTS":
            playlists = await send_playlists()
            return success("PLAYLISTS_DATA", {"playlists": playlists})

        elif command == "SAVE_PLAYLIST":
            await save_playlist(args)
            return success("SAVE_PLAYLIST", {"name": args.get("name")})

        elif command == "GET_AMBIENCE":
            ambience = await send_ambience()
            return success("AMBIENCE_DATA", {"ambience": ambience})

        elif command == "SAVE_AMBIENCE":
            await save_ambience(args)
            return success("SAVE_AMBIENCE", {"name": "Ambience"})

        # ===== Music Controls ===== #
        elif command == "PLAY_PLAYLIST":
            await load_playlist(args.get("name"))
            await play_music()
            return await state_response("PLAY_PLAYLIST")

        elif command == "NEXT_SONG":
            await skip()
            return await state_response("NEXT_SONG")

        elif command == "PREVIOUS_SONG":
            await previous()
            return await state_response("PREVIOUS_SONG")

        elif command == "SET_SHUFFLE":
            await toggle_shuffle()
            return await state_response("SET_SHUFFLE")

        elif command == "SET_LOOP":
            await toggle_loop()
            return await state_response("SET_LOOP")

        elif command == "SET_VOLUME_MUSIC":
            await set_volume("music", args.get("volume"))
            return await state_response("SET_VOLUME_MUSIC")

        # ===== Ambience Controls ===== #
        elif command == "PLAY_AMBIENCE":
            await play_ambience(args.get("url"), args.get("title"))
            return await state_response("PLAY_AMBIENCE")

        elif command == "SET_VOLUME_AMBIENCE":
            await set_volume("ambience", args.get("volume"))
            return await state_response("SET_VOLUME_AMBIENCE")

        # ===== Pause / Resume ===== #
        elif command == "PAUSE":
            await pause_track(args.get("type"))
            return await state_response("PAUSE")

        elif command == "RESUME":
            await resume_track(args.get("type"))
            return await state_response("RESUME")

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
        elif command == "UPDATE_QUEUE_MESSAGE":
            return await handle_queue_message_update(args)

        elif command == "UPDATE_UI_LINK":
            return await handle_ui_link_update(args)

        # ===== Default ===== #
        else:
            print(f"[DISPATCH] Unknown command: {command}")
            return fail(command, "Unknown command")

    except Exception as e:
        print(f"[DISPATCH] Error while handling {command}: {e}")
        return fail(command, str(e))


# ========== Helper Handlers ==========
async def handle_queue_message_update(args):
    """Update or create the queue message embed."""
    title = args.get("title", "Playlist Name")
    description = args.get("description", "\n# **Current Song Name**")
    color = args.get("color", 0x2f3136)
    fields = args.get("fields", [])
    embed = embed_generator(title=title, description=description, color=color, fields=fields)

    if botStatus.queue_message_id:
        print("[CMD] Editing existing queue message.")
        botStatus.queue_message_id = await edit_message(botStatus.queue_message_id, embed=embed)
    else:
        print("[CMD] Creating new queue message.")
        msg = await send_message_to_channel_ID(embed=embed)
        botStatus.queue_message_id = msg.id
        botConfig.save_bot_config({"queue_message_id": botStatus.queue_message_id})

    return success("UPDATE_QUEUE_MESSAGE")


async def handle_ui_link_update(args):
    """Update or create the UI link embed."""
    title = args.get("title", "# Ambience-inator")
    description = args.get("description", "# [UI Link](<https://myth1c.github.io/Ambience-inator>)")
    color = args.get("color", 0x2f3136)
    fields = args.get("fields", [
        {"name": "Bot Status", "value": f"Bot is currently {botStatus.is_running}"}
    ])
    embed = embed_generator(title=title, description=description, color=color, fields=fields)

    if botStatus.ngrok_message_id:
        print("[CMD] Editing existing UI Link message.")
        botStatus.ngrok_message_id = await edit_message(botStatus.ngrok_message_id, embed=embed)
    else:
        print("[CMD] Creating new UI Link message.")
        msg = await send_message_to_channel_ID(embed=embed)
        botStatus.ngrok_message_id = msg.id
        botConfig.save_bot_config({"ngrok_message_id": botStatus.ngrok_message_id})

    return success("UPDATE_UI_LINK")


# ========== Response Helpers ==========
def success(command, data=None):
    """Return a standard success response."""
    return {"ok": True, "command": command, "data": data or {}}


def fail(command, error):
    """Return a standard error response."""
    return {"ok": False, "command": command, "error": error}


async def state_response(command):
    """Return success and include latest playback state."""
    state = await get_playback_state()
    return {"ok": True, "command": command, "state": state}