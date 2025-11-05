# bot/ipc_bridge.py

import os, json, asyncio, aiohttp, time

AUTH_KEY = os.getenv("AUTH_KEY")
WEB_URL = os.getenv("WEB_URL")
WS_URL = WEB_URL.replace("https", "wss") + "/ipc"

class IPCBridge:
    def __init__(self):
        self.session = None
        self.ws = None
        self.connected = False
    
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
        
    async def listen_loop(self):
        from bot.ipc_server import handle_bot_command
        while True:
            try:
                if not self.connected:
                    await self.connect()
                async for msg in self.ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            print("[BOT] Received data:", data)
                        except Exception:
                            print("[IPC-Bridge] Invalid JSON from server:", msg.data)
                            continue
                        
                        # Expect a command payload such as {"command": "PLAY", ...}
                        if "command" in data:
                            try:
                                result = await handle_bot_command(data)
                                # Respond and acknowledge command
                                await self.safe_send({
                                    "type": "command_result",
                                    "ok": True,
                                    "for": data.get("command"),
                                    "result": result
                                })
                                
                            except Exception as e:
                                await self.safe_send({
                                    "type": "command_result",
                                    "ok": False,
                                    "for": data.get("command"),
                                    "error": str(e)
                                })
                        else:
                            # Other notifications for the bot can be handled here
                            pass
                        
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
                
            
            # Rest before a reconnect
            await asyncio.sleep(5)
            
    async def safe_send(self, payload: dict):
        if not self.connected or self.ws is None:
            return
        try:
            await self.ws.send_json(payload)
        except Exception as e:
            print("[IPC-BRIDGE] send error:", e)
            
    async def close(self):
        self.connected = False
        try:
            if self.ws is not None:
                await self.ws.close()
        finally:
            if self.session is not None:
                await self.session.close()
    
    async def send_state(self, state: dict):
        await self.safe_send({"type":"state_update", "auth": AUTH_KEY, "payload": state, "ts": time.time()})

