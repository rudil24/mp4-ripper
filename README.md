# mp4-ripper

A simple cross-platform desktop app to download YouTube videos as MP4 files — with audio, optional captions, and automatic quality selection.

Built with Python, yt-dlp, FFmpeg, and Tkinter.

---

## Features

- Paste a YouTube URL and preview the video title, thumbnail, duration, and best available resolution
- Downloads video and audio merged into a single `.mp4` file
- Auto quality selection: best available (1080p → 720p → highest available)
- Tri-state caption mode:
  - __No Captions__ — video only
  - __SRT File__ — downloads a `.srt` subtitle file alongside the `.mp4` (toggle in any standard player)
  - __Burned In__ — hardcodes subtitles directly into the video stream via FFmpeg
- YouTube Premium support via `cookies.txt` passthrough
- Choose your output folder
- Progress bar and status feedback

---

## Pre-requisites

You must have the following installed on your system before running mp4-ripper.

### 1. Python 3.10 or newer

| Platform | Instructions |
|---|---|
| Windows | Download from [python.org](https://www.python.org/downloads/). Check "Add Python to PATH" during install. |
| macOS | `brew install python` or download from [python.org](https://www.python.org/downloads/). |
| Linux | `sudo apt install python3 python3-pip` (Debian/Ubuntu) or equivalent for your distro. |

Verify: `python --version` (Windows) or `python3 --version` (macOS/Linux)

### 2. FFmpeg (must be on system PATH)

FFmpeg handles audio/video merging and subtitle burning.

| Platform | Instructions |
|---|---|
| Windows | Download a build from [ffmpeg.org](https://ffmpeg.org/download.html). Extract and add the `bin/` folder to your system PATH. |
| macOS | `brew install ffmpeg` |
| Linux | `sudo apt install ffmpeg` (Debian/Ubuntu) or equivalent. |

Verify: `ffmpeg -version`

---

## To Run

### Step 1 — Clone or download this repository

```bash
git clone https://github.com/youruser/mp4-ripper.git
cd mp4-ripper
```

Or download the ZIP and extract it.

### Step 2 — Install Python dependencies

```bash
# Windows
pip install -r requirements.txt

# macOS / Linux
pip3 install -r requirements.txt
```

### Step 3 — Launch the app

```bash
# Windows
python src/app.py

# macOS / Linux
python3 src/app.py
```

The app window will open. Paste a YouTube URL, choose your caption mode, and click Download.

### Troubleshooting

- __`yt-dlp` not recognized as a command:__ It's installed as a Python package, not a standalone CLI. Use `python -m yt_dlp` for any command-line diagnostics (e.g., `python -m yt_dlp --list-subs <url>`).
- __FFmpeg not found:__ The app checks for FFmpeg at startup and will show a clear error. See the FFmpeg install instructions above and ensure the `bin/` folder is on your system PATH.
- __Cookies expired:__ If a download fails with an auth error, re-export your `cookies.txt` from the browser extension and re-select it in the app.

---

## YouTube Premium (optional)

If you are a YouTube Premium subscriber and want to download ad-free or access Premium-only content, you can provide a `cookies.txt` file.

### How to export your cookies

1. Install the browser extension __"Get cookies.txt LOCALLY"__ (available for Chrome and Firefox).
2. Log in to YouTube in your browser.
3. Click the extension and export cookies for `youtube.com` in __Netscape format__.
4. Save the file somewhere accessible (e.g., `~/cookies.txt`).

### How to use it in mp4-ripper

In the app, click __Browse__ next to the "cookies.txt (optional)" field and select your exported file.

> Note: Cookies expire. If downloads fail with an authentication error, re-export your cookies.

---

## Caption Modes Explained

| Mode | What it does | Best for |
|---|---|---|
| No Captions | Downloads video + audio only | General use |
| SRT File | Downloads a `.srt` subtitle file alongside the `.mp4` | VLC (recommended), Plex, and most desktop players — captions can be toggled on/off |
| Burned In | Uses FFmpeg to permanently embed captions into the video | Sharing the file, or players that don't support external subtitles |

> __Windows users:__ The new Windows 11 Media Player app (v11) does not reliably support external `.srt` files. Use [VLC](https://www.videolan.org/vlc/) for SRT playback — it auto-detects the subtitle file when it shares the same name and folder as the video.

---

## Output

Downloaded files are saved to `~/Downloads/mp4-ripper/` by default. You can change this in the app before downloading.

---

## Links

- [TASK_LIST.md](TASK_LIST.md)
- [LOCAL_LOG.md](LOCAL_LOG.md)
- [LICENSE.md](LICENSE.md)

---

## Tech Stack

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — YouTube download engine
- [FFmpeg](https://ffmpeg.org/) — audio/video merging and subtitle burning
- [Tkinter](https://docs.python.org/3/library/tkinter.html) — GUI (included with Python)
- [Pillow](https://python-pillow.org/) — thumbnail image rendering
