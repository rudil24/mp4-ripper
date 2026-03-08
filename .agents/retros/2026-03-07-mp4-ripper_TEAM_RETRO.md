# Team Retro — mp4-ripper

__Date:__ 2026-03-07
__Project:__ mp4-ripper
__Stack:__ Python 3.10 · yt-dlp · FFmpeg · Tkinter
__Team:__ Cap (Team Lead/Architect), Nexus (Integration), Stella (UI/Frontend), Vera (QA)

---

## What went well

__Cap (Team Lead/Architect):__

- Stack selection was correct first time. Python + yt-dlp + Tkinter required zero backtracking — the whole scaffold went up cleanly and the Product Owner had a working download on the first run.
- Review-driven planning (TASK_LIST.md before any code) paid off. The tri-state caption design decision was confirmed by the Product Owner before implementation, saving a rework cycle.
- The decision to separate the subtitle fetch into its own yt-dlp pass (decoupled from the video/audio merge) was architecturally sound and directly solved the auto-embed bug.

__Nexus (API/Integration):__

- yt-dlp's `cookiefile` passthrough for YouTube Premium worked transparently — no credential storage, no OAuth complexity.
- `download_in_thread` with callback pattern kept the engine completely decoupled from the GUI. The downloader module has zero Tkinter imports — clean separation of concerns.
- The `cwd=` trick for FFmpeg subprocess calls elegantly sidestepped Windows drive-letter colon escaping in the `subtitles=` filter without any platform-specific branching.

__Stella (UI/Frontend):__

- Dark theme (Catppuccin-inspired) rendered well out of the box on Windows 11. Product Owner confirmed visual quality immediately.
- Fixed-size thumbnail canvas (`320x180` padded) prevented layout jitter on thumbnail load — a small detail that makes the UI feel polished.
- Caption radio disable/enable with the "No captions available" note was well-received — proactive UX rather than a silent failure.

__Vera (QA/DevOps):__

- Real-world testing (two actual YouTube videos) caught issues that no synthetic test would have surfaced: the SRT auto-embed bug, the rolling-word caption stacking bug, and the Windows Media Player SRT compatibility gap.
- The multi-pass `_clean_srt` function was validated against actual YouTube auto-caption output and confirmed working in VLC.
- Startup FFmpeg presence check prevented a confusing mid-download failure mode.

__Rudi (Owner):__

- This is the perfect example of why i built this team. This is an app I've been putting off for a year, because i manually downloaded yt-dlp but couldn't get it to give me video and audio together and couldn't figure it out from the github repo instructions. So i moved to other things. I give it to you guys and you NAILED it within 30 minutes, with all testing and tweaks.
- Also this was my first time using Claude on my Windows 11 workstation, (I'm macos mostly but for some projects and utilities i need them on this virtual pinball windows machine!) and it was also flawless within the VS Code extension, and very helpful with Powershell commands instead of bash.

---

## What went wrong

__Cap (Team Lead/Architect):__

- Window height (720x620) was too short, cutting off the Download button on first launch. Should have added a safety margin or used `pack` with a scrollable frame from the start.
- The initial SRT implementation assumed yt-dlp would write subtitle files separately during the merge pass. It doesn't — it silently embeds them. Required a second pass architecture to fix.

__Nexus (API/Integration):__

- First `_burn_subtitles` used `FFmpegEmbedSubtitle` postprocessor, which only soft-embeds (not burns). The distinction between soft-embed and hardcode burn was not checked before implementation.
- First `_clean_srt` only handled the prefix rolling-word pattern. Same-timestamp grouping and overlap trimming were missed, requiring a second revision after live testing revealed stacking still occurred.

__Stella (UI/Frontend):__

- No explicit handling for the case where the app launches without any video loaded — caption radio buttons start enabled with no context. Minor UX issue (low risk since downloading without a URL is already guarded).

__Vera (QA/DevOps):__

- `yt-dlp` is not on the system PATH when installed via `pip` — `python -m yt_dlp` is required for CLI diagnostics. Should be noted in the README troubleshooting section.
- Windows Media Player (v11, the new Windows 11 app) does not reliably support external SRT files. VLC is required. This should be called out explicitly in the README caption mode table.

__Rudi (Owner):__

- nothing wrong, the few things that we uncovered we worked through together. 
---

## What did we discover

__Cap (Team Lead/Architect):__

- yt-dlp's merge pass will silently absorb subtitle files into the MP4 container if subtitle flags are set alongside `merge_output_format`. The only reliable way to get a standalone `.srt` is a separate `skip_download=True` pass.
- The new Windows 11 Media Player app (v11.x) is a different application from the classic WMP 12. Online documentation conflates the two. For SRT soft-subtitle testing, VLC is the correct reference player.

__Nexus (API/Integration):__

- YouTube auto-captions arrive in two distinct messy formats: (1) rolling-word prefix chains, and (2) same-timestamp multi-line blocks. Both must be handled to produce clean burned-in subtitles. A three-pass cleaner (prefix drop → same-timestamp merge → overlap trim) covers both patterns.
- FFmpeg's `subtitles=` filter has a hard constraint on Windows: any colon in the path (including drive letters like `C:`) breaks the filter syntax. The `cwd=` workaround (set working directory to the file's parent, use just the filename) is the cross-platform solution.

__Stella (UI/Frontend):__

- Tkinter's `after(0, lambda: ...)` pattern is the correct and only safe way to update GUI state from a background thread. All download callbacks must route through this — direct widget updates from threads cause silent corruption.

__Vera (QA/DevOps):__

- For desktop tools with external subprocess dependencies (FFmpeg, yt-dlp), startup dependency checks are more valuable than runtime error handling. Catching a missing FFmpeg at launch with a clear human-readable message is far better UX than a cryptic subprocess traceback mid-download.

__Rudi (Owner):__

- Never knew about the separate .srt captioning, that was great learning given by the team to me. 
---

## Product Owner Comments

_(Awaiting your review — please add any comments below each section above, or reply here and I'll incorporate them.)

- comments incorporated inline above -RL
