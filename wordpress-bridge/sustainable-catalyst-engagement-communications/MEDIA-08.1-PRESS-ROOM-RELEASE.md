# MEDIA-08.1 Institutional Press Room completion: plugin 8.9.5 release candidate

Extends the existing MEDIA-08 Press Room (`SC_Media08_Press_Room`, `[sc_press_room]`). No second press or publication
system. Public release stays disabled until `SCEC_MEDIA08_PUBLIC_RELEASE` is set to `true` in wp-config **and** a
published `/press/` page contains `[sc_press_room]`.

## Reconciliation
| Source | Status | Accounted for in 8.9.5 |
|---|---|---|
| PR #24 Press renderer (8.8.3) | superseded | `render_press` / `[sc_press]` Media hub already in main; reused as the Press Room landing |
| PR #30 MEDIA-07 Newsletter Studio (8.9.1) | all commits in main | unchanged |
| PR #32 MEDIA-08 Press Room (8.9.2) | all commits in main | extended in place (this release) |
| PR #34 MEDIA-07.3 at `5f361a9` | **deployed build 8.9.3**, not in main | `media07-studio.php/.js` carried from `5f361a9` unchanged (staging bridge dormant unless configured) |
| PR #34 later Gate D commits (8.9.4) | not deployed, not in main | not included; remains its own review |
| MEDIA-09 (#36–#39) `[sc_press_inquiry]` | in main | preserved; inert unless `SCEC_MEDIA09_PRESS_URL` is defined |

Version 8.9.5 is above both the deployed 8.9.3 and the unmerged #34 candidate 8.9.4.

## What 8.9.5 adds
- **Permanent URLs** `/press/<year>/<slug>/` assigned once at release (word-boundary slug ≤ 80 chars, unique, never
  reassigned) and a release reference `SC-PR-<year>-<NNN>`.
- **SEO**: per-release `<title>`, description, canonical, robots, Open Graph (Rank Math filters when Rank Math is active,
  plain tags otherwise) and `NewsArticle` JSON-LD with `CorrectionComment` when corrected. Withdrawn releases are
  `noindex, follow` and carry no structured data.
- **Sitemap**: `/press/releases.xml` (released, not withdrawn), referenced from the Rank Math sitemap index. Not named
  `*-sitemap.xml`, which Rank Math's own rewrite rule would capture. Release actions invalidate Rank Math's index cache.
- **Corrections** are new records (`corrects` link) that go through the full submit → independent approval → release
  flow. On release the original shows a dated correction notice; its approved text is never changed.
- **Withdrawal** keeps the permanent URL with a dated public notice and reason; body hidden; removed from the sitemap.
- **History**: one append-only meta row per event (created, saved, submitted, returned, approved, released, corrected,
  correction_started, withdrawn) with UTC time, user and content SHA-256. Public pages show dated actions and the
  fingerprint, never user identities or internal notes.
- **Return to author**: a reviewer can send a submission back with a required note; the author's next save is a new revision.
- **Least-privilege reviewer role** `scec_press_reviewer` = `read` + `scec_press_review` only. Administrators receive
  `scec_press_author`, `scec_press_review`, `scec_press_publish`. The Press Room is a top-level admin menu
  (`admin.php?page=scec-media08`; the old Settings submenu URL is retired). The plugin defines the role; it never creates users.
- **Media page integration**: the Media hub "Press & News" card and the Press landing "Press Releases" card link to the
  Press Room only when it is launched (flag on and `/press/` published). Otherwise they keep "Not yet published".

## Unchanged guarantees
Content fingerprint definition (existing approvals stay valid); distinct author/reviewer at approval, release and every
public render; four reviewer attestations (rights, source integrity, privacy, institutional authority); strict UTC embargo
at release and render; any out-of-workflow edit to a released record removes it from public view; private, non-REST CPT;
no email, social, remote API or cross-posting.

## Tests
- `tests/media081-press-room-validation.php`: paths, references, fingerprint definition, role definition (CI).
- `tests/media081-wp-acceptance.php` + `tests/media081-staging-acceptance.sh`: **disposable staging only**. Real
  admin-post handlers, nonces and capabilities as an administrator author and a `scec_press_reviewer` user across
  phases private → gated → public → tamper → kill switch, plus anonymous HTTP checks. Refuses production.

## Operational notes
- Rewrite rules flush once per version on the first **web** request (never under WP-CLI, where Rank Math's sitemap
  rules are not registered).
- After changing the wp-config flag, allow for PHP opcache revalidation before verifying anonymously, then purge the page cache.
- Rollback: reinstall the previous plugin ZIP. Press records persist; with the flag unset nothing is public.
