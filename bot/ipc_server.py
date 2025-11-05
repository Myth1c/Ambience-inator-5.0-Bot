# bot/ipc_server.py

import asyncio
import aiohttp
import os
from aiohttp import web


# Import your existing functions
from bot.playback import (
    play_music, skip, previous, toggle_shuffle, toggle_loop, set_volume,
    play_ambience, pause_track, resume_track, join_vc, leave_vc, load_playlist
)
from bot.ambience import send_ambience, save_ambience
from bot.playlists import send_playlists, save_playlist
from bot.state_manager import botStatus, get_playback_state, broadcast_state
from bot.control import reboot_discord_bot, start_discord_bot, stop_discord_bot, embed_generator, send_message_to_channel_ID, edit_message
from bot.instance import botConfig

routes = web.RouteTableDef()


Bot_Broadcast_URL = None
_ipc_app = None


@routes.post("/bot_command")
async def handle_bot_command(request):
    data = await request.json()
    command = data.get("command")
    args = data.get("args", {}) or {}
    bot = request.app["bot"]

    print(f"[IPC] Received bot command: {command}")

    try:
        # ===== Display Commands ===== #
        match command:
            case "SETUP_SAVE":
                botConfig.save_bot_config(args)
                return web.json_response({"ok": True})
            case "GET_PLAYBACK_STATE":
                state = await get_playback_state()
                if "state" in state:
                    state = state["state"]
                return web.json_response({
                    "command" : "PLAYBACK_STATE",
                    "state": state
                })
            case "GET_PLAYLISTS":
                return web.json_response({
                    "command" : "PLAYLISTS_DATA",
                    "playlists": await send_playlists()})
            case "SAVE_PLAYLIST":
                await save_playlist(args)
                return web.json_response({"ok": True})
            case "GET_AMBIENCE":
                return web.json_response({
                    "command" : "AMBIENCE_DATA",
                    "ambience": await send_ambience()})
            case "SAVE_AMBIENCE":
                await save_ambience(args)
                return web.json_response({"ok": True})

            # ===== Music Commands ===== #
            case "PLAY_PLAYLIST":
                await load_playlist(args["name"])
                await play_music()
                return await success_response()
            case "NEXT_SONG":
                await skip()
                return await success_response()
            case "PREVIOUS_SONG":
                await previous()
                return await success_response()
            case "SET_SHUFFLE":
                await toggle_shuffle()
                return await success_response()
            case "SET_LOOP":
                await toggle_loop()
                return await success_response()
            case "SET_VOLUME_MUSIC":
                await set_volume("music", args["volume"])
                return await success_response()

            # ===== Ambience Commands ===== #
            case "PLAY_AMBIENCE":
                url = args.get("url")
                title = args.get("title")
                await play_ambience(url, title)
                return await success_response()
            case "SET_VOLUME_AMBIENCE":
                await set_volume("ambience", args["volume"])
                return await success_response()

            # ===== Pause / Resume ===== #
            case "PAUSE":
                await pause_track(args.get("type"))
                return await success_response()
            case "RESUME":
                await resume_track(args.get("type"))
                return await success_response()

            # ===== Voice ===== #
            case "JOINVC":
                vc_id = botConfig.voice_channel_id
                if not vc_id:
                    print(f"[IPC] No voice channel id found in bot config")
                    return {"ok": False, "error": "Voice Channel ID is missing"}
                
                await join_vc(bot, vc_id)
                return await success_response()
            case "LEAVEVC":
                await leave_vc()
                return await success_response()

            # ===== Booting ===== #
            case "REBOOT":
                print("[BOT] Bot Reboot requested.")
                botStatus.is_running = "booting"
                asyncio.create_task(reboot_discord_bot())
                return web.json_response({
                    "command": "BOT_STATUS", 
                    "online": botStatus.is_running 
                })
            case "START_BOT":
                print("[WEB] Start bot requested")
                botStatus.is_running = "booting"
                asyncio.create_task(start_discord_bot())
                return web.json_response({
                    "command": "BOT_STATUS", 
                    "online": botStatus.is_running 
                })
            case "STOP_BOT":
                print("[WEB] Stop bot requested")
                botStatus.is_running = "offline"
                await stop_discord_bot()
                return web.json_response({
                    "command": "BOT_STATUS", 
                    "online": botStatus.is_running 
                })
            case "GET_BOT_STATUS":
                print("[BOT] Bot boot status requested.")
                return web.json_response({
                    "command" : "BOT_STATUS",
                    "online" : botStatus.is_running
                })
            
            # ==== Discord Messages ==== #
            case "UPDATE_QUEUE_MESSAGE":
                print("[BOT] Received send/update queue message command")
                
                title = args.get("title", "Playlist Name")
                description = args.get("description", "" \
                "\n### *Previous Song Name*" \
                "\n# **Current Song Name**" \
                "\n## Next Song Name")
                color = args.get("color", 0x2f3136)
                fields = args.get("fields", [])
                
                embed = embed_generator(title=title, description=description, color=color, fields=fields)
                                
                if botStatus.queue_message_id:
                    print("[BOT] Queue Message found! Editing it instead.")
                    botStatus.queue_message_id = await edit_message(botStatus.queue_message_id, embed=embed)
                
                if botStatus.queue_message_id is None:
                    print("[BOT] No Queue Message found. Creating a new one.")
                    msg = await send_message_to_channel_ID(embed=embed)
                    botStatus.queue_message_id = msg.id
                    botConfig.save_bot_config({"queue_message_id": botStatus.queue_message_id})
                
                
                return web.json_response({"ok": True, "message": "Queue message updated."})
            case "UPDATE_UI_LINK":
                print("[BOT] Received send/update UI Linke command")

                title = args.get("title", "# Ambience-inator")
                description = args.get("description", "" \
                f"\n\n#- [UI Link](<{url}>)")
                color = args.get("color", 0x2f3136)
                fields = args.get("fields", [
                    {
                        "name": "\u200b",
                        "value": "\u200b",
                    },
                    {
                        "name": "\u200b",
                        "value": "\u200b",
                    },
                    {
                        "name": "Bot Status",
                        "value": f"Bot is currently {botStatus.is_running}",
                    }
                ])
                
                embed = embed_generator(title=title, description=description, color=color, fields=fields)
                                
                if botStatus.ngrok_message_id:
                    print("[BOT] UI Link found! Editing it instead.")
                    botStatus.ngrok_message_id = await edit_message(botStatus.ngrok_message_id, embed=embed)
                
                if botStatus.ngrok_message_id is None:
                    print("[BOT] No UI Link found. Creating a new one.")
                    msg = await send_message_to_channel_ID(embed=embed)
                    botStatus.ngrok_message_id = msg.id
                    botConfig.save_bot_config({"ngrok_message_id": botStatus.ngrok_message_id})
                
                
        
                return web.json_response({"ok": True, "message": "UI Link updated."})
            
            
            # ===== Default ===== #
            case _:
                print(f"[BOT] Unknown command: {command}")
                return web.json_response({"ok": False, "error": "Unknown command"})

    except Exception as e:
        print(f"[IPC] Error while handling command {command}: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def start_ipc_server(bot, host="0.0.0.0", port=8765):
    global _ipc_app
    
    app = web.Application()
    app["bot"] = bot
    app.add_routes(routes)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    _ipc_app = app
    print(f"[IPC] Bot IPC server started on {host}:{port}")

async def update_ipc_bot_instance(new_bot):
    """Safely update the bot reference in the running IPC server."""
    global _ipc_app
    if _ipc_app is None or new_bot is None:
        print("[IPC] No active IPC server to update, or invalid bot instance given.")
        return
    
    if _ipc_app["bot"] == new_bot:
        print("[IPC] This bot is already attached to the server")
        return
    
    _ipc_app["bot"] = new_bot
    print("[IPC] Updated IPC server to use new bot instance.")
    

   
# ========== Helper ==========
async def success_response():
    """Gather and broadcast the updated playback state, then return it."""
    try:
        await broadcast_state()
    except Exception as e:
        print(f"[IPC] Error broadcasting state: {e}")
        return web.json_response({"ok": False, "error": str(e)})