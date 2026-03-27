# Security policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a vulnerability

Please **do not** open a public issue for security-sensitive reports.

Use [GitHub Security advisories](https://github.com/landamartin/spaceguard_mac/security/advisories/new) for this repository (private report to maintainers).

Include: affected version, steps to reproduce, impact, and suggested fix if you have one.

## Scope

SpaceGuard runs as your user, deletes only paths you configure, and uses the macOS admin prompt only for the optional “restart noisy daemons” action. It does not ship a sandboxed App Store build; treat it like any other developer tool you run locally.
