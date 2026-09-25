# Test review — wave E1 verification tooling (`8f7b02`)

Reviewer: `test_reviewer` (read-only). Tree `/home/pall/projects/.exolon-wave-e1/exolon` @ `32e61e8`
(`origin/main` = `0b0dea9`). Date 2026-09-25. Only this file was written by the review; every
experiment ran in `/tmp` clones (`git clone --no-hardlinks`) and all scratch was deleted afterwards.
Post-review: `git status --porcelain` empty, `git show-ref | grep refs/heads/origin/` empty.

## Verdict: **FAIL — do not merge as certified**

At the exact head under review the change's own verifier returns **6/11 (rc=1)**, and the failures
are not bookkeeping noise: AC-003 and INV-001 assert "every merged meter is green on the E1 head",
and `wave_b_check.py` is genuinely red here (`no_magic_offsets`, 8/9). The shipped green evidence is
bound to a *different* head (`0b0dea9`) and to a dirty pre-commit tree. Mechanism quality is high —
18 independent controls of mine flipped exactly as claimed, including two mutations of the verifier
itself — so this is a "the net is well built but it does not cover the thing it now ships" failure,
not a sloppy-test failure.

---

## 1. Spec → symbol map (all 11 resolve; `--list` agrees)

| Spec id | `path::symbol` in `evidence/wave_e1_check.py` | Assert vs the spec sentence | Falsifiable? |
| --- | --- | --- | --- |
| AC-001 | `scan_covers_committed_union` (:374) | union re-derived from git independently (`union_swift_files`) **and** a needle list naming BlasterBullet/Grenade/TMXTileMapRenderer/Diagnostics/evidence harnesses **and** committed-garbage + untracked-garbage plants **and** parse selftest must be true. Sentence fully covered. | yes — mutation-proven (C7) |
| AC-002 | `attribution_scan_flips` (:439) | 0 violations, independent added-line recount must equal tool's count, allow-list must be *exactly* `['GameConstants.swift']`, 4 plants (per-map/±16/544/committed) each must redden, allow-list must **not** hide per-map logic. Covered, except bucket *placement* (see S4). | yes — mutation-proven (C8) |
| AC-003 | `cross_wave_suite_green` (:564) | rc/passed/failed/green per meter vs recorded counts, `ok=125/125` string, `--meter` really restricts, forced-red meter, absent-meter, budget. Covered. **False at this head.** | yes (and it is what fails here) |
| AC-004 | `loader_harness_green` (:627) | run.sh step 4 compiles GameConstants.swift, rc=0 with 125/125 + both negative controls, last-run/README re-recorded with ancestry-checked HEAD, revert control must fail with `cannot find 'GameConstants' in scope`. Covered *only pre-commit*. | pre-commit only (fails at :671 here) |
| AC-005 | `v3_header_present` (:703) | frozen header token groups + stripped-header falsification + live C-meter WARNINGs must cite it. Sentence's second half is solid. "behavior untouched" leg = same-file vs same-file **and** compares two empty stdout → no signal (:718-719). | predicate yes / inertness no |
| AC-006 | `b_meter_failclosed` (:751) | remote-less clone must be non-zero, print `FAIL-CLOSED`, and not print a scan line; pinned clone must be green with ≥150 lines/≥7 files. Strong. Its tail hygiene assert (`:786`) encodes `HEAD == origin/main`, so it cries wolf at any PR head. | yes |
| AC-007 | `m3_soft_band` (:808) | band soft **and** three deterministic twins hard (`producer<=0`, `<5×`, drain floor) **and** on-disk allocation injection hard **and** harness-layer warn-vs-fail split. Both directions present. | yes |
| AC-008 | `warp_guid_bound` (:916) | DEBUG moved into project-Release, target-Debug, target-Release and duplicated must all redden; real pbxproj must stay byte-identical. Sentence covered exactly. | yes |
| FORBID-001 | `product_untouched` (:1041) | product dirty + `base..HEAD` product diff + scope whitelist + scratch-artifact sweep + 90-line cap per sanctioned touch. The diff checks are real; the whitelist and caps are inert at a clean head (:1066) and the whitelist excludes the root `README.md` this commit changes. | partially (vacuous here) |
| FORBID-002 | `no_silent_relaxation` (:1078) | B non-vacuity guard + planted ±16 red + A hard checks byte-identical to HEAD + C edit text-only + wave_scan red without swiftc. Good intent; two of the five legs compare HEAD to HEAD post-commit, and `:1098` (`if not changed: raise`) *requires* a dirty tree. | mixed (guaranteed FAIL here) |
| INV-001 | `suite_standalone_agreement` (:1129) | two independent counters (this file's `count_verdicts` vs wave_scan's `verdicts`) compared as tuples + rc. Method is genuinely independent. **Claim false at this head.** | yes (and it fails here) |

## 2. My own controls (18, all in throwaway clones; `--no-hardlinks`)

| # | Control | Expected | Observed |
| --- | --- | --- | --- |
| C1 | committed syntax garbage in `BlasterBullet.swift` (committed, clone worktree clean) | parse contour red, names the file | `WAVE_SCAN_RED`, failures=1, problem names `BlasterBullet.swift`; pristine clone failures=0 |
| C1b | union really contains the four named files | membership, not just count | 20 parsed, BlasterBullet/Grenade/TMXTileMapRenderer all present |
| C2 | plant `if name == "L01S02" { return 48.0 }` in `GameScene.swift` | attribution red | violations=1, pattern `per-map имя`, path correct, `WAVE_SCAN_RED`; comment-only plant stays green (0) |
| C3a | delete `refs/remotes/origin/main` in clone | rc≠0, fail-closed, no fallback-green | **rc=4**, `FAIL-CLOSED: refs/remotes/origin/main отсутствует…`, `added-lines:` scan line absent |
| C3d | clone with the *real PR-head topology* (`origin/main`=0b0dea9, HEAD=32e61e8) | reproduce AC-003's red B | **rc=1**, `added-lines: 0 … в 0`, `FAIL no_magic_offsets` — the shipped head's series contour is red for a real reason |
| C3c | clone with `origin/main` pinned to HEAD (post-merge simulation) | green again | rc=0, `ALL_WAVE_B_CHECKS_MATCH_SPEC`, 2938 lines/16 files → the defect is *open-PR-state*-specific |
| C4a | over-band M3 (`percent_of_tick=99.0`) | WARNING + **PASS** | rc=0, `WARNING emission-cost band … 99.0 % of a 16.67 ms tick`, `RESULT: PASS (1/1)` |
| C4b | zero-clock (`producer_ns_per_event=0`) | must stay **hard** | rc=1 |
| C4c | inject `String(describing:)` into `appendRecord` on disk | allocation scan must **FAIL** | rc=1, `FAIL hot_path_is_allocation_free [INV-004]: … ['String\\(', 'String\\(describing']` |
| C5a | pbxproj anchor integrity | DEBUG declared exactly once | 1 |
| C5b/c | move DEBUG into **target Release** `800…004` (and project Release `800…002`), keeping exactly one declaration | must redden *on the GUID clause* | rc=1; reason names the owning block: `SWIFT_ACTIVE_COMPILATION_CONDITIONS=DEBUG is declared in the target Release (800000000000000000000004) configuration`; pristine rc=0 |
| C6 | `--only meters --meter wave-d-stage` | exactly 1 entry, 5 skips | `entries=['wave-d-stage'] skipped=5 partial=True rc=3` |
| C6b | `--meter wave-z-does-not-exist` | rejected, not silently skipped | rc=2, `unknown meter(s): […]` |
| C7 | **mutate the verifier's subject**: exclude `BlasterBullet.swift` from `wave_scan.swift_union()` | AC-001 must go red | rc=1 — `FAIL scan_covers_committed_union: wave_scan parses 19 files but the union is 20; not covered: ['Exolon/GameCore/Weapons/BlasterBullet.swift']` (this is exactly the "must fail if excluded, not merely if count≠20" test — it passes) |
| C8 | **mutate the tool**: delete the `L\d{2}S\d{2}` predicate from `MAGIC_PATTERNS` | AC-002 must go red | rc=1 — `planted per-map … did not redden the attribution scan (violations=0)` |

## 3. Reproduced full run at the reviewed head

`python3 evidence/wave_e1_check.py --json` → **rc=1, 206.6 s, checks=11, failed=5**:
PASS AC-001, AC-002, AC-005, AC-007, AC-008, FORBID-001 · FAIL AC-003, AC-004, AC-006, FORBID-002, INV-001.
AC-004/AC-006/FORBID-002 reproduce identically in 9.3 s via `--only` (deterministic, not load).
Recorded transcripts claim 11/11 at 211-215 s; `wave-e1-check.json` → `"head": "0b0dea97…"`,
`wave-e1-check-green.txt` cites `HEAD 0b0dea9`, `grok-verify-pr.txt` → `bases=route:0b0dea9`, `changed=28`
(the shipped commit is 29 files). The tool fails loudly rather than silently, and `--json` stays pure
JSON on stdout with progress on stderr — both good.

## 4. Process fact honestly recorded — confirmed

`tasks.md:151-157` records that the first AC-003 implementation ran 242-245 s because
`wave_e1_check.wave_scan()` appended `--meter` flags *after* starting the subprocess, so the
"restricted" control silently ran all six meters; it states the verdicts were still true but the
control was not the control it claimed. The fix is in the shipped file (argv built before `run()`,
:240-247) and the regression assert exists (AC-003 :578-583: one entry + exactly 5 skips + `partial`).
My C6/C6b confirm the assert bites and that an unknown meter exits 2 instead of skipping. The same
section also discloses two earlier `grok_verify` `source-stability` failures. Honest record; no
correction needed.

## 5. Gaps: what ships through this net

Must-fix:

1. **M1 — the series contour cannot go green on an open PR head, and `wave_scan`'s own suite proves it.**
   `wave_b_check.py::wave_base()` uses `merge-base(HEAD, origin/main)`; on a tooling-only branch that
   merge-base *is* `origin/main`, so the branch's own product delta is legitimately empty → 0 lines →
   its non-vacuity guard reddens `no_magic_offsets` (C3d, AC-003, INV-001). This is the failure mode
   issue #21 is about (base drifting under a wave), just inverted, and `release.md` "No-Go / hold: any
   meter red at its recorded count blocks E1" applies to this head. Fix: when the own-delta is empty,
   re-anchor to the root base the same way `wave_scan` does (or anchor B to `ROOT_BASE` and keep
   fail-closed only for a *missing* ref). Additionally `clone_tree()` pins `origin/main := HEAD`
   (:204-206), i.e. every clone control runs in a *post-merge* topology the real run never sees —
   pin to the real `merge-base(HEAD, origin/main)` so clone controls mirror production.
2. **M2 — four legs only certify a dirty pre-commit tree, which contradicts this repo's own rule.**
   AC-004's revert (:665-671), AC-005's before/after (:718-719), AC-007/FORBID-002's
   "byte-identical to HEAD" guards (:880, :1085-1088), FORBID-002's `if not changed` (:1098) and
   FORBID-001's per-touch caps (:1066) all compare the working tree to `HEAD`. Once the wave is
   committed they either become tautological (`x == x`) or raise falsely. `decisions.md`
   (2026-09-24) already records exactly this lesson — "Once the fix is on disk, a 'dry-run the
   post-fix plan' control degenerates into comparing the tree with itself … needs that inversion" —
   so this is a repeat of a documented mistake. Fix: bind the "pre-edit" side to the route/base commit
   recorded in `route.json`/`ROOT_BASE` (`git show <base>:path`), never to `HEAD`, and have the check
   assert the head it is running on.
3. **M3 — certification is bound to the wrong head.** No probe ever observed the shipped commit:
   root `README.md` was edited at 06:17 and `tasks.md` at 06:29, after the 06:01 check run and the
   06:12 `grok_verify` run, then committed. Re-run everything at the final head and re-record; the
   verifier should itself refuse to report green when `head` differs from the SHA its evidence names.
4. **M4 — FORBID-001's whitelist contradicts `AGENTS.md` "README before push".** `E1_PREFIXES` +
   `SANCTIONED_MERGED_EDITS` (:1015-1026) admit `engineering/tools/`, this package and the 9 merged
   touches; the root `README.md` is not in either, yet the shipped commit changes it — so
   `product_untouched` would have flagged a compliant README update as out of scope (my probe: the
   only offender in `0b0dea9..32e61e8` is `README.md`). Admit the root README (or revert it and do it
   in the PR body); otherwise the next wave must choose between two contracts.

Accepted (recorded, not hidden — no action required for this merge):

5. **A1** `wave_scan` records the swiftc *path* but never its version; the parse selftest
   (`broken_reddens && good_parses`) catches a stub or absent compiler, but a compiler whose accept
   set drifts changes what "parses" means with no trace in `wave-e1-check.json`. One-line fix later.
6. **A2** Budget coupling: `BUDGET_SECONDS=600` with per-meter `METER_TIMEOUT` up to 400 s run
   sequentially, and AC-003 additionally hard-fails above 600 s — two load-sensitive meters on a busy
   host can turn a correct tree red. Measured 81.9 s (7× headroom) here, so accepted; the M3
   soft-banding rationale in `release.md` says host load 16-18 already moved these numbers once.
7. **A3** The meter roster is duplicated (`wave_scan.py:69` and `wave_e1_check.py:79`) with no
   external anchor; a *coordinated* drop/rename of a merged meter in both files, or a new wave that
   never registers, keeps the suite green at 5/5. Absent-script and unknown-name cases are red (I
   verified both), so only roster shrinkage slips through. A discovery probe over
   `engineering/changes/*/evidence/*_check.py` would close it.
8. **A4** AC-002's `plant(..., expect_bucket=...)` parameter is never supplied (:468-486): plants are
   proven to *bite* but not to land in the wave that introduced them; bucket correctness rests only on
   "merged buckets are non-empty".
9. **A5** The root contour polices Swift only. The 125 TMX maps and `Exolon/Resources` data — wave B's
   actual product surface — are outside both `parse` and `attribution`; their only guard is the B
   meter that M1 shows can go red or fall back. In-spec (AC-001/AC-002 say "Swift"), but #21's blind
   spot is closed only for code.
10. **A6** `strip_comments()` `//`-inside-a-string-literal limit, inherited and disclosed in
    `release.md` residuals.

Evidence hygiene (item 4 of the brief): `wave-e1-check.json` and my own run's JSON both parse;
`--json` stdout is pure JSON. One scrub miss in a tracked file:
`evidence/analysis-repo_explorer.md:1` embeds `/home/pall/projects/.exolon-wave-e1/exolon @ 0b0dea9`
(tree-wide grep of the package and `engineering/tools/` found that single hit). Same line also
confirms the analysis ran on the pre-E1 head.

## 6. Credit where due

Control-the-control discipline is real and unusual: every plant is paired with a pristine baseline,
fail-closed beats are asserted as *not* fallback-green (C3a/C3d/C6b), the M3 leniency keeps three
deterministic hard twins (C4a-C4c), `--meter` must prove it ran what it says it ran (C6), and the
verifier survives self-mutation tests (C7/C8) — I could not weaken `wave_scan` without AC-001 or
AC-002 going red. All 18 controls ran in clones; the real tree stayed byte-clean and ref-clean.

## 7. Six-line summary

1. **Verdict: FAIL** — at the reviewed head `32e61e8` the shipped verifier itself reports 6/11, rc=1
   (AC-003, AC-004, AC-006, FORBID-002, INV-001), reproduced deterministically in 206.6 s and 9.3 s.
2. Spec→symbol map is complete (11/11 resolve) and assert strength is high: my 18 independent
   controls all flipped as claimed, including two mutations of `wave_scan.py` that AC-001/AC-002 caught.
3. Real regression, not paperwork: `wave_b_check.py`'s `merge-base(HEAD, origin/main)` base yields
   `added-lines: 0` on a tooling-only PR branch → `no_magic_offsets` FAIL → the suite contour is red
   on its own head (green only once merged, C3c); `release.md`'s own No-Go rule therefore blocks E1.
4. Root cause of the other four: five control legs compare the working tree to `HEAD`, so they
   certify only a dirty pre-commit state — the exact "comparing the tree with itself" mistake already
   written down in `decisions.md` (2026-09-24); bind them to the route/base commit instead.
5. Evidence binds the wrong head (`0b0dea9`, `changed=28` vs 29 committed files), `README.md` is
   outside FORBID-001's own whitelist yet changed by the commit, and one `/home/...` path leaked in
   `evidence/analysis-repo_explorer.md:1`; `wave-e1-check.json` parses and `--json` stays pure.
6. Must-fix before merge: M1 (B base re-anchor + mirror production ref topology in clones),
   M2 (pre-edit side = base SHA, not HEAD), M3 (re-run/re-record at the final head and have the check
   refuse to claim green off-head), M4 (whitelist root README). Accepted gaps A1-A6 listed in §5.
