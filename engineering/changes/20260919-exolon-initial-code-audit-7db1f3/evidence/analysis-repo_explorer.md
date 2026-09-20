# Repo explorer: Exolon product tree vs factory overlay

**Route:** `7db1f3f0b126`\
**Session:** `exolon-initial-audit-20260919`\
**HEAD:** `403eb1322d645154307ce11bf91be89e2082e1dd`\
**Branch:** `codex/factory-initial-audit`\
**Host:** Linux `<host>` <kernel> x86_64 (Ubuntu).\
**Date:** 2026-09-19\

**Confirmed host limits:** no `swift`, no `xcodebuild`, no `qemu-system-x86_64`. This report does **not** claim a Swift/macOS build pass.

Untracked at inspect time (not part of HEAD product): `engineering/` (this change package), `.grok-stack/runtime/*`, `__pycache__`.

---

## 1. Two trees in one Git repo (confirmed)

| Layer | Role | Tracked files (approx.) |
|---|---|---|
| **Product** | Native macOS SpriteKit remake | `Exolon/` (300 paths), `Exolon.xcodeproj/project.pbxproj` (1), `README.md`, `ORIGINAL_MECHANICS.md`, `LEVEL_COMPILER_AUDIT.md` |
| **Factory overlay** | Adaptive Grok / Python control plane | `factory/` (138), `scripts/` (13), `schemas/` (11), hook `*.py`, `AGENTS.md`, `.grok/`, `.grok-stack/`, `.agents/`, `bandit.yaml`, `ruff.toml`, `.coveragerc` |

Product sources do not import factory Python. Overlay does not compile into the SpriteKit target. Untracked `engineering/` is workflow evidence only.

---

## 2. Swift product inventory (confirmed)

**18** `*.swift` files under `Exolon/`; **0** Swift files outside that tree.

| Path |
|---|
| `Exolon/main.swift` |
| `Exolon/Platform/macOS/AppDelegate.swift` |
| `Exolon/Platform/macOS/GameView.swift` |
| `Exolon/Platform/macOS/GamepadInput.swift` |
| `Exolon/GameCore/GameConstants.swift` |
| `Exolon/GameCore/GameScene.swift` |
| `Exolon/GameCore/GameState.swift` |
| `Exolon/GameCore/HUDNode.swift` |
| `Exolon/GameCore/InputState.swift` |
| `Exolon/GameCore/Effects/ExplosionEffect.swift` |
| `Exolon/GameCore/Levels/TMXLevelRuntime.swift` |
| `Exolon/GameCore/Levels/TMXMapLoader.swift` |
| `Exolon/GameCore/Levels/TMXTileMapRenderer.swift` |
| `Exolon/GameCore/Objects/LevelObstacles.swift` |
| `Exolon/GameCore/Player/Player.swift` |
| `Exolon/GameCore/Player/PlayerSpriteNode.swift` |
| `Exolon/GameCore/Weapons/BlasterBullet.swift` |
| `Exolon/GameCore/Weapons/Grenade.swift` |

**pbxproj membership:** unique `/* … in Sources */` names = those 18 files. Symmetric difference vs filesystem = empty. Dual Debug/Release listing makes the Sources phase appear twice (36 entries / 18 unique).

**Xcode project facts:**

- Single `PBXNativeTarget` `"Exolon"`, `productType = com.apple.product-type.application`
- `SDKROOT = macosx`, `MACOSX_DEPLOYMENT_TARGET = 10.14`, `SWIFT_VERSION = 5.0`
- Frameworks: Cocoa, SpriteKit, GameController (`sourceTree = SDKROOT`)
- `PRODUCT_BUNDLE_IDENTIFIER = com.exolon.remake`
- `GENERATE_INFOPLIST_FILE = NO`; `INFOPLIST_FILE = Exolon/Resources/Info.plist`
- **No** `xcshareddata` / `.xcscheme` on disk (only `project.pbxproj`)
- **No** XCTest / second native target

`project.pbxproj` SHA-256: `d7393eb6a52014c30f61f9a2ee46782ecbbea8d397b130806afb969886bbe81a` (1474 lines).

---

## 3. Resources (confirmed)

`Exolon/Resources/` = **282** files, all git-tracked (`git ls-files` count 282).

| Type | Count |
|---|---|
| `.tmx` | **125** |
| `.png` | **153** |
| `.gif` | **3** |
| `Info.plist` | **1** |

### 3.1 TMX zones

Expected grid `L{01..05}S{01..25}.tmx` = 125. Filesystem has all 125; pbx unique TMX names = 125; missing-from-pbx = none; in-pbx-not-on-fs = none.

All 125 files start with XML `<map` (no empty files). Size range 2850–19251 bytes (mean ~4094).

Sample hashes:

- `Exolon/Resources/L01S01.tmx` `ddafc1e5f97ebb2c28771f6653202209b9b42e35895e80418ceb9986d1665440`
- `Exolon/Resources/L05S25.tmx` `c242d2f868df0d6873263771118281ce461a611e423e1abcb552c120490ce89e`

**Hypothesis (not verified here):** TMX `nextLevel` / object layers vs `ORIGINAL_MECHANICS.md` — needs a dedicated TMX parser pass, not a missing-file issue.

### 3.2 pbxproj vs filesystem mismatch (integrity)

Resources **on disk and git-tracked but not in pbxproj** (not in `path =` refs, not in Resources build phase):

| File | Note |
|---|---|
| `bubble.gif` | sibling `bubble.png` **is** in pbx |
| `rocks.gif` | sibling `rocks.png` **is** in pbx |
| `turret_bullet.gif` | sibling `turret_bullet.png` **is** in pbx |
| `light.png` | no pbx entry |
| `ship_fire.png` | `ship_fire_frame.png` **is** in pbx |

`Info.plist` is referenced via `INFOPLIST_FILE`, not copied as a Resources-phase item (normal for app plists).

Resources build phase: 552 entries / **276 unique** (Debug+Release duplication). Unique names = 282 − 5 unreferenced − 1 plist = 276. **No pbx resource names missing from disk.**

### 3.3 Zone original PNGs

- `zone_007_original.png` … `zone_124_original.png`: **118** files present
- Missing originals: `zone_001`–`zone_006` (confirmed absent)
- Extra naming: `zone004_scenery.png`, `zone005_scenery.png` (not `zone_00N_original`)
- `zone_125_original.png` not present (zones are 000–124 in README; 125 TMX maps L01–L05)

Whether 001–006 use other art (`generated_terrain.png`, `tiles.png`, scenery) is **hypothesis**.

---

## 4. Version mismatch (confirmed)

| Source | Field | Value |
|---|---|---|
| `Exolon.xcodeproj/project.pbxproj` Debug+Release | `MARKETING_VERSION` | **0.5** |
| same | `CURRENT_PROJECT_VERSION` | **1** |
| `Exolon/Resources/Info.plist` | `CFBundleShortVersionString` | **0.3** |
| same | `CFBundleVersion` | **1** |

Because `GENERATE_INFOPLIST_FILE = NO`, the shipped short version is the plist **0.3** unless a later Xcode setting overrides (not visible here). `MARKETING_VERSION` 0.5 is therefore stale or unused — **confirmed inconsistency**, runtime winner not executable-tested on this host.

Info.plist SHA-256: `3e26005fbfc4c7a16ec8e94b3c1c9c8fa4f5e7c7d1ea71c55c7f79132c05bd75`.

---

## 5. Tests

**Product:** no `ExolonTests`, no XCTest target, no Swift test files. `README.md` describes in-game “test Invulnerability”, not a unit suite.

**Factory overlay (Linux-runnable, not the game):**

- `factory/tests/`: 7 `test_*.py` plus helpers (`postgres_restart_probe.py`, `run_disposable_exit.py`, `__init__.py`) — **10** files
- ~72 Python modules under `factory/`
- Repo also has `scripts/grok_verify.py` and Python linters (`ruff.toml`, `bandit.yaml`) — they do not compile SpriteKit

---

## 6. What can be statically checked on Linux x86_64

**Can (no Xcode/Swift/QEMU):**

- File inventories, SHA-256, git membership vs pbxproj name sets
- TMX well-formed XML, map attributes, object counts vs `ORIGINAL_MECHANICS.md` / `LEVEL_COMPILER_AUDIT.md`
- PNG/GIF magic-byte / dimension checks (`file`, Python PIL if installed)
- Plist XML parse; version-string comparison
- Factory Python: `pytest factory/tests`, ruff, bandit (overlay only)
- Grep of Swift for APIs (textual), not type-check

**Cannot on this host:**

- `swiftc` / SpriteKit / AppKit link
- `.app` bundle resource copy verification
- GameController / window / GPU
- QEMU macOS guest (binary absent)
- XCTest

Do not treat “pbx names match” as “Xcode copy bundle phase succeeds.”

---

## 7. Files that should stay byte-for-byte (audit constraint)

This change package forbids editing product/docs. Integrity baselines at HEAD `403eb132`:

| Path | SHA-256 |
|---|---|
| `README.md` | `4920502f0bf587be24ac0f86f515654f749aaea5c8e30d52fa0f02cbad730955` |
| `ORIGINAL_MECHANICS.md` | `363c424a994d50cc450b83b1d51e6e0a20ca0149039c6f31d24d779504e8c00d` |
| `LEVEL_COMPILER_AUDIT.md` | `3c0ff4ed2a326ff0f28f89ee3cb3f1e771898ef870b5310bd5bc7bd7b1e4cfc5` |
| `Exolon.xcodeproj/project.pbxproj` | `d7393eb6a52014c30f61f9a2ee46782ecbbea8d397b130806afb969886bbe81a` |

Also treat as freeze for this audit: all **18** Swift sources, all **125** TMX, all **153** PNG + **3** GIF, `Info.plist`. Any TMX/PNG rewrite would invalidate zone fidelity vs the 125-zone pipeline described in `README.md`.

`AGENTS.md` (SHA-256 `e3f72096a7543ae24011694d5dea5701419dac5bed107b02cadbc8a974592cc7`) is overlay contract, not game assets.

---

## 8. Integrity risk summary

| ID | Status | Risk |
|---|---|---|
| TMX 125/125 present + named in pbx | **Confirmed OK** | No missing zone maps |
| Swift 18/18 pbx ↔ fs | **Confirmed OK** | No orphan sources |
| Version 0.5 vs 0.3 | **Confirmed mismatch** | Marketing vs shipped plist |
| 5 resources unreferenced in pbx | **Confirmed** | GIFs/`light.png`/`ship_fire.png` may be dead or runtime-loaded by name (hypothesis: if code uses `Bundle` name without pbx copy, macOS app will miss them) |
| `zone_001`–`006` originals absent | **Confirmed** | Early zones rely on other tilesets |
| No Xcode scheme file | **Confirmed** | Open-by-folder may still build; CI without scheme is fragile |
| No product unit tests | **Confirmed** | Linux cannot close gameplay defects |
| Swift compile | **Not run** | Host cannot |

---

## 9. Suggested next static checks (out of this explorer’s write scope)

1. Parse all TMX object types vs `TMXLevelRuntime.swift` / `LevelObstacles.swift` string keys.
2. Grep Swift `SKTexture(imageNamed:)` / `Bundle` names vs pbx Resources unique set (would confirm whether the 5 unreferenced files are actually loaded).
3. Align or document `MARKETING_VERSION` vs `CFBundleShortVersionString` (fix is a product edit; not done here).
