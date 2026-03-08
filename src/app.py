"""
app.py — mp4-ripper GUI entry point.

Single-screen Tkinter app:
  - URL entry + Fetch Info button
  - Thumbnail preview, title, duration, best resolution
  - Tri-state caption mode (No Captions / SRT File / Burned In)
  - Output folder selector
  - Optional cookies.txt selector (YouTube Premium)
  - Download button + progress bar + status label
"""

import io
import os
import threading
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
from pathlib import Path
from tkinter import ttk
from typing import Optional
from urllib.request import urlopen

from PIL import Image, ImageTk

from downloader import (
    CAPTION_BURNED,
    CAPTION_NONE,
    CAPTION_SRT,
    check_ffmpeg,
    download_in_thread,
    fetch_metadata,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

APP_TITLE = "mp4-ripper"
WINDOW_SIZE = "720x700"
THUMB_SIZE = (320, 180)
DEFAULT_OUTPUT_DIR = str(Path.home() / "Downloads" / "mp4-ripper")

BG = "#1e1e2e"
SURFACE = "#2a2a3e"
ACCENT = "#7c6af7"
ACCENT_HOVER = "#9d8fff"
TEXT_PRIMARY = "#cdd6f4"
TEXT_MUTED = "#6c7086"
SUCCESS = "#a6e3a1"
ERROR_COLOR = "#f38ba8"
PROGRESS_BG = "#313244"

FONT_BODY = ("Segoe UI", 10)
FONT_LABEL = ("Segoe UI", 9)
FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_SMALL = ("Segoe UI", 8)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class Mp4RipperApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.resizable(False, False)
        self.configure(bg=BG)

        # State
        self._thumb_image: Optional[ImageTk.PhotoImage] = None
        self._downloading = False
        self._progress_value = tk.DoubleVar(value=0.0)
        self._status_text = tk.StringVar(value="Idle")
        self._caption_mode = tk.StringVar(value=CAPTION_NONE)
        self._output_dir = tk.StringVar(value=DEFAULT_OUTPUT_DIR)
        self._cookies_path = tk.StringVar(value="")
        self._url_var = tk.StringVar()

        # Check FFmpeg once at startup
        self._ffmpeg_ok = check_ffmpeg()

        self._build_ui()
        self._apply_styles()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = tk.Frame(self, bg=BG, padx=24, pady=20)
        outer.pack(fill="both", expand=True)

        # Title
        tk.Label(
            outer,
            text="mp4-ripper",
            font=FONT_TITLE,
            bg=BG,
            fg=ACCENT,
        ).pack(anchor="w", pady=(0, 16))

        # --- URL Row ---
        self._build_url_row(outer)

        # --- Preview Panel ---
        self._build_preview_panel(outer)

        # --- Caption Mode ---
        self._build_caption_row(outer)

        # --- Output Folder ---
        self._build_folder_row(outer)

        # --- Cookies ---
        self._build_cookies_row(outer)

        # --- Progress + Status ---
        self._build_progress_row(outer)

        # --- Download Button ---
        self._build_download_button(outer)

        # --- Footer ---
        tk.Label(
            outer,
            text="For personal archival use only.",
            font=FONT_SMALL,
            bg=BG,
            fg=TEXT_MUTED,
        ).pack(side="bottom", pady=(12, 0))

    def _build_url_row(self, parent: tk.Frame) -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(0, 12))

        tk.Label(row, text="YouTube URL", font=FONT_LABEL, bg=BG, fg=TEXT_MUTED).pack(anchor="w")

        entry_row = tk.Frame(row, bg=BG)
        entry_row.pack(fill="x")

        self._url_entry = tk.Entry(
            entry_row,
            textvariable=self._url_var,
            font=FONT_BODY,
            bg=SURFACE,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
        )
        self._url_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self._url_entry.bind("<Return>", lambda _: self._fetch_info())

        self._fetch_btn = tk.Button(
            entry_row,
            text="Fetch Info",
            font=FONT_BODY,
            bg=ACCENT,
            fg="#ffffff",
            activebackground=ACCENT_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=14,
            pady=8,
            cursor="hand2",
            command=self._fetch_info,
        )
        self._fetch_btn.pack(side="left")

    def _build_preview_panel(self, parent: tk.Frame) -> None:
        panel = tk.Frame(parent, bg=SURFACE, pady=12, padx=12)
        panel.pack(fill="x", pady=(0, 14))

        # Thumbnail
        self._thumb_label = tk.Label(
            panel,
            bg=SURFACE,
            width=THUMB_SIZE[0],
            height=THUMB_SIZE[1],
            text="Thumbnail will appear here",
            font=FONT_SMALL,
            fg=TEXT_MUTED,
        )
        self._thumb_label.pack(side="left", padx=(0, 14))

        # Metadata text
        meta = tk.Frame(panel, bg=SURFACE)
        meta.pack(side="left", fill="both", expand=True, anchor="nw")

        self._title_label = tk.Label(
            meta,
            text="No video loaded",
            font=("Segoe UI", 11, "bold"),
            bg=SURFACE,
            fg=TEXT_PRIMARY,
            wraplength=310,
            justify="left",
            anchor="nw",
        )
        self._title_label.pack(anchor="nw", pady=(0, 6))

        self._duration_label = tk.Label(
            meta, text="Duration: —", font=FONT_LABEL, bg=SURFACE, fg=TEXT_MUTED, anchor="nw"
        )
        self._duration_label.pack(anchor="nw")

        self._resolution_label = tk.Label(
            meta, text="Best quality: —", font=FONT_LABEL, bg=SURFACE, fg=TEXT_MUTED, anchor="nw"
        )
        self._resolution_label.pack(anchor="nw")

    def _build_caption_row(self, parent: tk.Frame) -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(0, 12))

        tk.Label(row, text="Captions", font=FONT_LABEL, bg=BG, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 4))

        btn_row = tk.Frame(row, bg=BG)
        btn_row.pack(anchor="w")

        options = [
            ("No Captions", CAPTION_NONE),
            ("SRT File", CAPTION_SRT),
            ("Burned In", CAPTION_BURNED),
        ]
        self._caption_radios: list[tk.Radiobutton] = []
        for label, value in options:
            rb = tk.Radiobutton(
                btn_row,
                text=label,
                variable=self._caption_mode,
                value=value,
                font=FONT_BODY,
                bg=BG,
                fg=TEXT_PRIMARY,
                activebackground=BG,
                activeforeground=ACCENT,
                selectcolor=BG,
                indicatoron=True,
                cursor="hand2",
            )
            rb.pack(side="left", padx=(0, 20))
            self._caption_radios.append(rb)

        self._no_subs_label = tk.Label(
            row,
            text="",
            font=FONT_SMALL,
            bg=BG,
            fg=TEXT_MUTED,
        )
        self._no_subs_label.pack(anchor="w")

    def _build_folder_row(self, parent: tk.Frame) -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(0, 10))

        tk.Label(row, text="Output Folder", font=FONT_LABEL, bg=BG, fg=TEXT_MUTED).pack(anchor="w")

        field_row = tk.Frame(row, bg=BG)
        field_row.pack(fill="x")

        tk.Entry(
            field_row,
            textvariable=self._output_dir,
            font=FONT_BODY,
            bg=SURFACE,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
        ).pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))

        tk.Button(
            field_row,
            text="Browse",
            font=FONT_BODY,
            bg=SURFACE,
            fg=TEXT_PRIMARY,
            activebackground=ACCENT,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=10,
            pady=6,
            cursor="hand2",
            command=self._browse_output,
        ).pack(side="left")

    def _build_cookies_row(self, parent: tk.Frame) -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(0, 14))

        tk.Label(
            row,
            text="cookies.txt  (optional — YouTube Premium)",
            font=FONT_LABEL,
            bg=BG,
            fg=TEXT_MUTED,
        ).pack(anchor="w")

        field_row = tk.Frame(row, bg=BG)
        field_row.pack(fill="x")

        tk.Entry(
            field_row,
            textvariable=self._cookies_path,
            font=FONT_BODY,
            bg=SURFACE,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
        ).pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))

        tk.Button(
            field_row,
            text="Browse",
            font=FONT_BODY,
            bg=SURFACE,
            fg=TEXT_PRIMARY,
            activebackground=ACCENT,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=10,
            pady=6,
            cursor="hand2",
            command=self._browse_cookies,
        ).pack(side="left")

    def _build_progress_row(self, parent: tk.Frame) -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(0, 10))

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure(
            "Ripper.Horizontal.TProgressbar",
            troughcolor=PROGRESS_BG,
            background=ACCENT,
            thickness=10,
            bordercolor=PROGRESS_BG,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
        )

        self._progress_bar = ttk.Progressbar(
            row,
            variable=self._progress_value,
            maximum=100,
            mode="determinate",
            style="Ripper.Horizontal.TProgressbar",
        )
        self._progress_bar.pack(fill="x", pady=(0, 6))

        self._status_label = tk.Label(
            row,
            textvariable=self._status_text,
            font=FONT_SMALL,
            bg=BG,
            fg=TEXT_MUTED,
            anchor="w",
        )
        self._status_label.pack(anchor="w")

    def _build_download_button(self, parent: tk.Frame) -> None:
        self._download_btn = tk.Button(
            parent,
            text="Download",
            font=("Segoe UI", 11, "bold"),
            bg=ACCENT,
            fg="#ffffff",
            activebackground=ACCENT_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=0,
            pady=12,
            cursor="hand2",
            command=self._start_download,
        )
        self._download_btn.pack(fill="x", pady=(0, 4))

    # ------------------------------------------------------------------
    # Style helpers
    # ------------------------------------------------------------------

    def _apply_styles(self) -> None:
        """Post-build style tweaks that require widget references."""
        self._url_entry.config(highlightthickness=1, highlightbackground=SURFACE, highlightcolor=ACCENT)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _fetch_info(self) -> None:
        url = self._url_var.get().strip()
        if not url:
            mb.showwarning("No URL", "Please enter a YouTube URL first.")
            return

        self._set_status("Fetching video info...")
        self._fetch_btn.config(state="disabled")

        def _do_fetch() -> None:
            try:
                cookies = self._cookies_path.get().strip() or None
                meta = fetch_metadata(url, cookies_file=cookies)
                self.after(0, lambda: self._on_metadata(meta))
            except Exception as exc:
                self.after(0, lambda: self._on_fetch_error(exc))

        threading.Thread(target=_do_fetch, daemon=True).start()

    def _on_metadata(self, meta: dict) -> None:
        self._fetch_btn.config(state="normal")
        self._title_label.config(text=meta["title"])

        duration = meta["duration_seconds"]
        mins, secs = divmod(int(duration), 60)
        self._duration_label.config(text=f"Duration: {mins}m {secs:02d}s")
        self._resolution_label.config(text=f"Best quality: {meta['best_resolution']}")

        # Enable/disable caption options based on availability
        has_subs = meta.get("has_subtitles", False)
        for rb in self._caption_radios[1:]:  # index 0 is "No Captions" — always enabled
            rb.config(state="normal" if has_subs else "disabled")
        if not has_subs:
            self._caption_mode.set(CAPTION_NONE)
            self._no_subs_label.config(text="No captions available for this video.")
        else:
            self._no_subs_label.config(text="")

        self._set_status("Ready to download.")

        # Load thumbnail in background
        thumb_url = meta.get("thumbnail_url", "")
        if thumb_url:
            threading.Thread(target=self._load_thumbnail, args=(thumb_url,), daemon=True).start()

    def _on_fetch_error(self, exc: Exception) -> None:
        self._fetch_btn.config(state="normal")
        self._set_status("Error fetching info.")
        mb.showerror(
            "Could not fetch video",
            f"mp4-ripper could not retrieve video information.\n\n{_friendly_error(exc)}",
        )

    def _load_thumbnail(self, url: str) -> None:
        try:
            with urlopen(url, timeout=10) as resp:
                data = resp.read()
            img = Image.open(io.BytesIO(data))
            img.thumbnail(THUMB_SIZE, Image.LANCZOS)

            # Pad to exact size with BG colour so the panel stays stable
            padded = Image.new("RGB", THUMB_SIZE, color=(42, 42, 62))
            offset = ((THUMB_SIZE[0] - img.width) // 2, (THUMB_SIZE[1] - img.height) // 2)
            padded.paste(img, offset)

            photo = ImageTk.PhotoImage(padded)
            self.after(0, lambda: self._set_thumbnail(photo))
        except Exception:
            pass  # Thumbnail failure is non-fatal

    def _set_thumbnail(self, photo: ImageTk.PhotoImage) -> None:
        self._thumb_image = photo  # Keep a reference to prevent GC
        self._thumb_label.config(image=photo, text="")

    def _browse_output(self) -> None:
        chosen = fd.askdirectory(title="Select Output Folder", initialdir=self._output_dir.get())
        if chosen:
            self._output_dir.set(chosen)

    def _browse_cookies(self) -> None:
        chosen = fd.askopenfilename(
            title="Select cookies.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if chosen:
            self._cookies_path.set(chosen)

    def _start_download(self) -> None:
        if self._downloading:
            return

        url = self._url_var.get().strip()
        if not url:
            mb.showwarning("No URL", "Please enter a YouTube URL first.")
            return

        if not self._ffmpeg_ok:
            mb.showerror(
                "FFmpeg Not Found",
                "FFmpeg is required but was not found on your system PATH.\n\n"
                "Please install FFmpeg and ensure it is accessible from the command line.\n"
                "See the README for installation instructions.",
            )
            return

        caption_mode = self._caption_mode.get()
        output_dir = self._output_dir.get().strip() or DEFAULT_OUTPUT_DIR
        cookies = self._cookies_path.get().strip() or None

        self._downloading = True
        self._download_btn.config(state="disabled")
        self._progress_value.set(0.0)
        self._set_status("Starting download...")

        download_in_thread(
            url=url,
            output_dir=output_dir,
            caption_mode=caption_mode,
            cookies_file=cookies,
            progress_callback=self._on_progress,
            status_callback=self._on_status_update,
            done_callback=self._on_done,
        )

    def _on_progress(self, pct: float) -> None:
        self.after(0, lambda: self._progress_value.set(pct))

    def _on_status_update(self, msg: str) -> None:
        self.after(0, lambda: self._set_status(msg))

    def _on_done(self, exc: Optional[Exception]) -> None:
        self._downloading = False
        self.after(0, lambda: self._download_btn.config(state="normal"))
        if exc is None:
            self.after(0, lambda: self._progress_value.set(100.0))
            self.after(0, lambda: self._set_status("Done — file saved to output folder."))
            self.after(0, lambda: self._status_label.config(fg=SUCCESS))
        else:
            self.after(0, lambda: self._set_status("Download failed."))
            self.after(0, lambda: self._status_label.config(fg=ERROR_COLOR))
            self.after(
                0,
                lambda: mb.showerror(
                    "Download Failed",
                    f"The download did not complete.\n\n{_friendly_error(exc)}",
                ),
            )

    def _set_status(self, msg: str) -> None:
        self._status_text.set(msg)
        self._status_label.config(fg=TEXT_MUTED)


# ---------------------------------------------------------------------------
# Error formatting
# ---------------------------------------------------------------------------

def _friendly_error(exc: Exception) -> str:
    """Return a user-readable version of a yt-dlp or runtime exception."""
    msg = str(exc)

    if "HTTP Error 403" in msg or "Forbidden" in msg:
        return "Access denied by YouTube (HTTP 403). Try providing a cookies.txt file for YouTube Premium auth."
    if "Video unavailable" in msg or "Private video" in msg:
        return "This video is unavailable or private."
    if "No such file or directory" in msg and "ffmpeg" in msg.lower():
        return "FFmpeg could not be found. Please install it and ensure it is on your system PATH."
    if len(msg) > 300:
        return msg[:300] + "…"
    return msg


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = Mp4RipperApp()
    app.mainloop()
