# Design: Exolon → Facebook Gaming Instant Games (HTML5)

**Date:** 2026-10-01
**Status:** IMPLEMENTATION — Phase 1 + Phase 2 complete (core engine + gameplay systems, TypeScript compiles clean)
**Risk:** high (complete platform rewrite)

## Technology choices (user-decided)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Rendering | HTML5 Canvas 2D | Sprite-based game, sufficient perf, simplest Facebook Gaming compat |
| Language | TypeScript | Native web, full FB SDK support, maintainable |
| Assets | Convert PNG→spritesheet+JSON, TMX→custom JSON | Standard web pipeline, smallest download |

## Architecture overview

```
index.html          ← FB Instant Games SDK loader, canvas, game loop
src/
  main.ts           ← entry point, composition root
  game/
    GameLoop.ts     ← requestAnimationFrame + FixedTickDriver (ported from Swift)
    GameState.ts    ← flow state, score, lives (ported from GameState.swift)
    Player.ts       ← physics, movement, collision (ported from Player.swift)
    LevelManager.ts ← level loading, zone transitions (ported from TMXLevelRuntime)
    Entities.ts     ← enemies, hazards, pickups (ported from LevelObstacles)
    Weapons.ts      ← blaster, grenade (ported from Weapons/)
    StageBoundary.ts← stage-end awards (ported from StageBoundaryLedger)
    LauncherBonus.ts← double launcher logic (ported from LauncherBonusState)
    InputManager.ts ← Keyboard + Gamepad API → InputState (replaces NSEvent/GC)
    Renderer.ts     ← Canvas 2D drawing, sprite sheets, TMX tile rendering
    AudioManager.ts ← Web Audio API SFX/music (new — no audio in current build)
    Persistence.ts  ← localStorage high score (replaces UserDefaults)
  fb/
    FBSDK.ts        ← Facebook Gaming SDK wrapper (auth, requests, leaderboards)
    InstantGames.ts ← FB Instant Games specific integration
  assets/
    sprites/        ← converted spritesheets + JSON atlases
    levels/         ← converted TMX → JSON
    audio/          ← converted sound effects
  types/
    GameTypes.ts    ← shared interfaces (matches change-spec.yaml contracts)
```

## Key mappings (Swift → TypeScript)

| Swift system | TypeScript equivalent | Notes |
|-------------|----------------------|-------|
| SKScene + SKNode | Canvas 2D draw calls | All rendering to single `<canvas>` |
| NSApplication | HTML5 page lifecycle | `visibilitychange`, `blur`/`focus` |
| GameController | Gamepad API | `navigator.getGamepads()` |
| UserDefaults | localStorage | Persist high score only |
| Bundle (TMX/PNG) | Fetch + bundled assets | Levels as JSON, sprites as spritesheets |
| Foundation JSON | JSON.stringify/parse | Identical semantics |
| NSLock + ring buffer | SharedArrayBuffer or single-threaded | Single-threaded browser = no lock needed |
| GameplayEventLog | Console + optional upload | No file system in browser |

## Facebook Gaming integration

- **FB Instant Games SDK** (`https://connect.facebook.net/en_US/fbinstant.6.2.js`)
- **Auth:** `FBInstant.initializeAsync()` → player ID
- **Game requests:** `FBInstant.shareAsync()` for invites
- **Leaderboards:** `FBInstant.getLeaderboardAsync()` + `setScoreAsync()`
- **Loading progress:** `FBInstant.setLoadingProgress()`
- **Start game:** `FBInstant.startGameAsync()`

## Implementation phases

1. **Phase 1 — Core engine:** GameLoop, GameState, InputManager, Renderer (empty canvas)
2. **Phase 2 — Gameplay:** Player, Weapons, Entities, LevelManager (logic only, no visuals)
3. **Phase 3 — Visuals:** Sprite rendering, TMX tile rendering, HUD, animations
4. **Phase 4 — FB integration:** SDK wrapper, auth, leaderboards, sharing
5. **Phase 5 — Polish:** Audio, touch controls, optimization, testing

## Risks

| Risk | Mitigation |
|------|-----------|
| Canvas 2D perf with 125 zones + many sprites | Sprite batching, offscreen canvas for static tiles |
| Facebook SDK API changes | Abstract behind FBSDK.ts, test against current API |
| Asset conversion fidelity | Validate converted assets against original TMX/PNG |
| No audio in original build | Web Audio API from scratch — scope separately |
| Touch controls for mobile Facebook | Virtual joystick + buttons — design separately |

## Non-goals (out of scope for this change)

- macOS native build changes
- iOS native build changes
- Wave A/B/C/D/E1 product changes (already delivered)
- Sound design or music composition
- Facebook moderation/compliance review

## Acceptance criteria (proposed)

- AC-FB-001: Game launches in Facebook Gaming Instant Games iframe
- AC-FB-002: All 125 zones load and play with original mechanics
- AC-FB-003: Keyboard + gamepad input works; touch controls functional
- AC-FB-004: Facebook auth + leaderboard integration green
- AC-FB-005: No SpriteKit/AppKit/Foundation dependencies in product bundle
