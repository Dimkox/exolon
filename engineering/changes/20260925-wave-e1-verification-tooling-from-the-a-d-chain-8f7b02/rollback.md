# Rollback plan — Wave E1 verification tooling from the A-D chain debt (issues #21/#22)

> Typed rollback: `forward_fix`, maximum 1 step ([`change-spec.yaml`](change-spec.yaml)). E1 changes
> no product byte, no schema, no data and no deployment, so "roll back" means "stop trusting the
> tool and restore the tool files" — never "recover state".

## Trigger conditions

Any one of these is a trigger; each is observable from the tool's own output, not from a hunch:

1. `wave_scan.py` reddens a contour on a tree that a per-meter standalone run proves green (a
   tool defect, not a product defect), or reports `bucket=unattributed` for a real violation.
2. A merged meter starts passing **because** of an E1 change rather than despite it - i.e. the
   FORBID-002 twin stops being hard (the control stops flipping). Concretely: `hot_path_allocation`
   green with an allocating `appendRecord` on disk, or B green with a planted ±16.
3. The suite hides a red meter (a meter line prints `green=yes` while its own rc is non-zero).
4. The 10-minute budget is exceeded so the contour stops being usable as a gate.
5. The loader-harness or pbxproj touches turn out to be wrong (e.g. `run.sh` compiles something the
   Xcode target does not, or the GUID binding rejects a legitimate project layout).

## Application rollback

Single step, forward-fix style: revert the commit(s) that introduced `engineering/tools/wave_scan.py`
and this package's evidence, plus the seven recorded tool touches
([`tasks.md`](tasks.md) "Authorized merged-tool edits"). `git revert <sha>` is enough - there is no
migration, no cache, no queue, no external system and no product file involved, and
`Exolon/`/`Exolon.xcodeproj` are byte-identical before and after (FORBID-001 is enforced by
`wave_e1_check.py::product_untouched`).

Partial rollback is also safe and is the preferred shape for a single bad hardening: each tool touch
is independent and small, so reverting just one file returns one predicate to its wave-A/B/C/D
behaviour:

| revert | what you get back |
| --- | --- |
| `…7db1f3/evidence/harness/run.sh` (+ its `last-run.txt`/`README.md`) | the loader contour stops compiling again (`cannot find 'GameConstants' in scope`, rc=1) — measured as AC-004's control |
| `…35bac2/evidence/wave_b_check.py::wave_base()` | the silent wide fallback returns: a clone without `refs/remotes/origin/main` false-greens again (that is the release reviewer's recorded hazard), and B reddens on any tooling branch |
| `…32f59c/evidence/gameplay_log_check.py` + `harness/main.swift` | the M3 bands become hard asserts again: they can redden a correct tree under load (the original #22 item 5 symptom) |
| `…8341b7/evidence/stage_boundary_check.py::warp_debug_only` | the project-Release-only regex returns and a DEBUG move into a **target** block stops being caught by this check |
| `…7db1f3/evidence/v3_measurements.py` / `…f2d90a/evidence/wave_c_check.py` | the header / the WARNING wording only: no verdict moves either way |

## Data recovery / forward-fix

No data layer exists in this change, so there is nothing to restore: no migrations, no backfills, no
runtime state, no artifacts inside the clone (the harness writes to `${TMPDIR}`, and
`…/harness/fixtures/` is gitignored on purpose). Forward-fix rules that do apply:

- A new violation that `wave_scan` attributes to an already-merged wave is a **product** finding for
  the owning wave, not an E1 defect: fix it in a new route with its own change package; E1 must not
  be used to widen `CONSTANT_ALLOW` or narrow the pattern set to make it disappear.
- If the attribution buckets mis-name a future merge (e.g. a squash merge), fix `merge_ranges()` and
  add a control that plants a violation and requires the correct bucket name.
- If a meter legitimately changes its verdict count (a new check in wave F), update the recorded
  count in `wave_scan.METERS` **and** the expected counts in `wave_e1_check.METERS` in the same
  commit; the two files implement the verdict parser independently, so a silent mismatch reddens
  `suite_standalone_agreement`.

## Verification after rollback

1. `git status --porcelain -- Exolon Exolon.xcodeproj` → empty (product untouched by the revert).
2. `python3 engineering/changes/…35bac2/evidence/wave_b_check.py`,
   `…f2d90a/evidence/wave_c_check.py`, `…8341b7/evidence/macos_handout_check.py --phase D1`,
   `…8341b7/evidence/stage_boundary_check.py` and `…32f59c/evidence/gameplay_log_check.py` → each
   must return to its pre-E1 verdicts (9, 9, 11, 10, 28) and B must go red on a tooling branch
   again - that red is the pre-E1 behaviour, so it is expected, not a breakage.
3. `bash engineering/changes/…7db1f3/evidence/harness/run.sh; echo rc=$?` → expected rc=1 with
   `cannot find 'GameConstants' in scope` if (and only if) the harness touch was reverted; this is
   the measured pre-E1 state, and the loader line in `wave_scan` must be the one that reports it.
4. Re-run `python3 scripts/grok_verify.py --mode pr --no-record` on the reverted tree and record it;
   the revert itself ships through a PR like any other change.
