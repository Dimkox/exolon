# Requirements — Complete wave-D specification and release audit findings in the Exolon game: P1-10 (end-of-stage bonuses are incomplete versus ORIGINAL_MECHANICS - bravery bonus 10000 and timed bonus 0/1000/3000/5000/7000 at stage boundaries 24/49/74/99/124, plus-one-life capped at 9, exoskeleton cleared and ammo refilled 99/10 - restore the full stage-end sequence in coordination with the wave-A StageBoundaryLedger) and the remaining P1-11 scope (extend the committed release-layer verifier and engineering/runbooks/macos-probe.sh so signing, notarization and archive are checked end-to-end on a clean macOS machine; Linux-decidable parts committed, the macOS run documented as an external handout).

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Given ..., when ..., then ...

## Failure and edge cases

- Probe exit codes are operational, never verdicts: `0` ran, `2` usage, `66` no project, `73`
  cannot write `--out` or the transcript never finished flushing, `75` not macOS, `77` refused
  (Track-B gate unsatisfied, off-tty, or credential-shaped argv/env), `78` misconfiguration
  (in-clone scratch root, unparsable profile name). A `FAIL` verdict still exits `0` so the
  operator can capture it with `--out`.
- `MACOS_EVIDENCE=ABSENT (unverified)` (rc 1) is a third state next to `FAIL`: a missing Mac run
  can never be laundered into a pass, and a bound-to-a-nonexistent-commit report is `STALE`,
  never green.
- A report whose `archive_rc` is non-zero must classify the failure: `NO_SCHEME` next to
  `showdestinations_rc=0` is a contradiction and is rejected; `SIGNING` keeps the signing clause
  open without blaming the scheme.
- **Line-number drift (documentation-only, recorded so the next audit pass does not reopen it as
  a new citation defect).** Phase D-2 appended the Track A/B sections to
  `engineering/runbooks/macos-probe.sh` (210 lines at base, 788 after), so the probe line numbers
  quoted by dated evidence moved: `macos-probe.sh:119-123` (the codesign-flags comment) is now in
  section B, `:132-142` (the old optional archive) is section B2, and the citations
  `…7db1f3/evidence/perfile/citation-integrity.md:14,45,48` and
  `engineering/reports/exolon-full-audit-20260920-v3.md:189` refer to pre-extension offsets. Those
  files are append-only dated evidence and were **not** edited; `runbook_archive_step_present`
  and `runbook_stale_gap_claims` stay green because the merged checker reads text, not lines
  (verified: the unmodified `release_layer_check.py` still reports `RELEASE_LAYER_READY`,
  29/29 controls, on the extended tree).


## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security:
- Reliability:
- Performance:
- Observability:
