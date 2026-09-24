# Analysis — repo_explorer (route 32f59cc7dcb6)

- Branch: `codex/wave-a-gameplay-log-tick-fixes-20260924` @ HEAD `295690b` (2026-09-24)
- Scope: exact current-code locations for the wave-A findings P1-9 / P1-4 / P1-6 / P1-8, log-emit call sites, logging facility, Swift test-harness options.
- Method: direct read of `Exolon/**/*.swift` on this branch. All line numbers verified with `grep -n`/`awk` on this checkout.

---

## 1. Fixed-tick game loop (P1-9)

**Frame time enters** in `Exolon/GameCore/GameScene.swift:123-142` (`update(_:)`), driven by SpriteKit:

```
129	        let frameTime = min(currentTime - previousUpdateTime, GameConstants.maximumFrameTime)
130	        previousUpdateTime = currentTime
131	        accumulator += frameTime
132
133	        while accumulator >= GameConstants.fixedTimeStep {
134	            fixedUpdate(dt: GameConstants.fixedTimeStep)
135	            accumulator -= GameConstants.fixedTimeStep
136	        }
```

- Accumulator declared: `GameScene.swift:50-51` — `private var previousUpdateTime: TimeInterval = 0` / `private var accumulator: TimeInterval = 0`. First-frame guard at `:123-127` (`if previousUpdateTime == 0 { ... return }`).
- Constants: `Exolon/GameCore/GameConstants.swift:6-7` — `fixedTimeStep = 1.0/60.0`, `maximumFrameTime = 0.25`.
- The fixed step body is `GameScene.swift:148` (`fixedUpdate(dt:)`), called only from the while loop at `:134`.

**Zone/level transition path**: `fixedUpdate` tail `GameScene.swift:308` `if !player.isDying { checkScreenExit() }` → `checkScreenExit` `:609-620` → `transition(to:)` `:633-658`. `transition` resets (full body quoted in §4 excerpt below) `invulnerability`, `flowState`, `deathGroundTimer`, `sceneJumpWasPressed`, `fireWasPressed`, `grenadeWasPressed`, banner/step labels, `saveCheckpoint()` — **but never touches `accumulator` or `previousUpdateTime`**.

Verified tree-wide: `grep -n "accumulator\|previousUpdateTime" GameScene.swift` yields only lines 50, 51, 124, 125, 129, 130, 131, 133, 135. No reset in `transition`, `didMove`, `restartFromBeginning`, `beginFromTitle`, or anywhere else.

**P1-9 conclusion: claim CONFIRMED.** Because `transition(to:)` is invoked from inside `fixedUpdate`, which is inside the `while accumulator >= fixedTimeStep` loop (`:133-136`), leftover accumulated time (up to 0.25 s ≈ 15 fixed steps) keeps stepping the *newly created* zone in the same `update()` call. Additionally, `restartFromBeginning` (`:950-986`) also rebuilds the level without draining the accumulator.

## 2. Teleport handling and the UP/jump latch (P1-4)

**Teleport / changing-room interaction** is UP-gated contextual code in `fixedUpdate`, `GameScene.swift:229-252`:

```
229	        let jumpJustPressed = rawInput.jump && !sceneJumpWasPressed
230	        sceneJumpWasPressed = rawInput.jump
231	        var consumedUpInteraction = false
232
233	        if jumpJustPressed, !player.isDying {
234	            if currentLevel.changingRooms.contains(where: { $0.intersects(player.movementHitbox) }) {
235	                player.toggleExoskeleton()
...
239	            } else if let destination = currentLevel.teleportDestination(for: player.movementHitbox) {
240	                let departure = player.position
241	                player.teleport(to: destination)
242	                createTeleportFlash(at: departure)
243	                createTeleportFlash(at: destination)
244	                consumedUpInteraction = true
245	            }
246	        }
...
251	        if consumedUpInteraction {
252	            player.consumeContextualJumpPress()
253	        }
```

- Scene edge latch `sceneJumpWasPressed`: declared `GameScene.swift:35`; consumed/set per-tick `:229-230`; cleared on zone transition `:652`; seeded from held input at `beginFromTitle` `:715`, `leavePause` `:938`, `restartFromBeginning` `:982`. Teleport itself does NOT write `sceneJumpWasPressed` (already true from `:230`).
- Masked snapshot: `GameScene.swift:255-266` rebuilds `InputSnapshot(... jump: false ...)` only for the consuming tick; `player.update` is then called at `:269`.
- Player-side latch: declared `Player.swift:34` (`private var jumpWasPressed`); **consumed** in `Player.update` `Player.swift:110-115`:

```
110	        let jumpJustPressed = input.jump && !jumpWasPressed
111	        if jumpJustPressed && isGrounded && !isCrouching {
112	            velocity.dy = jumpVelocity
113	            isGrounded = false
114	        }
115	        jumpWasPressed = input.jump
```

- `Player.teleport(to:)` `Player.swift:207-214` sets `jumpWasPressed = true` at `:213`; `consumeContextualJumpPress()` `Player.swift:256-258` also sets `jumpWasPressed = true`. `respawn()` `:232-241` and `beginDeath()` `:218-225` reset it to `false` (`:239`, `:224`).
- Portal geometry: `TMXLevelRuntime.swift:226-233` (`teleportDestination`), `changingRooms` populated at `TMXLevelRuntime.swift:288-305` ("capsule") and `:378-386` (source marker `changing_room`).

**P1-4 mechanism CONFIRMED — the suppression is exactly one fixed tick.** Order inside the consuming tick: `consumeContextualJumpPress()` (`GameScene.swift:252`) and `teleport` (`Player.swift:213`) set `Player.jumpWasPressed = true`, but `player.update(input: jump:false)` (`:269` → `Player.swift:80`) then unconditionally rewrites `jumpWasPressed = input.jump` = **false** at `Player.swift:115` in the *same* call. Next fixed tick, with UP still physically held: scene edge `jumpJustPressed` is false (`:229`, latch true) so the teleport/changing-room branch is skipped and `playerInput = rawInput` (jump:true, `:255-266` else-arm); inside `Player.update`, `input.jump(true) && !jumpWasPressed(false)` → `jumpJustPressed = true` → **the jump fires** if grounded. A held UP therefore survives any teleport/changing-room and produces a jump one fixed tick later. (Same tick is correctly suppressed; only the next tick leaks.) If UP was held and the player also crossed x>510 into a new zone, `:652` + `respawn()` clear both latches and the spurious jump can fire in the new zone within the same frame, compounded by §1's undrained accumulator.

## 3. Double launcher bonus pickup (P1-6)

- Collect call: `GameScene.swift:299-303`:

```
299	        let launcherBonus = currentLevel.collectDoubleLauncherBonus(playerBox: player.movementHitbox)
300	        if launcherBonus > 0 {
301	            awardPoints(launcherBonus)
302	            showBanner("+1000")
303	        }
```

- `TMXLevelRuntime.swift:219-224`:

```
219	    func collectDoubleLauncherBonus(playerBox: CGRect) -> Int {
220	        for launcher in doubleLaunchers where launcher.collectBonusIfTouched(playerBox: playerBox) {
221	            return 1_000
222	        }
223	        return 0
224	    }
```

- Handler `DoubleLauncherObstacle.collectBonusIfTouched`, `Exolon/GameCore/Objects/LevelObstacles.swift:717-722`:

```
717	    func collectBonusIfTouched(playerBox: CGRect) -> Bool {
718	        guard isActive, playerBox.intersects(hitbox) else { return false }
719	        isActive = false
720	        node.alpha = 0.45
721	        return true
722	    }
```

- `isActive` gates firing: `LevelObstacles.swift:686` (`private(set) var isActive = true`) and `:697` `guard isActive, !player.isDying else { return nil }`; shot production loop `TMXLevelRuntime.swift:141-144`.
- **Restoration sites: there are none.** `isActive` has no reset/re-arm API (unlike e.g. nothing else in the file), and no code writes `isActive = true` after init. The launcher is only ever "restored" implicitly when a fresh `TMXLevelRuntime` is constructed: `GameScene.swift:61` (didMove), `:639` (transition), `:954-955` (restartFromBeginning). Death/respawn (`GameScene.swift:332`, `Player.swift:227-241`) does NOT rebuild the level, so within the same zone visit the launcher is dead for good.
- Related player "double shot" state (exoskeleton): `Player.swift:26` `hasExoskeleton`, `:243-246` `toggleExoskeleton()` (changing-room only), `:248-250` `setExoskeleton(_:)`, cleared only at `GameScene.swift:963` (`restartFromBeginning`). It is NOT cleared by death/respawn/transition.
- Spec baseline: `ORIGINAL_MECHANICS.md:43-48` — "Crossing the launcher's invisible bonus region awards 1000 points once." The spec asks only for the bonus to be once-per-region; the implementation also permanently silences the launcher (firing + visual) as the collect side effect.

**P1-6 conclusion: CONFIRMED as coded** — collecting the bonus disables that launcher's double-shot production for the remainder of the zone instance with no restore path.

## 4. Stage-end bonus and final-zone/title flow (P1-8)

Award site `GameScene.swift:622-631`:

```
622	    private func applyOriginalStageBoundaryIfNeeded(completedZone: Int) {
...
626	        guard [24, 49, 74, 99, 124].contains(completedZone) else { return }
627	        awardPoints(gameState.lives * 1_000)
628	        if gameState.lives < GameState.startingLives { gameState.lives += 1 }
629	        gameState.ammo = GameState.startingAmmo
630	        gameState.grenades = GameState.startingGrenades
631	    }
```

Trigger `GameScene.swift:609-620` (`checkScreenExit`, called every fixed tick from `:308`): `guard player.position.x > 510` → award → `guard !next.isEmpty, includedLevels.contains(next) else { enterContentComplete(nextLevelName: next); return }` → `transition(to: next)`.

There is **no awarded/idempotency flag anywhere**: `grep -rn "awarded|hasAwarded|bonusAwarded|stageBonus" Exolon/` → zero hits.

**Re-trigger loop on zone 124, exact path:** `Exolon/Resources/L05S25.tmx` has **no `nextLevel` property** (verified; contrast `L01S25.tmx` → `value="L02S01"`), so `nextLevelName = ""` (`TMXLevelRuntime.swift:98`). On first arrival at x>510: award at `:612` → `enterContentComplete("")` `:738-759` sets `flowState = .contentComplete`, `saveCheckpoint()` (persists inflated points, `:740`), and shows "FULL COMBAT ABILITY" (`:743` `if gameState.zone >= 124 && nextLevelName.isEmpty`). Then:

1. FIRE → `fixedUpdate :203-207` → `showTitleAfterContentComplete` `:761-767` → `flowState = .title`. Player position, zone and level object are untouched.
2. FIRE → `fixedUpdate :161-167` → `beginFromTitle` `:708-717` → `flowState = .playing`; it only hides the overlay, seeds `*WasPressed` latches and (because `hasSavedCheckpoint` is true) does NOT reset state or move the player.
3. Next `fixedUpdate` → `:308` `checkScreenExit()` → x is still > 510 → `applyOriginalStageBoundaryIfNeeded(completedZone: 124)` awards `lives*1000` **again** (+1 life per cycle until 9, `:628`), then `enterContentComplete` re-saves the checkpoint. Repeat every FIRE/FIRE cycle → unbounded score farm up to the 999 999 cap in `awardPoints` `:660-664`, and it also drags `highScore` up via `:663-665` + `persistence.saveHighScore`.

Secondary repeatable path (weaker, zones 24/49/74/99): none — for those, the next tick calls `transition(to:)` (`:619`) which moves/reloads and the player spawns back at the map spawn x, so x>510 is not immediately true again. The bug is specific to the terminal zone where no transition happens and the player is parked past the exit threshold.

Other `enterContentComplete` callers: only `:615` (nextLevel empty or outside `includedLevels` `GameScene.swift:53`); `enterGameOver` `:719-736` is only reachable via `updateDeathSequence` `:324`.

## 5. Candidate log-emit call sites (function enumeration)

All in `Exolon/GameCore/GameScene.swift` unless noted. Player actions:

- **shoot (blaster)** — `updateWeapons` `:338-352` (edge `:340`, bullet spawn `:342-345`, exoskeleton second barrel `:346-350`, ammo decrement `:351`)
- **shoot (grenade)** — `updateWeapons` `:354-361`
- **jump** — `Player.update` `Player/Player.swift:110-114` (only site where `velocity.dy = jumpVelocity`; scene cannot see the result — emit needs Player hook or scene post-check of `motionState == .jumping`)
- **collect grenade/ammo** — `updatePickups` `:522-536` (grenade pack `:524-527`, ammo pack `:529-532`)
- **collect double-launcher bonus** — `fixedUpdate` `:299-303`
- **exoskeleton toggle (changing room)** — `fixedUpdate` `:234-238`
- **teleport** — `fixedUpdate` `:239-244` (+ visual `createTeleportFlash` `:1024`)
- **player hit → begin death** — `hitPlayer` `:601-607` (single choke: all damage funnels here; callers `updateEnemyBullets:512`, `updateLethalEntities:541,550,563,570,576,585,595`)
- **death resolved / life lost / respawn** — `updateDeathSequence` `:311-336` (lives decrement `:322`, game-over branch `:324`, respawn `:332-336`)
- **enemy/object destroyed + score**: `updateBullets` `:366-425` (shoot-down `:371-380`, bubble `:382-388`, egg `:390-396`, force field `:398-405`), `updateGrenades` `:427-479`, `destroyWithGrenade` `:481-488`, `destroyMissileGuidanceIfHit` (`Levels/TMXLevelRuntime.swift:191-206` via `:460-467`), lethal-contact kills `:579-597`
Game events:

- **score change** — `awardPoints` `:660-667` (single choke point for ALL points, incl. high-score write `:663-665`; callers `:301,379,386,394,403,465,486,583,593,627`)
- **stage bonus awarded** — `applyOriginalStageBoundaryIfNeeded` `:622-631`
- **zone load (initial)** — `didMove(to:)` `:55-66` (`currentLevel = TMXLevelRuntime(resource:)` `:61`)
- **zone transition** — `transition(to:)` `:633-658`
- **game over** — `enterGameOver` `:719-736` (also `persistence.clearCheckpoint()` `:722`)
- **content complete** — `enterContentComplete` `:738-759`
- **title start / restart / title-return** — `beginFromTitle` `:708-717`, `restartFromBeginning` `:950-986`, `showTitleAfterContentComplete` `:761-767`
- **pause enter/leave** — `enterPause` `:917-928`, `leavePause` `:930-942` (edge consumed at `:153-159` via `InputState.consumePausePress`, `InputState.swift:71-76`)
- **checkpoint save/load** — `saveCheckpoint` `:696-706`, `loadPersistentState` `:685-694`
- **input edges (optional source of action logs)** — `InputState.set` `InputState.swift:41-53` (platform callers `Platform/macOS/GameView.swift:51-67`, `Platform/macOS/GamepadInput.swift:50-90`)

## 6. Existing logging facility in GameCore — NONE

`grep -n "print(|os_log|Logger|NSLog|FileHandle"` over `Exolon/**/*.swift` → **0 matches**. The only observability today is on-screen: `showBanner` `GameScene.swift:669-683`, `updateDebugText` `:1062-1073`, `updateDebugOverlay` `:1075+` (hitbox drawing), `stepLabel`/`gamepadLabel` text. A new log facility must be introduced; there is nothing to reuse or route through.

## 7. Test targets / how a GameScene-logic regression test can run here

- **No Swift test target exists**: `Exolon.xcodeproj/project.pbxproj` contains 0 matches for `XCTest|Test`; no `.xcscheme`, no `ExolonTests/`. Audit backlog agrees (`engineering/reports/exolon-full-audit-20260920.md:92,98` "XCTest у игры: 0 файлов", T3).
- **Host is Linux** with Swift 6.4 (`swiftc --version` → `Swift version 6.4 (swift-6.4-RELEASE)`, x86_64-unknown-linux-gnu). `scripts/grok_verify.py` has no Swift gate at all (no "swift" hits).
- **Established harness pattern** (the repo's only executable Swift evidence loop): `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/harness/` — `run.sh` + `coregraphics_shim.swift` (one line `@_exported import Foundation`, builds a fake `CoreGraphics` module) + `main.swift` + `last-run.txt` artifact. Pattern guarantees: product sources byte-identical except one inserted import (checked, rc=65), negative control (build must fail without shim), refuses to run on macOS (rc=75, pointing to `xcodebuild -project Exolon.xcodeproj -target Exolon -configuration Debug build`).
- **Applicability to this change**: the loader-only exclusion in `harness/README.md` ("Player/GameScene ... в контур не входит") was a scoping choice, not a hard limit. `GameCore/Player/Player.swift`, `GameCore/InputState.swift`, `GameCore/GameState.swift`, `GameCore/GameConstants.swift` import only CoreGraphics+Foundation → **compile and run on Linux under the same shim**, enough to pin the P1-4 latch semantics (`Player.swift:110-115/207-214/256-258`). Everything else — `GameScene.swift` (SKScene), `TMXLevelRuntime`/`LevelObstacles` (SKNode/SKTexture) — cannot run on Linux: the P1-9 accumulator reset, P1-4 scene half (`sceneJumpWasPressed`), P1-8 title-farm and P1-6 restore semantics are only assertable via (a) a real macOS XCTest target, or (b) extracting the pure state (accumulator/tick, latch flags, stage-award flag) into SpriteKit-free value types the implementer can put under the Linux harness. Choose one explicitly; a Makefile does not exist in the repo.
- Runbook for the Mac side: `engineering/runbooks/macos-probe.sh` (`xcodebuild -list` etc. sections A–D).

## 8. Unresolved

1. **Test strategy decision pending**: no Swift test target exists and GameScene is SpriteKit-bound; either design GameCore logic to be testable in the Linux harness (pure-value extraction) or accept macOS-only XCTest (needs new target in `Exolon.xcodeproj`, `.xcscheme`, and a Mac to run it — cannot be executed on this host).
2. **P1-6 intended semantics unclear**: `ORIGINAL_MECHANICS.md:43-48` only mandates "awards 1000 points once"; whether the collected launcher must keep firing afterwards (spec silent) or the +1000 should be decoupled from `isActive` needs a product ruling before the fix is pinned.
3. **P1-4 fix ownership**: the one-tick leak is caused by `Player.swift:115` overwriting the value set by `consumeContextualJumpPress` (`:257`) in the same `update` call — decide whether the latch masking moves into `Player` (input-edge model) or the scene stops passing a masked `jump:false` on the next tick; behavior of `beginDeath/respawn` (`Player.swift:224,239` resetting `jumpWasPressed=false` while UP held) is a second spurious-jump source after respawn.
4. **P1-9 fix scope**: `restartFromBeginning` (`:950`) and `didMove` (`:55`) also leave `accumulator`/`previousUpdateTime` untouched while swapping levels; the reset should probably be defined on any `currentLevel` replacement, not only on `transition`.
5. `L05S25.tmx` empty `nextLevel` was verified by property grep only (`grep -o name="nextLevel"`); no other terminal-zone data issue was investigated.
