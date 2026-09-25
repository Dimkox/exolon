# Independent re-check of the wave E1 fix batch — head `7653f33`

* Reviewer: `code_reviewer` (route 8f7b02), read-only; re-runs **my own** plants from
  `evidence/review-code.md` against the new head.
* Tree `/home/pall/projects/.exolon-wave-e1/exolon` @ `7653f33` (= `32e61e8` + the R1–R11 fix
  batch, 16 files, +1306/−185). Base under certification is still `0b0dea9` (route base);
  `0b0dea9..7653f33` = 2 commits. Controller receipt for this head: `be0293608f2fe158` @ 09:46:16Z.
* Every mutation ran in a scratch `git clone --no-hardlinks file://…/.exolon-wave-e1/exolon` under
  `/tmp/e1rc/`; clones deleted afterwards, shared repo verified clean (`refs/heads/origin/` count 0,
  no worktree added by me).

## VERDICT: **PASS** — R1–R11 are closed and each closed by a control I flipped myself.
### One release-blocking re-record (X1, not a code change) and one new low finding (X2).

No vector I attacked at `7653f33` let `wave_scan` report green over a live violation, in either
topology; the failure class that blocked `32e61e8` (green recorded for a head that is red live) is
gone — the suite is now green **in the open-PR topology I built by hand**, not only in a
synthesised one.

---

## A. R1 — the blocker: FIXED, measured in the real pre-merge topology

| clone of `7653f33` | `refs/remotes/origin/main` | `wave_scan.py` (full, 3 contours) |
| --- | --- | --- |
| `r1` — **true base, open-PR topology** | `0b0dea9` | **`RESULT: WAVE_SCAN_GREEN`, exit 0**, meters 6/6 (28, 9, 9, 11, 10, `REAL MAPS ok=125/125 failures=0`), parse 20 files / 0 failures / selftest true, attribution 2938 lines / 16 files / 0 violations, `elapsed=84.1s budget=600s tree_writes=none` |
| `r1pm` — post-merge topology | `7653f33` | `RESULT: WAVE_SCAN_GREEN`, exit 0, 6/6 |
| `noorigin` — ref deleted | *(absent)* | `RESULT: WAVE_SCAN_RED`, exit 1, `wave-b-mapdata rc=4` |

The re-anchor now keys on the **measured** own-delta, with a machine-readable reason
(`wave_b_check.py:698-703`), verified by running B standalone in the `r1` clone:

```
  wave_base: WAVE_BASE=0b0dea9 own_delta_files=0 own_delta_code_lines=0
             reason=no-product-delta-on-this-branch re_anchor=295690b (…)
  added-lines: 2938 стронок кода в 16 изменённых продуктовых файлах
RESULT: ALL_WAVE_B_CHECKS_MATCH_SPEC
```
So the green comes from a *wider real scan* (2938/16), not from skipping: `rc=4` is reserved for the
missing ref, and the ≥7/≥150 guard is untouched (`wave_b_check.py:1193`, and `--base HEAD`/`HEAD~1`/
`0b0dea9` still redden with "the root-anchored scan is strangely empty").
The harness no longer auto-pins: `clone_tree(name, topology=…)` (`wave_e1_check.py:179-212`) with a
control that **refuses a synthesised "real" topology** (`:1014-1016`) and runs all three (`:996`,
`:1013`, `:1020`). AC-006's old `origin/main == HEAD` hygiene assert is replaced by
"unchanged **and an ancestor** of HEAD" (`:1041-1046`).
Evidence probes at the head, in a clone whose `origin/main` I pinned to the **real** base — my run,
not theirs: `RESULT: WAVE_E1_PROBES_PASS | probes=11 failed=0 seconds=232.0` , rc=0.

## B. R2 / R4 / R5 / R11 — attribution blind spots: CLOSED (my plants, this head)

| plant (all in scratch clones of `7653f33`) | result |
| --- | --- |
| untracked new `Exolon/GameCore/Levels/E1HiddenNew.swift` with `544.0`, `100 + 16`, `"L01S02"` | **`WAVE_SCAN_RED`, 3 violations**, all `bucket=uncommitted (working tree + untracked)`, `code_lines 2938→2944`, `files 16→17`, `untracked_files` names the file; control without it: 0/2938/16 |
| ignored `Exolon/GameCore/coverage/HiddenBad.swift` (`git check-ignore` → `.gitignore:17:coverage/`) | **`WAVE_SCAN_RED` naming the file**: `FORBID-001 coverage: Exolon/GameCore/coverage/HiddenBad.swift exists under Exolon/ but git lists it neither as tracked nor as untracked …`; registry field `ignored_swift=["…HiddenBad.swift"]`; control after removal: green |
| `100 + 16`, `acc += 16`, `100 +  16` (2 spaces), `100 + (16)` | **all 4 RED** (widened predicate `[-+]=? ?\(?\s*\b16\b`, `wave_scan.py:64-71`) |
| `100 + 1_6`, `100 + 0x10`, violation behind `"https://…"` on the same line, `100 + NamedConstant.deltaSixteen` | green — **and each is in the printed registry** |
| committed plant on the branch (`GameScene.swift`, `544.0`) | RED → `bucket=codex/wave-e1-… (committed on this branch)` (unchanged behavior) |

`NOT_POLICED` is now 5 items, printed on every run (`SUMMARY not-policed 5 disclosed limits …`) and
carried in `--json`; it cannot be deleted in silence — `wave_e1_check.py:526-531` fails if any of
`'string literal' / 'Resources' / 'syntax-only'` disappears. R11's allowance is pinned inert by a
live recount: `attribution.strict_violations_without_allow_list` must be 0 (`wave_e1_check.py:515-518`);
I measured it 0 on the clean tree and equal to the violation count for each of my plants (3 and 1),
so the field is not decoration.

## C. R3 — previously vacuous controls: re-keyed to the route base, verified

`CHANGE_BASE` comes from `route.json:base_commit` with a regex-validated fallback
(`wave_e1_check.py:59-72`), and every pre-edit side reads `git show $CHANGE_BASE:<path>`
(`git_show_base`, `:248-250`) instead of `git checkout -- <path>`:
* **v3 inertness** compares the `0b0dea9` bytes against the reviewed bytes **and refuses to pass on
  identical bytes** (`:951-956`: "the inertness control compares identical bytes - re-keyed to HEAD
  by accident?"). My own independent pre/post run at the previous head already proved the header
  inert (both `rc=1`, both `stdout` empty, identical last traceback line); the control now enforces
  the same thing structurally.
* **AC-004's revert** writes the route-base `run.sh` (`:901`) — the probe detail reads "reverting the
  line gives `cannot find 'GameConstants' in scope`", and `last-run.txt`/README now cite `HEAD
  7653f33` instead of the pre-commit head.
* **FORBID-001 scope** uses `_changed_paths()` = `CHANGE_BASE..HEAD ∪ working ∪ cached ∪ untracked`
  (`:1303-1320`); it now **refuses** if the surface names no sanctioned merged edit (`:1338-1340`) and
  **refuses** if any sanctioned touch shows no diff against the base (`:1346-1352`) — exactly the
  vacuity I flagged. My own measurement of that surface at the head: `git diff --name-only
  0b0dea9..HEAD` = **32 paths**, `-- Exolon Exolon.xcodeproj` = **0 paths**, and every one of the ten
  sanctioned touches carries a real base-diff (`README.md 38+/1−`, `run.sh 7/1`, `last-run.txt 4/2`,
  `harness/README.md 1/1`, `v3_measurements.py 12/0`, `wave_c_check.py 5/2`, `wave_b_check.py 55/8`,
  `gameplay_log_check.py 26/12`, `harness/main.swift 28/12`, `stage_boundary_check.py 83/3`) — all
  capped files are within the ≤90 limit (max 86). The probe passed on this head (11/11, rc=0).
  (M4: `README.md` is in `SANCTIONED_MERGED_EDITS` with the reason recorded, and `tasks.md`'s
  "Package paperwork" + the fix-batch table name it; my tree-hash proof that `Exolon/` and
  `Exolon.xcodeproj` are **byte-identical between `0b0dea9` and `7653f33`** (`2573904c…`, `57913d72…`)
  still holds, and `git diff --name-only 0b0dea9..HEAD -- Exolon Exolon.xcodeproj` is empty.)
* **FORBID-002** now diffs the C-meter wording against `CHANGE_BASE` and fails if there is no
  base-diff (`:1382-1390`); A's hard checks are compared "byte-identical to the **route base**
  … (not to HEAD)" (`:1413`).

## D. R5–R9 disclosures with the named control, each flipped by me

| finding | control | my measurement |
| --- | --- | --- |
| R6 loader corpus size | `LOADER_MAPS = 125` pinned into the verdict (`wave_scan.py:61, :433`); AC-003 deletes 25 `L05S*.tmx` in a clone (`wave_e1_check.py:838-844`) | my own run, 100-map clone: `LOADER expected=1 passed=0 failed=1 green=False verdict='REAL MAPS ok=100/100 failures=0'` → **`WAVE_SCAN_RED` exit 1**, even though `run.sh` exited 0 |
| R7 synthesized marker | B branch now echoes the meter's own `RESULT:` line or raises (`wave_scan.py:405-410`); AC-006 requires no invented marker through `wave_scan` (`:1024-1029`) | remote-less clone through the suite: `passed=0 failed=9 rc=4 green=NO verdict='no "RESULT:" marker (a fail-closed wave_b_check exit prints none)'`; the problem line quotes `rc=4 tail=…` — **no `ALL_WAVE_B_CHECKS_MATCH_SPEC` anywhere** |
| R8 superset token | renamed `WAVE_SCAN_PARTIAL` (`wave_scan.py:560-563, :614-617`), banner always pairs with the skipped list | `wave_scan.py --only parse,attribution` → `SUMMARY meter skipped=wave-a-gameplay-log,…,loader-harness-125maps (partial run, not the series contour: sections=parse,attribution)` + `RESULT: WAVE_SCAN_PARTIAL`, **exit code 3** (measured directly, not through a pipe); `grep -w WAVE_SCAN_GREEN` cannot match it |
| R9 machine reason | `WAVE_BASE=… own_delta_code_lines=… reason=…` | asserted present with `own_delta_code_lines=0` (`wave_e1_check.py:1033-1036`) and observed in my standalone run (section A) |
| R5 disclosure | the two accepted forms are registry items 1–2, plus "not ported: B's ten-seam scan" in tasks.md "Accepted and disclosed" | registry printed every run; forms measured in section B |

## E. Process facts of the fix batch — recorded, not hidden (checked against the tree)

`tasks.md:159-172` documents three self-caught defects in the new certification pipeline, and each
is visible in the shipped code: (a) `evidence/freeze.sh` failed **its own** first pass with
`FREEZE FAIL: an absolute repository path leaked into a recorded artifact` (the JSON post-processing
step wrote the checker document unscrubbed); fixed by scrubbing there **and** by an explicit
`/home/`-or-`/Users/` refusal, so the pipeline now trips on its own leak instead of committing it;
(b) two wording defects caught *in the recorded output after a green pass* ("byte-identical to HEAD"
after the guards moved to the route base; two different `README.md` paths rendering identically);
(c) the first `freeze.sh` invocation computed the repository root one level too high (4 vs 5), making
`wave_scan` exit 2 in a non-repository — it now aborts early with "not a git repository". The freeze
row itself states `FREEZE OK head=32e61e8 dirty=16 scan=82s check=229s verify=184s` — honest about
which head it ran on, which is what surfaces X1 below.

## F. New findings at `7653f33`

### X1 — REQUIRED before the receipts bind: the five certification artifacts still name `32e61e8`
The committed `wave-scan-end-to-end.txt`, `wave-e1-check-green.txt`, `wave-e1-check.json`,
`ruff-new-tools.txt` and `grok-verify-pr.txt` all carry
`head=32e61e8fd49ab…  date=2026-09-25T08:05:54Z  dirty=16`. The package's own M3 gate says so, out
loud, in my run at the head:

```
WARNING stale-certification wave-scan-end-to-end.txt: records 32e61e8, head is 7653f33 - re-record with evidence/freeze.sh
… (×5) …
RESULT: WAVE_E1_PROBES_PASS | probes=11 failed=0 seconds=232.0 stale_certification=5
```
Characterisation, precisely: the *content* the freeze certified is this commit's content (`dirty=16`
equals the 16 files of `32e61e8..7653f33`), and I reproduced both results live at `7653f33` in the
real topology (section A), so no claim in those transcripts is false. What is missing is the
**re-record at the final head** — `freeze.sh` exists exactly for that, fails on any artifact that
does not name its head, and was last run one commit earlier while the batch was still dirty. Design
note worth one line to the owner: `stale_certification>0` currently costs a WARNING, not a verdict —
a standalone checker pass on a head whose artifacts describe another head still prints
`WAVE_E1_PROBES_PASS`/rc=0 (documented rationale at `wave_e1_check.py:1449-1458`: the probe must not
refuse its own recording pass; `freeze.sh` is the authority). Either re-run `bash
engineering/changes/…8f7b02/evidence/freeze.sh` at the final head before binding receipts (≈9 min),
or have the controller treat `stale_certification>0` as "not certified" — or both.

### X2 — LOW: the untracked union is repo-wide, while it is named and described as product-only
`wave_scan.py:263-272` (`untracked_product_swift`) passes pathspecs `-- Exolon '*.swift'`; git ORs
pathspecs, so this lists **any** untracked `*.swift` in the repository, and
`added_code_lines(..., end=None)` then feeds every line of it into the *product* FORBID-001 set:

```
new untracked engineering/scratch/E1Outside.swift containing `let bad = 544.0`
→ violations=1  hits=["engineering/scratch/E1Outside.swift|закреплённая граница…|uncommitted (working tree + untracked)"]
  files 16→17   untracked_files=["engineering/scratch/E1Outside.swift"]   WAVE_SCAN_RED
```
Direction: it polices **more** than documented, so it cannot produce a false green. Costs: the
`≥7/≥150` non-vacuity guard may be fed by non-product lines; an untracked evidence driver that
legitimately names a map (harness files full of `L01S10`) reddens the product gate; and the same
line escapes once committed (committed ranges use `-- Exolon` only), so a plant disappears when you
`git add` it. Fix is one predicate (`rel.startswith('Exolon/')`) — or rename the claim and the
`untracked_files` wording in AC-002's detail ("untracked **product** swift on the real tree now: 0").

### X3 — informational, no action
`ruff check` on the two new tools: clean. The 7 findings on the merged files
(`wave_b_check.py:59` F401, `:1245/:1246/:1449/:1450` F541, `stage_boundary_check.py:421` E741,
`:611` F841) are all outside E1's hunks (`wave_b_check.py` hunks = `648-708` only) and the package
transcript names them as pre-existing lines left alone. `git diff --check 0b0dea9..HEAD` → rc=0.

## G. Not re-verified here
macOS-side facts (probe Track A/B, `xcodebuild`, signing/notarization) — unchanged, still externally
blocked, no Apple host; `scripts/grok_verify.py` — controller-owned, not re-run by me; the receipt id
`be0293608f2fe158` itself — `.grok-stack/runtime` is deliberately not Git content.
