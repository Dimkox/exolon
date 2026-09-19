# Repository and task analysis

Both upstream snapshots own 346 paths; no additions, removals or installed divergences. The sole changed payload is factory/src/adaptive_factory/landing_http.py (+37/-4). The 304 original game files are outside managed scope. Apply the canonical Git blob, preserving AGENTS newline bytes and all runtime/audit data. Existing-target installer mode is read-only.

The full verifier exposed a preexisting consumer packaging defect: installed API/PostgreSQL tests import test_execution_contracts and test_execution_service, which the installer omits. Restore those two unchanged test modules from the same pinned upstream source as supplemental verification support. This is not a change to runtime behavior or the 346 managed payload entries. No check is disabled.
