# Verification plan

1. Run the three upstream landing failover/provider/live-executor unittest modules against the consumer package, asserting its import path. Compare baseline and updated results.
2. Match all 346 payload hashes and Linux modes against the pinned installer manifest; compare all 304 game files and prior audit/runtime files before and after applying.
3. Run python3 scripts/grok_verify.py --mode pr, including the installed factory unit modules and disposable PostgreSQL restart harness.
4. Independently review the final diff and evidence. macOS compilation/gameplay is outside this tooling update and cannot be tested on Linux.

The full verifier exposed a preexisting consumer packaging defect: installed API/PostgreSQL tests import test_execution_contracts and test_execution_service, which the installer omits. Restore those two unchanged test modules from the same pinned upstream source as supplemental verification support. This is not a change to runtime behavior or the 346 managed payload entries. No check is disabled.
