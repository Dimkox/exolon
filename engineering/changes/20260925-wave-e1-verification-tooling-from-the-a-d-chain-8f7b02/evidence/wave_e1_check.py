#!/usr/bin/env python3
"""Wave E1 self-checking verifier: verification tooling for the A-D chain debt (#21/#22).

Typed authority: ``../change-spec.yaml``. Every ``test`` path named there resolves to a function in
this file, so the stack recorder binds real evidence, not prose. The eleven functions are named
exactly as the spec names them:

    AC-001 scan_covers_committed_union      AC-005 v3_header_present
    AC-002 attribution_scan_flips           AC-006 b_meter_failclosed
    AC-003 cross_wave_suite_green           AC-007 m3_soft_band
    AC-004 loader_harness_green              AC-008 warp_guid_bound
    FORBID-001 product_untouched            FORBID-002 no_silent_relaxation
    INV-001  suite_standalone_agreement

Method (the discipline this repo already uses in ``wave_b_check.py`` / ``wave_c_check.py``): a
verdict is only worth its green if it can be made to fail. Every check here therefore ships with a
control that must flip the other way, and every control is applied to an **on-disk artifact** - a
fresh ``git clone --no-hardlinks`` tree with its own ``.git``, never a mutate-then-restore in the
real worktree. The real tree is only read (plus the meters' own idempotent evidence writes).

Two rules this file enforces about itself:
  * it never writes under ``Exolon/`` or ``Exolon.xcodeproj`` (FORBID-001) and never writes a ref
    into the real repository - the wave-C ``refs/heads/origin/main`` incident is why every
    ref-level control runs inside a clone;
  * it fails closed: a missing ``swiftc``, a failed clone, an unparsable meter line, a timeout -
    every one of them is a FAIL, never a skip.

Usage:
    python3 wave_e1_check.py                  # all eleven checks
    python3 wave_e1_check.py --list
    python3 wave_e1_check.py --only loader_harness_green,m3_soft_band
    python3 wave_e1_check.py --json           # machine-readable result document
    python3 wave_e1_check.py --keep-work      # keep the /tmp control trees
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
ROOT = PKG.parents[2]
TOOLS = ROOT / 'engineering' / 'tools'
WAVE_SCAN = TOOLS / 'wave_scan.py'
SWIFTC = os.environ.get('SWIFTC', '/opt/swift/usr/bin/swiftc')
# The change root of the A-D chain: every accumulated delta is policed from here down.
ROOT_BASE = '295690b'
DIAG_LOG = ROOT / 'Exolon' / 'GameCore' / 'Diagnostics' / 'GameplayEventLog.swift'

CHANGES = ROOT / 'engineering' / 'changes'
A_PKG = CHANGES / '20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c'
B_PKG = CHANGES / '20260924-fix-wave-b-map-data-and-physics-audit-findings-i-35bac2'
C_PKG = CHANGES / '20260924-close-wave-c-content-and-factory-audit-findings-f2d90a'
D_PKG = CHANGES / '20260924-complete-wave-d-specification-and-release-audit-8341b7'
H_PKG = CHANGES / '20260919-exolon-initial-code-audit-7db1f3'

A_CHECK = A_PKG / 'evidence' / 'gameplay_log_check.py'
B_CHECK = B_PKG / 'evidence' / 'wave_b_check.py'
C_CHECK = C_PKG / 'evidence' / 'wave_c_check.py'
D_HANDOUT = D_PKG / 'evidence' / 'macos_handout_check.py'
D_STAGE = D_PKG / 'evidence' / 'stage_boundary_check.py'
LOADER_RUN = H_PKG / 'evidence' / 'harness' / 'run.sh'
LOADER_LAST_RUN = H_PKG / 'evidence' / 'harness' / 'last-run.txt'
LOADER_README = H_PKG / 'evidence' / 'harness' / 'README.md'
V3_MIRROR = H_PKG / 'evidence' / 'v3_measurements.py'
A_HARNESS_MAIN = A_PKG / 'evidence' / 'harness' / 'main.swift'
PBXPROJ_REL = 'Exolon.xcodeproj/project.pbxproj'
PBXPROJ = ROOT / PBXPROJ_REL

# The five merged meters plus the loader harness, and the verdict counts each one is recorded at.
# Keyed by the name wave_scan reports, so INV-001 compares like with like.
METERS = (
    ('wave-a-gameplay-log', A_CHECK, [], 28, 'A'),
    ('wave-b-mapdata', B_CHECK, [], 9, 'B'),
    ('wave-c-content', C_CHECK, [], 9, 'C'),
    ('wave-d-handout', D_HANDOUT, ['--phase', 'D1'], 11, 'D1'),
    ('wave-d-stage', D_STAGE, [], 10, 'DSTAGE'),
    ('loader-harness-125maps', LOADER_RUN, [], 1, 'LOADER'),
)
METER_INDEX = {name: (script, extra, expected, tag) for name, script, extra, expected, tag in METERS}
METER_NAMES = [name for name, _, _, _, _ in METERS]

WORK = Path(os.environ.get('TMPDIR', '/tmp')) / f'exolon-wave-e1-check-{os.getpid()}'

CHECKS = (
    ('scan_covers_committed_union', 'AC-001'),
    ('attribution_scan_flips', 'AC-002'),
    ('cross_wave_suite_green', 'AC-003 / SIG-001'),
    ('loader_harness_green', 'AC-004'),
    ('v3_header_present', 'AC-005'),
    ('b_meter_failclosed', 'AC-006'),
    ('m3_soft_band', 'AC-007'),
    ('warp_guid_bound', 'AC-008'),
    ('product_untouched', 'FORBID-001'),
    ('no_silent_relaxation', 'FORBID-002'),
    ('suite_standalone_agreement', 'INV-001'),
)


class CheckFailure(Exception):
    """A check that cannot show its evidence has failed; the message names what is missing."""


# ---------------------------------------------------------------------------
# process + git helpers
# ---------------------------------------------------------------------------

def run(argv, cwd=None, env=None, timeout=900):
    """Run a command, return a dict. A timeout is rc=124 - never an exception, never a pass."""
    started = time.time()
    try:
        proc = subprocess.run([str(a) for a in argv], cwd=str(cwd or ROOT), env=env,
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or b''
        out = out.decode('utf-8', 'replace') if isinstance(out, bytes) else out
        return {'returncode': 124, 'stdout': out, 'stderr': 'timeout after %ss' % timeout,
                'seconds': round(time.time() - started, 1)}
    return {'returncode': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr,
            'seconds': round(time.time() - started, 1)}


def tail(text: str, limit: int = 400) -> str:
    lines = [line for line in (text or '').splitlines() if line.strip()]
    return ' | '.join(lines[-6:])[:limit]


def git(*args, cwd=None, check=True):
    proc = run(['git', '-c', 'core.quotepath=false', *[str(a) for a in args]],
               cwd=cwd or ROOT, timeout=300)
    if check and proc['returncode'] != 0:
        raise CheckFailure(f'git {" ".join(str(a) for a in args)} failed '
                           f'(rc={proc["returncode"]}): {proc["stderr"].strip()[:300]}')
    return proc['stdout']


def head_sha() -> str:
    return git('rev-parse', 'HEAD').strip()


def short_head() -> str:
    return git('rev-parse', '--short', 'HEAD').strip()


def ensure_work() -> Path:
    WORK.mkdir(parents=True, exist_ok=True)
    return WORK


def clone_tree(name: str, pin_origin: bool = True) -> Path:
    """Fresh ``git clone --no-hardlinks`` tree carrying the real HEAD plus this change's edits.

    A clone (never ``cp -a`` of this linked worktree) because ``cp -a`` copies the ``.git``
    *pointer* file, so every ref-writing command in the copy would hit the shared repository.
    """
    ensure_work()
    dst = WORK / name
    if dst.exists():
        shutil.rmtree(dst)
    proc = run(['git', 'clone', '--no-hardlinks', '--quiet', str(ROOT), str(dst)], timeout=900)
    if proc['returncode'] != 0 or not (dst / '.git').is_dir():
        detail = (proc['stderr'] or proc['stdout']).strip()[:300]
        raise CheckFailure(f'clone {name} failed: {detail}')
    git('rev-parse', '--verify', 'HEAD', cwd=dst)
    if git('rev-parse', 'HEAD', cwd=dst).strip() != head_sha():
        raise CheckFailure(f'clone {name} HEAD is not the real HEAD')
    copy_working_changes(dst)
    if pin_origin:
        pin_origin_main(dst, head_sha())
    return dst


def copy_working_changes(dst: Path) -> None:
    """Mirror the uncommitted wave-E1 edits (tools, meters, package) into a clone.

    Without this a clone would test ``HEAD``'s tools instead of the ones under review.
    """
    listed = set()
    for args in (['diff', '--name-only', 'HEAD'], ['diff', '--name-only', '--cached'],
                 ['ls-files', '--others', '--exclude-standard']):
        proc = run(['git', *args], cwd=ROOT, timeout=180)
        if proc['returncode'] != 0:
            detail = proc['stderr'].strip()[:200]
            raise CheckFailure(f'{" ".join(args)} failed: {detail}')
        listed.update(line for line in proc['stdout'].splitlines() if line.strip())
    for rel in sorted(listed):
        src, target = ROOT / rel, dst / rel
        if rel.startswith('Exolon/') or rel.startswith('Exolon.xcodeproj/'):
            raise CheckFailure(f'wave E1 edits a product path ({rel}); FORBID-001')
        if src.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
        elif target.exists():
            target.unlink()


def pin_origin_main(clone: Path, sha: str) -> None:
    git('update-ref', 'refs/remotes/origin/main', sha, cwd=clone)


def drop_origin(clone: Path) -> None:
    git('update-ref', '-d', 'refs/remotes/origin/main', cwd=clone, check=False)
    proc = run(['git', 'show-ref', '--verify', 'refs/remotes/origin/main'], cwd=clone, timeout=60)
    if proc['returncode'] == 0:
        raise CheckFailure('the remote-less clone still resolves refs/remotes/origin/main')


def read(path: Path) -> str:
    if not path.is_file():
        raise CheckFailure(f'{path.relative_to(ROOT) if path.is_absolute() else path} is missing')
    return path.read_text(encoding='utf-8')


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def require(condition, message) -> None:
    if not condition:
        raise CheckFailure(message)


def wave_scan(root: Path, only: str = 'parse,attribution,meters', timeout=900, meters=None):
    """Run the tool under review and require parsable JSON out of it - never a text grep."""
    if not WAVE_SCAN.is_file():
        raise CheckFailure(f'{rel(WAVE_SCAN)} is missing')
    if not Path(SWIFTC).is_file():
        raise CheckFailure(f'swiftc is absent at {SWIFTC}; the parse contour cannot be proven')
    argv = [sys.executable, str(WAVE_SCAN), '--root', root, '--only', only, '--json']
    for meter in (meters or []):
        argv += ['--meter', meter]
    proc = run(argv, timeout=timeout)
    text = proc['stdout'].strip()
    try:
        doc = json.loads(text)
    except (ValueError, TypeError):
        raise CheckFailure(f'wave_scan --json is not parsable (rc={proc["returncode"]}): '
                           f'{tail(proc["stdout"])} || {tail(proc["stderr"])}') from None
    for key in ('parse', 'attribution', 'meters', 'totals', 'result'):
        if key not in doc:
            raise CheckFailure(f'wave_scan JSON has no {key!r} section')
    doc['_returncode'] = proc['returncode']
    doc['_stderr'] = proc['stderr']
    return doc


def meter_argv(tag: str, root: Path, only=None) -> list:
    """Standalone invocation of one merged meter against ``root`` (its own path derives ROOT)."""
    script = {'A': A_CHECK, 'B': B_CHECK, 'C': C_CHECK, 'D1': D_HANDOUT, 'DSTAGE': D_STAGE,
              'LOADER': LOADER_RUN}[tag]
    in_clone = Path(root).resolve() != ROOT
    script = (Path(root) / rel(script)) if in_clone else script
    argv = ([sys.executable, str(script)] if script.suffix == '.py'
            else ['bash', str(script)])
    if tag == 'D1':
        argv += ['--phase', 'D1']
    if tag == 'A' and only:
        argv += ['--only', only]
    return argv


def count_verdicts(tag: str, stdout: str) -> tuple:
    """Independent verdict counter: this file's own parsing, not wave_scan's.

    Returns ``(passed, failed, detail)`` where detail is the meter line that carries the numbers.
    """
    lines = stdout.splitlines()
    if tag == 'A':
        m = [re.search(r'RESULT: (PASS|FAIL) \((\d+)/(\d+) checks passed\)', line) for line in lines]
        m = [x for x in m if x]
        if not m:
            raise CheckFailure(f'wave A meter printed no RESULT line: {tail(stdout)}')
        x = m[-1]
        return int(x.group(2)), int(x.group(3)) - int(x.group(2)), x.group(0)
    if tag == 'B':
        passed = sum(1 for line in lines if re.match(r'^(PASS|OK) ', line))
        failed = sum(1 for line in lines if re.match(r'^(FAIL|MISMATCH) ', line))
        marker = 'ALL_WAVE_B_CHECKS_MATCH_SPEC' if 'ALL_WAVE_B_CHECKS_MATCH_SPEC' in stdout \
            else 'MISMATCH'
        return passed, failed, marker
    if tag == 'C':
        m = [re.search(r'RESULT: (\S+) \| probes=(\d+) failed=(\d+)', line) for line in lines]
        m = [x for x in m if x]
        if not m:
            raise CheckFailure(f'wave C meter printed no RESULT line: {tail(stdout)}')
        x = m[-1]
        return int(x.group(2)) - int(x.group(3)), int(x.group(3)), x.group(0)
    if tag in ('D1', 'DSTAGE'):
        m = [re.search(r'SUMMARY checks=(\d+) failed=(\d+)', line) for line in lines]
        m = [x for x in m if x]
        if not m:
            raise CheckFailure(f'{tag} meter printed no SUMMARY line: {tail(stdout)}')
        x = m[-1]
        return int(x.group(1)) - int(x.group(2)), int(x.group(2)), x.group(0)
    if tag == 'LOADER':
        m = [re.search(r'REAL MAPS ok=(\d+)/(\d+) failures=(\d+)', line) for line in lines]
        m = [x for x in m if x]
        if not m:
            raise CheckFailure(f'loader harness printed no REAL MAPS line: {tail(stdout)}')
        x = m[-1]
        ok = int(x.group(1)) == int(x.group(2)) and int(x.group(3)) == 0
        return (1 if ok else 0), (0 if ok else 1), x.group(0)
    raise CheckFailure(f'unknown meter tag {tag}')


# ---------------------------------------------------------------------------
# shared probes
# ---------------------------------------------------------------------------

def union_swift_files(root: Path, base: str) -> list:
    """This file's own derivation of the union set - an independent witness to AC-001's count."""
    found = set()
    for args in (['diff', '--name-only', f'{base}..HEAD', '--', '*.swift'],
                 ['diff', '--name-only', 'HEAD', '--', '*.swift'],
                 ['ls-files', '--others', '--exclude-standard', '*.swift']):
        proc = run(['git', *[str(a) for a in args]], cwd=root, timeout=180)
        if proc['returncode'] != 0:
            detail = proc['stderr'][:200]
            raise CheckFailure(f'git {args[0]} {args[-1]} failed in {root}: {detail}')
        found.update(line for line in proc['stdout'].splitlines() if line.strip())
    return sorted(found)


def written(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def _commit_is_ancestor_or_head(ref: str) -> bool:
    """A transcript may cite HEAD or the commit it was recorded before committing."""
    return run(['git', 'merge-base', '--is-ancestor', ref, 'HEAD'],
               cwd=ROOT, timeout=60)['returncode'] == 0


def _last_line(text: str) -> str:
    kept = [line for line in (text or '').splitlines() if line.strip()]
    return kept[-1].strip() if kept else ''


def meter_result(stdout: str) -> str:
    lines = [line for line in stdout.splitlines()
             if re.match(r'^(RESULT|SUMMARY|MISMATCH)', line.strip())]
    return ' | '.join(lines[-3:])[:300]


def synth_artifacts(name: str, extras: list) -> Path:
    """An artifact directory holding the given ``emission_cost`` extras, in the harness's format.

    The wave A meter reads ``fixed/manifest.json`` for its cost numbers, so writing that file is an
    on-disk mutation of the meter's real input - not a monkey-patch of the check in memory.
    """
    root = ensure_work() / name
    written(root / 'fixed' / 'manifest.json',
            json.dumps({'artifacts': str(root), 'ran': True,
                        'scenarios': {'emission_cost': extras}}) + '\n')
    return root


# ---------------------------------------------------------------------------
# AC-001
# ---------------------------------------------------------------------------

def scan_covers_committed_union() -> str:
    require(WAVE_SCAN.is_file(), f'{rel(WAVE_SCAN)} does not exist')
    doc = wave_scan(ROOT, 'parse,attribution')
    parse = doc['parse']
    files = [entry['path'] for entry in parse['files']]
    got = union_swift_files(ROOT, doc['base'])
    missing = sorted(set(got) - set(files))
    if missing:
        raise CheckFailure(f'wave_scan parses {len(files)} files but the union is {len(got)}; '
                           f'not covered: {missing[:4]}')
    if len(files) != len(got):
        raise CheckFailure(f'wave_scan reports {len(files)} parse targets, the union is {len(got)}')
    for needle in ('GameplayEventLog.swift', 'BlasterBullet.swift', 'Grenade.swift',
                   'TMXTileMapRenderer.swift', 'evidence/harness/main.swift',
                   'wave_b_harness/main.swift', 'ledger-xcheck/main.swift'):
        if not any(needle in path for path in files):
            raise CheckFailure(f'the committed union set is missing {needle} ({len(files)} files)')
    bad = [f'{f["path"]}: {f["verdict"]}' for f in parse['files']
           if f['verdict'] != 'ok' and not f['verdict'].startswith('deleted')]
    if bad or int(parse.get('skipped', 0)):
        raise CheckFailure(f'committed Swift does not parse: {bad[:3]}')
    st = parse.get('selftest') or {}
    require(st.get('broken_reddens') is True and st.get('good_parses') is True,
            f'the parse gate is not falsifiable (selftest={st})')
    if int(parse['total']) < 20:
        raise CheckFailure(f'parse set is {parse["total"]} files, expected the full A-D union (>=20)')

    clone = clone_tree('ac001-committed-garbage')
    victim = clone / 'Exolon/GameCore/Weapons/BlasterBullet.swift'
    text = victim.read_text(encoding='utf-8')
    written(victim, text + '\nstruct CommittedGarbage {\n    let broken: Int\n')
    git('add', '--', 'Exolon/GameCore/Weapons/BlasterBullet.swift', cwd=clone)
    git("-c", "user.name=wave-e1-control", "-c", "user.email=control@localhost",
        'commit', '-q', '-m', 'planted syntax error in a committed file (AC-001 control)',
        cwd=clone)
    if git('status', '--porcelain', '--', 'Exolon', 'Exolon.xcodeproj', cwd=clone).strip():
        raise CheckFailure('the planted syntax error is not committed in the control tree')
    red = wave_scan(clone, 'parse')
    if is_green(red) or int(red['parse']['failures']) < 1:
        raise CheckFailure('committed syntax garbage does not redden the parse contour '
                           f'(result={red["result"]}, failures={red["parse"]["failures"]})')
    if not any('BlasterBullet.swift' in problem for problem in red['problems']):
        raise CheckFailure(f'the red parse verdict does not name the planted file: {red["problems"][:2]}')

    clone2 = clone_tree('ac001-untracked')
    written(clone2 / 'Exolon/GameCore/UntrackedGarbageE1.swift',
            'struct UntrackedGarbageE1 {\n  let broken: Int\n')
    dyn = wave_scan(clone2, 'parse')
    names = [f['path'] for f in dyn['parse']['files']]
    if 'Exolon/GameCore/UntrackedGarbageE1.swift' not in names:
        raise CheckFailure(f'an untracked new Swift file is not in the parse set ({len(names)} files)')
    if int(dyn['parse']['failures']) < 1 or is_green(dyn):
        raise CheckFailure('syntax garbage in an untracked file does not redden the scan')
    if git('status', '--porcelain', '--', 'Exolon', 'Exolon.xcodeproj').strip():
        raise CheckFailure('the real tree shows product changes after the AC-001 controls')
    return (f'committed union {len(files)} .swift files (product {parse["product_files"]} + '
            f'evidence {parse["evidence_files"]}) all parse ok, selftest {st}; '
            f'committed garbage reddened BlasterBullet.swift, untracked garbage entered the set '
            f'({int(dyn["parse"]["total"])} files)')


# ---------------------------------------------------------------------------
# AC-002
# ---------------------------------------------------------------------------

def attribution_scan_flips() -> str:
    require(WAVE_SCAN.is_file(), f'{rel(WAVE_SCAN)} does not exist')
    doc = wave_scan(ROOT, 'parse,attribution')
    att = doc['attribution']
    if int(att['violations']) != 0:
        raise CheckFailure(f'the accumulated A-D delta reports {att["violations"]} violations: '
                           f'{att["violation_details"][:2]}')
    buckets = att['buckets']
    if len(buckets) < 4:
        raise CheckFailure(f'{len(buckets)} attribution buckets, expected one '
                           'per merged wave')
    merged = [b for b in buckets if b['merge_subject'].startswith('Merge pull request')]
    zero = [b['name'] for b in merged if int(b['code_lines']) <= 0]
    if zero:
        raise CheckFailure('a merged wave bucket scanned zero added code lines (the #21 hole): '
                           + str(zero))
    non_empty = [b for b in buckets if int(b['code_lines']) > 0]
    if len(non_empty) < 4:
        raise CheckFailure(f'only {len(non_empty)} non-empty buckets, expected the four '
                           'merged waves A-D')
    mine = union_added_code_lines(ROOT, doc['base'])
    if mine != int(att['code_lines']):
        raise CheckFailure(f'wave_scan scanned {att["code_lines"]} added code lines, my own '
                           f'recount of the same diff is {mine}')
    allow = att.get('constant_allow_list')
    if allow != ['Exolon/GameCore/GameConstants.swift']:
        raise CheckFailure(f'the magic-literal allowance is {allow}, expected exactly the '
                           'single-source constants file')

    def plant(name, path, line, expect_pattern, expect_bucket=None, committed=False):
        clone = clone_tree(name)
        victim = clone / path
        original = victim.read_text(encoding='utf-8')
        written(victim, original.rstrip('\n') + '\n' + line + '\n')
        if committed:
            git('add', '--', path, cwd=clone)
            git('-c', 'user.name=wave-e1-control', '-c', 'user.email=control@localhost',
                'commit', '-q', '-m', 'planted violation (AC-002 control)', cwd=clone)
        out = wave_scan(clone, 'attribution')
        details = out['attribution']['violation_details']
        hit = [d for d in details if expect_pattern in d['pattern'] and path in d['path']]
        if is_green(out) or not hit:
            raise CheckFailure(f'planted {expect_pattern} at {path} did not redden the '
                               f'attribution scan (result={out["result"]}, '
                               f'violations={out["attribution"]["violations"]})')
        if expect_bucket is not None and hit[0]['bucket'] != expect_bucket:
            raise CheckFailure(f'planted violation landed in bucket {hit[0]["bucket"]!r}, '
                               f'expected {expect_bucket!r}')
        return hit[0]

    per_map = plant('ac002-per-map', 'Exolon/GameCore/GameScene.swift',
                    '        if name == "L01S02" { return 48.0 }', 'per-map')
    delta = plant('ac002-delta16', 'Exolon/GameCore/Objects/LevelObstacles.swift',
                  '        let probe: CGFloat = marker.x + 16', '±16')
    boundary = plant('ac002-boundary', 'Exolon/GameCore/Levels/TMXMapLoader.swift',
                     '        let probe: CGFloat = 544.0', 'граница')
    committed_hit = plant('ac002-committed', 'Exolon/GameCore/GameScene.swift',
                          '        if name == "L05S99" { return 1.0 }', 'per-map', committed=True)

    clone = clone_tree('ac002-constants-allow-list')
    victim = clone / 'Exolon/GameCore/GameConstants.swift'
    original = victim.read_text(encoding='utf-8')
    written(victim, original.rstrip('\n') + '\n    static let e1ProbeBound = 544.0\n')
    ok = wave_scan(clone, 'attribution')
    if not is_green(ok) or int(ok['attribution']['violations']) != 0:
        raise CheckFailure('the constants allow-list does not exempt a boundary literal in '
                           f'GameConstants.swift (violations={ok["attribution"]["violations"]})')
    written(victim, original.rstrip('\n') + '\n        if name == "L01S02" { return 1.0 }\n')
    red = wave_scan(clone, 'attribution')
    if is_green(red) or not red['attribution']['violation_details']:
        raise CheckFailure('the allow-list also hides per-map logic (FORBID-002)')
    if git('status', '--porcelain', '--', 'Exolon', 'Exolon.xcodeproj').strip():
        raise CheckFailure('the real tree shows product changes after the AC-002 controls')
    names = ', '.join(f"{b['name']}={b['code_lines']}" for b in buckets)
    return (f'0 violations over {att["code_lines"]} added code lines in {att["files"]} product '
            f'files across {len(buckets)} buckets ({names}); '
            f'planted per-map/±16/544 all reddened ({per_map["bucket"]}, {delta["bucket"]}, '
            f'{boundary["bucket"]}), committed plant attributed to {committed_hit["bucket"]}; '
            'allow-list exempts a constant but not per-map logic')


def union_added_code_lines(root: Path, base: str) -> int:
    """Count non-comment added Swift code lines from ``base`` to the working tree, independently."""
    proc = run(['git', 'diff', '-U0', base, '--', 'Exolon'], cwd=root, timeout=300)
    if proc['returncode'] != 0:
        detail = proc['stderr'][:200]
        raise CheckFailure(f'git diff -U0 {base} failed: {detail}')
    path, total = None, 0
    for line in proc['stdout'].splitlines():
        if line.startswith('+++ b/'):
            path = line[6:]
        elif line.startswith('+') and not line.startswith('+++'):
            if not (path or '').endswith('.swift'):
                continue
            code = re.sub(r'///?.*', '', line[1:])
            code = re.sub(r'/\*.*?\*/', '', code, flags=re.S)
            if code.strip():
                total += 1
    return total


# ---------------------------------------------------------------------------
# AC-003
# ---------------------------------------------------------------------------

_SUITE = {'doc': None}


def full_suite() -> dict:
    """Run the whole tool once and cache it - AC-003 and INV-001 must read the same suite."""
    if _SUITE['doc'] is None:
        _SUITE['doc'] = wave_scan(ROOT)
    return _SUITE['doc']


def is_green(doc: dict) -> bool:
    """`WAVE_SCAN_GREEN` and `WAVE_SCAN_GREEN_PARTIAL` both mean "nothing failed"; only the first
    is the series contour, and every check here names which one it demands."""
    return str(doc.get('result', '')).startswith('WAVE_SCAN_GREEN')


def meter_entries(doc: dict) -> dict:
    return {entry['name']: entry for entry in doc['meters']['entries']}


def cross_wave_suite_green() -> str:
    require(WAVE_SCAN.is_file(), f'{rel(WAVE_SCAN)} does not exist')
    doc = full_suite()
    entries = meter_entries(doc)
    if sorted(entries) != sorted(METER_NAMES):
        raise CheckFailure(f'the suite ran {sorted(entries)}, expected {sorted(METER_NAMES)}')
    if doc['result'] != 'WAVE_SCAN_GREEN' or doc['_returncode'] != 0:
        raise CheckFailure(f'wave_scan is not green: result={doc["result"]} '
                           f'rc={doc["_returncode"]} problems={doc["problems"][:4]}')
    if int(doc['totals']['meters_green']) != len(METER_NAMES):
        raise CheckFailure(f'{doc["totals"]["meters_green"]}/{len(METER_NAMES)} meters green: '
                           f'{doc["problems"][:3]}')
    bad = []
    for name, expected in ((n, e) for n, _, _, e, _ in METERS):
        entry = entries[name]
        if (int(entry['rc']) != 0 or int(entry['failed']) != 0
                or int(entry['passed']) != expected or not entry['green']):
            bad.append(f'{name}: rc={entry["rc"]} passed={entry["passed"]}/{expected} '
                       f'failed={entry["failed"]} line={entry.get("verdict_line")}')
    if bad:
        raise CheckFailure('meter sub-results do not match the recorded verdict counts: '
                           + '; '.join(bad))
    loader = entries['loader-harness-125maps']
    if 'ok=125/125' not in str(loader.get('verdict_line')):
        raise CheckFailure(f'the loader harness did not reproduce 125/125: {loader}')
    if float(doc['seconds']) > 600:
        raise CheckFailure(f'wave_scan took {doc["seconds"]} s, the budget is 10 min (SIG-001)')

    clone = clone_tree('ac003-forced-red-meter')
    victim = clone / 'Exolon/GameCore/GameConstants.swift'
    text = victim.read_text(encoding='utf-8')
    if 'static let phaseTicks = 1_800' not in text:
        raise CheckFailure('the forced-red control lost its anchor: phaseTicks is no longer 1_800')
    written(victim, text.replace('static let phaseTicks = 1_800', 'static let phaseTicks = 1_801', 1))
    probe = wave_scan(clone, 'meters', meters=['wave-d-stage'])
    if [e['name'] for e in probe['meters']['entries']] != ['wave-d-stage']:
        raise CheckFailure('--meter did not restrict the suite: the control would silently run '
                           f"every meter ({[e['name'] for e in probe['meters']['entries']]})")
    if len(probe['meters']['skipped']) != len(METER_NAMES) - 1:
        raise CheckFailure(f"the restricted run reports {probe['meters']['skipped']}")
    stage = meter_entries(probe)['wave-d-stage']
    if probe['result'] != 'WAVE_SCAN_RED' or probe['_returncode'] != 1 or stage['green']:
        raise CheckFailure(f'a forced-red meter did not redden the suite (result={probe["result"]} '
                           f'rc={probe["_returncode"]} meter={stage})')
    if not probe.get('partial'):
        raise CheckFailure(f'a restricted suite is not reported as partial: {probe.get("partial")}')

    clone2 = clone_tree('ac003-meter-absent')
    (clone2 / rel(D_STAGE)).unlink()
    probe2 = wave_scan(clone2, 'meters', meters=['wave-d-stage'])
    if probe2['result'] != 'WAVE_SCAN_RED':
        raise CheckFailure(f'an absent meter script does not read red (result={probe2["result"]})')
    counts = ', '.join(f'{n}={entries[n]["passed"]}' for n in METER_NAMES)
    return (f'{doc["totals"]["meters_green"]}/{len(METER_NAMES)} meters green ({counts}), parse '
            f'{doc["totals"]["parse_failures"]} failures, attribution '
            f'{doc["totals"]["attribution_violations"]} violations in {doc["seconds"]} s; '
            f'forced-red meter reddened the suite ({stage["failed"]} failed), absent meter is red')


# ---------------------------------------------------------------------------
# AC-004
# ---------------------------------------------------------------------------

def loader_harness_green() -> str:
    run_sh = read(LOADER_RUN)
    step4 = re.search(r'swiftc -I "\$BUILD" -L "\$BUILD" -lCoreGraphics[^\n]*\n'
                      r'(?:[ \t]+\S[^\n]*\n)+', run_sh)
    if not step4 or 'GameConstants.swift' not in step4.group(0):
        raise CheckFailure('run.sh step 4 does not compile Exolon/GameCore/GameConstants.swift')
    header = run_sh.split('set -euo pipefail')[0]
    require('E1 provenance' in header or 'wave E1' in header,
            'run.sh carries no E1 provenance header comment for the added file')

    proc = run(['bash', str(LOADER_RUN)], timeout=900)
    if proc['returncode'] != 0:
        raise CheckFailure('loader harness rc=%s: %s || %s'
                           % (proc['returncode'], tail(proc['stdout'], 500),
                              tail(proc['stderr'], 200)))
    maps = re.search(r'REAL MAPS ok=(\d+)/(\d+) failures=(\d+)', proc['stdout'])
    if not maps or maps.group(1) != '125' or maps.group(2) != '125' or maps.group(3) != '0':
        raise CheckFailure(f'loader harness did not reproduce 125/125: {maps and maps.group(0)}')
    for control in ('OK: удаление строки 2 возвращает файл к репозиторному',
                    'OK: без стаба не собирается'):
        if control not in proc['stdout']:
            raise CheckFailure(f'the harness negative control is gone: {control}')

    last_run = read(LOADER_LAST_RUN)
    require('REAL MAPS ok=125/125 failures=0' in last_run,
            'last-run.txt does not record REAL MAPS ok=125/125 failures=0')
    cited = re.search(r'HEAD=(\w{7,40})', last_run)
    require(cited and _commit_is_ancestor_or_head(cited.group(1)),
            'last-run.txt cites %s, which is neither HEAD (%s) nor its ancestor'
            % (cited and cited.group(1), short_head()))
    require('wave E1' in last_run[:400],
            'last-run.txt header does not name the wave E1 regeneration')
    readme = read(LOADER_README)
    row = [line for line in readme.splitlines() if 'last-run.txt' in line and line.startswith('|')]
    require(row and 'ok=125/125' in row[0] and 'wave E1' in row[0]
            and cited.group(1)[:7] in row[0],
            f'the harness README does not cite the regenerated transcript: {row[:1]}')

    clone = clone_tree('ac004-one-line-revert')
    rel_run = rel(LOADER_RUN)
    git('checkout', '--', rel_run, cwd=clone)     # safe: a clone owns its gitdir
    reverted = (clone / rel_run).read_text(encoding='utf-8')
    still = re.search(r'swiftc -I[^\n]*\n(?:[ \t]+\S[^\n]*\n)+', reverted)
    if not still or 'GameConstants.swift' in still.group(0):
        raise CheckFailure('the control tree still has the fix, so the control proves nothing')
    back = run(['bash', str(clone / rel_run)], timeout=900)
    if back['returncode'] == 0:
        raise CheckFailure('reverting the one-line fix still leaves the harness green (vacuous fix)')
    joined = back['stdout'] + back['stderr']
    if "cannot find 'GameConstants' in scope" not in joined:
        raise CheckFailure(f'the reverted harness failed for another reason: {tail(joined, 300)}')
    return (f'step 4 compiles GameConstants.swift, run.sh rc=0 with {maps.group(0)} and both '
            f'negative controls; last-run.txt + README re-recorded at HEAD {short_head()}; '
            'reverting the line gives "cannot find \'GameConstants\' in scope"')


# ---------------------------------------------------------------------------
# AC-005
# ---------------------------------------------------------------------------

# What a frozen-historical header must say, in either language the package is written in.
FROZEN_TOKENS = (('frozen-historical', 'frozen_historical'), ('wave_c_check.py',),
                 ('76', '51'), ('no behavior change', 'not maintained', 'не менялось'),
                 ('pre-fix', 'дофиксов'), ('abort', 'crash', 'падает'))


def frozen_header_problems(text: str) -> list:
    """Pure over text, so the falsification control can feed it a copy with the header stripped."""
    head = '\n'.join(text.splitlines()[:40]).lower()
    problems = []
    for group in FROZEN_TOKENS:
        if not any(token.lower() in head for token in group):
            problems.append(f'the header never says {"/".join(group)!r}')
    return problems


def v3_header_present() -> str:
    text = read(V3_MIRROR)
    problems = frozen_header_problems(text)
    if problems:
        raise CheckFailure(f'v3_measurements.py header: {"; ".join(problems)}')
    parts = text.split('"""', 2)          # shebang, docstring, body
    require(len(parts) == 3, 'v3_measurements.py has no single module docstring')
    stripped = parts[0] + '"""placeholder"""' + parts[2]
    control = frozen_header_problems(stripped)
    if not control:
        raise CheckFailure('the header predicate cannot be falsified (copy without a header passes)')

    clone = clone_tree('ac005-frozen-behavior')
    rel_v3 = rel(V3_MIRROR)
    git('checkout', '--', rel_v3, cwd=clone)
    before = run([sys.executable, str(clone / rel_v3)], timeout=300)
    after = run([sys.executable, str(V3_MIRROR)], timeout=300)
    if before['stdout'] != after['stdout']:
        raise CheckFailure('v3_measurements.py stdout changed - the header was not inert')
    last_before = _last_line(before['stderr'])
    last_after = _last_line(after['stderr'])
    if last_before.splitlines()[-1:] != last_after.splitlines()[-1:]:
        raise CheckFailure('v3_measurements.py failure mode changed - the header was not inert')

    c_text = read(C_CHECK)
    if 'owner-route cleanup owed' in c_text:
        raise CheckFailure("wave C's stale-mirror WARNING still promises pending cleanup")
    require('frozen-historical' in c_text,
            "wave C's stale-mirror WARNING does not point at the frozen-historical header")
    for key in ('still_covers', 'product_actually_covers', 'stale',
                'divergence', 'baseline_agrees'):
        if key not in c_text:
            raise CheckFailure(f'the stale-mirror logic changed shape ({key} is gone)')
    live = run([sys.executable, str(C_CHECK)], timeout=600)
    warns = [line for line in live['stdout'].splitlines() if line.startswith('WARNING')]
    require(live['returncode'] == 0 and 'ALL_WAVE_C_PROBES_PASS' in live['stdout'],
            f'wave C meter is not green after the wording edit: {meter_result(live["stdout"])}')
    require(len(warns) >= 2 and all('frozen-historical' in line for line in warns),
            f'the printed WARNINGs do not cite the header: {warns[:2]}')
    return (f'v3 header frozen (tokens {FROZEN_TOKENS}), stdout and failure mode byte-identical '
            f'to the pre-edit copy (rc={after["returncode"]}, {len(after["stdout"])} chars); '
            f'C meter green with {len(warns)} header-citing WARNINGs: {warns[0][:110]}')


# ---------------------------------------------------------------------------
# AC-006
# ---------------------------------------------------------------------------

def b_meter_failclosed() -> str:
    src = read(B_CHECK)
    require('refs/remotes/origin/main' in src,
            'wave_base() no longer looks at refs/remotes/origin/main, so it cannot fail closed')
    require('wave_base' in src and re.search(r'def wave_base\(\)', src),
            'wave_base() is gone from wave_b_check.py')

    clone = clone_tree('ac006-no-origin', pin_origin=False)
    drop_origin(clone)
    proc = run(meter_argv('B', clone), timeout=600)
    joined = proc['stdout'] + proc['stderr']
    if proc['returncode'] == 0:
        raise CheckFailure('wave_b_check.py is green in a clone without refs/remotes/origin/main')
    if 'ALL_WAVE_B_CHECKS_MATCH_SPEC' in joined:
        raise CheckFailure('the remote-less clone still prints the green verdict line')
    require('origin/main' in joined,
            f'the non-zero exit is not explained by the missing ref: {tail(joined, 300)}')
    require('FAIL-CLOSED' in joined.upper(),
            f'the missing-ref path prints no explicit fail-closed error: {tail(joined, 300)}')
    if 'added-lines: ' in joined:
        raise CheckFailure('the remote-less clone still ran a scan (the old wide fallback)')

    pinned = clone_tree('ac006-origin-pinned')
    ok = run(meter_argv('B', pinned), timeout=600)
    if ok['returncode'] != 0 or 'ALL_WAVE_B_CHECKS_MATCH_SPEC' not in ok['stdout']:
        raise CheckFailure(f'B is not green with origin/main pinned: {meter_result(ok["stdout"])}')
    scanned = re.search(r'added-lines: (\d+) стронок кода в (\d+) изменённых продуктовых файлах',
                        ok['stdout'])
    if not scanned or int(scanned.group(1)) < 150 or int(scanned.group(2)) < 7:
        raise CheckFailure(f'the root re-anchor did not keep B\'s scan non-vacuous: {scanned}')
    hygiene = run(['git', 'show-ref'], cwd=ROOT, timeout=60)['stdout']
    if re.search(r'refs/heads/origin/', hygiene):
        raise CheckFailure(f'ref pollution in the real repository: {hygiene.splitlines()[-3:]}')
    if short_head() not in run(['git', 'rev-parse', '--short', 'refs/remotes/origin/main'],
                              cwd=ROOT, timeout=60)['stdout']:
        raise CheckFailure("the real refs/remotes/origin/main moved during the AC-006 controls")
    return (f'remote-less clone: rc={proc["returncode"]} with the explicit fail-closed error; '
            f'pinned clone: green with {scanned.group(1)} added code lines in '
            f'{scanned.group(2)} files; real-tree refs clean '
            f'({len(hygiene.splitlines())} refs, no refs/heads/origin/)')


# ---------------------------------------------------------------------------
# AC-007
# ---------------------------------------------------------------------------

def _func_body(text: str, name: str) -> str:
    match = re.search(rf'\ndef {re.escape(name)}\(.*?(?=\ndef |\nclass |\Z)', text, re.S)
    if not match:
        raise CheckFailure(f'{name} is gone from {text[:40]}...')
    return match.group(0)


def _git_show(path: Path) -> str:
    return git('show', f'HEAD:{rel(path)}')


def m3_soft_band() -> str:
    a_src = read(A_CHECK)
    body = _func_body(a_src, 'emission_cost_budget')
    if 'WARNING' not in body:
        raise CheckFailure('emission_cost_budget prints no WARNING - the band was never softened')
    for hard in ('if producer <= 0:', 'if control < producer * 5:', 'if capacity < 3_600 * 8:'):
        after = body.split(hard, 1)[1][:300] if hard in body else ''
        if not after or 'raise' not in after:
            raise CheckFailure(f'the deterministic twin {hard!r} is not a hard failure')
    harness = read(A_HARNESS_MAIN)
    if 'Harness.check(producerNs > 1 && producerNs * 60 < 5_000' in harness:
        raise CheckFailure('the harness still hard-fails on the ~4 us M3 band')
    if 'func warn(' not in harness:
        raise CheckFailure('the harness has no warn() helper, so the soft band cannot be reported')

    over = synth_artifacts('ac007-over-band', [
        'producer_ns_per_event=42.0', 'percent_of_tick=99.0',
        'formatting_control_ns_per_event=1000.0', 'drain_ns_per_event=1.0',
        'drain_capacity_ev_per_s=999999'])
    soft = run(meter_argv('A', ROOT, only='emission_cost_budget') + ['--artifacts', str(over)],
               timeout=600)
    if soft['returncode'] != 0:
        raise CheckFailure(f'an over-band timing value still fails the check: {meter_result(soft["stdout"])}')
    warned = [line for line in soft['stdout'].splitlines() if 'WARNING' in line]
    if not warned or '99' not in warned[0]:
        raise CheckFailure(f'no WARNING with the measured value: {soft["stdout"][-300:]}')

    absurd = synth_artifacts('ac007-zero-clock', [
        'producer_ns_per_event=0', 'percent_of_tick=0.0',
        'formatting_control_ns_per_event=1.0', 'drain_ns_per_event=1.0',
        'drain_capacity_ev_per_s=999999'])
    zero = run(meter_argv('A', ROOT, only='emission_cost_budget') + ['--artifacts', str(absurd)],
               timeout=600)
    if zero['returncode'] == 0:
        raise CheckFailure('a clock that measured nothing (0 ns/event) passes - no sane-band twin')

    ratio = synth_artifacts('ac007-control-ratio', [
        'producer_ns_per_event=42.0', 'percent_of_tick=0.01',
        'formatting_control_ns_per_event=100.0', 'drain_ns_per_event=1.0',
        'drain_capacity_ev_per_s=999999'])
    control = run(meter_argv('A', ROOT, only='emission_cost_budget') + ['--artifacts', str(ratio)],
                  timeout=600)
    if control['returncode'] == 0:
        raise CheckFailure('the formatting control < 5x the append is no longer a hard failure')

    drain = synth_artifacts('ac007-drain-low', [
        'producer_ns_per_event=42.0', 'percent_of_tick=0.01',
        'formatting_control_ns_per_event=1000.0', 'drain_ns_per_event=1.0',
        'drain_capacity_ev_per_s=100'])
    low = run(meter_argv('A', ROOT, only='emission_cost_budget') + ['--artifacts', str(drain)],
              timeout=600)
    if low['returncode'] == 0:
        raise CheckFailure('the drain-capacity floor (8x realtime) is no longer a hard failure')

    alloc = run(meter_argv('A', ROOT, only='hot_path_is_allocation_free')
                + ['--artifacts', str(over)], timeout=600)
    if alloc['returncode'] != 0:
        raise CheckFailure(f'the allocation scan reddens on a clean tree: {meter_result(alloc["stdout"])}')
    clone = clone_tree('ac007-alloc-mutation')
    log_path = clone / rel(DIAG_LOG)
    original = log_path.read_text(encoding='utf-8')
    anchor = ('    private func appendRecord(_ rawKind: UInt8, _ entity: UInt16, '
              '_ a: Int16, _ b: Int16, _ c: Int16, _ d: Int16) {\n')
    if anchor not in original:
        raise CheckFailure('appendRecord signature changed; the allocation control lost it')
    written(log_path, original.replace(
        anchor, anchor + '        let e1Probe = String(describing: rawKind)\n', 1))
    mutated = run(meter_argv('A', clone, only='hot_path_is_allocation_free')
                  + ['--artifacts', str(over)], timeout=600)
    if mutated['returncode'] == 0:
        raise CheckFailure('an allocating hot path on disk does not redden the allocation scan '
                           '(FORBID-002: the leniency swallowed its hard twin)')
    if _func_body(a_src, 'hot_path_is_allocation_free') != \
            _func_body(_git_show(A_CHECK), 'hot_path_is_allocation_free'):
        raise CheckFailure('hot_path_is_allocation_free was edited by wave E1')

    swift_clone = clone_tree('ac007-swift-band')
    main_path = swift_clone / rel(A_HARNESS_MAIN)
    text = main_path.read_text(encoding='utf-8')
    if 'producerNs > 1' not in text:
        raise CheckFailure('the harness lower bound is gone - nothing left to prove hard')
    mutated_swift = text.replace('producerNs > 1', 'producerNs > 1_000_000_000_000', 1)
    mutated_swift = re.sub(r'producerNs \* 60 < 5_000', 'producerNs * 60 < 0', mutated_swift, count=1)
    written(main_path, mutated_swift)
    both = run(['bash', str(swift_clone / rel(A_PKG) / 'evidence/harness/run.sh')], timeout=900)
    joined = both['stdout'] + both['stderr']
    if both['returncode'] == 0:
        raise CheckFailure('the harness lower-bound breach did not fail the run')
    if 'producerNs > 1_000_000_000_000' not in joined and '60 locked appends' not in joined:
        raise CheckFailure(f'the hard breach is not reported: {tail(joined, 300)}')
    if 'FAIL' not in joined:
        raise CheckFailure('no FAIL line for the hard breach')
    warn_lines = [line for line in joined.splitlines() if line.startswith('WARNING')]
    if not warn_lines or 'M3' not in ' '.join(warn_lines):
        raise CheckFailure(f'the over-band M3 value printed no WARNING ({warn_lines[:2]})')
    if any('FAIL' in line and 'M3' in line for line in joined.splitlines()):
        raise CheckFailure('the M3 band is still a hard failure in the harness layer')
    if git('status', '--porcelain', '--', 'Exolon', 'Exolon.xcodeproj').strip():
        raise CheckFailure('the real tree shows product changes after the AC-007 controls')
    return (f'python band soft ({warned[0].strip()[:90]}); 0 ns clock, control <5x and low drain '
            'still FAIL; on-disk allocating appendRecord reddens the hard scan; harness layer '
            'warns on the band yet fails on the deterministic twin')


# ---------------------------------------------------------------------------
# AC-008
# ---------------------------------------------------------------------------

def warp_guid_bound() -> str:
    src = read(D_STAGE)
    body = _func_body(src, 'warp_debug_only')
    require('buildConfigurationList' in body or 'buildConfigurationList' in _helper_callers(src, body),
            'warp_debug_only does not derive the owning block GUID from the project object')
    for token in ('SWIFT_ACTIVE_COMPILATION_CONDITIONS', 'allowed.contains(target)',
                  'transition(to: target)', 'stderr'):
        if token not in body:
            raise CheckFailure(f'the warp check lost a clause: {token}')
    if '!= 1' not in body:
        raise CheckFailure('the exactly-once count guard is gone (belt-and-braces dropped)')

    clone = clone_tree('ac008-warp-guid')
    target = clone / PBXPROJ_REL
    pristine = read(PBXPROJ)

    def restore() -> None:
        written(target, pristine)

    def run_warp() -> dict:
        restore()
        return run([sys.executable, str(clone / rel(D_STAGE)), '--root', str(clone),
                    '--only', 'warp_debug_only'], timeout=300)

    def mutate(move_to: str) -> str:
        """Move the single DEBUG condition into another XCBuildConfiguration block."""
        text = pristine
        setting = '\t\t\t\tSWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG;\n'
        if text.count(setting) != 1:
            raise CheckFailure(f'{rel(PBXPROJ)}: the DEBUG condition is no longer declared '
                               'exactly once - the control lost its anchor')
        text = text.replace(setting, '', 1)
        header = re.search(r'(?ms)^\t\t' + re.escape(move_to) +
                           r' /\*[^*]*\*/ = \{\n\t\t\tisa = XCBuildConfiguration;\n'
                           r'\t\t\tbuildSettings = \{\n', text)
        if not header:
            raise CheckFailure(f'cannot find the buildSettings block of {move_to} to move into')
        return text[:header.end()] + setting + text[header.end():]

    clean = run_warp()
    if clean['returncode'] != 0 or 'RESULT warp_debug_only=PASS' not in clean['stdout']:
        raise CheckFailure(f'warp_debug_only is red on a clean tree: {tail(clean["stdout"], 300)}')

    project_release = '800000000000000000000002'
    target_debug = '800000000000000000000003'
    target_release = '800000000000000000000004'
    results = {}
    for label, guid in (('project-release', project_release), ('target-debug', target_debug),
                        ('target-release', target_release)):
        restore()
        written(target, mutate(guid))
        proc = run([sys.executable, str(clone / rel(D_STAGE)), '--root', str(clone),
                    '--only', 'warp_debug_only'], timeout=300)
        if proc['returncode'] == 0 or 'FAIL' not in proc['stdout']:
            results[label] = 'MISSED'
        else:
            results[label] = 'caught'
    missed = [label for label, verdict in results.items() if verdict != 'caught']
    if missed:
        raise CheckFailure(f'the DEBUG move into {missed} is not caught by warp_debug_only')

    restore()
    written(target, pristine.replace('\t\t\t\tSWIFT_VERSION = 5.0;\n',
                                     '\t\t\t\tSWIFT_VERSION = 5.0;\n'
                                     '\t\t\t\tSWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG;\n', 1))
    dup = run([sys.executable, str(clone / rel(D_STAGE)), '--root', str(clone),
               '--only', 'warp_debug_only'], timeout=300)
    if dup['returncode'] == 0:
        raise CheckFailure('a duplicated (project Debug + target Release) condition passes warp_debug_only')
    restore()
    if read(target) != pristine:
        raise CheckFailure('the control tree did not return to pristine bytes')
    if read(PBXPROJ) != pristine:
        raise CheckFailure('the real project.pbxproj changed while AC-008 ran (FORBID-001)')
    moved = run([sys.executable, str(D_STAGE), '--root', ROOT, '--only', 'warp_debug_only'],
                timeout=300)
    if moved['returncode'] != 0:
        raise CheckFailure(f'warp_debug_only is red against the real tree: {tail(moved["stdout"], 200)}')
    return ('DEBUG in the project Debug block passes; moving it into 800...002/003/004 and '
            f'duplicating it all redden ({", ".join(f"{k}={v}" for k, v in sorted(results.items()))}, '
            'duplicate=caught); real pbxproj byte-unchanged')


def _helper_callers(src: str, body: str) -> str:
    """Source of any helper the warp check calls, so a GUID derivation may live in one."""
    names = re.findall(r'\b([a-z_][a-z0-9_]{4,})\(', body)
    out = []
    for name in set(names):
        try:
            out.append(_func_body(src, name))
        except CheckFailure:
            continue
    return '\n'.join(out)


# ---------------------------------------------------------------------------
# FORBID-001
# ---------------------------------------------------------------------------

E1_PREFIXES = ('engineering/tools/', f'{rel(PKG)}/')
SANCTIONED_MERGED_EDITS = (
    rel(H_PKG / 'evidence/harness/run.sh'),
    rel(H_PKG / 'evidence/harness/last-run.txt'),
    rel(H_PKG / 'evidence/harness/README.md'),
    rel(V3_MIRROR),
    rel(C_CHECK),
    rel(B_CHECK),
    rel(A_CHECK),
    rel(A_HARNESS_MAIN),
    rel(D_STAGE),
)


def _working_paths() -> list:
    out = set()
    for args in (['diff', '--name-only', 'HEAD'], ['diff', '--name-only', '--cached'],
                 ['ls-files', '--others', '--exclude-standard']):
        proc = run(['git', *args], cwd=ROOT, timeout=180)
        if proc['returncode'] != 0:
            detail = proc['stderr'][:200]
            raise CheckFailure(f'{args} failed: {detail}')
        out.update(line for line in proc['stdout'].splitlines() if line.strip())
    return sorted(out)


def product_untouched() -> str:
    dirty = git('status', '--porcelain', '--', 'Exolon', 'Exolon.xcodeproj').strip()
    if dirty:
        raise CheckFailure(f'FORBID-001: the product tree is dirty: {dirty.splitlines()[:4]}')
    base = git('merge-base', 'HEAD', 'refs/remotes/origin/main').strip()
    committed = git('diff', '--name-only', f'{base}..HEAD', '--', 'Exolon', 'Exolon.xcodeproj').strip()
    if committed:
        raise CheckFailure(f'FORBID-001: commits since the E1 base touch the product: '
                           f'{committed.splitlines()[:4]}')
    touched = _working_paths()
    offenders = [path for path in touched
                 if not (path.startswith(E1_PREFIXES) or path in SANCTIONED_MERGED_EDITS)]
    if offenders:
        raise CheckFailure(f'wave E1 edited files outside its scope: {offenders[:5]}')
    scratch = [path for path in touched
               if path.endswith(('.bak', '.orig', '.rej', '.tmp', '.pyc'))
               or '/fixtures/' in path or '__pycache__' in path]
    if scratch:
        raise CheckFailure(f'scratch artifacts left in the repository: {scratch[:5]}')
    sizes = {}
    for path in (p for p in touched if p in SANCTIONED_MERGED_EDITS):
        numstat = git('diff', '--numstat', 'HEAD', '--', path).strip()
        added, deleted = (numstat.split('\t')[:2] if numstat else ('0', '0'))
        sizes[path] = f'+{added}/-{deleted}'
        capped = not path.endswith(('.txt', '.md'))
        if capped and int(added or 0) + int(deleted or 0) > 90:
            raise CheckFailure(f'the merged-tool touch {path} is {sizes[path]}, far beyond a '
                               'recorded one-line/heading edit')
    return (f'{len(touched)} working paths, all inside engineering/tools + this package + '
            f'{len(sizes)} sanctioned merged edits ({", ".join(f"{Path(k).name}:{v}" for k, v in sorted(sizes.items()))}); '
            'Exolon/ and Exolon.xcodeproj byte-clean against HEAD')


# ---------------------------------------------------------------------------
# FORBID-002
# ---------------------------------------------------------------------------

def no_silent_relaxation() -> str:
    b_src = read(B_CHECK)
    if 'n_files >= 7 and n_code >= 150' not in b_src:
        raise CheckFailure("wave B's non-vacuity guard was deleted to buy a green")
    if r'L\d{2}S\d{2}' not in b_src:
        raise CheckFailure("wave B's per-map predicate is gone")
    a_src = read(A_CHECK)
    for name in ('hot_path_is_allocation_free', 'frame_step_budget', 'producer_sites_use_helpers_only'):
        if _func_body(a_src, name) != _func_body(_git_show(A_CHECK), name):
            raise CheckFailure(f'the hard check {name} was edited by wave E1')
    stage_src = read(D_STAGE)
    warp = _func_body(stage_src, 'warp_debug_only')
    if 'SWIFT_ACTIVE_COMPILATION_CONDITIONS' not in warp or '!= 1' not in warp:
        raise CheckFailure('warp_debug_only dropped a clause while gaining the GUID binding')
    c_diff = git('diff', '-U0', 'HEAD', '--', rel(C_CHECK))
    changed = [line[1:].strip() for line in c_diff.splitlines()
               if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))]
    for line in changed:
        if 'stale' in line.lower() or 'divergence' in line:
            raise CheckFailure(f'the wave C stale-mirror edit touched logic, not only text: {line[:90]}')
    if not changed:
        raise CheckFailure('wave_c_check.py shows no edit at all - the WARNING wording was never updated')

    clone = clone_tree('forbid002-b-planted')
    victim = clone / 'Exolon/GameCore/Levels/TMXMapLoader.swift'
    original = victim.read_text(encoding='utf-8')
    written(victim, original.rstrip('\n') + '\n        let probe: CGFloat = marker.x + 16\n')
    proc = run(meter_argv('B', clone), timeout=600)
    if proc['returncode'] == 0 or 'FORBID-001 added' not in proc['stdout']:
        raise CheckFailure(f'wave B no longer bites on a planted ±16 at the root anchor '
                           f'(rc={proc["returncode"]}): {meter_result(proc["stdout"])}')

    missing = run([sys.executable, str(WAVE_SCAN), '--root', ROOT, '--only', 'parse',
                   '--swiftc', str(ROOT / 'no-such-compiler'), '--json'], timeout=300)
    try:
        doc = json.loads(missing['stdout'])
    except ValueError:
        raise CheckFailure(f'wave_scan --json is unparsable when swiftc is absent: {tail(missing["stdout"])}')
    if doc['result'] != 'WAVE_SCAN_RED' or missing['returncode'] != 1:
        raise CheckFailure(f'wave_scan does not fail closed without swiftc '
                           f'(result={doc["result"]} rc={missing["returncode"]})')
    if git('status', '--porcelain', '--', 'Exolon', 'Exolon.xcodeproj').strip():
        raise CheckFailure('the real tree shows product changes after the FORBID-002 controls')
    return ('B non-vacuity guard + planted ±16 red at the root anchor; A hard checks byte-identical '
            'to HEAD; C edit is text-only; wave_scan fails closed without swiftc')


# ---------------------------------------------------------------------------
# INV-001
# ---------------------------------------------------------------------------

def suite_standalone_agreement() -> str:
    doc = full_suite()
    entries = meter_entries(doc)
    rows, mismatches = [], []
    for name, _script, _extra, expected, tag in METERS:
        proc = run(meter_argv(tag, ROOT), timeout=900)
        passed, failed, line = count_verdicts(tag, proc['stdout'])
        entry = entries[name]
        suite_pair = (int(entry['passed']), int(entry['failed']))
        if (passed, failed) != suite_pair or proc['returncode'] != int(entry['rc']):
            mismatches.append(f'{name}: standalone ({passed},{failed},rc={proc["returncode"]}) vs '
                              f'suite {suite_pair} rc={entry["rc"]}')
        if passed != expected or failed != 0 or proc['returncode'] != 0:
            mismatches.append(f'{name}: standalone is not the recorded green '
                              f'({passed}/{expected} failed={failed} rc={proc["returncode"]})')
        rows.append(f'{name} {passed}/{expected}=={suite_pair[0]}')
    if mismatches:
        raise CheckFailure('suite and standalone disagree: ' + '; '.join(mismatches[:4]))
    return ('standalone == suite for all 6 meters (' + ', '.join(rows) + '); '
            'verdict lines: ' + ' | '.join(meter_entries(doc)[n]['verdict_line'][:38]
                                           for n in ('wave-a-gameplay-log', 'loader-harness-125maps')))


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--only', help='comma-separated subset of the named checks')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--keep-work', action='store_true', help='keep the /tmp control trees')
    args = parser.parse_args(argv)

    if args.list:
        for name, binding in CHECKS:
            print(f'{name}  [{binding}]')
        return 0
    wanted = None
    if args.only:
        wanted = {item.strip() for item in args.only.split(',') if item.strip()}
        unknown = wanted - {name for name, _ in CHECKS}
        if unknown:
            print(f'unknown checks: {sorted(unknown)}', file=sys.stderr)
            return 2

    started = time.time()
    sink = sys.stderr if args.json else sys.stdout   # --json keeps stdout pure JSON
    results = {}
    for name, binding in CHECKS:
        if wanted and name not in wanted:
            continue
        stamp = time.time()
        try:
            detail = globals()[name]()
        except CheckFailure as error:
            results[name] = {'binding': binding, 'pass': False, 'reason': str(error)[:1200],
                             'seconds': round(time.time() - stamp, 1)}
            print(f'FAIL {name} [{binding}]: {error}', file=sink, flush=True)
            continue
        except Exception as error:  # a crash is a failed check, never a pass
            results[name] = {'binding': binding, 'pass': False,
                             'reason': f'{type(error).__name__}: {error}'[:1200],
                             'seconds': round(time.time() - stamp, 1)}
            print(f'FAIL {name} [{binding}]: {type(error).__name__}: {error}', file=sink, flush=True)
            continue
        results[name] = {'pass': True, 'detail': detail, 'binding': binding,
                         'seconds': round(time.time() - stamp, 1)}
        print(f'PASS {name} [{binding}] ({results[name]["seconds"]}s): {detail}',
              file=sink, flush=True)

    failed = sorted(name for name, res in results.items() if not res['pass'])
    elapsed = round(time.time() - started, 1)
    if args.json:
        print(json.dumps({'tool': 'wave_e1_check', 'root': str(ROOT), 'head': head_sha(),
                          'base': ROOT_BASE, 'seconds': elapsed, 'checks': len(results),
                          'failed': len(failed), 'results': results,
                          'result': 'WAVE_E1_PROBES_PASS' if not failed else 'WAVE_E1_PROBES_FAIL'},
                         indent=2, sort_keys=True))
    else:
        print(f'RESULT: {"WAVE_E1_PROBES_FAIL" if failed else "WAVE_E1_PROBES_PASS"} | '
              f'probes={len(results)} failed={len(failed)} seconds={elapsed}')
        for name in failed:
            print(f'  ! {name}: {results[name]["reason"][:300]}')
    if not args.keep_work and WORK.exists():
        shutil.rmtree(WORK, ignore_errors=True)
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
