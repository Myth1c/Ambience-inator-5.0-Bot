# bot/command_dispatcher.py

import time


class CommandDispatcher:
    """
    Routes incoming IPC commands into BotCore subsystems.
    Usage:
        dispatcher = CommandDispatcher(core)
        await dispatcher.handle(data)
    """
    def __init__(self, core):
        self.core = core


    # =====================================================================
    # MAIN ENTRY POINT
    # =====================================================================
    async def handle(self, data: dict):
        """
        Called by IPCBridge whenever a command message arrives.
        """

        command = data.get("command")
        args = {k: v for k, v in data.items() if k != "command"}

        print(f"[DISPATCH] Command: {command}")
        print(f"[DISPATCH] Args: {args}")

        if not command:
            return self.fail("UNKNOWN", "Missing command")

        try:
            handler = self.COMMANDS.get(command)
            if handler is None:
                return self.fail(command, "Unknown command")

            return await handler(self, args)

        except Exception as e:
            print(f"[DISPATCH] Error in {command}: {e}")
            return self.fail(command, str(e))


    # =====================================================================
    # COMMAND HANDLERS
    # =====================================================================
    # ---------- Playback & Player Control ----------
    async def cmd_play_playlist(self, args):
        name = args.get("name")
        playlist = self.core.content.get_playlist(name)

        if not playlist:
            return self.fail("PLAY_PLAYLIST", "Playlist not found")

        # Load into PlaybackManager
        await self.core.playback.load_playlist(name)
        await self.core.playback.play_music()

        return self.success("PLAY_PLAYLIST")

    async def cmd_next_song(self, args):
        await self.core.playback.skip()
        return self.success("NEXT_SONG")

    async def cmd_previous_song(self, args):
        await self.core.playback.previous()
        return self.success("PREVIOUS_SONG")

    async def cmd_set_shuffle(self, args):
        await self.core.playback.toggle_shuffle()
        return self.success("SET_SHUFFLE")

    async def cmd_set_loop(self, args):
        await self.core.playback.toggle_loop()
        return self.success("SET_LOOP")

    async def cmd_set_volume_music(self, args):
        vol = args.get("volume")
        await self.core.playback.set_volume("music", int(vol))
        return self.success("SET_VOLUME_MUSIC")

    async def cmd_pause(self, args):
        await self.core.playback.pause(args.get("type"))
        return self.success("PAUSE")

    async def cmd_resume(self, args):
        await self.core.playback.resume(args.get("type"))
        return self.success("RESUME")

    async def cmd_play_ambience(self, args):
        url = args.get("url")
        title = args.get("title")
        await self.core.playback.play_ambience(url, title)
        return self.success("PLAY_AMBIENCE")

    async def cmd_set_volume_ambience(self, args):
        vol = args.get("volume")
        await self.core.playback.set_volume("ambience", int(vol))
        return self.success("SET_VOLUME_AMBIENCE")

    # ---------- Voice ----------
    async def cmd_joinvc(self, args):
        vc_id = self.core.botConfig.data.get("voice_channel_id")
        if not vc_id:
            return self.fail("JOINVC", "Voice channel ID missing")

        await self.core.playback.join_vc(vc_id)
        return self.success("JOINEDVC")

    async def cmd_leavevc(self, args):
        await self.core.playback.leave_vc()
        return self.success("LEFTVC")

    # ---------- Data: Playlists / Ambience ----------
    async def cmd_get_playlists(self, args):
        return self.success("PLAYLISTS_DATA", {
            "playlists": self.core.content.get_playlists()
        })

    async def cmd_save_playlist(self, args):
        name = args.get("name")
        data = args.get("data")

        if isinstance(data, str):
            import json
            data = json.loads(data)

        await self.core.content.save_playlist(name, data)
        return self.success("SAVE_PLAYLIST")

    async def cmd_get_ambience(self, args):
        return self.success("AMBIENCE_DATA", {
            "ambience": self.core.content.get_ambience()
        })

    async def cmd_save_ambience(self, args):
        data = args.get("data")

        if isinstance(data, str):
            import json
            data = json.loads(data)

        await self.core.content.save_ambience(data)
        return self.success("SAVE_AMBIENCE")

    # ---------- Config / Setup ----------
    async def cmd_setup_save(self, args):
        self.core.config.save_all(args)
        return self.success("SETUP_SAVE")

    async def cmd_get_playback_state(self, args):
        state = self.core.state.get_state()
        return {
            "type": "state_update",
            "payload": state,
            "ts": time.time()
        }

    # ---------- Bot Lifecycle ----------
    async def cmd_get_bot_status(self, args):
        return self.success("BOT_STATUS", {
            "online": self.core.state.bot_online
        })
    
    async def cmd_start_bot(self, args):
        await self.core.control.start_discord_bot()
        return self.success("BOT_STATUS", {
            "online": self.core.state.bot_online
        })
        
    async def cmd_stop_bot(self, args):
        await self.core.control.stop_discord_bot()
        return self.success("BOT_STATUS", {
            "online": self.core.state.bot_online
        })
        
    async def cmd_reboot_bot(self, args):
        await self.core.control.reboot_discord_bot()
        return self.success("BOT_STATUS", {
            "online": self.core.state.bot_online
        })

    # =====================================================================
    # COMMAND TABLE
    # =====================================================================
    COMMANDS = {
        "SETUP_SAVE":             cmd_setup_save,               
        "GET_PLAYBACK_STATE":     cmd_get_playback_state,       

        "PLAY_PLAYLIST":          cmd_play_playlist,            # Online only command
        "NEXT_SONG":              cmd_next_song,                # Online only command
        "PREVIOUS_SONG":          cmd_previous_song,            # Online only command
        "SET_SHUFFLE":            cmd_set_shuffle,              # Online only command
        "SET_LOOP":               cmd_set_loop,                 # Online only command
        "SET_VOLUME_MUSIC":       cmd_set_volume_music,         # Online only command

        "PLAY_AMBIENCE":          cmd_play_ambience,            # Online only command
        "SET_VOLUME_AMBIENCE":    cmd_set_volume_ambience,      # Online only command

        "PAUSE":                  cmd_pause,                    # Online only command
        "RESUME":                 cmd_resume,                   # Online only command

        "JOINVC":                 cmd_joinvc,                   # Online only command
        "LEAVEVC":                cmd_leavevc,                  # Online only command

        "GET_PLAYLISTS":          cmd_get_playlists,
        "SAVE_PLAYLIST":          cmd_save_playlist,

        "GET_AMBIENCE":           cmd_get_ambience,
        "SAVE_AMBIENCE":          cmd_save_ambience,

        "GET_BOT_STATUS":         cmd_get_bot_status,
        
        "START_BOT":              cmd_start_bot,                
        "STOP_BOT":               cmd_stop_bot,                 # Online only command
        "REBOOT_BOT":             cmd_reboot_bot,               # Online only command
    }


    # =====================================================================
    # RESPONSE HELPERS
    # =====================================================================
    def success(self, cmd, data=None):
        return {"ok": True, "command": cmd, "data": data or {}}

    def fail(self, cmd, error):
        return {"ok": False, "command": cmd, "error": error}
