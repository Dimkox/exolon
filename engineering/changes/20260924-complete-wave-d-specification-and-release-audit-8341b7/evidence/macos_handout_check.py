#!/usr/bin/env python3
"""Wave-D checker: the macOS clean-machine handout contract (Track A / Track B).

Typed authority: ../change-spec.yaml (AC-001..AC-004, INV-002, FORBID-001, FORBID-002,
SIG-001). Design contract: ../evidence/analysis-integration_architect.md - §2 (checklist
C-10..C-31), §3 (handout placement and binding fields), §4 (the frozen probe surface, the
M-8 flush race, the M-9 build-root defect), §5 (agent/human boundary, forbidden argv list),
§6 (report schema and the ten consistency rules).

WHAT THIS TOOL DECIDES ON LINUX (Class 1 of integration §3.5)
  * the probe's text contract: every load-bearing token the merged checker greps is still
    present, the Track A archive steps exist, the M-8/M-9 fixes are real, verdicts are
    machine-readable;
  * the handout's internal consistency: schema, ten rules, binding fields;
  * that an absent run stays ABSENT (unverified) instead of laundering into a pass.

WHAT IT NEVER DECIDES (Class 3): that a Mac existed, that a bundle was signed, that
Gatekeeper accepted anything. A green verdict here means "the report is internally
consistent and bound to real git objects", never "release-ready" (PR #3 AC-010).

rc contract
  0  every requested check behaved as expected
  1  at least one check went red, or --report found the evidence ABSENT/FAIL/STALE
  2  usage error or an unreadable tree

Subcommands
  (default)          run the named checks
  --report           print the single machine-readable MACOS_EVIDENCE line
  --derive TXT       derive the report JSON from a probe transcript (§6.1: the JSON is
                     derived from the TXT, never written by hand)

Stdlib only, no network, no writes outside a temp scratch dir and the explicit --out-json.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

# --- addresses ---------------------------------------------------------------
CHANGE_ID = "20260924-complete-wave-d-specification-and-release-audit-8341b7"
CHANGE_DIR = f"engineering/changes/{CHANGE_ID}"
PROBE_REL = "engineering/runbooks/macos-probe.sh"
SCHEMA_REL = "engineering/contracts/schemas/macos-probe-report-v1.schema.json"
HANDOUT_REL = f"{CHANGE_DIR}/evidence/macos-handout"
HANDOUT_README_REL = f"{HANDOUT_REL}/README.md"
LEDGER_REL = "Exolon/GameCore/Diagnostics/StageBoundaryLedger.swift"
PR3_DIR = "engineering/changes/20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698"
MERGED_CHECKER_REL = f"{PR3_DIR}/evidence/release_layer_check.py"
PBXPROJ_REL = "Exolon.xcodeproj/project.pbxproj"
ENTITLEMENTS_REL = "Exolon/Exolon.entitlements"
CODE_SIGN_SENTINEL = 'CODE_SIGN_IDENTITY = "-";'
SCHEMA_ID = "exolon.macos-probe-report/1"
STACK_UTIL_REL = ".grok-stack/adaptive_grok/util.py"
PENDING_REASON = "pending wave-A merge"

# Which phase the runner was asked to certify. D-2 is the tree this change writes now;
# D-1 is the same files after wave A merges and the hardened-runtime pbxproj edit lands.
# The merged checker's verdict is different in the two phases BY DESIGN (the documented
# cutover), so the assertion has to know which one it is judging.
PHASE = "D2"

# Guard tokens pinned by integration §4-D. Renaming one is a product change: measured as
# M-7 (renaming EXOLON_FORBIDDEN_ARGV reddened exactly one AC of the additive verifier).
PROBE_GUARD_TOKENS = (
    "EXOLON_HUMAN_SIGNING_RUN",
    "WITH_SIGNING",
    "EXOLON_NOTARY_PROFILE",
    "EXOLON_FORBIDDEN_ARGV",
    "EXOLON_FORBIDDEN_ENV_NAMES",
    "signing_track_verdict=REFUSED",
    "probe_report_saved",
    "report_flush_verified",
    "report_lines_expected",
    "report_lines_written",
    "SYMROOT",
    "OBJROOT",
)

# Key names cited by the merged package (release.md §Metrics, requirements.md
# §Observability) and frozen by integration §4-A.4: they must stay byte-identical.
PROBE_CITED_KEYS = (
    "version_single_source", "build_version_single_source", "plist_unexpanded_placeholders",
    "showdestinations_rc", "archive_rc", "codesign_flags", "hardened_runtime",
    "verdict_shared_scheme", "build_rc", "app_path_found", "verdict_toolchain",
    "plist_CFBundleShortVersionString", "plist_CFBundleVersion", "settings_MARKETING_VERSION",
    "bundle_resources_tmx", "bundle_has_gif", "bundle_has_generated_terrain", "defaults_domain",
    "defaults_domain_present", "defaults_keys", "play_answers", "product_log_calls",
    "level_warp_calls", "checkpoint_reader_calls", "codesign", "spctl", "arch", "os_version",
    "hostname_redacted", "probe_output_will_be_written", "build_log", "build_tail",
    "list_json_schemes", "shared_scheme_file_present", "shared_scheme_tracked",
    "settings_CURRENT_PROJECT_VERSION", "plist_LSMinimumSystemVersion", "sdk",
    "xcodebuild", "archive_path_present", "archive_tail", "showdestinations_tail",
    "defaults_keys", "high_score_line", "checkpoint_line", "capture",
)

# New Track A keys required by integration §2 (C-10..C-16) and §4-D. A missing key means
# the step is prose, not a measurement.
TRACK_A_KEYS = (
    "tree_clean_before_run", "tree_clean_after_run", "build_roots_out_of_tree",
    "verdict_scratch_root", "symroot", "objroot", "archive_path_out_of_tree",
    "archive_failure_class", "verdict_archive", "archived_app_present",
    "archived_plist_CFBundleShortVersionString", "archived_plist_CFBundleVersion",
    "archived_version_single_source", "archived_plist_unexpanded_placeholders",
    "archived_codesign_verify_rc", "archived_codesign_flags", "archived_codesign_timestamp",
    "archived_hardened_runtime", "archived_entitlements_count",
    "archived_entitlements_get_task_allow", "archived_signature", "archived_team_id_hash",
    "spctl_assess_verdict", "xattr_quarantine_present", "gatekeeper_representative",
    "play_observations", "repo_head", "probe_git_blob_sha1", "probe_bash_version",
    "tree_fingerprint_source", "artifact_sha256", "cdhash",
)

# Track B keys: they must exist and read NOT_ATTEMPTED whenever the gate is off (§4-D).
TRACK_B_KEYS = (
    "signing_track", "signing_track_verdict", "settings_CODE_SIGN_IDENTITY",
    "settings_CODE_SIGN_INJECT_BASE_ENTITLEMENTS", "codesign_flags_runtime_token",
    "notary_profile_present", "developer_id_identity_count", "notarytool_submit_rc",
    "notary_status", "notary_log_committed", "submission_uuid", "stapler_staple",
    "stapler_validate", "export_archive_rc", "identity_policy",
)

SELFTEST_KEYS = (
    "probe_selftest_signing_parser", "probe_selftest_notary_status_parser",
    "probe_selftest_verdict_not_collapsed", "probe_selftest_flush_barrier",
    "probe_selftest_forbidden_argv_scanner",
)

VERDICT5 = ("PASS", "FAIL", "NOT_ATTEMPTED", "TOOL_ABSENT", "REFUSED")

# integration §5.2.3: none of these invocation literals may appear in the probe at all,
# not even in a comment, so no agent can hand it a credential even by accident. The
# probe's own defence list is written with character classes for exactly this reason.
FORBIDDEN_PROBE_LITERALS = (
    "--apple-id", "--apple_id", "--password", "--provisioning-profile-path",
    "--mobileprovision", ".mobileprovision", ".p12", ".p8", "--keychain ",
    "--sign", "store-credentials", "unlock-keychain", "altool", "find-identity",
    "PRIVATE KEY", "-----BEGIN",
)

# integration §5.2.6: flags a Track-B operator must never type (documented in the README).
FORBIDDEN_FLAGS = (
    "-allowProvisioningUpdates", "-allowProvisioningDeviceRegistration",
    "notarytool store-credentials", "--apple-id", "--password", "codesign -s",
    "security unlock-keychain", "xcrun altool",
)

# FORBID-002: the exact expected post-D-1 red set of the merged checker.
DECLARED_CUTOVER_SET = frozenset({"hardened_runtime_key_count", "hardened_deferral_recorded"})

# Measured in D-2 (before the pbxproj edit) and re-measured after it: control 8 of the merged
# checker, `hardened_key_mutation_detected`, installs the key with
# `replace(anchor, anchor + KEY, 1)` and asserts the result is asymmetric. Once the key is
# legitimately present in BOTH target configs, that one-sided install is a duplicate of an
# identical setting - the parsed buildSettings dicts stay equal, so the control can never pass
# again. It is a pre-repayment instrument, and wave D must not edit PR #3's immutable package to
# make it look green: it declares it here instead. See evidence/cutover.md.
DECLARED_CUTOVER_CONTROLS = frozenset({"hardened_key_mutation_detected"})

KV_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)=(.*)$")
EMIT_RE = re.compile(r"""(?:emit|printf)\s+['"]([A-Za-z][A-Za-z0-9_]*)=""")
FN_BEGIN = "# >>> probe-check:begin {name}"
FN_END = "# <<< probe-check:end {name}"

VERDICT_WORDS = re.compile(
    r"\b(PASS|FAIL|ACCEPTED|REJECTED|NOT_ATTEMPTED|TOOL_ABSENT|REFUSED|MATCH|MISMATCH"
    r"|PRESENT|ABSENT|WORKED|Accepted|rejected)\b")

RULES = {
    "R1": "schema id and required keys (a missing key is never defaulted to pass)",
    "R2": "report_flush_verified + raw digest + line count bind the committed TXT",
    "R3": "repo_head resolves as a commit; probe blob sha1 and tree_fingerprint match",
    "R4": "track A => every Track-B field is NOT_ATTEMPTED/false",
    "R5": "track B => the full conjunction, else TRACK_B_PARTIAL",
    "R6": "an adhoc signature can never coexist with an Accepted submission",
    "R7": "an Invalid submission must carry a committed Apple log",
    "R8": "hardened_runtime=PRESENT must agree with the committed pbxproj",
    "R9": "unexpanded Info.plist placeholders reject the report outright",
    "R10": "producer self-test must be all-PASS or the report is untrusted",
}
STALE_RULES = ("R3",)


class CheckFailure(Exception):
    """A named check went red."""


class _Missing:
    def __repr__(self) -> str:  # pragma: no cover
        return "<MISSING>"


MISSING = _Missing()


# --- small utilities ---------------------------------------------------------
def repo_root(explicit: str | None) -> pathlib.Path:
    if explicit:
        return pathlib.Path(explicit).resolve()
    here = pathlib.Path(__file__).resolve()
    for cand in [here, *here.parents]:
        if (cand / "Exolon.xcodeproj").is_dir() and (cand / ".git").exists():
            return cand
    raise SystemExit("repository root not found - pass --root")


def rd(root: pathlib.Path, rel: str) -> str:
    p = root / rel
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""


def run(cmd: list[str], cwd: pathlib.Path | None = None,
        timeout: int = 180) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True,
                          text=True, check=False, timeout=timeout)


def git(root: pathlib.Path, *args: str) -> str:
    return run(["git", "-C", str(root), *args]).stdout.strip()


def git_ok(root: pathlib.Path, *args: str) -> bool:
    return run(["git", "-C", str(root), *args]).returncode == 0


def blob_sha1(data: bytes) -> str:
    """The same expression the merged checker uses for report pins (integration §3.3)."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def detect_phase(root: pathlib.Path) -> str:
    """D-1 is the phase where wave A's ledger exists AND the hardened repayment landed."""
    if (root / LEDGER_REL).is_file() and hardened_count_in_tree(root) >= 2:
        return "D1"
    return "D2"


def tree_fingerprint(root: pathlib.Path) -> str:
    """Re-derive with the repository's own fingerprint function when it is importable."""
    mod_path = root / STACK_UTIL_REL
    if not mod_path.is_file():
        return ""
    spec = importlib.util.spec_from_file_location("handout_stack_util", mod_path)
    if spec is None or spec.loader is None:
        return ""
    mod = importlib.util.module_from_spec(spec)
    sys.modules["handout_stack_util"] = mod
    try:
        spec.loader.exec_module(mod)
        return str(mod.tree_fingerprint(root))
    except Exception:  # noqa: BLE001 - a missing/unimportable stack is "cannot re-derive"
        return ""


def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def kv_pairs(text: str) -> list[tuple[str, str]]:
    out = []
    for line in text.splitlines():
        m = KV_RE.match(line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def kv_map(text: str) -> dict[str, str]:
    d: dict[str, str] = {}
    for k, v in kv_pairs(text):
        d.setdefault(k, v)
    return d


def first_token(value: str) -> str:
    value = (value or "").split(" (")[0].strip()
    return value.split()[0] if value else ""


def emit_keys(text: str) -> set[str]:
    return {m.group(1) for m in (EMIT_RE.search(ln) for ln in text.splitlines()) if m}


# --- mini JSON-schema validator (stdlib only, no third-party dependency) -----
def _type_ok(instance, want: str) -> bool:
    if want == "object":
        return isinstance(instance, dict)
    if want == "array":
        return isinstance(instance, list)
    if want == "string":
        return isinstance(instance, str)
    if want == "boolean":
        return isinstance(instance, bool)
    if want == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if want == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if want == "null":
        return instance is None
    return True


def _resolve_ref(ref: str, root_schema: dict) -> dict:
    if not ref.startswith("#/"):
        raise CheckFailure(f"schema: unsupported $ref {ref}")
    node: object = root_schema
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            raise CheckFailure(f"schema: dangling $ref {ref}")
        node = node[part]
    if not isinstance(node, dict):
        raise CheckFailure(f"schema: $ref {ref} does not resolve to an object")
    return node


def schema_validate(instance, schema: dict, *, defs_root: dict | None = None,
                    path: str = "$") -> list[str]:
    """Validate against the JSON-Schema subset this repository commits:
    $ref(#/...), type, required, properties, additionalProperties, items, minItems,
    enum, const, pattern, minimum, maximum, allOf, anyOf."""
    root_schema = defs_root if defs_root is not None else schema
    errs: list[str] = []
    if "$ref" in schema:
        errs += schema_validate(instance, _resolve_ref(schema["$ref"], root_schema),
                                defs_root=root_schema, path=path)
        schema = {k: v for k, v in schema.items() if k != "$ref"}
    want_type = schema.get("type")
    if want_type is not None:
        wants = want_type if isinstance(want_type, list) else [want_type]
        if not any(_type_ok(instance, w) for w in wants):
            errs.append(f"{path}: type {type(instance).__name__} not in {wants}")
            return errs
    if "const" in schema and instance != schema["const"]:
        errs.append(f"{path}: expected const {schema['const']!r}, got {instance!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: {instance!r} is not in the declared enum")
    if isinstance(instance, dict):
        for req in schema.get("required", []):
            if req not in instance:
                errs.append(f"{path}: missing required key '{req}'")
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in instance:
                errs += schema_validate(instance[key], sub, defs_root=root_schema,
                                        path=f"{path}.{key}")
        add = schema.get("additionalProperties", True)
        for key in instance:
            if key in props:
                continue
            if add is False:
                errs.append(f"{path}: unexpected key '{key}'")
            elif isinstance(add, dict):
                errs += schema_validate(instance[key], add, defs_root=root_schema,
                                        path=f"{path}.{key}")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errs.append(f"{path}: fewer than {schema['minItems']} items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(instance):
                errs += schema_validate(item, item_schema, defs_root=root_schema,
                                        path=f"{path}[{i}]")
    if isinstance(instance, str) and "pattern" in schema:
        if not re.search(schema["pattern"], instance):
            errs.append(f"{path}: {instance!r} violates pattern {schema['pattern']!r}")
    if isinstance(instance, int) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errs.append(f"{path}: {instance} > maximum {schema['maximum']}")
    if "allOf" in schema:
        for sub in schema["allOf"]:
            errs += schema_validate(instance, sub, defs_root=root_schema, path=path)
    if "anyOf" in schema:
        branches = [schema_validate(instance, sub, defs_root=root_schema, path=path)
                    for sub in schema["anyOf"]]
        if all(branches):
            errs.append(f"{path}: matches no anyOf branch")
    return errs


def load_schema(root: pathlib.Path) -> dict:
    text = rd(root, SCHEMA_REL)
    if not text.strip():
        raise CheckFailure(f"{SCHEMA_REL} is missing or empty "
                           "(change-spec contracts.json_schema names it)")
    schema = json.loads(text)
    if schema.get("$id") != SCHEMA_ID:
        raise CheckFailure(f"{SCHEMA_REL} $id={schema.get('$id')!r} != {SCHEMA_ID!r}")
    return schema


# --- probe text contract -----------------------------------------------------
def merged_probe_text(root: pathlib.Path) -> str:
    shown = run(["git", "-C", str(root), "show", f"HEAD:{PROBE_REL}"])
    if shown.returncode != 0 or not shown.stdout.strip():
        raise CheckFailure(f"cannot read HEAD:{PROBE_REL} with git show "
                           "(the token-preservation net needs the merged text)")
    return shown.stdout


def probe_new_lines(legacy: str, new: str) -> list[str]:
    old = set(legacy.splitlines())
    return [ln for ln in new.splitlines() if ln not in old]


def archive_call_is_gated(text: str) -> bool:
    """True when the archive invocation still hides behind WITH_ARCHIVE (AC-001 forbids it)."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if "xcodebuild" in ln and "archive" in ln:
            window = "\n".join(lines[max(0, i - 8):i + 1])
            if re.search(r'WITH_ARCHIVE:-0\}" = "1"', window):
                return True
    return False


def check_probe_text(root: pathlib.Path, text: str | None = None) -> list[str]:
    """AC-001/AC-002/AC-004 text invariants. Pure over text so a control can corrupt it."""
    if text is None:
        text = rd(root, PROBE_REL)
    if not text.strip():
        return [f"{PROBE_REL} is missing"]
    v: list[str] = []
    legacy = merged_probe_text(root)
    keys = emit_keys(text)
    for key in sorted(emit_keys(legacy)):
        if key not in keys:
            v.append(f"probe: merged emit-key '{key}' disappeared (load-bearing; M-7 class)")
    for key in PROBE_CITED_KEYS + TRACK_A_KEYS + TRACK_B_KEYS + SELFTEST_KEYS:
        if key not in keys:
            v.append(f"probe: required key '{key}' is never emitted")
    for tok in PROBE_GUARD_TOKENS:
        if tok not in text:
            v.append(f"probe: guard token '{tok}' missing (pinned by integration §4-D)")
    for ln in probe_new_lines(legacy, text):
        if "EXPECTED" not in ln:
            continue
        for pat in (r"no shared scheme", r"\b0 \.xcscheme", r"shared scheme.*ABSENT",
                    r"CFBundleShortVersionString\s*=\s*0\.3", r"\.xcscheme\)?\s*=\s*0",
                    r"shared_xcschemes\s*[:=]\s*0"):
            if re.search(pat, ln):
                v.append(f"probe: a new line re-introduces a stale EXPECTED claim ({pat})")
    for sec in "ABCDEFG":
        if not re.search(rf'^\s*emit "## {sec}\.', text, re.M):
            v.append(f"probe: section header '## {sec}.' lost")
    for sec in ("B3", "H", "I", "J", "K"):
        if not re.search(rf'^\s*emit "## {sec}\.', text, re.M):
            v.append(f"probe: extension section '## {sec}.' missing")
    for code, why in (("75", "non-Darwin"), ("66", "missing project"),
                      ("73", "cannot write --out"), ("2", "usage"), ("77", "refused"),
                      ("78", "misconfiguration")):
        if not re.search(rf"(?:^|[;&]|\bthen\b)\s*exit {code}\b", text, re.M):
            v.append(f"probe: exit {code} ({why}) is no longer reachable")
    if "set -uo pipefail" not in text:
        v.append("probe: 'set -uo pipefail' lost (a probe must survive what it measures)")
    if re.search(r"^set -e", text, re.M):
        v.append("probe: 'set -e' must never be added to a probe")
    if "$!" in text:
        v.append("probe: uses $! - macOS bash 3.2 does not set it for process substitution, "
                 "so the flush barrier must not depend on it (M-8)")
    if archive_call_is_gated(text):
        v.append("probe: the archive is still behind WITH_ARCHIVE - AC-001 requires Track A's "
                 "archive step to be mandatory")
    for token in ("plutil", "--verify --deep --strict", "--entitlements",
                  "Info.plist", ".xcarchive"):
        if token not in text:
            v.append(f"probe: .xcarchive content inspection needs '{token}'")
    for word in VERDICT5:
        if word not in text:
            v.append(f"probe: the 5-valued verdict vocabulary is missing {word}")
    for token in ('SYMROOT=', 'OBJROOT=', 'build_roots_out_of_tree=yes',
                  'build_roots_out_of_tree=no', 'verdict_scratch_root=OUT_OF_TREE',
                  'verdict_scratch_root=INSIDE_CLONE'):
        if token not in text:
            v.append(f"probe: the M-9 build-root contract needs '{token}'")
    if re.search(r'SYMROOT="?\$?\{?PWD\}?/?build', text) or "EXOLON_PROBE_SCRATCH=\"$PWD" in text:
        v.append("probe: a build root points inside the clone (M-9: the tree fingerprint "
                 "changes and every local receipt goes stale)")
    if "/Use" "rs/" in text:
        v.append("probe: an absolute home path is baked in (integration §5.2.5 PII rule)")
    for lit in FORBIDDEN_PROBE_LITERALS:
        if lit in text:
            v.append(f"probe: forbidden credential-shaped literal {lit!r} present "
                     "(integration §5.2.3 forbids it anywhere, comments included)")
    if "EXOLON_NOTARY_PROFILE" in text and (
            "EXOLON_NOTARY_PROFILE_RE=" not in text
            or 'grep -Eq -e "$EXOLON_NOTARY_PROFILE_RE"' not in text):
        v.append("probe: EXOLON_NOTARY_PROFILE is used without a validated name-only pattern "
                 "(a profile NAME is not a secret, and a flag must not fit into its place)")
    if "signing_track_verdict=REFUSED" not in text:
        v.append("probe: no refusal verdict token")
    return v


def extract_probe_fn(text: str, name: str) -> str:
    begin = FN_BEGIN.format(name=name)
    end = FN_END.format(name=name)
    if begin not in text or end not in text:
        raise CheckFailure(f"probe: region '{name}' is not delimited by {begin!r} .. {end!r} "
                           "(the checker executes shipped bytes, never a re-typed copy)")
    return text.split(begin, 1)[1].split(end, 1)[0]


def scanner_const(text: str, var: str) -> str:
    m = re.search(rf"^{var}='([^']*)'", text, re.M)
    if not m:
        raise CheckFailure(f"probe: {var} is not a single-quoted top-level literal, so the "
                           "checker cannot execute the shipped scanner")
    return m.group(1)


def run_probe_fn(text: str, name: str, body: str,
                 prelude: str = "") -> subprocess.CompletedProcess:
    script = ("set -uo pipefail\nexec 3>&2\n" + prelude
              + extract_probe_fn(text, name) + "\n" + body + "\n")
    with tempfile.TemporaryDirectory(prefix="exolon-probe-check-") as tmp:
        spath = pathlib.Path(tmp) / "harness.sh"
        spath.write_text(script, encoding="utf-8")
        return run(["bash", str(spath)], timeout=120)


# --- TXT -> JSON derivation (integration §6.1: never by hand) ----------------
DERIVE_MAP = {
    "shared_scheme": ("verdict_shared_scheme", "token"),
    "build_rc": ("build_rc", "int"),
    "build": ("build_rc", "rc_pass"),
    "version_single_source": ("version_single_source", "token"),
    "build_version_single_source": ("build_version_single_source", "token"),
    "plist_unexpanded_placeholders": ("plist_unexpanded_placeholders", "int"),
    "showdestinations_rc": ("showdestinations_rc", "int"),
    "archive_rc": ("archive_rc", "int"),
    "archive": ("archive_rc", "rc_pass"),
    "archive_failure_class": ("archive_failure_class", "token"),
    "hardened_runtime": ("archived_hardened_runtime", "token"),
    "signing_identity_class": ("archived_signature", "sig_class"),
    "secure_timestamp": ("archived_codesign_timestamp", "token"),
    "get_task_allow_present": ("archived_entitlements_get_task_allow", "yesno_bool"),
    "notary_profile_present": ("notary_profile_present", "token"),
    "notary_submit": ("notary_status", "notary"),
    "notary_log_committed": ("notary_log_committed", "yesno_bool"),
    "stapler_staple": ("stapler_staple", "token"),
    "stapler_validate": ("stapler_validate", "token"),
    "spctl_assess": ("spctl_assess_verdict", "spctl"),
    "gatekeeper_representative": ("gatekeeper_representative", "yesno_bool"),
    "play_observations": ("play_observations", "play"),
}
DERIVE_REQUIRED = (
    "tree_clean_before_run", "tree_clean_after_run", "report_flush_verified",
    "report_lines_expected", "report_lines_written", "repo_head", "probe_git_blob_sha1",
    "probe_bash_version", "signing_track", "os_version", "arch",
    "artifact_sha256", "cdhash", "submission_uuid", "xcodebuild",
) + tuple(key for key, _ in DERIVE_MAP.values()) + SELFTEST_KEYS


def _transform(kind: str, raw: str):
    tok = first_token(raw)
    if kind == "token":
        return tok
    if kind == "int":
        try:
            return int(tok)
        except ValueError:
            return tok
    if kind == "rc_pass":
        try:
            return "PASS" if int(tok) == 0 else "FAIL"
        except ValueError:
            return "NOT_ATTEMPTED"
    if kind == "yesno_bool":
        return {"yes": True, "no": False}.get(tok, str(tok).upper() == "TRUE")
    if kind == "sig_class":
        low = raw.lower()
        if "developer id application" in low:
            return "DEVELOPER_ID"
        if "apple development" in low:
            return "APPLE_DEVELOPMENT"
        if "adhoc" in low:
            return "ADHOC"
        return "NOT_ATTEMPTED" if tok == "NOT_ATTEMPTED" else "UNKNOWN"
    if kind == "notary":
        for needle, mapped in (("accepted", "ACCEPTED"), ("invalid", "INVALID"),
                               ("in progress", "IN_PROGRESS"), ("refused", "REFUSED"),
                               ("not_attempted", "NOT_ATTEMPTED"),
                               ("tool_absent", "TOOL_ABSENT")):
            if needle in raw.lower():
                return mapped
        return tok or "NOT_ATTEMPTED"
    if kind == "spctl":
        low = raw.lower()
        if "notarized developer id" in low:
            return "ACCEPTED_NOTARIZED_DEVELOPER_ID"
        if "accepted" in low:
            return "ACCEPTED_OTHER"
        if "rejected" in low:
            return "REJECTED"
        return "NOT_ATTEMPTED" if low == "not_attempted" else "NOT_RUN"
    if kind == "play":
        up = raw.upper()
        if "COMPLETE" in up and "PARTIAL" not in up:
            return "COMPLETE"
        if "PARTIAL" in up:
            return "PARTIAL"
        return "SKIPPED"
    raise CheckFailure(f"derive: unknown transform {kind}")


def derive_report(txt: bytes, *, attested_by: str = "unattested", human_present: bool = False,
                  now: str | None = None) -> dict:
    """Deterministically build the report JSON from the probe's own raw transcript."""
    text = txt.decode("utf-8", errors="replace")
    kv = kv_map(text)
    absent = sorted(k for k in DERIVE_REQUIRED if k not in kv)
    if absent:
        raise CheckFailure("derive: the transcript carries no value for "
                           + ", ".join(absent)
                           + " - refusing to fill verdicts with defaults")
    if kv.get("report_flush_verified") != "yes":
        raise CheckFailure("derive: report_flush_verified != yes - a truncated transcript must "
                           "never become a committed report (M-8)")
    verdicts = {}
    for field, (key, kind) in DERIVE_MAP.items():
        verdicts[field] = _transform(kind, kv[key])
    # verdict_toolchain is the probe's failure line: a healthy run never prints it. The
    # PASS reading is still an observation (xcodebuild present and not ABSENT), not a default.
    if "verdict_toolchain" in kv:
        verdicts["toolchain"] = first_token(kv["verdict_toolchain"])
    elif first_token(kv.get("xcodebuild", "")) == "ABSENT":
        verdicts["toolchain"] = "FAIL_NO_XCODE"
    else:
        verdicts["toolchain"] = "PASS"
    track = "B" if first_token(kv.get("signing_track", "")) == "HUMAN" else "A"
    doc = {
        "schema": SCHEMA_ID,
        "generated_utc": now or now_utc(),
        "track": track,
        "operational": {
            "probe_exit_code": 0,
            "probe_bash_version": kv["probe_bash_version"],
            "probe_script_blob_sha1": first_token(kv["probe_git_blob_sha1"]),
            "verifier_script_blob_sha1": "",
            "report_flush_verified": True,
            "report_lines_expected": int(first_token(kv["report_lines_expected"]) or 0),
            "report_lines_written": int(first_token(kv["report_lines_written"]) or 0),
            "raw_report_sha256": sha256_bytes(txt),
            "tree_clean_before_run": kv["tree_clean_before_run"] == "yes",
            "tree_clean_after_run": kv["tree_clean_after_run"] == "yes",
        },
        "environment": {
            "macos_version": first_token(kv["os_version"]),
            "arch": first_token(kv["arch"]),
            "xcodebuild": kv["xcodebuild"].strip() or "na",
            "sdks": [s for s in kv.get("sdk", "").strip("[]").split() if s] or ["na"],
            "host_hash": first_token(kv.get("hostname_redacted", "na")),
        },
        "provenance": {
            "repo_head": first_token(kv["repo_head"]),
            "tree_fingerprint": first_token(kv.get("tree_fingerprint", "")),
            "artifact_sha256": None if kv["artifact_sha256"] in ("none", "")
            else first_token(kv["artifact_sha256"]),
            "cdhash": None if kv["cdhash"] in ("none", "") else first_token(kv["cdhash"]),
            "submission_uuid": None if kv["submission_uuid"] in ("none", "")
            else first_token(kv["submission_uuid"]),
        },
        "verdicts": verdicts,
        "raw_kv": {k: v for k, v in kv_pairs(text)},
        "selftest": {
            "signing_parser": kv["probe_selftest_signing_parser"],
            "notary_status_parser": kv["probe_selftest_notary_status_parser"],
            "verdict_not_collapsed": kv["probe_selftest_verdict_not_collapsed"],
        },
        "track_b": None,
        "attestation": {
            "class_1_rederivable": ["digests", "blob binding", "schema consistency",
                                    "probe text invariants"],
            "class_2_attested": ["build", "archive", "codesign", "notary", "staple", "spctl"],
            "class_3_excluded": ["built-bundle truth", "scheme loader acceptance",
                                 "Gatekeeper outcome"],
            "operator_attested_by": attested_by,
            "human_present": bool(human_present),
        },
    }
    if track == "B":
        uuid = doc["provenance"]["submission_uuid"] or "unknown"
        doc["track_b"] = {
            "identity_hash": first_token(kv.get("archived_team_id_hash", "")),
            "authority_chain": [first_token(kv.get("notary_status", ""))],
            "notary_info_file": f"notary-info-{uuid}.txt",
            "notary_log_file": f"notary-log-{uuid}.json",
            "container": first_token(kv.get("export_container", "dmg")),
            "stapled_target": first_token(kv.get("stapled_target", "container")),
            "manual_smoke": {k: first_token(kv.get(f"manual_smoke_{k}", "NOT_ATTEMPTED"))
                             for k in ("gamepad", "hud", "audio", "debugger_attach")},
        }
    return doc


# --- handout binding + the ten rules ----------------------------------------
def binding_fields(root: pathlib.Path, txt: bytes) -> dict:
    probe_path = root / PROBE_REL
    return {
        "operational": {
            "probe_script_blob_sha1": blob_sha1(probe_path.read_bytes())
            if probe_path.is_file() else "",
            "raw_report_sha256": sha256_bytes(txt),
        },
        "provenance": {
            "repo_head": git(root, "rev-parse", "HEAD"),
            "tree_fingerprint": tree_fingerprint(root),
        },
    }


def hardened_count_in_tree(root: pathlib.Path) -> int:
    return rd(root, "Exolon.xcodeproj/project.pbxproj").count("ENABLE_HARDENED_RUNTIME")


def rule_checks(root: pathlib.Path, doc: dict, txt: bytes | None = None,
                report_path: pathlib.Path | None = None,
                hardened_count: int | None = None) -> list[str]:
    """Integration §6.3 rules 1..10 as decidable predicates, each tagged R<n>."""
    v: list[str] = []
    op = doc.get("operational", {}) or {}
    verdicts = doc.get("verdicts", {}) or {}
    prov = doc.get("provenance", {}) or {}
    track = doc.get("track")

    if doc.get("schema") != SCHEMA_ID:
        v.append(f"R1 schema id {doc.get('schema')!r} != {SCHEMA_ID!r}")

    if txt is None and report_path is not None:
        sibling = report_path.with_suffix(".txt")
        if sibling.is_file():
            txt = sibling.read_bytes()
    if txt is not None:
        if op.get("raw_report_sha256") != sha256_bytes(txt):
            v.append("R2 raw_report_sha256 does not match the committed TXT bytes")
        want_lines = len(txt.decode("utf-8", "replace").splitlines())
        if op.get("report_lines_written") != want_lines:
            v.append(f"R2 report_lines_written={op.get('report_lines_written')!r} != wc -l TXT "
                     f"({want_lines}) - the M-8 race is exactly this window")
        if op.get("report_lines_expected") != want_lines:
            v.append("R2 report_lines_expected does not match the committed TXT length")
        kv = kv_map(txt.decode("utf-8", "replace"))
        if kv.get("report_flush_verified") != "yes":
            v.append("R2 the transcript does not carry report_flush_verified=yes (§4-E)")
        for key, val in (doc.get("raw_kv") or {}).items():
            if kv.get(key) != val:
                v.append(f"R2 raw_kv.{key} disagrees with the transcript bytes")
                break
    elif report_path is not None:
        v.append("R2 no sibling probe-report-*.txt to bind the digest to")
    if op.get("report_flush_verified") is not True:
        v.append("R2 operational.report_flush_verified is not true - reject outright (§4-E)")

    head = prov.get("repo_head", "")
    if not re.fullmatch(r"[0-9a-f]{40}", head or ""):
        v.append(f"R3 provenance.repo_head {head!r} is not a full sha1")
    elif not git_ok(root, "cat-file", "-e", f"{head}^{{commit}}"):
        v.append(f"R3 provenance.repo_head {head} does not resolve as a commit in this "
                 "repository (STALE: the run measured a tree that does not exist here)")
    live_blob = blob_sha1((root / PROBE_REL).read_bytes()) if (root / PROBE_REL).is_file() else ""
    if not op.get("probe_script_blob_sha1"):
        v.append("R3 operational.probe_script_blob_sha1 is empty")
    elif live_blob and op.get("probe_script_blob_sha1") != live_blob:
        v.append("R3 the report was produced by a different probe text than the committed one "
                 "(INV-003)")
    fp = prov.get("tree_fingerprint", "")
    live_fp = tree_fingerprint(root)
    if not re.fullmatch(r"[0-9a-f]{64}", fp or ""):
        v.append(f"R3 provenance.tree_fingerprint {fp!r} is not a sha256 hex digest")
    elif live_fp and fp != live_fp:
        v.append("R3 tree_fingerprint differs from the current tree - STALE, never green (M-9)")

    if track == "A":
        # §6.3 rule 4 forbids a Track-A report claiming Track-B facts. Track A's own steps
        # C-12/C-13/C-14 legitimately observe the negative anchor (Signature=adhoc, no
        # Timestamp, spctl rejected), so the enforceable reading is "no positive claim":
        # nothing may assert a real identity, a secure timestamp, a stapled ticket or an
        # Accepted/Invalid notarization outcome. Narrower than a literal reading of rule 4
        # and recorded as a deviation; NOT_ATTEMPTED stays required for the notarization
        # and stapling fields, which Track A never touches at all.
        for key in ("stapler_staple", "stapler_validate", "notary_submit"):
            if verdicts.get(key) != "NOT_ATTEMPTED":
                v.append(f"R4 track=A but verdicts.{key}={verdicts.get(key)!r} - a Track-A run "
                         "never touches notarization or stapling")
        positive = {"notary_submit": ("ACCEPTED", "INVALID", "IN_PROGRESS"),
                    "signing_identity_class": ("DEVELOPER_ID",),
                    "secure_timestamp": ("PRESENT",),
                    "spctl_assess": ("ACCEPTED_NOTARIZED_DEVELOPER_ID",)}
        for key, banned in positive.items():
            if verdicts.get(key) in banned:
                v.append(f"R4 track=A claims {key}={verdicts.get(key)!r} (FORBID-001: a "
                         "Track-A run may never read as a signing or notarization verdict)")
        if doc.get("track_b") is not None:
            v.append("R4 track=A carries a track_b block")

    if track == "B":
        conj = {"signing_identity_class": "DEVELOPER_ID", "hardened_runtime": "PRESENT",
                "secure_timestamp": "PRESENT", "notary_submit": "ACCEPTED",
                "stapler_validate": "WORKED",
                "spctl_assess": "ACCEPTED_NOTARIZED_DEVELOPER_ID"}
        bad = [f"{k}={verdicts.get(k)!r}" for k, want in conj.items() if verdicts.get(k) != want]
        if verdicts.get("get_task_allow_present") is not False:
            bad.append("get_task_allow_present is not false")
        if not prov.get("submission_uuid"):
            bad.append("submission_uuid missing")
        if not op.get("tree_clean_after_run"):
            bad.append("tree_clean_after_run is not true")
        if prov.get("submission_uuid"):
            log = root / HANDOUT_REL / f"notary-log-{prov['submission_uuid']}.json"
            if not log.is_file():
                bad.append(f"notary-log-{prov['submission_uuid']}.json is not committed")
        if bad:
            v.append("R5 TRACK_B_PARTIAL (P1-11 stays open): " + ", ".join(bad))

    if verdicts.get("signing_identity_class") == "ADHOC" and verdicts.get("notary_submit") == "ACCEPTED":
        v.append("R6 an ad-hoc signature with an Accepted notarization is a documented "
                 "impossibility (Apple: Developer ID application certificates only)")

    if verdicts.get("notary_submit") == "INVALID" and verdicts.get("notary_log_committed") is not True:
        v.append("R7 notary_submit=INVALID must be paired with a committed Apple notary log")

    tree_count = hardened_count_in_tree(root) if hardened_count is None else hardened_count
    if verdicts.get("hardened_runtime") == "PRESENT" and tree_count == 0:
        v.append("R8 the report claims hardened_runtime=PRESENT but the committed "
                 "project.pbxproj has no ENABLE_HARDENED_RUNTIME setting")

    ph = verdicts.get("plist_unexpanded_placeholders")
    if isinstance(ph, int) and ph > 0:
        v.append("R9 plist_unexpanded_placeholders>0 rejects the report unconditionally "
                 "(PR #3 AC-003/INV-003)")

    st = doc.get("selftest") or {}
    for k in ("signing_parser", "notary_status_parser", "verdict_not_collapsed"):
        if k not in st:
            v.append(f"R10 selftest.{k} is missing")
        elif st[k] != "PASS":
            v.append(f"R10 selftest.{k}={st[k]!r}: the producer is broken, the report is untrusted")

    if (doc.get("attestation") or {}).get("operator_attested_by") != "owner":
        v.append("R1 attestation.operator_attested_by must be typed 'owner' (single-witness "
                 "facts are signed by a human, integration §3.3)")
    return v


def audit_report(root: pathlib.Path, doc: dict, txt: bytes | None = None,
                 report_path: pathlib.Path | None = None,
                 hardened_count: int | None = None) -> list[str]:
    """Schema + the ten rules, everything tagged."""
    try:
        schema = load_schema(root)
    except CheckFailure as exc:
        return [f"R1 {exc}"]
    errs = [f"R1 {e}" for e in schema_validate(doc, schema, defs_root=schema)]
    return errs + rule_checks(root, doc, txt=txt, report_path=report_path,
                              hardened_count=hardened_count)


def apply_pointer(doc: dict, pointer: str, value) -> None:
    parts = pointer.split(".")
    node: object = doc
    for part in parts[:-1]:
        node = node[part]  # type: ignore[index]
    if value is MISSING:
        del node[parts[-1]]
        return
    node[parts[-1]] = value  # type: ignore[index]


# --- synthetic fixture -------------------------------------------------------
def synth_txt_lines(root: pathlib.Path | None = None) -> list[str]:
    # the archived bundle's hardened-runtime observation must agree with the tree the report is
    # bound to: rule 8 forbids PRESENT-while-the-pbxproj-declares-nothing, so a fixture that
    # claimed ABSENT against a repaid tree would be describing a different build than this one
    hardened = "PRESENT" if hardened_count_in_tree(root or pathlib.Path(".")) else "ABSENT"
    body = [
        "# Exolon macOS probe",
        "os_version=26.0.1",
        "arch=arm64",
        "hostname_redacted=0a0b0c0d0e0f10111213141516171819",
        "xcodebuild=Xcode 26.1 Build version 17B100",
        "sdk=macosx26.1",
        "probe_bash_version=3.2.57(1)-release",
        "probe_output_will_be_written=/tmp/exolon-probe-20260924T200000Z/probe-report.txt",
        "## K. Provenance",
        "tree_clean_before_run=yes",
        "verdict_scratch_root=OUT_OF_TREE",
        "build_roots_out_of_tree=yes",
        "symroot=/tmp/exolon-probe-20260924T200000Z/sym",
        "objroot=/tmp/exolon-probe-20260924T200000Z/obj",
        "## A. Scheme discovery",
        "verdict_shared_scheme=PRESENT (EXPECTED after P1-11)",
        "## B. Build",
        "build_rc=0",
        "app_path_found=/tmp/exolon-probe-20260924T200000Z/sym/Debug/Exolon.app",
        "settings_MARKETING_VERSION=0.5",
        "plist_CFBundleShortVersionString=0.5",
        "plist_CFBundleVersion=1",
        "version_single_source=MATCH",
        "build_version_single_source=MATCH",
        "plist_unexpanded_placeholders=0",
        "bundle_resources_tmx=125 (EXPECTED 125)",
        "bundle_has_gif=0",
        "bundle_has_generated_terrain=1",
        "hardened_runtime=" + hardened,
        "codesign_flags=flags=0x2000002(adhoc)",
        "## B3. Archived bundle truth",
        "showdestinations_rc=0",
        "archive_rc=0",
        "verdict_archive=PASS",
        "archive_failure_class=NONE",
        "archive_path_out_of_tree=yes",
        "archived_app_present=yes",
        "archived_plist_CFBundleShortVersionString=0.5",
        "archived_plist_CFBundleVersion=1",
        "archived_version_single_source=MATCH",
        "archived_plist_unexpanded_placeholders=0",
        "archived_codesign_verify_rc=0",
        "archived_codesign_flags=flags=0x10000(runtime)",
        "archived_codesign_timestamp=ABSENT",
        "archived_hardened_runtime=" + hardened,
        "archived_entitlements_count=0",
        "archived_entitlements_get_task_allow=no",
        "archived_signature=Signature=adhoc",
        "archived_team_id_hash=sha256:0123456789ab",
        "spctl_assess_verdict=REJECTED",
        "xattr_quarantine_present=no",
        "gatekeeper_representative=no",
        "play_observations=SKIPPED (stdin not a tty)",
        "## H. Signing track gate",
        "signing_track=SKIPPED",
        "signing_track_verdict=NOT_ATTEMPTED",
        "settings_CODE_SIGN_IDENTITY=adhoc-sentinel",
        "settings_CODE_SIGN_INJECT_BASE_ENTITLEMENTS=UNVERIFIED",
        "codesign_flags_runtime_token=ABSENT",
        "notary_profile_present=NOT_APPLICABLE",
        "developer_id_identity_count=NOT_ATTEMPTED",
        "identity_policy=find_identity_not_executed_by_probe",
        "## I. Notarization track",
        "export_archive_rc=NOT_ATTEMPTED",
        "notarytool_submit_rc=NOT_ATTEMPTED",
        "notary_status=NOT_ATTEMPTED",
        "notary_log_committed=no",
        "submission_uuid=none",
        "stapler_staple=NOT_ATTEMPTED",
        "stapler_validate=NOT_ATTEMPTED",
        "artifact_sha256=none",
        "cdhash=none",
        "## J. Probe self-test",
        "probe_selftest_signing_parser=PASS",
        "probe_selftest_notary_status_parser=PASS",
        "probe_selftest_verdict_not_collapsed=PASS",
        "probe_selftest_flush_barrier=PASS",
        "probe_selftest_forbidden_argv_scanner=PASS",
        "tree_clean_after_run=yes",
    ]
    if root is not None:
        bind = binding_fields(root, b"")
        body.append(f"repo_head={bind['provenance']['repo_head']}")
        body.append(f"tree_fingerprint={bind['provenance']['tree_fingerprint']}")
        body.append(f"probe_git_blob_sha1={bind['operational']['probe_script_blob_sha1']}")
    else:
        body += ["repo_head=" + "f" * 40, "tree_fingerprint=" + "e" * 64,
                 "probe_git_blob_sha1=" + "a" * 40]
    body.append("probe_report_saved=/tmp/exolon-probe-20260924T200000Z/probe-report.txt")
    total = len(body) + 3
    body.append(f"report_lines_expected={total}")
    body.append(f"report_lines_written={total}")
    body.append("report_flush_verified=yes")
    return body


def synth_handout(root: pathlib.Path | None = None, **over) -> tuple[dict, bytes]:
    """A Track-A report that is honest by construction; controls break it on purpose."""
    txt = ("\n".join(synth_txt_lines(root)) + "\n").encode()
    doc = derive_report(txt, attested_by="owner", human_present=True,
                        now="2026-09-24T20:10:31Z")
    for pointer, value in over.items():
        apply_pointer(doc, pointer, value)
    return doc, txt


def evaluate_handout(root: pathlib.Path) -> dict:
    """Class-1 verdict over the committed handout. It never invents a pass."""
    hdir = root / HANDOUT_REL
    reports = sorted(hdir.glob("probe-report-*.json")) if hdir.is_dir() else []
    reports = [p for p in reports if p.is_file()]
    if not reports:
        return {"status": "ABSENT", "reports": [], "violations": [],
                "line": "MACOS_EVIDENCE=ABSENT (unverified)"}
    violations: list[str] = []
    stale = False
    for rp in reports:
        tag = rp.name
        try:
            doc = json.loads(rp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            violations.append(f"{tag}: R1 not parsable JSON ({exc})")
            stale = True
            continue
        hits = audit_report(root, doc, report_path=rp)
        violations += [f"{tag}: {hit}" for hit in hits]
        if any(hit.startswith(rule + " ") for hit in hits for rule in STALE_RULES):
            stale = True
    status = "STALE" if stale else ("FAIL" if violations else "OK")
    return {"status": status,
            "reports": [str(p.relative_to(root)) for p in reports],
            "violations": violations,
            "line": f"MACOS_EVIDENCE={status}"}


def free_text_verdict_lines(text: str) -> list[str]:
    """INV-002: a verdict claim must be key=value; prose verdicts are rejected."""
    bad = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "FATAL:", "- ", "EXPECTED:", "OBSERVED>")):
            continue
        if not VERDICT_WORDS.search(stripped):
            continue
        m = KV_RE.match(stripped)
        if m and m.group(2).strip():
            continue
        bad.append(stripped)
    return bad


# --- merged checker ----------------------------------------------------------
def merged_checker_via_subprocess(root: pathlib.Path) -> tuple[int, set, set]:
    """(rc, red AC keys, controls that stopped flipping) of the unmodified merged checker."""
    script = root / MERGED_CHECKER_REL
    if not script.is_file():
        raise CheckFailure(f"merged checker not found: {MERGED_CHECKER_REL}")
    proc = run([sys.executable, str(script), "--root", str(root), "--json"], timeout=300)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise CheckFailure(f"merged checker --json produced unparsable output (rc={proc.returncode})")
    broken = {k for k, v in payload.get("controls", {}).items() if not v}
    return proc.returncode, set(payload.get("mismatches", {})), broken


def import_merged(root: pathlib.Path):
    script = root / MERGED_CHECKER_REL
    if not script.is_file():
        raise CheckFailure(f"merged checker not found: {script}")
    spec = importlib.util.spec_from_file_location("waved_merged_release_layer_check", script)
    if spec is None or spec.loader is None:
        raise CheckFailure("cannot load the merged checker module")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["waved_merged_release_layer_check"] = mod
    spec.loader.exec_module(mod)
    return mod


def red_keys(mod, measured: dict) -> set:
    return {k for k, want in mod.EXPECTED.items() if measured.get(k) != want}


def merged_package_is_immutable(root: pathlib.Path) -> list[str]:
    """FORBID-002: nothing under the merged 20260921 package may differ from HEAD."""
    diff = git(root, "diff", "--name-only", "HEAD", "--", PR3_DIR)
    untracked = git(root, "ls-files", "--others", "--exclude-standard", PR3_DIR)
    out = [f"merged evidence changed: {p}" for p in diff.splitlines() if p]
    out += [f"merged evidence gained a file: {p}" for p in untracked.splitlines() if p]
    return out


# --- evidence hygiene (integration §5.2.5, and the local PR secret-scan) ------
HYGIENE_SCOPE = (PROBE_REL, SCHEMA_REL, HANDOUT_README_REL, ENTITLEMENTS_REL,
                 f"{CHANGE_DIR}/evidence/macos_handout_check.py",
                 f"{CHANGE_DIR}/evidence/cutover.md",
                 f"{CHANGE_DIR}/evidence/stage_boundary_check.py")
HYGIENE_BANS = (
    ("private key header", re.compile(r"BEGIN [A-Z ]*PRIVATE KEY")),
    ("home-directory path", re.compile("/Use" + "rs/")),
    ("aws-style access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("inline credential assignment",
     re.compile(r"""(api[_-]?key|secret|password|token)\s*[:=]\s*['"][^'"]{12,}['"]""", re.I)),
)


def evidence_hygiene(root: pathlib.Path) -> list[str]:
    """The files this change adds must not carry secrets or operator PII."""
    v: list[str] = []
    for rel in HYGIENE_SCOPE:
        text = rd(root, rel)
        if not text:
            if not (root / rel).is_file():
                v.append(f"hygiene: {rel} is missing, so it was never checked")
            continue
        for name, pattern in HYGIENE_BANS:
            for i, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    v.append(f"hygiene: {rel}:{i} carries a {name}")
                    break
    for rel, extra in ((HANDOUT_README_REL, FORBIDDEN_FLAGS),):
        text = rd(root, rel)
        for flag in extra:
            if flag not in text:
                v.append(f"hygiene: {rel} must name the forbidden form {flag!r}")
    return v


# =============================================================================
# named checks (change-spec evidence ids)
# =============================================================================
def probe_contract_green(root: pathlib.Path) -> None:
    """AC-001: the Track A probe contract holds and the merged checker is rc-invariant."""
    probe_path = root / PROBE_REL
    if not probe_path.is_file():
        raise CheckFailure(f"{PROBE_REL} is missing")
    proc = run(["bash", "-n", str(probe_path)])
    if proc.returncode != 0:
        raise CheckFailure("bash -n failed: " + (proc.stderr.strip() or proc.stdout.strip()))
    violations = check_probe_text(root)
    if violations:
        raise CheckFailure(" | ".join(violations)[:1500])
    immut = merged_package_is_immutable(root)
    if immut:
        raise CheckFailure("; ".join(immut))
    rc, red, broken_controls = merged_checker_via_subprocess(root)
    if PHASE == "D1":
        undeclared = broken_controls - DECLARED_CUTOVER_CONTROLS
        if undeclared:
            raise CheckFailure(f"post-D-1 merged-checker controls that stopped flipping must be "
                               f"exactly the declared cutover instrument, extra: "
                               f"{sorted(undeclared)}")
    elif broken_controls:
        raise CheckFailure(f"the unmodified merged checker lost a flipping control on the D-2 "
                           f"tree: {sorted(broken_controls)}")
    if PHASE == "D2":
        if rc != 0 or red:
            raise CheckFailure(f"the unmodified merged checker changed its verdict on the D-2 "
                               f"tree: rc={rc} red={sorted(red)}")
    else:
        # After D-1 the only acceptable red is the declared cutover itself; anything else is
        # a regression, and a fully green D-1 tree would mean the pbxproj edit never landed.
        if red - DECLARED_CUTOVER_SET or not red:
            raise CheckFailure(f"post-D-1 merged-checker reds must be a non-empty subset of "
                               f"{sorted(DECLARED_CUTOVER_SET)}, got {sorted(red)}")
    # Control (M-7): renaming a pinned guard token must redden this detector. The probe
    # bytes on disk are never touched - the mutation stays in memory.
    text = probe_path.read_text(encoding="utf-8")
    mutated = text.replace("EXOLON_FORBIDDEN_ARGV", "REFUSED_CREDENTIAL_ARGV")
    if mutated == text:
        raise CheckFailure("control impossible: the probe has no EXOLON_FORBIDDEN_ARGV")
    hits = check_probe_text(root, mutated)
    if not any("guard token" in h or "disappeared" in h for h in hits):
        raise CheckFailure("control did not flip: renaming a pinned guard token stayed green")
    # Control: losing the archive step must redden both this detector and the merged one.
    no_archive = text.replace('emit "archive_rc=$ARCHIVE_RC"', 'emit "archive_done=$ARCHIVE_RC"')
    no_archive = no_archive.replace('  emit "archive_rc=127"', '  emit "archive_done=127"')
    if no_archive == text:
        raise CheckFailure("control impossible: the archive_rc measurement was not found")
    if not any("archive" in h for h in check_probe_text(root, no_archive)):
        raise CheckFailure("control did not flip: deleting the archive measurement stayed green")


def flush_barrier(root: pathlib.Path) -> None:
    """AC-002 (M-8): an incomplete --out file must be impossible behind rc=0."""
    text = rd(root, PROBE_REL)
    for token in ("report_lines_expected=", "report_lines_written=", "report_flush_verified="):
        if token not in text:
            raise CheckFailure(f"probe: barrier key {token} missing")
    if "probe_flush_barrier" not in text:
        raise CheckFailure("probe: the flush barrier is not an extractable function")
    if "probe_flush_barrier" not in text.split(FN_END.format(name="flush_barrier"), 1)[-1]:
        raise CheckFailure("probe: the barrier is defined but never invoked on the exit path")
    # (1) the M-8 condition, reproduced deterministically: the sink is still draining when
    # the probe would have exited. The shipped barrier must wait and then certify the file.
    lag = r"""
d="$(mktemp -d)"; file="$d/r.txt"; fifo="$d/p"; mkfifo "$fifo"
want=40
( while IFS= read -r l; do printf '%s\n' "$l" >> "$file"; sleep 0.02; done < "$fifo" > /dev/null ) &
exec 9>"$fifo"
i=1; while [ "$i" -le "$want" ]; do printf 'line_%03d=value\n' "$i" >&9; i=$((i+1)); done
exec 9>&-
sleep 0.05
short=$(wc -l < "$file" 2>/dev/null | tr -d ' '); short=${short:-0}
PROBE_FLUSH_TRIES=60 PROBE_FLUSH_DELAY=0.05 probe_flush_barrier "$file" "$want"
rc=$?
printf 'lag_short_before_barrier=%s\n' "$short" >&3
printf 'lag_rc=%s\n' "$rc" >&3
cat "$file" >&3
"""
    p1 = run_probe_fn(text, "flush_barrier", lag)
    out1 = p1.stdout + p1.stderr
    if "report_flush_verified=yes" not in out1 or "lag_rc=0" not in out1:
        raise CheckFailure("the shipped barrier cannot rescue a lagging writer (the M-8 case): "
                           + out1.strip()[-400:])
    m = re.search(r"lag_short_before_barrier=(\d+)", out1)
    if not m or int(m.group(1)) >= 40:
        raise CheckFailure("the fixture did not actually reproduce an incomplete file, so the "
                           "barrier proved nothing (short=%s)" % (m.group(1) if m else "n/a"))
    # (2) control: a permanently short file must be reported as no + a non-zero rc.
    dead = r"""
d="$(mktemp -d)"; file="$d/r.txt"
printf 'line_001=value\nline_002=value\n' > "$file"
PROBE_FLUSH_TRIES=3 PROBE_FLUSH_DELAY=0.02 probe_flush_barrier "$file" 40 2>&1 | cat >&3
printf 'dead_rc=%s\n' "${PIPESTATUS[0]}" >&3
cat "$file" >&3
"""
    p2 = run_probe_fn(text, "flush_barrier", dead)
    out2 = p2.stdout + p2.stderr
    if "report_flush_verified=no" not in out2 or "dead_rc=0" in out2:
        raise CheckFailure("control did not flip: a truncated report still looked clean: "
                           + out2.strip()[-400:])
    if "dead_rc=73" not in out2:
        raise CheckFailure(f"the barrier must fail with the existing I/O exit 73, got: "
                           f"{out2.strip()[-200:]}")


def build_roots_out_of_tree(root: pathlib.Path) -> None:
    """AC-002 (M-9): SYMROOT/OBJROOT are forced outside the clone and *validated*."""
    text = rd(root, PROBE_REL)
    m9 = [h for h in check_probe_text(root) if "M-9" in h or "build root" in h]
    if m9:
        raise CheckFailure("; ".join(m9))
    for token in ('SYMROOT="$', 'OBJROOT="$'):
        if token not in text:
            raise CheckFailure(f"probe: xcodebuild must be passed {token}... as a build setting")
    if "EXOLON_PROBE_SCRATCH" not in text:
        raise CheckFailure("probe: no scratch-root contract variable (integration §2 C-00.3)")
    if "exit 78" not in text.split("verdict_scratch_root=INSIDE_CLONE", 1)[-1][:900]:
        raise CheckFailure("probe: the scratch-root validation must refuse with exit 78 at the "
                           "branch that detects an in-clone root, not merely recommend it")
    # Control: strip the refusal discriminator. A validation that cannot name the failing
    # state is a recommendation, and M-9 is a defect about exactly that difference.
    mutated = text.replace("verdict_scratch_root=INSIDE_CLONE", "verdict_scratch_root=whatever")
    hits = check_probe_text(root, mutated)
    if not any("M-9" in h for h in hits):
        raise CheckFailure("control did not flip: the probe could not report an in-clone "
                           "build root and stayed acceptable")
    mutated2 = re.sub(r'^\s*exit 78\s*$', '   : # refused', text, flags=re.M)
    if mutated2 != text and not any("exit 78" in h for h in check_probe_text(root, mutated2)):
        raise CheckFailure("control did not flip: removing the misconfiguration exit stayed green")


def handout_controls_flip(root: pathlib.Path) -> None:
    """AC-003: each of the ten consistency rules has a contradictory fixture that reddens."""
    doc, txt = synth_handout(root)
    baseline = audit_report(root, doc, txt=txt)
    if baseline:
        raise CheckFailure("the honest synthetic Track-A handout is not green: "
                           + " | ".join(baseline)[:900])
    fixtures = {
        "R1": ("verdicts.build_rc", MISSING),
        "R2": ("operational.raw_report_sha256", "0" * 64),
        "R3": ("provenance.repo_head", "deadbeef" + "0" * 32),
        "R4": ("verdicts.notary_submit", "ACCEPTED"),
        "R5": ("track", "B"),
        "R6": ("verdicts.signing_identity_class", "ADHOC"),
        "R7": ("verdicts.notary_submit", "INVALID"),
        "R8": ("verdicts.hardened_runtime", "PRESENT"),
        "R9": ("verdicts.plist_unexpanded_placeholders", 3),
        "R10": ("selftest.verdict_not_collapsed", "FAIL"),
    }
    if set(fixtures) != set(RULES):
        raise CheckFailure("the fixture set must cover all ten rules exactly")
    for rule, (pointer, value) in fixtures.items():
        broken, broken_txt = synth_handout(root)
        apply_pointer(broken, pointer, value)
        if rule == "R7":
            apply_pointer(broken, "verdicts.notary_log_committed", False)
        if rule == "R6":
            apply_pointer(broken, "verdicts.notary_submit", "ACCEPTED")
            apply_pointer(broken, "track", "B")
        hits = audit_report(root, broken, txt=broken_txt,
                            hardened_count=0 if rule == "R8" else None)
        if not any(h.startswith(rule + " ") for h in hits):
            raise CheckFailure(f"control {rule} did not flip: {pointer}={value!r} produced "
                               f"{hits[:3]}")
    # a rule that cannot be violated is not a rule: R1 must also reject a *missing*
    # schema id, and the schema file must be the contract rather than decoration.
    bad_schema = dict(doc)
    bad_schema["schema"] = "exolon.macos-probe-report/2"
    if not any(h.startswith("R1") for h in audit_report(root, bad_schema, txt=txt)):
        raise CheckFailure("control did not flip: a foreign schema id was accepted")


def absent_is_unverified(root: pathlib.Path) -> None:
    """AC-003: no machine evidence => MACOS_EVIDENCE=ABSENT (unverified), never a pass."""
    live = evaluate_handout(root)
    if live["status"] != "ABSENT":
        raise CheckFailure(f"a handout is already committed ({live['status']}) - this check "
                           "documents the absence semantics, run it on a tree without one")
    if live["line"] != "MACOS_EVIDENCE=ABSENT (unverified)":
        raise CheckFailure(f"the ABSENT line is not machine-exact: {live['line']!r}")
    if live["violations"]:
        raise CheckFailure("an absent handout must report no violations, not invent them")
    if live["reports"]:
        raise CheckFailure("ABSENT must report no files")
    with tempfile.TemporaryDirectory(prefix="exolon-absent-") as tmp:
        fake = pathlib.Path(tmp)
        for rel in (SCHEMA_REL, PROBE_REL, "Exolon.xcodeproj/project.pbxproj"):
            src = root / rel
            if not src.is_file():
                raise CheckFailure(f"fixture root needs {rel}")
            dst = fake / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        # control 1: a directory with only the protocol README stays ABSENT
        hdir = fake / HANDOUT_REL
        hdir.mkdir(parents=True, exist_ok=True)
        (hdir / "README.md").write_text("protocol only\n", encoding="utf-8")
        res = evaluate_handout(fake)
        if res["status"] != "ABSENT" or "ABSENT" not in res["line"]:
            raise CheckFailure(f"a README-only handout dir must stay ABSENT, got {res}")
        # control 2: a present-but-broken handout is FAIL/STALE, never ABSENT and never OK
        doc, txt = synth_handout(root)
        apply_pointer(doc, "verdicts.plist_unexpanded_placeholders", 7)
        (hdir / "probe-report-bad.json").write_text(json.dumps(doc), encoding="utf-8")
        (hdir / "probe-report-bad.txt").write_bytes(txt)
        res2 = evaluate_handout(fake)
        if res2["status"] not in ("FAIL", "STALE"):
            raise CheckFailure(f"a broken handout must be FAIL or STALE, got {res2['status']}")
        if res2["status"] == "ABSENT":
            raise CheckFailure("FAIL and ABSENT collapsed into one state")
        # control 3: absence must be rc=1-shaped for a release consumer
        if res2["status"] == "OK":
            raise CheckFailure("a report contradicting its own pbxproj went green")


def agent_boundary(root: pathlib.Path) -> None:
    """AC-004: Track B is structurally unreachable from any agent path."""
    text = rd(root, PROBE_REL)
    v = [h for h in check_probe_text(root)
         if "credential" in h or "§5.2.3" in h or "profile" in h.lower()]
    if v:
        raise CheckFailure("; ".join(v))
    if "WITH_SIGNING" not in text or "EXOLON_HUMAN_SIGNING_RUN" not in text:
        raise CheckFailure("probe: the double env gate is absent")
    gate = text.split('emit "## H.', 1)[-1]
    if not gate:
        raise CheckFailure("probe: section H (the signing gate) is missing")
    if "[ -t 0 ]" not in gate and "[ ! -t 0 ]" not in gate:
        raise CheckFailure("probe: Track B does not require an interactive tty")
    if "exit 77" not in gate:
        raise CheckFailure("probe: the off-tty / ungated refusal path does not exit 77")
    if "HUMAN_SIGNING_RUN" not in gate:
        raise CheckFailure("probe: Track B does not require the typed interactive attestation")
    if '"$EXOLON_NOTARY_PROFILE"' not in text:
        raise CheckFailure("probe: notarytool must be reachable only through the profile NAME")
    if re.search(r"^\s*EXOLON_HUMAN_SIGNING_RUN=", text, re.M):
        raise CheckFailure("probe: the human gate must never be set by the script itself - an "
                           "agent could then satisfy it (integration §5.2.1)")
    # dynamic: the SHIPPED scanner must abort (never redact) on every listed form
    pre = ("EXOLON_FORBIDDEN_ARGV='%s'\nEXOLON_FORBIDDEN_ARGV_PATH='%s'\n"
           "EXOLON_FORBIDDEN_ARGV_TEXT='%s'\nEXOLON_FORBIDDEN_ARGV_SHORT='%s'\n" % (
               scanner_const(text, "EXOLON_FORBIDDEN_ARGV"),
               scanner_const(text, "EXOLON_FORBIDDEN_ARGV_PATH"),
               scanner_const(text, "EXOLON_FORBIDDEN_ARGV_TEXT"),
               scanner_const(text, "EXOLON_FORBIDDEN_ARGV_SHORT")))
    taint_cases = ["--apple-id", "--apple_id", "--password", "--password=hunter2hunter2",
                   "--key", "--mobileprovision", "cert.p12", "key.p8", "team.pem",
                   "some PEM", "-s", "--sign", "x --sign y",
                   "-----BEGIN" + " PRIVATE KEY-----"]
    missed = []
    for case in taint_cases:
        body = ("if probe_forbidden_argv_scan '%s'; then printf 'CLEAN\\n'; "
                "else printf 'TAINT\\n'; fi\n" % case.replace("'", "'\\''"))
        proc = run_probe_fn(text, "forbidden_argv_scan", body, prelude=pre)
        if "TAINT" not in proc.stdout + proc.stderr:
            missed.append(case)
    if missed:
        raise CheckFailure("the forbidden-argv scanner let through: " + ", ".join(missed))
    for ok_case in ["--out", "--config", "Release", "--keychain-profile", "exolon-notary",
                    "Exolon.xcodeproj", "/tmp/scratch/Exolon.xcarchive", "--target"]:
        body = ("if probe_forbidden_argv_scan '%s'; then printf 'CLEAN\\n'; "
                "else printf 'TAINT\\n'; fi\n" % ok_case)
        proc = run_probe_fn(text, "forbidden_argv_scan", body, prelude=pre)
        if "CLEAN" not in proc.stdout:
            raise CheckFailure(f"control overshot: legitimate argv {ok_case!r} was refused "
                               f"({proc.stdout.strip()} {proc.stderr.strip()})")
    # env names only, never values. The count is compared against the runner's own
    # baseline instead of assuming a clean environment: any host that exports a variable
    # matching the ban list (GH_TOKEN and friends) raises the baseline, and that is the
    # same refusal the operator will hit on a real machine - documented in the handout
    # README as the clean-shell requirement, not papered over here.
    envpre = "EXOLON_FORBIDDEN_ENV_NAMES='%s'\n" % scanner_const(text, "EXOLON_FORBIDDEN_ENV_NAMES")
    base = run_probe_fn(text, "forbidden_env_names", "probe_forbidden_env_names\n", prelude=envpre)
    try:
        baseline = int(base.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise CheckFailure("the env-name scanner is not callable in isolation: "
                           + (base.stdout + base.stderr)[-200:])
    for name, want in (("EXOLON_PASSWORD", 1), ("NOTARY_TOKEN", 1), ("SERVICE_APPLE_ID", 1),
                       ("MY_SECRET_THING", 1), ("SSH_PRIVATE_KEY", 1),
                       ("EXOLON_NOTARY_PROFILE", 0), ("WITH_SIGNING", 0),
                       ("EXOLON_PROBE_SCRATCH", 0), ("EXOLON_HUMAN_SIGNING_RUN", 0)):
        body = ("export %s='hunter2-value-not-printed'\nprobe_forbidden_env_names\n" % name)
        proc = run_probe_fn(text, "forbidden_env_names", body, prelude=envpre)
        try:
            got = int(proc.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            raise CheckFailure(f"the env-name scan produced no counter for {name}: "
                               + (proc.stdout + proc.stderr)[-200:])
        if got != baseline + want:
            raise CheckFailure(f"the env-name scan misclassified {name}: counted {got}, "
                               f"expected {baseline + want} (baseline {baseline})")
        if "hunter2" in proc.stdout + proc.stderr:
            raise CheckFailure(f"the env-name scan printed a value for {name} (abort-not-redact)")
    if baseline and re.search(r"exit 77", text) is None:
        raise CheckFailure("a non-zero baseline must still be a refusal, not a silent pass")
    # the notary profile is a NAME, validated, never a secret
    valpre = "EXOLON_NOTARY_PROFILE_RE='%s'\n" % scanner_const(text, "EXOLON_NOTARY_PROFILE_RE")
    for name, want in (("exolon-notary", "OK"), ("a" * 64, "OK"), ("a" * 65, "BAD"),
                       ("bad name", "BAD"), ("", "BAD"), ("x;rm -rf", "BAD"),
                       ("--apple-id", "BAD")):
        body = ("if probe_validate_notary_profile '%s'; then printf 'OK\\n'; "
                "else printf 'BAD\\n'; fi\n" % name)
        proc = run_probe_fn(text, "notary_profile_gate", body, prelude=valpre)
        if want not in proc.stdout:
            raise CheckFailure(f"profile-name validation misclassified {name!r}: "
                               f"{proc.stdout}{proc.stderr}")
    # identity material may only enter the handout as a hash
    if "archived_team_id_hash" not in text or "identity_policy" not in text:
        raise CheckFailure("probe: Team ID / certificate material is not hashed into the report")
    if re.search(r"\bdefaults write\b|\bsecurity import\b", text):
        raise CheckFailure("probe: it must not write defaults or import key material")
    hy = evidence_hygiene(root)
    if hy:
        raise CheckFailure(" | ".join(hy)[:600])
    # control: a planted credential must be caught, or the hygiene scan is decoration
    planted = ("password" + " = " + chr(34) + "hunter2hunter2" + chr(34)
                 + "\n" + "api_key" + ": " + chr(39) + "AKIA-lookalike-value" + chr(39))
    hits = [name for name, pattern in HYGIENE_BANS if pattern.search(planted)]
    if "inline credential assignment" not in hits:
        raise CheckFailure("control did not flip: the secret-scan pattern missed an inline "
                           f"credential (matched {hits})")


def no_track_b_claim(root: pathlib.Path) -> None:
    """FORBID-001: no handout may claim Track B (notarization Accepted) without the gate."""
    doc, txt = synth_handout(root)
    honest = [h for h in audit_report(root, doc, txt=txt)]
    if honest:
        raise CheckFailure("the honest Track-A fixture must be acceptable, got "
                           + " | ".join(honest)[:500])
    lying, lying_txt = synth_handout(root)
    for pointer, value in (("verdicts.notary_submit", "ACCEPTED"),
                           ("verdicts.signing_identity_class", "DEVELOPER_ID"),
                           ("verdicts.secure_timestamp", "PRESENT"),
                           ("verdicts.hardened_runtime", "PRESENT"),
                           ("verdicts.stapler_validate", "WORKED"),
                           ("verdicts.stapler_staple", "PASS"),
                           ("verdicts.spctl_assess", "ACCEPTED_NOTARIZED_DEVELOPER_ID")):
        apply_pointer(lying, pointer, value)
    hits = audit_report(root, lying, txt=lying_txt)
    offenders = [h for h in hits if h.startswith(("R4", "R5", "R6", "R8"))]
    if not offenders:
        raise CheckFailure("control did not flip: a Track-A-shaped report asserting notarization "
                           "Accepted stayed acceptable")
    # ... and the same lie must survive no reviewer's reading of the protocol doc
    readme = rd(root, HANDOUT_README_REL)
    if "Track B" not in readme:
        raise CheckFailure(f"{HANDOUT_README_REL} does not state the Track B boundary")
    for marker in ("Track B is NOT closed", "P1-11 stays partially closed",
                   "notarization Accepted"):
        if marker not in readme:
            raise CheckFailure(f"{HANDOUT_README_REL} must carry the fixed wording "
                               f"{marker!r} so the boundary cannot be paraphrased away")
    prose = "This run proves notarization Accepted and the release is ready."
    if not free_text_verdict_lines(prose):
        raise CheckFailure("control did not flip: a prose verdict was accepted")
    for flag in FORBIDDEN_FLAGS:
        if flag not in readme:
            raise CheckFailure(f"{HANDOUT_README_REL} must list the forbidden flag {flag} "
                               "(integration §5.2.6)")


def cutover_set_exact(root: pathlib.Path) -> None:
    """FORBID-002: the post-D-1 red set of the merged checker is exactly the declared one."""
    immut = merged_package_is_immutable(root)
    if immut:
        raise CheckFailure("; ".join(immut))
    rc, red, broken_controls = merged_checker_via_subprocess(root)
    if PHASE == "D2" and broken_controls:
        raise CheckFailure(f"merged checker controls regressed on the D-2 tree: "
                           f"{sorted(broken_controls)}")
    if broken_controls - DECLARED_CUTOVER_CONTROLS:
        raise CheckFailure(f"undeclared merged-checker control loss (FORBID-002 class): "
                           f"{sorted(broken_controls - DECLARED_CUTOVER_CONTROLS)}")
    if PHASE == "D2" and red:
        raise CheckFailure(f"the D-2 tree must not have triggered the cutover yet: red={sorted(red)}")
    if PHASE == "D1" and not red:
        raise CheckFailure("a D-1 tree with a fully green merged checker means the "
                           "hardened-runtime edit is missing")
    if red - DECLARED_CUTOVER_SET:
        raise CheckFailure(f"undeclared cutover red (FORBID-002): {sorted(red - DECLARED_CUTOVER_SET)}")
    mod = import_merged(root)
    ctx = mod.load_inputs(root)
    for key in sorted(DECLARED_CUTOVER_SET):
        if key not in mod.EXPECTED:
            raise CheckFailure(f"declared cutover key {key} is not an AC of the merged checker")
    insert = "\t\t\t\tENABLE_HARDENED_RUNTIME = YES;\n"
    anchors = list(re.finditer(r"\t\t\t\tCODE_SIGN_STYLE = Manual;\n", ctx["pbx"]))
    if len(anchors) != 2:
        raise CheckFailure(f"expected exactly 2 target-config anchors, found {len(anchors)}")
    # The two declared members and the shape of the post-D-1 diff, measured rather than quoted.
    # `already` distinguishes the phases: on a pre-repayment tree the D-1 shape is simulated in
    # memory (so the declaration is tested before anything depends on it); on the repaid tree it
    # is the tree itself, because re-inserting an identical setting proves nothing - the parsed
    # buildSettings dicts stay equal, which is also why the merged checker's own control 8 stops
    # flipping and is declared in DECLARED_CUTOVER_CONTROLS / evidence/cutover.md.
    already = ctx["pbx"].count("ENABLE_HARDENED_RUNTIME")
    if already:
        red_sym = red_keys(mod, mod.measure(ctx)[0])
        if "hardened_runtime_key_count" not in red_sym:
            raise CheckFailure(f"the repaid tree reddens {sorted(red_sym)} but not "
                               "hardened_runtime_key_count: the repayment never reached the "
                               "merged checker")
    else:
        sym = ctx["pbx"]
        for m in reversed(anchors):
            sym = sym[:m.end()] + insert + sym[m.end():]
        red_sym = red_keys(mod, mod.measure(dict(ctx, pbx=sym))[0])
        if "hardened_runtime_key_count" not in red_sym:
            raise CheckFailure("the D-1 pbxproj edit reddens nothing: the declaration is prose")
    undeclared = red_sym - DECLARED_CUTOVER_SET
    if undeclared:
        raise CheckFailure(f"the declared cutover set is wrong: the D-1 shape reddens "
                           f"{sorted(undeclared)}, which FORBID-002 does not declare")
    red_rec = red_keys(mod, mod.measure(mod.undo_records(ctx))[0])
    if "hardened_deferral_recorded" not in red_rec:
        raise CheckFailure("the declared cutover member hardened_deferral_recorded is not a live "
                           "key: the merged checker cannot turn it red")
    # Measured truth about that second member: the pbxproj repayment alone does NOT redden it,
    # because it reads PR #3's immutable plan text. The cutover registry says so explicitly.
    if already and "hardened_deferral_recorded" in red_sym:
        raise CheckFailure("hardened_deferral_recorded reddened on the real tree; the registry "
                           "in evidence/cutover.md is now wrong")
    # A one-sided key - installing it in one config on a pre-edit tree, or dropping it from one
    # config on a repaid tree - is a regression class, never a declared cutover.
    if already:
        one_side = re.sub(r"^\t{4}ENABLE_HARDENED_RUNTIME = YES;\n", "", ctx["pbx"], count=1,
                          flags=re.M)
    else:
        one_side = ctx["pbx"].replace(anchors[0].group(0), anchors[0].group(0) + insert, 1)
    red_one = red_keys(mod, mod.measure(dict(ctx, pbx=one_side))[0])
    if not (red_one - DECLARED_CUTOVER_SET):
        raise CheckFailure("control did not flip: a one-sided hardened key produced no "
                           "undeclared red, so 'any other cutover red is a regression' is "
                           "unmeasurable")
    if not (red_one & {"hardened_symmetric", "target_cfg_symmetric"}):
        raise CheckFailure("control did not flip: the symmetry keys stayed green on a "
                           "one-sided edit")


def verdicts_machine_readable(root: pathlib.Path) -> None:
    """INV-002: verdicts are key=value only, and every step carries a flipping control."""
    text = rd(root, PROBE_REL)
    if not text.strip():
        raise CheckFailure(f"{PROBE_REL} is missing")
    keys = emit_keys(text)
    for key in TRACK_A_KEYS + TRACK_B_KEYS + SELFTEST_KEYS:
        if key not in keys:
            raise CheckFailure(f"probe: verdict key {key} is not emitted as key=value")
    legacy = merged_probe_text(root)
    bad = []
    for ln in probe_new_lines(legacy, text):
        s = ln.strip()
        if not s.startswith('emit "'):
            continue
        rest = s[len('emit "'):]
        m = KV_RE.match(rest)
        if m and m.group(2).strip():
            continue
        # a non-kv emit line is legal only where the merged probe already keeps prose
        # (section headers, the "what this probe does not prove" bullets, FATAL lines) and
        # only as long as it carries no verdict word: a prose verdict is the exact
        # misreading the extension exists to remove.
        if not s.startswith(('emit "## ', 'emit "# ', 'emit "- ', 'emit "FATAL:', 'emit "  ')):
            bad.append(s)
        elif VERDICT_WORDS.search(rest):
            bad.append(s)
    if bad:
        raise CheckFailure("probe: new free-text emit lines (must be key=value): "
                           + " | ".join(bad)[:400])
    doc, txt = synth_handout(root)
    if free_text_verdict_lines(txt.decode()):
        raise CheckFailure("the clean synthetic transcript has prose verdict lines: "
                           + " | ".join(free_text_verdict_lines(txt.decode()))[:300])
    polluted = txt.decode() + "\nnotarization looks ACCEPTED to me\nspctl says rejected\n"
    hits = free_text_verdict_lines(polluted)
    if len(hits) != 2:
        raise CheckFailure("control did not flip: prose verdict lines were not detected "
                           f"(got {hits})")
    schema = load_schema(root)
    errs = schema_validate(doc, schema, defs_root=schema)
    if errs:
        raise CheckFailure("the derived synthetic report violates its own committed schema: "
                           + " | ".join(errs)[:500])
    broken, broken_txt = synth_handout(root)
    apply_pointer(broken, "verdicts.notary_submit", "GARBAGE")
    if not schema_validate(broken, schema, defs_root=schema):
        raise CheckFailure("control did not flip: the schema accepted an undefined verdict value")
    broken2, _ = synth_handout(root)
    apply_pointer(broken2, "operational.probe_exit_code", "zero")
    if not schema_validate(broken2, schema, defs_root=schema):
        raise CheckFailure("control did not flip: the schema accepted a non-integer rc")
    if doc.get("verdicts", {}).get("notary_submit") != "NOT_ATTEMPTED":
        raise CheckFailure(f"the Track-A fixture must read NOT_ATTEMPTED, got "
                           f"{doc['verdicts'].get('notary_submit')!r}")
    for verdict in VERDICT5:
        if verdict not in text:
            raise CheckFailure(f"probe: verdict value {verdict} never appears in the shipped "
                               "text, so the 5-valued vocabulary is decorative")


def entitlements_and_hardening_shape(root: pathlib.Path) -> None:
    """Task 10's product shape, measured: hardened in both target blocks, a real minimal
    entitlements file named by both, nothing secret in either.

    This is the half of P1-11's signing clause that Linux can actually decide. The observed
    flags on a built bundle stay out of reach (cutover.md section 6), and saying so is part of
    the check: a tree that claims more than settings and a plist is the failure mode PR #3 AC-010
    was written against.
    """
    import plistlib
    pbx = rd(root, PBXPROJ_REL)
    v: list[str] = []
    if hardened_count_in_tree(root) != 2:
        v.append(f"ENABLE_HARDENED_RUNTIME must appear exactly twice (both target configs), "
                 f"found {hardened_count_in_tree(root)}")
    for guid in ("800000000000000000000003", "800000000000000000000004"):
        m = re.search(re.escape(guid) + r" /\* \w+ \*/ = \{\n.*?\n\t\t\};\n", pbx, re.S)
        if not m:
            v.append(f"target configuration block {guid} is gone from the project")
            continue
        body = m.group(0)
        if "ENABLE_HARDENED_RUNTIME = YES;" not in body:
            v.append(f"{guid} lacks ENABLE_HARDENED_RUNTIME = YES")
        if f"CODE_SIGN_ENTITLEMENTS = {ENTITLEMENTS_REL};" not in body:
            v.append(f"{guid} lacks CODE_SIGN_ENTITLEMENTS pointing at {ENTITLEMENTS_REL}")
    if re.search(r"^\t{4}ENABLE_HARDENED_RUNTIME", pbx, re.M) and hardened_count_in_tree(root) > 2:
        v.append("the hardened key appears outside the two target blocks")
    if CODE_SIGN_SENTINEL not in pbx:
        v.append("CODE_SIGN_IDENTITY stopped being the ad-hoc sentinel: a signing identity would "
                 "now be in the tree, which this change must not introduce")
    if 'DEVELOPMENT_TEAM = "";' not in pbx:
        v.append("DEVELOPMENT_TEAM is no longer empty: a team id entered the tree")
    ent = root / ENTITLEMENTS_REL
    if not ent.is_file():
        v.append(f"{ENTITLEMENTS_REL} does not exist")
    else:
        try:
            keys = plistlib.loads(ent.read_bytes())
        except Exception as exc:  # noqa: BLE001 - a plist that will not parse is the finding
            raise CheckFailure(f"{ENTITLEMENTS_REL} is not a property list: {exc}")
        if sorted(keys) != []:
            v.append(f"{ENTITLEMENTS_REL} must be the empty entitlement set, it grants "
                     f"{sorted(keys)}")
        blob = ent.read_bytes()
        if b"get-task-allow" in blob:
            v.append("the debugger entitlement is in the shipped entitlements file")
        if b"-----BEGIN" in blob or b"entitlements.com.apple.security.app-sandbox" in blob:
            v.append("unexpected material in the entitlements file")
    if v:
        raise CheckFailure(" | ".join(v)[:900])
    # Control: strip the key from one config in memory; the shape test must notice.
    one_sided = re.sub(r"^\t{4}ENABLE_HARDENED_RUNTIME = YES;\n", "", pbx, count=1, flags=re.M)
    if one_sided.count("ENABLE_HARDENED_RUNTIME") != 1:
        raise CheckFailure("control impossible: cannot produce a one-sided hardened tree")
    if hardened_count_in_tree(root) == 2 and len(re.findall(
            "ENABLE_HARDENED_RUNTIME = YES;", one_sided)) != 1:
        raise CheckFailure("control did not flip: the one-sided mutation was not a mutation")


CHECKS: dict[str, object] = {
    "entitlements_and_hardening_shape": entitlements_and_hardening_shape,
    "probe_contract_green": probe_contract_green,
    "flush_barrier": flush_barrier,
    "build_roots_out_of_tree": build_roots_out_of_tree,
    "handout_controls_flip": handout_controls_flip,
    "absent_is_unverified": absent_is_unverified,
    "agent_boundary": agent_boundary,
    "no_track_b_claim": no_track_b_claim,
    "cutover_set_exact": cutover_set_exact,
    "verdicts_machine_readable": verdicts_machine_readable,
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="macos_handout_check.py")
    ap.add_argument("--root")
    ap.add_argument("--only", action="append", default=[],
                    help="run one named check (repeatable)")
    ap.add_argument("--phase", choices=("auto", "D2", "D1"), default="auto",
                    help="auto (default) reads the tree: D-1 once wave A's ledger and the "
                         "hardened-runtime repayment are both in it")
    ap.add_argument("--report", action="store_true",
                    help="print the machine-readable MACOS_EVIDENCE line (rc 1 when not OK)")
    ap.add_argument("--derive", metavar="TXT", help="derive the report JSON from a transcript")
    ap.add_argument("--out-json", metavar="PATH")
    ap.add_argument("--attested-by", default="unattested")
    ap.add_argument("--human-present", action="store_true")
    global PHASE
    args = ap.parse_args(argv)
    root = repo_root(args.root)
    PHASE = args.phase if args.phase != "auto" else detect_phase(root)
    print(f"PHASE={PHASE} " + ("(from --phase)" if args.phase != "auto" else "(detected from the tree)"))

    if args.derive:
        data = pathlib.Path(args.derive).read_bytes()
        try:
            doc = derive_report(data, attested_by=args.attested_by,
                                human_present=args.human_present)
        except CheckFailure as exc:
            print(f"DERIVE=REFUSED {exc}", file=sys.stderr)
            return 1
        # Only file-local facts are re-derived here. repo_head and the probe blob stay as
        # the machine measured them, otherwise rule R3 could never notice a stale report.
        doc["operational"]["raw_report_sha256"] = sha256_bytes(data)
        doc["operational"]["verifier_script_blob_sha1"] = blob_sha1(
            pathlib.Path(__file__).resolve().read_bytes())
        fingerprint = tree_fingerprint(root)
        if fingerprint:
            doc["provenance"]["tree_fingerprint"] = fingerprint
        out = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
        if args.out_json:
            pathlib.Path(args.out_json).write_text(out, encoding="utf-8")
            print(f"DERIVE=OK {args.out_json}")
        else:
            sys.stdout.write(out)
        return 0

    if args.report:
        res = evaluate_handout(root)
        print(res["line"])
        for viol in res["violations"][:20]:
            print(f"  violation {viol}")
        return 0 if res["status"] == "OK" else 1

    names = args.only or list(CHECKS)
    unknown = [n for n in names if n not in CHECKS]
    if unknown:
        print(f"unknown check(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    failures = 0
    for name in names:
        try:
            CHECKS[name](root)  # type: ignore[operator]
            print(f"RESULT {name}=PASS")
        except CheckFailure as exc:
            failures += 1
            print(f"RESULT {name}=FAIL {exc}")
        except Exception as exc:  # noqa: BLE001 - a crash must never read as a pass
            failures += 1
            print(f"RESULT {name}=ERROR {type(exc).__name__}: {exc}")
    print(f"SUMMARY checks={len(names)} failed={failures} phase={PHASE}")
    print("SCOPE=class-1-only: no macOS fact is certified by this tool (integration §3.5)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
