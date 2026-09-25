# Analysis — architect (wave D): P1-10 stage-end composition + P1-11 remainder split

Route `8341b7aa6eb4`, base commit `295690b7fc724e57b37b5fac86b71c1da7d8b032`,
tree fingerprint `5b47433c…1ad3`. READ-ONLY analysis; no product file was touched.

Evidence read (all line numbers verified against this working tree):

| Anchor | What it proves |
| --- | --- |
| `Exolon/GameCore/GameScene.swift:610-631` | `checkScreenExit()` calls `applyOriginalStageBoundaryIfNeeded(completedZone: gameState.zone)` at `:612` **before** `guard !next.isEmpty, includedLevels.contains(next)` at `:614`; body `:622-631` = `awardPoints(gameState.lives * 1_000)`, `if lives < GameState.startingLives { lives += 1 }`, `ammo = startingAmmo`, `grenades = startingGrenades`; stale comment `:623-625` claims the code is dormant |
| `GameScene.swift:660-667` | `awardPoints(_ value: Int)` is the single score funnel and clamps at `999_999`, then raises + persists `highScore` |
| `GameScene.swift:633-658` | `transition(to:)` sets `gameState.zone`, computes `isStageStart = [0,25,50,75,100].contains(zone)` (`:644`) and does **not** reset `accumulator`/`previousUpdateTime` (wave-A P1-9 owns this line) |
| `GameScene.swift:234-237` | changing-room activation site: `player.toggleExoskeleton()` + `playerNode.update` + `showBanner("EXOSKELETON ON"/"OFF")` inside the fixed step, edge-triggered on `jumpJustPressed` |
| `GameScene.swift:346`, `:557` (`:546` region) | suit grants double blaster fire and immunity (`continue` before hazard test) — the *gameplay* consequence of the flag wave-D must clear |
| `GameScene.swift:738-760` | `enterContentComplete(nextLevelName:)` shows `FULL COMBAT ABILITY` when `zone >= 124 && next.isEmpty`, else `CONTENT COMPLETE`; calls `saveCheckpoint()` |
| `GameScene.swift:761-767` | `showTitleAfterContentComplete` → `.title` (norm `ORIGINAL_MECHANICS.md:148` says "returns the game to the beginning" — a **separate** deviation, see §8) |
| `GameScene.swift:963` | the **only** `setExoskeleton(false)` in the product, on `restartFromBeginning` — confirms `engineering/reports/exolon-full-audit-20260920-v3.md:35` ("3 из 6 правил отсутствуют") |
| `GameScene.swift:123-146` | fixed-step loop: `accumulator += min(frameTime, maximumFrameTime)`; `while accumulator >= fixedTimeStep`. No tick counter exists at base (wave-A `FixedTickDriver` introduces it) |
| `Exolon/GameCore/GameState.swift:82-104` | `startingAmmo = 99`, `startingGrenades = 10`, `startingLives = 9` (so the current `lives < 9` test **is** the "capped at 9" rule; that rule is not missing) |
| `Exolon/GameCore/Player/Player.swift:1-2`, `:26`, `:243-250` | `Player` imports `CoreGraphics`+`Foundation` only (SpriteKit-free, needs the existing CG shim on Linux); `private(set) var hasExoskeleton`, `toggleExoskeleton()` (guarded by `!isDying`), `setExoskeleton(_:)` |
| `ORIGINAL_MECHANICS.md:138-148` | the six stage-end rules + `:147` stage-start coordinates; `:115-118` suit persists through deaths until stage end, cleared at stage end, forfeits bravery |
| `engineering/changes/20260919-…-7db1f3/evidence/perfile/gamescene.md:62` (GS-02) | the missing-rule list measured: no `10_000`, no `0/1000/3000/5000/7000`, no suit clear; chain `L01S01→…→L05S25` complete so the guard is live |
| `…/evidence/analysis-docs_researcher-fullaudit.md:215-216, 285, 549` | `blk_stage_end` markers sit on **type 15** in all five `S25` maps and load into `TMXLevelRuntime.stageExitMarkers` (`TMXLevelRuntime.swift:30`, `:370`) which is **never read** by the product |
| `engineering/changes/20260924-…-32f59c/architecture.md:37`, `tasks.md:17-19` | wave A owns `Exolon/GameCore/Diagnostics/StageBoundaryLedger.swift` (Foundation-only, once-per-playthrough award + suppression witness). **Measured gap:** the string "Ledger" appears nowhere in wave A's `evidence/analysis-architect.md` (34 KB) or `analysis-integration_architect.md` (36 KB) — the ledger's *API* is not frozen anywhere; only its responsibility and file path are |
| `…/20260924-…-32f59c/evidence/analysis-integration_architect.md:271-273, 380-384` | frozen wave-A event payloads and stream predicate B (the collision in §3) |
| `engineering/changes/20260921-…-2e7698/change-spec.yaml:18-105`, `tasks.md`, `evidence/release_layer_check.py`, `evidence/perfile/macos-validation-handout-v2.md`, `engineering/runbooks/macos-probe.sh` | the committed P1-11 release layer, its self-checking verifier, the dated handout convention, and what the probe already reads (`§A` scheme discriminator, `§C` codesign flags + `spctl`, `§B2` `-scheme`/`WITH_ARCHIVE`, `§E1-E15` manual, `§F` non-claims) |
| `Exolon.xcodeproj/project.pbxproj:1415-1444` | remaining P1-11 clause, measured at base: `CODE_SIGN_IDENTITY = "-"`, `CODE_SIGN_STYLE = Manual`, `DEVELOPMENT_TEAM = ""`, **no** `ENABLE_HARDENED_RUNTIME`, **no** `CODE_SIGN_ENTITLEMENTS` in both target blocks; `find -name '*.entitlements'` → 0 results; `Exolon/Resources/Info.plist` still carries the literal `LSMinimumSystemVersion 10.14` while version keys are now `$(…)`. |

---

## 1. The one question that decides everything: what is a *pure function* here?

P1-10 has exactly one arithmetic/state core and a lot of skin. Split by **who can be wrong
on Linux**:

| Belongs in `StageBoundaryLedger` (wave A file, Foundation-only, Linux-testable) | Belongs in `GameScene` (SpriteKit, macOS-only to observe) |
| --- | --- |
| Stage-scoped state: `stageStartTick`, `tookExoskeletonInStage` latch, `awardedZones` set, playthrough identity — the ledger is the *only* stage-scoped state machine; a second copy in `GameScene` is how GS-01 was born | `bannerLabel` / `terminalOverlay` text and `SKAction` timings (`showBanner` `:669-681`, `enterContentComplete` `:738-760`) |
| Terminal trigger recognition: `completedZone ∈ {24,49,74,99,124}` and the `already_awarded` / `not_stage_end` suppression outcome (wave A ruling 3) | calling `awardPoints(_:reason:)` with the deltas the ledger returned, so `score.awarded` keeps wave A's single-funnel property |
| Award **sequence** as data: `[lives×1000, bravery 10000?, timed phase?, +1 life (cap 9), refill 99/10, clearExoskeleton]` — ordered, each component separately observable | applying `player.setExoskeleton(false)` + `playerNode.update(from:dt:)` (the ledger must never touch `Player`: it does not import it, and that keeps the shim out of the harness) |
| `bravery` predicate from `tookExoskeletonInStage` (§5) | `saveCheckpoint()` ordering, `flowState` writes, `persistence` |
| `timed` phase from `stageElapsedTicks` (§6) — a pure table, no `Date()`, no `SKAction.wait` | *when* to sample the observation (the fixed step where `x > 510` holds) — that stays `GameScene.swift:610` |
| Cap arithmetic **declared as earned vs applied**: post-clamp deltas are produced by `awardPoints`, so the ledger returns *earned* components + the running `pointsBefore` it was given, and GameScene reports back what was *applied* (see the risk in §7) | HUD refresh, `stepLabel`, F1 overlay |

Rule that keeps wave D rebase-safe: **wave D adds no new product file.** Every P1-10 type
(`StageBoundaryObservation`, `StageBoundaryAward`, `TimedBonusPhase`) goes *inside*
`Exolon/GameCore/Diagnostics/StageBoundaryLedger.swift`. That deletes the whole
`project.pbxproj` conflict class — wave A's task 11 writes 4 pbxproj edits per new file into
the same regions wave D would touch, and pbxproj merges in this repo have already produced one
audit finding (`release_layer_check.py` exists because a grep could not certify block membership).

## 2. Emission seam (so the witness cannot be forgotten)

`StageBoundaryLedger` holds `var events: any GameplayEventSink = NullGameplayEventSink.shared`
and emits **its own** `bonus.stage_points` / `bonus.stage_boundary_suppressed`. Justification is
wave A's own normative requirement — "an assertion that only counts awards would also pass on a
run where the bonus silently never fires at all" (`analysis-integration_architect.md:386-388`) —
which is only structurally guaranteed if the suppression emit sits on the same code path as the
suppression decision. `GameScene` emits nothing for the ledger; `awardPoints` keeps emitting
`score.awarded`.

`GameplayEventSink` is Foundation-only per wave A's boundary rule, so this does not cost the
Linux harness anything, and `.synchronous`/memory-sink modes keep the ledger testable with no
file writer at all.

## 3. MEASURED COLLISION with wave A's committed predicate B (must be fixed by amendment, not by wave D working around it)

Wave A freezes (`analysis-integration_architect.md:380-384`):

```
sum(points) from `score.awarded{reason:"stage_boundary"}` <= 5 * lives_cap_bonus
```

and the `score.awarded.reason` catalog (`:273`) is closed over
`(blaster_shotdown, bubble, egg, force_field, grenade_kill, guidance, launcher, stage_boundary)`.

At base, one boundary awards ≤ `9 × 1000 = 9000`, so the bound is `45 000`. After P1-10 the same
boundary earns `9000 + 10 000 bravery + 7 000 timed = 26 000`, i.e. a legitimate correct run
reaches `130 000` — **wave A's own stream predicate turns RED on wave D's correct build**, and
worse, wave A's negative control `p1_8_fixed_passes_and_revert_fails` would then be able to pass
on a reverted fix for an unrelated reason. Three sub-decisions follow, and they must be taken
*before* either branch merges:

1. Do **not** silently widen the constant inside wave A's already-frozen auditor by wave D.
   `gameplay_log_check.py` lives in wave A's evidence and is fingerprint-bound to wave A's write
   owner (`tasks.md:13`). One tree, one writer. Wave D supplies the arithmetic; the bound is
   amended in wave A's package by wave A's owner (or by the controller after wave A rebases),
   and wave D ships an independent `evidence/stage_end_check.py` that re-derives the award from
   components so the corrected bound is *also* attested by a file wave D owns.
2. Prefer the **component-form bound** over a bigger magic number, because a bigger constant
   cannot distinguish "correct" from "farmed bravery 500 times":
   `count(bonus.stage_points) ≤ 5`, `≤1` per `completed_zone` per playthrough (unchanged), and
   per award `points == lives×1000 + bravery_points + timed_points` with
   `bravery_points ∈ {0, 10000}`, `timed_points ∈ {0,1000,3000,5000,7000}`, plus the phase
   recomputed from `stage_elapsed_ticks` (§6). A farm then breaks the *identity*, not just a sum.
3. The three new score reasons (`stage_bravery`, `stage_timed`) are an **additive widening of the
   v1 name/reason catalog**, legal under wave A's compatibility rule only for *optional payload
   fields*, not for renames/removals — so the schema delta must be written into
   `engineering/contracts/schemas/gameplay-event-v1.schema.json` **after** wave A creates that
   path (it does not exist at base: `ls engineering/contracts` → absent). Wave D must not create
   it independently: two authorities for one contract is the exact failure the P1-11 verifier was
   written to punish.

Minimal-churn alternative if the controller refuses a schema edit: keep one
`score.awarded{reason:"stage_boundary"}` per boundary carrying the total, put the components only
in `bonus.stage_points` payload, and re-derive the bound from that payload (§3.2). Cheaper, one
less enum widening; loses per-component `points_before/points_after` around the `999_999` clamp,
which is precisely what makes a clamp bug invisible. Ruling recommended: components in the payload
**and** one `score.awarded` per component.

## 4. Interface wave D needs from wave A (state it as a requirement, not an assumption)

Because the ledger API is not frozen in wave A's evidence (§1 table, last rows), wave D's
rebase plan must be API-agnostic. The minimum wave A must be able to express, else wave D's
design has no host:

```swift
// shape required, not the spelling
struct StageBoundaryObservation {          // wave D field set
    var completedZone: Int
    var lives: Int
    var points: Int                        // pointsBefore
    var tookExoskeletonInStage: Bool       // wave D
    var stageElapsedTicks: Int             // wave D  (§6)
}
enum StageBoundaryOutcome {                // awarded(award) | suppressed(reason)
    case awarded(StageBoundaryAward)
    case suppressed(SuppressionReason)    // alreadyAwarded | notStageEnd
}
struct StageBoundaryAward {
    var livesBonus: Int; var bravery: Int; var timed: Int; var timedPhase: Int
    var earned: Int                        // sum before clamp
    var livesBefore: Int; var livesAfter: Int   // cap 9
    var refillAmmo: Bool; var clearExoskeleton: Bool
}
// ledger needs: noteExoskeletonActivated(atTick:), noteStageStarted(atTick:),
//               beginPlaythrough(atTick:) / endPlaythrough — wave A already needs the
//               last two for its own once-per-playthrough set.
```

If wave A implemented the ledger as a plain `struct` returning `[Int]` deltas, wave D's change is
"add the two input fields + the three output components", still inside one file. If wave A has no
`beginPlaythrough`, wave D must not invent it — that is wave A's P1-8 semantic and its tests own
it; wave D files the mismatch as a blocking amendment instead of parallel-implementing.

## 5. `bravery` — the norm contradicts itself, so pin a falsifiable reading

`ORIGINAL_MECHANICS.md:142` "If no exoskeleton **was taken**" vs `:118` "**Having** the
exoskeleton forfeits". `toggleExoskeleton()` (`Player.swift:243-246`) can turn the suit **off**
again (`GameScene.swift:234-237` banners both directions), so the two readings differ on a real
reachable state: ON→OFF inside stage 1, then walk out of zone 024.

Ruling (recommended): latch semantics — `tookExoskeletonInStage` is set by the ledger on every
changing-room **activation** (edge), never cleared by a later OFF, and cleared at stage end and at
playthrough boundaries (matches `:115` "persists through deaths until the end of the current
25-zone stage"). Bravery awarded iff `!tookExoskeletonInStage`. Consequences to test:
ON→OFF before 024 ⇒ **no** bravery; death while wearing ⇒ suit restored by respawn and latch kept;
latch never set by the respawn path (`finishDeathAndRespawn`, `:332` region).
Record the `:118` reading as an accepted deviation, one line, in the change package.

The latch lives in the ledger, but the *set* call must be made from the single existing
activation site (`GameScene.swift:235`), not from `hasExoskeleton` polling — polling an off state
loses the toggle-off case, and the audit norm is about the event.

## 6. `timed bonus` made deterministic on Linux — tick, never clock

`ts_us = round(tick*1_000_000/60)` (wave A normative, `architecture.md:63`) means the **tick** is
the only time coordinate an auditor can recompute from the log without the process. Therefore:

```
stageElapsedTicks = tick - stageStartTick          // both ledger-owned, tick injected
phase             = min(4, stageElapsedTicks / phaseTicks)   // 5 phases, frozen ladder
timedPoints[phase] = [7000, 5000, 3000, 1000, 0][phase]      // fastest stage = best
```

Design constraints, each one testable headless:

1. **No wall clock.** The ledger must not read `Date()`, `ProcessInfo.systemUptime`, or
   `SKScene.currentTime`; `tick` arrives as a parameter. The harness calls
   `resolve(completedZone: 24, atTick: stageStart + 0/1800/108_000/…)` and asserts the exact
   phase. Production passes `FixedTickDriver.tick`, so product and harness share one coordinate.
   Because wave A owns the driver *and* the accumulator reset (P1-9), the tick is already proven
   monotonic-per-step across a zone transition — this is a hard ordering dependency, not a
   nicety: without P1-9 the discarded accumulator makes `tick` unaligned with wall time and the
   ladder becomes the very non-determinism wave A's risk table warns about ("RNG nondeterminism
   breaks absolute-tick asserts").
2. **Wave-A predicate style forbids absolute-tick assertions** (`architecture.md` risk row). So the
   ladder is expressed in the auditor as a *relative* recomputation
   `ts_us(award.tick) - ts_us(stageStart.tick)` → phase → compare with the logged
   `timed_points`. Absolute constants like `tick == 64800` appear only in the pure-Swift harness
   (which feeds the ticks itself), never in the stream auditor.
3. **`phaseTicks` is the single tunable and it is not derivable from the norm.**
   `ORIGINAL_MECHANICS.md:143` names the values (0/1000/3000/5000/7000) and the mechanism
   ("cursor … selected phase") but no cadence; the only timing hint in the document, the 700-loop
   zone timer of `:131-137` ("roughly 20–30 seconds"), belongs to a different mechanic (the
   pursuer) and must not be silently reused as a derivation. Propose
   `phaseTicks = 1_800` (30 s at the canonical 60 Hz, one stage ≈ 2.5 min sweep), declared in
   `GameConstants.swift`, pinned by a digest-style test, and flagged `UNCONFIRMED vs original`
   next to the GS-01-style honest comment. The **frozen, testable part** is the ladder's shape:
   exactly 5 phases, values exactly `{0,1000,3000,5000,7000}`, monotonically non-increasing in
   elapsed time, saturating at the last phase. A wrong `phaseTicks` is then a P2 data tuning
   finding; a broken shape is caught by a P1 assertion.
4. **The "cursor" reading is a named spec gap.** `:143` may describe an interactive
   stop-the-cursor bonus (fire to select a phase). That variant needs input state in the ledger
   and a macOS source check; it is explicitly **out of scope** for wave D. The elapsed-time ladder
   is the deterministic subset both readings agree on (a held cursor's phase *is* a function of
   elapsed time), so wave D can land arithmetic now and re-target the constant later without
   moving code. This must be written down, because an unrecorded guess here is exactly how
   "deliberately dormant" (`GameScene.swift:623-625`) happened.
5. `stageStartTick` is set where `isStageStart` is already computed (`GameScene.swift:644`), plus
   `didMove(to:)`/`beginFromTitle`/`restartFromBeginning`. `transition(to:)` is wave A's P1-9 edit
   site — this is the second reason wave D should hold no new copy of that function: two branches
   editing the same 26 lines is a guaranteed conflict with a shared semantic.

## 7. Acceptance structure — three layers of pure-type RED→GREEN

| Layer | Executed on | Test | RED (before fix) | GREEN (after fix) | Contradictory control (must flip) |
| --- | --- | --- | --- | --- | --- |
| L0 characterization | Linux, `swiftc` + existing `coregraphics_shim.swift` harness (precedent: `20260921-…/evidence/piston-anchor-harness/run.sh`, which itself refuses to run on Darwin with `exit 75` and asserts "must not build without shim") | compile **today's** `GameScene.swift:622-631` arithmetic as a local re-implementation and assert `9000 / +1 / refill / suit kept / no bravery / no timed` | n/a (this layer is red by definition *after* the fix) | deleted once L1 lands, kept in the package as the frozen "before" | if L0 still passes after the fix, the fix did not change the product |
| L1 pure ledger | Linux only | `stage_boundary_ledger_check.swift` against the real `StageBoundaryLedger.swift` (Foundation-only ⇒ no shim, no SpriteKit): 5 phases × bravery on/off × lives 1/8/9 × zone 23/24/49/…/125 × second-call-suppression × playthrough reset | every bravery/timed/suit-clear assert fails on the pre-rebase tree (no such fields exist yet ⇒ the RED is authored against wave A's post-rebase ledger with the three components stubbed to `0/false`) | full table matches §1 | revert one component at a time (bravery → 0, `clearExoskeleton → false`, `phaseTicks *= 2`) and each named AC must go red alone; a mutation that leaves all green means the AC measures nothing |
| L2 stream predicate | Linux | `evidence/stage_end_check.py` over a `.synchronous` memory-writer log: per playthrough `count(bonus.stage_points) ≤ 5`, `≤1` per zone, `points == lives×1000 + bravery + timed` identity, `timed == ladder(Δtick)`, `exoskeleton_after == false`, `ammo_reset`, one suppression witness per repeat | FAILS on the pre-P1-10 build (no bravery/timed fields, suit stays) | PASSES | a 600 s zone-124 FIRE farm must stay red on the fixed build for the *right* reason (identity + count), and the same script must go red when the ledger's suppression emit is deleted — never rely on the count alone (`analysis-integration_architect.md:386-388`) |
| L3 macOS observation | real Mac, one run | new probe item `E16`: at zone 024 with suit ON → banner sequence, `SCORE %06d` delta, suit OFF in zone 025, then zone 124 `FULL COMBAT ABILITY` + one award | — | recorded in the handout (§9), not in a Linux verdict | E16's expectation must be generated from the L1 table, so a Mac observation that disagrees is a finding, not a tautology |

Cap caveat that must be in the design, not discovered later: `awardPoints` clamps at `999_999`
and `highScore` follows it (`GameScene.swift:660-666`). With a near-cap score, the *applied* stage
delta < *earned* delta. So `bonus.stage_points` carries `earned_points` **and** the ledger outcome
records `clamped`, and the auditor's identity check must be written as
`sum(score.awarded points) == min(earned, 999_999 - pointsBefore)` per boundary, or the identity
fails on a legitimately correct run. Harness case: start at `points = 995 000`, award a full
26 000 boundary, assert `points_after = 999_999` and `clamped = true`.

## 8. Explicitly out of P1-10 (named, not silently skipped)

- `showTitleAfterContentComplete` (`:761-767`) → title instead of "returns the game to the
  beginning" (`ORIGINAL_MECHANICS.md:148`, flagged at `…/perfile/…:285`). Changing it rewrites the
  playthrough boundary events wave A's predicate B segments on (`state.title_enter` vs
  `state.restart`), so it is a coordinated wave-A/wave-D decision, not a drive-by. File as its own
  finding with the boundary consequence stated.
- `stageExitMarkers` (`TMXLevelRuntime.swift:30, :370`) as an alternative trigger geometry:
  rejected (§10). Wave A ruling 3 froze `x > 510`.
- `blk_stage_end` type-15 vs type-16 marker-code error (`analysis-docs_researcher-fullaudit.md:215`)
  — content-factory/wave-B domain, no ledger dependency.
- Exoskeleton *visual* frames (`PlayerSpriteNode.swift:43-46` "temporary visual cue") — art.

## 9. P1-11 remainder: what Linux can decide, what it never can

**Linux-decidable now, committed in this wave** (extend `release_layer_check.py`, which already
proves block-membership rather than grep counts — the reason it exists):

1. `ENABLE_HARDENED_RUNTIME = YES` present **exactly once in each** of the two target
   `XCBuildConfiguration` bodies (`project.pbxproj:1415-1444` region) and zero times outside them;
   the wave-2e7698 `FORBID-002`/`INV-001` deferral record must flip to a repayment record in the
   same AC that turns green (the verifier already has the "deferral record disappeared" red path —
   reuse it, do not add a second).
2. A real `Exolon/Resources/Exolon.entitlements` exists, is tracked by `git ls-files`, parses via
   `plistlib`, and its key set equals the frozen design set; `CODE_SIGN_ENTITLEMENTS` appears in
   both target blocks with that exact path. 0 such files exist at base (measured).
3. Signing identity is no longer the ad-hoc sentinel: `CODE_SIGN_IDENTITY != "-"` and
   `CODE_SIGN_STYLE` value is a decision (Manual + named identity, or Automatic + `DEVELOPMENT_TEAM`),
   recorded identically in both blocks; plus a rule that no secret material (no `-----BEGIN`, no
   API key literal, no `.p8` path content) is in the tree — `scripts/grok_verify.py --mode pr`
   secret-scan + `bandit.yaml` are the committed instruments for that half.
4. `Info.plist`: `LSMinimumSystemVersion` → `$(MACOSX_DEPLOYMENT_TARGET)` and the remaining
   release-shell keys (`LSApplicationCategoryType`, icon, copyright) resolved as placeholders, with
   the digest-pin of the untouched keys (the AC-001 pattern); zero `$(…)` keys whose setting the
   pbxproj reader cannot find **in a target block** — a placeholder pointing at a setting that only
   exists in the project block is the exact one-sided bug class AC-002 was written for.
5. `macos-probe.sh` static contract: `bash -n` clean; a new section exists for every macOS claim in
   the handout; every new section emits `key=value` only (the parser the Linux verifier will use
   depends on it); the Darwin guard still exits **75** on Linux (a Linux-decidable proof the probe
   cannot self-certify), and a Linux run of the probe must be asserted non-zero by the verifier.
6. Scheme: `ArchiveAction buildConfiguration = Release`, `buildForArchiving = YES`, zero
   `TestableReference`, single `.xcscheme` tree-wide (already AC-003…AC-005; keep as regression,
   do not re-derive).
7. **Handout internal consistency + commit binding** (item 10 below) — decidable on Linux and the
   single highest-value addition of this wave.

**Strictly macOS-clean-machine — a Linux verdict on these is a forbidden outcome:**

| Check | Why Linux cannot decide it |
| --- | --- |
| `codesign -vv --deep --strict <App>` validity/seal/nested content | needs the Apple codesign binary and a built bundle |
| `codesign -d --verbose=4 … flags=0x…(runtime)` | the hardened-runtime *observation*; pbxproj presence ≠ applied flag (the probe comment at `macos-probe.sh:119-123` documents exactly this: `--entitlements` prints a plist where the flag physically cannot appear) |
| `spctl -a -vv` (Gatekeeper) | requires a real Developer ID + notarization + timestamp; ad-hoc `-` identity can never satisfy it |
| `notarytool submit --wait` / `notarytool log <RequestID>` / `stapler validate` | Apple-side service, needs credentials that must not enter the agent environment |
| `security find-identity -v -p codesigning`, keychain/TCC prompts, team resolution | host state, not repo content |
| first-ever `xcodebuild` compile of the product (M-01′) | no Swift-on-Apple toolchain here; note the asymmetry: this *is* partially covered by `swiftc -frontend -parse` in wave A's task 15 (parse ≠ type-check), so the Linux gate must be described as a syntax gate, never as "compiles" |
| `WITH_ARCHIVE=1` real archive + `-exportNotarizedApp` | needs signing + network |
| manual play items E1–E15 and new E16 | one human run, no Linux substitute |

**Handout artifact shape that makes the macOS part auditable later** (extends, not replaces, the
dated `2e7698` `perfile/macos-validation-handout-v2.md` convention — that file stays immutable as
the 2026-09-21 evidence, precedent stated in its own header):

```
evidence/macos-handout/
  MANIFEST.sha256        # sha256 of every file below + the .app and .xcarchive on the Mac
  context.txt            # uname=Darwin, arch, sw_vers, xcodebuild -version, codesign --version
  repo.txt               # git rev-parse HEAD ; git rev-parse HEAD:Exolon (tree oid) ;
                         # git status --porcelain (must be empty) ; base_fingerprint from route.json
  probe.txt              # raw `macos-probe.sh --out` transcript, key=value only
  codesign.txt           # full argv + rc + verbatim stdout/stderr of -vv --deep --strict
                         # and of -d --verbose=4
  spctl.txt  archive.txt  export.txt  notary-submit.txt  notary-log.json  stapler.txt
  play-observations.md   # E1…E16, one line each, EXPECTED generated from the L1 table
  REDACTIONS.md          # what was removed (Team ID, Apple ID, paths) and why
  handout.json           # [{"claim":"M-03-hardened-runtime","artifact":"codesign.txt",
                          #   "sha256":"…","argv":"codesign -d --verbose=4 build/…/Exolon.app",
                          #   "rc":0,"expected":"flags contains (runtime)",
                          #   "observed":"…","verdict":"MATCH"}]
```

Norms for the handout, each of which the Linux verifier can enforce:

- **Verbatim, never summarized.** Every claim points at a byte range/hash of a raw transcript plus
  the exact argv. A claim whose evidence is an operator's prose is not a claim.
- **Recomputable verdict.** `verdict=MATCH` must be re-derivable from the artifact text by a rule
  in the committed verifier (`handout_check.py`), so a future reader does not need a Mac to
  re-check the Mac.
- **Commit-bound.** `repo.txt` HEAD must satisfy `git cat-file -e` and `git merge-base
  --is-ancestor <sha> <current>` on Linux. This is what converts "trust me" into "this run
  measured a tree that really exists in this repository's history".
- **Fresh-or-flagged.** A handout whose HEAD predates the release-layer commits is scored
  `STALE`, never green — this is the P1-11 lesson that `v3_measurements.py`'s old
  "собралось 0.5 ⇒ V1 неверен" line became a success condition after the fix.
- **Absent ≠ green.** With no `macos-handout/`, the verifier prints
  `MACOS_EVIDENCE=ABSENT (unverified)` and exits 1 for the release-profile AC only, leaving every
  other AC reported, so a missing Mac can never be laundered into a pass.
- **Contradictory control.** A synthetic handout that says `plist_CFBundleShortVersionString=0.5`
  while its own `settings_MARKETING_VERSION=0.4` line is present, or whose `MANIFEST.sha256`
  mismatches, **must** turn the check red; if it stays green, the auditor measures nothing.
- **Secrets.** The agent never runs `codesign`/`notarytool`, never reads key material, and the
  handout carries key *labels* only. The notarization `RequestID`/`sha256` are safe to commit and
  are the external anchor Apple's service can later be re-queried with.

## 10. Risks

- **The ledger is not yet an API.** Wave A froze only a file path and a responsibility
  (`architecture.md:37`, `tasks.md:17-19`); the string "Ledger" appears in neither of its two
  analysis documents (measured in §1's table). Wave D's design therefore depends on a shape it
  cannot see, so the rebase can fail in exactly one place — `StageBoundaryObservation`/
  `StageBoundaryAward` field ownership. Mitigation: §4's requirement list becomes a written
  amendment to wave A's package *before* wave A implements task 5, and wave D's P1-10 code is
  authored as a diff to that file, never as a parallel type.
- **Wave A's committed predicate B turns red on wave D's correct build** (§3) unless the bound is
  amended by its owner. Mitigation: component-form identity check + wave D's own
  `stage_end_check.py`, with `gameplay_log_check.py` untouched by this branch.
- **A `phaseTicks` that no source confirms** becomes a silent invented norm — the same failure mode
  as the "deliberately dormant" comment at `GameScene.swift:623-625`. Mitigation: the tunable is
  one named constant in `GameConstants.swift`, the *shape* (5 phases, exact value set, monotone)
  is what P1-asserts, the constant is marked `UNCONFIRMED vs original`, and probe `E16`/the
  original-hardware walkthrough is the repayment path; the alternative "leave P1-10 half-done" is
  the finding we are closing, not an option.

## 11. Rejected alternatives

- **Re-implement a stage-end sequence in `GameScene` (or add `StageBoundaryLedger+P1_10.swift`) and
  let the two ledgers coexist.** Rejected: it recreates the GS-01 defect class by construction — two
  owners of "has this boundary already paid", one of which has no playthrough reset — and it drags a
  new `project.pbxproj` 4-edit registration conflict into the rebase for a type that has no reason
  to be separate.
- **Wall-clock or `SKAction`/`currentTime` timing for the timed bonus** (e.g. `Date()` at stage start,
  or an SKAction cursor advancing the phase). Rejected: `ts_us` is *derived* from the tick, not
  measured, so a wall-clock input is unrecomputable from the log, unreproducible under the `.synchronous`
  harness, and non-deterministic across the P1-9 accumulator reset — it also breaks wave A's own
  predicate style, which forbids absolute-time assertions for the 16 unseeded nondeterminism sites.
- **Close P1-11 by writing the macOS-only checks into the Linux verifier with "assumed PASS"
  (or by committing a hand-made `macos-handout/` without a Mac).** Rejected: that is a fabricated
  attestation on the publication path — the repo contract already says prompt files, hooks, and
  local receipts are never merge authority, and a synthetic handout would pass every static rule
  while proving nothing about signature, notarization or Gatekeeper. The honest version is §9's
  `MACOS_EVIDENCE=ABSENT (unverified)` + rc=1, which keeps the Linux half green and the Mac half
  visibly open.
