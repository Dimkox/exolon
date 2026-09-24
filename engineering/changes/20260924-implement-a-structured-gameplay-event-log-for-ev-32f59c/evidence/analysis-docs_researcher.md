# Canonical spec research — route 32f59cc7dcb6, wave-A findings P1-4 / P1-6 / P1-8 / P1-9

Author: `docs_researcher` (read-only). Date: 2026-09-24.
Normative sources examined (source-of-truth order per `AGENTS.md`):
`ORIGINAL_MECHANICS.md` (OM), `README.md` (RW, weaker — self-declared "runnable checkpoint,
not the claim that every late-zone action is already audited", RW:17),
`engineering/reports/exolon-full-audit-20260920-v3.md` (A3, declared "авторитет" at A3:6),
`LEVEL_COMPILER_AUDIT.md` (LCA, level-data only), GitHub issues #8/#10/#12/#13 in
`Dimkox/exolon`, plus per-file lag evidence cited by A3 (`evidence/perfile/*` under
`engineering/changes/20260919-exolon-initial-code-audit-7db1f3/`; A3 §5 keeps some lag
numbers as unconfirmed). Code line refs are current HEAD tree (they drifted from A3 refs).

---

## 1. P1-4 — jump latch fires after teleport/changing-room while UP held (issue #8)

**Canonical expected behavior (quoted):**
- OM:100-102 (Teleports): "Never automatic. / Player must be correctly aligned in one of the
  paired portals and press UP. / One press edge activates the teleport; holding UP must not
  continuously retrigger it."
- OM:113 (Exoskeleton/changing room): "Player must be aligned in the changing room and press
  UP; activation is edge-triggered."
- RW:23 (remake promise): "UP inside a changing room/teleport is consumed as a contextual
  action and cannot become an accidental jump on the following fixed step."
- Issue #8 (https://github.com/Dimkox/exolon/issues/8): "Контекстное действие сбрасывает jump
  latch в том же fixed tick. Нужен regression-тест teleport/changing-room input edge."

**Expected semantics, stated as spec:** a single UP edge activates the contextual action once;
the same physical press must never become a jump — neither on the activating step nor on any
following step while the key stays held; holding UP must not retrigger the teleport either.
After teleport arrival the original is an instant transfer with no vertical movement
(player-input lag, PI-02 row: "Оригинал: телепорт — мгновенный перенос без движения",
`perfile/player-input.md:51`).

**Numeric constants that matter:**
- Fixed step = 1/60 s (`GameConstants.swift fixedTimeStep`); "the following fixed step" in
  RW:23 therefore means ≈16.7 ms later — PI-01 measured the false jump as +26.65 px vs control
  28.00 px (`perfile/player-input.md:50`).
- Current defect mechanics: `GameScene.swift:251-269` passes synthesized `InputSnapshot(jump:false)`
  when `consumedUpInteraction`, calls `player.consumeContextualJumpPress()`
  (`Player.swift:256-258`, sets `jumpWasPressed = true`), but `Player.swift:115` then
  unconditionally rewrites `jumpWasPressed = input.jump` at the end of the same
  `update(input:)` — the latch collapses in the same step (A3 §1 P1-4,
  `exolon-full-audit-20260920-v3.md:29`).
- `Player.swift:207-214 teleport()` zeroes velocity, sets `isGrounded = true` and
  `jumpWasPressed = true` (arrival-latch behaviour PI-02 keys on).
- Contextual consumption happens once per fixed step inside `fixedUpdate` chain
  (snapshot → consumePause → edge jump → cabin/teleport → synthesized snapshot,
  `perfile/player-input.md:16`).

**Contradictions / silence:**
- OM is silent about jump suppression: "holding UP must not continuously retrigger it" (OM:102)
  governs *teleport re-trigger*, not the accidental *jump*; the no-accidental-jump promise exists
  only in RW:23, which is a checkpoint document, not a mechanics source. PI-01 verdict
  (`perfile/player-input.md:112`) explicitly says the earlier docs-researcher verdict
  "ПОДТВЕРЖДЁНО" at `analysis-docs_researcher-fullaudit.md:110` was true only for the
  double-toggle case.
- OM never says the arriving player's jump latch state must be held; `jumpWasPressed = true`
  inside `teleport()` is a remake invention with no cited normative source (silence).

---

## 2. P1-6 — double launcher permanently disabled after bonus collect (issue #10)

**Canonical expected behavior (quoted):**
- OM:44-48 (Double-barrel launcher): "Fires from two vertically separated barrels. / Stops
  firing when Vitorc is too close. / Its 16x16 projectiles travel left, are destroyable by
  blaster and award 50 points each. / Crossing the launcher's invisible bonus region awards
  1000 points once."
- Issue #10 (https://github.com/Dimkox/exolon/issues/10): "После collectDoubleLauncherBonus
  launcher больше не восстанавливается. Разделить состояние бонуса и состояние препятствия/стрельбы."
- A3:31: "объектов `double_launcher`: **19 на 18 картах**; `collectDoubleLauncherBonus` —
  единственный писатель флага активности, восстановление отсутствует."

**Expected semantics, stated as spec:** the 1000-point bonus is a **once-per-launcher award for
crossing the bonus region**; the launcher itself remains a live hazard that keeps firing (with
the proximity stop), keeps shooting-destroyable projectiles worth 50 points, and stays visible.
Bonus state and obstacle/fire state are two distinct states (issue #10 wording).

**Numeric constants that matter:**
- Bonus = 1000 points, once per launcher (`TMXLevelRuntime.swift:219-223` returns `1_000` per
  collected launcher; awarded at `GameScene.swift:299-301`).
- Projectile award = 50 points (`LevelObstacles.swift:152` `pointsWhenShotDown = 50`; OM:47).
- Proximity stop = 110 px in current code (`LevelObstacles.swift:703-705`
  `distance > 110`); OM:46 only says "too close" — no canonical number.
- Fire cadence: `Int.random(in: 20...160)/60` s (`LevelObstacles.swift:686,707`); no normative
  source for this range (OM says only "fires from two barrels").
- Current defect: `collectBonusIfTouched` (`LevelObstacles.swift:718-722`) is the sole writer of
  `isActive=false` for this class and also dims to `alpha 0.45`; `fixedUpdate` gate
  `guard isActive, !player.isDying` (`:699`) then kills fire forever (A3:31, OBST-01 at
  `perfile/obstacles.md:25`, which adds "вызывается и во время анимации смерти" and notes the
  2000-point award observable on L04S13).
- Coverage: 19 launcher objects on 18 maps (A3:31).

**Contradictions / silence:**
- OM:48 says the bonus region is **invisible** ("invisible bonus region"); the remake reuses the
  same visible 64×48 sprite hitbox for both bonus crossing and fire gating
  (`LevelObstacles.swift:719`, `perfile/obstacles.md:25` "видимым хитбоксом 64×48") — spec/
  implementation divergence, and OM never defines the region geometry (silence).
- OM never states explicitly that the launcher *keeps firing after the bonus*; that expectation
  is assembled from OM:44-47 (present-tense continuous behaviour, shootable 50-point rockets)
  plus issue #10's imperative. A3 §1 and issue #10 are the only sources that name the defect as
  "permanently disabled".
- Silence on whether the once-award is per-launcher-instance or per-screen: OM:48 "once";
  the code awards per instance (`TMXLevelRuntime.swift:220` loop returns once per call but
  each of the 19 objects can award).

---

## 3. P1-8 — stage bonus re-triggers on final zone 124, score farm via title flow (issue #12)

**Canonical expected behavior (quoted):**
- OM:138-148 (Stage ends: Zones 024, 049, 074, 099, 124): "Reaching the stage-end trigger opens
  the bonus sequence. / Award 1000 points per remaining life. / If no exoskeleton was taken,
  award 10,000 bravery points. / Timed bonus cursor can add 0/1000/3000/5000/7000 points
  depending on the selected phase. / Add one life, capped at 9. / Clear exoskeleton. / Restore
  ammo=99 and grenades=10. … / Zone 124 displays FULL COMBAT ABILITY and then returns the game
  to the beginning."
- OM:117: "At stage end the exoskeleton flag is cleared."
- OM:163 (walkthrough): "Zone 124 completes the full game and loops to the beginning."
- Issue #12 (https://github.com/Dimkox/exolon/issues/12): "После Zone 124 stage bonus может
  срабатывать повторно через title/terminal path. Нужен одноразовый terminal state и
  regression-тест."

**Expected semantics, stated as spec:** the stage-end bonus sequence is a one-shot event bound
to *reaching the stage-end trigger and advancing past the stage boundary*; after zone 124 the
terminal is one-shot: FULL COMBAT ABILITY → game returns to the beginning (a new game —
OM:14 "New game starts with 9 lives, 99 blaster rounds and 10 grenades"), never a re-entry into
zone 124 at the same position with the same score. Re-awarding `lives×1000` per SPACE cycle is
out of spec on every reading.

**Numeric constants that matter:**
- Award formula: `lives × 1000`; bravery 10 000; timed bonus ladder 0/1000/3000/5000/7000;
  +1 life capped at 9 (startingLives=9); refill ammo=99/grenades=10 (OM:141-145; A3 P1-10).
- Stage boundary zones: `[24, 49, 74, 99, 124]` in code — `zoneNumber` is 0-based
  (`GameScene.swift:626` guard), consistent with OM:11 "125 zones: `000...124`".
- Exit trigger in code is `player.position.x > 510` (`GameScene.swift:609`), not the
  `stageExitMarkers` objects (write-only, RT-05/A4.2, A3:38).
- Farm arithmetic (A3:33, P1-8): score clamp `min(999_999, …)` (`GameScene.swift:662`);
  at 9 lives each cycle pays +9000 ⇒ `(999999−45000)/9000 = 106.1 ⇒ 107` cycles to the ceiling;
  `beginFromTitle` (`GameScene.swift:708-717`) resets no points/lives/zone/position, while
  `position.x` is clamped to `[24, 544]` (`Player.swift` movement clamp) so `x > 510` stays true
  and `checkScreenExit` (`:608-619`) re-fires on the next fixed step. Bonus is applied at
  `:612` *before* the `guard !next.isEmpty` terminal branch at `:614`.
- GS-01's executable replica figure: 111 cycles / 222 presses → 999 999
  (`perfile/gamescene.md:61`; A3 §5 notes loop counts from Linux replicas remain "lag" numbers —
  A3 confirmed only the mechanics by reading `GameScene.swift:610-612, :708-717`).

**Contradictions / silence:**
- The code comment at `GameScene.swift:622-625` claims the stage-bonus path is "deliberately
  dormant until later steps add Zones 024/049/074/099/124", while the guard is live on the full
  125-zone chain — a documented in-code lie (A3 P1-10: "комментарий врёт"; GS-02 in
  `perfile/gamescene.md:62`).
- OM names a "stage-end trigger" but never defines it (which x, which marker); LCA only lists
  action codes (`14:4:15,15:13:16` on the S25 maps, e.g. LCA:32 zone 024). The remake's
  `x > 510` + `zone ∈ {24,49,74,99,124}` combination has no normative source (silence).
- Bravery 10 000, timed bonus, and "Clear exoskeleton" are OM requirements with no
  implementation (A3 P1-10/ECO-03; GS-02) — relevant because the spec says the *full* sequence,
  including its one-shot transition to the next stage start position (OM:146-147 lists stage
  starts), is what "opens the bonus sequence" means; OM is silent about what exact UI/sequence
  order the remake must use.
- RW:15 "every application launch still starts from Zone 000" vs the terminal→title→
  `beginFromTitle` "continue" path (gamescene.md:164: «SPACE … ничего не начинает, а
  продолжает») — README promise contradicts the title-flow behaviour the farm rides on.

---

## 4. P1-9 — fixed-tick accumulator not reset on zone transition; up to 15 steps modelled before first frame (issue #13)

**Canonical expected behavior:**
- The normative sources are **silent on a tick/accumulator policy** — this is remake-internal
  timing, not original mechanics. What OM *does* pin:
  - OM:13: "Normal screen entry gives no invulnerability." (so extra modelled steps are
    immediately lethal-time, no grace to absorb them)
  - OM:16: "The original rebuilds the current zone after death; a new zone clears active
    bullets, grenades, enemies, mines, rockets, sphere buffers and transient effects."
  - OM:30: the original's own clock unit is 50 Hz ZX ticks ("grenade after FIRE is held for
    15 game ticks"; `GameConstants.swift:7-9` comment uses "ZX Spectrum timing is 50 Hz").
- Issue #13 (https://github.com/Dimkox/exolon/issues/13) is the operative expectation:
  "Accumulator не сбрасывается при transition; после frame gap в новую зону уходят лишние шаги
  без защиты. Сбрасывать accumulator и определить transition timing." ⇒ spec: (a) reset the
  accumulator on zone transition, (b) transition timing must be *defined* (currently undefined),
  (c) a new zone must not receive unprotected catch-up steps.

**Numeric constants that matter:**
- `fixedTimeStep = 1.0/60.0`, `maximumFrameTime = 0.25` (`GameConstants.swift:6-7`);
  `frameTime = min(currentTime - previousUpdateTime, 0.25)` then
  `while accumulator >= fixedTimeStep { fixedUpdate(...) }` (`GameScene.swift:129-136`).
  A 0.25 s gap ⇒ **15 fixed steps** (0.25/(1/60) = 15) — the "до 15 шагов без защиты" of
  A3:34 and LC-2 (`perfile/spritekit-lifecycle.md:57`).
- `transition()` runs synchronously *inside* that same `fixedUpdate` chain
  (`checkScreenExit` → `transition`, `GameScene.swift:618, 633`); zone load cost
  (XML parse + up to 247 sprites + cold 512×384 texture) inflates the next frame delta
  (LC-2). `invulnerability = 0` on normal entry (`GameScene.swift:650`, per OM:13).
- `accumulator` appears only at `GameScene.swift:51, 131, 135` — never reset by `transition`
  (A3:34).
- `postDeathProtectionDuration = 0.4` s is documented as 20 ticks @ 50 Hz
  (`GameConstants.swift:8-9`) while all other tick conversions divide by 60 — TC-05
  (A3 §3: "единицы тиков противоречат себе"; `perfile/timing-concurrency.md:236`; documented
  source of the number 70 does not exist in repo).

**Contradictions / silence:**
- 50 Hz original units vs 60 Hz remake steps: no normative ruling on which cadence the remake
  owes the player; only the original is 50 Hz (OM:30 context, `GameConstants.swift:7-9`
  comment). TC-05 verdict: "требует именованного решения" (needs a named human decision) —
  i.e., the sources explicitly do not settle it.
- No source (OM, RW, LCA) states a frame-gap/catch-up policy ("drop vs clamp vs reset") —
  issue #13's "определить transition timing" acknowledges this as missing spec, not violated
  spec.
- LC-23 companion fact (`perfile/spritekit-lifecycle.md:78`): app deactivation pauses input but
  not the SKView update, producing the same unprotected catch-up class — silent in all
  normative docs.

---

## 5. Cross-cutting notes for the event-log part of the route

- A3 §9: the product currently has **0** calls to `print`/`NSLog`/`os_log`
  (`grep print|NSLog|os_log = 0`, confirmed in A3:200) — a structured gameplay event log is a
  green-field surface, nothing to migrate.
- Determinism caveat for testability: TC-06 (A3 §3, lag-unconfirmed): 16 global RNG call sites
  (≈3 per step) ⇒ golden replays impossible today; the double-launcher fire timer
  (`LevelObstacles.swift:686,707` `Int.random`/`Bool.random`) is one of them.
- OM's "Current remake audit rule" (OM:165-170) requires every action marker to have a runtime
  implementation; events for launcher/teleport/stage-end actions are auditable outcomes, so the
  log vocabulary should track OM's named mechanics, not the code's private flags.

## 6. Summary of spec status per finding

| Finding | Canonical spec strength | Primary normative anchor | Gap type |
| --- | --- | --- | --- |
| P1-4 | Medium — edge-activation is OM law; the *jump-suppression on following step* is RW-only | OM:102, OM:113, RW:23, issue #8 | RW vs OM hierarchy; OM silent on jump |
| P1-6 | Medium-strong — "1000 once" + live hazard behaviour in OM; separation mandate only in issue #10 | OM:44-48, issue #10, A3:31 | OM silent on post-bonus fire; "invisible region" contradicts shared hitbox |
| P1-8 | Strong for the one-shot sequence + "returns the beginning"; farm violates it | OM:138-148, OM:163, issue #12, A3:33 | trigger geometry undefined; code comment lies; 3 of 6 bonus rules missing (P1-10) |
| P1-9 | Weak as *spec* — sources silent; the requirement is issue #13 itself | issue #13; OM:13,16; A3:34, LC-2 | missing spec (transition timing, 50vs60 Hz undecided — TC-05 "требует именованного решения") |
