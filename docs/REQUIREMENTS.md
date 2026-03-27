# Requirements checklist (testable)

## Monitoring

- [ ] App reads free space for `/` and displays it in the tray tooltip.
- [ ] App reads swap used (MiB) from `sysctl vm.swapusage` when available.
- [ ] Tray icon reflects OK / warning / critical per `docs/SPEC.md`.

## Settings

- [ ] Settings persist to `~/Library/Application Support/SpaceGuard/settings.json` with atomic write.
- [ ] User can adjust disk/swap thresholds, enable/disable disk vs swap triggers, debounce timings, and cleanup presets.
- [ ] User can add/remove custom paths under home; invalid paths are rejected by validation rules in `cleanup.py`.

## Alerts

- [ ] No prompt spam: consecutive-check requirement + cooldowns enforced (`state.py`).
- [ ] “Notifications only” suppresses the modal cleanup prompt and shows a tray message instead.
- [ ] First-run welcome message is shown once (`_shown_welcome` in settings).

## Cleanup

- [ ] “Run cleanup” removes only enabled preset paths and existing custom paths; failures are summarized.
- [ ] Cleanup deletes files only (no process termination as part of cleanup).
- [ ] Optional daemon restart is manual and may prompt for admin password.

## Login item

- [ ] “Start at login” installs/removes Launch Agent plist and loads/unloads via `launchctl` where possible.

## Quality

- [ ] `pytest` passes for `monitor`, `state`, and `settings_store` (see `tests/`).
