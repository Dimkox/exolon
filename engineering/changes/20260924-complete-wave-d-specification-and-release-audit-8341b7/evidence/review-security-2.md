# Review: security_reviewer — part 2 (probe/verifier boundary + handout integrity)

- Change: `20260924-complete-wave-d-specification-and-release-audit-8341b7`
- Tree: `/home/pall/projects/.exolon-wave-d/exolon` @ `84b7813f0dc9c8f25c93967908df2410dc385da2`
  (branch `codex/wave-d-spec-release-20260924`, PR base `817bf52` = `origin/main`)
- Part 1 (product/build-settings scope): `evidence/review-security-1.md` — PASS. No overlap.
- Mode: read-only over the tree. The only write in the tree is this file. All mutation and
  execution ran in a `git clone --no-hardlinks` at `/tmp/secd2` (`git status --porcelain` empty
  at the end of the session) plus throwaway copies `/tmp/secd3|4|5`.
- Harness (new this part): a logging macOS-toolchain shim set (`uname`, `sw_vers`, `scutil`,
  `md5`, `defaults`, `plutil`, `codesign`, `xcodebuild`, `xcrun`, `spctl`, `xattr`, `ditto`,
  `security`, `notarytool`) that appends the **exact argv of every invocation** to a per-case
  log, plus `script -q -e` to give the probe a real pty. This runs the *shipped probe bytes*
  (`git hash-object engineering/runbooks/macos-probe.sh` = `06d168ae…` = `HEAD:…`), never a
  re-typed copy.
- Checker runs on the pristine clone: `macos_handout_check.py --root .` → 10/10 PASS, rc=0
  (PHASE=D1 detected); `--root . --report` → `MACOS_EVIDENCE=ABSENT (unverified)`, rc=1.
- Note for whoever closes the gate: `tree_fingerprint` counts untracked files under
  `engineering/changes/`, so writing review evidence itself moves it. Measured on this host: the
  pristine `84b7813` clone fingerprints to `ecff8744067d5579…` (the value part 1 cites), while a
  working tree carrying an unsealed review report fingerprints differently (`3366bfc79d4ec9d9…`
  with part 1's file still untracked). Any local receipt recorded before this file landed is stale
  for that reason alone, not because a product file changed — re-run the final gate after all
  writers in this tree are done.

### Baseline drift during this review (measured, findings re-verified on the new head)

While this part was running, the branch advanced: `84b7813` → `377e7ae599253365ade98ff919b87537ed3aab2f`
("docs(release): fill release/rollback plans and rebind wave-D claims to the typed spec"), which
also committed part 1's report and a `review-release.md`. Every measurement below was taken against
a clone pinned at the briefed head `84b7813`; the delta was then checked and this part re-run at
`377e7ae`:

- Files cited in Items 1, 2, 4, 5 — `engineering/runbooks/macos-probe.sh`, both contract schemas,
  `Exolon/Exolon.entitlements`, `Exolon/GameCore/Diagnostics/*`, `macos-handout/README.md` — are
  **byte-identical** between the two heads, so those items and all their line citations are
  unaffected.
- `macos_handout_check.py` is the only file in this part's scope that moved (+21/−10):
  `DECLARED_CUTOVER_SET` was narrowed to `{hardened_runtime_key_count}` with a new
  `DECLARED_NON_RED_KEYS` (`:163` at the new head) and `cutover_set_exact` was rewritten to require
  liveness of every declared key. That is FORBID-002 territory, outside this part's brief.
- Two hunks moved the checker's line numbers: +7 for everything after `:160` and a further +4 for
  everything after `cutover_set_exact`'s body (`:1534`), i.e. **+7 above the second hunk, +11
  below it**. Mapped (old→new, verified by grep at `377e7ae`):
  `tree_fingerprint()` `:249-263`→`:256-270`, R2 digest block `:747-763`→`:754-770`,
  R3 `repo_head` `:767-771`→`:774-778`, R3 blob `:773-778`→`:780-785`, **R3 fingerprint
  `:779-784`→`:786-791`, the fail-open clause `:783`→`:790`**, R5 `:810-826`→`:817-833`,
  R7 `:832-833`→`:839-840`, `evaluate_handout` `:995`→`:1002`,
  `merged_package_is_immutable` `:1072`→`:1079` (calls `:1131`/`:1487`→`:1138`/`:1494`),
  `HYGIENE_SCOPE` `:1082-1084`→`:1089-1091`, `evidence_hygiene` `:1095`→`:1102`,
  agent-boundary taint/ok-case loops `:1367`/`:1380`→`:1374`/`:1387` (+7); and +11 for the two
  entries below the second hunk: derive's `if fingerprint:` `:1730-1732`→`:1741-1743`,
  `--report` rc mapping `:1741-1746`→`:1752-1757`.
- Re-verified at `377e7ae` in a fresh clone: `--root . ` → 10/10 PASS rc=0 (PHASE=D1);
  `--report` → `MACOS_EVIDENCE=ABSENT (unverified)` rc=1 (item 3's absence property holds on both
  heads); F-2's honest on-disk seal → `MACOS_EVIDENCE=STALE` rc=1; and F-1's planted
  zero-fingerprint report on a root with `.grok-stack` removed → **`MACOS_EVIDENCE=OK`, rc=0**.
  No verdict in this report changes.

---

## Item 1 — the human-run gate in `engineering/runbooks/macos-probe.sh` — **PASS** (3 suggestions)

**Reachability of the distribution-side lane.** The only lane that executes distribution tools is
section I, gated by `TRACK_B` — `xcodebuild -exportArchive` (`:633`), `xcrun notarytool submit`
(`:644`), `notarytool log` (`:652`), `notarytool info` (`:655`), `stapler staple` (`:666`),
`stapler validate` (`:669`), then `ditto` (`:674`), `xattr -w` (`:677`) and `spctl -a -t exec`
(`:680`) on the staged copy. `TRACK_B` is set to 1 (`:598`) only after five ordered gates in
section H (`:559-624`): `WITH_SIGNING=1` (`:561`) → `EXOLON_HUMAN_SIGNING_RUN=1` (`:562`, `exit 77`
at `:566`) → `[ ! -t 0 ]` (`:568`, `exit 77` at `:572`) → the typed attestation read and compared
for equality (`:576-584`, `exit 77` at `:583`) → profile NAME present (`:585-589`, `exit 78`) and
shape-valid (`:590-594`, `exit 78`). `TRACK_B=0` is initialised at `:560`, so no path reaches `1`
without all five. Measured (each row is one real probe run; `dist` = export/notarytool/stapler
invocations):

| case | envs | stdin | rc | verdict line | dist calls |
|---|---|---|---|---|---|
| T1 | `WITH_SIGNING=1 EXOLON_HUMAN_SIGNING_RUN=1` | non-tty | **77** | `REFUSED_NOT_TTY` | 0 |
| T2 | `WITH_SIGNING=1` only | non-tty | **77** | `REFUSED_HUMAN_GATE` | 0 |
| T5 | both | pty, attestation wrong | **77** | `REFUSED_ATTESTATION` | 0 |
| T4 | both, attestation right | pty, no profile | **78** | `notary_profile_present=NO` | 0 |
| T6/b/c/d | both, attestation right | pty, profile `'bad name'` / `'--apple-id'` / 65 chars / `'x;rm -rf /'` | **78** | shape refusal | 0 |
| T7 | both, attestation right | pty, profile `exolon-notary` | 0 | `signing_track=HUMAN` | 1×export, 3×notarytool, 2×stapler |
| T3 | none | non-tty | 0 | `signing_track=SKIPPED` / `NOT_ATTEMPTED` | 0 |

The Track A archive (`xcodebuild … archive`, `:393-395`) is deliberately **not** behind the gate —
AC-001 makes it mandatory and it needs no credentials (identity stays ad-hoc; part 1, Item 1).
Refusal paths are all non-zero (77/78), and every one of them exits before the lane is reached.

**No code path reads or stores secret material.** Every `EXOLON_NOTARY_PROFILE` use is a NAME:
required at `:585`, shape-validated at `:590`, and passed at exactly three sites — `:644`, `:652`,
`:655` — all as `--keychain-profile "$EXOLON_NOTARY_PROFILE"`. In the full Track B run T7 the
logged argv
contains `--keychain-profile exolon-notary` three times and **nothing else** derived from that
variable; a grep of the whole T7 call log for `password|secret|token|private_key|apple[-_]id|
BEGIN.*PRIVATE|\.p12|\.p8|\.pem|unlock-keychain|store-credentials|allowProvisioning` returns
nothing. No `read -s` exists; `security` is never executed (shim present, 0 calls; `:613` emits
`identity_policy=find_identity_not_executed_by_probe`, and the C-20 identity count is *typed by
the human* into `EXOLON_DEVELOPER_ID_COUNT`, `:621`); `notarytool store-credentials` is never
executed. Every file the probe writes lands in `$SCRATCH_ROOT` or `$OUT`
(`:347, :388, :395, :437, :451, :634, :645, :653, :656, :666, :669`) and the scratch root is
forced outside the clone (`:274-281`, `exit 78` on `INSIDE_CLONE` — measured: rc=78, tree stayed
clean, 0 changed entries). Identity material enters the report as hashes only:
`hostname_redacted` (md5, `:307`), `archived_team_id_hash=sha256:…` (`:447`),
`settings_DEVELOPMENT_TEAM_hash=sha256:…` (`:604`), `archived_codesign_dump_sha256` (`:436`),
plus the CDHash. The tree carries no credential material at all: a `git grep` over the whole tree
for private-key headers, `AKIA…`, `ghp_…`, `github_pat_…`, `xox[baprs]-…` matches only
pattern-definition text, and `git ls-files` finds no `.pem/.p12/.p8/.key/.mobileprovision`.
25 probe runs with `cwd` inside the clone left `git status --porcelain` empty — the probe writes
nothing into the repository.

**S-1 (Suggestion, privacy/PII — protocol self-contradiction).** The handout's own Track A
command uses `$HOME` for both roots (`macos-handout/README.md` §1 `EXOLON_PROBE_SCRATCH="$HOME/…"`
and `--out "$HOME/exolon-probe-report.txt"`), while §5 forbids "no absolute path under someone's
home directory in any committed file". Measured with `HOME` pointed at a sentinel directory: the
transcript carries the operator home path on 5+ lines — `symroot=`, `objroot=`, `build_log=`,
`archive_log_copy=`, `scratch_root_kept=` (and `probe_output_will_be_written=`/
`probe_report_saved=` with §1's `--out`). §2.2 forbids scrubbing it ("Do not edit any other byte:
the digest and the line count are the evidence"), and no control scans report *content*:
`HYGIENE_SCOPE` (`macos_handout_check.py:1082-1084`, applied by `evidence_hygiene` `:1095-1119`)
covers 7 shipped files, not
`HANDOUT_REL/probe-report-*`. Fix: document a scratch/`--out` outside any home directory (e.g.
`/tmp`), or add the report files to the hygiene scope and allow a documented scrub step.
Not blocking: Track A is declared permanently unrunnable here (`README.md` §"Neither track will
be run"), so no such transcript can exist today.

**S-1b (Suggestion, same rule measured against this branch's own evidence).** §5 states that "the
two greps the release profile uses — one for private-key headers, one for home-directory paths —
must return nothing over the files added here", and `analysis-integration_architect.md:330` states
the same requirement as `git grep -I -E 'BEGIN [A-Z ]*PRIVATE KEY|/Users/'` over the added
evidence. Measured on `84b7813`: the private-key half returns nothing anywhere in the tree, but the
home-path half is not 0 over the added files — `analysis-integration_architect.md:330` itself
quotes the pattern, and the wave-A gate's stricter form
(`/home/[a-zA-Z0-9_-]`, `engineering/changes/20260919-*/evidence/privacy_gate.sh:15`) matches two
files this branch adds (`analysis-docs_researcher.md:272`, `analysis-repo_explorer.md:2`, both the
author's local absolute path). This is **not** a regression — 29 files already matched at the base
`817bf52`, and the immutable `20260921` package contains the same pattern — but it does mean §5's
sentence describes a gate that has never been applied to analysis prose, and the branch adds two
more files that would fail it. Either scope §5's wording to shipped artifacts (which is what
`evidence_hygiene` actually enforces) or stop writing local absolute paths into analyses.

**S-2 (Suggestion, privacy asymmetry).** `settings_CODE_SIGN_IDENTITY` is emitted **verbatim**
(`:602`) while every other identity term in the same block is hashed. On a real Track B machine
that build-setting value is `Developer ID Application: <organisation> (<TEAMID>)`, so the
organisation name — and any operator name inside it — lands in the committed transcript, against
the design rule that identity enters "only as hashes". The schema does not close this: only
`track_b.identity_hash` is pattern-bound to `^sha256:…`; `raw_kv` is a free-form string map
(`macos-probe-report-v1.schema.json`). Fix: emit `sha256:<12>` for that line too, or a class token.

## Item 2 — forbidden-argument list enforced by ABORT before execution — **PASS** (1 suggestion)

The lists are `macos-probe.sh:37` (argv forms), `:38` (key-file path suffixes), `:39` (embedded
credential text), `:40` (short forms), `:41` (environment **name** patterns), `:44` (notary
profile NAME shape); cited by line only, per the brief. The scanner region is `:102-121`
(`probe_forbidden_argv_scan`, executed over `RAW_ARGV` captured *before* parsing at `:25-26`, so a
token cannot be reshaped by the parser), the env-name scanner is `:123-137`, and the abort is
`:251-268` with `exit 77` at `:265`. It is an abort, not a redaction: the offending token is never
echoed by the refusal (`:262-264`), and the env scanner exports only a counter (`:134-135`).

**Ordering, measured with the call log (the decisive part):**

| fixture | rc | who refuses | external tools executed before refusal |
|---|---|---|---|
| `EXOLON_NOTARY_PASSWORD=…` in env | 77 | scanner `:257-265` | **only `uname -s`** (the Darwin guard) |
| `GH_TOKEN=…` in env | 77 | same | only `uname -s` |
| `--config "Release --apple-id x"` | 77 | scanner (value of a recognised flag) | only `uname -s` |
| `--out <path>.pem` | 77 | scanner | only `uname -s` |
| `--apple-id <value>` | 2 | parser `:62` | none (0 calls) |
| `--target TeamID.p12` | 66 | project guard `:70-72` | none (1 call) |

So no `xcodebuild`/`codesign`/`notarytool`/`security` invocation can ever inherit tainted argv or
env, and no partial Track-B report is produced.

**Shipped-bytes fixture run** (scanner region extracted and executed, 18 fixtures): the four
protocol-shaped legitimate command lines stay `CLEAN` (including `--keychain-profile
exolon-notary`, which the checker also pins as an anti-overshoot control at
`macos_handout_check.py:1380-1387`), and every form the handout README §4 names as forbidden goes
`TAINT`: `--apple-id`, `--password`, `-s`, `--sign`, `*.p12`, `*.pem`, `*.mobileprovision`,
`login.keychain`, `-----BEGIN … PRIVATE KEY …` (the PEM header, quoted with an
ellipsis on wave A's precedent at `engineering/reports/exolon-full-audit-20260920-v3.md:248`: writing it
out in full makes this report itself fail the repository's own secret scan), `"some PEM"`, plus a single argv element
carrying two tainted tokens (`"Release --apple-id x"`) and an empty argv (rc 0, no `set -u`
crash). Result: 0 mismatches. One documented overshoot is confirmed and is fail-closed, not
unsafe: `--out /tmp/release-notes-password.txt` is refused because the text pattern is unanchored.

**S-3 (Suggestion, ordering nit).** The scan runs at `:251`, but the report sink is opened earlier
at `:96` (`exec > >(tee "$OUT")`). A forbidden-shaped path named via `--out` is therefore
**truncated and overwritten with report lines before the refusal**: measured by planting a
victim file `victim.pem` holding sentinel bytes, then running the probe with
`--out …/victim.pem` — rc=77 (refused, 0 tool calls) but the pre-existing bytes were gone (4
report lines in their place). No disclosure and no execution happens, but the strictest reading of
"abort before execution" and the §5 rule that a key-file path must never be touched are both
looser than claimed. One-line fix: move the `:251-268` block above `:89` (it needs only
`RAW_ARGV`, `:37-41` and the emit helpers), or scan again before the `--out` branch.

## Item 3 — `macos_handout_check.py` integrity controls — **PASS** (3 findings, one of them the priority of this part)

**Identity binding (what is actually verified vs what §3 claims).** Verified against live state:
`operational.raw_report_sha256` (the sha256 of the TXT bytes) and
`report_lines_expected`/`report_lines_written` (recomputed against `wc -l` of those bytes) at
`:747-755`, every `raw_kv` entry re-read from the TXT at `:758-760`, and
`report_flush_verified` at `:756-763`; `probe_script_blob_sha1` vs the live probe file
(`:773-778`), and `tree_fingerprint` vs a live re-derivation (`:779-784`, via `binding_fields`
`:710-724` and `tree_fingerprint()` `:249-263`). Existence-only: `repo_head` is checked with
`git cat-file -e <head>^{commit}` (`:767-771`). Self-declared: `artifact_sha256`, `cdhash`,
`submission_uuid` are pattern-validated by the schema and never compared to an oracle (by design
§5 — the artifact is not committed); `track_b.identity_hash` is pattern-bound to `^sha256:`, and
`R5`/`R7` do force a committed Apple `notary-log-<uuid>.json` behind any Track-B claim
(`:810-826`, `:832-833`).

**Forged re-seal stays red (measured two ways).** (a) On-disk, using `--derive` exactly as §2.3
documents (which recomputes `raw_report_sha256`, the two line counts, `verifier_script_blob_sha1`
and the fingerprint): forging `probe_git_blob_sha1=` in the transcript → `R3 … produced by a
different probe text`; claiming Track B (`signing_track=HUMAN` + `notary_status=Accepted`) →
`R5 TRACK_B_PARTIAL` **and** `R6` (ad-hoc + Accepted is a documented impossibility). (b) In-memory
against a green baseline (so the STALE floor described below cannot mask the result): forging the
probe blob → red; fingerprint → 64 zeros → red; a Track-B lie → `R5`+`R6`. The committed control
`handout_controls_flip` (`:1252-1292`) additionally reddens all ten rules with one contradictory
fixture each, and `agent_boundary` (`:1337-1444`) executes the shipped scanner and the shipped
profile-shape and env-name validators over 13 taint and 8 legitimate cases (and asserts a planted
secret is caught by the hygiene patterns) — I reproduced those runs green and independently
re-derived the same conclusions above.

**Where §3/AC-003 over-promises** (all measured, none of them a credential exposure):
- `repo_head` set to a **real ancestor commit** (`817bf52`) → in-memory audit: **GREEN**. So "the
  head moved ⇒ STALE" is enforced only as "the head exists".
- Re-sealing an **edited transcript** the documented way (`build_rc 0→65`, `archive_rc 0→65`,
  `tree_clean_before_run yes→no`, `resource`/`marker` untouched) → **GREEN**: `--derive` recomputes
  the digest, the line counts and `raw_kv` from whatever bytes it is handed, so the digest chain
  detects *un-re-sealed* edits, not re-derived ones. This is the disclosed Class 1/Class 2
  boundary (`README.md` §6: "It does not mean the machine existed"), and `SCOPE=class-1-only` is
  printed by the checker itself — but AC-003's wording ("binding fields … artifact
  sha256/CDHash, notary uuid make stale evidence report STALE and never green") reads stronger
  than those fields can deliver.

**F-1 (Suggestion — highest priority here; a green default from unverifiable evidence).**
`tree_fingerprint()` returns `""` when the fingerprint source cannot be imported
(`:252-253` if `.grok-stack/adaptive_grok/util.py` is absent — a state `AGENTS.md` calls
legitimate — and `:262-263` on any import error). `R3` then compares with
`elif live_fp and fp != live_fp` (`:783`), so an empty `live_fp` **skips the only tree binding**,
and `--derive` likewise skips the re-stamp (`if fingerprint:` `:1731-1732`). Measured: a hand-
sealed report claiming `tree_fingerprint=0000…0` (64 zeros) in a copy of this tree with
`.grok-stack` removed prints `MACOS_EVIDENCE=OK`, **rc=0** — a green verdict for evidence whose
binding is unverifiable, i.e. exactly the failure mode AC-003 was written to prevent. Mitigating
facts, both measured: the same tree cannot pass the suite (`handout_controls_flip`,
`absent_is_unverified`, `no_track_b_claim`, `verdicts_machine_readable` all FAIL, because the
synthetic fixture's fingerprint becomes `''` and violates the schema pattern), and the path is
only reachable once a handout exists, which this repository says never happens. Fix is one clause:
treat `live_fp == ""` as `R3`-red ("cannot re-derive the tree fingerprint here — unverified"),
mirroring the ABSENT semantics.

**F-2 (Suggestion — fails closed, but the binding is unsatisfiable).** An honest report stored in
`HANDOUT_REL` can never read `OK`, because the fingerprint it carries is a function of the tree
that must contain it. Measured through the documented order in a sandbox copy: derive with the
pair untracked → `STALE`; commit the pair and re-run → `STALE`; re-derive on the now-clean tree
and re-run → `STALE` (stored `26da28a4…` vs live `9aca1ade…`, the delta being the JSON write
itself, plus `generated_utc` changes on every pass so no fixed point exists). Consequence: no
committed control exercises the on-disk green path — `absent_is_unverified` only asserts ABSENT and
FAIL-vs-STALE distinctness, and `handout_controls_flip` audits in memory — so the "green handout"
state is untested and, as constructed, unreachable. Not a security exposure (it can only ever
under-accept), and it is masked in practice by the ABSENT steady state, but the first real
Track-A run will be rejected no matter how honest it is.

**ABSENT ⇒ unverified rc=1 — PASS, independently confirmed.** `evaluate_handout` (`:995-1022`)
returns `{"status": "ABSENT", "line": "MACOS_EVIDENCE=ABSENT (unverified)"}` when the directory
holds no `probe-report-*.json`, and `main` (`:1741-1746`) maps any non-`OK` status to rc 1.
Measured directly: `--root . --report` on the pristine clone → `MACOS_EVIDENCE=ABSENT
(unverified)`, rc=1; a README-only handout dir also stays ABSENT, and a planted
rule-violating report becomes `FAIL`/`STALE` (never ABSENT, never OK) — the committed control's
three cases, which I ran green rather than re-inventing.

## Item 4 — event-log / ledger privacy sweep on the merged tree — **PASS** (1 precision correction)

- **Structural guarantee, not a convention.** The hot-path sink takes only fixed-width integers:
  `func emit(_ kind:entity:_ a:Int16,_ b:Int16,_ c:Int16,_ d:Int16)`
  (`GameplayEventSink.swift:379`, with integer-only overloads at `:389-425`). No `emit*` helper in
  that file has a `String` parameter (`grep -E 'func emit[A-Za-z]*\(' | grep -i string` → no
  match), so no product string can reach a record. The wire encoders are `number`/`flag`/`label`
  (`GameplayEventLog.swift:854-870`, `label` documented as "Whitelisted lowercase-ASCII label: no
  free text reaches this path") and `string` (`:871-875`), whose callers are an enumerated set of
  pattern-constrained fields.
- **Every `string()` caller checked** (15 sites): the five exempt header fields
  (`run_id`, `build`, `wall_utc`, `path`, `seed` — `:795-800`, `run_id` pattern `^[0-9a-f]{8,32}$`);
  `reason` from an enum label (`:587`); `marker`, a fixed template with one integer
  (`:817`, schema pattern `^# dropped [0-9]+ oldest events`); `object_id`/`launcher_object_id`,
  `^[0-9]+$`; and `resource`/`next_level` from `GameplayWire.resource(for:)`
  (`GameplayEventSink.swift:901-904`), a pure `String(format: "L%02dS%02d", …)` over a clamped
  zone integer, schema-pattern-bound to `^L[0-9]{2}…`. Nothing user-, env- or file-derived flows
  through any of them.
- **Banner text is never logged.** The only banner strings in the product are two literals
  (`"EXOSKELETON ON"/"OFF"` at `GameScene.swift:370`, `"+1000"` at `:439`) consumed by
  `showBanner(_:)` (`:919`, `bannerLabel.text = text` at `:922`); `showBanner` has no sink
  reference, and the exoskeleton event beside it carries the enum *cause*, not the label text.
- **The two D-added lanes are integer+label.** `stage_component_id` 1→3 codes
  (`bravery_no_exoskeleton`, `timed_phase_ladder` — `GameplayEventSink.swift:1157-1163`, domain
  `codeCount: 3` at `:988`) reach the wire only via
  `line.label("component_id", GameplayWire.stageComponentLabel(subject))`
  (`GameplayEventLog.swift:1054`) with the closed-table lookup and the integer fallback
  `"unknown\(bits)"` (`:919`); `exoskeleton_cause` 3→4 (`stage_boundary`,
  `GameplayEventSink.swift:1042-1049`) reaches the wire as a wire code, applied at
  `GameScene.swift:852`. Both values are declared as **closed enums** in
  `engineering/contracts/schemas/gameplay-event-v1.schema.json` (and the appended
  `x-extension-rule` requires schema+enum+sequence to move in one commit). `StageBoundaryLedger`'s
  one `String` is the internal dedupe key (`awardedCounts: [String: Int]`, `:138`, `onceKey` `:261`)
  and never reaches the wire. The zone lane also converts its one String input back to an integer
  before emission: `emitZoneTransition(to levelName:)` → `zoneNumber(for:)`
  (`GameScene.swift:1358-1360`, `:1440`) → `emitZoneTransition(toZone: Int, …)`
  (`GameplayEventSink.swift:664-667`) — so even the Debug warp's `EXOLON_DEBUG_WARP` value cannot
  become log text.
- **Precision correction (paths).** "No file paths outside `log.begin`" holds for the field named
  `path`: `line.string("path", path)` occurs exactly once, in `beginRecordLine` (`:799`,
  `log.begin`), and the schema marks `path`/`build`/`seed` with `"x-only-in": "log.begin"`. But
  `log.rotate` additionally writes `from_path`/`to_path` (`:774-775`), declared as plain
  `{"type":"string","minLength":1}` with no `x-only-in`. Two consequences worth recording: the
  correct claim is "the log's own paths appear in `log.begin.path` and `log.rotate.from_path/to_path`
  and nowhere else", and `x-only-in` is **advisory only** — no validator in the tree enforces it
  (`grep -rn "x-only-in" --include=*.py` → no hits; wave A's `validate()` supports
  `type/enum/const/minimum/maximum/pattern/required/properties/allOf`, not `x-only-in`). The
  current implementation is compliant by construction, and the disclosed values are the log's own
  rotation paths (no user or gameplay data), so this is a wording/enforcement note, not a leak.

## Item 5 — the immutable historical package `20260921-*` — **PASS**

`PR3_DIR` is `engineering/changes/20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698`
(`macos_handout_check.py:56`). Measured base→HEAD:
`git log --oneline --stat 817bf52..84b7813 -- 'engineering/changes/20260921-*'` → **no commits**;
`git diff --stat 817bf52 84b7813 -- <PR3_DIR>` → empty; per-commit file lists for all three branch
commits (`c402526`, `7929818`, `84b7813`) match `20260921` **0 times**; `git ls-tree -r` for the
package is byte-identical between `817bf52` and `84b7813` (27 entries each, same blob SHAs —
`diff` → identical). The package is additionally protected in code
(`merged_package_is_immutable`, `:1072-1078`, called from `probe_contract_green` `:1131` and
`cutover_set_exact` `:1487`); both checks passed on the pristine clone. No other historical package
is touched either: the whole base→HEAD file list is 23 files under this change's own
`…8341b7/` package plus 11 product/contract files (`Exolon.xcodeproj/project.pbxproj`,
`Exolon/GameCore/GameScene.swift`, `GameConstants.swift`, `Diagnostics/StageBoundaryLedger.swift`,
`Diagnostics/GameplayEventSink.swift`, `Diagnostics/FixedTickDriver.swift`,
`Exolon/Exolon.entitlements`, `engineering/runbooks/macos-probe.sh`, the two contract schemas, and
`decisions.md`); a grep of that list for any other change package returns nothing.

---

## Verdicts

| # | Scope | Verdict |
|---|---|---|
| 1 | Track B reachable only behind both env opt-ins + tty + typed attestation; refusals non-zero; no secret read/stored, profile NAME only | **PASS** (S-1, S-1b, S-2) |
| 2 | Forbidden argv/env list enforced by abort before any tool execution; never redacts | **PASS** (S-3: `--out` sink opens before the scan → key-path file clobbered by refusal) |
| 3 | Handout integrity: identity binding, forged re-seal stays red, ABSENT ⇒ rc=1 unverified | **PASS** (F-1 green-default when the fingerprint source is absent; F-2 on-disk green unreachable; `repo_head`/artifact digests bound weaker than §3 wording) |
| 4 | Event-log/ledger privacy: integer+label payloads, banner text never logged, paths confined | **PASS** (correction: `log.rotate` also carries the log's own paths; `x-only-in` is unenforced) |
| 5 | Nothing in the branch touches `20260921-*` | **PASS** |

Overall part 2: **PASS — no blocking security defect.** The probe/agent boundary holds under
execution, not just under reading: I could not reach a single distribution-side tool without the
human gates, and I could not get a credential-shaped value into any invoked argv. The one finding
that deserves a follow-up ticket before this protocol is ever used is **F-1**: `--report` can print
`MACOS_EVIDENCE=OK` (rc 0) on a host that cannot re-derive the tree fingerprint, which is a green
default built out of the same `live_fp and …` short-circuit that AC-003 exists to forbid. Fix is
one clause; the suite itself already fails loudly on such a host, which is why this is a
Suggestion and not a Critical.

Findings summary (all checker/protocol side, none in product behaviour):

| id | severity | file:line | one line |
|---|---|---|---|
| F-1 | Suggestion (priority) | `macos_handout_check.py:783` (`:249-263`, `:1731`) | Unverifiable fingerprint ⇒ `MACOS_EVIDENCE=OK`, rc=0 (measured) |
| F-2 | Suggestion | `macos_handout_check.py:1730-1732` + `:779-784` | An honest in-tree report can never read OK (self-referential fingerprint); fails closed, untested path |
| — | Suggestion (doc) | `macos-handout/README.md` §3, `change-spec.yaml` AC-003 | "head moved ⇒ STALE" and artifact-digest "binding" are stronger than the enforced checks (existence/format only) |
| S-1 | Suggestion | `macos-handout/README.md` §1 vs §5 | Documented `$HOME` scratch/`--out` puts home paths into a file §5 forbids them in; no content scan exists |
| S-1b | Suggestion | `README.md` §5 / `analysis-integration_architect.md:330` | The stated home-path grep is not 0 over the files this branch adds (2 analysis files carry `/home/<user>`; 29 did at base) — the rule has never covered prose |
| S-2 | Suggestion | `macos-probe.sh:602` | `settings_CODE_SIGN_IDENTITY` emitted verbatim while every sibling identity term is hashed |
| S-3 | Suggestion | `macos-probe.sh:96` before `:251-268` | Report sink opens (and truncates `--out`) before the credential scan aborts the run |
| — | Nice to have | `GameplayEventLog.swift:774-775` + event schema | State the path rule as "`path` is `log.begin`-only; `log.rotate` carries its own two more", or enforce `x-only-in` in the validator |
