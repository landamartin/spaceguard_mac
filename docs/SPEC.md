# SpaceGuard — product specification

## Purpose

SpaceGuard is a macOS menu bar utility that:

- Monitors **free disk space** on the root volume (`/`) and **swap usage** via `sysctl vm.swapusage`.
- Shows a **color-coded tray icon** (OK / warning / critical).
- Optionally prompts the user to run a **safe cleanup** of selected cache locations when thresholds are exceeded, with **debouncing** to avoid spam.
- Persists all settings under `~/Library/Application Support/SpaceGuard/settings.json`.

## Non-goals (v1)

- Per-process disk write monitoring, Time Machine / APFS snapshot management, Mac App Store sandboxing.

## Defaults

| Setting | Default |
|--------|---------|
| Disk warning | Free space &lt; **1.0 GB** |
| Disk critical | Free space &lt; **0.5 GB** |
| Swap warning | Used &gt; **500 MB** |
| Swap critical | Used &gt; **1000 MB** |
| Poll interval | **45 s** |
| Consecutive checks before prompt | **2** |
| Minimum time between prompts | **10 min** |
| Cooldown after **Ignore** | **45 min** |

## Tray indicator

Severity order (strongest wins):

1. **Critical** if free disk &lt; critical threshold **or** swap &gt; critical threshold.
2. Else **Warning** if free disk &lt; warning threshold **or** swap &gt; warning threshold.
3. Else **OK**.

If swap cannot be parsed, swap-based thresholds are ignored for severity (fail-safe: no false critical from swap).

## Alert / prompt logic

A **pressure** condition is active when:

- Disk triggers are enabled and free GB &lt; disk **warning** threshold, or
- Swap triggers are enabled and swap MB &gt; swap **warning** threshold.

A **prompt** (modal dialog or tray notification only — see settings) may be shown when:

- Pressure is active for **N** consecutive timer ticks (default **2**), and
- Not within **ignore cooldown** after the user dismissed a prompt, and
- Not within the global **prompt cooldown** since the last prompt.

When a prompt is scheduled, the app records the prompt **before** showing UI so repeated timer ticks do not open multiple dialogs.

## Cleanup

- Preset targets include global caches, logs, optional browser profile cache dirs, common IDE caches, and selected Electron app caches. Each preset can be toggled.
- **Custom paths** must resolve under the user’s home directory; obvious system roots are rejected.
- **Optional “restart noisy daemons”** (`analyticsd`, `searchpartyd`) is **not** run during automatic cleanup. It is available as a **manual** action that requests an administrator password via AppleScript (`osascript`).

## Permissions

- Runs as the logged-in user; deletes only paths the user can write.
- Admin password is requested **only** for the optional daemon restart action.
- Full Disk Access is generally **not** required for typical `~/Library/...` cache paths; document any OS-specific restrictions in release notes if they appear.

## Packaging

- Development: `uv run python -m spaceguard`.
- Distribution: Nuitka standalone `.app` (see `scripts/build_mac_app.sh` and `README.md`).
- **Start at login** uses a **Launch Agent** plist (`com.spaceguard.mac`) installed into `~/Library/LaunchAgents/`.

## Multi-volume note

Disk free space uses the volume containing `/`. External volumes are out of scope for v1.
