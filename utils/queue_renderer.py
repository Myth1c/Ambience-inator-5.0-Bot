# utils/queue_renderer.py

import discord

GREEN = 0x4CAF50
BOX_WIDTH = 46  # inner width


def _md_escape(s: str) -> str:
    """Basic Markdown escaping for Discord."""
    return (s.replace('\\', '\\\\')
             .replace('`', r'\`')
             .replace('*', r'\*')
             .replace('_', r'\_')
             .replace('|', r'\|')
             .replace('[', r'\[')
             .replace(']', r'\]')
             .replace('(', r'\(')
             .replace(')', r'\)'))


def render_queue_embed(queue: dict, page: int = 1, per_page: int = 10) -> discord.Embed:
    """
    queue = {
        "playlist_name": str,
        "tracks": [{"name": str, "url": str}, ...],
        "current_index": int,
        "loop_current": bool,
        "shuffle_mode": bool }
    """
    name = queue.get("playlist_name") or "None"
    tracks = queue.get("tracks") or []
    cur = max(0, queue.get("current_index", 0))
    total = len(tracks)

    # Clamp index
    if total == 0:
        cur = 0
    elif cur >= total:
        cur = total - 1

    # ===================================================================
    # NOW PLAYING BLOCK
    # ===================================================================
    box_width = BOX_WIDTH

    if total > 0:
        now_title = _md_escape(tracks[cur]["name"])[:box_width]
        title_line = now_title.center(box_width)

        now_block = (
            "┏" + "━" * box_width + "┓\n"
            f"┃{title_line}┃\n"
            f"┃{f'(index {cur+1}/{total})'.center(box_width)}┃\n"
            "┗" + "━" * box_width + "┛"
        )
    else:
        msg = "(No song playing)".center(box_width)
        now_block = (
            "┏" + "━" * box_width + "┓\n"
            f"┃{msg}┃\n"
            "┗" + "━" * box_width + "┛"
        )

    # ===================================================================
    # Recently Played (up to 3)
    # ===================================================================
    recent_lines = []
    if total > 0 and cur > 0:
        start = max(0, cur - 3)
        for i in range(start, cur):
            idx = f"{i+1}."
            title = _md_escape(tracks[i]["name"])
            recent_lines.append(f"{idx:>3}  {title}")

    # ===================================================================
    # Up Next — paginated
    # ===================================================================
    upnext_lines = []
    page_start = cur + 1 + (page - 1) * per_page
    page_end = min(total, page_start + per_page)

    if page_start < total:
        for i in range(page_start, page_end):
            idx = f"{i+1}."
            title = _md_escape(tracks[i]["name"])
            upnext_lines.append(f"{idx:>3}  {title}")

    remaining = max(0, (total - (cur + 1)) - (page * per_page))

    # ===================================================================
    # BUILD EMBED
    # ===================================================================
    em = discord.Embed(title=f"Current Playlist: {name}", color=GREEN)

    em.add_field(name="   Now Playing",
                 value=f"```{now_block}```",
                 inline=False)

    if recent_lines:
        em.add_field(
            name="   Recently Played",
            value="```" + "\n".join(recent_lines) + "```",
            inline=False,
        )

    if upnext_lines:
        footer_more = f"\n… +{remaining} more" if remaining > 0 else ""
        em.add_field(
            name=f"   Up Next — Page {page}",
            value="```" + "\n".join(upnext_lines) + "```" + footer_more,
            inline=False,
        )
    elif total == 0:
        em.add_field(name="   Up Next",
                     value="(queue is empty)",
                     inline=False)

    em.set_footer(
        text=f" Loop: {'On' if queue.get('loop_current') else 'Off'}"
             f"  •  Shuffle: {'On' if queue.get('shuffle_mode') else 'Off'}"
             f"  •  Tracks: {total}"
    )

    return em
