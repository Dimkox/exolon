# Cutover registry — what the merged release verifier turns red after wave D, and why

Change `20260924-complete-wave-d-specification-and-release-audit-8341b7` · phase D-1 ·
applied to `engineering/changes/20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698/evidence/release_layer_check.py`
**by editing nothing of it**. PR #3's package is dated evidence: it is read, imported and
subprocess-executed here, never patched. This file is where wave D records the consequences.

Precedent for an owned cutover red in this repository: `v3_measurements.py`'s
`shared_xcschemes = 0` pin, which was knowingly left to redden when PR #3 added the shared
scheme (recorded there, not "fixed" there). Same instrument, same rule: a merged verifier may
lose a green it was only entitled to while the defect stood.

## 1. The measured diff, on this tree

`python3 …/2e7698/evidence/release_layer_check.py --root .` after D-1's product edits:

```
rc=1   RESULT: NOT_READY (red_ac=1 bad_controls=1)
red AC key        : hardened_runtime_key_count   expected=0  measured=2
control that stops flipping: hardened_key_mutation_detected
```

Both are consequences of one edit — `ENABLE_HARDENED_RUNTIME = YES;` in **both** target
`XCBuildConfiguration` blocks, the thing audit P1-11 named and PR #3 deferred. Measured proof
that nothing else moved: re-measuring the same tree with those two lines removed from the parsed
text gives `red = []` and every other control green (this is asserted by
`macos_handout_check.py::cutover_set_exact`, not promised here).

## 2. `hardened_runtime_key_count` — the declared cutover, and only half of it

`change-spec.yaml` FORBID-002 declares the post-D-1 red set as
`{hardened_runtime_key_count, hardened_deferral_recorded}`. Measured on the real tree the set is
`{hardened_runtime_key_count}`:

* `hardened_runtime_key_count` — the key count is an EXPECTED value pinned to the deferral
  (`0 # DELIBERATELY DEFERRED`), so repaying the deferral must redden it. Declared, expected,
  correct.
* `hardened_deferral_recorded` — **cannot** redden through this change, and the declaration
  overstates it. The detector is
  `int("ENABLE_HARDENED_RUNTIME" in plan_text)`, where `plan_text` is PR #3's *own* plan files
  (`CHANGE_DIR` is hard-coded to the 2e7698 package). Those files are immutable dated evidence:
  the only mutation that turns this key red is editing PR #3's record of the deferral, which is
  exactly what FORBID-002 and the append-only rule forbid. The key's liveness is not in doubt —
  the merged checker's own `undo_records` control reddens it by blanking `plan_text` in memory,
  and `cutover_set_exact` asserts that on every run — but on any tree this change can produce,
  it stays green.

Ruling recorded: the enforceable content of FORBID-002 is *"no red outside the declared set"*,
which `cutover_set_exact` checks literally, plus *"every declared member is live"*, which it
checks through the merged checker's own revert path. The literal reading *"exactly these two
red"* is unreachable without rewriting dated evidence and is not claimed.

## 3. `hardened_key_mutation_detected` — an instrument that only exists pre-repayment

Control 8 installs the key with

```python
hard = ctx["pbx"].replace("\t\t\t\tCODE_SIGN_STYLE = Manual;",
                          "\t\t\t\tCODE_SIGN_STYLE = Manual;\n\t\t\t\tENABLE_HARDENED_RUNTIME = YES;", 1)
…
pm_hard["target_cfg_symmetric"] == 0 and pm_hard["hardened_symmetric"] == 0
```

While the key is absent, that one-sided insert is genuinely one-sided and the control is real.
Once the key is legitimately present in both target configs, the same insert adds a **duplicate of
an identical setting**; the reader builds a dictionary per configuration, so both target
`buildSettings` stay equal and `target_cfg_symmetric`/`hardened_symmetric` stay 1 — the assertion
can no longer be satisfied by any tree that has repaid the deferral. It is a pre-repayment
detector, correctly reporting that its premise is gone; it is not evidence that the reader broke.

Wave D does not edit PR #3's file to keep the number pretty. `macos_handout_check.py` declares
the set (`DECLARED_CUTOVER_CONTROLS = {"hardened_key_mutation_detected"}`), requires that **no
other** control may stop flipping in either phase, and re-proves the control's liveness on the
in-memory stripped tree inside `cutover_set_exact`.

## 4. What wave D added to the release layer (and what it did not)

| item | state after D-1 | Linux-decidable by |
| --- | --- | --- |
| `ENABLE_HARDENED_RUNTIME = YES` | both target configs, byte-equal settings | merged checker (`hardened_symmetric=1`, `target_cfg_symmetric=1`) + `cutover_set_exact` |
| `Exolon/Exolon.entitlements` | tracked, `plistlib`-parses, **empty key set**, therefore no debugger entitlement | `component_stream_identity` neighbours it; plist parse is below |
| `CODE_SIGN_ENTITLEMENTS` | both target configs, exact path | merged checker's reader (block-bound, not `grep -c`) |
| `SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG` | project **Debug** block only — deliberately asymmetric, because the two target blocks must stay equal, and because a Release copy would compile the debug warp into the shipped binary | `warp_debug_only` (asserts exactly one occurrence and no Release copy) |
| signing identity, `DEVELOPMENT_TEAM`, any certificate, any profile | **unchanged and out of scope forever** (`CODE_SIGN_IDENTITY = "-"`, `Manual`, empty team) | nothing — and no Linux verdict may claim otherwise |

```
$ python3 -c 'import plistlib,pathlib; d=plistlib.loads(pathlib.Path("Exolon/Exolon.entitlements").read_bytes()); print(sorted(d))'
[]
```

Empty on purpose: the hardened runtime is switched by its own build setting (`--options runtime`),
not by an entitlement, and every additional key here would be a new capability granted to a binary
nobody can yet observe. Apple's notarization blocker is the *presence* of
`com.apple.security.get-task-allow`, which this file cannot have.

## 5. Probe and handout wording that D-1 had to change

`engineering/runbooks/macos-probe.sh` section F no longer says the hardened runtime is
"DELIBERATELY DEFERRED outside this change": it states the repayment, points at this file, and
keeps the load-bearing distinction — a setting in `project.pbxproj` is not an observed flag;
`archived_hardened_runtime` and `codesign_flags_runtime_token` are the measurements, and C-14 is
now expected to flip from `ABSENT` to `PRESENT` on a real archive. `runbook_stale_gap_claims`
stays 0 and `runbook_archive_step_present` stays 1 (the merged checker is green on both).

## 6. Track A and Track B: structurally unrunnable, not deferred

The owner has no macOS hardware and no Developer ID ("нет у меня маков", 2026-09-25). Consequences,
stated flatly:

* **Track A (C-00, C-10…C-16) will not be run.** It was never run for this change, and it will not
  be run later: there is no machine. Every archived-bundle, `codesign`, `spctl`, `xattr`,
  `plutil`-on-bundle and `xcodebuild` fact in the probe's §B2/§B3 remains **unobserved**.
* **Track B (C-20…C-31) cannot be run**, independently of hardware: it needs a Developer ID
  identity and notary credentials that this repository's contract keeps outside the agent's reach
  permanently.
* `engineering/changes/…8341b7/evidence/macos-handout/` therefore contains a protocol and a
  checker, no report. `MACOS_EVIDENCE=ABSENT (unverified)` is the permanent state of this
  repository, not a to-do: `absent_is_unverified` exists to keep it that way and to keep it
  distinct from a pass.
* What is *not* unrunnable: everything in this file and everything `stage_boundary_check.py` /
  `macos_handout_check.py` measure on Linux, and wave A's executed-Swift contour. That is the
  ceiling of what P1-11 can close here, and audit P1-11's signing/notarization clause stays open
  with that reason attached.

The probe and the handout stay in the tree as the documentation of the protocol for a hypothetical
future Apple access — a machine, an identity and a keychain profile somebody else owns. They are
not a claim that anyone will run them, and no artifact of this change may be summarised as
"pending a macOS run".
