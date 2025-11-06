# bot/ipc_bridge.py

import os, json, asyncio, aiohttp, time

from bot.state_manager import get_playback_state

AUTH_KEY = os.getenv("AUTH_KEY")
WEB_URL = os.getenv("WEB_URL")
WS_URL = WEB_URL.replace("https", "wss") + "/ipc"

class IPCBridge:
    def __init__(self):
        self.session = None
        self.ws = None
        self.connected = False
        self.heartbeat_task = None
    
    async def connect(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
        print(f"[IPC-Bridge] Connecting to {WS_URL}")
        self.ws = await self.session.ws_connect(WS_URL, heartbeat=20)
        self.connected = True
        print("[IPC-Bridge] Connected")
        
        
        # Identify this bot
        await self.ws.send_json({
            "type": "bot_hello", 
            "auth": AUTH_KEY,
            "ts": time.time()
        })
        
        # Start heartbeat loop if not already running
        if not self.heartbeat_task or self.heartbeat_task.done():
            self.heartbeat_task = asyncio.create_task(self.start_heartbeat())
        
    async def listen_loop(self):
        """Continuously maintain a connection to the web IPC endpoint."""
        while True:
            try:
                if not self.connected:
                    await self.connect()

                async for msg in self.ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await self.handle_message(msg.data)
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        print("[IPC-Bridge] WS closed")
                        self.connected = False
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print("[IPC-Bridge] WS error", msg)
                        self.connected = False
                        break
            except Exception as e:
                print(f"[IPC-Bridge] Loop error: {e}")
                self.connected = False
                try:
                    if self.ws:
                        await self.ws.close()
                except Exception:
                    pass
            
            # Rest before a reconnect
            await asyncio.sleep(5)
    
    async def handle_message(self, raw_data: str):
        from bot.command_dispatcher import dispatch_command
        """Process a single incoming WebSocket message from the server."""
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            print("[IPC-Bridge] Received invalid JSON:", raw_data)
            return

        msg_type = data.get("type")
        command = data.get("command")

        # === Handle by message type ===
        if msg_type == "server_ack":
            print("[IPC-Bridge] Server acknowledged connection.")
            return

        if msg_type == "broadcast":
            print("[IPC-Bridge] Received broadcast:", data)
            return
        
        if msg_type == "heartbeat_check":
            await self.safe_send({"type": "heartbeat_ack", "ts": time.time()})
            return

        if command:
            print(f"[BOT] Received command: {command}")
            result = await dispatch_command(data)
            await self.safe_send(result)
        else:
            print("[IPC-Bridge] Ignored message without 'command' or known 'type'.")

    async def start_heartbeat(self, interval=60):
        """Periodically broadcast bot state to the server."""
        print("[IPC-Bridge] Heartbeat started (interval default 60s)")
        while self.connected:
            try:
                state = get_playback_state()
                await self.send_state(state)
            except Exception as e:
                print("[IPC-Bridge] Heartbeat send failed:", e)
                self.connected = False
            await asyncio.sleep(interval)
        print("[IPC-Bridge] Heartbeat stopped")
    
    async def safe_send(self, payload: dict):
        if not self.connected or self.ws is None:
            return
        try:
            await self.ws.send_json(payload)
        except Exception as e:
            print("[IPC-BRIDGE] send error:", e)
            
    async def close(self):
        self.connected = False
        
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            
        try:
            if self.ws is not None:
                await self.ws.close()
        finally:
            if self.session is not None:
                await self.session.close()
    
    async def send_state(self, state: dict):
        await self.safe_send({"type":"state_update", "payload": state, "ts": time.time()})
