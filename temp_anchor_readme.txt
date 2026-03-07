=== README.md Content ===
# reproducible-self-pub-kit

## Source of truth
Canonical workflow, paths, and rules live in **ANCHOR.md**.

If anything disagrees with `ANCHOR.md`, update `ANCHOR.md` first, then fix reality to match.

---

## Git workflow (new user guidance)

### Quick daily commands
~~~powershell
git status -sb
git pull --ff-only
git add -A
git commit -m "Describe your change"
git push
=== ANCHOR.md Content ===
# Reproducible Self‑Pub Kit — Anchor (Ground Truth)

> This repo exists because **drift is the default**—and reproducibility is a feature you have to build on purpose.
>
> I spoke in token words; the build replied in tears.  
> Coding Club: **no drift, no leaks.**

Last updated: 2026-03-04  
Owner machine: Windows (PowerShell 7.x, pwsh)  
Verified on owner machine: PowerShell 7.5.4  
Repo: https://github.com/tonefreqhz/reproducible-self-pub-kit  
Branch: main

---

## 0) What this file is (and is not)
This ANCHOR is the **single source of truth** for: repo layout, commands, verified toolchain, and “good state” checks.

- If anything disagrees with this file, **update this file first**, then fix reality to match.
- Standardize Markdown code fences to `~~~` in this repo.
- PowerShell note: do **not** use `<like-this>` placeholders in runnable commands (PowerShell parses `<` and `>` as redirection).
- **Terminal safety:** Only paste lines inside `~~~powershell` fences into PowerShell. Everything else is documentation.

---

## Command sequences must start from repo root (anti-drift)
Every runnable command sequence in this repo must begin by changing directory to **PROJECT_ROOT** (repo root).  
Do not assume the current shell location; drift starts there.

Canonical on owner machine:

~~~powershell
cd "$HOME\OneDrive\Desktop\reproducible-self-pub-kit"
~~~

Sanity checks:

~~~powershell
pwd
git rev-parse --show-toplevel
~~~

Stop if `git rev-parse --show-toplevel` does not resolve to the repo you intend.

---

## 1) Machine + repo ground truth
- Owner machine: Windows (PowerShell 7.x, pwsh)
- Verified on owner machine: PowerShell 7.5.4
- Repo: https://github.com/tonefreqhz/reproducible-self-pub-kit
- Branch: `main`
- Repo root (owner machine): `C:\Users\peewe\OneDrive\Desktop\reproducible-self-pub-kit`

### Toolchain verification (must be PowerShell 7.x)
Run these in the repo root to confirm you are using **PowerShell 7.x (pwsh)** and not Windows PowerShell 5.1.

~~~powershell
cd "$HOME\OneDrive\Desktop\reproducible-self-pub-kit"
$PSVersionTable.PSVersion
(Get-Process -Id $PID).Path
~~~

### Repo root must match exactly (anti-drift)
If the folder is suffixed (example: `.old`), rename it back to the canonical root:

~~~powershell
cd "$HOME\OneDrive\Desktop"
Rename-Item "reproducible-self-pub-kit.old" "reproducible-self-pub-kit"
~~~
