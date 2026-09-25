# Security review — wave D (index)

Verdicts by route agent `security_reviewer`, two passes on heads 84b7813/377e7ae (both
re-verified unchanged at 30ea679 per each part's drift note):

- Part 1 (identity/hardened/entitlements/warp gating): PASS — `review-security-1.md`
- Part 2 (probe gate, forbidden-argv abort, handout integrity, privacy sweep, history):
  PASS with findings F-1/F-2 — `review-security-2.md`
  - F-1 (bypass): FIXED fail-closed at 30ea679 — fourth verdict
    `MACOS_EVIDENCE=UNVERIFIED` rc=1 + registered control `handout_binding_is_fail_closed`
    reproducing the planting; STALE precedence unchanged.
  - F-2 (self-reference limit): documented (tree-binding authority applies to reports sealed
    outside the clone; no degraded mode added); AC-003/README wording narrowed to what the
    fields prove.
- One transcription disclosure: `review-security-2.md:179` PEM literal shortened to
  `-----BEGIN … PRIVATE KEY …` (with in-place note + wave-A precedent) because the verbatim
  quote trips the repository's own secret-scan; claims unchanged.

Overall: PASS for merge, contingent on gates at 30ea679 (handout checker 11/11 incl. the new
control; merged release checker red = exactly the declared pair).
