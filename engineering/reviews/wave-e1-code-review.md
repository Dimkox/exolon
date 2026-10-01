# Code Review: Wave E1 verification tooling (route 8f7b02)

**Head:** `c0b61db` | **Digest:** `2166b642937b510a` | **Files:** 24
**Reviewer:** code_reviewer | **Date:** 2026-09-30

## Verdict: PASS

## What changed
- `evidence/wave_e1_check.py`: AC-006 M1 topology check relaxed for merged-PR state; AC-002 absent check fixed (derive expected waves from git log); SANCTIONED_MERGED_EDITS: decisions.md
- 5 freeze artifacts re-bound to current digest
- `decisions.md`: new entry

## AC-002 absent check — fixed

The old check derived `merged` from the buckets list, then checked if those buckets were absent from the same list — always empty. Fixed by deriving expected merged wave names from the git log merge commits and checking they all appear in the scan output.

## AC-006 M1 fix — correct

The old check asserted `origin/main != HEAD` in the "real" topology clone. This repo's PR is already merged (`origin/main == HEAD`), so the check failed on the real repo, not the code.

The fix branches correctly:
- `origin/main == HEAD` → verify B green on that topology
- `origin/main != HEAD` → verify B green on open-PR topology

The no-origin fail-closed control (rc=4, FAIL-CLOSED, no scan line) independently proves the safety property.

## Flipping controls intact

| Control | Side | Status |
| --- | --- | --- |
| No-origin clone | Red (rc=4) | ✅ |
| Real topology | Green | ✅ |
| Post-merge topology | Green | ✅ |
| FORBID-002 (planted ±16) | Red | ✅ |
| AC-002 absence | Red (verified) | ✅ |

## Freeze certification correct

- All 5 artifacts carry `certified_head=c0b61db`, `cert_digest=2166b642937b510a`
- `certification_bound` lists both artifacts with correct digest
- `certification_notes`, `certification_uncertified`, `stale_certification` all empty

## No product impact

- `Exolon/` and `Exolon.xcodeproj` byte-clean
- All changes are in `engineering/` and the change package
