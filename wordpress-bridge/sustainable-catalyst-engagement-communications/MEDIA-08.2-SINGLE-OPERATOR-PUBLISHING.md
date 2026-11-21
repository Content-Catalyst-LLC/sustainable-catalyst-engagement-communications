# MEDIA-08.2 single-operator publishing: plugin 8.9.6

Lets the institutional owner author, review, approve and release press releases without a second account, while
keeping every other MEDIA-08/08.1 control. Owner self-review is recorded and disclosed as self-review and is never
described as independent review.

## Configuration
`define('SCEC_MEDIA08_SINGLE_OPERATOR_OWNER', <user ID>);` in wp-config (an integer). The mode is active only while
that user is an administrator. Unset (the default): independent review is required exactly as in 8.9.5.

## Rules
- Approving one's own submission requires: the configured owner, the four attestations (rights, source integrity,
  privacy, institutional authority), an explicit self-review declaration, a valid nonce, and the submitted fingerprint.
- The approval records `approval_mode = owner_self`, the approver, UTC time, the approved SHA-256 and the decision,
  plus an append-only `owner_self_approved` history event.
- Release (administrator) re-checks the gate: flag, Press page, state, fingerprint, embargo and, for self-review, that
  owner mode is still configured for the approver.
- Public render accepts an owner self-review while the approver remains an administrator, so removing the constant
  stops new self-approvals without taking released records offline. Out-of-workflow edits still remove a release.
- Public release pages state: "approved by Sustainable Catalyst's institutional publisher under a single-operator
  editorial process: it was self-reviewed, not independently reviewed". Independent approvals keep their label.
- Other administrators still cannot approve their own submissions. The Press reviewer role is unchanged and optional.

## Tests
`tests/media082-single-operator-validation.php` (CI) and the staging phases `single` and `single_off` in
`tests/media081-wp-acceptance.php` / `tests/media081-staging-acceptance.sh`.
