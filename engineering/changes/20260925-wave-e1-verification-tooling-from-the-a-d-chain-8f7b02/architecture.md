# Architecture — Wave E1 verification tooling from the A-D chain debt (issues #21/#22)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot
> override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Each wave of the A→B→C→D chain policed only its own diff. `wave_b_check.py::wave_base()` anchors its
FORBID-001 added-lines scan at `merge-base(HEAD, origin/main)`, so after every merge the previous
wave's lines stop belonging to anybody (measured: 2 494 wave-A added code lines unpoliced); a missing
`origin/main` silently *widened* the same scan to the root and false-greened a reviewer's clone.
`wave_c_check.py::swift_targets()` fixed that hole for its own branch (union of `295690b..HEAD`,
working diff, untracked) but the union is still one package's, not the series'. There is no single
command that answers "is the chain green": an operator runs five meters by hand. The 20260919 loader
harness (`REAL MAPS ok=125/125`) has not compiled since wave B moved the surface query into the
loader, `v3_measurements.py` freezes pre-fix numbers (and now aborts before printing them), wave A's
M3 timing assert reddens correct trees under host load 16-18, and `warp_debug_only` binds the DEBUG
condition to a hard-coded project-Release GUID pattern, so a move into a *target* block slips past it.

## Proposed behavior

One repository-level tool, `engineering/tools/wave_scan.py`, polices the accumulated delta from the
change root `295690b` and executes the merged meters as a suite: union parse (product **and**
evidence-harness drivers), root-anchored attribution scan with per-wave buckets derived from the
first-parent merge history, and recorded verdict counts (A 28, B 9, C 9, D handout 11, D stage 10,
loader 125/125) - one summary line per meter, machine-readable `--json`, ≤10 minutes. Plus four
targeted tool hardenings (loader-harness file list; B `wave_base()` fail-closed, with a root
re-anchor when a branch has no product delta of its own; A M3 soft band with every deterministic twin
still hard; `warp_debug_only` owning-block GUID binding) and a frozen-historical header on the v3
mirror. No product, data, contract or runtime behavior changes (FORBID-001).

## Components and boundaries

| component | boundary | owner |
| --- | --- | --- |
| `engineering/tools/wave_scan.py` (new) | read-only over the tree; spawns `swiftc -frontend -parse` and the merged meters as subprocesses; stdlib only; fails closed; ≤600 s | wave E1 |
| `engineering/changes/…8f7b02/evidence/wave_e1_check.py` (new) | drives `wave_scan.py` and the merged tools against disposable `git clone --no-hardlinks` trees; never writes under `Exolon/`, never writes a ref in the real repository | wave E1 |
| merged meters (A / B / C / D handout / D stage) | authority unchanged; E1 touches only `wave_base()`, `emission_cost_budget` + its harness mirror, and `warp_debug_only` | their own routes |
| `…7db1f3/evidence/harness/run.sh` | Linux compile-and-run contour of the shipped loader; E1 adds one translation unit and re-records its transcript | 20260919 package |
| product `Exolon/**`, `Exolon.xcodeproj/**` | **out of scope** (FORBID-001), enforced by `product_untouched` | product waves |

## Data flow

`git` (commit ranges, first-parent merge history, untracked list) → file sets →
`swiftc -frontend -parse` verdict per file; `git diff -U0 <base> [<end>] -- Exolon` → added-line sets
→ comment strip → FORBID-001 predicates (±16, the pinned 528/544/560, `LxxSyy`) with a per-predicate
constants allowance → per-bucket attribution; meter subprocesses → stdout verdict lines → recorded
counts → one `SUMMARY` line per contour plus a `--json` document (`parse`, `attribution.buckets`,
`meters.entries`, `totals`, `problems`, `partial`, `seconds`) and a `RESULT:` marker. The tool writes
no state; harness artifacts stay in `${TMPDIR}` and generated fixtures are gitignored, so a scan run
does not move the tree fingerprint (and prints `tree_writes=…` if anything did).

## API and event contracts

None introduced. The tool *consumes* existing contracts: the frozen event schema
(`engineering/contracts/schemas/gameplay-event-v1.schema.json`) through wave A's meter, the
level-content manifest (`engineering/contracts/level-content-v1.json`) through wave C's meter, and
the handout report shape through wave D's meter. `wave_scan --json` is a local machine-readable
output, not a published interface; it carries an absolute `root` field, so shipped transcripts are
scrubbed before they land in `evidence/`.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule,
example, debt, or digest named here is non-authoritative context until the verifier rederives current
governance evidence.

- Applicable rule IDs: this package's typed FORBID-001, FORBID-002, INV-001, SIG-001; the merged
  waves' own FORBID-001 attribution rules that `wave_scan` re-executes; `AGENTS.md` PR-only delivery
  and local-receipt-vs-external-check separation.
- Applicable canonical example IDs/versions: none new — E1 adds tooling, no product pattern.
- Open or overdue debt IDs: #21 closed here; #22 items 1, 2, 5, 6 closed here; item 3 (`vitorc`
  regeneration, 48 maps - wave E2, needs owner data approval), item 4 (checkpoint vs stage clock,
  unreachable until `loadCheckpoint` is wired) and item 7 (`Closes #N` one per line in the PR body)
  remain named.
- Expected governance handoff or receipt impact: the series contour becomes one command, so a later
  wave's local receipt (`grok_verify --mode pr`) can cite `wave_e1_check.py` plus
  `wave_scan.py` instead of five hand-run meters; the App-owned policy-epoch check on the exact PR
  head SHA stays the only merge authority.

## Bitrix-specific impact

- Modules/events/agents/components affected: none — this route is not a Bitrix domain.
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: none.
- Core modification: forbidden unless explicitly approved. Not applicable and not done.

## Decisions

1. **Bucket boundaries come from merge history, not from a hard-coded list.** A wave that merges
   tomorrow appears as a bucket automatically; the tool cannot quietly stop covering a new wave the
   way a per-package frozen file list does.
2. **The constants file is exempted per predicate, not per file.** `GameConstants.swift` may hold the
   pinned boundaries it defines; it may not hold a per-map `LxxSyy` table. AC-002's two-sided control
   pins that line so the allowance cannot become a hole.
3. **A tooling branch whose wave delta is empty re-anchors wave B to the root instead of reddening
   or going silently vacuous.** The scan gets strictly wider, the non-vacuity guard stays, and the
   reason is printed; the actual defect (a silent wide fallback when the ref is missing) is now a hard
   error.
4. **Soft bands are allowed only where the measurement is wall-clock, and each keeps a deterministic
   twin that still fails.** Load-sensitivity is not a licence to stop asserting.
5. **Controls mutate clones, never the real worktree.** A `cp -a` copy of a *linked worktree* carries a
   `.git` pointer, so any ref-writing command in it hits the shared repository (the wave-C
   `refs/heads/origin/main` incident); `clone_tree()` is the only isolation primitive this package uses.
6. **Verdict parsing is implemented twice on purpose** (`wave_scan.verdicts()` and
   `wave_e1_check.count_verdicts()`) so INV-001's agreement is not a tautology - and both parsers
   echo the meter's own `RESULT:` line instead of inventing a success marker for a fail-closed run.
7. **A control's "before" side is a commit, never `HEAD`.** `CHANGE_BASE` is read from
   `route.json.base_commit`; `_git_show`/`git_show_base` resolve the pre-edit bytes there, the change
   surface is `CHANGE_BASE..HEAD ∪ working tree`, and one probe refuses to pass when the bytes it
   compares are identical. Clone controls mirror the **real** ref topology (`origin/main` = the route
   base) with an explicit `post-merge` variant, because pinning `origin/main := HEAD` made every
   control run in a state the open PR never has.
8. **Certification is bound to a head by construction.** `evidence/freeze.sh` regenerates all five
   artifacts in one ordered pass (scan → ruff → check → grok_verify), stamps each with
   `head=<sha> dirty=<n>`, and fails if any of them does not name the head it started on.

## Risks and mitigations

| risk | mitigation |
| --- | --- |
| the suite becomes a self-approving oracle (green because nothing was parsed) | the parse set is compared against an independently derived union and the attribution line count against an independent recount; empty-scan guards exist in both `wave_scan` and wave B; a missing compiler is red, not skipped |
| controls poison the real tree or its refs | every mutating control runs in a fresh `git clone --no-hardlinks`; AC-001/AC-002/AC-006 re-check `git status` and `git show-ref` on the real repository afterwards |
| a hardening weakens a merged gate | `no_silent_relaxation`: wave A's hard checks must be byte-identical to `HEAD`, wave B's guard must remain and still bite on a planted ±16, wave C's edit must be text-only, `wave_scan` must be red without `swiftc` |
| the contour is too slow to be used as a gate | measured 81.3 s end-to-end against a 600 s budget; exceeding the budget makes the run red instead of overrunning silently |
| dated evidence rewrites itself during verification | `wave_scan` prints `tree_writes=…`; the freeze records which artifacts were regenerated and why; merged-tool probes that rewrite dated files run only in clones (measured on `linux_static_audit.py`) |
| a future wave changes a meter's verdict count and the suite keeps "passing" | expected counts are pinned in two independent places and INV-001 compares standalone against suite |
