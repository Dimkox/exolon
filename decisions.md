# Decisions

## 2026-09-20: Preserve upstream payload and restore its verification support

Apply the exact pinned upstream module and preserve all game content. The official installed PostgreSQL tests depend on two omitted upstream test modules, so include those modules unchanged rather than disabling checks; record them separately from installer-owned files.

## 2026-09-20: Full audit retracts cabin P0 and appends, never overwrites, prior evidence

The only P0 of the 19.09 audit (capsule exclusion cuts the cabin floor) was refuted by a per-cell re-measurement of L01S10 with a mutation control (shifting the exclusion down by 33 or 48 px does cut floor cells, while 32 px leaves its lower bound exactly on the floor top and does not; the shipped formula does not). Full-audit evidence was written under `-fullaudit` filenames so the dated first-pass evidence stays intact, and correction banners were added to the live report/backlog instead of rewriting them. Swift parsing on Linux (`swiftc -frontend -parse`) was adopted as the strongest static gate at that pass; typecheck/build remain macOS-only. Superseded the same day, see the next entry.

## 2026-09-20: Product code executes on Linux for the loader path; TMX parsing must use a real XML parser

`Exolon/GameCore/Levels/TMXMapLoader.swift` is compiled and run on this host behind a one-line `CoreGraphics` shim (`@_exported import Foundation`) plus `import FoundationXML`, with the delta to the repository file asserted byte-exact (`sed '2d'` restores it): 125/125 shipped maps load through real product code, and malformed-input behaviour (`compression` -> throw, empty map -> playable void, `y="17o"` -> 0, layer/objectgroup property leak into map properties) is now observed instead of read. It replaces "Swift parse is the ceiling" as the strongest Linux gate; SpriteKit-bound code, typecheck, build and gameplay stay macOS-only.

Consequence for every future measurement in this repo: TMX `<object>` elements are parsed with `xml.etree`, never with a regex, and never with attribute names guessed — `height=`, not `h=`. A regex pass in this session reported 97 markers instead of 127 and "3 lethal pistons" instead of 1 lethal + 2 edge-touching + 43 below the player's feet; the committed self-checking tool `evidence/v3_measurements.py` (rc=0 iff the report matches, 11 flipping controls) exists to make that class of error visible instead of plausible.

## 2026-09-21: A self-checking tool must pin what the platform actually emits, and prove its green is causal

`evidence/release_layer_check.py` (P1-11) graduating from draft to committed caught two defects that
only a tool-with-controls can catch in itself. (1) The draft pinned `ReferencedContainer =
"Container:Exolon.xcodeproj"`, but Xcode writes the lowercase `container:` form; because every
synthetic fixture reused the same helper, all controls were green against a value Xcode cannot
resolve — so the casing pin is now a literal expectation and `container_prefix_casing_rejected` must
turn the capitalised form red on every reference. The same class killed the draft's project name
(`Exolon.xcodeproj.xcodeproj`), which is why derived-from-glob values are never accepted as pins.
(2) Once the fix is on disk, a "dry-run the post-fix plan" control degenerates into comparing the
tree with itself; it was replaced by `undo_fix_is_red`, which reverts each of the four plan halves
in memory and requires each to redden only its own ACs and the full revert to equal their union.
Any post-fix verifier that wants to stay meaningful after its own fix lands needs that inversion,
not a rehearsal fixture.

## 2026-09-24: The ring is the backlog, the wire is JSON-lines, and the file lives outside the clone

Wave A's gameplay event log measured three shapes before committing to one: a single-slot batch handoff from producer to writer silently lost 250 of 26 873 events (99.1 %) with no crash, a `DispatchSourceTimer` whose handler called the `queue.sync` wrapper deadlocked dispatch outright, and `beginTick` pre-incrementing made the first tick 2 - so the shipped core appends one 24-byte record into a 65 536-slot ring under `NSLock` (measured 55-68 ns/event = 0.020-0.025 % of a 16.67 ms step at the worst credible 60 events/tick), the ring itself is the file backlog with a consumer cursor and a counted drop, and the drain (measured ~296 000 events/s formatting to JSON-lines) never runs through the sync wrapper. Formatting stays on the drain thread and the wire is JSON-lines rather than the compact positional format the measurements would have preferred, because three consumers (`json.loads`, `tail -f`, the in-game F1 tail) must read one self-describing record with no bespoke parser - which costs ~1.1 µs/event off the frame path and buys an enforceable contract file. The directory is `$TMPDIR/exolon/` rather than `~/Library/Caches` because this route's fingerprint-bound receipts count any untracked file inside the clone as a tree change, so a log written under the working tree silently invalidates its own evidence.

## 2026-09-24: A probe extension is guarded by diffing its own emitted keys against git HEAD

`engineering/runbooks/macos-probe.sh` gained Track A archive inspection, a Track-B gate, a flush
barrier and out-of-tree build roots without losing a single consumer: `macos_handout_check.py`
extracts the emit-keys of `git show HEAD:<probe>` and requires every one of them to still be
emitted (46 before, 127 after, zero lost (re-measured on head `84b7813`: the D-2 draft said 126)), because measurement M-7 proved that renaming one
detector token (`EXOLON_FORBIDDEN_ARGV`) reddens exactly one AC of the merged verifier - a guard
string is product surface, not prose. The same rule applies to the tool's own assertions: a shell
probe must pass operator-shaped patterns to `grep -e` (a pattern starting with `-` is parsed as an
option), a checker that asserts on the environment must compare against its own baseline (the agent
host exports `*_TOKEN` names), and a control that "mutates" a shipped file must mutate a string in
memory, never the file.

## 2026-09-25: When a merged verifier's premise ends, declare the consequence instead of editing it

Wave D repaid PR #3's deferred `ENABLE_HARDENED_RUNTIME`, which reddened exactly one AC
(`hardened_runtime_key_count`) — and silently made one of PR #3's 29 controls
(`hardened_key_mutation_detected`) unsatisfiable: it installs the key with
`replace(anchor, anchor + KEY, 1)` and demands asymmetry, but on a repaid tree that insert is a
duplicate of an equal setting, so the parsed buildSettings dicts stay equal forever. The two
temptations were both wrong: editing PR #3's immutable package to tidy the number, and reporting
the red as "expected" while leaving the dead control unmentioned. Wave D instead measured the
whole diff (re-measuring with the two lines stripped in memory proves nothing else moved), declared
the dead control in wave D's own registry (`evidence/cutover.md` +
`DECLARED_CUTOVER_CONTROLS`), and made the checker require that no *other* control may stop
flipping in either phase. Related: a declared-expected set can overstate reality — FORBID-002's
second member `hardened_deferral_recorded` cannot redden without rewriting the dated package it
reads, so the enforceable claim became "no red outside the set + each member live via the merged
checker's own revert path", recorded as a deviation rather than a silent narrowing.
