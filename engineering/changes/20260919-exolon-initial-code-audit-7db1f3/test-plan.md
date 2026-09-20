# Test plan — Exolon initial code audit

## Risk-based scenarios

| Priority | Scenario | Evidence available here |
| --- | --- | --- |
| P0 | 125 TMX present, parseable, in pbxproj, chained `nextLevel` | `linux_static_audit.py` |
| P0 | Cabin/teleport consume UP; suit toggle exists; mines/pistons skip if suit | source read (`GameScene.swift`, `Player.swift`) |
| P0 | No Swift/xcodebuild on this host | `command -v` in repo explorer |
| P1 | Action-marker vs TMX live objects | compiler dump + TMX inventory |
| P1 | Version 0.5 vs 0.3 | pbxproj + Info.plist |
| P2 | Factory `grok_verify --mode pr` | actual command output |

## Automated checks

- Unit: **none** for the SpriteKit product (no XCTest target).
- Integration: none for the game.
- Contract: factory overlay only.
- E2E: not possible (no macOS).
- Static analysis: `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/linux_static_audit.py`.
- Factory: `python3 scripts/grok_verify.py --mode pr` (profile `base`: git-diff-check, secret-scan; optional ruff/bandit). **Not a Swift build.**

## Manual checks (pending macOS)

```bash
xcodebuild -project Exolon.xcodeproj -target Exolon -configuration Debug build
```

Play scenarios (see final report): Zone 000 turret/rocks, 002 teleport, 007 mines, 008 beacon, 009 cabin, 024 stage bonus, 035 force field, analog-stick UP vs D-pad UP, death vs suit, process relaunch Zone 000.
