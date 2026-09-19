# Decisions

## 2026-09-20: Preserve upstream payload and restore its verification support

Apply the exact pinned upstream module and preserve all game content. The official installed PostgreSQL tests depend on two omitted upstream test modules, so include those modules unchanged rather than disabling checks; record them separately from installer-owned files.
