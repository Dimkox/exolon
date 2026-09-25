# Requirements — Wave E1 verification tooling from the A-D chain debt (issues #21/#22)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot
> override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- **AC-001** Given a merged tree whose earlier waves committed `BlasterBullet.swift`,
  `Grenade.swift`, `TMXTileMapRenderer.swift` and the Diagnostics files, when `wave_scan.py` runs,
  then every Swift file in `295690b..HEAD ∪ working ∪ untracked` is parsed with
  `swiftc -frontend -parse` (20 files here: 16 product + 4 evidence-harness drivers) and a planted
  syntax error in a committed file reddens the run.
- **AC-002** Given the accumulated delta since the change root, when the attribution scan runs, then
  it reports zero violations over 2 938 added code lines in 16 product files, bucketed per merged
  wave (A 2 494, B 237, C 95, D 124), and reddens on a planted per-map table, a planted ±16 and a
  planted pinned boundary - each attributed to the bucket that introduced it.
- **AC-003** Given the five merged meters plus the loader harness, when `wave_scan.py` runs the
  suite, then it records A 28, B 9, C 9, D handout 11, D stage 10, loader 125/125 and exits green
  only if all six are green; one forced-red meter reddens the whole contour.
- **AC-004** Given wave B moved the surface query into the loader, when the 20260919 harness runs,
  then `run.sh` compiles `GameConstants.swift` too, reproduces `REAL MAPS ok=125/125 failures=0`
  with both negative controls, and reverting that one line makes it fail with
  `cannot find 'GameConstants' in scope`.
- **AC-005** Given `v3_measurements.py` is a dated mirror, when a reader opens it, then the header
  states that its 76/51/32/125 numbers describe the pre-fix tree, that the maintained truth is
  `wave_c_check.py`, and that on this head the program aborts before printing them; behavior is
  untouched and wave C's WARNING points at that header instead of owing cleanup.
- **AC-006** Given a clone without `refs/remotes/origin/main`, when `wave_b_check.py` resolves its
  scan base, then it prints an explicit `FAIL-CLOSED` error and exits 4 (never a silent wide
  fallback, never a green); with the ref pinned it is green over the widened root-anchored scan.
- **AC-007** Given a loaded host, when the M3 append timing exceeds its band, then both mirror
  layers print a WARNING with the measured value and pass, while a clock that measured nothing, a
  formatting control under 5× the append, a drain under 8× realtime and an allocating hot path all
  still fail.
- **AC-008** Given the warp's `#if DEBUG`, when `warp_debug_only` reads the project, then the
  condition must belong to the project Debug block - derived from
  `PBXProject → buildConfigurationList → buildConfigurations` - and be absent from the project
  Release, target Debug and target Release blocks; moving or duplicating it reddens the check.

## Failure and edge cases

- Swift file added only in the working tree, or untracked: enters the parse set (control in
  `wave_e1_check.py::scan_covers_committed_union`), so a wave cannot dodge the gate by not
  committing yet.
- A wave that *deleted* a Swift file since the root: listed under `parse.deleted` and not counted as
  a parse failure, and not silently dropped from the set.
- Empty scan (files<7 or code lines<150): red for wave B's own predicate and for `wave_scan` - an
  empty scan is never a green one.
- `swiftc` absent: `wave_scan` reddens the parse contour instead of skipping it; the meters
  themselves keep their own `TOOL_ABSENT` behaviour (wave B returns rc 3 without `--artifact-only`).
- Meter script missing, verdict line unparsable, meter timeout, budget overrun: each is a red, with
  the reason in `problems[]`.
- A restricted run (`--only`, `--meter`) that found nothing wrong: `WAVE_SCAN_GREEN_PARTIAL`, exit 3
  - visibly not the series contour and never a substitute for the full green.
- `git status` noise from evidence-refreshing tools: `wave_scan` prints `tree_writes=…` so a run that
  moved the tree is visible instead of stale-ing a receipt silently.
- A tooling wave with no product delta of its own: wave B's base re-anchors to the root and *prints
  the reason*; it is neither red noise nor a silent green.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule,
example, debt, or digest named here is non-authoritative context until the verifier rederives current
governance evidence.

- Applicable rule IDs: FORBID-001 (no `Exolon/` change), FORBID-002 (no hardening by weakening),
  INV-001 (suite and standalone agree), SIG-001 (one command ≤10 min, one machine-readable line per
  meter).
- Canonical-example deviations and evidence: `strip_comments()` keeps wave B's behaviour including
  its `//`-inside-a-string-literal blind spot (changing it would re-open what A-D certified) -
  disclosed in `wave_scan.py` and `tasks.md`, not fixed.
- Intentional debt created, repaid, or accepted: repaid - #21 (union parse + root-anchored
  attribution), #22 items 1, 2, 5, 6 and the loader-harness break. Accepted/deferred - #22 item 3
  (`vitorc` regeneration, wave E2, needs owner data approval), item 4 (checkpoint vs stage clock,
  unreachable until `loadCheckpoint` is wired), item 6 (all class-2/macOS facts - no Apple host).

## Non-functional requirements

- Security: no secrets, no PII, no host paths in shipped evidence (the freeze transcripts are
  scrubbed; `privacy_gate.sh` is the project's own gate). The warp check is a security-relevant
  guard and is strengthened, never relaxed; product build settings are untouched by E1.
- Reliability: stdlib-only tools; every contour fails closed; controls run in disposable
  `git clone --no-hardlinks` trees so no ref or file of the real worktree can be poisoned;
  idempotent evidence writes (a meter run must not move the tree fingerprint).
- Performance: `wave_scan.py` end-to-end measured 81.3 s against a 600 s budget (parse contour
  parallel over ≤8 workers; the merged meters dominate). `wave_e1_check.py` full 11-probe run
  measured in `evidence/wave-e1-check-green.txt`.
- Observability: one `SUMMARY` line per contour and per meter with expected/actual counts, rc and
  seconds; `--json` documents the same structure (`parse`, `attribution.buckets`,
  `meters.entries`, `totals`, `problems`, `partial`, `seconds`); `RESULT:` line for grep-based
  gating; load-sensitive measurements print their measured value in a WARNING rather than
  disappearing.
