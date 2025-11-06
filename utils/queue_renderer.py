# utils/queue_render.py


import discord

from html import escape as _html_escape
from bot.playback import music_queue

GREEN = 0x4CAF50
BOX_WIDTH = 46 # Inner width (no borders)


def _md_escape(s: str) -> str:
    # Minimal Markdown escaper for Discord (bold/italics/backticks/links)
    return (
        s.replace('\\', '\\\\')
         .replace('`', r'\`')
         .replace('*', r'\*')
         .replace('_', r'\_')
         .replace('|', r'\|')
         .replace('[', r'\[')
         .replace(']', r'\]')
         .replace('(', r'\(')
         .replace(')', r'\)')
    )

def render_queue_embed(page: int = 1, per_page: int = 10) -> discord.Embed:
    """
    queue dict shape:
      {
        "playlist_name": str | None,
        "tracks": [{"name": str, "url": str}, ...],
        "current_index": int,
        "previous_stack": [int, ...],     # optional
        "loop_current": bool,
        "shuffle_mode": bool
      }
    """
    queue = music_queue.get_queue()
    
    name = queue.get("playlist_name") or "None"
    tracks = queue.get("tracks") or []
    cur = max(0, int(queue.get("current_index", 0)))
    total = len(tracks)

    # Clamp current index
    if total == 0:
        cur = 0
    elif cur >= total:
        cur = total - 1

    # --- Build Now Playing card (monospace via code block) ---
    box_width = BOX_WIDTH  # 46

    if total > 0:
        # Escape + clamp title
        now_title = _md_escape(tracks[cur]["name"])[:box_width]

        # Center the title inside the box
        title_line = now_title.center(box_width)

        # Build the block
        now_block = (
            "┏" + "━" * box_width + "┓\n"
            f"┃{title_line}┃\n"
            f"┃{f'(index {cur+1}/{total})'.center(box_width)}┃\n"
            "┗" + "━" * box_width + "┛"
        )

    else:
        # Center the no-song message
        msg = "(No song playing)".center(box_width)
        now_block = (
            "┏" + "━" * box_width + "┓\n"
            f"┃{msg}┃\n"
            "┗" + "━" * box_width + "┛"
        )

    # --- Recently played (up to 3 before current) ---
    recent_lines = []
    if total > 0 and cur > 0:
        start = max(0, cur - 3)
        for i in range(start, cur):
            idx_label = f"{i+1}."
            title = _md_escape(tracks[i]["name"])
            # monospace lines via code fence later
            recent_lines.append(f"{idx_label:>3}  {title}")

    # --- Up next (paginated) ---
    next_start = cur + 1
    next_end = min(total, next_start + per_page * page)
    # Compute page window: items [cur+1 : cur+1 + per_page]
    page_start = cur + 1 + (page - 1) * per_page
    page_end = min(total, page_start + per_page)
    upnext_lines = []
    if total > 0 and page_start < total:
        for i in range(page_start, page_end):
            idx_label = f"{i+1}."
            title = _md_escape(tracks[i]["name"])
            upnext_lines.append(f"{idx_label:>3}  {title}")
    remaining = max(0, (total - (cur + 1)) - (page * per_page))

    # --- Build embed ---
    em = discord.Embed(
        title=f"Current Playlist: {name}",
        color=GREEN
    )

    # Now playing panel (monospace via triple backticks)
    em.add_field(
        name="   Now Playing",
        value=f"```{now_block}```",
        inline=False
    )

    # Recently played (only if present)
    if recent_lines:
        em.add_field(
            name="   Recently Played",
            value=f"```" + "\n".join(recent_lines) + "```",
            inline=False
        )

    # Up next (with pagination)
    if upnext_lines:
        footer_more = f"\n… +{remaining} more" if remaining > 0 else ""
        em.add_field(
            name=f"   Up Next — Page {page}",
            value=f"```" + "\n".join(upnext_lines) + "```" + footer_more,
            inline=False
        )
    elif total == 0:
        em.add_field(  
            name="   Up Next",
            value="(queue is empty)",
            inline=False
        )

    loop = "On" if queue.get("loop_current") else "Off"
    shuf = "On" if queue.get("shuffle_mode") else "Off"
    em.set_footer(text=f" Loop: {loop}  •    Shuffle: {shuf}  •    Tracks: {total}")

    return em
