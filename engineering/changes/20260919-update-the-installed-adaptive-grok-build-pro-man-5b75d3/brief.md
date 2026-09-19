# Update installed factory source

Update Exolon from factory source 26a0d3d to 90078959ff816068af374ad42f4bb80fdbaec866. Product VERSION remains 2.0.18. The user requested this update on 2026-09-20 (Europe/Moscow).

Apply the upstream installer plan as a reviewed source change. Exactly one of 346 managed files changes: factory/src/adaptive_factory/landing_http.py. Preserve all 304 game files, prior audit artifacts and runtime evidence. No named human gate applies.

The full verifier exposed a preexisting consumer packaging defect: installed API/PostgreSQL tests import test_execution_contracts and test_execution_service, which the installer omits. Restore those two unchanged test modules from the same pinned upstream source as supplemental verification support. This is not a change to runtime behavior or the 346 managed payload entries. No check is disabled.
