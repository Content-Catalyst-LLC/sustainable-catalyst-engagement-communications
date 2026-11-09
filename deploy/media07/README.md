# MEDIA-07 — Sustainable Catalyst Newsletter Studio (Substack-first)

**Decision updated 2026-11-08 by platform owner.** Primary newsletter sending stays in Substack for now. A paid/professional delivery service is an **optional future integration**, not a present deployment dependency.

**Implementation status:** Offline API contract committed; editor not built, provider not connected. Do not deploy listmonk, provision a mailing database, add SMTP credentials, or expose new public ports for the current release.

## Current delivery model

1. Draft and visually design in Sustainable Catalyst using future GrapesJS + MJML editor, with branding black, white, pure red, reusable blocks, charts, links, citations and responsive preview.
2. Keep canonical source document, design JSON, revision hash, approval, image assets, HTML email archive and accessible text alternative independent of any distributor.
3. Generate a **Substack-compatible rich-text and image edition**; do not imply arbitrary HTML/CSS survives Substack editor. Show a clear preview of any design fidelity differences.
4. An authorized human pastes/reviews the edition in Substack and chooses recipients, scheduling and whether to email. All actual sends and subscriber records stay in Substack.
5. Optionally record the public Substack URL and sending receipt as *operator attestation* for a reviewed revision. Do not claim API verification.

## Future premium delivery escape hatch

Implement an adapter contract that can eventually support AWS SES, Postmark, Mailgun, SendGrid, a licensed/self-hosted listmonk instance, or another provider — chosen only when audience scale, costs, or workflow justify it.

The provider-agnostic contract should define:
- `provider_id`, `delivery_mode`, `campaign_ref`, `approved_revision_sha256`, `provider_draft_ref`
- create/update draft, preview/send-test, explicit release authorization, status and receipt reconciliation
- subscriber ownership, consent provenance, unsubscribe and suppression enforcement, bounce/webhook signatures and retention controls
- feature flags and scoped credentials outside WordPress/source control

**No provider is currently selected or enabled for this interface.** A premium provider must not acquire access to Research/Workspace accounts, source documents, or WordPress credentials by default.

## What the feature branch currently contains

- Offline `/v1/newsletter-studio/status` and `/plan` endpoints: report Substack as primary, premium adapter disabled, and no subscriber/transport calls.
- Disallow raw subscribers, recipient emails, provider secrets, scheduling, sending and auto-publishing; tests enforce the boundary.
- Historical option: `compose.staging.yml` is retained as a **deferred, optional listmonk/Mailpit experiment**, not the deployment plan. Running it is NOT necessary for building or sending through Substack. No production cutover or live resources requested.

## Build sequence

- [ ] MEDIA-07.1 GrapesJS/MJML visual-editor prototype, Sustainable Catalyst templates and responsive preview
- [ ] MEDIA-07.2 Persistent revision history, signed approval, per-newsletter source/asset provenance and ownership
- [ ] MEDIA-07.3 Substack-compatible export, image delivery, copy-ready rich text, human send checklist and optional published URL receipt
- [ ] MEDIA-07.4 HTML email / plain-text export, local archive and content portability
- [ ] MEDIA-07.5 Provider-neutral draft/release contract **without an actual email provider**
- [ ] MEDIA-07.6 Future premium adapter implementation **only after separate scope and consent authorization**

## Gates for later premium sending
No direct email sending or subscriber import until verified consent/double-opt-in as applicable, unsubscribe and suppression, legal basis/rights, retention, sender domain SPF/DKIM/DMARC, safe credential storage, bounce handling, complaint management, rate limits, independently authenticated release approvals, audit, backup and rollback.

Substack sending remains an independent manual action outside the Sustainable Catalyst API. MEDIA-06 human reviewer authentication is still not production-certified.

## Licensing
GrapesJS/MJML plugin: BSD-3-Clause. Optional listmonk: AGPLv3, requires license review if adopted later. Any paid provider requires a separate terms, privacy and cost review.
