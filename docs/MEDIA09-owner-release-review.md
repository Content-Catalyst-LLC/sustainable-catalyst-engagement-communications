# MEDIA-09 owner/privacy release review — version 2

**Decision: NO-GO. DRAFT FOR REVIEW; NOT APPROVED FOR PUBLICATION.**

This document makes the previously local notice available for exact-wording review. It does not approve processing, activate staff sign-in, or enact a retention policy. The original packet is preserved verbatim below. Owner decision: [issue #35 privacy review](https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications/issues/35#issuecomment-6862323605).

## Proposed revised inquiry notice — incomplete until marked items are resolved

> Content Catalyst LLC operates Sustainable Catalyst. We collect your name, reply email address, inquiry category, subject and message to assess and respond to your inquiry and, where relevant, manage the resulting institutional correspondence. Only provide information needed for your request; do not submit sensitive personal information, credentials or private research.
>
> Where GDPR applies, our proposed basis for ordinary Press, research collaboration and institutional partnership correspondence is legitimate interests in responding to requests and coordinating institutional relationships, subject to an approved necessity and balancing assessment. Steps you request toward a contract may use the applicable contractual basis when you personally would be a contracting party. **Controller identity, GDPR applicability and these bases require authorized review before this notice can be published.**
>
> Your inquiry is private and available to authorized staff according to their responsibilities. It is not published or added to a newsletter. Acknowledging this notice does not provide marketing consent or authorize CRM synchronization. HubSpot is disconnected; no inquiry information is sent to it in the present release.
>
> **Retention wording is pending implementation and approval.** The proposed schedule appears below. It must not be represented as an operational guarantee until deletion, legal holds, backups and restore-time suppression have been implemented and tested.
>
> **Processor and transfer disclosures are pending:** identify the approved hosting and backup entities, processing countries, relevant recipients and any required international-transfer safeguards. Do not replace this with an unverified assurance.
>
> Subject to applicable law, you may request access, correction, erasure, restriction or portability, object to processing based on legitimate interests, and complain to the relevant supervisory authority. Privacy requests may be sent to tariq@sustainablecatalyst.com, the channel in the [published privacy policy](https://sustainablecatalyst.com/privacy-policy/); the authorized reviewer must confirm this channel for Media. Requests will be handled within applicable legal time limits, with any permitted extension explained.

Proposed checkbox wording: **“I have read the privacy notice.”** It is an acknowledgment, not a lawful-basis declaration or optional marketing opt-in. No newsletter or marketing checkbox is included. Before real activation, the existing `consent_to_reply` contract/storage terminology must be reconciled with this distinction and tested; its boolean must not be treated as GDPR consent or CRM permission.

## Owner-proposed retention baseline — not enacted

| Category | Proposed schedule | Current acceptance |
|---|---|---|
| Spam, invalid or rejected inquiries | Delete within 30 days | Not implemented/approved for real data |
| Answered or closed Press inquiries | Delete 12 months after last substantive correspondence | Not implemented/approved for real data |
| Active inquiries | Review after six months of inactivity; delete when no longer needed | Not implemented/approved for real data |
| Established institutional relationships | Annual review; delete after 24 months without meaningful activity unless another documented basis applies | Not implemented/approved for real data |
| Security/access logs | 30–90 days according to necessity | Operational schedule not accepted |
| Backups | Target expiry within 90 days; beyond-use restrictions and restore-time re-deletion | Rotation/suppression not implemented or certified |
| Genuinely non-identifying audit records | Up to 24 months where justified | Current UUID-linked audit is not certified non-identifying |

These are the owner's proposed policy choices, not statutory retention periods. Required acceptance includes synthetic PostgreSQL erase/retain boundary tests; last-substantive-correspondence tracking (not merely an inquiry status timestamp); active/inactive review; scoped, reviewed legal holds; canonical contact reference handling; processor/CRM erasure if ever enabled; backup rotation and restore suppression; proportionate rights verification and rights-request response timing. Existing create/review/backup tests do not certify these capabilities. No purge or deletion job has been enabled.

## Consolidated identity deployment blocker — Platform Core owns provisioning

**Platform Core must provision the HTTPS identity origin, register a separate confidential Media OIDC client with exact HTTPS redirects, Authorization Code + PKCE and MFA, and supply a dedicated server-mounted credential file readable only by the Media service.** This is one deployment blocker. No issuer, client ID, credential path or identity acceptance is invented here. Do not reuse the HTTP SC-AUTH-02 issuer, sc-workspace client credentials, or staging secret files.

Staff sign-in and real personal-data processing remain disabled until identity and privacy release gates pass. Public Media/Press source, synthetic inquiry tests and optional HubSpot mocks can continue independently. HubSpot remains disconnected; no newsletter, marketing, sending or private Research authorization is inferred.

## Approval still required

Authorized owner/privacy reviewer must inspect the exact notice, resolve controller/contact/processor/transfer details, confirm lawful bases and balancing assessment, approve the policy, and review implemented deletion/rights/backup evidence. Record versioned protected approval evidence and the final notice hash. Security and production cutover authorization remain separate. The version-2 draft is intentionally not publication-ready.

Official review references: [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng/), [Irish DPC transparency](https://www.dataprotection.ie/en/organisations/know-your-obligations/transparency), [Irish DPC retention guidance](https://dataprotection.ie/en/faqs/responsibilities-data-controllers/how-long-should-personal-data-be-held-meet-obligations-imposed-gdpr). The policy proposals above are recorded from the owner's review, not newly granted legal approval.

---

## Original local packet — verbatim

Original SHA-256: `356af2f401d2bd53187055a8a3308bf203f3aa6489efe51e7645185a9f4439c5`

# Media / Press — owner release review

The implemented product is running in private synthetic staging. Real collection and production cutover remain disabled. Implementation and acceptance: https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications/pull/37

## Proposed form notice — requires owner/privacy approval

Content Catalyst LLC operates Sustainable Catalyst. We use your name, reply email, inquiry category, subject and message to review your request and respond. Your inquiry stays in our private Media workflow and is accessible to authorized staff. Submitting does not publish your message or subscribe you to a newsletter. Do not include sensitive personal information or private research. Optional CRM disclosure requires separate approval. For retention, processing information and privacy rights, see our [Privacy Policy](https://sustainablecatalyst.com/privacy-policy/). Privacy requests may be sent to the contact listed there.

This draft follows the published policy's operator and inquiry/privacy boundaries. The policy is not evidence that this particular deployment has been approved. Confirm the applicable lawful basis, operational retention/deletion schedule (including backups), rights handling, and whether the proposed notice is approved before actual personal-data intake. HubSpot remains disconnected during this decision.

## Identity action

Provide the approved **HTTPS platform OIDC issuer/client** and protected server credential-file location, plus the authorized staff subject/organization/role mapping. Do not send credential values. The available SC-AUTH-02 synthetic test issuer is HTTP-only; no production identity acceptance has been recorded.

## Production action

After identity and privacy/security acceptance, verify the real production backup and isolated restore, approve the exact proxy/WordPress installation and final cutover. The source includes an explicit release gate requiring approval references, and a rollback procedure. No production deployment, DNS or public collection was performed.

## Optional HubSpot: one owner action

Provision a supported **single-account, private-distribution static-auth token** in the approved HubSpot account with only contacts read/write and companies read/write scopes, install it in a protected backend file, and provide its path. This is optional and does not block first-party intake. [Official HubSpot authentication documentation](https://developers.hubspot.com/docs/apps/developer-platform/build-apps/authentication/overview).

## Preview

Private staging runs on Contabo loopback HTTPS port 18982. Tunnel:

```sh
ssh -N -L 18982:127.0.0.1:18982 catalystadmin@94.72.113.77
```

Then open https://localhost:18982/press/. The preview uses a seven-day self-signed certificate. Chrome browser verification stopped at the certificate warning; no warning was bypassed. Browser acceptance remains pending a trusted staging certificate or your manual browser handoff.
