# Independent code review — wave E1 verification tooling

* Reviewer: `code_reviewer` (route 8f7b02), read-only over the tree.
* Tree `/home/pall/projects/.exolon-wave-e1/exolon` @ `32e61e8` (author 06:17:38Z, committer
  06:29:40Z), diff under review = `git diff 0b0dea9..HEAD` (10 modified + 19 added paths,
  +3045/−42). Verification receipt named by the controller: `24249abceeec48d9`.
* Question asked: the change is tooling-only, so **can the tool lie?** (report green while the
  A–D chain is broken / while a debt is live).
* Method: the diff plus executed probes. Every mutation ran in a scratch
  `git clone --no-hardlinks file://…/.exolon-wave-e1/exolon` under `/tmp/e1rev/` (never `cp -a` of
  a linked worktree, never mutate-then-restore in the reviewed tree); clones deleted afterwards.

## VERDICT: FAIL — block on R1. No false green found in `wave_scan` itself.

`wave_scan.py`'s three contours were attacked on ~20 vectors and never once reported green over a
live violation **inside the merged chain** — the fail-closed rules (absent `swiftc`, absent meter,
unparsable verdict, timeout, budget, non-vacuity guard, narrowed `--base`) all resolve to red. What
does not survive the head is the *recorded* green: the suite is red on the exact commit that this
package certifies as green, and three named probes now pass without proving anything.

---

## A. Findings

### R1 — CRITICAL (blocking): the series gate is red on the certified head; the recorded green predates the commit

Reproduced in a fresh clone of `32e61e8` with the same ref layout as the reviewed worktree
(`refs/remotes/origin/main` = `0b0dea9`, HEAD = `32e61e8`):

```
python3 engineering/tools/wave_scan.py --json     # /tmp/e1rev/pinned
  result = WAVE_SCAN_RED   meters = 5/6 green
  wave-b-mapdata  rc=1 passed=8/9 failed=1 (MISMATCH)     (the other five green at 28, 9, 11, 10, 125/125)
python3 …/i-35bac2/evidence/wave_b_check.py       # same clone
  added-lines: 0 стронок кода в 0 изменённых продуктовых файлах
  FAIL no_magic_offsets  →  added-lines скан странно пуст: файлов=0 строк=0     rc=1
```

Measured identically **in the reviewed tree itself** (read-only git queries): `merge-base(HEAD,
origin/main) = 0b0dea9 ≠ HEAD`, and `git diff -U0 0b0dea9 -- Exolon` yields 0 files / 0 added code
lines — wave E1 is a tooling wave, so B's own-delta scan is empty by construction.

Root cause: `engineering/changes/20260924-…-i-35bac2/evidence/wave_b_check.py:688` triggers the
"no product delta → re-anchor to the root base" rule on `merge-base(HEAD, origin/main) == HEAD`.
That holds only when HEAD is *already an ancestor of main* (post-merge) — or when `origin/main` is
synthesised to equal HEAD, which is exactly what the evidence harness does
(`evidence/wave_e1_check.py:176  pin_origin_main(dst, head_sha())`). On a **pre-merge PR head of a
tooling wave** — the only state any review or merge gate ever observes — the condition is false, the
scan is empty, and the ≥7/≥150 non-vacuity guard (`wave_b_check.py:1179`) reddens B.

Why the committed transcripts still say green: `evidence/wave-scan-end-to-end.txt` is stamped
`2026-09-25T05:58Z`, i.e. **before** the commit (06:17/06:29) — its own bucket table proves it
(`range=0b0dea9..HEAD files=0 code_lines=0` for the branch bucket, yet B printed 9/9, which is only
reachable through the re-anchor, i.e. only while HEAD was `0b0dea9`). Same for
`wave-e1-check-green.txt` (06:01Z) and `grok-verify-pr.txt` (06:12Z, `changed=28`). Nothing in the
package re-ran after the commit that this review covers.

Consequences, stated exactly:
* AC-003 ("exits green only if every one is green on the E1 head") and INV-001 are **not met on the
  head**; the brief's own rule "a red there blocks E1, not them" therefore blocks E1.
* The gate fails **closed** (false red, never false green) — no chain debt escapes through this
  defect, and a tooling wave cannot be certified green by `wave_scan` in the pre-merge state.
* Direction of the hazard to disclose to the owner: the temptation this creates is to "fix" the red
  by pinning `origin/main` (as the probe already does) or by running `--only`, which is how a real
  green later becomes a synthetic one.
* Fix: key the re-anchor on the *measured emptiness* of the own delta (`added files == 0`) instead of
  on ref equality, keeping the reason print; and re-record `wave_scan` + `wave_e1_check` on the
  committed head so the transcripts describe the commit they sit in.

Also measured, same run (`/tmp/e1rev/probes`, fresh clone of the head):
`wave_e1_check.py --json` → `WAVE_E1_PROBES_FAIL`, 6 PASS / 5 FAIL:
`cross_wave_suite_green` (AC-003) and `suite_standalone_agreement` (INV-001) fail on R1;
`loader_harness_green` (AC-004) fails with "the control tree still has the fix, so the control
proves nothing"; `no_silent_relaxation` (FORBID-002) fails with "wave_c_check.py shows no edit at
all"; `b_meter_failclosed` (AC-006) fails with "the real refs/remotes/origin/main moved during the
AC-006 controls". AC-001, AC-002, AC-005, AC-007, AC-008, FORBID-001 passed in my independent run.

### R2 — CRITICAL: the attribution contour cannot see untracked new files, while its own bucket name says it does

`wave_scan.py:236-241` (`added_code_lines`) builds added lines from `git diff -U0 <start> [<end>] --
Exolon`; `git diff` never reports untracked files. `wave_scan.py:217` nevertheless names the bucket
`uncommitted (working tree + untracked)`, and the package claims the same coverage (change-spec
AC-002 "added lines 295690b..HEAD union working"; tasks.md AC-002 row).

```
# /tmp/e1rev/plant — fresh clone of 32e61e8
new file Exolon/GameCore/Levels/E1HiddenNew.swift:
    static let y = 544.0 / static let n = 100 + 16 / static let map = "L01S02"
→ violations=0  code_lines=2938 (unchanged)  files=16 (unchanged)  result not red
# same file, syntax error instead:
→ parse contour RED, total=21, names the file  (so only attribution is blind)
```
Independently reproduced in a synthetic two-wave repo: the working-tree *edit* of an existing file
was caught and bucketed, the *untracked* sibling in the same directory was not. Blast radius: the
pre-commit window — precisely when a wave's own additions are reviewable — is unpoliced for any
brand-new product source. This is inherited from wave B's identical `git diff` usage
(`wave_b_check.py:696-720`), so it is not a regression; it is an over-claim plus an untested control
(AC-002's `plant()` only ever writes into already-committed files). Fix: union the untracked
`*.swift` under `Exolon/` (whole file = added lines) or `git add -N` them into a temp index, then
add the untracked-new-file plant to AC-002's controls.

### R3 — CRITICAL (evidence integrity): four named probes are only valid while the change is uncommitted; two now pass vacuously

| probe | line | state at `32e61e8` |
| --- | --- | --- |
| `v3_header_present` inertness control | `wave_e1_check.py:717` `git checkout -- rel_v3` | **passes vacuously** — HEAD already contains the header, so `before` and `after` are the same bytes; the claim "stdout and failure mode byte-identical to the pre-edit copy" is now unprovable by this code path |
| `product_untouched` scope + ≤90-line caps | `:1029-1038, :1050-1067` (`_working_paths()` = working diff only) | **passes vacuously** — reports "0 working paths, 0 sanctioned merged edits"; a later wave that rewrites a merged meter wholesale trips no cap (its product half is *not* vacuous: `:1046` checks `merge-base..HEAD`) |
| `loader_harness_green` revert control | `:667` | fails loudly (rightly refuses to run a control that cannot flip) |
| `no_silent_relaxation` C-edit check | `:1092` `git diff -U0 HEAD -- wave_c_check.py` | fails loudly ("shows no edit at all") |
| `b_meter_failclosed` hygiene assert | `:784` requires `refs/remotes/origin/main == HEAD` in ROOT | fails loudly pre-merge, can only pass in the synthetic layout |

Fix: anchor every one of these to the change base `0b0dea9` (`git show 0b0dea9:<path>`,
`git diff 0b0dea9..HEAD`) instead of `HEAD`, so the controls that name AC-004/AC-005/FORBID-001/
FORBID-002 stay falsifiable after the commit — these probes are the reusable part of E1 and E2 will
cite them.

### R4 — SUGGESTION: a git-ignored Swift file is invisible to *both* contours, and one bare ignore rule reaches a product path

`swift_union:113-121` uses `ls-files --others --exclude-standard` and `git diff`, both of which skip
ignored paths. `.gitignore:17` is a bare `coverage/`, which matches at any depth:
`git check-ignore -v Exolon/GameCore/coverage/HiddenBad.swift` → `.gitignore:17:coverage/`. A file
at that path carrying a **syntax error plus `+ 16` plus `544.0` plus `L04S11`** leaves the parse
contour at `files=20 failures=0` and attribution at `2938/16, violations=0` — byte-identical to the
control run with the file removed. Same for `**/harness/fixtures/`. Impact is bounded (an ignored
file cannot be committed, so it cannot ship; and the wave-C meter's `rglob('*.swift')` *does* see
such paths), but "plus untracked `*.swift`" is materially incomplete as written. Fix: cross-check a
filesystem `*.swift` walk against the git-derived set and redden on a mismatch outside an explicit
allow-list.

### R5 — SUGGESTION: the `±16` added-line predicate is bypassable by syntax, and that form is not in the disclosed residuals

`MAGIC_PATTERNS` (`wave_scan.py:59-63`) uses `[-+] ?\b16\b`. Planted in a tracked product file's
working-tree additions, each on its own line:

| form | verdict |
| --- | --- |
| `100 + 16` | RED ✓ |
| `100 &+ 16` | RED ✓ |
| `acc += 16` | **green (missed)** |
| `100 +  16` (two spaces) | **green (missed)** |
| `100 + (16)` | **green (missed)** |
| `100 + 1_6`, `100 + 0x10` | green (missed) |

Parity with the merged predicate is genuine — I compared `wave_scan.strip_comments` with
`wave_b_check.strip_comments` over all 4 219 added lines of `295690b..worktree` and got **0
mismatches**, so this is inherited leniency, deliberately kept ("byte-compatible on purpose"). Two
honesty caveats though: (a) `tasks.md` discloses only the `//`-inside-a-string residual, not the
operator/whitespace forms; (b) wave B's *seam* scan uses the stricter bare `\b16\b` over ten named
seams (`wave_b_check.py:1148`) and `wave_scan` does **not** port that scan — its coverage of those
seams comes only from running B as a meter (which is red per R1). Recommend adding the `+= 16` and
`+ (16)` forms to the disclosed residual list, or a `[-+]= ?\(?\s*\b16\b` twin.

### R6 — SUGGESTION: the loader meter's recorded number (125/125) is not pinned by `expected=1`

`METERS` gives `loader-harness-125maps` `expected=1` and `verdicts('LOADER')` (
`wave_scan.py:344-351`) only requires `ok == total and failures == 0`; neither `run.sh` nor
`harness/main.swift:29` asserts the corpus size (`ok/\(fm.count)`). Measured: in a clone with
`Exolon/Resources/L05S*.tmx` removed (100 maps), the meter reported
`expected=1 passed=1 failed=0 green=True verdict='REAL MAPS ok=100/100 failures=0'`. Not a live hole
— the suite still reddens on a shrunken corpus through wave B's `карт N != 125`
(`wave_b_check.py:722-723`) — but AC-003's "recorded sub-results … 125/125" is only recorded for the
`verdict_line`, not asserted. Fix: pin the pair `(125, 125)`.

### R7 — SUGGESTION: `verdict_line` can name a success marker the meter never printed

`wave_scan.py:328` returns `('ALL_WAVE_B_CHECKS_MATCH_SPEC' if failed == 0 else 'MISMATCH')` — a
synthesised string, not a line from the meter's output. Measured with the remote-less clone
(`wave_b_check.py:675` exits 4, prints no marker):
`rc=4 passed=6 failed=0 green=False verdict_line='ALL_WAVE_B_CHECKS_MATCH_SPEC'`, and the suite
problem line reads `wave-b-mapdata: rc=4 passed=6/9 failed=0 (ALL_WAVE_B_CHECKS_MATCH_SPEC)`. The
*gate* is correct (`green` requires `rc == 0`), but SIG-001's machine-readable per-meter line — the
field every transcript quotes as the meter's verdict — asserts a marker for a run that fail-closed.
Echo the meter's own line, or emit `NO VERDICT MARKER`.

### R8 — SUGGESTION: `WAVE_SCAN_GREEN_PARTIAL` is a string superset of `WAVE_SCAN_GREEN`

`wave_scan.py:470-474`. `RESULT: WAVE_SCAN_GREEN_PARTIAL` (exit 3) matches `grep WAVE_SCAN_GREEN`,
so a restricted contour can be mis-read as the series verdict by any consumer that greps instead of
using `--json` (`partial: true`) or the exit code — a live risk precisely because R1 pushes
operators toward `--only`. Rename to `WAVE_SCAN_PARTIAL`, or document the exact-match requirement at
the top of the exit-code table.

### R9 — SUGGESTION: make the re-anchor decision machine-visible

The reason for re-anchoring is a prose `print` (`wave_b_check.py:689-692`); the only machine-checkable
trace is the existing `added-lines: N стронок кода в M …` line, which AC-006 does assert (≥150/≥7).
The non-vacuity guard itself is sound and cannot be bought off by a narrowed anchor — measured:
`--base HEAD`, `--base HEAD~1`, `--base 0b0dea9` all give `code_lines=0 files=0 → WAVE_SCAN_RED
("the root-anchored scan is strangely empty")`, and `--base deadbeef` gives `REFUSED … rc=2`. Add
`WAVE_BASE=295690b reason=no-product-delta` so a log line cannot be re-interpreted later.

### R10 — MEDIUM (provenance): `README.md` is edited by this commit while `tasks.md` records it as not an E1 edit

`git diff --name-status 0b0dea9..HEAD` includes `M README.md` (+35/−0: new "Map-data physics (wave
B)", "Stage-end & release layer (wave D)" and "Verification tooling (wave E1)" sections). But
`tasks.md` Residuals states: *"E1's own scope forbids touching anything outside
`engineering/tools/`, the three merged touch-points and this package, so the README line … is a
PR-body/controller step, not an E1 file edit."* `README.md` is in neither `E1_PREFIXES` nor
`SANCTIONED_MERGED_EDITS` (`wave_e1_check.py:1015-1026`), so had the edit been uncommitted,
`product_untouched` would have failed with "wave E1 edited files outside its scope: ['README.md']".
AGENTS.md does require the README to match the tree, so the *content* is desirable — the *record* is
wrong. Either add README.md to the sanctioned list with a tasks.md entry, or move it out of the
commit. (Its added text is itself accurate: it describes waves B/D/E1 as landed, and I verified wave
B's and D's claims against their meters' own outputs.)

### R11 — NICE TO HAVE: `CONSTANT_ALLOW` is laxer than the predicate it claims to re-run, and has no expiry

`wave_scan.py:66` exempts `Exolon/GameCore/GameConstants.swift` from the two numeric predicates;
wave B's own added-lines scan has **no** such exemption (`wave_b_check.py:1167-1178`), so a future
`+ 16` in that file passes wave_scan and reddens B. Load-bearing check: I applied all three
predicates to every one of the 2 938 added lines from `295690b` — the match set is **empty**, so the
allow-list currently hides nothing and FORBID-002's "narrowed to hide violations" does not apply to
this head (measured, not inferred). Add the same exemption to B (or drop it here) and pin the empty
match set as a control so the exemption cannot silently start carrying the green.

---

## B. Certified true (attacked, did not flip)

1. **Exolon zero-touch (FORBID-001): proven at the strongest level.** `git rev-parse 0b0dea9:Exolon`
   == `HEAD:Exolon` (`2573904c69ee783df5c005fcf1db83db0b7063be`) and `0b0dea9:Exolon.xcodeproj` ==
   `HEAD:Exolon.xcodeproj` (`57913d7247bcd8274339716410752191dac2ba57`); `git status` clean; no
   untracked and no ignored-but-present file under `Exolon`. The only dirty entry in the reviewed
   worktree during my run was a sibling reviewer's `evidence/review-test.md` (not mine, not mine to
   touch).
2. **All nine merged-file edits are exactly what `tasks.md` records** — function-level AST
   comparison `0b0dea9` → `HEAD`:
   `run.sh` +6 header comment lines and one compile-line change adding
   `"$ROOT/Exolon/GameCore/GameConstants.swift"` (step 6's negative control untouched);
   `v3_measurements.py` 9→9 defs, **0 functions changed**, +12 lines, all docstring prose;
   `wave_c_check.py` 72→72 defs, only `stale_mirror_report`, and with every string constant masked
   the two ASTs are **identical** (literal-only edit) with `%`-spec arity preserved 5→5;
   `wave_b_check.py` 38→38 defs, only `wave_base` (`no_magic_offsets`, which holds the guard and the
   predicates, byte-identical); `gameplay_log_check.py` 79→79 defs, only `emission_cost_budget`,
   `hot_path_is_allocation_free` **byte-identical**; `harness/main.swift` confined to `enum Harness`
   (new `warn` + `warnings`) and `scenarioCostBudget`; `stage_boundary_check.py` 23→26 defs =
   `warp_debug_only` plus three new pbx readers, no other existing function touched;
   `last-run.txt`/`harness/README.md` re-record the transcript at `HEAD=0b0dea9`.
3. **`v3_measurements.py` behaviorally inert — proved independently of R3's broken control.** In a
   clone, running the `0b0dea9` copy and the `HEAD` copy in place: both `rc=1`, both `stdout`
   empty (0 chars), identical last stderr line (`AttributeError: 'NoneType' object has no attribute
   'group'`) → the header changed nothing, and the Rulings disclosure is accurate (the mirror
   aborts before printing 76/51; it does not print rc=0).
4. **AC-006 fail-closed half holds.** Remote-less clone (`git update-ref -d
   refs/remotes/origin/main`, verified unresolvable): `wave_b_check.py` → `rc=4`, explicit
   `FAIL-CLOSED: refs/remotes/origin/main отсутствует …` on stderr, and **no** `added-lines:` scan
   line — the old silent wide fallback is gone.
5. **AC-008 (warp GUID binding) is a genuine strengthening.** The condition is now derived from
   `PBXProject`/`PBXNativeTarget → buildConfigurationList → buildConfigurations`
   (`stage_boundary_check.py:628-680`), must appear in exactly one block, must be the *project*
   Debug block, and a reader-vacuity guard (configs<4 or no owners) reddens instead of asserting on
   nothing. `wave_e1_check.warp_guid_bound` passed in my own run over the committed pbxproj:
   project-Release / target-Debug / **target-Release (the reviewer mutation)** / duplicate all
   redden, and the real `Exolon.xcodeproj` stayed byte-clean.
6. **AC-007 (soft M3 band) keeps its hard twins.** Read of the new
   `emission_cost_budget`: soft = `percent > 5`, `percent > 0.5`, `producer >= 1_000`; hard =
   `producer <= 0`, `control < producer * 5`, `capacity < 3_600 * 8`, plus the untouched static
   allocation scan. `harness/main.swift` mirrors it: `producerNs > 1`, the >5× relation and the 8×
   drain stay `Harness.check`; only the four absolute bands moved to `Harness.warn`.
   `m3_soft_band` passed in my run.
7. **Bucketing behaves as claimed** (synthetic two-wave repo with real `--no-ff` PR merges): a plant
   in wave A's territory → `wave-a`, in wave B's → `wave-b`; a line **authored by A and edited by B**
   (`edited_later = 7` → `= 100 + 16`) is attributed to **`wave-b`** (the added side), not hidden; a
   working-tree plant → `uncommitted …`; a committed plant on the branch → the branch bucket; a
   small total delta trips the `≥7/≥150` guard. On the real head the buckets partition the range
   contiguously (`295690b..17a742a..3407c37..817bf52..0b0dea9..HEAD..worktree`) and any violation —
   including an `unattributed` one — always produces a `problems[]` entry, so misattribution cannot
   buy a green.
8. **Parse contour is honest and self-falsifying.** Union of 20 files (16 product + 4 evidence) with
   a planted committed syntax error reddening and naming the file; untracked files enter the set —
   including names with **spaces** (`E1 Hidden Space.swift`) and **non-ASCII**
   (`E1Проверка.swift`) — thanks to `core.quotepath=false` and argument-vector (non-shell) git
   calls; the selftest requires broken ≠ good and fails the contour if it does not; `swiftc`
   absence reddens the whole contour (`no_silent_relaxation` control passed in my run).
9. **Suite/standalone counters are two implementations, not one.** `wave_e1_check.py` imports only
   stdlib (`argparse json os re shutil subprocess sys time pathlib`) and never imports `wave_scan` —
   it runs the tool as a subprocess (`wave_e1_check.py:233-256`) and re-parses meter output with its
   own `count_verdicts` (`:272`); `wave_scan` re-runs meters in-process from `METERS`. The two
   tables' expected counts are separately typed literals, and the B branches genuinely differ
   (`wave_scan.verdicts` raises on "no verdict lines", `count_verdicts` does not). Caveat worth
   stating: the regexes are line-for-line the same, so INV-001 proves subprocess/determinism
   agreement, not immunity to a shared mis-read of a meter's own format — and it currently FAILS at
   this head (R1) rather than silently agreeing.
10. **The suite does not write into the tree**: after the full 6-meter run in `/tmp/e1rev/pinned`,
    `git status --porcelain` was empty (only my own `nohup.out`), matching the `tree_writes=none`
    claim; `git fsck`-level hygiene of the *shared* repository is clean — `refs/heads/origin/`
    count 0 and the worktree list is unchanged at 7 entries.
11. `python3 -m ruff check` on `wave_scan.py` + `wave_e1_check.py` → "All checks passed!" (rc=0);
    `git diff --check 0b0dea9..HEAD` → rc=0 in the committed state.

## C. What I did not/could not verify

* Anything macOS-side (Track A/B handout protocol, `xcodebuild`, signing): no Apple host; the meters
  record those as externally blocked and E1 does not claim them.
* The controller's receipt id `24249abceeec48d9` itself (`.grok-stack/runtime` is deliberately not
  Git content); I only checked that the *transcripts committed into the package* were recorded
  pre-commit and do not reproduce post-commit (R1).
* Whether the red in R1 disappears after the PR merges (it should: `main` ⊇ HEAD ⇒ re-anchor fires);
  that is a post-merge state, not merge authority, and it does not retroactively certify the head.

## D. Required to turn this into a pass

1. R1: re-key the re-anchor on "own product delta measured empty" (not `merge-base == HEAD`), re-run
   `python3 engineering/tools/wave_scan.py` **and** `wave_e1_check.py` on the committed head, and
   replace the three pre-commit transcripts with head-bound ones.
2. R2: untracked new product files into the attribution union + an AC-002 control that plants a
   violation in a brand-new untracked file (must redden) — or rename the bucket and narrow the AC-002
   wording to "tracked working tree".
3. R3: re-anchor the AC-004/AC-005/FORBID-001/FORBID-002 controls to `0b0dea9` so they stay
   falsifiable after commit; R10: reconcile `README.md` with the recorded scope.
4. R4–R9 are hardening/disclosure items — none of them lets the tool report green over a broken
   chain today, and they can ship as named residuals if the owner accepts that.
