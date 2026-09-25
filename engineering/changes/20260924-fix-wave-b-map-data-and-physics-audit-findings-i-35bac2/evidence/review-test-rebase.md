# Test review — REBASE verification pass, wave B (`…-i-35bac2`)

Scope: the four items named by the rebase brief — (1) whether the new FORBID-001 scan base
(`wave_base()` → `git merge-base HEAD origin/main`) is weakenable by attribution to the other side,
(2) the post-rebase "byte-identical regeneration" claim for `wave_b_swift.txt`, (3) wave A's
28-check contract story executed on the merged bytes, (4) my delta-pass controls subset re-run.
Read-only: the only file written in this tree is this one. Every mutation ran in
`/tmp/lab/repo` (a copy of this worktree carrying the repository's own `.git`, so
`merge-base HEAD origin/main` resolves identically: `HEAD` = `6c7dfe5`, merge-base = `17a742a`,
`git status` clean before and after each run).

## VERDICT: **PASS** — for the rebase specifically.

The scan-base change is not weakenable in the direction the brief asked about: I planted
per-map literals and a `±16` offset seven different ways (including the two most adversarial —
verbatim duplication of a *base* line, and a wave-B edit laid *on top of a wave-A line*) and every
one reddened. The degenerate-anchoring cases fail closed, and the fallback goes *wider*, never
narrower. Regeneration is byte-identical by my own `cmp`, not by the meter's word. Wave A's
28/28 holds on these bytes. Two residual scanner holes (one new, one timing) and one quantified
coverage reduction are nits/suggestions; none blocks this rebase.

## 0. Rebase shape, and one bookkeeping discrepancy worth naming

`git log` is linear: `6c7dfe5` (wave B) directly on `17a742a` = `origin/main` = the merge of PR #20
(wave A). So `merge-base(HEAD, origin/main) == origin/main`, and wave B's scan base is exactly the
post-A main.

The committed `wave_b_check_green.txt` header still says *"ПОСЛЕ REBASE … (head e520884)"*, and
`e520884 != 6c7dfe5`. `git diff --stat e520884 6c7dfe5` = 5 files, **all inside this change
package** (`wave_b_check.py` +21 lines — the `wave_base()` anchoring change itself — `wave_b_check_green.txt`,
`wave_b_harness/last-run.txt` (build-dir PID only), `release.md`, `tasks.md`), **zero bytes under
`Exolon/`**. Substance of the green claim therefore survives, but the header is off by one amend and
everything below is my own re-measurement at `6c7dfe5`, not that artifact.

## 1. Item 1 — is the merge-base-anchored added-lines scan weakenable? No (measured 9 ways)

Mechanism under test: `wave_base()` (`wave_b_check.py:646-662`) → `git_added_lines(base)`
(`:663-680`, `git diff -U0 <base> -- Exolon`, keeping `+` lines of `*.swift`) → consumed at
`:1130` inside `no_magic_offsets()` (`:1080`), predicates at `:1141-1143`
(`[-+] ?\b16\b`, `\b528\b|\b544\b|\b560\b`, `L\d{2}S\d{2}`), non-vacuity guard at `:1146`
(`n_files >= 7 and n_code >= 150`), fail-closed on absent diff at `:1132`.

Lab baseline first (the control that makes every red below attributable): clean lab copy, live run
→ `rc=0`, `added-lines: 237 стронок кода в 8 изменённых продуктовых файлах` — identical to the real
tree's number.

| id | hide attempt planted in the lab | meter verdict | evidence |
| --- | --- | --- | --- |
| **M1** (required) | `if name == "L01S02" { return 148 }` inside a new `private static func spawnGroundOverride(forName:)` in `TMXLevelRuntime.swift` (the file that already carries baseline per-map tables at `:450`/`:525-535`) | **`rc=1`, `FAIL no_magic_offsets`** | `FORBID-001 added Exolon/GameCore/Levels/TMXLevelRuntime.swift: per-map имя: if name == "L01S02" { return 148 }` (count line moved 237→241) |
| **M2** | verbatim duplicate of an **existing base** per-map table line (`            "L01S01": [(28,344,.white),…`, base line 525) inserted adjacent to itself — "hide by copying text that is already in the base" | **`rc=1`, `FAIL no_magic_offsets`** | `git diff` still emits it as a `+` line (diff is line-count based, not novelty based) → same per-map error |
| **M7a** | per-map line in `GameScene.swift`, a product file wave B never touched | **`rc=1`, `FAIL no_magic_offsets`** | `FORBID-001 added Exolon/GameCore/GameScene.swift: per-map имя: …` (scan is directory-wide, not "B's 8 files") |
| **M7b** | per-map line **and** `return y - 16` in `Player.swift` | **`rc=1`**, two hits | `… ±16 смещение: return y - 16` + `… per-map имя: …` |
| **M8** | wave-B edit appended **onto a line wave A authored** (`private var heldStepsByAction = [Int32](repeating: 0, count: 10)`) — the literal "attribute it to the other side" play | **`rc=1`, `FAIL no_magic_offsets`** | the `+` side of an A-line edit is scanned: `FORBID-001 added …GameScene.swift: per-map имя: private var heldStepsByAction = … if name == "L01S02" { }` |
| **P1** | brand-new product file `Exolon/GameCore/Levels/WaveBReviewProbe.swift`, staged | **`rc=1`**, `no_magic_offsets` **and** `single_surface_query` | per-map hit + FORBID-002's filesystem glob caught the second surface definition |
| **M3** | anchoring degeneracy: `origin/main` advanced to include wave B ⇒ `merge-base == HEAD` ⇒ empty added set | **`rc=1`** (fail **closed**) | `added-lines: 0 стронок кода в 0 изменённых продуктовых файлах` + `added-lines скан странно пуст: файлов=0 строк=0` — the guard at `:1146` is what keeps the re-anchoring from silently becoming a no-op |
| **M5** | `refs/remotes/origin/main` deleted (fresh clone) ⇒ `git merge-base` rc=128 ⇒ documented fallback `295690b` | `rc=0`, scan **widens** to `2731 стронок кода в 16 … файлах` | the failure direction is fail-safe: no ref ⇒ *more* lines scanned, never fewer |
| **M6** | lab re-baseline after the battery | `rc=0`, 237/8 | lab was not left dirty (`git status` clean) |

**Answer to the brief's question: no.** The base is a *commit*, not an author. A line escapes the
scan iff that exact text is already in the merge-base tree — which wave B cannot arrange for its own
new code: insertion, verbatim duplication of a base line (`M2`), placement in an untouched file
(`M7a`), placement in a new file (`P1`), and editing a wave-A line (`M8`) all still produce a `+`
line. Attribution soundness measured: of the 3 355 raw added lines the re-anchoring drops, **0**
are absent from the `17a742a` blobs — i.e. every dropped line really is pre-existing base content,
not B-authored code laundered into the "other side".

The two base anchors the change promises *not* to move (`:651-652` docstring) are intact, checked
independently of the meter: `git_show_base()` still hardcodes `295690b` (`:637-638`),
`tmx_base_hashes.json` still declares `generated_from_commit 295690b` and its 125 entries match
`git ls-tree -r 295690b -- Exolon/Resources` with **0 mismatches**; 0 TMX files differ in the
working tree since `295690b`.

### 1a. The one real cost of re-anchoring — quantified, and it is not this wave's problem to fix

| base | raw added swift lines | files | non-comment code lines (meter's count) |
| --- | --- | --- | --- |
| `295690b` (old) | 3 780 | 16 | 2 731 |
| merge-base `17a742a` (new) | 420 | 8 | 237 |
| dropped (attributed to wave A) | 3 355 | 12 | 2 494 |

I ran the meter's own three predicates over those 2 494 A-side code lines (12 files: the five new
`Diagnostics/*`, `GameScene`, `InputState`, `GameConstants`, `TMXLevelRuntime`, `LevelObstacles`,
`Player`, `macOS/AppDelegate`): **0 hits**, with a positive control that fires on the identical
predicate. Seven lines merely mention the numerals legitimately (`let capacity = max(16, …)`,
`var candidate = 16`, `case playerThrowGrenade = 16`, …) and none matches `[-+] ?\b16\b` /
`528|544|560` / `L\d{2}S\d{2}`. Consistently, `M5` shows the *wide* scan is green on these bytes —
so the anchoring change flips no verdict in this tree; it buys honest attribution at the price of
coverage.

The gap to name plainly: **`gameplay_log_check.py` (wave A, merged) contains no added-lines/git-diff
attribution scan at all** (`grep -n "merge-base|git diff|added-lines"` → no hits), so after this
change nobody re-scans the A-side delta for magic offsets or per-map tables. Today's exposure is
measured-zero, and it is not a rebase defect — but the wave-A/C/D chain inherits it.
**Suggestion (non-blocking, belongs to the controller, not to this branch):** run the FORBID-001
predicate once per wave over the *newly merged* base delta (my 15-line dropped-line scanner in §5
does exactly that), or make each wave's verifier own its own added-lines scan before its lines
become base for the next wave.

## 2. Item 2 — "byte-identical regeneration post-rebase": HOLDS, by my own measurement

```
$ bash …/evidence/wave_b_harness/run.sh > /tmp/live_swift.txt     # rc=0, 2.7 s, at 6c7dfe5
$ cmp /tmp/live_swift.txt …/evidence/wave_b_swift.txt   → identical
$ wc -c → 54 267 B, 434 lines; sha256 13bab912988760c69276d1d4f2459123556dd2e15797ba2ef1364d9adf31b891 (both)
stderr: root=/home/pall/projects/.exolon-wave-b/exolon
        OK: дельта сборочной копии загрузчика = ровно 1 строка импорта
        OK: без стаба не собирается (… error: no such module 'CoreGraphics')
```

Both genuine controls print (the `+1 import` byte-check and the fatal-on-success no-shim negative
control). The meter's independent live run agrees: `артефакт Swift: живой (совпал: True)`, 9× PASS,
`rc=0`, `elapsed=3.0s`. My live stdout also matches the committed `wave_b_check_green.txt` body
except for `elapsed` (3.0 vs 3.1 s) and the shell-appended `rc=0` line — so the published green text
describes these bytes even though its header names the pre-amend head (§0).

## 3. Item 3 — wave A's contract on the merged tree: 28/28, `rc=0`

`python3 …/20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c/evidence/gameplay_log_check.py`
on `/home/pall/projects/.exolon-wave-b/exolon` at `6c7dfe5` → 28 `PASS` lines, 0 `FAIL`,
`RESULT: PASS (28/28 checks passed)`, `rc=0`, 68 s wall (00:00:50→00:01:58 UTC), artifacts in
`/tmp/exolon-harness-9s45huqn`. The wave-B product/physics edits did not disturb A's log
contract, tick/state-machine fixes, envelope/schema conformance or the `FORBID-003` "no log file in
the clone" clause (it self-proves it: `every log.begin.path is outside it`). `git status --porcelain`
was empty after the run: A's checker writes nothing into the tree.

## 4. Item 4 — delta-pass controls subset, re-run on merged bytes

Lab runs, all reverted (`git checkout -- .`, lab clean at the end):

| control (delta-pass id) | this run | verdict |
| --- | --- | --- |
| truncated executed stream — artifact cut to 260/434 lines, `--artifact-only` (missing-evidence fail-closed, my §5 claim) | `rc=1`, `FAIL spawn_ground_all_maps`, `piston_anchor_all_pistons`, `beam_shared_hp_all_maps`, `pinned_geometry_unchanged` (`rects совпали не на всех картах: 74`) | **holds** — no silent skip when the stream is short |
| GEOMETRY line only deleted, `--artifact-only` (**N-1**) | `rc=0`, 9× PASS | **N-1 still open** on merged bytes (nit, unchanged: `if geom:` guard skips) |
| same deletion, LIVE harness | `rc=1`, `FAIL controls_flip` (`вывод живого harness не совпал с закоммиченным артефактом`, `совпал: False`) | N-1's exposure still needs *both* a doctored artifact and the explicit offline opt-in |
| spawn `halfWindow` ×2 (`TMXMapLoader.swift:117` `CGFloat(tileHeight)` → `* 2`), live (**D4 / §M13**) | `rc=1`, `FAIL spawn_ground_all_maps` + `controls_flip`, divergence maps exactly `['L01S12.tmx','L01S13.tmx','L01S20.tmx','L01S22.tmx','L01S23.tmx']` | **reproduces** — same five maps as published, on rebased bytes |
| halfWindow ×2 with `swiftc` off PATH (**D4b**) | 9× PASS lines but `RESULT: TOOL_ABSENT`, **`rc=3`** | **still closed** — a mutated product cannot earn a silent green without the toolchain (the mirror only compares against the committed stream) |
| clean merged tree with `swiftc` off PATH (**D1b class**) | `RESULT: TOOL_ABSENT`, **`rc=3`** | no false `rc=0` |

Measurement caveat, stated so the record is honest: my driver labelled these runs with
`bash -lc command -v swiftc`, and a login shell re-sources the profile that adds `/opt/swift`, so the
label printed `yes`. The authoritative evidence is the meter's own `shutil.which("swiftc")` under
`PATH=/usr/bin:/bin` — its `TOOL_ABSENT` branch (`:463`, `:1450`) is exactly what fired, producing
`rc=3` in both no-toolchain cases.

## 5. Residual holes found by this pass (neither rebase-introduced, neither blocking)

* **R-a (minor, contrived — the added-lines scan *is* strippable, just not by attribution).**
  `strip_comments()` (`:1302-1305`) is `re.sub(r"///?.*", "", block)` — it cuts at the first `//`
  *inside a string literal* too. So a violation placed after such a substring on the same physical
  line is invisible to both the added-lines scan and the 10-seam scan. Hidden, `rc=0`:
  `    let probeURL = "https://example" ; if mapName == "L01S02" { groundY = 544 } ; let _ = probeURL`
  Control without the URL prefix (same predicate, same file) → `rc=1` with *both* the per-map and the
  pinned-boundary hits. Pre-existing (the same helper serves the fallback base path, so `M5` behaves
  identically), requires deliberate self-boobytrapping, and a human reading the diff sees the whole
  line. One-line hardening: scan per-map names/numerals on the raw line and use `strip_comments`
  only for the offset predicates — or strip line comments outside quoted spans.
* **R-b (minor, timing-only — untracked files escape the diff).** `git diff <base>` cannot see
  untracked files: identical new product file left unstaged ⇒ `no_magic_offsets` **PASS** (`P2`);
  the moment it is staged ⇒ **FAIL** (`P1`). No merge-authority exposure (an untracked file never
  reaches the PR), and FORBID-002's filesystem glob still caught it. Optional hardening: also scan
  `git ls-files --others --exclude-standard -- Exolon '*.swift'`.

## 6. Hygiene

Real tree: `git status --porcelain` empty before the run, empty after the meter, and empty after
wave A's checker — I changed no byte except this report (`write_if_changed` kept
`wave_b_deltas.md` byte-stable; harness stderr went to a `/tmp` scratch, so the committed
`wave_b_harness/last-run.txt` stayed static as designed). All nine mutations plus the artifact
truncations lived in `/tmp/lab/repo`, which ends clean.
Standing consequence for the controller (**P-1** from my delta pass, unchanged by the rebase):
this file moving into the tree shifts the tree fingerprint, so `grok_verify`/`grok_review`
must be recorded *after* this write and after the other reviewers settle — the committed
`wave_b_check_green.txt` header additionally needs its head string corrected to `6c7dfe5` (cosmetic,
but the receipt binds to it).
**Measured, not predicted:** a second review writer ran in this same tree concurrently —
`evidence/review-code-rebase.md` appeared at 00:12:56 (18 079 B, size stable 20 s later), alongside
my `review-test-rebase.md` at 00:12:52. Two untracked reviewer files, both landing after the
`wave_b_check.py` edit that defines the anchoring under review: the gate must be re-recorded once,
after *both* have settled, and any later edit to `wave_b_check.py` in response to either report
invalidates that recording again.

Reproduction: labs are `/tmp/lab/drive.py` (scan-base battery M1–M6), `/tmp/lab/drive2.py`
(controls T1/T2/H1/N1/N2 + M7a/b), `/tmp/lab/drive3.py` (P1/P2 + manifest anchors),
`/tmp/lab/drive4.py` (M8/M9); the A-side dropped-line predicate check is the inline
`python3 - <<'PY'` block quoted in §1a (functions `added()`/`strip()` reproduce the meter's).

## 7. Disposition

**PASS for the rebase.** Wave B's evidence is reproducible on the rebased bytes: 9/9 green live with
a byte-identical artifact, 28/28 for wave A on the same tree, the FORBID-001 added-lines scan
demonstrably non-weakenable by attribution (7 planted violations, 7 reds; degenerate anchoring fails
closed; missing-ref fallback goes wider), and every delta-pass control I relied on still flips the
same way. Required before merge, in order: correct the green-run head string, re-record the local
receipt at `6c7dfe5` after all review writers settle (P-1). Recommended, not blocking: the
controller-side per-wave predicate run of §1a (the A-side delta is currently unpoliced by anyone),
apply N-1, and optionally close R-a/R-b.
