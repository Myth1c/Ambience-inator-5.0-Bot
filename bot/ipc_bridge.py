# bot/ipc_bridge.py

import os, json, asyncio, aiohttp, time


WS_URL = os.getenv("WEB_URL", "").replace("https", "wss") + "/ipc"
AUTH_KEY = os.getenv("AUTH_KEY")


class IPCBridge:
    """
    Handles WebSocket communication between the bot and the Web Dashboard.
    Powered by aiohttp, lifecycle controlled by BotCore.
    """
    def __init__(self, core):
        from bot import CommandDispatcher # Lazy import to handle this 1 specific circular import
        
        self.core = core

        self.session: aiohttp.ClientSession | None = None
        self.ws: aiohttp.ClientWebSocketResponse | None = None

        self.connected = False
        self._closing = False

        self.heartbeat_task = None
        
        self.dispatcher = CommandDispatcher(core)


    # ==========================================================
    # CONNECTION + LISTEN LOOP
    # ==========================================================
    async def listen_loop(self):
        """Maintains a persistent WS connection, auto-reconnects on errors."""

        while not self._closing:
            try:
                await self._connect()

                async for msg in self.ws:
                    await self._handle_message_frame(msg)

            except Exception as e:
                print(f"[IPC] Connection/loop error: {e}")

            # force cleanup
            await self._cleanup_ws()

            # retry after delay
            print("[IPC] Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

    async def _connect(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

        print(f"[IPC] Connecting to {WS_URL}...")
        self.ws = await self.session.ws_connect(WS_URL, heartbeat=30)
        self.connected = True

        print("[IPC] Connected.")

        # Send hello packet
        await self.ws.send_json({
            "type": "bot_hello",
            "auth": AUTH_KEY,
            "ts": time.time()
        })

        # Start heartbeat if not running
        if not self.heartbeat_task or self.heartbeat_task.done():
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _cleanup_ws(self):
        """Close sockets safely after disconnect."""
        self.connected = False

        try:
            if self.ws is not None:
                await self.ws.close()
        except:
            pass
        self.ws = None


    # ==========================================================
    # MESSAGE HANDLING
    # ==========================================================
    async def _handle_message_frame(self, msg):
        """Dispatch WS frames from aiohttp."""

        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)
            except json.JSONDecodeError:
                print("[IPC] Invalid JSON:", msg.data)
                return

            msg_type = data.get("type")
            cmd = data.get("command")
            
            if not self.core.ready and cmd not in (
                "SETUP_SAVE", "GET_PLAYBACK_STATE", "GET_PLAYLISTS", "SAVE_PLAYLISTS",
                "GET_AMBIENCE", "SAVE_AMBIENCE", "GET_BOT_STATUS", "START_BOT"
                ):
                await self.safe_send({
                    "ok": False,
                    "command": data.get("command"),
                    "error": "BOT_NOT_READY",
                    "ts": time.time()
                })
                print("[IPC] Command rejected: Bot is not ready")
                return

            # -----------------------------
            # Built-in message types
            # -----------------------------
            if msg_type == "server_ack":
                print("[IPC] Server acknowledged connection.")
                return

            elif msg_type == "broadcast":
                print("[IPC] Broadcast from server:", data)
                return

            elif msg_type == "heartbeat_check":
                await self.safe_send({"type": "heartbeat_ack", "ts": time.time()})
                return

            # -----------------------------
            # Commands
            # -----------------------------
            if cmd:
                print(f"[IPC] Received command: {cmd}")
                result = await self.dispatcher.handle(data)
                await self.safe_send(result)
                return

            print("[IPC] Ignoring unrecognized message:", data)

        elif msg.type == aiohttp.WSMsgType.CLOSED:
            print("[IPC] WS closed.")
            self.connected = False

        elif msg.type == aiohttp.WSMsgType.ERROR:
            print("[IPC] WS error:", msg)
            self.connected = False


    # ==========================================================
    # HEARTBEAT / STATE PUSH
    # ==========================================================
    async def _heartbeat_loop(self, interval=60):
        """Pushes full state to dashboard every 60s."""
        print("[IPC] Heartbeat started.")

        while not self._closing:
            if self.connected:
                try:
                    await self.send_state()
                except Exception as e:
                    print("[IPC] Heartbeat failed:", e)
                    self.connected = False

            await asyncio.sleep(interval)

        print("[IPC] Heartbeat stopped.")

    async def send_state(self):
        """Send full bot state from StateManager."""

        state_payload = self.core.state.get_state()

        await self.safe_send({
            "type": "state_update",
            "payload": state_payload,
            "ts": time.time()
        })


    # ==========================================================
    # SAFE SEND METHODS
    # ==========================================================
    async def safe_send(self, payload: dict):
        """Send JSON if connected."""

        if not self.connected or self.ws is None:
            print("[IPC] send skipped - not connected")
            return False

        try:
            await self.ws.send_json(payload)
            return True
        except Exception as e:
            print("[IPC] send error:", e)
            self.connected = False
            return False


    # ==========================================================
    # SHUTDOWN
    # ==========================================================
    async def close(self):
        """Full teardown used by Core."""
        self._closing = True
        self.connected = False

        if self.heartbeat_task:
            self.heartbeat_task.cancel()

        try:
            if self.ws:
                await self.ws.close()
        except:
            pass

        if self.session:
            await self.session.close()

        print("[IPC] Closed.")
