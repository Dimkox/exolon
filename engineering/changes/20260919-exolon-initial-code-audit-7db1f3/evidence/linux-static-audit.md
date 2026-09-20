# Linux static audit evidence

Host: Linux x86_64. This is **not** an `xcodebuild` or gameplay result.

## Integrity

- TMX on disk: 125 / 125
- TMX missing on disk: none
- TMX missing from pbxproj: none
- Extra TMX in pbxproj: none
- Swift sources: 18; missing from pbxproj: none
- Info.plist CFBundleShortVersionString: 0.3
- pbxproj MARKETING_VERSION: ['0.5']
- Resource files under Exolon/Resources: 282
- Missing zone original PNGs (007-124 expected): none
- Extra zone original PNGs: none
- Missing image references from TMX: [{'level': 'L01S04', 'source': '../images/tiles.gif'}]
- Non-35x24@16 maps: none
- Maps without vitorc spawn: none
- nextLevel chain breaks: none
- Odd teleport counts (not 0 or 2): none
- Capsule/changing-room maps: ['L01S10']
- Base64 collision layers (solid count not decoded here): ['L01S01', 'L01S02', 'L01S03', 'L01S04']

## Object names

- `source_marker`: 127
- `vitorc`: 125
- `teleport`: 70
- `mine`: 53
- `ammo_pack`: 48
- `piston`: 46
- `grenade_pack`: 38
- `turret`: 37
- `bubble_creator`: 31
- `rocket`: 29
- `incubator`: 22
- `double_launcher`: 19
- `radar`: 12
- `ship`: 7
- `gate`: 6
- `light_ceiling`: 3
- `light_floor`: 3
- `ship_fire`: 2
- `capsule`: 1
- `cocoon`: 1

## sourceBlock values

- `blk_teleportGate`: 66
- `blk_mine`: 50
- `blk_box_white`: 46
- `blk_anim_pump`: 45
- `blk_box_yellow`: 35
- `blk_anim_swarm`: 28
- `blk_waggon`: 24
- `blk_tower_rocket`: 23
- `blk_birthpod`: 21
- `blk_blinker`: 19
- `blk_double_barrel`: 18
- `blk_gunMachine_BOTTOM`: 18
- `blk_gunMachine_TOP`: 18
- `blk_gunMachine1`: 15
- `blk_beacon_base`: 13
- `blk_control_beacon`: 13
- `blk_beam_down`: 10
- `blk_beam_up`: 10
- `blk_tower_dish`: 10
- `blk_mushroom`: 9
- `blk_gate_green`: 6
- `blk_ship`: 6
- `blk_changing_room`: 5
- `blk_stage_end`: 5
- `blk_topdown_electro`: 2

## Runtime classification (from TMXLevelRuntime.swift switch)

- `scenery:vitorc`: 125
- `live:teleport`: 70
- `live:mine`: 53
- `unhandled`: 51
- `live:ammo_pack`: 48
- `live:piston`: 46
- `live:grenade_pack`: 38
- `live:turret`: 37
- `live:bubble_creator`: 31
- `live:rocket`: 29
- `live:incubator`: 22
- `live:beam_`: 20
- `live:double_launcher`: 19
- `noop:blinker`: 19
- `live:beacon_base`: 13
- `live:control_beacon`: 13
- `live:radar`: 12
- `scenery:ship`: 7
- `live:gate`: 6
- `live:stage_end`: 5
- `live:changing_room`: 4
- `scenery:light_ceiling`: 3
- `scenery:light_floor`: 3
- `noop:topdown_electro`: 2
- `scenery:ship_fire`: 2
- `live:capsule`: 1
- `live:cocoon`: 1

Unhandled/unknown objects: 51

| level | name | sourceBlock | x | y | runtime |
| --- | --- | --- | --- | --- | --- |
| L01S23 | source_marker | blk_waggon | 128 | 208 | unhandled |
| L01S23 | source_marker | blk_waggon | 224 | 208 | unhandled |
| L01S24 | source_marker | blk_gunMachine_BOTTOM | 400 | 272 | unhandled |
| L01S24 | source_marker | blk_waggon | 224 | 32 | unhandled |
| L02S01 | source_marker | blk_mushroom | 176 | 240 | unhandled |
| L02S01 | source_marker | blk_mushroom | 256 | 240 | unhandled |
| L02S02 | source_marker | blk_waggon | 176 | 224 | unhandled |
| L02S02 | source_marker | blk_waggon | 272 | 224 | unhandled |
| L02S08 | source_marker | blk_gunMachine_BOTTOM | 160 | 272 | unhandled |
| L02S13 | source_marker | blk_waggon | 96 | 208 | unhandled |
| L02S13 | source_marker | blk_waggon | 192 | 208 | unhandled |
| L02S19 | source_marker | blk_mushroom | 416 | 240 | unhandled |
| L02S21 | source_marker | blk_gunMachine_BOTTOM | 384 | 128 | unhandled |
| L02S22 | source_marker | blk_gunMachine_BOTTOM | 304 | 288 | unhandled |
| L02S22 | source_marker | blk_gunMachine_BOTTOM | 304 | 128 | unhandled |
| L02S24 | source_marker | blk_waggon | 80 | 240 | unhandled |
| L03S04 | source_marker | blk_gunMachine_BOTTOM | 192 | 176 | unhandled |
| L03S04 | source_marker | blk_mushroom | 160 | 16 | unhandled |
| L03S04 | source_marker | blk_mushroom | 256 | 16 | unhandled |
| L03S05 | source_marker | blk_waggon | 160 | 128 | unhandled |
| L03S08 | source_marker | blk_gunMachine_BOTTOM | 400 | 256 | unhandled |
| L03S12 | source_marker | blk_gunMachine_BOTTOM | 384 | 256 | unhandled |
| L03S16 | source_marker | blk_waggon | 176 | 224 | unhandled |
| L03S20 | source_marker | blk_mushroom | 288 | 224 | unhandled |
| L03S22 | source_marker | blk_gunMachine_BOTTOM | 400 | 256 | unhandled |
| L03S24 | source_marker | blk_gunMachine_BOTTOM | 272 | 256 | unhandled |
| L04S01 | source_marker | blk_waggon | 32 | 208 | unhandled |
| L04S01 | source_marker | blk_waggon | 320 | 240 | unhandled |
| L04S04 | source_marker | blk_waggon | 160 | 208 | unhandled |
| L04S04 | source_marker | blk_gunMachine_BOTTOM | 160 | 96 | unhandled |
| L04S04 | source_marker | blk_waggon | 288 | 48 | unhandled |
| L04S07 | source_marker | blk_gunMachine_BOTTOM | 368 | 256 | unhandled |
| L04S16 | source_marker | blk_mushroom | 368 | 96 | unhandled |
| L04S16 | source_marker | blk_mushroom | 448 | 96 | unhandled |
| L04S17 | source_marker | blk_waggon | 304 | 240 | unhandled |
| L04S17 | source_marker | blk_waggon | 384 | 240 | unhandled |
| L04S20 | source_marker | blk_waggon | 96 | 208 | unhandled |
| L04S20 | source_marker | blk_waggon | 176 | 208 | unhandled |
| L04S20 | source_marker | blk_waggon | 256 | 208 | unhandled |
| L04S23 | source_marker | blk_gunMachine_BOTTOM | 400 | 80 | unhandled |
| L04S23 | source_marker | blk_gunMachine_BOTTOM | 400 | 256 | unhandled |
| L05S02 | source_marker | blk_waggon | 224 | 224 | unhandled |
| L05S02 | source_marker | blk_waggon | 320 | 224 | unhandled |
| L05S08 | source_marker | blk_gunMachine_BOTTOM | 160 | 272 | unhandled |
| L05S13 | source_marker | blk_waggon | 96 | 208 | unhandled |
| L05S13 | source_marker | blk_waggon | 192 | 208 | unhandled |
| L05S19 | source_marker | blk_mushroom | 416 | 240 | unhandled |
| L05S21 | source_marker | blk_gunMachine_BOTTOM | 384 | 128 | unhandled |
| L05S22 | source_marker | blk_gunMachine_BOTTOM | 304 | 288 | unhandled |
| L05S22 | source_marker | blk_gunMachine_BOTTOM | 304 | 128 | unhandled |
| L05S24 | source_marker | blk_waggon | 80 | 240 | unhandled |

## Compiler action count vs live TMX objects (heuristic)

Original type 4 flashing cells are excluded from the expected live count. A large gap is a candidate missing runtime mapping, not proof of a crash.

| level | zone | live TMX | compiler actions | non-flash | objects |
| --- | --- | --- | --- | --- | --- |
| L01S14 | 13 | 3 | 6 | 6 | {'vitorc': 1, 'incubator': 1, 'double_launcher': 1, 'piston': 1} |
| L01S15 | 14 | 6 | 17 | 9 | {'vitorc': 1, 'teleport': 2, 'double_launcher': 1, 'piston': 3} |
| L01S21 | 20 | 5 | 8 | 8 | {'vitorc': 1, 'double_launcher': 1, 'bubble_creator': 2, 'piston': 2} |
| L01S24 | 23 | 3 | 8 | 8 | {'vitorc': 1, 'turret': 1, 'source_marker': 2, 'piston': 1, 'rocket': 1} |
| L02S03 | 27 | 2 | 7 | 7 | {'vitorc': 1, 'ammo_pack': 1, 'grenade_pack': 1} |
| L02S04 | 28 | 2 | 9 | 9 | {'vitorc': 1, 'double_launcher': 1, 'incubator': 1, 'ship': 1} |
| L02S05 | 29 | 4 | 15 | 7 | {'vitorc': 1, 'turret': 1, 'teleport': 2, 'ammo_pack': 1} |
| L02S08 | 32 | 5 | 17 | 9 | {'vitorc': 1, 'mine': 2, 'turret': 1, 'source_marker': 1, 'teleport': 2} |
| L02S09 | 33 | 5 | 16 | 8 | {'vitorc': 1, 'ammo_pack': 1, 'grenade_pack': 1, 'teleport': 2, 'double_launcher': 1} |
| L02S14 | 38 | 5 | 16 | 8 | {'vitorc': 1, 'teleport': 2, 'bubble_creator': 2, 'double_launcher': 1} |
| L02S20 | 44 | 4 | 7 | 1 | {'vitorc': 1, 'rocket': 2, 'grenade_pack': 1, 'gate': 1} |
| L02S21 | 45 | 3 | 15 | 7 | {'vitorc': 1, 'teleport': 2, 'turret': 1, 'source_marker': 1} |
| L02S22 | 46 | 6 | 14 | 14 | {'vitorc': 1, 'turret': 2, 'source_marker': 2, 'ammo_pack': 1, 'grenade_pack': 1, 'bubble_creator': 2} |
| L02S23 | 47 | 5 | 8 | 8 | {'vitorc': 1, 'incubator': 1, 'turret': 1, 'piston': 3} |
| L02S24 | 48 | 3 | 16 | 8 | {'vitorc': 1, 'source_marker': 1, 'teleport': 2, 'double_launcher': 1} |
| L03S01 | 50 | 10 | 13 | 13 | {'vitorc': 1, 'mine': 6, 'source_marker': 4} |
| L03S02 | 51 | 4 | 13 | 1 | {'vitorc': 1, 'source_marker': 2, 'gate': 2} |
| L03S03 | 52 | 5 | 16 | 8 | {'vitorc': 1, 'teleport': 2, 'double_launcher': 1, 'bubble_creator': 2} |
| L03S04 | 53 | 3 | 7 | 7 | {'vitorc': 1, 'ammo_pack': 1, 'grenade_pack': 1, 'turret': 1, 'source_marker': 3} |
| L03S06 | 55 | 6 | 2 | 2 | {'vitorc': 1, 'rocket': 4, 'grenade_pack': 1, 'piston': 1} |
| L03S08 | 57 | 3 | 9 | 9 | {'vitorc': 1, 'turret': 1, 'source_marker': 1, 'grenade_pack': 1, 'ammo_pack': 1} |
| L03S12 | 61 | 3 | 18 | 7 | {'vitorc': 1, 'teleport': 2, 'source_marker': 4, 'turret': 1} |
| L03S24 | 73 | 1 | 5 | 5 | {'vitorc': 1, 'turret': 1, 'source_marker': 1} |
| L04S03 | 77 | 3 | 16 | 8 | {'vitorc': 1, 'teleport': 2, 'double_launcher': 1} |
| L04S04 | 78 | 4 | 8 | 8 | {'vitorc': 1, 'mine': 3, 'source_marker': 3, 'turret': 1} |
| L04S07 | 81 | 6 | 18 | 10 | {'vitorc': 1, 'teleport': 2, 'piston': 2, 'mine': 1, 'turret': 1, 'source_marker': 1} |
| L04S13 | 87 | 3 | 9 | 9 | {'vitorc': 1, 'ammo_pack': 1, 'double_launcher': 2} |
| L04S21 | 95 | 5 | 18 | 10 | {'vitorc': 1, 'teleport': 2, 'double_launcher': 1, 'ammo_pack': 1, 'grenade_pack': 1} |
| L04S23 | 97 | 4 | 14 | 14 | {'vitorc': 1, 'ammo_pack': 1, 'grenade_pack': 1, 'turret': 2, 'source_marker': 2} |
| L05S03 | 102 | 2 | 7 | 7 | {'vitorc': 1, 'ammo_pack': 1, 'grenade_pack': 1} |
| L05S04 | 103 | 2 | 9 | 9 | {'vitorc': 1, 'double_launcher': 1, 'incubator': 1, 'ship': 1} |
| L05S05 | 104 | 4 | 15 | 7 | {'vitorc': 1, 'turret': 1, 'teleport': 2, 'ammo_pack': 1} |
| L05S08 | 107 | 5 | 17 | 9 | {'vitorc': 1, 'mine': 2, 'turret': 1, 'source_marker': 1, 'teleport': 2} |
| L05S09 | 108 | 5 | 16 | 8 | {'vitorc': 1, 'ammo_pack': 1, 'grenade_pack': 1, 'teleport': 2, 'double_launcher': 1} |
| L05S14 | 113 | 5 | 16 | 8 | {'vitorc': 1, 'teleport': 2, 'bubble_creator': 2, 'double_launcher': 1} |
| L05S20 | 119 | 4 | 7 | 1 | {'vitorc': 1, 'rocket': 2, 'grenade_pack': 1, 'gate': 1} |
| L05S21 | 120 | 3 | 15 | 7 | {'vitorc': 1, 'teleport': 2, 'turret': 1, 'source_marker': 1} |
| L05S22 | 121 | 6 | 14 | 14 | {'vitorc': 1, 'turret': 2, 'source_marker': 2, 'ammo_pack': 1, 'grenade_pack': 1, 'bubble_creator': 2} |
| L05S23 | 122 | 5 | 8 | 8 | {'vitorc': 1, 'incubator': 1, 'turret': 1, 'piston': 3} |
| L05S24 | 123 | 3 | 16 | 8 | {'vitorc': 1, 'source_marker': 1, 'teleport': 2, 'double_launcher': 1} |
