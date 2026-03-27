# GitHub repository settings

Apply these in the repo admin UI (needs **Owner** or **Admin**). This file is documentation; it does not change settings by itself.

## Branch protection (`main`)

**Settings → Rules → Rulesets** (or **Branches → Branch protection rules** on older UIs):

- Require a pull request before merging.
- Require status checks to pass: CI workflow (`test` or equivalent).
- Require branches to be up to date before merging (optional but recommended).
- Do not allow bypassing the above for admins (optional, stricter teams).
- Restrict who can push to matching branches: no direct pushes to `main` if everything goes through PRs.

## Dependabot

**Settings → Code security and analysis**

- Enable **Dependabot alerts** (and **Dependabot security updates** if available).
- Dependabot version updates are configured in [`.github/dependabot.yml`](../.github/dependabot.yml).

## Secret scanning

If the repo is **public** or **GitHub Advanced Security** is enabled:

- **Secret scanning** → enable push protection where possible.

## Tags and releases

- Create a **signed** annotated tag (`git tag -s v0.1.0`) if you use a GPG or SSH signing key; otherwise lightweight tags are fine for personal projects.
- Prefer **GitHub Releases** attached to tags; attach the `.zip` built by CI or a local `./scripts/build_mac_app.sh` run.

## Two-factor authentication

- Org/account **2FA** should be on for anyone who can push or publish releases.
