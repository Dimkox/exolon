# Rollback plan — Exolon initial code audit

## Trigger conditions

Product tree must remain byte-identical to import HEAD `403eb1322d645154307ce11bf91be89e2082e1dd` for `Exolon/`, `Exolon.xcodeproj/`, `README.md`, `ORIGINAL_MECHANICS.md`, `LEVEL_COMPILER_AUDIT.md`.

## Application rollback

No product change. Discarding `engineering/` and `.grok-stack/runtime/` returns to import-only tree.

## Data recovery / forward-fix

N/A.

## Verification after rollback

`git status` on frozen paths is clean.
