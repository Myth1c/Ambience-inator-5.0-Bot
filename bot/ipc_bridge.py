# bot/ipc_bridge.py

import os, json, asyncio, aiohttp, time

from contextlib import suppress

WS_URL = os.getenv("WEB_URL", "").replace("https", "wss") + "/ipc"
AUTH_KEY = os.getenv("AUTH_KEY")


class IPCBridge:
    """
    Long-lived WS bridge between bot container and web dashboard.
    - Keeps a persistent connection with auto-reconnect.
    - Uses a bounded outbound queue + dedicated sender task to avoid hangs.
    - Reader and sender tasks are per-connection; they are recreated on reconnect.
    """
    def __init__(self, core, *, outbound_capacity: int = 100):
        from bot import CommandDispatcher  # avoid circular import
        self.core = core

        # aiohttp session and ws
        self.session: aiohttp.ClientSession | None = None
        self.ws: aiohttp.ClientWebSocketResponse | None = None

        # lifecycle flags
        self._closing = False
        self.connected = False

        # connection-scoped tasks
        self._reader_task: asyncio.Task | None = None
        self._sender_task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None

        # long-lived supervisor
        self._supervisor_task: asyncio.Task | None = None

        # send queue
        self._outbound = asyncio.Queue(maxsize=outbound_capacity)

        # connection gate (for waiters who need to know when we're up)
        self._connected_evt = asyncio.Event()

        # dispatcher
        self.dispatcher = CommandDispatcher(core)

        # backoff
        self._reconnect_delay = 5

    # =========================================================
    # Public API
    # =========================================================
    async def run_forever(self):
        """
        Supervisor loop: connect, spawn reader/sender/heartbeat tasks, and
        reconnect on any failure. Call exactly once at process startup.
        """
        while not self._closing:
            try:
                await self._ensure_session()
                await self._connect()

                # Start per-connection tasks
                self._reader_task   = asyncio.create_task(self._reader_loop(), name="ipc-reader")
                self._sender_task   = asyncio.create_task(self._sender_loop(), name="ipc-sender")
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(), name="ipc-heartbeat")

                # Wait for the first task to end (error or normal close)
                done, pending = await asyncio.wait(
                    {self._reader_task, self._sender_task, self._heartbeat_task},
                    return_when=asyncio.FIRST_COMPLETED
                )

                # If any ended, we need to reconnect: cancel the rest
                for task in pending:
                    task.cancel()
                for task in (self._reader_task, self._sender_task, self._heartbeat_task):
                    with suppress(Exception):
                        await task
                self._reader_task = self._sender_task = self._heartbeat_task = None

            except Exception as e:
                print(f"[IPC] Supervisor error: {e}")

            # Cleanup and schedule reconnect
            await self._cleanup_ws()
            if not self._closing:
                print(f"[IPC] Reconnecting in {self._reconnect_delay} seconds...")
                await asyncio.sleep(self._reconnect_delay)

    async def send(self, payload: dict, *, drop_if_full: bool = False) -> bool:
        """
        Enqueue a JSON payload for sending by the sender task.
        Returns True if enqueued, False if dropped (only if drop_if_full=True).
        """
        if self._closing:
            return False

        item = json.dumps(payload)
        try:
            if drop_if_full:
                self._outbound.put_nowait(item)
            else:
                await self._outbound.put(item)
            return True
        except asyncio.QueueFull:
            print("[IPC] Outbound queue full; dropping message.")
            return False

    async def wait_connected(self, timeout: float | None = None) -> bool:
        """
        Wait until the websocket is connected (or timeout).
        """
        if self.connected and self.ws and not self.ws.closed:
            return True
        try:
            await asyncio.wait_for(self._connected_evt.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def close(self):
        """
        Full teardown for process shutdown.
        """
        self._closing = True
        self._connected_evt.clear()

        # cancel supervisor (if you wrapped run_forever in a task)
        if self._supervisor_task:
            self._supervisor_task.cancel()
            with suppress(Exception):
                await self._supervisor_task
            self._supervisor_task = None

        # cancel per-connection tasks
        for task in (self._reader_task, self._sender_task, self._heartbeat_task):
            if task:
                task.cancel()
        for task in (self._reader_task, self._sender_task, self._heartbeat_task):
            if task:
                with suppress(Exception):
                    await task
        self._reader_task = self._sender_task = self._heartbeat_task = None

        await self._cleanup_ws()

        if self.session:
            with suppress(Exception):
                await self.session.close()
            self.session = None

        print("[IPC] Closed.")

    # =========================================================
    # Connection management
    # =========================================================
    async def _ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def _connect(self):
        print(f"[IPC] Connecting to {WS_URL}...")
        self.ws = await self.session.ws_connect(WS_URL, heartbeat=30)
        self.connected = True
        self._connected_evt.set()
        print("[IPC] Connected.")

        # Send hello packet via sender (avoid writing from connect thread)
        await self.send({
            "type": "bot_hello",
            "auth": AUTH_KEY,
            "ts": time.time()
        })

    async def _cleanup_ws(self):
        self.connected = False
        self._connected_evt.clear()

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            with suppress(Exception):
                await self._heartbeat_task
            self._heartbeat_task = None

        # Drain outbound queue so we don't hold stale messages forever
        # (Alternatively, keep them to resend after reconnect)
        while not self._outbound.empty():
            with suppress(Exception):
                self._outbound.get_nowait()
                self._outbound.task_done()

        if self.ws:
            with suppress(Exception):
                await self.ws.close()
            self.ws = None

    # =========================================================
    # Loops
    # =========================================================
    async def _reader_loop(self):
        """
        Receives frames and dispatches commands.
        Any exception or CLOSED/ERROR will bubble up to supervisor.
        """
        assert self.ws is not None
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                with suppress(Exception):
                    data = json.loads(msg.data)
                await self._handle_frame_safe(data)
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                print("[IPC] WS closed by server.")
                break
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print("[IPC] WS error:", msg)
                break

    async def _sender_loop(self):
        """
        Consumes the outbound queue and writes to the websocket.
        If the transport is closing/closed, raises to trigger reconnect.
        """
        assert self.ws is not None
        while True:
            item = await self._outbound.get()
            try:
                # double-check connection
                if not self.connected or self.ws is None or self.ws.closed:
                    raise ConnectionError("WS not connected")

                await self.ws.send_str(item)
            except Exception as e:
                print("[IPC] send error in sender_loop:", e)
                # put message back at the front? (simple approach: drop; or requeue once)
                # Re-queue once to avoid message loss on transient timing:
                with suppress(Exception):
                    self._outbound.put_nowait(item)
                # Bubble up to reconnect
                raise
            finally:
                self._outbound.task_done()

    async def _heartbeat_loop(self, interval: int = 60):
        """
        Periodically enqueue full state to dashboard.
        """
        print("[IPC] Heartbeat started.")
        try:
            while True:
                # Only enqueue if connected; otherwise skip quietly
                if self.connected:
                    try:
                        await self.send({
                            "type": "state_update",
                            "payload": self.core.state.get_state(),
                            "ts": time.time()
                        }, drop_if_full=True)
                    except Exception as e:
                        print("[IPC] Heartbeat enqueue failed:", e)
                await asyncio.sleep(interval)
        finally:
            print("[IPC] Heartbeat stopped.")

    # =========================================================
    # Frame handling
    # =========================================================
    async def _handle_frame_safe(self, data: dict):
        """
        Handle a parsed JSON frame with protection.
        """
        if not isinstance(data, dict):
            print("[IPC] Ignoring non-dict frame.")
            return

        msg_type = data.get("type")
        cmd = data.get("command")

        # Gate commands while bot core is not ready (allow a few setup ones)
        if cmd and not self.core.ready and cmd not in (
            "SETUP_SAVE", "GET_PLAYBACK_STATE", "GET_PLAYLISTS", "SAVE_PLAYLISTS",
            "GET_AMBIENCE", "SAVE_AMBIENCE", "GET_BOT_STATUS", "START_BOT"
        ):
            await self.send({
                "ok": False,
                "command": cmd,
                "error": "BOT_NOT_READY",
                "ts": time.time()
            })
            print("[IPC] Command rejected: Bot is not ready")
            return

        # Built-ins
        if msg_type == "server_ack":
            print("[IPC] Server acknowledged connection.")
            return

        if msg_type == "broadcast":
            print("[IPC] Broadcast from server:", data)
            return

        if msg_type == "heartbeat_check":
            await self.send({"type": "heartbeat_ack", "ts": time.time()})
            return

        # Commands
        if cmd:
            print(f"[IPC] Received command: {cmd}")
            result = await self.dispatcher.handle(data)
            await self.send(result)
            return

        print("[IPC] Ignoring unrecognized message:", data)