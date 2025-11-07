# bot_runner.py

import asyncio, os, aiohttp

from bot.bot_core import BotCore


# -------------------------------------------------------------
# Wait for the Web Server (needed so IPC Bridge has somewhere to connect)
# -------------------------------------------------------------
async def wait_for_web():
    """
    Wait until the WebSocket IPC endpoint is accepting connections.
    """
    web_url = os.getenv("WEB_URL", "https://ambienceinator-web.onrender.com")
    ipc_url = web_url.replace("https", "wss") + "/ipc"

    print(f"[RUNNER] Waiting for IPC endpoint: {ipc_url}")

    for i in range(15):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ipc_url, timeout=5) as ws:
                    print("[RUNNER] IPC endpoint is live!")
                    return
        except Exception:
            print(f"[RUNNER] IPC not ready yet... ({i+1}/15)")
            await asyncio.sleep(2)

    print("[RUNNER] Proceeding even though IPC didn't respond.")


# -------------------------------------------------------------
# Main Startup
# -------------------------------------------------------------
async def main():
    print("[RUNNER] Launching Ambience-inator Bot...")

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is missing")

    # 1. Create the central bot core
    core = BotCore()

    # 2. Build the Discord bot instance
    core.create_discord_bot()

    # 3. Wait for the web server (prevents IPC connect spam)
    await wait_for_web()

    # 4. Start the Discord bot — bot_core handles IPC + state init on_ready
    print("[RUNNER] Starting Discord bot connection to Discord API…")
    await core.start(token)

    print("[RUNNER] Bot is running.")

    # Keep the process alive indefinitely
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        print("[RUNNER] Shutdown signal received. Exiting…")


# -------------------------------------------------------------
# Entrypoint
# -------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
