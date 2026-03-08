"""
downloader.py — yt-dlp download engine for mp4-ripper.

Responsibilities:
- Fetch video metadata (title, duration, thumbnail URL, best resolution)
- Download video + audio merged as a single .mp4
- Tri-state caption support: none, SRT file, burned-in via FFmpeg
- YouTube Premium cookies.txt passthrough
- Progress callback for GUI progress bar
"""

import glob
import os
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional

import yt_dlp


# ---------------------------------------------------------------------------
# Caption mode constants
# ---------------------------------------------------------------------------

CAPTION_NONE = "none"
CAPTION_SRT = "srt"
CAPTION_BURNED = "burned"


# ---------------------------------------------------------------------------
# FFmpeg availability check
# ---------------------------------------------------------------------------

def check_ffmpeg() -> bool:
    """Return True if ffmpeg is accessible on the system PATH."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


# ---------------------------------------------------------------------------
# Metadata fetch
# ---------------------------------------------------------------------------

def fetch_metadata(url: str, cookies_file: Optional[str] = None) -> dict:
    """
    Fetch video metadata without downloading.

    Returns a dict with keys:
        title, duration_seconds, thumbnail_url, best_resolution, webpage_url
    Raises yt_dlp.utils.DownloadError on failure.
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    if cookies_file and os.path.isfile(cookies_file):
        opts["cookiefile"] = cookies_file

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    # Determine best resolution label from available formats
    best_height = 0
    for fmt in info.get("formats", []):
        h = fmt.get("height") or 0
        if h > best_height:
            best_height = h
    resolution_label = f"{best_height}p" if best_height else "unknown"

    # Check subtitle availability (manual + auto-generated)
    has_subtitles = bool(info.get("subtitles")) or bool(info.get("automatic_captions"))

    return {
        "title": info.get("title", "Unknown Title"),
        "duration_seconds": info.get("duration", 0),
        "thumbnail_url": info.get("thumbnail", ""),
        "best_resolution": resolution_label,
        "webpage_url": info.get("webpage_url", url),
        "has_subtitles": has_subtitles,
    }


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_video(
    url: str,
    output_dir: str,
    caption_mode: str = CAPTION_NONE,
    cookies_file: Optional[str] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
    status_callback: Optional[Callable[[str], None]] = None,
) -> None:
    """
    Download a YouTube video to output_dir.

    Args:
        url:               YouTube video URL.
        output_dir:        Directory to save output files.
        caption_mode:      CAPTION_NONE, CAPTION_SRT, or CAPTION_BURNED.
        cookies_file:      Path to a Netscape-format cookies.txt file (optional).
        progress_callback: Called with a float 0.0–100.0 as download progresses.
        status_callback:   Called with a status string for display in the GUI.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    def _notify_status(msg: str) -> None:
        if status_callback:
            status_callback(msg)

    def _progress_hook(d: dict) -> None:
        if d["status"] == "downloading" and progress_callback:
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                progress_callback((downloaded / total) * 100.0)
        elif d["status"] == "finished":
            if progress_callback:
                # Don't snap to 100 here — merging may still be in progress
                progress_callback(90.0)

    # ------------------------------------------------------------------
    # Build yt-dlp options
    # ------------------------------------------------------------------

    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

    opts: dict = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
        "noplaylist": True,
        "progress_hooks": [_progress_hook],
        "quiet": True,
        "no_warnings": True,
    }

    if cookies_file and os.path.isfile(cookies_file):
        opts["cookiefile"] = cookies_file

    # ------------------------------------------------------------------
    # Caption mode logic
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Download (video + audio only — no subtitle flags here to prevent
    # yt-dlp from silently embedding subs into the MP4 during the merge)
    # ------------------------------------------------------------------

    _notify_status("Downloading...")
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # prepare_filename gives us the expected output path before merging;
        # after merging yt-dlp always produces a .mp4 due to merge_output_format.
        raw_filename = ydl.prepare_filename(info)

    final_mp4 = os.path.splitext(raw_filename)[0] + ".mp4"

    # ------------------------------------------------------------------
    # Subtitle fetch — separate yt-dlp pass (skip_download=True)
    # Decoupled from the merge so the .srt is never auto-embedded.
    # ------------------------------------------------------------------

    if caption_mode in (CAPTION_SRT, CAPTION_BURNED):
        _notify_status("Fetching subtitles...")
        sub_opts: dict = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitlesformat": "srt",
            "subtitleslangs": ["en"],
            "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }
        if cookies_file and os.path.isfile(cookies_file):
            sub_opts["cookiefile"] = cookies_file

        with yt_dlp.YoutubeDL(sub_opts) as ydl:
            ydl.extract_info(url, download=True)

        # Clean rolling-word artifacts from the downloaded SRT
        base = os.path.splitext(final_mp4)[0]
        for srt_file in glob.glob(glob.escape(base) + ".*.srt"):
            _clean_srt(srt_file)

    # ------------------------------------------------------------------
    # Burned-in subtitle pass (FFmpeg hardcode)
    # ------------------------------------------------------------------

    if caption_mode == CAPTION_BURNED:
        _notify_status("Burning in subtitles...")
        base = os.path.splitext(final_mp4)[0]
        srt_candidates = glob.glob(glob.escape(base) + ".*.srt")
        if srt_candidates:
            srt_path = srt_candidates[0]
            _clean_srt(srt_path)
            _burn_subtitles(final_mp4, srt_path)
        else:
            _notify_status("No subtitles found to burn — saving video without captions.")

    if progress_callback:
        progress_callback(100.0)
    _notify_status("Done")


def _clean_srt(srt_path: str) -> None:
    """
    Clean YouTube auto-caption SRT artifacts in-place.

    YouTube produces two types of messy caption patterns:

    1. Rolling-word (prefix): each entry is a superset of the previous
         Entry 1 "Hello"  Entry 2 "Hello world"  Entry 3 "Hello world now"
       Fix: drop any entry whose text is a prefix of the next entry's text.

    2. Overlapping / same-timestamp blocks: two entries share the same
       start time (or overlap heavily), causing FFmpeg to display both
       lines simultaneously.
       Fix: group by start time, merge text within the group; then
       trim overlapping end times so no two entries are active at once.
    """
    import re

    # ------------------------------------------------------------------
    # SRT timestamp helpers
    # ------------------------------------------------------------------

    def _ts_to_ms(ts: str) -> int:
        """'HH:MM:SS,mmm' -> milliseconds"""
        ts = ts.strip().replace(",", ".")
        h, m, rest = ts.split(":")
        s, ms = rest.split(".")
        return int(h) * 3_600_000 + int(m) * 60_000 + int(s) * 1_000 + int(ms)

    def _ms_to_ts(ms: int) -> str:
        """milliseconds -> 'HH:MM:SS,mmm'"""
        ms = max(0, ms)
        h, ms = divmod(ms, 3_600_000)
        m, ms = divmod(ms, 60_000)
        s, ms = divmod(ms, 1_000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    # ------------------------------------------------------------------
    # Parse
    # ------------------------------------------------------------------

    with open(srt_path, encoding="utf-8", errors="replace") as f:
        raw = f.read()

    blocks = [b.strip() for b in re.split(r"\n\s*\n", raw) if b.strip()]

    parsed = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3:
            continue
        timing_line = lines[1]
        m = re.match(r"(.+?)\s*-->\s*(.+)", timing_line)
        if not m:
            continue
        start_ms = _ts_to_ms(m.group(1))
        end_ms = _ts_to_ms(m.group(2))
        text = "\n".join(lines[2:]).strip()
        parsed.append({"start": start_ms, "end": end_ms, "text": text})

    if not parsed:
        return

    # ------------------------------------------------------------------
    # Pass 1: drop rolling-word prefix entries
    # ------------------------------------------------------------------

    after_prefix = []
    for i, entry in enumerate(parsed):
        if i < len(parsed) - 1:
            next_text = parsed[i + 1]["text"].replace("\n", " ").strip()
            this_text = entry["text"].replace("\n", " ").strip()
            if next_text.startswith(this_text):
                continue  # This is a partial version of the next entry
        after_prefix.append(entry)

    # ------------------------------------------------------------------
    # Pass 2: merge entries that share the same start time
    # ------------------------------------------------------------------

    merged = []
    i = 0
    while i < len(after_prefix):
        group = [after_prefix[i]]
        j = i + 1
        while j < len(after_prefix) and after_prefix[j]["start"] == after_prefix[i]["start"]:
            group.append(after_prefix[j])
            j += 1
        # Merge group into one entry: join texts, use the longest end time
        combined_text = " ".join(e["text"].replace("\n", " ") for e in group)
        combined_end = max(e["end"] for e in group)
        merged.append({"start": group[0]["start"], "end": combined_end, "text": combined_text})
        i = j

    # ------------------------------------------------------------------
    # Pass 3: fix overlapping end times
    # Trim each entry's end so it doesn't overlap with the next entry's start.
    # ------------------------------------------------------------------

    for i in range(len(merged) - 1):
        if merged[i]["end"] > merged[i + 1]["start"]:
            merged[i]["end"] = merged[i + 1]["start"]

    # ------------------------------------------------------------------
    # Write back
    # ------------------------------------------------------------------

    out_lines = []
    for idx, entry in enumerate(merged, start=1):
        timing = f"{_ms_to_ts(entry['start'])} --> {_ms_to_ts(entry['end'])}"
        out_lines.append(str(idx))
        out_lines.append(timing)
        out_lines.append(entry["text"])
        out_lines.append("")

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))


def _burn_subtitles(mp4_path: str, srt_path: str) -> None:
    """
    Hardcode the subtitle file into the video using FFmpeg.
    Operates in-place: rewrites the .mp4 file.

    Uses cwd= trick to avoid Windows drive-letter colon escaping issues
    in the FFmpeg subtitles= filter.
    """
    work_dir = os.path.dirname(os.path.abspath(mp4_path))
    mp4_name = os.path.basename(mp4_path)
    srt_name = os.path.basename(srt_path)
    tmp_name = mp4_name + ".tmp.mp4"

    # Escape characters that are special in FFmpeg filter syntax.
    # On Windows the filename itself may contain colons (from the title) — escape them.
    def _escape(name: str) -> str:
        return name.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

    cmd = [
        "ffmpeg",
        "-y",
        "-i", mp4_name,
        "-vf", f"subtitles={_escape(srt_name)}",
        "-c:a", "copy",
        tmp_name,
    ]

    result = subprocess.run(
        cmd,
        cwd=work_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0:
        err = result.stderr.decode(errors="replace")
        raise RuntimeError(f"FFmpeg subtitle burn failed:\n{err}")

    os.replace(os.path.join(work_dir, tmp_name), mp4_path)

    # Clean up the .srt file after burning (it's now in the video)
    try:
        os.remove(srt_path)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Thread helper (used by GUI)
# ---------------------------------------------------------------------------

def download_in_thread(
    url: str,
    output_dir: str,
    caption_mode: str = CAPTION_NONE,
    cookies_file: Optional[str] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
    status_callback: Optional[Callable[[str], None]] = None,
    done_callback: Optional[Callable[[Optional[Exception]], None]] = None,
) -> threading.Thread:
    """
    Run download_video in a background thread.

    done_callback is called with None on success, or the Exception on failure.
    Returns the Thread object (already started).
    """
    def _run() -> None:
        try:
            download_video(
                url=url,
                output_dir=output_dir,
                caption_mode=caption_mode,
                cookies_file=cookies_file,
                progress_callback=progress_callback,
                status_callback=status_callback,
            )
            if done_callback:
                done_callback(None)
        except Exception as exc:
            if done_callback:
                done_callback(exc)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t
