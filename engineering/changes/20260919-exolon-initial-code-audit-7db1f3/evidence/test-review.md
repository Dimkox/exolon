# Test review — Exolon initial code audit (`7db1f3f0b126`)

**Verdict: FAIL**

Product gameplay and Swift build are **not verified**. There is no XCTest target, no `xcodebuild` receipt, and no play session. Factory `grok_verify.py --mode pr` is **FAIL**. Linux TMX static audit is rerunnable data evidence only. This agent does not invent a pass receipt.

Independent of other review agents. Host: Linux. Intent: review.

---

## 1. XCTest / Swift test target — confirmed absent

- `<repo>/Exolon.xcodeproj/project.pbxproj`: one `PBXNativeTarget` `"Exolon"`, `productType = com.apple.product-type.application`.
- No second native target, no `ExolonTests`, no `XCTest` import, no `*.swift` under a Tests folder.
- In-game “test Invulnerability” in `README.md` is a cheat flag, not a unit suite.

**Adequacy:** zero automated characterization of SpriteKit behavior.

---

## 2. `linux_static_audit.py` — rerunnable, 125 TMX, not gameplay proof

Path: `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/linux_static_audit.py`

- Docstring: “Does not compile Swift or simulate gameplay.”
- `ROOT` walks to repo root; parses TMX via `xml.etree.ElementTree`.
- Re-run from repo root this session: **exit 0**.
- Independent count: `Exolon/Resources/*.tmx` = **125**; all parse as `<map>`.
- JSON (`linux-static-audit.json`): `tmx_expected`/`tmx_on_disk` = 125; `compiler_zones` = 125; chain/vitorc/dimension lists empty.
- Markdown (`linux-static-audit.md`) repeats “not an xcodebuild or gameplay result.”

**Use:** integrity of maps, pbx membership, object-name inventory, unhandled `source_marker` counts. **Not** collision physics, cabin floor, analog UP, or “the game boots.”

---

## 3. `python3 scripts/grok_verify.py --mode pr` — FAIL (honest)

This session:

```
FAIL git-diff-check: ... ERROR git-refs: delivery verification requires a locally resolvable PR target
PASS change-spec
SKIP architecture / governance / workflow-artifacts
PASS secret-scan, contract-structure, sql-safety, ruff, bandit
PASS factory-unit: exit=0
FAIL factory-postgres-exit: exit=1
PASS source-stability
RESULT: FAIL | profiles=base
EXIT:1
```

| Check | Meaning |
| --- | --- |
| `git-diff-check` FAIL | No locally resolvable PR target. Route forbids push/PR. |
| `factory-postgres-exit` FAIL | `factory/tests/run_disposable_exit.py` (disposable Postgres). Host services not installed. |
| `factory-unit` PASS | Python tests under `factory/tests/` (`test_api.py`, `test_contracts.py`, …). **Not** Swift, **not** SpriteKit. |

Do not treat factory-unit PASS as an Exolon binary.

---

## 4. Test plan / Russian §11 checklist — characterization later, not complete

Sources: `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/test-plan.md`, `engineering/reports/exolon-initial-audit.md` §11.

**Sufficient as a first macOS gate** for the Step 9 README claims: explicit `xcodebuild -target Exolon`, cabin 009 (no fall-through, UP toggle, analog vs D-pad), teleport 002, mines 007, beacon 008, bonus 024, beam 035, restart → zone 000.

**Gaps if later work claims a full port or “tests pass”:**

- No XCTest / SKView harness to lock cabin `minY` math, consume-UP, suit skip.
- Base64 collision layers L01S01–S04 not decoded in the Linux script.
- Texture load of `tiles.gif` vs `tiles.png` (L01S04) — visual only on macOS.
- DualShock Options, pad unplug, pause/restart edge cases listed but not automated.
- Expected Step 9 misses (bottom guns 023, table flyers, pursuer, full bonus) are called out as expected fail — good — but there is no regression net if someone “fixes” them later.
- Zones 010–123 mostly unwalked except a few table rows.
- Version 0.3 vs 0.5 (`Info.plist` vs `MARKETING_VERSION`) needs a built-app check.

The checklist is **adequate to start** xcodebuild + play; it is **not** sufficient evidence that those scenarios passed.

---

## 5. Why `test_review` is FAIL

| Required evidence | Status |
| --- | --- |
| Swift unit / UI tests | Missing by construction |
| `xcodebuild` | Not run (no Xcode on host) |
| Play / cabin / input | Pending; cabin fall-through remains **hypothesis** |
| Linux TMX parse 125/125 | PASS as **data** only |
| `grok_verify --mode pr` | FAIL (git-diff-check + factory-postgres-exit) |

Recording **pass** would fabricate a receipt the user forbade. Static inventory does not substitute for a game build.

**Re-run later (macOS, not this host):**

```bash
xcodebuild -project Exolon.xcodeproj -target Exolon -configuration Debug build
python3 engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/linux_static_audit.py
# then §11.1 cabin + analog UP; do not claim pass until those logs exist
```
