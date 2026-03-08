# LOCAL_LOG.md — mp4-ripper

__Project:__ mp4-ripper
__Team Lead:__ Cap
__Stack:__ Python 3.10+ · yt-dlp · FFmpeg · Tkinter
__Started:__ 2026-03-07

---

## Stage 1 — Scope & Design (2026-03-07)

### Kickoff

Product Owner requested a cross-platform desktop app to download YouTube videos to local MP4, with audio, optional captions, and a simple URL-entry UI. Key requirements captured in `owner.txt`.

### Architectural Decisions

- __Stack chosen:__ Python + yt-dlp + FFmpeg + Tkinter.
  - Rationale: yt-dlp is the gold standard for YouTube downloads with audio merge, caption support, and Premium cookie passthrough. Tkinter ships with Python — zero extra GUI framework install for the user. FFmpeg handles audio/video merging and subtitle burning natively.
- __Caption tri-state design:__ Product Owner confirmed three modes — No Captions, SRT File (soft subtitles), Burned In (FFmpeg hardcode). This gives maximum flexibility across different players and sharing contexts.
- __YouTube Premium auth:__ cookies.txt (Netscape format) passthrough via yt-dlp's `cookiefile` option. No stored passwords. User exports cookies from browser.
- __Threading strategy:__ Download runs in a background thread; GUI updates via Tkinter's `after()` polling pattern to keep the UI non-blocking.
- __FFmpeg check at startup:__ App will verify FFmpeg is on PATH before the user attempts a download, surfacing a clean error rather than a raw subprocess traceback.

### Phase 1 Deliverables Completed

- Project folder structure created (`src/`, `assets/`)
- `requirements.txt` written
- `README.md` written — includes full cross-platform "To Run" section, cookies.txt instructions, caption mode explanation table
- `LICENSE.md` written (ISC)
- `LOCAL_LOG.md` initialized (this file)

---

## Stage 2 — Development & Testing (2026-03-07)

### Phase 2 — Download Engine (Nexus)

- `src/downloader.py` written — yt-dlp wrapper with full tri-state caption logic, cookies.txt passthrough, progress hook, and background thread helper.
- __Burned subtitle bug caught and fixed:__ Initial draft used `FFmpegEmbedSubtitle` postprocessor, which only soft-embeds subtitles (toggleable). Replaced with a manual FFmpeg pass using `subprocess.run` with `cwd=` set to the output directory. This avoids Windows drive-letter colon escaping issues in the FFmpeg `subtitles=` filter — a known cross-platform landmine.
- __Progress hook nuance:__ Hook reports 90% on `finished` (file written, FFmpeg merge still possible). 100% is only set after all post-processing (including subtitle burn) is confirmed complete.
- __SRT file discovery:__ yt-dlp saves subtitle files as `<title>.<lang>.srt`. After download, burned mode uses `glob` to find the first `.*.srt` match alongside the `.mp4`. Gracefully skips burn if no subtitle file found.

### Phase 3 — GUI (Stella)

- `src/app.py` written — single-screen Tkinter app with dark theme (Catppuccin-inspired palette).
- Thumbnail loaded via `urllib.request` + `Pillow` in a background thread; padded to fixed `320x180` canvas so the panel never shifts on load.
- Download runs in a daemon thread; all GUI updates routed through `self.after(0, ...)` — no cross-thread Tkinter writes.
- FFmpeg presence checked once at startup (`check_ffmpeg()`); blocks Download button with a clear error message if missing.
- Status label changes colour on success (green) / failure (red).

### Phase 4 — Integration

- All GUI events wired to downloader callbacks.
- URL validation fires on both Enter key and Fetch Info button.
- Download button disabled for duration of active download; re-enabled on completion or error.

### Phase 5 — QA (Vera)

- Syntax check: both `src/app.py` and `src/downloader.py` parse clean (`ast.parse`).
- Import audit: all stdlib imports verified; third-party (`yt-dlp`, `Pillow`) confirmed in `requirements.txt`; `requests` included for forward compatibility.
- File tree verified: all deliverables present.

## Known Limitations / Future Work

- Caption language is hardcoded to English (`en`) with auto-generated subtitle fallback. A language selector could be added in a future iteration.
- No download queue — single URL at a time by design (Product Owner requested "super simple").
- `requests` is in `requirements.txt` but not yet used directly — available for future thumbnail or metadata enrichment without a new install step.

---

## Stage 3 — Retro (2026-03-07)

### Retrospective Complete

- Team retro written and Product Owner comments incorporated: `.agents/retros/2026-03-07-mp4-ripper_TEAM_RETRO.md`
- 6 learnings extracted: `.agents/learnings/2026-03-07-mp4-ripper.md`
- Retro summary written: `.agents/retros/2026-03-07-mp4-ripper.md`
- README updated with VLC recommendation for Windows SRT playback and Troubleshooting section
- TASK_LIST.md checked off

### Key Learnings Summary

- __L1:__ yt-dlp silently embeds subtitles during merge — always use a separate `skip_download=True` pass for standalone `.srt` files
- __L2:__ YouTube auto-captions require a three-pass SRT cleaner (prefix drop → same-timestamp merge → overlap trim)
- __L3:__ FFmpeg `subtitles=` filter breaks on Windows drive-letter colons — use `cwd=` workaround
- __L4:__ Startup dependency checks beat runtime error handling for external CLI tools
- __L5:__ Windows 11 Media Player v11 ≠ WMP 12 — VLC is the correct reference player for SRT
- __L6:__ Tkinter requires `after(0, ...)` for all background thread GUI updates

### Product Owner Sign-off

Rudi (Product Owner) confirmed the app solved a year-deferred problem, completed within a single session including all testing and tweaks. First Windows 11 / VS Code extension session for this project — confirmed flawless.
