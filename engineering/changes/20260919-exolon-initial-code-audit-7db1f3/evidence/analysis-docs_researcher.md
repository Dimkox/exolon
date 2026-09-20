# Docs researcher — intended mechanics and Step 9 limitations

**Route:** `7db1f3f0b126`  
**Scope:** repository docs and Swift comments only.  
**Rule:** these sources describe *intent / remake claims / compiler output*. They are **not** proof that runtime behaviour matches.

Sources used:

| File | Role |
|------|------|
| `ORIGINAL_MECHANICS.md` | Claimed **authoritative intended mechanics** for the remake (disassembly + zone data + action routines). |
| `LEVEL_COMPILER_AUDIT.md` | Compiler dump: 125 screens, action-type **counts**, per-screen `x:y:type` markers. |
| `README.md` | **Step 9 rebase (test archive)** checkpoint notes, not a full-game claim. |
| Swift comments / HUD strings | Remake implementation notes, input mapping, test-mode, unfinished visuals. |

---

## 1. Source-of-truth vs walkthrough vs remake-test-mode

### Source-of-truth (as declared)

`ORIGINAL_MECHANICS.md:1-7` lists:

1. Cecco 1987 game as disassembled in `rusarh/exolon-esl`
2. `data_zone_data.asm` / `data_zone_blocks.asm` (125 zones)
3. `actions_*.asm` behaviour routines

`ORIGINAL_MECHANICS.md:168-170` audit rule: a sprite in the backdrop is **not** implementation. Every marker from `game_init_actions.asm` needs a runtime counterpart. Visuals and gameplay are audited separately.

### Walkthrough-only (cross-check, not primary)

`ORIGINAL_MECHANICS.md:7` — StrategyWiki is **only** a cross-check for routes and player-facing behaviour.

Walkthrough-backed items called out in that file:

- Suit “double blaster fire” (`ORIGINAL_MECHANICS.md:119`) — “walkthrough behaviour also describes… must be retained”
- Timed pursuer “roughly 20–30 seconds on original hardware” (`ORIGINAL_MECHANICS.md:136`)
- Section “Walkthrough checkpoints that must work exactly” (`ORIGINAL_MECHANICS.md:150-166`)

### Remake / test-mode (explicitly non-original)

- `ORIGINAL_MECHANICS.md:17` — **TEST INVULNERABILITY** is deliberately non-original, for verification only.
- `ORIGINAL_MECHANICS.md:30` — original grenade is FIRE held 15 ticks; remake keeps **GRENADE as a separate button**; trajectory/destruction should stay original.
- `README.md:1-17` — “Step 9 Rebase (test archive)”; “runnable checkpoint… **not** the claim that every late-zone action is already audited.”
- `README.md:11` — pistons lethal unless test Invulnerability is ON.
- `GameScene.swift:45,186-187,602,819-822` — pause menu toggles `testInvulnerabilityEnabled`; `hitPlayer()` no-ops when ON.
- `GameScene.swift:832` — title overlay still labels **“STEP 10”** while window title is Step 9 (`AppDelegate.swift:16`). Docs/UI disagree on step name; treat as remake chrome, not original.

---

## 2. Global structure (intended)

From `ORIGINAL_MECHANICS.md:9-17`:

- **125 zones** `000…124`, five stages × 25.
- Discrete screen advance; no continuous scrolling.
- Normal screen entry: **no** invulnerability.
- New game: **9 lives, 99 blaster, 10 grenades**.
- Death: −1 life; refill ammo 99 / grenades 10; original **rebuilds current zone**.
- New zone clears bullets, grenades, enemies, mines, rockets, sphere buffers, transients.

`LEVEL_COMPILER_AUDIT.md:3` — “Generated all 125 screens from the 1987 zone/block/font data.” Lines `000`–`124` map `L01S01`…`L05S25`.

`README.md:15` — remake claim: every launch still starts **Zone 000**; High Score persists. (Claim, not verified here.)

---

## 3. Action-type catalog (types 2–17)

**Docs never print a numbered table `2=torch`.** Counts are in `LEVEL_COMPILER_AUDIT.md:5`. Names of markers that *must* exist are in `ORIGINAL_MECHANICS.md:170`. Per-screen records are `x:y:type` triplets.

The mapping below is **inferred** by lining those names up with counts and landmark screens in the compiler dump. It is **not** an official API and must not be treated as proven runtime enum values.

| Type | Count (`LEVEL_COMPILER_AUDIT.md:5`) | Inferred original marker | Landmark in dump |
|------|--------------------------------------|--------------------------|------------------|
| 2 | 101 | torches | L01S01 `1:6:2,9:6:2`; L01S08 mines screen also has `:2` |
| 3 | 37 | gun machines | L01S01 `20:14:3`; L01S08 `12:4:3`; Zone 023 empty of actions (see below) |
| 4 | 341 | flashing cells | densest type; e.g. L01S01 many `:4` |
| 5 | 53 | mines | L01S08 `10:19:5,15:19:5,20:19:5` (Zone 007 first mines) |
| 6 | 70 | teleport | L01S03 `23:6:6,5:13:6` (Zone 002 first paired teleport) |
| 7 | 48 | white ammo boxes | L01S10 `18:16:7` with `:8` sibling |
| 8 | 38 | yellow grenade boxes | L01S10 `29:16:8` |
| 9 | 48 | sphere homes | L01S06 `24:15:9`; L01S09 `27:15:9` |
| 10 | 46 | pumps / crushers | L01S03 `27:18:10`; L01S10 `4:20:10,12:20:10` |
| 11 | 56 | rocket launchers | often paired with `:14` (e.g. L01S11 `23:15:11,24:15:14`) |
| 12 | **5** | changing room | L01S10 `23:11:12` (Zone 009); also L02S10, L03S11, L04S16, L05S10 |
| 13 | 13 | green guidance / control beacon | L01S09 `20:11:13` (Zone 008) |
| 14 | 92 | bonus triggers | frequent; often next to `:11` |
| 15 | 7 | high voltage (stage-end adjacent?) | L01S25 `14:4:15` then `15:13:16` |
| 16 | **5** | stage end | L01S25, L02S25, L03S25, L04S25, L05S25 all have `:16` |
| 17 | 10 | beam / vertical force field | L02S11 `20:2:17` (Zone 035 25-hit field); often flanked by `:2` |

`ORIGINAL_MECHANICS.md:170` required runtime list (order as written):  
torches, gun machines, flashing cells, mines, teleport, white/yellow refill boxes, sphere homes, pumps, rocket launchers, changing room, green guidance, bonus triggers, high voltage, stage end, beam.

Screens with **empty** `actions=` in the dump (compiler: no markers):  
`L01S23` (Zone 022), `L03S09` (058), `L03S14` (063), `L04S11` (085) — `LEVEL_COMPILER_AUDIT.md:31,58,63,85`. Walkthrough still names Zone 023 for gun-machine layout (`ORIGINAL_MECHANICS.md:160`); **zone numbering vs `LxxSyy` is 0-based zone index** (`000` = L01S01).

---

## 4. Zone / action / solid counts

- 125 compiled screens (`LEVEL_COMPILER_AUDIT.md:3,7-132`).
- Type totals as above; type 4 dominates (341).
- Five changing rooms (type 12) and five stage-end markers (type 16) match five stages.
- Per-screen `solid=` is tile-solid cell count (e.g. L01S01 solid=223, L02S03/L05S03 solid=54). Not a gameplay API.

`README.md:6` — project keeps the 125-zone / original-visual pipeline.

---

## 5. Cabin / teleport / suit rules

### Intended (ORIGINAL_MECHANICS)

**Teleports** (`ORIGINAL_MECHANICS.md:98-103`):

- Never automatic.
- Align in a paired portal and press **UP**.
- Edge-triggered; holding UP must not retrigger.
- Destination = paired portal + original small X adjustment + particle effect.

**Exoskeleton / changing room** (`ORIGINAL_MECHANICS.md:111-119`):

- Align in changing room, press **UP**, edge-triggered.
- Toggles suit and sprite set.
- Persists through **deaths until end of current 25-zone stage**.
- Immunity for hazards that call `KillPlayer_unless_Exoskeleton` (mines, pumps).
- Stage end **clears** the flag.
- Suit **forfeits 10,000 bravery bonus**.
- Double blaster: walkthrough-described; remake must keep it.

**Mines / pumps** (`ORIGINAL_MECHANICS.md:68-78`): mines from narrow feet region; pumps phase in/out; both skip kill if exoskeleton.

### Step 9 remake claims (README — not proof)

`README.md:7-15,19-23`:

- Zone 009 objects from reference TMX, not old source-marker approximation.
- Zone 009 pistons: x=64/192, **y=320** (not y=384).
- Changing room: real **32×80** rectangle at **x=368, y=176** Tiled coords.
- Rectangle vs tile-object conversion explicit.
- Pistons lethal when exposed unless test invuln.
- **UP in changing room toggles Exoskeleton**.
- Exoskeleton: double blaster; protects vs mines/pistons.
- Restart/new session **resets** Exoskeleton (narrower than original “until stage end” if a session spans stages — docs conflict with `ORIGINAL_MECHANICS.md:115`).
- Cabin artwork pass-through; collision exclusion by **object type** on **every** changing-room screen, not only Zone 009.
- UP in cabin/teleport consumed as contextual action; must not jump on the next fixed step.

### Swift comments (remake notes, not original ROM)

- `TMXLevelRuntime.swift:113-116,291-306` — changing room is not a wall; 32×80 TMX rect is trigger; exclusion ~96× wide, floor kept solid.
- `TMXLevelRuntime.swift:281-284` — TMX type `"teleport"`; `"capsule"` = changing room.
- `LevelObstacles.swift:283-298` — teleport colrect `updateColRect(16,32,32,48)`; full 64×96 containment required.
- `GameScene.swift:233-253`, `Player.swift:252-257` — UP consumed for cabin/teleport; `consumeContextualJumpPress()` holds jump latch.
- `PlayerSpriteNode.swift:43-45` — **temporary cyan tint** until original exoskeleton frames exist; comment claims “mechanics already exact” (claim, not evidence).

---

## 6. Input mapping claims

### Intended original vs remake grenade

- Original: FIRE held **15 ticks** → grenade (`ORIGINAL_MECHANICS.md:30`).
- Remake: separate GRENADE button.

### Keyboard (`GameView.swift:17-67`)

| Key | Action |
|-----|--------|
| Left / Right arrows | move |
| Down | crouch (+ menu down) |
| Up | jump / contextual UP (+ menu up) |
| Space | fire |
| Option (left/right, incl. `flagsChanged`) | grenade |
| P | pause |
| F1 | debug hitboxes |

### Gamepad (`GamepadInput.swift:49-90`)

| Control | Action |
|---------|--------|
| D-pad L/R | move |
| D-pad down / stick Y < −0.65 | crouch |
| D-pad up / buttonA (PS Cross) | jump |
| buttonX (PS Square) | fire / menu confirm |
| buttonB (PS Circle) | grenade |
| Pause/Options handler | pause pulse |
| Stick deadzone 0.35 | move |

Pause overlay copy (`GameScene.swift:805-807`): `↑/↓ D-PAD — SELECT`, `SPACE / □ — ACTIVATE`, `P / OPTIONS — RESUME`. Invulnerability is a pause-menu item (`GameScene.swift:819-822`).

`InputState.swift:70-71` — pause is edge-triggered because gamepad pause is a pulse.

---

## 7. Other intended mechanics (catalog, not implementation proof)

Summarised from `ORIGINAL_MECHANICS.md:19-148`:

- **Blaster:** finite ammo; kills floaters, spheres, launcher rockets; **not** ordinary turret bullets; double-launcher shots 50 pts; force field 25 hits / 1000 pts; scenery stops shots.
- **Grenade:** one at a time; phase table not generic ballistics; terrain contact checks destroyable table; generic destroyable **150** pts.
- **Gun machine:** RNG cadence; origin action cell X, Y+3 orig px; 2× SK: 4×4 centre `turret.left+2`, `turret.bottom+56`; bullets left, not shootable; turret grenade-destroyable 150.
- **Double launcher:** two barrels; stops when Vitorc too close; 16×16 left, blaster-kill 50; invisible bonus region **1000 once**.
- **Rocket tower:** fire only if player far (30 orig units); vx = −2; blaster 50; contact kills player and rocket.
- **Green beacon:** block 31 grenade-destroyable; one guided missile; start right, accelerate after orig X=70 → **X=280** on 512-wide; homing ±1 Y/step; not blaster-killable; beacon 150 + missile 850 = **1000** typical. Required Zone 008 and every beacon block.
- **Spheres:** 8 per home; cap 24; bounce; blaster 50; contact kills player.
- **Flying enemies:** only `tab_enemy` zones; six trajectory tables literal; max 6 slots; spawn right X=120 orig, Y from player; no spawn if player X ≥ 84 orig; blaster 150.
- **Ammo/grenade boxes:** set **exactly** 99 / 10, not additive.
- **Force field:** vertical to next no-walk; touch lethal; 25 hits (13 double-shot pulls); grenades not intended shortcut.
- **Timed pursuer:** 700-loop threshold; indestructible; timer reset on zone/death rebuild.
- **Stage ends 024, 049, 074, 099, 124:** 1000/life; 10000 bravery if no suit; timed cursor 0/1000/3000/5000/7000; +1 life cap 9; clear suit; ammo 99 / grenades 10.
- Stage start orig coords: 000 `(16,112)`, 025 `(0,120)`, 050 `(0,32)`, 075 `(40,128)`, 100 `(16,112)`.
- Zone 124: FULL COMBAT ABILITY then loop to start.

`GameScene.swift:622-625` — stage-end bonus code exists but comment says it is **deliberately dormant until later steps add Zones 024/049/074/099/124**, even though those TMX files exist in Resources. Step 9 limitation: **bonus sequence not claimed complete**.

`TMXLevelRuntime.swift:166-168` — comment restates one-missile / grenade-kills-guidance / not blaster-destroyable.

---

## 8. Known unfinished / Step 9 limitations (docs + comments)

From **README.md** (test archive):

- Not every late-zone action audited (`README.md:17`).
- Rebase focused Zone 009 cabin/pistons/TMX conversion (`README.md:7-10`).

From **ORIGINAL_MECHANICS.md:168-170**:

- Backdrop ≠ behaviour; full `game_init_actions.asm` set still the bar.

From **Swift comments**:

- `GameScene.swift:624-625` — stage-end awards dormant pending “later steps”.
- `PlayerSpriteNode.swift:43-45` — original exoskeleton frames not wired.
- `TMXLevelRuntime.swift:494-498` — Step 9: do not hand-place planets; TMX layers only + sparse stars.
- `GameConstants.swift:25-31` — crouch **damage** box 49 px (not 52) is a remake collision tweak to match turret-duck behaviour.
- Title says STEP 10 (`GameScene.swift:832`) vs archive “Step 9”.

`README.md:15` vs original persistence: remake **resets Exoskeleton on restart/new session**; original keeps it until **stage** end (`ORIGINAL_MECHANICS.md:115,145`).

---

## 9. Walkthrough checkpoints (must-work list — walkthrough-backed)

`ORIGINAL_MECHANICS.md:150-166` (zone numbers 000-based):

| Zone | Intended check |
|------|----------------|
| 000 | Grenade destroys opening turret/rocks |
| 002 | First paired teleport; UP |
| 003 | First table-driven flying enemy |
| 005 | Birthpod/container → spheres after destruction |
| 006 | Double launcher: shootable shots; stops nearby; bonus region 1000 |
| 007 | First mines |
| 008 | Guided missile not blaster-killable; grenade beacon stops missile |
| 009 | Changing room: exoskeleton / double shot via UP |
| 023 | Combined upper/lower gun-machine |
| 024 | First stage bonus |
| 035 | 25-hit force field |
| 043 | Grenade placement required on intended route |
| 059 | Teleport to reach/destroy control beacon |
| 086–088 | Alternate route + another guided missile |
| 100–124 | Pattern of 025–049 with cosmetic changes after 101; 124 ends and loops |

Compiler cross-check (not gameplay proof): Zone 009 = `L01S10` has type 12 (`LEVEL_COMPILER_AUDIT.md:16`); Zone 008 = `L01S09` has type 13 (`:13`); Zone 035 = `L02S11` has type 17 (`LEVEL_COMPILER_AUDIT.md:35`).

---

## 10. What this report does **not** do

- Does not assert that TMX, SpriteKit, or collisions implement any of the above.
- Does not treat action-type number mapping as an official contract (numbers from compiler dump; names from mechanics list).
- Does not edit game sources.
