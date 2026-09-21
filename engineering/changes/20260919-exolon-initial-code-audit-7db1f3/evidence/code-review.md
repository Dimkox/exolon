# Code review — Exolon initial audit package

**Verdict (audit package quality): pass**\
**Would record `grok_review` / `code_review`: pass**

Route `7db1f3f0b126`, intent `review`, `write_agent=null`. Product HEAD `403eb1322d645154307ce11bf91be89e2082e1dd`. Independent of architect/docs/repo reports; claims spot-checked against Swift/TMX and git.

This is **not** a Swift/xcodebuild review. Host cannot compile or play. Pending macOS checks stay pending.

---

## 1. Frozen product paths

`git diff 403eb1322d645154307ce11bf91be89e2082e1dd -- Exolon/ Exolon.xcodeproj/ README.md ORIGINAL_MECHANICS.md LEVEL_COMPILER_AUDIT.md` is empty.

Worktree product HEAD is that commit (`Import Exolon Step 9…`). Untracked work is under `engineering/`, `.grok-stack/`, factory overlay — not frozen game bytes.

FORBID-001 / INV-001 hold for this tree.

---

## 2. Honesty of confirmed vs hypothesis vs Step 9 unfinished

`engineering/reports/exolon-initial-audit.md` defines tags (§2) and uses them in the P0 table (§10).

Spot-checks that match source:

| Claim | Source | Tag in report |
| --- | --- | --- |
| Cabin exclusion `minY - 16` vs comment “16 px above” | `TMXLevelRuntime.swift:297-306` | confirmed formula; play-through as hypothesis |
| Stick Y only `.menuUp` | `GamepadInput.swift:64-72` | confirmed |
| Contextual UP consumes jump | `GameScene.swift:229-253`, `Player.swift:252-258` | matches README checkpoint |
| `sourceHazards` never filled | declared `TMXLevelRuntime.swift:28`, only read `GameScene.swift:575` | confirmed |
| `stageExitMarkers` write-only | append `:370`, no other Swift readers | confirmed |
| Stage-end comment “dormant” vs live `guard [24,49,…]` | `GameScene.swift:622-631` | unfinished / stale comment |
| Exo ammo −1 per press, second bullet +12 Y | `GameScene.swift:346-351` | confirmed; 2-ammo original as hypothesis |
| Double-launcher bonus sets `isActive=false` | `LevelObstacles.swift:718-723` | confirmed vs original |
| `beam_` both up and down spawn fields | `TMXLevelRuntime.swift:356-360` | confirmed; 50-hit play as hypothesis |
| Keyboard map / Option via `flagsChanged` | `GameView.swift:17-67` | confirmed |
| Versions 0.5 vs 0.3, `GENERATE_INFOPLIST_FILE=NO` | `project.pbxproj:1420-1424`, `Info.plist:17-18` | confirmed |
| Title STEP 10 vs window Step 9 | `GameScene.swift:832`, `AppDelegate.swift:16` | confirmed |
| 125 TMX | disk + `linux-static-audit.json` summary | confirmed |
| Capsule only `L01S10`, tiledRect | `L01S10.tmx` object id 5 | confirmed |

Unfinished original (BOTTOM guns, rocket towers as destructibles, swing bubbles, no pursuer) is labeled **недоделка**, not ZIP regression. That matches `source_marker` default ignore (`TMXLevelRuntime.swift:409-413`) and unhandled census 51 (`blk_waggon` 24, `BOTTOM` 18, `blk_mushroom` 9).

§11 keeps macOS playtests pending. §3 states no `xcodebuild`/`swiftc`.

---

## 3. grok_verify FAIL is factory overlay, not xcodebuild

Receipt `.grok-stack/runtime/receipts/7db1f3f0b126/verification.json`:

- Overall fail.
- `git-diff-check` fail: `pr-base-unavailable` / “delivery verification requires a locally resolvable PR target”.
- `factory-postgres-exit` fail (`status: fail`, `summary: exit=1`).
- Python ruff/bandit/unit/source-stability pass; architecture SKIP.

Report §1 table matches this and says **not** an xcodebuild result. Factory unit pass is correctly scoped as overlay, not a game build.

Nit (does not fail the package): §1 attributes postgres-exit mainly to missing disposable Postgres. Receipt stderr also shows `ModuleNotFoundError: factory.tests.test_execution_contracts` and import failure of `test_postgres_integration`. FAIL is still honest.

---

## 4. Minor notes (non-blocking)

- `blk_changing_room` count is 5 in TMX properties vs `live:changing_room: 4` because zone 009 uses named `capsule` plus a marker; report already uses 1+4=5.
- `git-diff-check` stdout summary “3/3 checks passed” while status is fail — overlay quirk; report still records FAIL.
- Reviewer did not re-run `linux_static_audit.py`; counts were cross-checked against JSON + `ls Exolon/Resources/*.tmx` = 125.

---

## 5. Contracts / AC

AC-001 frozen paths: pass.\
AC-003 125 TMX + pbx + versions: pass vs JSON/source.\
AC-004/005 Russian report + backlog exist and keep pending macOS.\
AC-006 verify FAIL recorded.\
AC-008 gameplay/build blocked.

No product edits; no claim of playable Linux binary.

---

## 6. grok_review recommendation

Record **code_review: pass** for this *audit package*. Do not treat this as a pass of Exolon gameplay or Swift compilation.
