# Test plan — wave B

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Bounded AC-001: maps with a Collision top within ±16 px of the marker feet spawn delta-0 on it; no map's spawn moves >16 px vs marker; no-surface maps enumerated unmoved; old rule reproduces the 37/59/29 marker-vs-surface control | `wave_b_check.py::spawn_ground_all_maps` |
| P0 | 46 pistons on 27 maps: world-bottom ≤ player foot line (lethal band reached); old anchor formula FAILS the same check (control) | `wave_b_check.py::piston_anchor_all_pistons` |
| P0 | Beam pairs: one 25-HP pool per pair; destruction removes both segments; per-map sum check over all beam maps | `wave_b_check.py::beam_shared_hp_all_maps` |
| P1 | Bullet culling bound ≥ 544 + bullet width (derived, not literal); transition trigger x>510 unchanged | `wave_b_check.py::bullet_cull_bounds` |
| P1 | Reverted-fix controls fail; truncated/garbage TMX fixture fails loudly (meter self-check) | `wave_b_check.py::controls_flip` |

## Automated checks
- Unit: surface query on synthetic collision grids (edge cases: gap column, full column, y=0 row).
- Integration: all-125-map meters (stdlib Python), Swift loader-harness where formulas were ported.
- Contract: n/a (no wire contract in wave B).
- E2E: manual macOS spot (first map of each defect class: spawn land, piston kill, beam shot-down,
  right-edge shot) — record in PR.
- Static: `swiftc -frontend -parse`; `grok_verify --mode pr`.

## Manual checks
- Play L01S01-ish spawn map and one beam map on macOS build after rebase; no stuck-on-spawn,
  no double-HP beam surprise.
