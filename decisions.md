# Decisions

## 2026-09-20: Preserve upstream payload and restore its verification support

Apply the exact pinned upstream module and preserve all game content. The official installed PostgreSQL tests depend on two omitted upstream test modules, so include those modules unchanged rather than disabling checks; record them separately from installer-owned files.

## 2026-09-20: Full audit retracts cabin P0 and appends, never overwrites, prior evidence

The only P0 of the 19.09 audit (capsule exclusion cuts the cabin floor) was refuted by a per-cell re-measurement of L01S10 with a mutation control (shifting the exclusion down by 33 or 48 px does cut floor cells, while 32 px leaves its lower bound exactly on the floor top and does not; the shipped formula does not). Full-audit evidence was written under `-fullaudit` filenames so the dated first-pass evidence stays intact, and correction banners were added to the live report/backlog instead of rewriting them. Swift parsing on Linux (`swiftc -frontend -parse`) was adopted as the strongest static gate at that pass; typecheck/build remain macOS-only. Superseded the same day, see the next entry.

## 2026-09-20: Product code executes on Linux for the loader path; TMX parsing must use a real XML parser

`Exolon/GameCore/Levels/TMXMapLoader.swift` is compiled and run on this host behind a one-line `CoreGraphics` shim (`@_exported import Foundation`) plus `import FoundationXML`, with the delta to the repository file asserted byte-exact (`sed '2d'` restores it): 125/125 shipped maps load through real product code, and malformed-input behaviour (`compression` -> throw, empty map -> playable void, `y="17o"` -> 0, layer/objectgroup property leak into map properties) is now observed instead of read. It replaces "Swift parse is the ceiling" as the strongest Linux gate; SpriteKit-bound code, typecheck, build and gameplay stay macOS-only.

Consequence for every future measurement in this repo: TMX `<object>` elements are parsed with `xml.etree`, never with a regex, and never with attribute names guessed — `height=`, not `h=`. A regex pass in this session reported 97 markers instead of 127 and "3 lethal pistons" instead of 1 lethal + 2 edge-touching + 43 below the player's feet; the committed self-checking tool `evidence/v3_measurements.py` (rc=0 iff the report matches, 11 flipping controls) exists to make that class of error visible instead of plausible.
