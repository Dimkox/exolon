# Decisions

## 2026-09-20: Preserve upstream payload and restore its verification support

Apply the exact pinned upstream module and preserve all game content. The official installed PostgreSQL tests depend on two omitted upstream test modules, so include those modules unchanged rather than disabling checks; record them separately from installer-owned files.

## 2026-09-20: Full audit retracts cabin P0 and appends, never overwrites, prior evidence

The only P0 of the 19.09 audit (capsule exclusion cuts the cabin floor) was refuted by a per-cell re-measurement of L01S10 with a mutation control (shifting the exclusion 32/48 px does cut floor cells; the shipped formula does not). Full-audit evidence was written under `-fullaudit` filenames so the dated first-pass evidence stays intact, and correction banners were added to the live report/backlog instead of rewriting them. Swift parsing on Linux (`swiftc -frontend -parse`) is adopted as the product's strongest static gate; typecheck/build remain macOS-only.
