# Architect design judgment — closing P1-11 «release layer is not publishable»

Route `2e76988444b0`, change `20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698`.
Role: read-only analysis agent. Base commit `403eb13`, HEAD `d4c7a58`. No product file was
modified by this document; every claim below was re-derived on this tree in this session.

Authority read: `engineering/reports/exolon-full-audit-20260920-v3.md` §1 row P1-11 (line 36),
§6 backlog (line 130), §9 macOS-контур (lines 183-196), §10 (lines 205-215);
`engineering/runbooks/macos-probe.sh`; `.../7db1f3/evidence/perfile/pbxproj-build.md`;
`.../7db1f3/evidence/perfile/macos-validation-handout.md`; `.../7db1f3/evidence/v3_measurements.py`.

## 0. Verified baseline (what is actually on disk, not what the brief asserted)

| Claim in the brief | Verdict | Where measured |
| --- | --- | --- |
| `CFBundleShortVersionString = 0.3` | TRUE | `Exolon/Resources/Info.plist:17-18` (4-space indent, literal) |
| `CFBundleVersion = 1` | TRUE | `Info.plist:19-20` |
| `MARKETING_VERSION = 0.5` | TRUE, exactly 2 occurrences, both **target-level only** | `project.pbxproj:1424,1443` |
| `CURRENT_PROJECT_VERSION = 1` | TRUE, 2 occurrences | `project.pbxproj:1418,1437` |
| `GENERATE_INFOPLIST_FILE = NO` | TRUE, 2 | `project.pbxproj:1420,1439` |
| `CODE_SIGN_IDENTITY = "-"`, `CODE_SIGN_STYLE = Manual`, `DEVELOPMENT_TEAM = ""` | TRUE, 2 each | `project.pbxproj:1415-1416,1419` and `1434-1435,1438` |
| `ENABLE_HARDENED_RUNTIME` absent | TRUE, 0 occurrences tree-wide in the pbxproj | `grep -c` on `project.pbxproj` |
| `MACOSX_DEPLOYMENT_TARGET = 10.14`, `SWIFT_VERSION = 5.0` | TRUE and **duplicated** at project level (`1394,1406`) and target level (`1423,1442`) | pbxproj |
| objectVersion 51 / compatibilityVersion "Xcode 9.3" / CreatedOnToolsVersion 10.2 | TRUE; also `LastUpgradeCheck = 1020` | `project.pbxproj:5,1054,1059,1051` |
| 1 native target `500000000000000000000001`, 0 test targets | TRUE; `productType = com.apple.product-type.application`, product `Exolon.app` = `200000000000000000000010` | `project.pbxproj:1028-1042` |
| 0 `.xcscheme` anywhere, no `xcshareddata` | TRUE; `find . -name '*.xcscheme'` → empty; `ls Exolon.xcodeproj` → `project.pbxproj` only | shell |
| `*.xcscheme` is not git-ignored | TRUE — `git check-ignore -v Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme` → rc=1 | shell |

Three facts the brief did **not** state and that change the design:

1. **`INFOPLIST_FILE = Exolon/Resources/Info.plist` is set at target level** (`1421,1440`), so the
   plist is processed and `$(...)` expansion is live — and already load-bearing: `Info.plist` today
   contains four working placeholders (`$(DEVELOPMENT_LANGUAGE)`, `$(EXECUTABLE_NAME)`,
   `$(PRODUCT_BUNDLE_IDENTIFIER)`, `$(PRODUCT_NAME)`). Candidate (a) introduces **no new
   mechanism**, it only joins two keys to a mechanism this same file already depends on.
2. **`LSMinimumSystemVersion` is a literal `10.14`** (`Info.plist:21-22`) and agrees with
   `MACOSX_DEPLOYMENT_TARGET` today. It is a latent trap (documented in
   `perfile/pbxproj-build.md:135`), not a present falsity. See §4.
3. **`v3_measurements.py` pins `"shared_xcschemes": 0`** (line 84) and computes it with a
   tree-wide glob (line 367: `len(list(root.glob("**/*.xcscheme")))`). I ran the tool on this
   tree: `RESULT: ALL_V3_MEASUREMENTS_MATCH_REPORT`, **rc=0**. I then reproduced the counting
   expression on a scratch tree in `/tmp` and added one file at the proposed shared-scheme path:
   `before: 0 → after: 1`. **Candidate (c) therefore deterministically turns the repo's flagship
   self-checking measurer red.** This is the main blast radius of the whole change (§1.C, §5, §6).

Also verified: `scripts/grok_verify.py` → `.grok-stack/adaptive_grok/verification.py` contains no
reference to `.swift`, `.plist`, `.pbxproj` or `.xcodeproj`; its whitespace gate is generic
(`git diff --check` on worktree, index and `base..HEAD`, lines 602-610). **`grok_verify --mode pr`
PASS proves nothing about this change** — it cannot see the files being edited. The only Linux
authority this change can have is a tool we commit ourselves (§5).

## 1. Per-candidate judgment

### A. (a) Info.plist version keys → `$(MARKETING_VERSION)` / `$(CURRENT_PROJECT_VERSION)`

**Recommend: IN. This is the finding.** P1-11's actual defect is *two sources of truth for one
identity*, and the audit's own evidence column names exactly this pair.

Minimal-diff shape — 2 changed lines in `Exolon/Resources/Info.plist`, 4-space indent preserved:

```xml
    <key>CFBundleShortVersionString</key>
    <string>$(MARKETING_VERSION)</string>
    <key>CFBundleVersion</key>
    <string>$(CURRENT_PROJECT_VERSION)</string>
```

Correctness: Xcode's Info.plist preprocessing expands build settings for `INFOPLIST_FILE` when
`GENERATE_INFOPLIST_FILE = NO`; `MARKETING_VERSION` and `CURRENT_PROJECT_VERSION` are
Xcode-defined settings present on the target in both configs (verified above), so both resolve.
This is the stock pattern from current Xcode app templates. `CURRENT_PROJECT_VERSION` is required
as the paired half: without it `CFBundleVersion` stays a literal `1` and the next build still
cannot raise the build number — the exact complaint in `perfile/pbxproj-build.md:140`.

Blast radius: **zero** at runtime for gameplay; no Swift, no bundle id, no `defaults` domain
(`com.exolon.remake` unchanged, so persisted HighScore/checkpoint keys are untouched). One
user-visible value changes: About/Finder/`mdls` report `0.5` instead of `0.3`. Note this makes the
tree self-consistent, not the *product* version decision — see §4.

Linux-verifiable? **Partly, and only partly is enough.** Provable on Linux: the two plist values
are exactly those two placeholders; the two settings exist in both *target-level* config blocks;
no literal digit remains in those two plist strings. Not provable on Linux: that Apple's expander
actually substitutes them. Cheapest macOS assertion (already wired — probe section C prints both
keys, so it costs one build we need anyway): after `xcodebuild … build`,
`plutil -extract CFBundleShortVersionString raw Exolon.app/Contents/Info.plist` must print `0.5`
and the built plist must contain **no `$(MK` substring**. The failure mode to watch for is
`0.3` → substitution not applied, or literal `$(MARKETING_VERSION)` → placeholder unknown to the
expander.

### B. (c) Shared scheme `Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme`

**Recommend: IN.** It is the second half of "publishable identity" in a precise, non-rhetorical
sense: **`Archive` is a scheme-level action.** With zero shared schemes, there is no in-tree
artifact that names an archive configuration or an archive product — the handout says so itself
(`perfile/macos-validation-handout.md:29-31`: «`-target Exolon` обязателен, а не стилистичен…
общей схемы нет и `-scheme Exolon` указывать не на что»). `build/`-directory archaeology is not a
release layer.

Minimal-diff shape: one new file, ~60 lines, no pbxproj edit at all (Xcode does not record shared
schemes in the project object). Attributes that are load-bearing, not decoration:

* root `<Scheme LastUpgradeVersion = "1020" version = "1.3">` — matches this project's
  `CreatedOnToolsVersion = 10.2` / `LastUpgradeCheck = 1020`, so Xcode 10.2…15.x will not offer a
  scheme upgrade.
* `BuildActionEntry` with `buildForArchiving = "YES"` (plus Running/Profiling/Testing/Analyzing
  `YES`). **Without this attribute the Archive action exists but has nothing to archive** — it is
  the single line that makes the route's "Archive action" requirement true rather than nominal.
* `BuildableReference`: `BuildableIdentifier="primary"`,
  `BlueprintIdentifier="500000000000000000000001"`, `BuildableName="Exolon.app"`,
  `BlueprintName="Exolon"`, `ReferencedContainer="container:Exolon.xcodeproj"` — the blueprint id
  and product name are verified above.
* `ArchiveAction buildConfiguration = "Release" revealArchiveInOrganizer = "YES"`;
  `ProfileAction buildConfiguration = "Release"`; `LaunchAction buildConfiguration = "Debug"`;
  `TestAction` present with **no** `<Testable>` child (mirrors what Xcode writes for a
  test-less app target, and keeps the "0 test targets" fact true instead of papering over it).
* Do **not** commit `xcuserdata/…/xcschememanagement.plist` — machine-local, and committing it
  creates a per-developer merge-conflict magnet.

Blast radius: **the largest of the three, and it is a documentation/evidence radius, not a product
one.** (i) It flips `v3_measurements.py` to rc=1 (§0.3, §6). (ii) It makes three committed probe
expectations false in the *opposite* direction — they now call the good state "unexpected" (§6).
(iii) It makes the handout's «`-target` обязателен» paragraph stale. Product risk is low but not
zero: a malformed scheme XML does not fail loudly, it makes `-scheme Exolon` invisible, and a
scheme whose blueprint id does not exist resolves to a target-less scheme that builds nothing.

Linux-verifiable? **Structure: yes, semantics: no.** XML well-formedness, root element and version,
the five action elements, `buildForArchiving="YES"`, `buildConfiguration` of Archive/Profile/Run,
zero `Testable` elements, and cross-reference of `BlueprintIdentifier` +
`ReferencedContainer` against the real pbxproj — all assertable here with `xml.etree`.
Not provable here: that Xcode's scheme loader accepts the file. Cheapest macOS assertion, no
compile required:
`xcodebuild -project Exolon.xcodeproj -scheme Exolon -showdestinations` → rc=0 and a destination
list proves the loader parsed the scheme. Then the real one, in the same session as M-01:
`xcodebuild -project Exolon.xcodeproj -scheme Exolon -configuration Release archive
-archivePath /tmp/Exolon.xcarchive` — and I state honestly: **whether an ad-hoc
`CODE_SIGN_IDENTITY = "-"` archive is permitted by Xcode is not knowable from this host.** The
expected outcome is that the scheme is now *addressable* and any failure is a signing failure, not
a "no scheme" failure; that distinction is the whole deliverable of (c). Record the archive result
as new macOS evidence either way; do not pre-declare it green.

While here — a **probe defect I can prove by reading**, because it will silently mislead the
owner after (c) lands: `macos-probe.sh` section A decides with a substring match,
`case "$LIST" in *"Schemes"*"Exolon"*`. That pattern cannot distinguish a *shared* scheme from an
*Xcode-autogenerated* scheme, and modern Xcode autogenerates and lists `Exolon` for a project with
zero `.xcscheme` files. So section A may already report `PRESENT` on the unmodified tree and will
report it regardless of our work. Fix inside this change (route demands probe updates anyway): the
authoritative shared-vs-generated discriminator is `xcodebuild -project Exolon.xcodeproj -list
-json` (its scheme lists separate shared from generated), with the filesystem check
`test -f Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme` as the portable half that also
runs on Linux.

### C. (b) `ENABLE_HARDENED_RUNTIME = YES` in both target configs

**Recommend: DEFER, with the reason written down and an owner-actionable next step.** (This is
the answer to question 2; the argument is there.)

If the owner overrules it (the human gate is `scope_and_design_approval`, so they may), the
correct minimal-diff shape is 2 added lines, tabs (`^I`×4 — verified with `cat -A`), inserted in
alphabetical position between `DEVELOPMENT_TEAM` and `GENERATE_INFOPLIST_FILE` in **both**
`800000000000000000000003 /* Debug */` and `800000000000000000000004 /* Release */`:

```
				ENABLE_HARDENED_RUNTIME = YES;
```

Symmetry is not stylistic here: `perfile/macos-validation-handout.md:34-36` records a committed,
Linux-recheckable invariant that the Debug and Release target blocks are **byte-identical**. A
Release-only addition breaks a dated claim *and* silently diverges the two configs. Correctness of
the flag itself is fine: hardened runtime is a signature flag (`--options runtime`), and an ad-hoc
signature *can* carry it — `codesign -s -` with options yields
`flags=0x10002(adhoc,runtime)`.

Linux-verifiable? Only absence/presence of the key in the right blocks. Whether it *took* is
macOS-only, and the currently committed probe cannot see it: `macos-probe.sh` line
`hardened_runtime=$(codesign -d --entitlements :- "${APP}" …)` dumps **entitlements**, not the
flags word. With no `.entitlements` file in the tree, that line prints nothing useful forever.
Cheapest macOS assertion to close it, and it must replace that line:
`codesign -dvvv "$APP" 2>&1 | grep -o 'flags=0x[0-9a-f]*(.*)'` → must contain `runtime`;
negative control: `codesign -dvvv` on a build from the pre-change tree must **not** contain
`runtime`.

### D. (d) Other "publishable identity" candidates, each judged

| Candidate | Verdict | Reason |
| --- | --- | --- |
| `LSMinimumSystemVersion` → `$(MACOSX_DEPLOYMENT_TARGET)` | **OUT (defer)** | Same single-sourcing principle, but the value is *not currently wrong* — `10.14` == `MACOSX_DEPLOYMENT_TARGET`. P1-11 is about identity that **disagrees**; this one agrees. It also adds a second unverifiable substitution to a file we are already changing, and the deployment target is duplicated project-vs-target, so a future edit at project level would move the floor without anyone touching the plist. Fix it in the deployment-target change where it can be validated against a real 10.14 machine. |
| App icon (`ASSETCATALOG_COMPILER_APPICON_NAME`, `.xcassets`/`.icns`, `CFBundleIconFile`) | **OUT** | Real publishability gap (`perfile/pbxproj-build.md:149`: no icon asset exists at all → stock placeholder in Dock/Finder/About), but it is new binary assets + pbxproj object graph + a design decision. Not reversible-by-one-revert in spirit, and it is not what the finding measured. Name it as the next release-layer change. |
| `LSApplicationCategoryType`, `NSHumanReadableCopyright` | **OUT (one-liners, no gain today)** | Both absent; both inert and trivially Linux-checkable; both only *observable* in a rebuilt bundle. Bundling them in would dilute the "identity is single-sourced" claim with cosmetic plist growth. Next release-shell change. |
| `GENERATE_INFOPLIST_FILE = YES` + `INFOPLIST_KEY_*` migration | **OUT** | This is the modern shape and it *would* solve (a) too, but it deletes the file we are auditing and moves every key into build settings — a rewrite, not the smallest coherent change, and it silently changes which 4 placeholders currently work. |
| Probe: replace `plist_marker_version_present=$(grep -c 'MARKETING_VERSION = 0.5' …)` with a comparison against `xcodebuild -showBuildSettings` | **IN (part of the probe-update mandate)** | Today it hard-codes `0.5`, is misnamed (it greps the pbxproj, not the plist), and re-breaks on the next version bump — the exact brittleness P1-11 was caused by. Compare built plist value to the setting value instead of to a literal. |
| Probe: document that `-scheme Exolon` becomes available and keep `-target Exolon` as the build path | **IN** | Keeping both paths working is the point of (c); switching the probe's own build to `-scheme` in the same commit would remove the fallback the handout protocol currently relies on. |
| `DEVELOPMENT_TEAM` / real signing identity / `.entitlements` | **OUT** | Requires secrets and accounts this repository must never hold; AGENTS.md forbids agent handling of signing keys. |

## 2. The real risk of (b) in this configuration — and why I defer it

Configuration under analysis, all verified: ad-hoc `CODE_SIGN_IDENTITY = "-"`,
`CODE_SIGN_STYLE = Manual`, `DEVELOPMENT_TEAM = ""`, `CODE_SIGN_ENTITLEMENTS` absent (0 matches
tree-wide), `MACOSX_DEPLOYMENT_TARGET = 10.14`.

Hardening, notarization and Gatekeeper are three different things and only one of them is
reachable from this tree:

* **Gatekeeper** rejects a quarantined download unless it has a valid Developer ID signature (or
  the user overrides). An ad-hoc signature is rejected *regardless* of the hardened-runtime flag.
  `perfile/pbxproj-build.md:144` already states the outcome plainly: ad-hoc ⇒ «"Developer cannot be
  verified" при скачивании — гарантировано».
* **Notarization** requires a Developer ID signing identity, a distribution-time secure timestamp
  and `notarytool` submission, then a stapled ticket. None of those exist here and none can be
  created by editing tracked files.
* **Hardened runtime** is only a *prerequisite* for notarization and a set of *runtime
  enforcement rules*. Turning it on in this configuration therefore buys exactly **zero**
  additional publishability today, while imposing real enforcement on a binary this project has
  never been proven to run.

That last clause is the decisive one and it is sourced, not rhetorical: the handout's own M-01
expectation is «сборка **успешна** (первый в истории проекта type-check)». We do not currently
possess evidence that this target compiles at all on a maintained Xcode. Enabling hardened runtime
inside the same change that first establishes buildability destroys attribution: if the run fails,
no one can tell whether the cause is the (a)/(c) identity work, the flag, or a pre-existing
compile error. The three candidate effects also cannot be separated on the only host we have.

Second, and specific to this game: the hardened runtime is *not* an inert flag. It activates
library validation, blocks unsigned executable memory, restricts legacy plugin loading, and
restricts `task_for_pid` — i.e. **debugging**. The target links `Cocoa`, `SpriteKit`,
`GameController` (verified in `PBXFrameworksBuildPhase`) — all Apple-signed, so *library
validation should pass*; that "should" is precisely the class of claim this repository just spent
a 213-dangling-citation sweep learning not to ship unproven. Two concrete, game-specific unknowns
I cannot close on Linux: whether `GameController`'s HID/multipeer paths behave identically under
validation on 10.14-class systems, and whether a Debug build with hardening can still be launched
under the debugger without `com.apple.security.get-task-allow`. Hardening on the **Debug** config
is the part most likely to cost the maintainer time and least likely to be noticed by any check we
can run here.

**Recommendation: defer (b), do not "do it with an entitlements file" either.** Adding an
`.entitlements` file would *reduce* the unknown (it makes the relaxations explicit) but it raises
the scope past the finding: a new file, a new build setting, and a design decision about sandbox
vs MAS vs direct distribution that belongs to a signing change, not to a version-identity change.

Reason the owner can act on, one sentence for the backlog: *the hardened-runtime half of P1-11 is
deferred because with ad-hoc Manual signing it cannot change any Gatekeeper or notarization
outcome, while it does change runtime enforcement for an app whose first successful build is still
unproven; schedule it as its own change immediately after macOS row M-01 goes green, gated on the
`codesign -dvvv … | grep runtime` assertion plus one manual gamepad/HUD/audio launch run, and
decide the `.entitlements` file in that change when there is a real failure to justify it.*
Consequence to state out loud in the closure note: **P1-11 must be recorded as *partially*
closed by this change** — identity and scheme closed, signature/hardening open — because the
audit's §1 evidence column names all three (версии/схема/подпись). Marking it closed would be
the same overclaim the v3 report was built to prevent.

## 3. Rollback, forward recovery, and the signal that it worked

`change-spec.yaml` types this as `"rollback": {"maximum_steps": 1, "strategy": "forward_fix"}` and
the design fits that constraint by construction:

* **Rollback = one `git revert <sha>`** of the single commit. It is a clean 1-step operation
  because all three edits are plain-text and nothing is generated, migrated or persisted: two
  literal→placeholder line swaps in a tracked plist, and one *new* file that revert deletes.
  There is no state to unwind: the bundle id is unchanged, so `defaults read com.exolon.remake`
  (HighScore, the write-only checkpoint keys) survives in both directions, and LaunchServices
  re-registers the app on next build with no residue. `xcuserdata/` must not be in the commit —
  that is what keeps revert single-step.
* **Asymmetric files need no separate path**, but note them for the operator: reverting (a)
  re-introduces the *false* `0.3`, and reverting (c) re-introduces "no shared scheme", i.e. both
  re-opens the finding rather than breaking anything. A partial recovery is still expressible in
  one step (`git checkout <base> -- Exolon/Resources/Info.plist`) if the owner wants to keep the
  scheme and drop the version swap; that is a 1-step forward fix, not a rollback ladder.
* **Forward recovery if the substitution does not happen on macOS** (bundle shows
  `$(MARKETING_VERSION)` literally): the smallest forward fix is one plist line back to a literal
  plus a P2 finding that the setting name is unavailable to this Xcode; no product code depends on
  the placeholder, so nothing else has to move.

Observable signals, by host:

* **macOS, version identity (the finding itself):**
  `xcodebuild -project Exolon.xcodeproj -target Exolon -configuration Debug build &&
  plutil -extract CFBundleShortVersionString raw build/Debug/Exolon.app/Contents/Info.plist &&
  plutil -extract CFBundleVersion raw build/Debug/Exolon.app/Contents/Info.plist`
  expected `** BUILD SUCCEEDED **`, then `0.5`, then `1` — and specifically **not** `0.3` and
  **not** a `$(…)` string. One-line alternative: `defaults read "$PWD/build/Debug/Exolon.app/Contents/Info" CFBundleShortVersionString`.
* **macOS, scheme is real:** `xcodebuild -project Exolon.xcodeproj -scheme Exolon
  -showdestinations` → rc=0 with a destination list (proves the loader parsed the file), then the
  archive attempt in §1.C.
* **Linux, the proof that holds up:** `python3
  engineering/changes/20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698/evidence/release_layer_check.py
  --root . ; echo rc=$?` → `RESULT: RELEASE_LAYER_OK`, rc=0, with every macOS-only AC printed as
  `SKIP_MACOS_REQUIRED` and never as PASS. Plus the scope proof
  `git diff --name-only 403eb13..HEAD -- Exolon Exolon.xcodeproj` listing **exactly three** paths
  (`Exolon/Resources/Info.plist`, the new `.xcscheme`; a fourth — `project.pbxproj` — appears only
  if the owner forces (b) in).
* **macOS, the deferred item's own signal, for the future change:**
  `codesign -dvvv build/Debug/Exolon.app 2>&1 | grep -o 'flags=0x[0-9a-f]*(.*)'` must gain the
  `runtime` token; the pre-change build must not have it.

## 4. What must explicitly stay OUT of this change

| Out of scope | Why it is out, not merely inconvenient |
| --- | --- |
| Adding an XCTest target (or any test target) | The 0-test-target fact is *measured evidence* in three committed artifacts (`v3_measurements.py` `test_targets=0`, the audit row, the probe's §F line). A new target is a pbxproj object-graph change plus a scheme `Testables` change, unvalidatable here, and P1-11 never claimed schemes are unavailable *because* of tests. Track as its own item. |
| Notarization, App Store / MAS, `xcodebuild -exportArchive`, Developer ID, `.entitlements`, sandboxing | Requires identities, certificates and secrets that must never enter this tree (AGENTS.md prohibits agent handling of signing material). Also blocked behind the deferred (b). |
| Deciding the marketing version (bumping `MARKETING_VERSION` to 0.6, or "fixing" 0.5 back to 0.3) | This change removes the **dual source of truth**; it does not adjudicate the number. Editing both files to agree on a *chosen* value re-creates the same disease with a nicer number and would make the checker I am specifying here structurally unable to detect a future regression. |
| `objectVersion 51` → modern, `compatibilityVersion`, `LastUpgradeCheck`, letting Xcode "upgrade" the project | Xcode rewrites the whole 1 475-line pbxproj (renumbered sections, reordered attributes, file-per-group churn). Diff becomes unauditable, every committed line citation (`pbxproj:1424,1443`, `Info.plist:17-18`) in dated evidence dies at once, and it is not 1-step reversible. |
| Refactoring Swift for testability; any `Exolon/*.swift` edit | No Swift change can affect the measured P1-11 evidence; it also drags this change into the never-proven-to-compile path and destroys failure attribution for (a)/(c). |
| `LSMinimumSystemVersion`, app icon, `LSApplicationCategoryType`, copyright, `GENERATE_INFOPLIST_FILE=YES` migration | Judged individually in §1.D: none is currently false, all need a rebuilt bundle to observe, mixing them in makes the closure claim unfalsifiable. |
| Declaring P1-11 fully closed | The audit's evidence column names three clauses — версии/схема/подпись. This change closes the identity and scheme clauses only; `подпись` (signing/hardening) stays open (§2), so the closure note must say "partially closed" or the finding will be re-audited against a false claim. |
| Creating `START_HERE.md` / `PROJECT_STATE.json` / `mistakes.md` | Verified absent on this tree, yet AGENTS.md makes them mandatory entrypoints ("Fresh-clone bootstrap", "Agent self-learning", and it tells agents to log to a `mistakes.md` that does not exist). That is a stack/factory contract gap, unrelated to the macOS release layer; fix it in the factory track, do not smuggle it into a release commit. |

## 5. Acceptance criteria for `evidence/release_layer_check.py` (Linux, self-checking, with mandatory controls)

House style is fixed by `v3_measurements.py`: `EXPECTED` dict, `got` measurements, a `controls`
dict where each entry **must** flip, `rc=0 ⇔ report matches`, `RESULT: ALL_V3_MEASUREMENTS_MATCH_REPORT`.
The new tool copies that contract and ends with `RESULT: RELEASE_LAYER_OK` / `RELEASE_LAYER_MISMATCH`.
Each probe below names its control; **if a control does not flip the verdict, the tool must exit
rc=1** — that is the repo's rule («every probe needs a contradictory control that is required to
break»), and the reason `decisions.md` keeps the TMX-regex lesson alive.

AC ids follow this repo's convention (`AC-001`…; `OBJ-001` already in the spec, and note
`spec.py` requires every gate-time criterion to carry non-empty `evidence` whose `test` path
**exists** — so these ids can only be typed into `change-spec.yaml` after the tool is written, and
`FORBID-*` / `required_scopes` are mandatory because `risk.tier = "red"`).

| AC | Binary assertion (Linux) | Control that MUST flip the verdict |
| --- | --- | --- |
| **AC-001** version is single-sourced | `Info.plist` `CFBundleShortVersionString == "$(MARKETING_VERSION)"` and `CFBundleVersion == "$(CURRENT_PROJECT_VERSION)"`, byte-exact, and neither value contains a digit | Mutate the in-memory plist copy to `0.3` → FAIL. Second control: change only `CFBundleVersion` to `$(MARKETING_VERSION)` (wrong-variable swap) → must FAIL; a probe that checks "starts with `$(`" would pass it, so the check must be per-key equality |
| **AC-002** the placeholders resolve to settings **on the target**, not somewhere in the file | Parse the pbxproj into blocks; `MARKETING_VERSION` and `CURRENT_PROJECT_VERSION` each present exactly once in the body of **both** target configs `800000000000000000000003`/`004` | Control: measure the project-level blocks `001`/`002` → count must be **0** (verified: it is). This is the control that proves block attribution; a whole-file `grep -c` yields 2 either way and would certify a plist that expands to empty |
| **AC-003** no unresolved placeholder can ship | Collect every `$(VAR)` in `Info.plist`; each VAR must be in the allowed set {the 4 pre-existing} ∪ {`MARKETING_VERSION`,`CURRENT_PROJECT_VERSION`} and the 2 new ones must also appear as pbxproj settings | Control: inject `$(NOT_A_SETTING)` into a copy → FAIL. This is the direct guard against About printing a literal `$(…)` |
| **AC-004** shared scheme exists and is shared | `os.path.isfile("Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme")` and `.xcscheme` count tree-wide == 1 | Three separate controls, all required: (i) relocate the file to `xcuserdata/…` → FAIL (proves "shared" is checked, not "some scheme"); (ii) delete it → FAIL; (iii) add a second dummy scheme → FAIL (catches an accidental extra/`Exolon 1.xcscheme`) |
| **AC-005** Archive action is genuinely wired | XML parse: root `Scheme`, `version == "1.3"`, `BuildActionEntry/@buildForArchiving == "YES"`, an `ArchiveAction` with `@buildConfiguration == "Release"`, plus `LaunchAction` and `ProfileAction` present | Control: flip `buildForArchiving` to `"NO"` → FAIL (this is the mutation a careless author makes while typing the template); control 2: set `ArchiveAction/@buildConfiguration = "Debug"` → FAIL |
| **AC-006** no test target smuggled in | `TestAction` has **zero** `<Testable…>` descendants; `isa = PBXNativeTarget` count == 1; no `com.apple.product-type.bundle.unit-test`; product-type of `5000…0001` is `com.apple.product-type.application` | Control: append one `<Testable>` block referencing a fictional bundle id → FAIL |
| **AC-007** scheme refers to the real, unique target | `BuildableReference/@BlueprintIdentifier` == the single native-target id; `BlueprintName == "Exolon"`; `BuildableName == "Exolon.app"`; `ReferencedContainer == "container:Exolon.xcodeproj"` and that container path exists; `BuildableIdentifier == "primary"` | Control: corrupt the blueprint id by one hex digit → FAIL. Control 2: point `ReferencedContainer` at `container:Nope.xcodeproj` → FAIL |
| **AC-008** Debug/Release target configs stay symmetric | The two target config blocks are identical modulo the `name = …;` line (re-derives the dated handout claim), **and** `ENABLE_HARDENED_RUNTIME` is absent in both or present in both — never one | Control: insert `ENABLE_HARDENED_RUNTIME = YES;` into the Debug block only → both sub-assertions FAIL. This is the AC that makes a future one-sided (b) impossible to land quietly |
| **AC-009** deferred (b) is recorded, not silently skipped | `ENABLE_HARDENED_RUNTIME` absent in tree **⇒** the deferral note exists in this package (`release.md` §Deferred contains the literal token `ENABLE_HARDENED_RUNTIME`); present ⇒ this AC inverts and demands the macOS `flags=…(runtime)` evidence line instead | Control: remove the deferral sentence while the flag stays absent → FAIL. A pure "is the flag off" check would pass a silently dropped commitment; this one cannot |
| **AC-010** dated evidence was appended to, never rewritten | For the protected dated set (`evidence/v3_measurements.py`, `evidence/perfile/pbxproj-build.md`, `evidence/perfile/macos-validation-handout.md`, `engineering/reports/exolon-full-audit-20260920*.md`, `engineering/reports/exolon-initial-audit*.md`): `git diff --name-only <base>..HEAD --` that set must be **empty** | Control: append one comment line to `v3_measurements.py` in a scratch worktree → FAIL. This is the only machine-enforced form of the "append, never overwrite dated evidence" rule; note it must run against the route base `403eb13`, and it deliberately tolerates *new* files in those dirs |
| **AC-011** Linux must not certify macOS-only facts | The tool hard-refuses `--assume-macos`; every macOS-only AC (bundle value after expansion, scheme loader acceptance, archive availability, `codesign` runtime flags) is printed `SKIP_MACOS_REQUIRED` and is excluded from the `ok` conjunction while being *listed* in the summary | Control: call `verify_bundle_expansion()` directly on Linux → must raise/return SKIP, never `True`. This AC exists because this repo's own failure mode — the last three commits are correction and citation-integrity passes — is claiming more than was measured |

Structural requirements for the tool: stdlib only (`xml.etree`, `pathlib`, `argparse`, `subprocess`
for the git call); parse the plist with `xml.etree`, **never** regex — the regex prohibition in
`v3_measurements.py`'s docstring and `decisions.md` exists because regex measurement in this repo
already produced a 97-vs-127 error, and `Info.plist` is exactly the kind of file where a
self-closing tag breaks a pattern; no trailing whitespace anywhere (`git diff --check` is an
active gate at `verification.py:602-610`); `--root <path>` and `--json` flags so it can be pointed
at a scratch tree to run controls, matching `v3_measurements.py`'s interface; every control must
operate on an **in-memory copy** so the committed tree is never mutated by its own self-test.

The AC-001/AC-002 pair is the only combination that closes P1-11's measured defect: AC-001 alone
passes on a plist that points at a nonexistent setting, AC-002 alone passes on an unchanged plist
with the settings sitting correctly in the pbxproj. Both, with both controls, is the finding.

## 6. Committed documents this change makes false, and the handling

The rule in force (this repo's own, stated in `exolon-full-audit-20260920-v3.md` §0: superseded
reports «получает баннер; тело не правится») is **append a dated correction, never rewrite the
body** — because the body is a measurement *of a tree at a commit*, and at `403eb13` every number
in it is correct. Note this rule is machine-guarded here by **AC-010**, so it is not just
etiquette.

| Artifact | Line/claim | After the change | Handling |
| --- | --- | --- | --- |
| `engineering/runbooks/macos-probe.sh` §A | `EXPECTED: no shared scheme`; branch prints `PRESENT (unexpected: аудит finding no .xcscheme in tree)` | Actively misleading: it labels the *goal* as unexpected | **Edit in this change** — it is a runbook, not dated evidence, and the route task orders it. Replace with shared-vs-`generated` discrimination (`-list -json`) plus the `test -f …/xcshareddata/…` assertion; keep an explicit negative control line |
| same, §C | `EXPECTED: CFBundleShortVersionString=0.3 при MARKETING_VERSION=0.5 — P1 из pbxproj-лагa` | Inverts to `0.5` | **Edit**: expectation becomes `0.5` *and* `== $(xcodebuild -showBuildSettings … MARKETING_VERSION)`; drop the hard-coded `plist_marker_version_present` grep (§1.D) |
| same, §F | `ENABLE_HARDENED_RUNTIME отсутствует` | Still true (deferred) | Edit only to add the pointer that (b) is deferred with reason + the `codesign -dvvv | grep runtime` command that would prove it, and fix the `--entitlements` line which cannot observe the flag (§1.C) |
| `…/7db1f3/evidence/v3_measurements.py:84` | `"shared_xcschemes": 0`, rc=0 today (measured) | **rc=1 on the post-closure tree**, deterministically | Do **not** edit the value (dated, AC-010). Record in this package's closure note that a red `shared_xcschemes` on the post-closure tree is the *expected* result and is a **cutover signal, not a regression** — so nobody "fixes" it by deleting the scheme. Supersede those three keys (`shared_xcschemes`, `test_targets`, and the version half) with `release_layer_check.py` AC-004/AC-006/AC-001, which is exactly what `v3_measurements.py` did to `linux_static_audit.py` before it. If the owner insists every committed tool be green, the *only* acceptable edit is a dated comment **next to** the key — never a changed number — and it must be approved as an exception to AC-010 |
| `engineering/reports/exolon-full-audit-20260920-v3.md` §1 row P1-11 (line 36) | plist 0.3 vs 0.5, `.xcscheme` = 0, no hardened runtime | Two of three clauses now historical | **Append**, do not edit the row: add a dated `§11 Closure delta (2026-09-21)` section naming the closure commit, what flipped, what is deferred (`подпись`), and the exact Linux command that now measures it. Add one new row to §0's hierarchy table pointing at this package. §6's backlog line 130 keeps P1-11 listed with a parenthetical *in a new line*, not by rewriting the list |
| `engineering/reports/exolon-full-audit-20260920.md` (v2), `exolon-initial-audit.md:40,155,350,368`, `exolon-initial-audit-backlog.md:38` | 0.3-vs-0.5 as open; the original `V1/P3` grading (`V1` even graded **P3**, and the v3 promotion to **P1** is the escalation this change answers) | open→partly closed | Already banner-carrying historical layers. **No edit.** Their truth condition was "at the tree I measured" |
| `…/7db1f3/evidence/perfile/pbxproj-build.md:27,36-38,138,140,143,144,149` | `.xcscheme` = 0; `CFBundleShortVersionString` = 0.3 "P1-расхождение"; hardened absent; no icon; `CODE_SIGN_ENTITLEMENTS` absent | lines 27/36-38/138/140 become historical; 143/144/149 stay true | **No edit** (dated perfile primary). AC-008 re-derives the still-live invariant («Debug/Release bodies byte-identical», handout:34-36) so the one genuinely reusable conclusion from this file survives the closure as a checked assertion instead of a sentence |
| `…/7db1f3/evidence/perfile/macos-validation-handout.md:26-36` and M-01 row | «`-target Exolon` обязателен, а не стилистичен», 0 schemes; M-01 expects `CFBundleShortVersionString` = **0.3** with the explicit control «собралось 0.5 ⇒ вывод V1 неверен» | M-01's *control* is now the *expected* result — the handout defines our success as its own falsification | **No edit.** Ship `evidence/perfile/macos-validation-handout-v2.md` in this package: M-01′ with `0.5`/`1`, the `-scheme` path added alongside `-target`, the archive attempt and its honest unknown, and a line stating that M-01 turning green is the precondition for releasing deferred (b). Order-of-work matters for the operator: **the macOS session should run M-01′ once, after this change, and that single run closes both the release-layer evidence gap and the never-built-before gap** |
| `README.md` | No version, scheme, signing or bundle claim anywhere (checked) | — | **Not made false.** But AGENTS.md's «README before push» requires README to state where release identity lives; adding two lines (identity is single-sourced in `project.pbxproj`, scheme path, and the deferred hardening) is legitimate in this change if the owner wants a release-tag path. Optional, not required |
| `ORIGINAL_MECHANICS.md`, `LEVEL_COMPILER_AUDIT.md` | No version/scheme claims (grepped) | — | No action |
| `.grok-stack/runtime/receipts/7db1f3f0b126/verification.json` | Lists `v3_measurements.py` only as a *changed file*, not as an executed gate | Stale-by-rule | No action; AGENTS.md already defines any repo change as invalidating receipts |

## 7. Recommended shape of the change (for the single `write_agent` that owns it)

One commit, three product-side paths, in this order: (1) `Exolon/Resources/Info.plist` — the 2-line
swap of AC-001; (2) `Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme` — new file per
AC-004/005/007; (3) `engineering/runbooks/macos-probe.sh` — §A/§C/§F expectations plus the
`codesign` flags fix. Then this package: `release_layer_check.py`,
`macos-validation-handout-v2.md`, `release.md` §Deferred carrying the (b) reason verbatim from §2,
the `change-spec.yaml` AC/FORBID/INV/approvals fill-in (currently empty and
`success_metric`/`target` = `UNKNOWN`, which `spec.py` rejects at gate time for a red-risk change —
the spec must be typed **before** `grok_verify --mode pr` can be expected to pass), and the
`§11 Closure delta` append to the v3 report. No `project.pbxproj` edit unless the owner forces
(b) in, in which case exactly 2 tab-indented lines in both target configs and AC-008 must still be
green.

---

## Summary (8 lines)

1. **In scope, one commit:** `Info.plist` → `$(MARKETING_VERSION)` + `$(CURRENT_PROJECT_VERSION)`
   (2 lines) and a shared `Exolon.xcscheme` with `buildForArchiving="YES"` + Archive@Release.
2. **In scope:** `macos-probe.sh` §A/§C/§F expectation flip, its non-discriminating scheme match,
   and its `codesign --entitlements` line that cannot observe the hardened-runtime flag.
3. **In scope:** committed `evidence/release_layer_check.py` — 11 Linux binary ACs, each with a
   control that must break, AC-010 machine-enforcing "append, never overwrite dated evidence".
4. **Deferred with reason:** `ENABLE_HARDENED_RUNTIME = YES` — with ad-hoc `CODE_SIGN_IDENTITY="-"`
   it buys zero Gatekeeper/notarization outcome while changing runtime enforcement for an app whose
   first successful build is still unproven; sequence it right after macOS M-01 goes green.
5. **Also deferred:** `LSMinimumSystemVersion` substitution, app icon, category/copyright keys,
   `GENERATE_INFOPLIST_FILE=YES` migration, `.entitlements`, any signing identity or team.
6. **Out of scope:** XCTest target, notarization/MAS, choosing the version number itself,
   `objectVersion`/project upgrade, Swift testability refactors, missing `START_HERE.md`/
   `PROJECT_STATE.json`/`mistakes.md` (factory gap).
7. **Rollback:** one `git revert` (typed as `maximum_steps: 1`); macOS proof is
   `plutil -extract CFBundleShortVersionString raw …` → `0.5`; Linux proof is the checker at rc=0
   with controls flipping.
8. **Top residual risk:** adding the scheme deterministically turns the flagship committed
   measurer `v3_measurements.py` red (`shared_xcschemes: 0` → 1; its current rc=0 verified), so if
   the expected-cutover is not written down as clearly as the fix, the next agent will "repair" it
   by deleting the scheme — and P1-11 must be recorded as **partially** closed (identity+scheme,
   `подпись` open), not closed.
