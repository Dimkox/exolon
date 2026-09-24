# Release review — P1-11 release layer (route `2e76988444b0`)

- Range reviewed: `d4c7a58..fee613e` — `edba343` (release layer: plist substitution + shared
  Archive scheme + retargeted `macos-probe.sh` + this change package) and `fee613e`
  (read-only measurement evidence for P1-1 / P1-2 / P1-7, no product files).
- HEAD at review time: `fee613ef4ff12798c9345793335e94aeb276ff5c`, branch
  `codex/release-layer-p1-11-20260921`, worktree clean (`git status --porcelain` empty before this file).
- Host: Linux 6.8.0-110-generic, Python 3.12.3, `xcodebuild` ABSENT, `codesign` ABSENT
  (`plutil`/`swiftc` exist under `/opt/swift`, so plist/pbxproj linting and Swift parsing are possible;
  **no macOS build, scheme loading, archiving or signing is observable here**).
- Role: `release_reviewer` for route `2e76988444b0` (allowed agents: repo_explorer, architect,
  docs_researcher, security_reviewer, release_reviewer; one write owner, this reviewer is read-only).
- Files written by this review: **only** `engineering/changes/20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698/evidence/review-release_reviewer.md`.
  No product file, no other document, no git write command. All destructive/mutation testing was done
  in a throwaway local clone at `/tmp/exolon_mut` (`git clone` from this repo, HEAD `fee613e`), never in the working tree.

VERDICT: pass

Meaning: the product layer and the evidence chain are good enough to open the pull request and merge
**once the three BLOCKING items below are discharged** (all of them are records/wording; none requires
touching `Exolon/`, `Exolon.xcodeproj/` or `engineering/runbooks/`). This review is **not** a release
authorisation for any artefact: tag, `.xcarchive`, notarisation or GitHub Release stay NO-GO until the
owner's macOS session proves M-01′/M-02′ green (`evidence/perfile/macos-validation-handout-v2.md`).

---

## 1. Claim-by-claim verification

### Claim 1 — committed Linux verifier is green on this tree

Command run:

```
python3 engineering/changes/20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698/evidence/release_layer_check.py --root .
```

Observed: `rc=0`, last line `RESULT: RELEASE_LAYER_READY`. 48 AC metric rows, none carrying a `RED`/`✗`
marker (0 red); 29 control rows, all `OK` (0 bad controls), including `undo_fix_is_red`. The success
line does not print the counters as `red_ac=0 bad_controls=0` (it prints them only in the `NOT_READY`
form) — the counters were derived by counting rows: 48/0 red, 29/29 OK, which matches
`change-spec.yaml` `objective.target = "rc=0 / red_ac=0 / bad_controls=0"`.

**HOLD.**

### Claim 2 — `v3_measurements.py` is red only on `shared_xcschemes`, and the cutover is owned

Command run:

```
python3 engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/v3_measurements.py
```

Observed: `rc=1`, exactly one line `НЕСОВПАДЕНИЯ: {"shared_xcschemes": [0, 1]}`, and all 10 of its own
controls `OK` (so the tool is still self-checking, not degraded). `RESULT: MISMATCH`.

Is the ownership written down clearly enough that the next agent will not "fix" it? Yes, in five places,
all greppable from the failing key: `release.md` §Metrics ("обязан быть **1** … «чинить» его удалением
схемы запрещено"), `requirements.md` AC-008, `architecture.md` §"Владельчество landmine" (names the
exact mismatch string), `rollback.md` §Data recovery, `change-spec.yaml` AC-008 + FORBID-004, and
`test-plan.md` P1 row "«Починить v3, удалив схему» красится, а не молча проходит".

Is the forbidden repair actually caught by `release_layer_check.py`? Verified by mutation, not by prose
(all in `/tmp/exolon_mut`, HEAD `fee613e`):

| Mutation | Result |
| --- | --- |
| delete `Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme` | `rc=1`, `RESULT: NOT_READY (red_ac=12 bad_controls=1)` |
| edit the dated pin `shared_xcschemes: 0 → 1` inside `v3_measurements.py` | `rc=1`, `v3_pin_shared_xcschemes = 1 RED ожидалось 0`, `bad_controls=3` |
| replace the token `shared_xcschemes` in **every** plan doc of this package | `rc=1`, `v3_shared_scheme_cutover_owned = 0 RED ожидалось 1` |
| replace it in `release.md` only | still `rc=0` (record survives in the other four docs) |

**HOLD**, with one sharp edge: the anti-landmine guard is *token-presence*, not semantic. An agent who
keeps the literal string `shared_xcschemes` somewhere in a plan file while deleting the sentence that
forbids removing the scheme stays green. `decisions.md`/`mistakes.md` — the files AGENTS.md designates
as cross-task shared memory — carry **no** mention of the cutover (the new `decisions.md` entry is about
tool causality only), so an agent that reads only the shared-memory files is not warned.

### Claim 3 — product scope is exactly three paths, `project.pbxproj` untouched

Commands run:

```
git diff --name-only d4c7a58..HEAD -- Exolon Exolon.xcodeproj engineering/runbooks
git diff --name-only 403eb13..HEAD -- Exolon Exolon.xcodeproj engineering Exolon/Resources   # as literally written in release.md
```

Observed (first): exactly
`Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme`, `Exolon/Resources/Info.plist`,
`engineering/runbooks/macos-probe.sh` — three paths, no `project.pbxproj`, no `xcuserdata`.
Independent confirmation that the deferral is real, from my own block parse of
`Exolon.xcodeproj/project.pbxproj` (not the tool's): whole-file `ENABLE_HARDENED_RUNTIME` occurrences = 0;
`CODE_SIGN_IDENTITY = "-"`, `CODE_SIGN_STYLE = Manual`, `DEVELOPMENT_TEAM = ""` in both target configs,
i.e. the signing clause is genuinely still open. Consistent with `release.md` §Deferred,
`change-spec.yaml` AC-007/AC-007-evidence/INV-001/FORBID-002 and `requirements.md` §Отсрочка.

Observed (second, the command printed in `release.md` Go criteria): **115 paths**, not three — the base
in that command (`403eb13`, = `origin/main`, also `route.json:base_commit`) is not this branch's parent
(`d4c7a58`), and the pathspec includes `engineering`, so the two unmerged ancestor PRs' audit docs are
swept in. Only 2 of those 115 paths are non-`engineering/`.

**HOLD for the scope claim; NOT HOLD for the go/no-go command as written** — see BLOCKING B2.

### Claim 4 — rollback `strategy=forward_fix, maximum_steps=1`, and the asymmetric consequences

`change-spec.yaml` → `"rollback": {"strategy": "forward_fix", "maximum_steps": 1}`. Verified against the
diff shape in the clone:

```
git revert --no-commit fee613e edba343   → rc=0, no conflict
git diff --stat d4c7a58                  → empty (tree byte-identical to the base)
python3 .../v3_measurements.py           → RESULT: ALL_V3_MEASUREMENTS_MATCH_REPORT   (green again)
```

So one revert *is* enough and it restores the exact base tree; the bundle id is unchanged
(`com.exolon.remake`), so no state key moves in either direction — as `rollback.md` claims.
`rollback.md` §Data recovery does name the asymmetric consequences out loud rather than "fixing" them:
the revert re-introduces the false `0.3` (finding re-opens) and re-greening `v3_measurements.py` "is not
a health signal". **HOLD** for the typed claim and for the disclosure.

Two defects in `rollback.md`'s verification section, both reproducible (see BLOCKING B3):

- "`python3 evidence/release_layer_check.py --root .` → обязан стать красным ровно на отменённых
  клаузах" is not executable after the one-step revert it prescribes: the verifier lives *inside*
  `edba343`, so `git revert edba343` deletes the tool along with the fix
  (`ls: cannot access …release_layer_check.py: No such file or directory`).
- Reverting only `edba343` leaves the seven `fee613e` files (`evidence/analysis-p1-2-spawn.md`,
  `analysis-p1-7-markers.md`, `p1-1_piston_probe.py`, `piston-anchor-harness/*`,
  `piston-anchor-swift.{txt,err}`) orphaned in a change package whose `change-spec.yaml`,
  `requirements.md`, `release.md`, `rollback.md`, `route.json`, `state.json` are gone.
- Partial revert of just the plist (the forward-recovery branch `rollback.md` itself offers) does not
  produce a red report either: the verifier aborts —
  `AssertionError: откат plist не найден в тексте: контроль причинности бессмысленен`
  (`release_layer_check.py:710` inside `undo_fix_is_red`), `rc=1`, **stdout empty** (no AC rows, no
  `RESULT` line). It fails closed, which is the safe direction, but it reports nothing.

### Claim 5 — version identity is target-config-scoped, and 0.3 → 0.5 is disclosed

`release_layer_check.py` reports `marketing_version_in_target_configs=2`,
`marketing_version_outside_target_configs=0`, `project_version_in_target_configs=2`,
`project_version_outside_target_configs=0`. I re-derived block attribution myself (independent parser,
balanced-brace scan over `isa = XCBuildConfiguration` blocks, `plutil -lint` says the pbxproj is a valid
property list):

| Config block | name | MARKETING_VERSION | CURRENT_PROJECT_VERSION |
| --- | --- | --- | --- |
| `800000000000000000000001` | Debug (project) | — | — |
| `800000000000000000000002` | Release (project) | — | — |
| `800000000000000000000003` | Debug (target) | `0.5` | `1` |
| `800000000000000000000004` | Release (target) | `0.5` | `1` |

Both keys exist **only** in the two target-level blocks, once each; the project-level blocks do not
define them, so a whole-file `grep -c` genuinely cannot certify this and the block-aware check is the
right instrument. `INFOPLIST_FILE`/`GENERATE_INFOPLIST_FILE = NO` are likewise target-scoped, and the
plist diff is exactly the two version lines (`CFBundleVersion` value is unchanged at `1`, so only
`CFBundleShortVersionString` moves).

Disclosure of the user-visible consequence: `release.md` §Feature flags — "Видимое потребителю отличие
ровно одно: About/Finder/`mdls` начинают показывать `0.5` вместо `0.3`"; `brief.md:27`; and
`release.md` §Deferred closes the loop with "Номер версии (0.5 vs 0.3) этим change **не** назначается".

Whether the **built bundle** really changes 0.3 → 0.5 depends on Xcode expanding `$(MARKETING_VERSION)`
at build time. On Linux I can only prove the structure (substitution present, setting present in the
target configs, same mechanism already used by four other plist keys).

**HOLD** for the settings placement and the disclosure; **UNVERIFIABLE_ON_LINUX** for the expanded value.
Settling command (handout M-01′):
`plutil -extract CFBundleShortVersionString raw build/Debug/Exolon.app/Contents/Info.plist` → `0.5`,
plus `grep -c '$(' …/Contents/Info.plist` → `0`.

### Claim 6 — closure honesty: two of three clauses, plainly stated; discoverability from the audit report

"Partially closed" is stated plainly, and in the authoritative places: `requirements.md:15`
("находка фиксируется как **закрытая частично**"), `change-spec.yaml` FORBID-006 ("P1-11 must not be
declared fully closed") and the typed objective statement, `tasks.md` §"Что остаётся после этого change"
item 1 (signing clause → separate change after green M-01′), `rollback.md:14`, `release.md` title and
§Deferred.

The dated audit report was **not** edited, and that is machine-checked
(`reports_dated_count=2`, `reports_blob_mismatches=0`). I confirmed append-only by mutating a copy:
appending one HTML comment to `engineering/reports/exolon-full-audit-20260920-v3.md` →
`rc=1`, `reports_blob_mismatches = 1 RED ожидалось 0`.

But: `grep -rn "P1-11" engineering/reports/` returns **only** the two original lines — `:36` (the finding)
and `:130` (backlog, still under "P1 (чинить до релиза)"). There is **no pointer at all** from the report
to this change package, and the report's own P3 line ("отсутствие иконки/shared scheme") is now stale too.
`PROJECT_STATE.json` and `START_HERE.md` — which AGENTS.md names as the zero-context handoff entrypoints —
**do not exist in this tree**, so the change package directory is genuinely the only record.

Judgement: the failure direction is safe (a reader of the backlog sees P1-11 as *still open*, never as
"done"), and `tasks.md` item 4 assigns the re-statement to the next audit run, which is the correct
append-only remedy. The residual problem is discoverability in the other direction: nothing outside
`engineering/changes/20260921-*` says "identity+scheme closed, signature open".
**HOLD for the wording requirement; the pointer gap is NON-BLOCKING N3.**

### Claim 7 — README consistency and the "README before push" gate

`git diff --name-only d4c7a58..HEAD` does not include `README.md`; `git log -1 -- README.md` = `403eb13`.
`grep -niE "0\.[0-9]|version|scheme|MARKETING" README.md` finds no version claim, no release-identity
claim, no scheme claim → **this change falsifies nothing in README**, and there is no
`architecture/system.yaml`/`architecture/rules.yaml` in this repo for the second README clause to bite on.
AGENTS.md's gate fires "before proposing a release"; `release.md` §Deployment states this change creates
no artefact, so the gate is not triggered by this commit pair. README is independently stale ("Step 9
Rebase (test archive)", zone-009 narrative) — pre-existing, not caused here.
**HOLD (no stale claim introduced)**; the gate *will* bind the change that cuts the first Release/tag,
and that change must document where release identity now lives (pbxproj target configs, plist by
substitution, shared scheme path).

### Claim 8 — macOS unknowns are not claimed as done; the handout is executable

- No document claims an expansion, a scheme-loader acceptance, an archive or a codesign flag as proven.
  Targeted grep for `BUILD SUCCEEDED|уже собран|подтверждён на macOS|archive собран|нотариз…` across the
  package returns nothing but expectation text. AC-010 exists precisely to forbid a Linux metric for
  these, and `release_layer_check.py` contains no such metric (its 48 rows are plist/pbxproj/scheme/
  runbook/records only). The handout states its own limit up front: "Хост исполнителя — Linux … ни один
  его пункт не засчитывается Linux-вердиктом".
- The handout is a one-session protocol as written: M-01′…M-04′ each carry literal commands
  (`xcodebuild -target Exolon -configuration Debug build`, `plutil -extract …`, `grep -c '$('`,
  `xcodebuild -list -json`, `xcodebuild -scheme Exolon -showdestinations`,
  `WITH_ARCHIVE=1 engineering/runbooks/macos-probe.sh --out /tmp/probe-p1-11.txt`,
  `codesign -d --verbose=4 … | grep -o 'flags=0x[0-9a-f]*(.*)'`), numeric expectations
  (`0.5`, `1`, `0`, `rc=0`), a per-line "Если иначе" falsification branch, and named negative controls
  (`grep -c '$(' ≥ 1` = forbidden state; the pre-fix build's `codesign` dump must NOT contain `runtime`;
  `-scheme` failing "по причине нет схемы" vs "по подписи" separated explicitly in M-03′). It also keeps
  the `-target` fallback in §B rather than removing it in the same commit, and the return path of the
  artefact (`--out` into this package's `evidence/`) is stated.
- `engineering/runbooks/macos-probe.sh`: `bash -n` clean; refuses to run off macOS with `exit 75`
  (a Linux-runable negative control in itself); `set -uo pipefail` without `-e`, so the new
  `grep -c`/`grep -o` probes cannot abort the report mid-run.
- **UNVERIFIABLE_ON_LINUX** for: scheme acceptance by the Xcode loader, first successful build,
  archive outcome, `codesign` `runtime` token. Each has the exact settling command above.

---

## 2. BLOCKING — discharge before the merge head is frozen (none needs a product change)

**B1. The route's own required human-gate scope for the deferral is unrecorded.**
`route.json`/`state.json` title asks to "enable the hardened runtime"; this change deliberately does not.
`change-spec.yaml` `approvals.required_scopes` names `scope_and_design_approval` and
`defer_hardened_runtime`. Nothing in the tree records that the owner granted either
(`grep -rn defer_hardened_runtime .` → the one occurrence is the requirement itself;
`.grok-stack/runtime/approvals.json` contains only a `git-push-branch` grant bound to `fee613e`, TTL
2026-09-21T07:49Z, and `state.json` still reads `status: "draft"`). AGENTS.md: merge requires all
required approval scopes present. The deferral argument itself is sound and measurable
(`AC-007 hardened_deferral_recorded=1`, red if the record disappears while the key stays absent — I
verified the guard by mutation G). **Action: record the owner's decision (grant or refuse) for
`defer_hardened_runtime` before merge; if refused, `release.md` already specifies the exact re-entry
(2 tab-indented `ENABLE_HARDENED_RUNTIME = YES;` lines in both target configs, INV-001 staying green).**

**B2. `release.md` Go/no-go product-scope command cannot be executed as written.**
`git diff --name-only 403eb13..HEAD -- Exolon Exolon.xcodeproj engineering Exolon/Resources` returns 115
paths, not the "ровно три продукта-пути" the same paragraph asserts, because 403eb13 is `origin/main` and
the branch carries two unmerged ancestor PRs (#1 `codex/update-factory-20260920`, #2
`codex/factory-updated-20260920` = `d4c7a58`, both OPEN). An agent executing the gate literally gets a
false no-go; an agent that "fixes" it by opening this PR against `main` ships the ancestor PRs' content
too. **Action: change that bullet to base `d4c7a58` with pathspec `Exolon Exolon.xcodeproj
engineering/runbooks` (verified: exactly the three paths, no `project.pbxproj`), and state the PR base
explicitly. Same stale base appears in `rollback.md` §Частичная forward-recovery
(`git checkout 403eb13 -- Exolon/Resources/Info.plist`) and §Verification after rollback, and in the
handout header "база маршрута `403eb13`" — `grep -n 403eb13` in this package before re-gating.**

**B3. One evidence claim names the wrong artefact, and one rollback step is unrunnable.**
`tasks.md:9` (checked box) states `evidence/release_layer_check.py` "запущен на пред-фиксном дереве
(rc=1, 15 красных AC)". The committed tool cannot produce that: on the pre-fix product tree it dies in
`undo_plist` (`AssertionError: откат plist не найден в тексте`, line 710) with empty stdout — I ran it
against a `git checkout d4c7a58 -- Exolon Exolon.xcodeproj engineering/runbooks` tree: `rc=1`, 0 AC rows.
The `red_ac=15 / 26 controls` transcript belongs to the deleted draft
(`analysis-verifier-draft.md` §5/§7 and the honest §9 divergence list, which already says the draft's
`post_fix_dry_run_is_all_green` was replaced by `undo_fix_is_red`). So the draft record is clean; only
the tasks.md attribution and `rollback.md`'s post-rollback verification step are wrong.
**Action: reword tasks.md line 9 to name the draft, and rewrite `rollback.md` §Verification after
rollback to the executable truth — full revert deletes the verifier with the fix (assert by
`git diff --stat <base>` being empty, which I proved), and the "tool must go red" property is held
in-memory by `undo_fix_is_red`, not by running the tool on a reverted tree.**

---

## 3. NON-BLOCKING

**N1. `undo_fix_is_red` aborts instead of reporting.** Any tree where the plist half is missing produces a
Python traceback with no AC rows and no `RESULT` line (`rc=1`). Fail-closed, so not a correctness risk,
but it removes the tool's diagnostic value exactly when an operator is mid-incident. Consider a guarded
"fix-not-present" branch that still prints the red AC set.

**N2. `test-plan.md` says the verifier "ничего не пишет"; it writes bytecode caches.** Importing
`v3_measurements` from the *dated* audit package creates
`engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/__pycache__/v3_measurements.cpython-312.pyc`
(and one in this package). It is `__pycache__/`-ignored, so `git status` stayed clean and
`tree_fingerprint` stayed `6dec5533…` across all my runs — no receipt effect. Fix the sentence, not the tool.

**N3. The cutover/partial-closure facts are not in the shared-memory files.** AGENTS.md designates
`decisions.md` + `mistakes.md` as the cross-task memory; the new `decisions.md` entry covers tool
causality but neither the `shared_xcschemes` landmine nor "P1-11 closed partially (identity+scheme;
signature open)". A one-line entry in each is the only pointer that survives outside
`engineering/changes/20260921-*`, given `START_HERE.md`/`PROJECT_STATE.json` do not exist in this tree.

**N4. Hand-written-scheme residual, recorded for the owner.** `LastUpgradeVersion = "1020"` is coherent
with the project's own `CreatedOnToolsVersion = 10.2` / `LastSwiftUpdateCheck = 1020`, so no migration
prompt is expected; if Xcode does re-serialise the file on first open, the worktree becomes dirty and the
checker re-evaluates the new text — the verifier pins XML semantics (action set, five `buildFor*`,
`BlueprintIdentifier` vs the real `PBXNativeTarget`, lowercase `container:`), not formatting, so a
re-serialisation is unlikely to turn it red spuriously. Worth one look during the macOS session.

**N5. Commit hygiene.** `edba343` and `fee613e` share one author date (06:42:35); the split is
semantically right (product+package vs other findings' evidence) and `fee613e` touches zero product
files, but the second commit is *inside this change's* `evidence/` directory, so reverting the first or
leaves orphaned evidence (see B3). Not worth restructuring now; note it for the next route.

---

## 4. Checked and found clean

- Product diff shape: plist change is 2 lines (literal → `$(MARKETING_VERSION)` /
  `$(CURRENT_PROJECT_VERSION)`); the other nine plist keys untouched and digest-pinned
  (`plist_nonversion_untouched=1`, `plist_key_count=11`); `plutil -lint` OK for the plist and the pbxproj.
- Scheme file, verified independently of the committed tool: 6 canonical action elements
  (`BuildAction/TestAction/LaunchAction/ProfileAction/AnalyzeAction/ArchiveAction`), exactly 4
  `BuildableReference`, all with `BlueprintIdentifier = 500000000000000000000001`, all with
  `container:Exolon.xcodeproj` (lowercase), `ArchiveAction buildConfiguration="Release"`,
  `LaunchAction/TestAction/AnalyzeAction="Debug"`, `ProfileAction="Release"`, no `TestableReference`.
  That GUID is the single `PBXNativeTarget` `Exolon`, `productType = com.apple.product-type.application`,
  `productReference = Exolon.app` — the scheme is not addressing a phantom.
- Fresh-clone proof (the real "does the release layer exist for the next machine" test): a plain
  `git clone` of this branch to `/tmp/exolon_mut` yields `shared_scheme_count = 1` and a green verifier,
  so the scheme is tracked and nothing depends on `xcuserdata` (`user_scheme_count = 0`).
- No smuggled scope: 0 test targets, no `.entitlements`, no `DEVELOPMENT_TEAM` value, no signing
  identity, no Swift/source or object-graph edits, no `objectVersion` bump (FORBID-003/005 hold —
  product pathspec is 3 files).
- Regression guards reproduced by mutation, not read: `hardened_runtime_key_count` goes red on a
  one-sided `ENABLE_HARDENED_RUNTIME = YES` insert (`red_ac=1 bad_controls=1`, INV-001 + FORBID-002);
  dated-report tampering goes red (`reports_blob_mismatches=1`); dated `v3_measurements.py` pin tampering
  goes red (`v3_pin_shared_xcschemes=1`).
- Evidence chain binds to THIS tree: `.grok-stack/runtime/receipts/2e76988444b0/verification.json`
  `status=pass`, `tree_fingerprint=6dec5533c4485a1cfdf08b3ed132e153511aec0133e9725ad204ac709565d720`,
  and `adaptive_grok.util.tree_fingerprint('.')` recomputes to the same value at HEAD `fee613e`
  (`changed_files = []`) both before and after every verifier run in this review.
- `fee613e` (other findings' evidence) is self-checking too:
  `python3 evidence/p1-1_piston_probe.py` → `rc=0`, `RESULT: ALL_P1_1_MEASUREMENTS_MATCH_REPORT`,
  14/14 controls OK, 20 measurement rows, and it publishes the disagreement with the dated audit model
  (`swift_groundy_agrees_product_rule=46` vs `…_audit_rule=1`) instead of quietly overriding it. It adds
  no product risk. (Its `sys.path` import of the dated `v3_measurements` is a coupling; AC-009 pins that
  file's blob, which is the right containment.)
- Route hygiene: `allowed_agents` respected (this reviewer is listed); `write_agent` ownership untouched by
  the review; the audit's own `AC-019` ("every numeric claim of the v3 report is produced by one
  self-checking committed tool whose exit code depends on the report matching") is NOT violated by the
  red cutover — the tool still self-checks, it just now reports an honest mismatch.

---

## 5. Shipping a hand-written Xcode scheme without ever running Xcode — my judgement

Acceptable to **merge**, not acceptable to **publish**. The reasoning is bounded by what the merge
actually does: `release.md` §Deployment is explicit that no artefact is produced by this change, so the
scheme cannot hurt a user before the owner's macOS session runs. The failure mode is confined and loud:
if the loader rejects the file, `xcodebuild -scheme Exolon -showdestinations` returns non-zero, which is
M-02′ with an `rc` expectation; and if the plist substitution does not expand, the app's About panel
literally prints `$(MARKETING_VERSION)` — the bundle shows a visible string, not a silently wrong
version. The hand-written shape is pinned to Xcode's own emitted form (four references, no
`ArchiveAction` reference, lowercase `container:`), cross-checked against the real target GUID, and the
casing trap that killed the draft is now a mandatory-flip control (`container_prefix_casing_rejected`)
rather than a hope. The repair radius is one new file.

What I would block on, plainly: (1) the recorded owner decision on the hardened-runtime deferral (B1) —
the change narrows an explicit route instruction and its own typed spec says that needs a scope;
(2) the two unexecutable commands in the go/no-go and rollback plans (B2, B3) — in a repository whose
whole discipline is "a claim must be a command", a release plan whose gate command returns 115 paths is
the defect worth fixing before the head is frozen; (3) anything that turns these commits into a public
artefact before M-01′/M-02′ are green. No block on the plist substitution, the scheme's structure, the
scope of the diff, or the rollback design.

---

## 6. Residual risk accepted by this review

1. Xcode may still refuse to load the hand-written scheme, or may rewrite it on first open. Bounded to one
   file, detected by `showdestinations_rc`, repaired in the same session; no merged artefact exists before that check.
2. `$(MARKETING_VERSION)` may not expand on the owner's Xcode version (first build in project history —
   M-01′ is also the first type-check ever). Detected as `plist_unexpanded_placeholders > 0` /
   `version_single_source=MISMATCH`; `rollback.md` prescribes the one-step response.
3. `archive_rc` may be non-zero because of ad-hoc signing (`CODE_SIGN_IDENTITY = "-"`, empty
   `DEVELOPMENT_TEAM`). Accepted knowingly: that is the third, still-open clause of P1-11, not a regression.
4. `v3_measurements.py` stays red on every future Linux run of this tree, and the anti-landmine guard is
   token-based rather than semantic (Claim 2). Accepted: the pin is dated evidence, ownership is recorded,
   and the machine check catches both "fixes" (delete the scheme, edit the pin).
5. P1-11 remains **partially closed** — identity and scheme clauses only; `ENABLE_HARDENED_RUNTIME`,
   `.entitlements`, Developer ID and notarisation stay open. The dated audit report still lists P1-11 as
   "чинить до релиза" and carries no closure pointer (append-only, AC-009); the next audit run must
   rebuild the row, and the interim pointer lives only in this package (see N3).
6. The release layer is stacked on two unmerged PRs (#1, #2); merge of this change assumes their order.
   Not a code risk, but it is why B2's base-sha wording matters.
7. Local receipts are workflow evidence only. At review time no pull request exists for
   `codex/release-layer-p1-11-20260921` (`gh pr list --head …` → `[]`), so no App-owned
   `adaptive-trust-ci/verified@<policy-sha12>` check exists for `fee613e`. This pass does not create one.
8. Writing this review's file has already stale-ed the local evidence, measured rather than assumed:
   `tree_fingerprint` moved from `6dec5533c4485a1cfdf08b3ed132e153511aec0133e9725ad204ac709565d720`
   (the value bound into `receipts/2e76988444b0/verification.json`) to
   `eaa0ab0e89f9c5c14576cbdd2d0335358d7755632ec9413af3b5084c09f1a890`, because `git status` now lists two
   untracked review reports — mine plus the concurrently written
   `evidence/review-security_reviewer.md` (not authored by this reviewer). The `verification` receipt must
   be re-taken on the final head after B1–B3 are discharged, and both review receipts must bind to that
   same final fingerprint.
