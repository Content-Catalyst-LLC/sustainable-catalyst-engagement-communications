# MEDIA-02 — WordPress public Media site acceptance package

Build date: 2026-11-07 (America/Chicago)  
Package: `sustainable-catalyst-media-wordpress-MEDIA-02-v8.8.6.zip`  
Version: **8.8.6**  
ZIP size: 18,543 bytes  
SHA-256: `936b6fd070feba374bdb38f18cc03640d6c0b59b1d5b98a69fedd4072b5ca847`

## Included
- Base v8.8.5 Media hub: Substack, YouTube, LinkedIn, social channels, public WordPress news and inquiries.
- Readiness diagnostics under **WordPress → Settings → Media & Communications**.
- Opt-in legacy 301 redirects from exact `/press/` and `/channel/` to published `/media/`.
- No redirects when source page exists or target is missing, unpublished, password-protected or lacks a Media shortcode.
- Existing shortcodes and channel settings retained; no migration/DB changes.

## Local verification
- PHP syntax: **PASS** — No syntax errors detected in /mnt/data/media02-build/sustainable-catalyst-engagement-communications/sustainable-catalyst-engagement-communications.php
- JavaScript syntax: **PASS**
- ZIP integrity: **PASS**
- Synthetic WordPress smoke and MEDIA-02 acceptance: **PASS** (78 individual expectations)
- Public WordPress signed-out acceptance: **NOT PERFORMED** — server/browser environment inaccessible.
- Live CDN/HTTP 301 acceptance: **NOT PERFORMED** — redirects are off by default.

## Install and acceptance
See `INSTALLATION.txt` and `MEDIA-02-RELEASE.md` in the ZIP. Back up the current plugin first.

## Rollback
Uncheck **Redirect old Press / Channel URLs** in Settings → Media & Communications, restore prior plugin ZIP and WordPress page/menu backup if needed, then purge caches. No automatic WordPress content changes occur.

## Scope exclusions
No linked account authorization, live newsletter distribution, sending, Substack/YouTube/LinkedIn autoposting, subscriber tracking, private API access, or Research/Workspace identity bridging.
