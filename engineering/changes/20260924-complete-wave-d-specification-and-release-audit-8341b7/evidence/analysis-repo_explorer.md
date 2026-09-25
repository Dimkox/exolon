# analysis-repo_explorer — wave-D (P1-10 stage-end bonuses / P1-11 release layer)
Tree: /home/pall/projects/.exolon-wave-d/exolon @ 295690b, branch codex/wave-d-spec-release-20260924
(Persisted by the controller verbatim from the read-only agent's report; the agent had no write tool.)

## 1. Current stage-end path

### Spec (the clause wave-D must satisfy)
ORIGINAL_MECHANICS.md:138-146
```
## Stage ends: Zones 024, 049, 074, 099, 124
- Reaching the stage-end trigger opens the bonus sequence.
- Award 1000 points per remaining life.
- If no exoskeleton was taken, award 10,000 bravery points.
- Timed bonus cursor can add 0/1000/3000/5000/7000 points depending on the selected phase.
- Add one life, capped at 9.
- Clear exoskeleton.
- Restore ammo=99 and grenades=10.
```
plus ORIGINAL_MECHANICS.md:117 — "At stage end the exoskeleton flag is cleared."

### Implementation today
Exolon/GameCore/GameScene.swift:609-631 (verbatim):
```swift
    private func checkScreenExit() {
        guard player.position.x > 510 else { return }
        let next = currentLevel.nextLevelName
        applyOriginalStageBoundaryIfNeeded(completedZone: gameState.zone)

        guard !next.isEmpty, includedLevels.contains(next) else {
            enterContentComplete(nextLevelName: next)
            return
        }

        transition(to: next)
    }

    private func applyOriginalStageBoundaryIfNeeded(completedZone: Int) {
        // Original Exolon awards the lives bonus at the five 25-zone stage ends.
        // Our current content is still being extended through Step 9, so this is deliberately dormant
        // until later steps add Zones 024/049/074/099/124.
        guard [24, 49, 74, 99, 124].contains(completedZone) else { return }
        awardPoints(gameState.lives * 1_000)
        if gameState.lives < GameState.startingLives { gameState.lives += 1 }
        gameState.ammo = GameState.startingAmmo
        gameState.grenades = GameState.startingGrenades
    }
```

Clause-by-clause verdict:

| Spec clause | Status | Evidence |
|---|---|---|
| lives × 1000 | PRESENT | GameScene.swift:627 |
| bravery 10 000 if no exoskeleton | MISSING | grep -rniE "bravery|10_000|10000" --include=*.swift Exolon → 0 hits |
| timed bonus 0/1000/3000/5000/7000 | MISSING | grep -rniE "timed|cursor" → 0 hits; no per-zone elapsed state exists (GameState.swift:85-90 fields are only ammo, grenades, points, lives, highScore, zone) |
| +1 life, capped at 9 | PARTIAL | GameScene.swift:628 — cap borrowed from startingLives; no max-lives constant anywhere; order lives×1000 then +1 matches "per remaining life" |
| clear exoskeleton | MISSING at the boundary | only setExoskeleton(false) in the product is GameScene.swift:963 inside restartFromBeginning(:950); API exists: Player.swift:248-250, :243-246, private(set) var hasExoskeleton Player.swift:26 |
| refill ammo 99 / grenades 10 | PRESENT | GameScene.swift:629-630 |
| "stage-end trigger opens the bonus sequence" | MISSING (whole sequence) | boundary inferred from player.position.x > 510 (:610), not from the stage_end marker. stageExitMarkers parsed (TMXLevelRuntime.swift:30, :369-371) and consumed nowhere — dead data. enterContentComplete (:738-760) is the only terminal overlay |

### The "deliberately dormant" comment is false — changes finding severity
Content already covers all 125 zones, so every boundary is live:
- GameScene.swift:53 includedLevels = L01S01…L05S25 (125 names).
- GameScene.swift:988-997 zoneNumber(for:) is 0-based: max(0, min(124, (stage-1)*25 + (screen-1))).
- L01S25.tmx → nextLevel=L02S01 (in includedLevels); L02S25 → L03S01; L01S24 → L01S25. Only L05S25 has NO nextLevel property.
- stage_end marker present in all five of L01S25/L02S25/L03S25/L04S25/L05S25 (1 occurrence each).
⇒ zones 24/49/74/99 award the bonus AND transition; zone 124 awards the bonus AND then falls into enterContentComplete. The comment at :623-625 claims the opposite.

### Pre-existing ordering defect the new code must not inherit
:612 call sits BEFORE the :614 guard, so at zone 124 the award is not rolled back when no transition happens; combined with beginFromTitle (:708) which resets neither points nor zone — the documented farm (GS-01/ECO-02) in engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/perfile/gamescene.md:61 and .../perfile/economy-score.md:248,306, probe item E10 in engineering/runbooks/macos-probe.sh.

### Where caps live
- GameState.swift:81-83 — startingAmmo=99, startingGrenades=10, startingLives=9 (only cap constants).
- Consumers: GameState.swift:85-88 (init), :94-97 (resetForNewGame), GameScene.swift:330-331 (death refill), :629-630 (stage boundary), :628 (life cap).
- Lives lower bound: GameScene.swift:322 max(0, lives-1), gameOver at :323.
- Points ceiling is a magic literal, not a constant: GameScene.swift:662 gameState.points = min(999_999, points + value) inside awardPoints (:660).
- updatePickups duplicates numbers as literals (:526 grenades=10, :533 ammo=99) — matches ORIGINAL_MECHANICS.md:107-108 "sets exactly 99/10" but unshared.
- GameConstants.swift (34 lines) contains NO lives/ammo/grenade/points constant — only sizes/timers.
- Persistence cannot carry ledger/timer/exoskeleton: GameCheckpoint (GameState.swift:13-19) = {levelName, ammo, grenades, points, lives}; keys Exolon.Step10.* (:23-30).

## 2. Release-layer assets that exist

### release_layer_check.py (engineering/changes/20260921-...2e7698/evidence/, 1002 lines)
- Contract (docstring): rc=0 ⇔ релизный слой совпал с EXPECTED (после закрытия P1-11) И каждый контроль перевернулся; pre-fix tree must rc=1. Mutations/synthetics in-memory only; never writes product files; git read-only (git() :525).
- Entry points: main() :727; flags --root <path>, --json; root auto-discovery walks up for Exolon.xcodeproj+.git. Final gate ok = not mism and all(controls.values()); verdict RESULT: RELEASE_LAYER_READY; release.md Go criterion rc=0, 0 красных AC, 29/29 контролей OK.
- Addresses :60-75: PBXPROJ, INFO_PLIST, SCHEME_REL, RUNBOOK engineering/runbooks/macos-probe.sh, V3_TOOL, CHANGE_DIR, PLAN_FILES (evidence/ and brief.md excluded as self-citation), TARGET_GUID, four XCBuildConfiguration GUIDs.
- Parsers by format: plistlib, xml.etree.ElementTree, hand-written tab-depth OpenStep-ASCII reader read_pbxproj :215 recording which XCBuildConfiguration block owns each key (block-binding, not grep -c).
- EXPECTED = 44 keys in 4 groups: (A) plist version substitution/literal/nonversion digest pin 8801d6fb…210f; (B) pbxproj MARKETING/CURRENT placement + hardened_runtime_key_count: 0 # DELIBERATELY DEFERRED + symmetry + deferral record; (C) scheme actions/archiving/refs/configs + user_scheme_count 0; (D) evidence hygiene reports append-only pins, cutover ownership, runbook stale-claim zero.
- Detectors: detect_plist :171, detect_pbxproj :314, classify_scheme :385, want_container :395, detect_scheme :404, detect_cutover :470, detect_runbook :493, detect_reports :516, gather_reports :533, load_inputs :552, measure :587.
- 29 named controls (plist_rejects_truncated, substitution_probe_flips_on_literal, untouched_guard_flips_on_unrelated_edit, reader_balance_detects_unclosed, reader_target_cfg_list_derived, marketing_moves_between_blocks, marketing_delete_flips_count, marketing_value_is_typed, hardened_key_mutation_detected, deferral_record_ignores_brief_echo, user_scheme_not_shared, synthetic_scheme_can_be_green, bogus_blueprint_flips, missing_canon_attr_flips, wrong_container_flips, container_prefix_casing_rejected, archiving_no_flips, archive_config_flips, launch_config_flips, dangling_test_flips, scheme_garbage_rejected, container_pin_is_literal_not_derived, absent_scheme_is_red, cutover_needs_record, cutover_pin_is_ast_not_grep, runbook_stale_flips, append_only_wrong_pin_flips, append_only_worktree_edit_flips, undo_fix_is_red :947).
- In-memory undo synthetics: GOOD_SCHEME/good_scheme() :700, undo_plist :705, undo_scheme :714, undo_runbook :718, undo_records :722.

### Scheme Archive action
Exolon.xcscheme:87-90: ArchiveAction buildConfiguration="Release" revealArchiveInOrganizer="YES" only — no pre/post actions, no ExecutionAction; notarytool cannot hook from scheme.

### Version identity
Info.plist 11 keys; CFBundleShortVersionString=$(MARKETING_VERSION), CFBundleVersion=$(CURRENT_PROJECT_VERSION). pbxproj:1415-1425 (Debug) and :1434-1444 (Release) byte-identical settings: CODE_SIGN_IDENTITY="-", CODE_SIGN_STYLE=Manual, CURRENT_PROJECT_VERSION=1, DEVELOPMENT_TEAM="", INFOPLIST_FILE, MARKETING_VERSION=0.5, PRODUCT_BUNDLE_IDENTIFIER=com.exolon.remake. No CODE_SIGN_ENTITLEMENTS, no ENABLE_HARDENED_RUNTIME.

### engineering/runbooks/macos-probe.sh
- Guards: non-Darwin exit 75; missing project exit 66; --out exit 73. Flags --out/--target/--config (Debug default), WITH_ARCHIVE=1.
- A scheme discovery with real discriminators (shared_scheme_file_present, shared_scheme_tracked via git ls-files, verdict_shared_scheme).
- B/C build + bundle truth: xcodebuild target build; plutil version extraction vs -showBuildSettings (version_single_source=MATCH|MISMATCH); plist_unexpanded_placeholders; bundle_resources_tmx EXPECTED 125; bundle_has_gif 0; generated_terrain 1; codesign -dv; spctl -a -vv; codesign_flags; hardened_runtime=PRESENT|ABSENT.
- B2: -showdestinations; WITH_ARCHIVE=1 only → archive to ARCHIVE_PATH → archive_rc; else SKIPPED.
- D defaults read com.exolon.remake; E 15 tty manual observations (E10 zone-124 farm; E3/E4 exoskeleton; E11 CONTINUE); G capture practice (product_log_calls=0, level_warp_calls=0 ⇒ ~11 min real walk to zone 124).
- Where it stops (section F, its own words): not an XCTest substitute (0 tests in product); manual E1-E15 single-run observations; Debug build ≠ release (ad-hoc/Manual signing); ENABLE_HARDENED_RUNTIME DELIBERATELY DEFERRED outside the change.
- Structurally: signature observed on build/Debug/Exolon.app, never on the archived product; .xcarchive contents never inspected; no verdict_signature=/verdict_notarization= keys and no rc contract for them; spctl without quarantine xattr cannot represent a downloaded artifact.
- .../2e7698/release.md §Deployment/§Deferred boundary (verbatim): "релизный слой дерева становится пригодным для публикации, самого артефакта (.xcarchive, notarization, Release на GitHub) этот change не создаёт"; "3. Только после зелёного M-01′ — отдельный change на клаузу «подпись»". Gatekeeper reasoning: при ad-hoc CODE_SIGN_IDENTITY="-"/Manual/пустом DEVELOPMENT_TEAM флаг не меняет исход Gatekeeper и недоступность нотаризации. Dated handout evidence/perfile/macos-validation-handout-v2.md:44-53 (M-03′) deliberately tolerates nonzero archive_rc BECAUSE OF SIGNING — that expectation must invert for a release-green run.

### VERSION / README release wiring
- git ls-files: no VERSION, no CHANGELOG.md, no Makefile, no .xcconfig, no *.entitlements, no .icns/assets, no packaging script — yet .grok-stack/config/policy.json:13,:56 list VERSION as identity carrier and AGENTS.md requires README to state current VERSION.
- README.md title "Exolon — Step 9 Rebase (test archive)"; grep version|0.5|archive|release → zero release wiring. Version 0.5 exists only in pbxproj. Live identity drift in runbook E1: stepLabel "STEP 9 · …" (GameScene.swift:650) vs Exolon.Step10.* keys (GameState.swift:23-30).

### Absent today for clean-machine signing/notarization E2E
1. Developer ID identity/settings: CODE_SIGN_IDENTITY "-", Manual, DEVELOPMENT_TEAM "" — needs host key + separate approval, not fixable by editing tracked files.
2. *.entitlements + CODE_SIGN_ENTITLEMENTS — both absent.
3. ENABLE_HARDENED_RUNTIME=YES in both target configs — deferred; release_layer_check.py has guards to accept it (hardened_runtime_key_count, hardened_symmetric, hardened_key_mutation_detected, deferral_record_ignores_brief_echo) but plan text must change or hardened_deferral_recorded goes red.
4. Mandatory (non-WITH_ARCHIVE) Distribution archive + archive CONTENT inspection (Products/Applications/Exolon.app present, plutil on archived Info.plist, codesign --verify --deep --strict --verbose=4 on the archived binary, not Debug build).
5. Notary submission: xcrun notarytool submit <zip> --keychain-profile … --wait (+ notarytool log on failure). Tree-wide grep notarytool|stapler|altool → only two prose mentions in P1-11 evidence; no implementation.
6. Stapling + verification: xcrun stapler staple/validate; spctl -a -t execute -vv against a quarantine-xattr copy from a real distribution artifact (ditto -c -k --keepParent / hdiutil create); nothing produces an artifact or hash manifest.
7. Machine-readable verdict vocabulary + rc contract for (4)-(6) so a Linux verifier can consume the run (today free text + EXPECTED comments; only verdict_shared_scheme/verdict_toolchain are keys).
8. Linux-decidable counterpart: EXPECTED has no entitlements_present/notary_*/staple_*/archive_step_mandatory/distribution_artifact keys — wave-D must add keys AND flipping controls, else the release claim is unfalsifiable off-macOS.
9. A dated signing handout (only macos-validation-handout-v2.md exists; its M-03′ expectation is the opposite of a green release).
10. VERSION carrier + README release section to satisfy AGENTS.md "README before push".

## 3. Existing Python verifiers wave-D should extend, not duplicate
- engineering/changes/20260919-...7db1f3/evidence/linux_static_audit.py — level/zone-structure reader: expected_levels() :220-226 (model matching GameScene.swift:988-997), map_properties() :201 (nextLevel), iter_objects :154, source_marker_runtime :174, object_runtime :186, collision_solid_count :136, parse_compiler_audit :105, sha256_file :97, pbx_paths :228, "stage_end" tables :51,:77, expected_zone_png :425, tmx_expected 125 :445. Extend to assert the five stage boundaries exist and chain.
- .../evidence/v3_measurements.py — the EXPECTED/got/controls/RESULT/sys.exit template release_layer_check.py copied; HANDLED tuple :89; docstring forbids regex on TMX objects (regex gives 97 markers instead of 127). Its shared_xcschemes pin is an intentional cutover-red after P1-11 — do not "fix".
- .../evidence/fullaudit_measurements.py — geometry math only (world_root, collision_gids, solid_rects, subtract, measure_cabin, measure_beams, measure_b01).
- .../2e7698/evidence/p1-1_piston_probe.py — single-property numeric probe pattern.
- .../7db1f3/evidence/harness/ (run.sh, main.swift, coregraphics_shim.swift, gen_fixtures.py) — only executable-Swift-on-Linux contour (TMXMapLoader over 125 maps + 17 malformed fixtures, REAL MAPS ok=125/125); README: not a project typecheck; Player/GameScene (SpriteKit) excluded — stage-end arithmetic cannot execute there.
- scripts/*.py are stack tooling only; no product math.
- NO committed stage-end bonus verifier exists (the cited replica was /tmp/lane-score/{inventory.py,zones.py,econ.swift}, never committed). Wave-D bonus verifier is genuinely new: recommend engineering/changes/<waveD>/evidence/stage_boundary_check.py on linux_static_audit.py readers + release_layer_check.py control/undo discipline.

## Unresolved
1. StageBoundaryLedger does not exist yet (wave-A unmerged; all branches at base 295690b). Wave-D cannot integrate against it, only design in parallel.
2. "Timed bonus" is undefined against the tree: ORIGINAL_MECHANICS.md:143 cursor/phase and :131 "700-loop threshold"; no zone timer, no phase state, no 50 Hz tick; only LevelObstacles.swift:395-410 projectile delay and postDeathProtectionDuration. Which clock drives 0/1000/3000/5000/7000 and its reset scope is a named design decision.
3. checkScreenExit ordering vs P1-8 guard-move collide: same decision as consuming stageExitMarkers — one owner needed (wave A holds transition()/guard code).
4. Cap placement: GameConstants has no score/life constants; 999_999 bare literal :662; no max-lives constant; bravery 10 000 against ceiling + farm makes placement a spec question.
5. Bravery bonus needs a durable "exoskeleton taken this stage" latch; hasExoskeleton is Player-only (Player.swift:26), not in GameState/GameCheckpoint; reset point (stage start vs zone 124) changes semantics.
6. Signing cannot be proven on this host (probe exit 75; no codesign/notarytool) — steps 1-6 need a delegated macOS session + Developer ID/Apple-team credentials outside the PR trust domain. Linux-decidable vs external-handout split is an owner-gate decision.
7. archive_rc expectation currently tolerates signing failure (handout :50-53); inverting it is a dated-claim change; runbook_stale_gap_claims markers don't cover "signing-expected-to-fail" yet — extend markers first.
8. README/VERSION vs AGENTS.md: introducing VERSION is a protected-path decision needing named targets.
9. Zone-124 verification cost: level_warp_calls=0 and loadCheckpoint never called ⇒ ~11 min real walk per macOS confirmation attempt unless a bounded debug warp is granted.
