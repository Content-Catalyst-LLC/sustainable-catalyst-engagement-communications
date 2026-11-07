# Handoff — Engagement & Communications → Press product identity (not yet a technical rename)

**Date:** 2026-11-07
**Status:** Owner-approved product architecture; implementation planning **only**. No production cutover.
**Canonical platform decision:** [Product boundaries — Publications / Press / Research / Library / Workspace](https://github.com/Content-Catalyst-LLC/sustainable-catalyst-platform-core/blob/main/docs/PRODUCT-BOUNDARIES-PUBLICATIONS-PRESS-RESEARCH-2026-11-07.md)

## Summary

The **Publications** section of Sustainable Catalyst is the **existing WordPress editorial blog/article publishing surface**. The **Press** concept is the public-facing name for the present **Engagement & Communications** system, emphasizing newsroom, announcements, media relations, press kits, outreach, newsletters and institutional communications. These are distinct from Research's scientific production and Library's source management.

Do **not** rename or redeploy this repository now. Preserve `Content-Catalyst-LLC/sustainable-catalyst-engagement-communications`, existing API paths, WordPress plugin slugs, service identities, DB migrations, flags and source/version history until an explicitly approved, reversible migration exists.

## Existing SCEC capabilities to retain, not duplicate

- Institutional newsroom, media relations, press outreach and editorial planning.
- Communications objects, reviewed content lineage, newsroom and release planning.
- Newsletter/alert previews, audience and campaign planning, events and outreach.
- Privacy, consent, suppression, embargo, review and tenant-authority gates.
- Existing WordPress bridge and standalone UI foundation as they currently exist.

Existing v12.2 and related code are largely **default-off synthetic/staging preview capabilities**; do not imply that real mailing, contacts, production publishing or human SSO are activated. Privacy and production authorization gates remain authoritative.

## New product boundary

| Operation | Owner |
| --- | --- |
| Write/edit/schedule/publish blog posts and public editorial articles | **WordPress Publications** |
| Manage research investigation, paper, supporting calculations and scientific finding versions | **Research** (with native authorized source services) |
| Discover and retain cited papers, datasets, bibliographies and provenance | **Library** |
| Coordinate people, deliverables, milestones, approvals and project state | **Workspace** |
| Author/review press releases, media pitches, press announcements, press kit and newsletter/channel distribution plans | **Press** (existing Engagement & Communications code) |
| Capture support tickets, private contact forms and feedback | Existing **Support/Engagement Intake/Feedback** ownership; explicit privacy-reviewed bridges only |

## Integration handoff contract: conceptual, not implemented

1. Research or WordPress Publications supplies a versioned, approved public record reference; Press stores the reference and its release/rights metadata, **not a copied private manuscript or shared password**.
2. Before any Press publication or distribution, check provenance, citation/claim consistency, approved version, reviewer signoff, embargo, rights/license and channel/audience/consent/suppression requirements.
3. Press output is a separately versioned communications artifact with a route back to the authoritative WordPress article or Research release.
4. Corrections and withdrawals trigger explicit review/remediation; no silent retroactive editing or automated message sending.
5. All links across products must obey tenant scope, existing identity authority, ownership checks, least-privilege and audit logging; no direct cross-database writes.

## Future implementation backlog (not authorization)

1. Inventory Engagement & Communications navigation labels, subdomains, WordPress menus, slugs, APIs, legacy contracts and externally linked URLs.
2. Produce a **Press** information architecture that preserves existing backend/module naming during transition.
3. Define Publications ↔ Press approved-content reference contract and approval history; do not replace WordPress as the editorial CMS.
4. Plan canonical identity and role mapping with Workspace/Research but preserve existing accounts until verified.
5. Run privacy, consent, tenant isolation, source-rights, embargo, rollback and external delivery acceptance before any public label changes or sending.

## Release gate

This handoff does not activate staging flags, real contact processing, distribution, email delivery, public releases, service cutovers, URL moves, Caddy or WordPress changes. **Human review and explicit owner deployment approval are required for each later release.**
