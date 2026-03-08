# TASK_LIST.md — mp4-ripper

__Project:__ mp4-ripper
__Team Lead:__ Cap
__Stack:__ Python 3.10+ · yt-dlp · FFmpeg · Tkinter
__Status:__ Complete — Product Owner sign-off 2026-03-07

---

## Phase 1 — Project Scaffold

- [x] **T1.1** Create project folder structure (`src/`, `assets/`)
- [x] **T1.2** Write `requirements.txt` (yt-dlp, Pillow for thumbnail preview, requests)
- [x] **T1.3** Write `README.md` with full "To Run" section covering Windows, macOS, and Linux
- [x] **T1.4** Write `LICENSE.md` (ISC)
- [x] **T1.5** Initialize `LOCAL_LOG.md`

---

## Phase 2 — Core Download Engine (Nexus)

- [x] **T2.1** Create `src/downloader.py` — yt-dlp wrapper module
  - Fetch video metadata (title, duration, available formats/resolutions)
  - Auto-select best quality (1080p → 720p → best available) with audio merged
  - Output: single `.mp4` file with audio, saved to user-chosen output directory
- [x] **T2.2** Implement YouTube Premium support via `cookies.txt` passthrough
  - Accept path to `cookies.txt` (Netscape format, exported from browser)
  - Pass to yt-dlp's `cookiefile` option
  - Gracefully handle missing/expired cookie file
- [x] **T2.3** Implement tri-state caption mode:
  - __Mode 0 — No captions:__ Download video+audio only, no subtitle processing
  - __Mode 1 — SRT file:__ Download best available subtitle track as a separate `.srt` file alongside the `.mp4` (soft subtitles, toggled by any standard player)
  - __Mode 2 — Burned-in:__ Download subtitle track then invoke FFmpeg to hardcode subtitles into the video stream (permanent, player-agnostic)
- [x] **T2.4** Progress callback hook — expose download/merge progress as a numeric percentage for the GUI progress bar

---

## Phase 3 — GUI (Stella)

- [x] **T3.1** Create `src/app.py` — main Tkinter application entry point
- [x] **T3.2** URL entry bar with "Load" / "Fetch Info" button
- [x] **T3.3** Video preview panel — display thumbnail image, video title, duration, and detected best resolution
- [x] **T3.4** Caption mode selector — radio button tri-state: `No Captions` · `SRT File` · `Burned In`
- [x] **T3.5** Output folder selector — Browse button + current path display (defaults to `~/Downloads/mp4-ripper/`)
- [x] **T3.6** `cookies.txt` path input — optional field with Browse button and tooltip explaining its purpose
- [x] **T3.7** Download button + progress bar (0–100%) + status label (Idle / Fetching / Downloading / Merging subtitles / Done / Error)
- [x] **T3.8** Error display — surface yt-dlp and FFmpeg errors in a readable in-app message (no raw tracebacks shown to user)

---

## Phase 4 — Integration & Wiring

- [x] **T4.1** Wire GUI events to downloader module (non-blocking — run download in a background thread, update progress bar via `after()` polling)
- [x] **T4.2** Validate URL on "Load" click before fetching metadata
- [x] **T4.3** Disable Download button while a download is in progress; re-enable on completion or error
- [x] **T4.4** Confirm FFmpeg is installed and on PATH at startup; show a clear human-readable error if not found

---

## Phase 5 — QA & Polish (Vera)

- [x] **T5.1** Test all three caption modes end-to-end with a real URL
- [x] **T5.2** Test on Windows (primary), document macOS/Linux instructions
- [x] **T5.3** Test `cookies.txt` passthrough path (valid file, missing file, expired cookies)
- [x] **T5.4** Test invalid/private/unavailable URL error handling
- [x] **T5.5** Accessibility review — keyboard navigation, tab order, ARIA-equivalent labeling where Tkinter supports it
- [x] **T5.6** Write test coverage report in `LOCAL_LOG.md`

---

## Deliverables Checklist

- [x] `README.md` with "To Run" section (Windows, macOS, Linux)
- [x] `requirements.txt`
- [x] `LICENSE.md`
- [x] `LOCAL_LOG.md`
- [x] `src/app.py` (GUI entry point)
- [x] `src/downloader.py` (download engine)
- [x] Working download: video + audio merged, tri-state captions, Premium cookies support

---

## Pre-Execution Dependency Notes

The following must be present on the user's machine before running the app:

| Dependency | Install Method |
|---|---|
| Python 3.10+ | python.org or system package manager |
| FFmpeg | ffmpeg.org — must be on system PATH |
| pip packages | `pip install -r requirements.txt` |
| cookies.txt (optional) | Export from browser via "Get cookies.txt" extension |
