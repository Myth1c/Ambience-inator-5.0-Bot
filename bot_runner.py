# bot_runner.py

import asyncio, os, aiohttp

from bot import BotCore


# -------------------------------------------------------------
# Wait for the Web Server (needed so IPC Bridge has somewhere to connect)
# -------------------------------------------------------------
async def wait_for_web():
    web_url = os.getenv("WEB_URL")

    if not web_url:
        print("[RUNNER] WEB_URL not set, skipping web readiness check.")
        return

    print(f"[RUNNER] Waiting for web server: {web_url}")

    for i in range(10):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(web_url) as resp:
                    if resp.status in (200, 301, 302):
                        print("[RUNNER] Web server detected, continuing startup")
                        return
        except Exception:
            print(f"[RUNNER] Attempt {i+1}/10: Web server unreachable... retrying in 2s.")

        await asyncio.sleep(2)

    print("[RUNNER] Proceeding despite web server not responding.")


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
