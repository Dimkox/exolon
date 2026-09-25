# Test review RE-CHECK — wave E1 (`8f7b02`) at head `7653f33`

Reviewer: `test_reviewer` (read-only). Head `7653f33` (`fix(tooling): honest certification topology,
blind-spot closure, base-anchored controls`), `origin/main` = `0b0dea9`, tree clean. Date 2026-09-25.
Only `evidence/review-test-recheck.md` written; every experiment ran in `/tmp/e1-recheck/*` clones
(`git clone --no-hardlinks`) and all scratch (~570 MB) was deleted. Post-review: `git status
--porcelain` shows only the two reviewer re-check files, `git show-ref | grep refs/heads/origin/`
empty. Cites my first-pass findings M1-M4 (`evidence/review-test.md`) and the fix batch
(`tasks.md` "Fix batch after the first reviews (R1-R11 / M1-M4 at head 32e61e8)").

## Verdict for the test story: **PASS** — one must-fix remains, and it is M3

M1, M2 and M4 are closed and I proved each closure by planting a regression that the old code would
have passed. M3's *mechanism* is right and honest, but the change's own release gate is now
self-contradictory: `release.md:70-72` lists "a non-empty `stale_certification`" as **No-Go**, and at
the head that ships it is **5**. Fix the wording (or close `tasks.md:8`), do not ship the clause as
written.

## 1. M1 — certification topology: FIXED (measured)

I ran the shipped verifier myself at the committed head:

```
RESULT: WAVE_E1_PROBES_PASS | probes=11 failed=0 seconds=235.6 stale_certification=5   (rc=0)
11/11 green · AC-003 88.1s · INV-001 84.1s · AC-007 28.9s · AC-006 13.1s · rest ≤8.1s
JSON `head` == `git rev-parse HEAD` : True (7653f33…); change_base = 0b0dea9
```

* `cross_wave_suite_green`: **6/6 meters green** (28/9/9/11/10/1) at `7653f33`, suite 83.9 s of the
  600 s budget, forced-red meter and absent-meter controls intact.
* `b_meter_failclosed` now runs three topologies: `no-origin` → rc=4 fail-closed with **no** scan
  line; `real` (open PR, `origin/main` = route base) → green with 2938 lines/16 files through the
  measured-empty re-anchor; `post-merge` → green. `clone_tree` default is `topology='real'` and the
  probe actively raises if a "real" clone was synthesised to post-merge (:1015-1017). Hygiene assert
  rewritten to "unchanged **and** an ancestor of HEAD" instead of "equal to HEAD" — the form that
  could only pass in a synthesised repo.
* **Is the fix load-bearing?** P5 below disabled the re-anchor (`if own_code == 0:` → `if False …`)
  and re-ran wave B at the real topology: `rc=1`, `added-lines: 0 … в 0`, `FAIL no_magic_offsets`.
  So the green at an open-PR head is bought by the fix, not by luck.
* `wave_b_check.py` prints the reason machine-readably
  (`WAVE_BASE=0b0dea9 own_delta_files=0 own_delta_code_lines=0 reason=no-product-delta-on-this-branch
  re_anchor=295690b`) and AC-006 asserts that line exists and says `own_delta_code_lines=0`; the
  `≥7 files / ≥150 code lines` non-vacuity guard stays.

## 2. M2 — base-anchored controls: FIXED, one plant per former hole

| Former hole (my first-pass §5) | Plant in a clone | Required | Measured |
| --- | --- | --- | --- |
| v3 "inertness" compared a file to itself and empty stdout to empty stdout | **P1a2**: behaviour change that actually executes inserted above the module body | AC-005 red | **FAIL** `v3_measurements.py failure mode changed - the header was not inert` (caught on the stderr leg; the stdout leg is still empty-vs-empty and the message discloses `rc=1, 0 chars`) |
| same leg, must not over-react to text | **P1a3**: comment-only line appended | AC-005 green | rc=0 PASS |
| the base side could silently be re-keyed to HEAD | **P1b**: `route.json:base_commit` := HEAD in the clone | AC-005 must *refuse* | **FAIL** `the inertness control compares identical bytes - re-keyed to HEAD by accident?` |
| FORBID-001's 90-line per-touch cap never applied at a clean head | **P2a**: `stage_boundary_check.py` grown +140 lines | cap trips | **FAIL** `the merged-tool touch …/stage_boundary_check.py is …, far beyond a recorded one-line/heading edit` |
| scope whitelist only looked at the working diff | **P2b**: new `scripts/reviewer_out_of_scope.py` | named | **FAIL** `wave E1 edited files outside its scope: ['scripts/reviewer_out_of_scope.py']` |
| "byte-identical to HEAD" guards were `x == x` | **P3**: one comment line inside `gameplay_log_check.hot_path_is_allocation_free` | FORBID-002 red | **FAIL** `the hard check hot_path_is_allocation_free was edited by wave E1` (comparison now against the **route base** `0b0dea9`) |
| `expect_bucket` was a dead parameter (my A4) | **P4**: force every violation into `buckets[0]` inside `wave_scan.attribution_gate` | AC-002 red | **FAIL** `planted per-map at Exolon/GameCore/GameScene.swift landed in bucket 'wave-a', expected 'uncommitted (working tree + untracked)'` |
| staleness probe could be permanently red (unfalsifiable) | **P62**: substitute the recorded sha, then set it to the current head | names it / accepts it | `records fffffff, head is 7653f33` → after binding to the live head: **none** — the probe is two-sided |

Also live in the shipped run: AC-002's own synthetic two-wave repo (built in `${TMPDIR}`) attributes a
line authored by "wave A" and edited into `100 + 16` by "wave B" to **`wave-b`** — a case the real
chain cannot express, which is exactly the bucket-correctness assertion my first pass asked for.
`CHANGE_BASE` is read from `route.json:base_commit` with a format-validated fallback, so the anchor is
the route's own record, not a constant. AC-004's revert control now writes `git_show_base(LOADER_RUN)`
into the clone and passed at a committed head (it falsely failed at `32e61e8`).

## 3. M3 — provenance: mechanism honest, gate wording self-defeating (**must-fix**)

What they built: `evidence/freeze.sh` regenerates all five artifacts in one pass, each header carrying
`head=<sha> date=<utc> dirty=<n>`, scrubs `<repo>` in place of the absolute path, exits 9 on any
unscrubbed `/home` or `/Users` path, and **fails** at step 5 if any artifact does not name the head the
freeze started on. `wave_e1_check` publishes `stale_certification` (WARNING lines + JSON list) and
`grok-verify-pr.txt` now records `changed=32`, matching FORBID-001's 32-path surface.

The shipped artifacts record `head=32e61e8 dirty=16`, so my live run at `7653f33` reports
`stale_certification=5`. **The expectation "11/11 + stale_certification=0" at a head that follows the
freeze is not achievable, and that is structural, not sloppiness**: the artifacts live inside the tree
they certify, so any commit carrying them is a newer head than the one they can name; re-freezing at
`7653f33` writes five dirty files whose commit is again a newer head — an infinite regress.

**My position (as asked):** I **accept** freeze-on-parent + the fingerprint/receipt chain, and I
**reject** demand-freeze-on-new-head as the closure. It is non-circular and I verified it twice:

1. `dirty=16` equals exactly the 16 files `32e61e8..7653f33` changed — the certified state is this
   commit's content; and
2. the local receipt `.grok-stack/runtime/receipts/8f7b0281a27b/verification.json`
   (`created_at 2026-09-25T09:46:16Z`, `status: pass`, `tree_fingerprint
   be0293608f2fe15896ddcb37343538bf8232b2636eafd567b84cda6449c58ea3`) **recomputes byte-for-byte** on
   the current clean tree at `7653f33` (`adaptive_grok.util.tree_fingerprint(Path('.'))` → identical).
   A fingerprint is content-addressed, so unlike a sha-in-a-header it *can* name the tree it certifies.
3. Independently of both, the substance re-ran green **here** (§1), so nothing is being inherited on
   trust alone.

But the paperwork must be made consistent, because as written it fails its own gate:

* **must-fix (a):** `release.md:70-72` — "No-Go / hold: … a non-empty `stale_certification` (evidence
  bound to another head)". Read literally at the shipped head, wave E1 is No-Go. Re-word to bind by
  content: stale unless the certified head is an ancestor **and** the recorded dirty set equals the
  commit's file set **and** a fingerprint-bound receipt (or a live re-run at this head) re-establishes
  the binding.
* **must-fix (b):** close `tasks.md:8` ("- [ ] Bind evidence to the final tree fingerprint") by writing
  the certified `tree_fingerprint` into each artifact header. Then `dirty=16` stops being a coincidence
  count and becomes verifiable, and `stale_certification` can compare content instead of commit
  identity. This is the item they already know is open.
* Minor (accepted): `stale_certification()` judges an artifact by the **first** 40-hex in its text that
  isn't `CHANGE_BASE`; a transcript naming several SHAs is judged by whichever sorts first. It behaved
  correctly in P62, but a `certified_head=` key parsed explicitly (freeze.sh already writes one into
  the JSON) would be sturdier.

## 4. M4 — README sanction, caps, base-diff: FIXED, one stale paragraph

`README.md` is in `SANCTIONED_MERGED_EDITS` with an explicit authorization comment (M4/R10, controller
edit, documentation only), and FORBID-001 reports it among **10** sanctioned edits with real
base-diffs at a committed head: `README.md:+38/-1, …/run.sh:+7/-1, …/v3_measurements.py:+12/-0,
…/wave_c_check.py:+5/-2, …/stage_boundary_check.py:+83/-3, …/wave_b_check.py:+55/-8,
…/gameplay_log_check.py:+26/-12, …/main.swift:+28/-12` (all ≤90 changed lines; the `.py` cap is
enforced — P2a trips it). `_changed_paths()` = `CHANGE_BASE..HEAD ∪ working ∪ staged ∪ untracked`, and
the probe now **refuses** if a sanctioned touch shows no diff against the base ("the scope list is
being compared against nothing"). The product half still holds: `Exolon/` and `Exolon.xcodeproj`
byte-clean against the route base.

**Residual (small, text-only):** `tasks.md:130-133` still carries the pre-fix paragraph — "E1's own
scope forbids touching anything outside `engineering/tools/`, the three merged touch-points and this
package, so the README line … is a PR-body/controller step, **not an E1 file edit**" — which the M4 row
three lines below contradicts. Rewrite that paragraph; the whitelist in code is authoritative.

## 5. AC-002/AC-003 assert strength — no count-pinned tautologies left

* **AC-001** keeps `< 20` as a *floor* only; the binding assertions are set-difference against an
  independently derived union, 7 named files, and the committed/untracked garbage plants. (My
  first-pass mutation test `C7` already proved exclusion of `BlasterBullet.swift` reddens it.)
* **AC-002** cross-checks the tool's 2938 added code lines against its own recount **including
  untracked lines**, requires every merged-wave bucket non-empty, pins the allowance to exactly
  `['Exolon/GameCore/GameConstants.swift']`, and now additionally pins
  `strict_violations_without_allow_list == 0` (the exemption must be *inert*, R11), requires
  `ignored_swift` empty (the `coverage/` blind spot, R4) and requires the tool to keep publishing
  `not_policed` naming the `//`-in-string limit, `Exolon/Resources` data and syntax-only parsing.
* **AC-003** was the real count-pinning risk and it is closed: `verdicts('LOADER')` now asserts
  `ok == total == LOADER_MAPS == 125` (`wave_scan.py:433`, R6) instead of accepting any
  `ok == total`, and AC-003 *proves* it by deleting 25 `L05S*.tmx` in a clone — measured in this run:
  `deleting 25 maps reddened the loader contour (REAL MAPS ok=100/100 failures=0)`. Recorded counts
  (28/9/9/11/10/1) are each paired with `rc==0`, `failed==0`, `green` and INV-001's second independent
  parser, so a count alone buys nothing.
* **R8** removed a real super-set hazard: `is_green()` is now exact membership in
  `('WAVE_SCAN_GREEN','WAVE_SCAN_PARTIAL')` (not `startswith`), the partial token was renamed away
  from `WAVE_SCAN_GREEN_PARTIAL`, and AC-003 demands the literal `WAVE_SCAN_GREEN` for the series
  contour — a restricted run can no longer satisfy the contour claim.
* **R7**: `verdicts('B')` no longer synthesises `ALL_WAVE_B_CHECKS_MATCH_SPEC`; AC-006 drives the
  fail-closed meter *through* `wave_scan` and requires red **and** no invented marker.

## 6. Gaps now

Must-fix: §3(a) and §3(b) only (gate wording + fingerprint binding). Both are text/one-field changes,
no semantic risk.

Accepted with evidence (unchanged from my first pass unless noted):
1. `swiftc` version still not recorded in `wave_scan`/evidence JSON (path + broken/good selftest only).
2. Budget coupling: `BUDGET_SECONDS=600` vs sequential per-meter timeouts up to 400 s; measured suite
   83.9 s here (7× headroom), whole verifier 235.6 s (recorded 229 s — stable).
3. Meter roster is duplicated in `wave_scan.py` and `wave_e1_check.py` with no discovery anchor; an
   absent script or unknown `--meter` name is red, but a *coordinated* roster shrink still passes.
4. `Exolon/Resources` TMX data is outside the root contour (now explicitly *disclosed* via
   `not_policed`, and the loader corpus size is pinned at 125 — strictly better than my first pass).
5. B's re-anchor fires only at `own_delta_code_lines == 0`; a future wave touching 1-149 product code
   lines reddens B's guard by construction (`requirements.md:60-61` states this is intended policy, so
   E2 must plan for it).
6. The `//`-inside-a-string-literal limit in `strip_comments()` (inherited, disclosed).

## 7. Six-line summary

1. **PASS for the test story at `7653f33`**: I ran the shipped verifier myself — `probes=11 failed=0`,
   rc=0, 235.6 s, JSON `head` == git head, 6/6 meters green on the real open-PR topology (M1 closed).
2. M1 is load-bearing, not lucky: disabling `wave_base()`'s measured-empty re-anchor reproduces the old
   shipped-head failure exactly (`rc=1`, `added-lines: 0 … в 0`, `FAIL no_magic_offsets`).
3. M2 closed and proven hole-by-hole with 8 plants — v3 inertness now bites a real behaviour change and
   refuses an identical-bytes comparison, the 90-line cap and the scope whitelist trip, the
   base-anchored "edited by wave E1" guard fires, and forced misattribution reddens AC-002 (dead
   `expect_bucket` is now an asserted parameter, plus the synthetic two-wave repo).
4. M4 closed (README sanctioned with an authorization line, caps apply, base-diff required and
   present); only residual is `tasks.md:130-133`, still claiming in prose that README is "not an E1 file
   edit" — rewrite that paragraph.
5. **M3 remains must-fix**: at the shipped head `stale_certification=5`, and `release.md:70-72` calls a
   non-empty stale list **No-Go** — the change declares itself blocked by its own clause; freeze-on-new-head
   is an infinite regress (artifacts certify the tree containing them), so I accept freeze-on-parent plus
   the non-circular bind, which I verified: `dirty=16` == the 16 committed files, and the receipt
   fingerprint `be0293608f2fe158…` recomputes exactly on this clean tree. Demand: re-word that No-Go
   clause and close `tasks.md:8` by writing the certified tree fingerprint into the artifact headers.
6. Assert strength re-read is clean — no count-pinned tautologies: `LOADER_MAPS=125` replaces
   "any ok==total" and is proven by deleting 25 maps, `is_green()` lost its `startswith` super-set, and
   AC-002 pins the constants allowance to being *inert*; all experiments ran in `/tmp` clones
   (deleted), the real tree stayed byte-clean and ref-clean, and I wrote only
   `evidence/review-test-recheck.md`.
