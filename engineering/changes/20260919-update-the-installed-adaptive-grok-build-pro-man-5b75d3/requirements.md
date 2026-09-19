# Requirements

The installed managed payload must match the pinned source. Preserve original game content and prior audit data byte-for-byte. Run focused upstream regression tests against the actual consumer module and the route-selected verifier on Linux. Deliver a branch and PR; do not merge main without its applicable external gate.

The full verifier exposed a preexisting consumer packaging defect: installed API/PostgreSQL tests import test_execution_contracts and test_execution_service, which the installer omits. Restore those two unchanged test modules from the same pinned upstream source as supplemental verification support. This is not a change to runtime behavior or the 346 managed payload entries. No check is disabled.
