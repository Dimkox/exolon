# Architecture — Exolon initial code audit

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Two trees share one Git repo:

1. **Product** — macOS SpriteKit app: `Exolon/` (18 Swift files) + `Exolon.xcodeproj/` + 125 TMX zones + docs.
2. **Factory overlay** — Adaptive Grok Python control plane. It does not compile into the game.

Runtime (from source, not executed here):

- `AppDelegate` hosts `GameView` + `GameScene` (512×384 logical, 60 Hz fixed step).
- `InputState` merges keyboard + gamepad sources; pause is edge-latched.
- `TMXLevelRuntime` instantiates objects from TMX names / selected `source_marker` blocks.
- `Player` has separate movement vs damage hitboxes; UP is jump unless cabin/teleport consumes it.
- Persistence: in-session checkpoint + high score; **process launch always Zone 000**.

## Proposed behavior

No product behavior change. Audit artifacts live under `engineering/` and `.grok-stack/runtime/` only.

## Components and boundaries

| Component | Role | Audit focus |
| --- | --- | --- |
| `GameView` / `GamepadInput` | HID | mapping, edge vs level, stick vs D-pad UP |
| `Player` / `GameConstants` | motion, colliders | solids, duck damage height |
| `GameScene` | flow, weapons, death, stage | suit, stage bonus, exit |
| `TMXLevelRuntime` | map objects | handled vs ignored markers |
| `LevelObstacles` | entity machines | mines, pumps, missiles, force fields |
| TMX `L01S01`–`L05S25` | 125 datasets | integrity vs compiler dump |

## Data flow

TMX XML → `TMXMapLoader` → renderer collision + object switch → `GameScene.fixedUpdate`.

Original action types 2–17 are **not** a Swift enum. Coverage is reconstructed by object `name` + `sourceBlock` versus `LEVEL_COMPILER_AUDIT.md`.

## API and event contracts

None. macOS app, no HTTP.

## Decisions

1. Treat `ORIGINAL_MECHANICS.md` as intended mechanics SoT; `README.md` as Step 9 checkpoint limits; compiler dump as zone/action inventory.
2. Do not treat missing late-zone polish as accidental regression when README says the archive is not fully audited.
3. Linux static counts are evidence of **data/code shape**, not of playable behaviour.
4. Packaging version mismatch (0.5 vs 0.3) is a candidate to verify on macOS, not a Linux crash.

## Risks and mitigations

- False “pass” from factory Python checks → explicit pending macOS section.
- Over-filing Step 9 gaps as bugs → separate backlog columns: defect / unfinished / hypothesis.
