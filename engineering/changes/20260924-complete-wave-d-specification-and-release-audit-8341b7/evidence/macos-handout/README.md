# macOS clean-machine handout — P1-11 remaining (Track A now, Track B by the owner)

Change `20260924-complete-wave-d-specification-and-release-audit-8341b7` · route base
`295690b` · branch `codex/wave-d-spec-release-20260924`.

This file is the whole protocol. Nothing here requires reading code: every step is one
command, and every command has exactly one expected shape of output. The Linux side
(`macos_handout_check.py`, next to this file) re-checks everything you capture.

**What this handout closes and what it does not.** Track A (C-00, C-10…C-16) is a clean
build, a mandatory archive, and a read of the archived bundle. It needs no credentials.
Track B (C-20…C-31, Developer ID signing and notarization) **Track B is NOT closed** by
this change and cannot be closed by an agent: the probe refuses it unless a human sets the
second gate and types the attestation on a terminal. Until Track B is green on a real
artifact, **P1-11 stays partially closed** — the version-identity and scheme clauses are
done, the signing clause is not. No verdict produced on Linux can ever say otherwise
(PR #3 AC-010), and no report in this directory may state **notarization Accepted**
without the Apple-side objects that rule 5 of the contract requires.

**Neither track will be run. This is permanent, not a queue.** The owner has no macOS
hardware and no Developer ID identity, and stated it plainly on 2026-09-25
("нет у меня маков"). So:

* Track A is **structurally unrunnable** here, not awaiting a schedule. No
  `probe-report-*.txt`/`.json` will ever land in this directory from this project, and
  `MACOS_EVIDENCE=ABSENT (unverified)` is the repository's steady state. `absent_is_unverified`
  exists to keep it that way and to keep absence distinct from a pass.
* Track B is unrunnable twice over: no hardware, and it needs an identity plus notary
  credentials that this repository's contract keeps outside any agent's reach permanently.
* What this protocol **is**: the complete, executable documentation for a hypothetical future
  Apple access — a machine, an identity, a keychain profile owned by someone else. Run it then,
  unchanged, and the checker here will consume the result. Nothing in this change claims,
  predicts, or approximates that result; the Linux-decidable half of the release layer is
  measured by `macos_handout_check.py` and `stage_boundary_check.py`, and the executed-Swift
  half by wave A's Linux contour.
* Consequently no wording like "pending a macOS run" belongs in any artifact of this change:
  there is no run pending, and there is no date on which one will happen.

---

## 0. What you need

* A Mac with Xcode command line tools (`xcode-select -p` prints a path).
* Git access to this repository, and about 15 minutes of mostly-waiting time.
* A directory **outside** the clone for build products. The probe refuses (exit 78) if you
  point it inside the clone: an in-tree build changes the tree fingerprint and silently
  invalidates every recorded local receipt (defect M-9).
* No credentials of any kind for Track A. Track B additionally needs a Developer ID
  identity and a notary keychain profile name (a name, never a secret).

Troubleshooting the refusal codes: `75` = not macOS; `66` = wrong working directory, run
from the repository root; `73` = cannot create the report file, or the report never
finished flushing; `77` = refused (you asked for Track B without the human gate, or the
probe saw credential-shaped input in its own argv/environment); `78` = misconfiguration
(bad scratch root or bad profile name). `0` means it ran — it does **not** mean anything
passed. Verdicts are the `key=value` lines, and they take five values:
`PASS`, `FAIL`, `NOT_ATTEMPTED`, `TOOL_ABSENT`, `REFUSED`.

If your shell exports any variable whose *name* contains `PASSWORD`, `SECRET`, `TOKEN`,
`PRIVATE_KEY` or `APPLE_ID`, the probe refuses with `77` before doing anything. That is
deliberate (abort, never redact). Start from a shell without them, for example
`env -i HOME="$HOME" PATH="$PATH" TERM="$TERM" bash -l`, and re-run.

## 1. Track A — one capture (unrunnable here; the procedure, verbatim, for a future machine)

Run from the repository root, on a clean checkout of the exact commit under review:

```bash
git status --porcelain=v1            # must print nothing at all
git rev-parse HEAD                   # must equal the pull-request head SHA
EXOLON_PROBE_SCRATCH="$HOME/exolon-probe-$(date -u +%Y%m%dT%H%M%SZ)" \
  engineering/runbooks/macos-probe.sh \
  --out "$HOME/exolon-probe-report.txt"
echo "probe_rc=$?"
```

Expected raw captures (one line each, `key=value`; copy them verbatim, never paraphrase):

| step | what you should see |
| --- | --- |
| C-00.1 clean clone | the two commands above: empty status, exact SHA |
| C-00.2 toolchain | `os_version=`, `arch=`, `xcodebuild=Xcode …`, `sdk=[macosx…]`, `probe_bash_version=` |
| C-00.3 out-of-tree root | `verdict_scratch_root=OUT_OF_TREE`, `build_roots_out_of_tree=yes`, `symroot=`, `objroot=` all pointing outside the clone |
| C-00.4 cold state | `defaults_domain_present=no` before you play; `yes` afterwards is correct |
| C-10 build | `build_rc=0`, `verdict_shared_scheme=PRESENT …`, `showdestinations_rc=0`, `version_single_source=MATCH`, `build_version_single_source=MATCH`, `plist_unexpanded_placeholders=0`, `bundle_resources_tmx=125 …`, `bundle_has_gif=0 …`, `bundle_has_generated_terrain=1 …` |
| C-11 archive | `archive_rc=0`, `verdict_archive=PASS`, `archive_failure_class=NONE`, `archive_path_out_of_tree=yes`. A non-zero `archive_rc` must be classified: `SIGNING` keeps the signing clause open and says nothing about the scheme; `NO_SCHEME` after `showdestinations_rc=0` is a contradiction the checker will reject |
| C-12 identity read-back | `archived_app_present=yes`, `archived_plist_*`, `archived_version_single_source=MATCH`, `archived_plist_unexpanded_placeholders=0`, `archived_codesign_verify_rc=0`, `archived_codesign_flags=flags=0x…`, `archived_signature=Signature=adhoc`, `archived_team_id_hash=sha256:…`, `cdhash=…` |
| C-13 Gatekeeper, honestly | `spctl_assess_verdict=REJECTED`, `xattr_quarantine_present=no`, `gatekeeper_representative=no`. A locally built bundle is **not** a Gatekeeper verdict: assessment is documented for downloaded software. Record it as it comes out |
| C-14 hardened runtime | `archived_hardened_runtime=ABSENT` on today's tree, plus the deferral pointer already printed in section F. After D-1 this is the pair that must flip |
| C-15 play observations | run the probe from a terminal to answer E1…E16; `play_answers=SKIPPED …` and `play_observations=SKIPPED` are the correct output when stdin is not a terminal, and a skip is never a pass. E16 needs the D-1 build (or a real ~11-minute walk to zone 024) |
| C-16 tree after the run | `tree_clean_after_run=yes`; `git status --porcelain=v1` on the Mac prints nothing. If it does, the run is not reproducible and the report is worthless |
| flush barrier | the last three lines of the file: `report_lines_expected=`, `report_lines_written=` (equal to each other and to `wc -l` of the file), `report_flush_verified=yes`. Without `yes` the checker rejects the report (defect M-8: the file used to be truncated behind a zero exit code) |

Sanity check on the captured file: `wc -l "$HOME/exolon-probe-report.txt"` must equal the
`report_lines_written=` value in it.

## 2. Bring the evidence in, then derive, then commit — in that order

1. Copy the transcript into this directory, named
   `probe-report-<UTC>-<head7>.txt` (for example `probe-report-20260924T201031Z-295690b.txt`).
2. Strip trailing whitespace only (`sed -i '' -e 's/[[:space:]]*$//' <file>`); a raw log is
   allowed to be a raw log, but `git diff --check` is a gate and it will fail on whitespace.
   Do not edit any other byte: the digest and the line count are the evidence.
3. Derive the machine report from those bytes — never write it by hand:

   ```bash
   python3 engineering/changes/20260924-complete-wave-d-specification-and-release-audit-8341b7/evidence/macos_handout_check.py \
     --derive engineering/changes/20260924-complete-wave-d-specification-and-release-audit-8341b7/evidence/macos-handout/probe-report-<UTC>-<head7>.txt \
     --out-json  engineering/changes/20260924-complete-wave-d-specification-and-release-audit-8341b7/evidence/macos-handout/probe-report-<UTC>-<head7>.json \
     --attested-by owner --human-present
   ```

   `--attested-by owner` is your statement that you were at the machine. It is mandatory:
   a report left `unattested` is refused. The derivation is what re-binds the report to the
   committed probe text and to the tree fingerprint of the tree you are committing into.
4. Commit the transcript, the JSON and (for Track B) the Apple objects — nothing else.
5. Only after that commit, record the local receipts (`scripts/grok_verify.py --mode pr`,
   then the review receipts). Receipts bind to the tree fingerprint, so any later edit —
   including a second macOS run inside the clone — makes them stale.

## 3. What the checker will do to your evidence, and the STALE policy

```bash
python3 engineering/changes/20260924-complete-wave-d-specification-and-release-audit-8341b7/evidence/macos_handout_check.py \
  --root . --report
```

* No `probe-report-*.json` here prints `MACOS_EVIDENCE=ABSENT (unverified)` and exits 1.
  Absence is never a pass, and it is a different state from `FAIL`.
* The report is bound to: `repo_head` (must resolve as a real commit, checked with
  `git cat-file`), `tree_fingerprint`, the probe's git blob sha1, and the artifact digests
  (`sha256` plus the `CDHash`, and for Track B the notary submission uuid).
* If any binding stops matching — the probe text changed, the head moved, the tree
  fingerprint differs — the verdict is **STALE, never green**. Fix it by re-running, not by
  re-dating the file. Dated evidence in this repository is append-only: do not edit or
  delete a superseded report, add the new one and note the supersession.
* Ten consistency rules are enforced, each with a contradictory fixture that must turn the
  checker red; a rule that cannot be violated is treated as a bug in the checker, not as a
  clean bill. Rule 4 is why a Track-A report can never say notarization Accepted.

## 4. Track B — only the owner, only on a terminal (no owner machine exists)

Track B is off by construction. All three conditions must hold, or the probe exits `77`:

```bash
export EXOLON_PROBE_SCRATCH="$HOME/exolon-probe-$(date -u +%Y%m%dT%H%M%SZ)"
export EXOLON_NOTARY_PROFILE='<the name of the keychain profile you stored earlier>'
WITH_SIGNING=1 EXOLON_HUMAN_SIGNING_RUN=1 \
  engineering/runbooks/macos-probe.sh --out "$HOME/exolon-probe-trackb.txt"
# the probe then asks you to type: HUMAN_SIGNING_RUN
```

`notarytool store-credentials` is run by you, in a different shell, and is never recorded
in the probe or in a report. The probe accepts only the profile **name**; it has no code
path that takes an Apple ID, a password or a key file, and it refuses credential-shaped
argv or environment instead of redacting it.

Steps C-20…C-31: identity count and certificate fingerprint typed by you, the hardened
runtime product prerequisite (D-1), the real archive, `codesign -dvvv` showing
`Authority=Developer ID Application:` with a `Timestamp=` and the `runtime` flag, absence
of the debugger entitlement, an exported container with its `sha256`, the notary
submission, Apple's log and info objects, `stapler staple` plus `stapler validate`, a
Gatekeeper assessment of a genuinely quarantined copy, and the hardened-runtime smoke
(gamepad, HUD, audio, debugger attach). Track B counts as closed only when all of those
hold for the **same** artifact digest; anything less is `TRACK_B_PARTIAL` and P1-11 stays
partially closed.

Never type these into the probe's command line or add them to the protocol — the probe
refuses forms like them, and this repository's protocol forbids them outright:
`-allowProvisioningUpdates`, `-allowProvisioningDeviceRegistration`,
`notarytool store-credentials` (inside the probe), `--apple-id`, `--password`,
`codesign -s`, `security unlock-keychain`, `xcrun altool`.

## 5. What stays on the machine

Commit: the scrubbed transcript, the derived JSON, and for Track B the verbatim
`notary-info-<uuid>.txt` and `notary-log-<uuid>.json` (Apple issues those; they are the
strongest objects in the set), plus `checksums-sha256.txt` for the files in this directory.

Do **not** commit: the `.xcarchive`, the `.dmg`/`.pkg`/`.zip`, the app binary,
`exportoptions.plist` if it carries a team id, any `.p12` or keychain export, any Apple ID,
the contents of the notary profile, and the raw output of an identity listing. Replace them
with digests and the CDHash. Team identifiers and certificate fingerprints appear only as
`sha256:` prefixes of 12 hex characters. No hostname, no operator name, and no absolute
path under someone's home directory in any committed file: the probe already hashes the
computer name, and the two greps the release profile uses — one for private-key headers,
one for home-directory paths — must return nothing over the files added here.

## 6. Reading a report without a Mac

`result` semantics, in one paragraph: a green checker run here means the transcript is
internally consistent, bound to a commit that really exists, and produced by the probe text
that is in this tree. It does not mean the machine existed, that the bundle is signed by a
real identity, or that Gatekeeper accepted anything — those are attested (Class 2) or
excluded (Class 3) facts, listed in the report's own `attestation` block. Quote the
`key=value` lines when you make a claim; a prose sentence about a Mac run is not evidence.
