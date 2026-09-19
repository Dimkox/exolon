# Exolon — authoritative mechanics audit

Sources of truth for this remake:
1. Rafaelle Cecco's 1987 game as disassembled in `rusarh/exolon-esl`.
2. `data_zone_data.asm` / `data_zone_blocks.asm` for all 125 zone layouts and action markers.
3. The individual `actions_*.asm` routines for behaviour.
4. StrategyWiki walkthrough only as a cross-check for intended play routes and player-facing behaviour.

## Global structure

- 125 zones: `000...124`, arranged as five stages of 25 zones.
- Screens advance discretely; no continuous scrolling.
- Normal screen entry gives no invulnerability.
- New game starts with 9 lives, 99 blaster rounds and 10 grenades.
- Death consumes one life and refills ammo to 99 and grenades to 10.
- The original rebuilds the current zone after death; a new zone clears active bullets, grenades, enemies, mines, rockets, sphere buffers and transient effects.
- This remake's TEST INVULNERABILITY is deliberately non-original and exists only for verification.

## Player weapons

### Blaster
- Finite ammo.
- Ordinary blaster rounds destroy floating enemies, spheres and launcher rockets.
- Ordinary fixed-turret bullets are not shootable.
- Double-barrel launcher projectiles are shootable and award 50 points.
- The vertical force field counts blaster hits and disappears on the 25th hit; award is 1000 points.
- Solid scenery/destroyable obstacles stop blaster fire.

### Grenade
- The original triggers a grenade after FIRE is held for 15 game ticks. Our user-selected remake control keeps GRENADE as a separate button, but trajectory/destruction rules should remain original.
- One active grenade at a time.
- It follows a fixed phase table rather than generic ballistic physics.
- On contacting terrain/obstacle/border it deactivates and checks the destroyable-object table.
- Generic destroyable object: 150 points.

## Stationary gun machine

- Random firing cadence from the original RNG.
- Bullet origin is the action cell at X and at Y+3 original pixels; in our 2x SpriteKit conversion the 4x4 projectile centre is `turret.left + 2`, `turret.bottom + 56`.
- Bullets travel left and are not destroyable by the player's blaster.
- The turret itself is grenade-destroyable and is worth 150 points through the generic destroyable table.

## Double-barrel launcher

- Fires from two vertically separated barrels.
- Stops firing when Vitorc is too close.
- Its 16x16 projectiles travel left, are destroyable by blaster and award 50 points each.
- Crossing the launcher's invisible bonus region awards 1000 points once.

## Rocket tower

- Fires randomly only while the player is sufficiently far away; original threshold is 30 internal pixels/units.
- Rocket horizontal velocity is -2 in the original routine.
- Rockets are destroyable by blaster and award 50 points.
- Rocket/player collision destroys the rocket and kills the player.

## Green missile-guidance beacon

- The control beacon is block 31 and is explicitly listed as grenade-destroyable.
- While it exists, only one guided missile is active at a time.
- Missile starts at the right side, moves left, then accelerates after crossing the original X=70 threshold (mapped to X=280 in the 512-wide reference conversion).
- Every update it moves vertically by one step toward the player's current Y position.
- The missile cannot be shot down directly with the blaster.
- A grenade striking the beacon destroys the beacon. If a guided missile is currently alive, it is removed immediately.
- Generic beacon destruction awards 150 points; removing the active guided missile at the same time awards another 850, i.e. 1000 total in the normal case.
- This is the required mechanic in Zone 008 and again wherever the control-beacon block occurs.

## Mines

- Trigger from a narrow horizontal/feet region, not from arbitrary sprite overlap.
- Once fired, a mine changes to a spent/explosion state.
- Normal player dies from the mine; the source explicitly routes mine damage through `KillPlayer_unless_Exoskeleton`.

## Pumps / crushers

- Hidden/waiting, then move into the play area according to the original phase counter, pause, and retract.
- Contact during the active phase kills a normal player.
- Source explicitly routes pump damage through `KillPlayer_unless_Exoskeleton`.

## Sphere homes / birthpods

- Each sphere home initializes 8 spheres; engine capacity is 24 spheres.
- Spheres bounce/change horizontal direction against bounds/terrain and make random vertical changes.
- A blaster hit destroys a sphere for 50 points.
- Sphere/player contact destroys the sphere and kills the player.

## Flying enemies

- They do not appear generically on every screen. `tab_enemy` explicitly lists the zones that may spawn them.
- Each listed zone selects one of six exact trajectory tables, a sprite family and a spawn delay.
- Maximum six active enemy slots.
- New enemies start from the right at X=120 original units, with Y derived from the player's Y (either roughly 10 above or player Y plus a random 0...15 offset).
- No new flying enemy is spawned once player X >= 84 in the original coordinate system.
- Blaster kill = 150 points.
- Contact kills the player and removes the enemy.
- The six trajectory byte tables in `actions_enemy_trajectory.asm` must be ported literally, not replaced by generic homing/patrol AI.

## Teleports

- Never automatic.
- Player must be correctly aligned in one of the paired portals and press UP.
- One press edge activates the teleport; holding UP must not continuously retrigger it.
- Destination is the paired portal with the original small X adjustment and teleport particle effect.

## Ammo / grenade boxes

- White box sets ammo to exactly 99 and disappears.
- Yellow box sets grenades to exactly 10 and disappears.
- These are refills, not additive pickups.

## Exoskeleton / changing room

- Player must be aligned in the changing room and press UP; activation is edge-triggered.
- It toggles the exoskeleton state and changes the player sprite set.
- It persists through deaths until the end of the current 25-zone stage.
- Source-confirmed immunity applies to hazards that call `KillPlayer_unless_Exoskeleton`, including mines and pumps.
- At stage end the exoskeleton flag is cleared.
- Having the exoskeleton forfeits the 10,000-point bravery bonus.
- Walkthrough behaviour also describes the suit as giving double blaster fire; this must be retained in the remake.

## Vertical force field

- Extends vertically from its source marker until the next no-walk cell.
- Touch is lethal.
- Exactly 25 blaster hits destroy it (13 trigger pulls with double-shot because two bullets count separately).
- Destruction awards 1000 points.
- Grenades are not the intended shortcut.

## Timed indestructible pursuer

- Zone timer uses a 700-loop threshold in the original.
- After the delay, an indestructible fighter appears at the right edge at the player's Y.
- It moves left rapidly; touching it kills the player.
- It cannot be shot down.
- Reaching the left edge removes it and permits another appearance after the delay logic.
- The timer is reset by a new zone/death rebuild; the walkthrough describes this as roughly 20–30 seconds on original hardware.

## Stage ends: Zones 024, 049, 074, 099, 124

- Reaching the stage-end trigger opens the bonus sequence.
- Award 1000 points per remaining life.
- If no exoskeleton was taken, award 10,000 bravery points.
- Timed bonus cursor can add 0/1000/3000/5000/7000 points depending on the selected phase.
- Add one life, capped at 9.
- Clear exoskeleton.
- Restore ammo=99 and grenades=10.
- Stage starting positions from source: Zone 000 `(16,112)`, 025 `(0,120)`, 050 `(0,32)`, 075 `(40,128)`, 100 `(16,112)` in original coordinates.
- Zone 124 displays FULL COMBAT ABILITY and then returns the game to the beginning.

## Walkthrough checkpoints that must work exactly

- Zone 000: grenade can destroy the opening turret/rocks route.
- Zone 002: first paired teleport; UP activates it.
- Zone 003: first table-driven flying enemy.
- Zone 005: birthpod/container releases sphere threat after destruction.
- Zone 006: double launcher projectiles are shootable; launcher stops firing nearby; touching its bonus region gives 1000.
- Zone 007: first mines.
- Zone 008: guided missile is indestructible by blaster; grenade destroys the antenna/control beacon and stops the missile.
- Zone 009: changing room activates exoskeleton/double shot with UP.
- Zone 023: combined upper/lower gun-machine arrangement.
- Zone 024: first stage bonus.
- Zone 035: 25-hit force field.
- Zone 043: grenade placement is required on the intended route.
- Zone 059: teleport is used to reach/destroy a control beacon.
- Zones 086–088: alternate route and another guided-missile situation.
- Zones 100–124 repeat the structural pattern of 25–49 with cosmetic changes after 101; Zone 124 completes the full game and loops to the beginning.

## Current remake audit rule

A mechanic is not considered implemented merely because its sprite appears in the restored backdrop. Every action marker in `game_init_actions.asm` must have a corresponding runtime implementation: torches, gun machines, flashing cells, mines, teleport, white/yellow refill boxes, sphere homes, pumps, rocket launchers, changing room, green guidance, bonus triggers, high voltage, stage end and beam. Visual fidelity and gameplay behaviour are audited separately so changing artwork must never rewrite working collision/physics again.
