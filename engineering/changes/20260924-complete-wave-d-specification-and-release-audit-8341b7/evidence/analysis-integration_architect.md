# Contract freeze — P1-11 REMAINING: clean-macOS signing / notarization / archive verification

Agent: `integration_architect` (read-only over the tree). Route `8341b7aa6eb4`,
change `20260924-complete-wave-d-specification-and-release-audit-8341b7`, base
`295690b7fc724e57b37b5fac86b71c1da7d8b032`.
Date: 2026-09-24. **Nothing below is implemented** — this document is the contract the
implementer and the two review agents must hold the change to.

## 0. Method and what was measured (not asserted)

Every constraint in §3 is the output of a run, not a reading of the source. Runs performed
(all outside the product tree; `git status --porcelain` after the session shows only the
pre-existing untracked wave-D change dir — the repo was not modified):

| # | Measurement | Result |
| --- | --- | --- |
| M-1 | `python3 …/20260921…p1-11/evidence/release_layer_check.py --root .` on the current tree | `rc=0`, `RESULT: RELEASE_LAYER_READY`, 48 AC keys green, **29/29 controls OK**; `runbook_stale_gap_claims=0`, `runbook_archive_step_present=1` |
| M-2 | `detect_runbook()` fed 12 candidate new probe lines (signing/notary/staple/spctl phrasings) | `stale` stays 0 for 11 of them; **`# EXPECTED: no shared scheme` and `EXPECTED 0 .xcscheme` each give `stale +1`** → those two wordings are forbidden in the extension |
| M-3 | Faithful scratch copy of the tree (`/tmp/fakeroot2`, product files copied, not symlinked — `rglob` does not follow symlinked dirs, which silently produced 12 red ACs in the first attempt) with the merged verifier | baseline `rc=0` reproduced on the copy |
| M-4 | Same scratch tree, probe **extended** with a §H signing/notarization block; merged verifier unchanged | `rc=0`, `RELEASE_LAYER_READY` → **the back-compat target is reachable** |
| M-5 | Same extended tree + an *additive* verifier (4 new EXPECTED keys + their own controls) | `rc=0`, **30/30 controls OK including `undo_fix_is_red`** |
| M-6 | Same additive verifier against the **unextended** probe | `rc=1 (red_ac=3, bad_controls=0)` → the new keys are causal, they cannot go green by editing prose only |
| M-7 | Renamed the guard token `EXOLON_FORBIDDEN_ARGV` → `REFUSED_CREDENTIAL_ARGV` in the probe | additive verifier `rc=1` on that one key → **detector tokens are load-bearing; renaming them is a product change** |
| M-8 | `--out` durability: a script with the probe's exact `exec > >(tee "$OUT") 2>&1` … `exit 0` shape, 401 lines, 10 runs | **7/10 runs saw an incomplete file at probe exit, 4/10 saw an EMPTY file** while the script had already returned `rc=0`. Adding `TEE_PID=$!` + close stdout + `wait` (bash 5.2) → 10/10 complete |
| M-9 | `.gitignore` × `adaptive_grok/util.py::_fingerprint_noise` / `changed_files` / `tree_fingerprint` | `_fingerprint_noise` excludes only `.grok-stack/runtime/`, `__pycache__`, `.pyc/.pyo`, `coverage/`; `changed_files()` adds `git ls-files --others --exclude-standard`; `.gitignore` does **not** ignore `build/`, `DerivedData/`, `*.xcworkspace`, `xcuserdata/` → an in-tree macOS build mutates the fingerprint and stales every receipt |
| M-10 | `.grok-stack/adaptive_grok/verification.py` gates | `git-diff-check` runs `git diff --check` on worktree+index+base..HEAD → **trailing whitespace in a committed raw log fails the PR gate**; `_secret_scan` patterns are `-----BEGIN … PRIVATE KEY-----`, `AKIA[0-9A-Z]{16}`, `(api[_-]?key|secret|password|token)\s*[:=]\s*["'][^"']{12,}["']` |
| M-11 | `project.pbxproj` at HEAD | `CODE_SIGN_IDENTITY = "-"`, `CODE_SIGN_STYLE = Manual`, `DEVELOPMENT_TEAM = ""` in both target configs; **no** `CODE_SIGN_INJECT_BASE_ENTITLEMENTS`, no `OTHER_CODE_SIGN_FLAGS`, no `ENABLE_HARDENED_RUNTIME` |
| M-12 | `spec.py::_semantic_errors` | `test` evidence paths are checked for **existence** at gate time (`path::symbol` → file part); `observability` signals must all `proves` the objective id; AC/INV/FORBID ids must match `^AC-[0-9]{3,6}$` etc. |

External facts are labelled **DOCUMENTED** (Apple page opened in this session), **MEASURED**
(run above) or **UNVERIFIED** (must be re-cited by `docs_researcher` before the checklist is
published, see §7).

## 1. What "P1-11 REMAINING" is, exactly

The finding (`engineering/reports/exolon-full-audit-20260920-v3.md:36`) has three evidence
clauses: **version identity**, **scheme**, **signing**. PR #3 (`edba343`) closed the first two
structurally and deferred signing (`20260921…p1-11/release.md` §Deferred, AC-007/AC-010). The
remaining scope is therefore *not* "make the app notarizable in the repo" — that is impossible
by construction (§4): notarization requires a Developer ID identity and notary credentials that
must never enter this tree (**DOCUMENTED**: “Use a “Developer ID” application … certificate …
(Don’t use a Mac Distribution, ad hoc, Apple Developer, or local development certificate.)” —
Apple, *Notarizing macOS software before distribution*).

The remaining scope that **is** deliverable, and which this contract freezes, is:

* **R-A** a machine-checkable, clean-macOS protocol that produces a *report* whose contents
  Linux reviewers can audit without the machine (§2, §3);
* **R-B** an additive, causally-checked extension of `engineering/runbooks/macos-probe.sh` and
  `release_layer_check.py` that can express signing/notarization expectations and cannot be
  satisfied by prose (§4);
* **R-C** an enforced agent/human boundary such that no agent run can ever emit a signing
  verdict (§5).

**Two tracks, permanently separate.** Track A needs no credentials and is what this route can
close. Track B needs a Developer ID identity and is documented as a handout; a Track-A-only
PR must state that P1-11 stays *partially closed*.

| | Track A — clean build / archive (no secrets) | Track B — Developer ID sign + notarize |
| --- | --- | --- |
| Who runs it | owner (human) on a clean Mac; **an agent may drive only non-signing steps if it never sets the signing gate var** | owner only, always |
| Prerequisite tree | HEAD as merged | a **separate** product change that sets `ENABLE_HARDENED_RUNTIME = YES` in *both* target configs (INV-001 symmetry; FORBID-002 of PR #3 blocks it before a green M-01′) |
| Can this PR close it | yes, if green | no — becomes an audited handout |

## 2. The clean-macOS checklist (R-A + R-B), with exit semantics

Conventions used below.

* **Verdict tokens are 5-valued and never collapse to a number:**
  `PASS` / `FAIL` / `NOT_ATTEMPTED` / `TOOL_ABSENT` / `REFUSED`. `rc=0` is *not* a verdict; it is
  the probe's operational status. `NOT_ATTEMPTED` **must never be readable as a pass** — this is
  the single most important rule of the extension, because the current probe already prints
  `archive_rc=SKIPPED …` and a reader can mistake a skip for success.
* Probe exit codes (existing ∪ new, `sysexits.h` discipline): `0` ran (any verdict),
  `2` usage, `66` target project not found, `73` cannot create `--out`, `75` not macOS,
  `77` refused (signing gate not satisfied / credential-shaped input detected) — **new**,
  `78` configuration error (bad profile name, unparsable plist) — **new**.
* Every step lists a **contradictory control** — what must flip for the step to be considered a
  measurement at all (repo rule: *у каждого замера обязана быть пара, которая перевернётся*).

### C-00 Preparation (no product state)

| step | command | expected | exit | control that must flip |
| --- | --- | --- | --- | --- |
| C-00.1 clean clone | `git clone <url> exolon && cd exolon && git checkout <pr-head-sha> && git status --porcelain=v1 && git rev-parse HEAD` | `git status` **empty**; `HEAD` == the exact SHA in the PR | 0 | check out the *base* commit → the report's `repo_head` differs from the pinned SHA and §3's Linux consumer must reject it |
| C-00.2 toolchain stamp | `sw_vers -productVersion`; `xcodebuild -version`; `xcodebuild -showsdks`; `bash --version`; `uname -m` | recorded verbatim | 0 | `xcodebuild` absent → probe must print `verdict_toolchain=FAIL_NO_XCODE` (it already does) |
| C-00.3 **out-of-tree build root** | `export EXOLON_PROBE_SCRATCH="$HOME/exolon-probe-$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$EXOLON_PROBE_SCRATCH"` and pass `SYMROOT`/`OBJROOT` under it, or run the whole clone from a copy | repo stays `git status --porcelain` clean after the run | 0 | run the probe *without* redirection → `build/` appears untracked → `tree_fingerprint` changes → M-9 says every local receipt goes stale (MEASURED) |
| C-00.4 cold persisted state | `defaults delete com.exolon.remake` (ignore "does not exist"), then record `defaults read com.exolon.remake` rc | section D prints `defaults_domain_present=no` before play | 0 | after one play session the domain exists → `defaults_domain_present=yes` (probe already discriminates) |
| C-00.5 bash version | record `probe_bash_version=` | `>= 4.4` **or** the flush self-check of §4-D present | — | bash 3.2 (`/bin/bash` on a stock Mac; the shebang is `#!/usr/bin/env bash`) does not set `$!` for process substitution → the flush barrier must be version-independent |

### Track A — C-10 … C-16 (no credentials; this is what the PR can close)

| step | command | expected output | exit semantics | control |
| --- | --- | --- | --- | --- |
| C-10 probe, archive on | `WITH_ARCHIVE=1 engineering/runbooks/macos-probe.sh --out "$SCRATCH/probe-report.txt"` | `build_rc=0`, `verdict_shared_scheme=PRESENT`, `showdestinations_rc=0`, `version_single_source=MATCH`, `build_version_single_source=MATCH`, `plist_unexpanded_placeholders=0`, `bundle_resources_tmx=125`, `bundle_has_gif=0`, `bundle_has_generated_terrain=1`, `hardened_runtime=ABSENT` (deferral is tree truth), `codesign_flags` contains `adhoc` and **no** `runtime` token | `0` ran; `75` off-macOS; `66` wrong cwd; **never** non-zero because of a FAIL verdict | run `--config Release` too, and deliberately break `MARKETING_VERSION` in a scratch copy → `version_single_source=MISMATCH` must appear |
| C-11 archive verdict | same run, section B2 | `archive_rc=0` **or** `archive_rc!=0` with the tail classified: `archive_failure_class=SIGNING` vs `NO_SCHEME` vs `OTHER`. A `NO_SCHEME` outcome after `showdestinations_rc=0` is a contradiction the report verifier must reject | — | an unredacted classification is required: today `archive_rc` + an 8-line tail is the whole evidence, and `NO_SCHEME` vs `SIGNING` are not distinguished |
| C-12 identity read-back | `codesign -dvvv "$APP" 2>&1` | `Signature=adhoc`, `TeamIdentifier=not set`, `flags=0x…(adhoc)` ; **`Timestamp=` absent** | rc 0 | `codesign -d --entitlements :-` prints a plist with no `runtime` bit — that is exactly why PR #3 switched to `-d --verbose=4` (probe §B comment); keep both, the entitlements dump is the B-24 carrier |
| C-13 Gatekeeper, honestly | `spctl -a -t exec -vv "$APP"`; `xattr -l "$APP"` | `rejected` **and** `xattr` shows no `com.apple.quarantine` | `0` accepted / `3` rejected (verify `--help` on the machine) | **This is not a Gatekeeper verdict**: Apple documents assessment for *downloaded* software (“When a user downloads and opens an app … from outside the App Store”, Gatekeeper and runtime protection). Locally built bundle ⇒ record `gatekeeper_representative=no`. The `spctl -a` + `xattr` pair is the contradictory control that a bare `spctl` line lacks (the `:96` assertion was already flagged as having no EXPECTED) |
| C-14 hardened-runtime negative anchor | `codesign -d --verbose=4 "$APP" \| grep -o 'flags=0x[0-9a-f]*(.*)'` | `hardened_runtime=ABSENT` on this tree, and the report must state the deferral pointer | — | the pre-fix dump is the negative control PR #3 promised (`release.md` §Deferred) |
| C-15 manual observation set | E1…E15 of the probe, from a real tty | answers recorded, or `play_answers=SKIPPED` | — | run once with stdin not a tty → the SKIPPED branch must appear |
| C-16 post-run tree check | `git status --porcelain=v1` | **empty** | — | if not empty, the run is not reproducible from a clean clone; the report must carry `tree_clean_after_run=yes` |

Track A verdict rule: **all of C-10/C-11/C-12/C-14 green with `hardened_runtime=ABSENT` closes
M-01′/M-02′/M-03′/M-04′ of `macos-validation-handout-v2.md` and nothing else.** It does not
close clause three of P1-11.

### Track B — C-20 … C-31 (human-only; `WITH_SIGNING=1` + `EXOLON_HUMAN_SIGNING_RUN=1`)

| step | command | expected | exit | control |
| --- | --- | --- | --- | --- |
| C-20 identity present (human, own shell) | `security find-identity -v -p codesigning` | ≥ 1 line `Developer ID Application: <org> (<TEAMID>)` | 0 | the probe must **not** run this; report carries only `developer_id_identity_count=` and a SHA-256/12 hash of the cert fingerprint |
| C-21 tree prerequisite | product change sets `ENABLE_HARDENED_RUNTIME = YES` in both target configs | `release_layer_check.py`: `hardened_runtime_key_count=2`, `hardened_symmetric=1`, `target_cfg_symmetric=1`, `hardened_deferral_recorded` flips meaning → needs the dated note of §4-E | 0 | a one-sided insert must redden it — already controlled by `hardened_key_mutation_detected` (MEASURED green today) |
| C-22 archive with real identity | `xcodebuild -project Exolon.xcodeproj -scheme Exolon -configuration Release -archivePath "$SCRATCH/Exolon.xcarchive" archive` | `** ARCHIVE SUCCEEDED **`, `archive_rc=0` | 0 | `-allowProvisioningUpdates` / `-allowProvisioningDeviceRegistration` are **forbidden** in this repo's protocol (they perform account operations) |
| C-23 signature + timestamp | `codesign -dvvv "$APP"`; `codesign --verify --deep --strict --verbose=4 "$APP"` | `Authority=Developer ID Application: …`, `TeamIdentifier=<10>`, flags token contains `runtime`, **`Timestamp=` present** | verify rc 0 | Apple: Xcode “adds a secure timestamp only during the archive (as of Xcode 10.2) and export workflows” (DOCUMENTED, resolving-common-notarization-issues#Include-a-secure-timestamp) — so a Debug-build dump is the negative control and the archive dump the positive one |
| C-24 `get-task-allow` absence | `codesign -d --entitlements :- "$APP"` | no `com.apple.security.get-task-allow` with a true value | 0 | Apple: leaving it in ⇒ “notarization fails with … `The executable requests the com.apple.security.get-task-allow entitlement.`” (DOCUMENTED). Also record `settings_CODE_SIGN_INJECT_BASE_ENTITLEMENTS=` from `xcodebuild -showBuildSettings`: the key is **absent from `project.pbxproj`** (MEASURED, M-11) and Apple does not publish the default ⇒ **UNVERIFIED until measured**, and this is the only place it can be measured |
| C-25 container for submission | `xcodebuild -exportArchive -archivePath … -exportPath "$SCRATCH/out" -exportOptionsPlist "$SCRATCH/exportoptions.plist"` (method `developer-id`), or `ditto -c -k --keepParent`; record `shasum -a 256` of the produced `.pkg`/`.dmg`/`.zip` | artifact + digest in the report | 0 | Apple: “You cannot staple directly to a ZIP archive … not possible to staple tickets to standalone binaries” (DOCUMENTED, customizing-the-notarization-workflow) ⇒ a `.zip` submission must be paired with `stapler staple <App.app>` **before** re-zipping, or the container must be `.dmg`/`.pkg` |
| C-26 submit (**human**) | `xcrun notarytool submit "$ARTIFACT" --keychain-profile "$EXOLON_NOTARY_PROFILE" --wait` | stdout contains `status: Accepted` and `id: <uuid>`; `submit_rc=0` | with `--wait`, rc 0 = Accepted, non-zero = Invalid/In-progress/transport (verify on the machine with `xcrun notarytool submit --help`, capture the help text as evidence) | submit a deliberately **unsigned** copy → `notary_status=Invalid`, `submit_rc!=0`, and the log of C-27 must be non-empty: this is the required contradictory control of the whole track |
| C-27 Apple log / info | `xcrun notarytool log <uuid> --keychain-profile "$P" "$SCRATCH/notary-<uuid>.json"`; `xcrun notarytool info <uuid> --keychain-profile "$P"` | log JSON committed verbatim; `info` captured | 0 | for an `Invalid` submission the log lists `issues[]` — a report with `notary_status=Invalid` and an empty/absent log must be rejected by the consumer |
| C-28 staple + validate | `xcrun stapler staple "$ARTIFACT"`; `xcrun stapler validate "$ARTIFACT"` | staple rc 0; validate rc 0 and `The validate action worked!` | 0 | validate a **pre-staple** copy → must fail; that pair is what makes `stapler_validate=PASS` mean something |
| C-29 Gatekeeper on a genuinely quarantined copy | fetch the artifact the way a user does (browser download, or `curl -L` then set `com.apple.quarantine`), then `spctl -a -t exec -vv <staged app>` / `-t instl` for `.pkg` | `accepted` **with `source=Notarized Developer ID`** | 0 accepted / 3 rejected | `source=` is the discriminating token: `accepted source=Mac App Store` or `=loose validation` must be classified differently, and the same binary assessed without quarantine must be marked `gatekeeper_representative=no` |
| C-30 hardened-runtime smoke | launch, then gamepad / HUD / audio / debugger-attach checks (the manual run PR #3 already scoped) | `manual_smoke=PASS` per item, one line each | — | hardened runtime *can* restrict JIT / unsigned executable memory / library validation (DOCUMENTED: hardened-runtime) — the smoke list is the control for “it still runs” |
| C-31 retention / non-commit | list of what stays off the machine | see §5.4 | — | — |

**Track B is closed only when C-23 (`runtime` + `Timestamp=`), C-26 (`Accepted`), C-27 (log
committed), C-28 (`worked!`) and C-29 (`Notarized Developer ID`) are all green on the same
artifact digest.** Any other combination is `PARTIAL` and must be printed as such.

## 3. The committed evidence handout (so the PR is auditable without the machine)

### 3.1 Placement and filenames

Everything lands in the **wave-D package** (dated dir; never back-edit PR #3's package):

```
engineering/changes/<wave-D>/evidence/macos/
  README.md                                 # index + "how to re-verify on Linux" (one command)
  handout-clean-macOS-v3.md                 # §2 as a printable protocol (the mandate's "external handout")
  probe-report-<UTC>-<head7>.txt            # scrubbed stdout of macos-probe.sh (raw, ordered)
  probe-report-<UTC>-<head7>.json           # §6 schema; derived from the .txt, never by hand
  notary-info-<submissionUuid>.txt          # Track B only, verbatim
  notary-log-<submissionUuid>.json          # Track B only, verbatim  ← the external anchor
  codesign-dvvv-<cdhash12>.txt              # Track B only, redacted per §5.4
  spctl-<cdhash12>.txt                      # assess output + `xattr -l` pair
  run-receipt.json                          # provenance bundle (§3.3)
  checksums-sha256.txt                      # sha256 of every file above
```

`<UTC>` = `%Y%m%dT%H%M%SZ`, `<head7>` = short HEAD. No operator names, no operator home
paths, no hostname (`hygiene-pii.md` failed exactly on this class; the probe already hashes
`ComputerName` → keep that precedent).

### 3.2 What MUST be captured (and what must not)

Must be committed: the scrubbed raw report, the derived JSON, `run-receipt.json`, and for
Track B the notary `info` + `log` and the `codesign -dvvv` / `spctl` dumps. The notary log is the
strongest object in the set: it is issued by Apple, names the submission id, and cannot be
produced by the operator's own tooling.

Must **not** be committed (and the handout must say so, because a reviewer will otherwise ask):
the `.xcarchive`, the `.dmg`/`.pkg`, the app binary, `exportoptions.plist` if it carries a team
id, any `.p12`/keychain export, any Apple ID, any profile *contents*, the raw
`security find-identity` output. Those are replaced by digests + the CDHash.

### 3.3 Binding digests (`run-receipt.json`)

| field | why it is there | who re-derives it on Linux |
| --- | --- | --- |
| `repo_head` (full SHA) + `tree_fingerprint` | ties the report to one exact tested tree; `AGENTS.md` requires exact-SHA evidence | `git rev-parse HEAD`, `adaptive_grok.util.tree_fingerprint` |
| `probe_script_blob` (git blob sha1 of `macos-probe.sh`) | **anti-reuse**: a report cannot be reinterpreted against a later version of the probe (M-7 proves the probe text is the contract) | `hashlib.sha1(b"blob %d\0" % len(data) + data)` — the *same* expression `release_layer_check.py` already uses for `REPORTS_PIN_BLOB` |
| `verifier_script_blob` | same, for the consumer | as above |
| `report_sha256`, `report_lines` | detects the `tee` flush race (M-8): a truncated report fails the digest **and** the line count | `sha256sum` |
| `artifact_sha256` (submitted container), `cdhash` | the notarization was of *this* bytes, not of an unnamed build | compared to the id inside `notary-log` |
| `submission_uuid` | primary key of the Apple-side record | present in `notary-info`/`log` |
| `xcode_version`, `macos_version`, `arch`, `bash_version`, `host_hash` | clean-machine provenance; bash 3.2 vs 5.x changes the flush story (C-00.5) | human cross-check |
| `operator_attestation` (`"owner"`, `attested_by_hash`) | Track B facts are single-witness; the artifact states that openly | n/a |

### 3.4 Ordering (measured, not stylistic)

1. run probe (§2) → 2. copy report + receipt into `evidence/macos/` → 3. scrub whitespace
   (`git diff --check` gate, M-10; precedent: `…7db1f3/evidence/harness/last-run.txt` header
   says it scrubbed for exactly this) → 4. **commit** → 5. only *then* run
   `python3 scripts/grok_verify.py --mode pr` and record `verification` / `security_review` /
   `release_review` receipts (they bind to the fingerprint and go stale on any later edit).
   A macOS run performed *after* the receipts, inside the repo, stales them (M-9).

### 3.5 Auditability classes (what a Linux reviewer may and may not conclude)

* **Class 1 — re-derivable without the machine:** every digest of §3.3; the schema/consistency
  checks (§6.3); the *text* invariants of the probe (§4).
* **Class 2 — attested, internally cross-checked, not re-derivable:** build/archive success,
  `codesign`/`spctl`/`stapler` verdicts, the notary `Accepted`. The consumer can prove they are
  mutually consistent and bound to the right blob/HEAD, not that the machine existed.
* **Class 3 — must never be inferred from a Linux verdict:** anything about the built bundle,
  scheme-loader acceptance, Gatekeeper outcome (PR #3 AC-010 says exactly this; the new verifier
  must keep it).

## 4. How `macos-probe.sh` may be extended without breaking its consumers

### 4-A Frozen surface (changing any of these is a separate, named decision)

1. **Path** `engineering/runbooks/macos-probe.sh`. It is a `test` evidence path in PR #3's
   `change-spec.yaml` (`AC-006`, `AC-010`) and is cited in dated reports
   (`engineering/reports/exolon-full-audit-20260920-v3.md:189`,
   `…7db1f3/evidence/perfile/citation-integrity.md:14,45,48`). Moving it breaks `spec`
   validation (M-12: paths must exist at gate time).
2. **Exit codes** `0/2/66/73/75` and the rule *exit code = operational, verdict = content*.
   Do not make the probe exit non-zero on a FAIL — the human captures it with `--out`.
3. **CLI** `--out|--target|--config|-h`, `WITH_ARCHIVE=1`, positional rejection ⇒ `exit 2`.
   New flags are additive only: `WITH_SIGNING=1`, `--json` (optional, must not change §A–G text).
4. **Key names cited elsewhere** (must stay byte-identical): `version_single_source`,
   `build_version_single_source`, `plist_unexpanded_placeholders`, `showdestinations_rc`,
   `archive_rc`, `codesign_flags` (PR #3 `release.md` §Metrics + `requirements.md`
   §Observability), plus `hardened_runtime`, `verdict_shared_scheme`, `build_rc`,
   `app_path_found`, `plist_*`, `bundle_*`, `defaults_*`.
5. **Line grammar** `key=value`, sections `## A … ## G`; the `-e`-free `emit` helper;
   `set -uo pipefail` with **no** `-e` (a probe must survive the failure it is measuring).
6. **Detector tokens** that the wave-D verifier greps — §4-D list. M-7: renaming one reddens an
   AC; therefore they are pinned in `requirements.md` and every one of them must have a
   `""` → 0 control (M-5 pattern).
7. **The `-target Exolon` build path** (handout-v2 M-02′ keeps it as fallback while `-scheme`
   is proved) — do not switch the §B build to `-scheme` in this change.

### 4-B What `release_layer_check.py::detect_runbook` actually enforces (M-1/M-2)

`runbook_stale_gap_claims` must stay `0`. A line is stale iff it contains the literal
`EXPECTED` **and** matches one of: `no shared scheme` · `\b0 \.xcscheme` ·
`shared scheme.*ABSENT` · `CFBundleShortVersionString\s*=\s*0\.3` · `\.xcscheme\)?\s*=\s*0` ·
`shared_xcschemes\s*[:=]\s*0`. Consequences for the extension:

* never write `EXPECTED … no shared scheme` or `EXPECTED … 0 .xcscheme` (M-2: each +1 red);
* the words `shared scheme` and `ABSENT` must not share a line that also carries `EXPECTED`
  (regex is `.*`, order-sensitive); identity/notary verdicts belong on their own lines;
* `runbook_archive_step_present` stays 1 as long as the file mentions `archiv` — so the new
  sections must not be *substituted* for §B2, only appended;
* `verdict_*`/regression message lines must keep **not** containing `EXPECTED`
  (§A's `ABSENT (REGRESSION: …)` line is legal for that reason alone).

### 4-C §4.5 line-number drift (documentation-only, but must be recorded)

Dated files cite probe line numbers (`macos-probe.sh:151`, `citation-integrity.md:48` "(161)").
Appending ~90 lines shifts them. Those dated files must **not** be edited (append-only rule,
AC-009 of PR #3); wave-D must add a one-paragraph drift note in its own `requirements.md`
so the next audit pass does not re-open it as a new citation defect.

### 4-D Required new probe content (the extension itself)

Sections to append (letters H/I/J do not collide with the existing A–G):

* **§H Signing track** — emits `signing_track=SKIPPED|HUMAN|REFUSED`,
  `settings_CODE_SIGN_IDENTITY`, `settings_CODE_SIGN_INJECT_BASE_ENTITLEMENTS`,
  `codesign_flags_runtime_token`, `notarytool_submit_rc`, `notary_status`,
  `stapler_validate`, `spctl_assess_verdict`, `gatekeeper_representative`,
  `artifact_sha256`, `cdhash`, `submission_uuid`. Defaults when the gate is off:
  every verdict key = `NOT_ATTEMPTED` (M-4 shows this text is back-compat-clean).
* **§I Notarization track** — only reachable behind §H's gate.
* **§J Probe self-test** — pure-text parsers run over two canned strings each, emitting
  `probe_selftest_signing_parser=PASS|FAIL`, `probe_selftest_notary_status_parser=PASS|FAIL`,
  `probe_selftest_verdict_not_collapsed=PASS|FAIL` (must FAIL if `Accepted` and
  `NOT_ATTEMPTED` produce the same output). This is what makes the Track-B parser
  Linux-auditable, since the self-test lines are in the committed report.
* **Guard tokens** (pinned, non-renameable): `EXOLON_HUMAN_SIGNING_RUN`, `WITH_SIGNING`,
  `EXOLON_NOTARY_PROFILE`, `EXOLON_FORBIDDEN_ARGV`, `signing_track_verdict=REFUSED`,
  `probe_report_saved`, `report_flush_verified`.
* **§4-E flush barrier (mandatory fix, M-8).** Because the report file is the digest carrier and
  `exec > >(tee "$OUT")` + `exit 0` leaves it incomplete in 7/10 runs (4/10 empty), the probe
  must, before exiting, re-read `$OUT` and emit
  `report_lines_expected=` / `report_lines_written=` / `report_flush_verified=yes|no`,
  retrying with a bounded wait; it must **not** depend on `$!` (bash 3.2 on a stock Mac).
  `report_flush_verified=no` must make the §6 consumer reject the report outright.

### 4-E Extending `release_layer_check.py` (route mandate: "extend", not fork)

MEASURED recipe (M-4/M-5/M-6):

1. Append new keys to `EXPECTED` — never mutate an existing value, never delete a key, never
   renumber the printed AC lines.
2. Feed them from `detect_runbook()`-style **pure detectors that take text/data**, so controls
   can corrupt them.
3. Add one contradictory control per new key, each of the shape
   `detect("")==0 and detect(fixture)==1` (mirrors the existing archive detector control).
4. Keep every new key red under at least one of the four existing reverts, otherwise
   `undo_fix_is_red`'s equality `r_all == (r_plist|r_scheme|r_run|r_rec) - {v3_…}` breaks.
   A new dimension (e.g. `undo_signing_track`) must be added **with** its disjointness
   assertions. M-5 confirms the current 4-key addition leaves 30/30 green; M-6 confirms it is
   red on the unextended probe.
5. Add a **report consumer** (`measure_report(ctx)` reading the committed
   `evidence/macos/probe-report-*.json`) whose verdict is Class-1 only (§3.5) and which can
   state `macos_only_acs_never_certified_on_linux=1`. Its EXPECTED values must be satisfiable
   by a Track-A report, so this PR can be green without Track B.
6. `RUNBOOK` text is not blob-pinned by the tool (`gather_reports` only globs
   `engineering/reports/*-20??????.md`), so extending the probe needs no re-pin; the two dated
   reports must keep their pinned blobs byte-identical (AC-009).

## 5. Agent / human boundary — enforced in the design, not by good intentions

### 5.1 Allocation

| action | agent | human | why |
| --- | --- | --- | --- |
| write/extend the probe, the verifier, this contract, the handout | ✅ | review | text + Linux-decidable |
| run `release_layer_check.py`, `grok_verify.py`, parse a committed report | ✅ | — | read-only, no credentials |
| run Track A probe steps (C-00…C-16) on the owner's Mac | ❌ default | ✅ | it mutates a machine and executes product code; `route.human_gates` includes `production_action_approval` |
| `WITH_SIGNING=1` / any of C-20…C-31 | ❌ **structurally impossible** | ✅ only | signing keys + notary credentials |
| `notarytool store-credentials`, keychain access, `.p12`, Apple ID | ❌ | ✅ | AGENTS.md: agents must not create/use human approval keys or read signing secrets |
| commit the evidence, type `attested_by` | prepare file bytes | ✅ sign-off | single-witness facts |

### 5.2 Mechanical enforcement points (each one must exist and be checked by §4-E)

1. **Two-gate opt-in.** Signing/notary steps run only if `WITH_SIGNING=1` **and**
   `EXOLON_HUMAN_SIGNING_RUN=1`; missing the second emits
   `signing_track_verdict=REFUSED …` and exits **77**. An agent cannot set the second gate
   without the owner typing it, and if it does, the refusal-turned-run is *in the report*,
   which the review receipts then cover.
2. **Interactive attestation.** With `WITH_SIGNING=1` on a tty, the probe requires the operator
   to type the literal `HUMAN_SIGNING_RUN` at a prompt; off a tty it exits 77 (reuses the
   existing `[ -t 0 ]` discipline from section E). Non-interactive signing is therefore
   unimplementable without editing the script — and the edit is caught by §J/detector tokens.
3. **No credential arguments exist.** The probe's only notary invocation form is
   `xcrun notarytool … --keychain-profile "$EXOLON_NOTARY_PROFILE"`. It must not contain
   `--apple-id`, `--password`, `-p`, `.p12`, `.mobileprovision`, `--key`, `PEM`, or
   `codesign --sign <identity>` anywhere — **including comments** — so no agent can supply
   credentials even by accident. `EXOLON_NOTARY_PROFILE` is validated
   `^[A-Za-z0-9._-]{1,64}$` or exit 78.
4. **Self-defence scan** (`EXOLON_FORBIDDEN_ARGV`): argv and the names (never values) of env
   vars matching `.*(PASSWORD|SECRET|TOKEN|PRIVATE_KEY|APPLE_ID).*` abort the run with
   `signing_track_verdict=REFUSED_CREDENTIAL_ARGV`, exit 77. Abort, not redact: the run must
   not produce a partial Track-B report.
5. **Redaction is inside the producer.** Apple-ID emails are never printed; Team ID and cert
   fingerprints are printed as SHA-256/12 (precedent: `hostname_redacted=$(… | md5 -q)`).
   `git grep -I -E 'BEGIN [A-Z ]*PRIVATE KEY|/Users/'` over the added evidence must return 0 —
   this is also what keeps M-10's `secret-scan` from failing the PR (`password = "…"`-shaped
   text in a captured log is a real trap; the notary `--help` capture must be scrubbed of the
   `--password <…>` example lines, or excluded).
6. **Prohibited flag list** in the handout: `-allowProvisioningUpdates`,
   `-allowProvisioningDeviceRegistration`, `notarytool store-credentials` (interactive-only, run
   by the human in a *different* shell, never recorded in the probe), `--apple-id`,
   `--password`, `codesign -s`, `security unlock-keychain`, `xcrun altool` (service removed
   2023-11-01, DOCUMENTED — a script still calling it is broken, not conservative).
7. **Receipt separation.** §3.4 ordering; Track B receipts can only ever be
   `release_review`/`security_review` on a *report*, never a claim of execution.

### 5.3 Typed enforcement (goes into `change-spec.yaml`, ids per M-12)

* `FORBID-001` No signing identity, `DEVELOPMENT_TEAM` value, `.entitlements` file, certificate
  or provisioning profile enters the tree through this change (extends PR #3's `FORBID-003`).
* `FORBID-002` No `ENABLE_HARDENED_RUNTIME` in either configuration before M-01′ is green
  (inherited unchanged from PR #3 — Track B depends on it, so the dependency must be visible).
* `FORBID-003` No `SKIPPED`/`NOT_ATTEMPTED` may be recorded or summarised as a pass anywhere in
  the report, handout, PR body or receipts.
* `FORBID-004` No agent may invoke, wrap or emulate Track B steps; the probe must refuse.
* `FORBID-005` No dated evidence (PR #3 package, `engineering/reports/*`) is edited; the
  P1-11 line stays *partially closed* until Track B is green.
* `INV-001` The merged verifier stays green across the probe extension (M-4).
* `INV-002` Every new EXPECTED key is causal: green only with the extension present (M-6).
* `INV-003` A report whose `probe_script_blob` ≠ committed probe is invalid.

### 5.4 What leaves the machine and what stays (Track B retention)

Keep: everything in §3.1. Delete after digests are recorded: `.xcarchive`, `.dmg/.pkg`,
`exportoptions.plist`, keychain profile *contents*, screenshots of `find-identity`. Never
transmit to any hosted tool (AGENTS.md: no proprietary/signing material to external tools).

## 6. Probe report artifact schema

### 6.1 Filenames

`probe-report-<UTC>-<head7>.json` (machine) + `probe-report-<UTC>-<head7>.txt` (raw, the
authoritative byte stream the JSON is derived from). The JSON never replaces the TXT; a
disagreement is `FAIL`.

### 6.2 JSON schema (normative)

```json
{
  "schema": "exolon.macos-probe-report/1",
  "generated_utc": "2026-09-24T20:10:31Z",
  "track": "A|B",
  "operational": {
    "probe_exit_code": 0,
    "probe_bash_version": "3.2.57(1)-release",
    "probe_script_blob_sha1": "<40 hex>",
    "verifier_script_blob_sha1": "<40 hex>",
    "report_flush_verified": true,
    "report_lines_expected": 412,
    "report_lines_written": 412,
    "raw_report_sha256": "<64 hex>",
    "tree_clean_before_run": true,
    "tree_clean_after_run": true
  },
  "environment": {
    "macos_version": "26.0.1", "arch": "arm64",
    "xcodebuild": "Xcode 26.1  Build version 17B100",
    "sdks": ["macosx26.1"], "host_hash": "<md5 of ComputerName, or na>"
  },
  "provenance": {
    "repo_head": "<40 hex>", "tree_fingerprint": "<64 hex>",
    "artifact_sha256": "<64 hex or null>", "cdhash": "<hex or null>",
    "submission_uuid": "<uuid or null>"
  },
  "verdicts": {
    "toolchain": "PASS|FAIL_NO_XCODE",
    "shared_scheme": "PRESENT|ABSENT",
    "build_rc": 0, "build": "PASS|FAIL|NOT_ATTEMPTED",
    "version_single_source": "MATCH|MISMATCH|NOT_ATTEMPTED",
    "build_version_single_source": "MATCH|MISMATCH|NOT_ATTEMPTED",
    "plist_unexpanded_placeholders": 0,
    "showdestinations_rc": 0,
    "archive_rc": 0, "archive": "PASS|FAIL|NOT_ATTEMPTED",
    "archive_failure_class": "NONE|SIGNING|NO_SCHEME|OTHER|NOT_ATTEMPTED",
    "hardened_runtime": "PRESENT|ABSENT|NOT_ATTEMPTED",
    "signing_identity_class": "ADHOC|DEVELOPER_ID|APPLE_DEVELOPMENT|UNKNOWN|NOT_ATTEMPTED",
    "secure_timestamp": "PRESENT|ABSENT|NOT_ATTEMPTED",
    "get_task_allow_present": false,
    "notary_profile_present": "YES|NO|NOT_APPLICABLE",
    "notary_submit": "ACCEPTED|INVALID|IN_PROGRESS|REFUSED|NOT_ATTEMPTED|TOOL_ABSENT",
    "notary_log_committed": true,
    "stapler_staple": "PASS|FAIL|NOT_ATTEMPTED",
    "stapler_validate": "WORKED|FAIL|NOT_ATTEMPTED",
    "spctl_assess": "ACCEPTED_NOTARIZED_DEVELOPER_ID|ACCEPTED_OTHER|REJECTED|NOT_RUN|NOT_ATTEMPTED",
    "gatekeeper_representative": false,
    "play_observations": "COMPLETE|PARTIAL|SKIPPED"
  },
  "raw_kv": { "<every key=value line of the TXT, verbatim>": "…" },
  "selftest": {
    "signing_parser": "PASS|FAIL",
    "notary_status_parser": "PASS|FAIL",
    "verdict_not_collapsed": "PASS|FAIL"
  },
  "track_b": null,
  "attestation": {
    "class_1_rederivable": ["digests","blob binding","schema consistency","probe text invariants"],
    "class_2_attested": ["build","archive","codesign","notary","staple","spctl"],
    "class_3_excluded": ["built-bundle truth","scheme loader acceptance","Gatekeeper outcome"],
    "operator_attested_by": "owner",
    "human_present": true
  }
}
```

For `track: "B"`, `track_b` becomes
`{"identity_hash": "sha256:12…", "authority_chain": ["…Developer ID Application: <org> (<TEAMID_HASH>)"],
"notary_info_file": "notary-info-<uuid>.txt", "notary_log_file": "notary-log-<uuid>.json",
"container": "pkg|dmg|zip", "stapled_target": "container|app", "manual_smoke": {"gamepad":"PASS","hud":"PASS","audio":"PASS","debugger_attach":"PASS"}}`.

### 6.3 Consistency rules the Linux consumer must enforce (each with its contradictory control)

1. `schema` == `exolon.macos-probe-report/1`; all required keys present (missing key ⇒ reject,
   never default to pass).
2. `operational.report_flush_verified == true` **and** `raw_report_sha256` == hash of the
   committed TXT **and** `report_lines_written == wc -l TXT` (M-8).
3. `provenance.repo_head` is resolvable in the PR and `operational.probe_script_blob_sha1` ==
   `git hash-object engineering/runbooks/macos-probe.sh` at that head (M-7/§5.3 INV-003).
4. `track == "A"` ⇒ every Track-B verdict key must be exactly `NOT_ATTEMPTED`/`false`; a Track-A
   report claiming `ACCEPTED` is invalid.
5. `track == "B"` ⇒ `signing_identity_class == DEVELOPER_ID` ∧ `hardened_runtime == PRESENT` ∧
   `secure_timestamp == PRESENT` ∧ `get_task_allow_present == false` ∧
   `notary_submit == ACCEPTED` ∧ `stapler_validate == WORKED` ∧
   `spctl_assess == ACCEPTED_NOTARIZED_DEVELOPER_ID` ∧ `submission_uuid` present in the
   committed `notary-log-*.json` ∧ `tree_clean_after_run == true`; otherwise
   `TRACK_B_PARTIAL` and P1-11 stays open.
6. `signing_identity_class == ADHOC` ∧ `notary_submit == ACCEPTED` ⇒ hard reject (documented
   certificate-class impossibility; control C-26's deliberately-unsigned submission).
7. `notary_submit == INVALID` ⇒ `notary_log_committed == true` (an unexplained invalid is
   worthless).
8. `hardened_runtime == PRESENT` on a tree whose `hardened_runtime_key_count == 0` ⇒ reject
   (report contradicts the Linux-measurable pbxproj).
9. `verdicts.plist_unexpanded_placeholders > 0` ⇒ reject unconditionally (PR #3 AC-003/INV-003).
10. `selftest.* == PASS` all three, else reject the report as producer-broken.

### 6.4 Markdown wrapper (`handout-clean-macOS-v3.md`) template

```
# macOS clean-machine handout v3 — P1-11 remaining (signing / notarization / archive)
Snapshot: head <sha>, tree_fingerprint <fp>, verifier blob <sha1>, probe blob <sha1>.
Rule: no item here is closed by a Linux verdict (PR #3 AC-010).

## C-00 preparation        → table: step | command | observed | PASS|FAIL|NOT_ATTEMPTED | control that flipped
## Track A (C-10…C-16)     → same table; one row per §2 step, `raw=` quote of the probe line
## Track B (C-20…C-31)     → same table; every row names the human who typed it
## Artifact digests        → artifact sha256, cdhash, submission uuid, committed file blob ids
## Divergences             → one row per mismatch with the expectation, with the probe line quoted verbatim
## What this run does NOT prove → §3.5 Class 2/3 list, §1 retention list
```

Row semantics: `PASS` only if the observation equals the expectation of this document; a
mismatch is an audit result, never something to re-shoot until it matches (verbatim rule from
`…7db1f3/evidence/perfile/macos-validation-handout.md` §3 — keep it, it is the anti-fabrication
clause).

## 7. Open items, blockers, honesty conditions

1. **B-1 blocker for Track B in general:** `ENABLE_HARDENED_RUNTIME` + a real identity are a
   *product* change that PR #3 explicitly gated behind a green M-01′ (`FORBID-002`). Wave-D must
   not smuggle it. Consequence: wave-D can deliver Track A + the contract, and Track B remains a
   handout. P1-11 stays "partially closed" until then.
2. **`CODE_SIGN_INJECT_BASE_ENTITLEMENTS` is UNVERIFIED** — absent from `project.pbxproj`
   (M-11) and Apple does not publish the default; only C-24's `-showBuildSettings` on the real
   machine settles it. The contract must keep it as a measured field, not an assertion.
3. **`spctl` needs quarantine to be meaningful** and Apple documents assessment only for
   downloaded software; the `xattr` pairing is mandatory, and `gatekeeper_representative` must be
   reported. The "no quarantine ⇒ no check" wording itself stays FOLKLORE until a
   `docs_researcher` pass documents it (PR #3's analysis reached the same conclusion).
4. **`--output-format json` / `notarytool info` flags:** only `submit … --keychain-profile …
   --wait`, `log <id> --keychain-profile <p> <file>` and `stapler staple` are DOCUMENTED from
   the Apple page opened here. Re-cite `xcrun notarytool --help` on the machine and store the
   help capture before relying on any other flag.
5. **Single-witness limit:** no committed artifact proves the machine existed. §3.5 Class 2 is
   the ceiling; the PR body and receipts must not phrase Track A results as "release-ready".
6. **Notarization service state in 2026** was not re-verified beyond `altool` removal
   (2023-11-01, DOCUMENTED via developer.apple.com/developer-id/). If Apple has since changed
   required entitlements or the submission API, only `docs_researcher` can rule on it — a
   checklist published without that pass risks FOLKLORE in exactly the clause it is meant to
   enforce.
7. `.gitignore` lacks `build/`, `DerivedData/`, `*.xcworkspace`, `xcuserdata/` (M-9). Preferred
   fix is C-00.3 (out-of-tree roots) so this change touches no control-plane file; a `.gitignore`
   edit is a separate named decision with its own grant.

## Sources

Apple (opened this session):
- https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
- https://developer.apple.com/documentation/security/customizing-the-notarization-workflow
- https://developer.apple.com/developer-id/ (altool cut-off 2023-11-01)
Previously committed in-tree (PR #3): `analysis-docs_researcher.md` §2.1–2.3 for
hardened-runtime / Gatekeeper / get-task-allow / secure-timestamp citations.

Repo evidence cited: `engineering/runbooks/macos-probe.sh`;
`engineering/changes/20260921-…p1-11/evidence/release_layer_check.py` (`EXPECTED`,
`detect_runbook`, controls 20–22, `gather_reports`); same package's `release.md`,
`requirements.md` (AC-006/AC-009/AC-010), `change-spec.yaml` (AC evidence `path::symbol`),
`evidence/perfile/macos-validation-handout-v2.md`, `evidence/analysis-architect.md` §1–2,
`evidence/analysis-repo_explorer.md` §2.2; `engineering/changes/20260919-…7db1f3/evidence/
perfile/{macos-validation-handout.md,hygiene-pii.md,citation-integrity.md,pbxproj-build.md}` and
`evidence/harness/last-run.txt`; `.grok-stack/adaptive_grok/{util.py,verification.py,spec.py}`;
`.gitignore`; `Exolon.xcodeproj/project.pbxproj:1415-1443`.
