# Focused regression evidence

Pinned upstream: 90078959ff816068af374ad42f4bb80fdbaec866. Three upstream unittest modules were loaded while asserting adaptive_factory and landing_http resolved from the installed consumer tree; test support resolved from upstream. HTTP provider calls are mocked.

- Before the module update: 69 tests, 34 failures, exit 1 (3.317 s).
- After the module update: 69 tests, 0 failures, exit 0 (2.396 s).
- Managed integrity: all 346 expected payload SHA-256 values match. AGENTS.md checkout mode normalized to installer 0644 with unchanged content.
- Original game integrity: all 304 files match the import manifest.
- The initial full verifier reproduced an existing missing-test-module error on both original and updated consumers. The two unchanged upstream support modules were subsequently added; the repeated full verifier passed: 51 unit tests and 201 PostgreSQL/API tests, including two actual database restarts.

Run the recorded script as `python3 regression-runner.py.txt CONSUMER_ROOT UPSTREAM_ROOT`. This is factory tooling evidence, not a macOS game build or gameplay test.

Some upstream static assertions read upstream FACTORY_ROOT. The independent 346-file payload equality check covers consumer source equivalence; behavioral calls resolve to the consumer module.
