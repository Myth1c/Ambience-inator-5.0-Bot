# bot_runner.py

import asyncio
import os
import aiohttp

from bot.instance import get_bot_instance
from bot.ipc_server import start_ipc_server
from bot.control import start_discord_bot

async def wait_for_web():
    web_URL = os.getenv("WEB_URL", "https://ambienceinator-web.onrender.com")

    for i in range(10):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(web_URL) as resp:
                    if resp.status in (200, 302):
                        print("[BOT] Web server detected, continuing startup")
                        return
        except Exception:
            print(f"[BOT] Waiting for web server at {web_URL}... ({i+1}/10)")
            await asyncio.sleep(2)
    print("[BOT] Proceeding without web confirmation.")


async def main():
    print("[RUNNER] Starting Ambience-inator Bot process...")

    # Load environment variables (set in docker-compose .env)
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN environment variable not set")

    # Attach token to bot for reuse
    bot = get_bot_instance()
    bot.http.token = bot_token

    # Start the IPC server in the background
    asyncio.create_task(start_ipc_server(bot))
    print("[RUNNER] IPC server started")
    

    # Start the Discord bot using our control lifecycle logic
    await wait_for_web()
    await start_discord_bot()
    print("[RUNNER] Discord bot running")
    

    # Keep process alive
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        print("[RUNNER] Shutting down bot...")

if __name__ == "__main__":
    asyncio.run(main())
