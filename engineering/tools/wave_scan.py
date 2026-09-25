#!/usr/bin/env python3
"""Root-anchored union scan and merged-meter suite for the Exolon A-D chain (wave E1).

Why this exists (issues #21, #22 items 1-3): every wave policed only its own uncommitted diff, so
once a wave was merged its files left everybody's parse and attribution sets - measured 2 494
wave-A added code lines scanned by nobody after wave B re-anchored its base to
``merge-base(HEAD, origin/main)``. This tool re-polices the *accumulated* delta from the change root
``295690b`` down, and runs every merged meter as one suite so a series contour is one command.

Three contours, all root-anchored:

  parse        ``swiftc -frontend -parse`` over the union of
               ``git diff --name-only <base>..HEAD -- '*.swift'`` (everything committed since the
               root), ``git diff --name-only HEAD`` (the working tree) and untracked ``*.swift``.
               Includes the evidence harness drivers, which is where harness drift would otherwise
               hide. Self-falsifying: a known-broken and a known-good file must disagree.
  attribution  the merged FORBID-001 predicates (``+/-16`` offsets, the pinned ``528/544/560``
               boundary literals, ``LxxSyy`` per-map names) re-run over *every* added line from the
               root base to the working tree, bucketed per wave range by the merge history so a
               violation names the wave that introduced it. The numeric predicates skip exactly one
               file, ``Exolon/GameCore/GameConstants.swift`` - the single source those boundaries
               are defined in; the per-map predicate applies there too.
  meters       each merged meter runs as a subprocess with its verdict counts recorded:
               wave A 28, wave B 9, wave C 9, wave D handout 11 (``--phase D1``), wave D stage 10,
               plus the 20260919 loader harness at 125/125 maps. Green only if every one is green.

Fail-closed rules: an absent compiler, an absent meter script, an unparsable verdict line, a
timeout or a budget overrun is always a failure, never a skip.

Exit codes: 0 = the whole contour is green, 1 = red, 2 = usage, 3 = clean but PARTIAL (a restricted
run - `--only`/`--meter` - which is never the series contour). The partial verdict is
`WAVE_SCAN_PARTIAL`, deliberately NOT a string super-set of `WAVE_SCAN_GREEN` (review-code R8: any
consumer that greps instead of reading `--json`/exit code must not be able to read a restricted run
as the series gate), and it is always printed together with the `skipped=…` line naming what was not
run.

Usage:
    python3 engineering/tools/wave_scan.py
    python3 engineering/tools/wave_scan.py --json
    python3 engineering/tools/wave_scan.py --only parse,attribution
    python3 engineering/tools/wave_scan.py --only meters --meter wave-d-stage   # partial, honest
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DEFAULT_BASE = '295690b'
DEFAULT_SWIFTC = '/opt/swift/usr/bin/swiftc'
BUDGET_SECONDS = 600          # SIG-001: one command, ten minutes
PARSER_TIMEOUT = 240
LOADER_MAPS = 125             # review-code R6: the loader contour's recorded corpus size

# The merged FORBID-001 pattern set (wave B's ``no_magic_offsets``, wave C's parse gate).
MAGIC_PATTERNS = (  # (pattern, meaning, exempt inside the single-source constants file)
    # review-code R5: `[-+] ?\b16\b` alone is bypassable by syntax (`acc += 16`,
    # `100 +  16`, `100 + (16)`). Measured over every one of the 4 219 added lines of
    # 295690b..worktree the widened form adds ZERO hits, so it is a strict tightening of
    # the merged predicate, not a policy change. `0x10` / `1_6` spellings stay disclosed
    # residuals (catching arbitrary literal encodings means evaluating constants).
    (r'[-+]=? ?\(?\s*\b16\b', '±16 смещение', True),
    (r'\b528\b|\b544\b|\b560\b', 'закреплённая граница вместо вывода из констант', True),
    (r'L\d{2}S\d{2}', 'per-map имя', False),
)
# The numeric predicates are meaningless in the file that *defines* the boundaries. Everything else
# - including per-map names - is policed everywhere. Widening this set would be a policy change.
CONSTANT_ALLOW = ('Exolon/GameCore/GameConstants.swift',)

# What this tool does NOT police. Printed in every run and carried in --json, so a green line can
# never be read as "everything is covered" (review-code R2/R4/R5, review-test A5/A6): a scanner that
# over-states its own coverage is the same failure class as the wave that stopped scanning a file.
NOT_POLICED = (
    'a `//` inside a string literal ends comment-stripping, so a violation placed after '
    '"https://..." on the same physical line is invisible to every predicate in this series '
    '(inherited from wave B deliberately: changing it re-opens what A-D certified)',
    'the number 16 written as `0x10`, `1_6`, or via a named constant/another expression form '
    'the textual predicate does not match',
    'Exolon/Resources data (125 TMX maps, PNGs): neither parse nor attribution reads it - only '
    'wave B/C/D meters do, and wave B is itself one of the six meters this suite runs',
    '`swiftc -frontend -parse` is syntax-only: no type checking, no SpriteKit-bound semantics, '
    'no macOS runtime behaviour (class-2 stays external - this host has no Apple toolchain)',
    'the meter roster is the six names in METERS; a new merged meter must be registered here and '
    'in evidence/wave_e1_check.py, and only a coordinated edit to both keeps the suite green',
)

# (name, script inside the repo, extra argv, expected passing verdicts, verdict tag)
METERS = (('wave-a-gameplay-log',
           'engineering/changes/20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c'
           '/evidence/gameplay_log_check.py', (), 28, 'A'),
          ('wave-b-mapdata',
           'engineering/changes/20260924-fix-wave-b-map-data-and-physics-audit-findings-i-35bac2'
           '/evidence/wave_b_check.py', (), 9, 'B'),
          ('wave-c-content',
           'engineering/changes/20260924-close-wave-c-content-and-factory-audit-findings-f2d90a'
           '/evidence/wave_c_check.py', (), 9, 'C'),
          ('wave-d-handout',
           'engineering/changes/20260924-complete-wave-d-specification-and-release-audit-8341b7'
           '/evidence/macos_handout_check.py', ('--phase', 'D1'), 11, 'D1'),
          ('wave-d-stage',
           'engineering/changes/20260924-complete-wave-d-specification-and-release-audit-8341b7'
           '/evidence/stage_boundary_check.py', (), 10, 'DSTAGE'),
          ('loader-harness-125maps',
           'engineering/changes/20260919-exolon-initial-code-audit-7db1f3'
           '/evidence/harness/run.sh', (), 1, 'LOADER'))
METER_TIMEOUT = {'A': 400, 'B': 180, 'C': 300, 'D1': 240, 'DSTAGE': 180, 'LOADER': 400}


class ToolAbsent(Exception):
    """A required executable is missing: reported as a red contour, never as a skip."""


def git(root: Path, *args, timeout=180) -> str:
    proc = subprocess.run(['git', '-c', 'core.quotepath=false', *[str(a) for a in args]],
                          cwd=str(root), capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f'git {" ".join(str(a) for a in args)}: {proc.stderr.strip()[:300]}')
    return proc.stdout


def strip_comments(text: str) -> str:
    """The merged predicate's own comment stripper (wave B) - kept byte-compatible on purpose.

    Known limit, inherited: it cuts at a ``//`` inside a string literal, so a violation placed after
    ``"https://..."`` on the same physical line is invisible here too. Changing it would change what
    the earlier waves certified; it is listed as a residual in ``tasks.md`` instead.
    """
    text = re.sub(r'///?.*', '', text)
    return re.sub(r'/\*.*?\*/', '', text, flags=re.S)


def swift_union(root: Path, base: str) -> list:
    """Every ``*.swift`` path touched since the root base, plus the working tree, plus untracked."""
    found = set()
    for args in (('diff', '--name-only', f'{base}..HEAD', '--', '*.swift'),
                 ('diff', '--name-only', 'HEAD', '--', '*.swift'),
                 ('ls-files', '--others', '--exclude-standard', '*.swift')):
        found.update(line for line in git(root, *args).splitlines() if line.strip())
    return sorted(found)


def deleted_swift(root: Path, base: str) -> list:
    """Union-listed Swift files a wave *removed*: there is nothing to parse, and the removal is
    not a syntax failure. Naming them keeps the set honest instead of silently shrinking it."""
    gone = set()
    for args in (('diff', '--name-only', '--diff-filter=D', f'{base}..HEAD', '--', '*.swift'),
                 ('diff', '--name-only', '--diff-filter=D', 'HEAD', '--', '*.swift')):
        gone.update(line for line in git(root, *args).splitlines() if line.strip())
    return sorted(rel for rel in gone if not (root / rel).is_file())


def parse_one(swiftc: str, root: Path, rel_path: str):
    path = root / rel_path
    if not path.is_file():
        return {'path': rel_path, 'verdict': 'file missing'}
    try:
        proc = subprocess.run([swiftc, '-frontend', '-parse', str(path)],
                              capture_output=True, text=True, timeout=PARSER_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {'path': rel_path, 'verdict': f'parse timeout after {PARSER_TIMEOUT}s'}
    if proc.returncode == 0:
        return {'path': rel_path, 'verdict': 'ok'}
    first = (proc.stderr.strip().splitlines() or ['parse failed'])[-1]
    return {'path': rel_path, 'verdict': first[:200]}


def parse_gate(root: Path, base: str, swiftc: str) -> dict:
    """Contour (a): parse the union, and prove the gate can fail."""
    files = swift_union(root, base)
    deleted = deleted_swift(root, base)
    to_parse = [rel for rel in files if rel not in set(deleted)]
    section = {'tool': swiftc, 'total': len(files), 'files': [], 'failures': 0,
               'deleted': deleted,
               'product_files': sum(1 for f in files if f.startswith('Exolon/')),
               'evidence_files': sum(1 for f in files if not f.startswith('Exolon/')),
               'skipped': 0, 'selftest': {}, 'problems': []}
    if not os.path.isfile(swiftc) or not os.access(swiftc, os.X_OK):
        section['problems'].append(f'swiftc is absent at {swiftc}: the parse contour cannot run')
        section['failures'] = len(to_parse)
        section['skipped'] = len(to_parse)
        section['files'] = ([{'path': rel, 'verdict': 'deleted since the base (nothing to parse)'}
                             for rel in deleted]
                            + [{'path': f, 'verdict': 'not run (swiftc absent)'} for f in to_parse])
        return section
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, (os.cpu_count() or 2))) as pool:
        verdicts = list(pool.map(lambda rel: parse_one(swiftc, root, rel), to_parse))
    section['files'] = sorted(verdicts, key=lambda entry: entry['path'])
    for entry in verdicts:
        if entry['verdict'] != 'ok':
            section['failures'] += 1
            section['problems'].append(f'{entry["path"]}: {entry["verdict"]}')
    section['selftest'] = parse_selftest(swiftc)
    if not (section['selftest'].get('broken_reddens') and section['selftest'].get('good_parses')):
        section['problems'].append(f'parse gate is not falsifiable: {section["selftest"]}')
        section['failures'] += 1
    return section


def parse_selftest(swiftc: str) -> dict:
    """Feed the compiler a known-broken and a known-good file; they must disagree."""
    work = Path(tempfile.mkdtemp(prefix='wave-e1-scan-'))
    try:
        broken = work / 'E1Broken.swift'
        broken.write_text('struct E1Broken {\n    let x: Int\n', encoding='utf-8')  # unclosed brace
        good = work / 'E1Fine.swift'
        good.write_text('struct E1Fine {\n    let x: Int\n}\n', encoding='utf-8')
        bad = parse_one(swiftc, work, 'E1Broken.swift')['verdict']
        fine = parse_one(swiftc, work, 'E1Fine.swift')['verdict']
        return {'broken_reddens': bad != 'ok', 'good_parses': fine == 'ok',
                'broken_verdict': bad[:120]}
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------------------------------------------------------------------------
# contour (b): root-anchored attribution, bucketed by merge history
# ---------------------------------------------------------------------------

def merge_ranges(root: Path, base: str) -> list:
    """Split ``base..HEAD`` into one range per merged wave, from the first-parent merge history.

    A release series lands each wave as ``Merge pull request #N from <owner>/<branch>``, so the
    boundaries are read from the repository rather than hard-coded: if the next wave merges, the
    next bucket appears here automatically and its lines stop being somebody's blind spot.
    """
    merges = [sha for sha in git(root, 'rev-list', '--first-parent', '--merges',
                                f'{base}..HEAD').split() if sha.strip()][::-1]
    ranges, previous = [], base
    for sha in merges:
        subject = git(root, 'show', '-s', '--format=%s', sha).strip()
        ranges.append({'name': bucket_name(subject, sha), 'start': previous,
                       'end': sha, 'merge_subject': subject[:120]})
        previous = sha
    ranges.append({'name': f'{branch_name(root)} (committed on this branch)', 'start': previous,
                   'end': 'HEAD', 'merge_subject': 'branch commits after the last merge'})
    ranges.append({'name': 'uncommitted (working tree + untracked)', 'start': 'HEAD', 'end': None,
                   'merge_subject': 'not yet committed'})
    return ranges


def bucket_name(subject: str, sha: str) -> str:
    match = re.search(r'wave[ -]([a-z0-9]+)', subject, re.I)
    if match:
        return f'wave-{match.group(1).lower()}'
    return f'merge-{sha[:7]}'


def branch_name(root: Path) -> str:
    try:
        return git(root, 'rev-parse', '--abbrev-ref', 'HEAD').strip() or 'HEAD'
    except RuntimeError:
        return 'HEAD'


def untracked_product_swift(root: Path) -> list:
    """New product sources that exist only in the working tree.

    review-code R2: ``git diff`` never reports untracked files, so the attribution contour was blind
    to a brand-new ``Exolon/**/X.swift`` while its own bucket name promised "working tree + untracked"
    (the parse contour already covered them). Every line of such a file is an added line.
    """
    listed = git(root, 'ls-files', '--others', '--exclude-standard', '--', 'Exolon', '*.swift')
    return sorted(line for line in listed.splitlines() if line.strip().endswith('.swift'))


def ignored_product_swift(root: Path) -> list:
    """``*.swift`` present on disk under ``Exolon/`` that git shows nobody (review-code R4).

    ``.gitignore`` carries a bare ``coverage/`` rule that matches at any depth, so an ignored file
    at ``Exolon/GameCore/coverage/Bad.swift`` is invisible to ``git diff`` **and** to
    ``ls-files --others --exclude-standard``. Rather than quietly narrow the claim, the contour
    reddens and names the file: nothing under the product tree may be outside the scan.
    """
    on_disk = {str(path.relative_to(root)) for path in (root / 'Exolon').rglob('*.swift')}
    known = set(git(root, 'ls-files', '--', 'Exolon', '*.swift').split())
    known.update(untracked_product_swift(root))
    return sorted(on_disk - known)


def added_code_lines(root: Path, start: str, end):
    """``[(path, added line)]`` for ``*.swift`` under ``Exolon/`` from ``start`` to ``end``/worktree.

    Against the worktree the set is a union: ``git diff`` output **plus** every line of every
    untracked product ``*.swift`` (a diff cannot see those).
    """
    args = ['diff', '-U0', start] + ([end] if end else []) + ['--', 'Exolon']
    out, path, result = git(root, *args, timeout=300), None, []
    for line in out.splitlines():
        if line.startswith('+++ b/'):
            path = line[6:]
        elif line.startswith('+') and not line.startswith('+++'):
            if path and path.endswith('.swift'):
                result.append((path, line[1:]))
    if end is None:
        for rel in untracked_product_swift(root):
            try:
                text = (root / rel).read_text(encoding='utf-8', errors='replace')
            except OSError:
                result.append((rel, 'let unreadable: Int = 544'))
                continue
            result.extend((rel, line) for line in text.splitlines())
    return result


def scan_violations(added, strict=False) -> list:
    """Apply the merged FORBID-001 predicates to added lines, honouring the constants allowance.

    ``strict=True`` disables the allowance; wave E1's checker reports it as a pinned control
    (review-code R11) so the exemption cannot silently start carrying the green.
    """
    hits = []
    for path, raw in added:
        code = strip_comments(raw)
        if not code.strip():
            continue
        for pattern, why, exempt_in_constants in MAGIC_PATTERNS:
            if path in CONSTANT_ALLOW and exempt_in_constants and not strict:
                continue   # the boundary is *defined* here; per-map names are policed anyway
            if re.search(pattern, code):
                hits.append({'path': path, 'pattern': why, 'line': code.strip()[:160]})
    return hits


def attribution_gate(root: Path, base: str) -> dict:
    root_added = added_code_lines(root, base, None)
    files = sorted({path for path, _ in root_added})
    code_total = sum(1 for _, line in root_added if strip_comments(line).strip())
    ranges = merge_ranges(root, base)
    buckets, keys = [], {}
    for entry in ranges:
        added = added_code_lines(root, entry['start'], entry['end'])
        scanned = [item for item in added if strip_comments(item[1]).strip()]
        buckets.append({'name': entry['name'], 'range': f"{entry['start'][:7]}.."
                        + (entry['end'][:7] if entry['end'] else 'worktree'),
                        'merge_subject': entry['merge_subject'],
                        'files': len({p for p, _ in scanned}), 'code_lines': len(scanned),
                        'violations': 0})
        for item in scanned:
            keys.setdefault(item, entry['name'])   # earliest wave that added the line wins
    details = []
    for hit in scan_violations(root_added):
        hit['bucket'] = keys.get((hit['path'], raw_line(root_added, hit)), 'unattributed')
        details.append(hit)
    for bucket in buckets:
        bucket['violations'] = sum(1 for hit in details if hit['bucket'] == bucket['name'])
    scanned_zero = [b['name'] for b in buckets if b['code_lines'] == 0]
    untracked = untracked_product_swift(root)
    ignored = ignored_product_swift(root)
    section = {'base': base, 'code_lines': code_total, 'files': len(files), 'file_list': files,
               'buckets': buckets, 'violations': len(details), 'violation_details': details,
               'constant_allow_list': list(CONSTANT_ALLOW), 'problems': [],
               'empty_buckets': scanned_zero, 'untracked_files': untracked,
               'ignored_swift': ignored, 'not_policed': list(NOT_POLICED),
               'strict_violations_without_allow_list': len(scan_violations(root_added, strict=True))}
    for hit in details:
        section['problems'].append(f"FORBID-001 added {hit['path']} [{hit['bucket']}]: "
                                   f"{hit['pattern']}: {hit['line'][:110]}")
    for rel in ignored:
        section['problems'].append(f'FORBID-001 coverage: {rel} exists under Exolon/ but git lists '
                                   'it neither as tracked nor as untracked (an ignore rule hides it '
                                   'from every contour) - name it or move it out of the product tree')
    if code_total < 150 or len(files) < 7:
        section['problems'].append(f'the root-anchored scan is strangely empty: '
                                   f'files={len(files)} code lines={code_total}')
    return section


def raw_line(added, hit):
    for path, raw in added:
        if path == hit['path'] and strip_comments(raw).strip()[:160] == hit['line']:
            return raw
    return None


# ---------------------------------------------------------------------------
# contour (c): the merged meters, as a suite with recorded sub-results
# ---------------------------------------------------------------------------

def verdicts(tag: str, stdout: str):
    """Count one meter's verdicts from its own output. Red if the line cannot be found."""
    lines = stdout.splitlines()
    if tag == 'A':
        found = [re.search(r'RESULT: (?:PASS|FAIL) \((\d+)/(\d+) checks passed\)', line)
                 for line in lines]
        found = [m for m in found if m]
        if not found:
            raise ValueError('no "RESULT: PASS (n/n checks passed)" line')
        m = found[-1]
        passed, total = int(m.group(1)), int(m.group(2))
        return passed, total - passed, m.group(0)
    if tag == 'B':
        passed = sum(1 for line in lines if re.match(r'^(PASS|OK) ', line))
        failed = sum(1 for line in lines if re.match(r'^(FAIL|MISMATCH) ', line))
        # review-code R7: the verdict_line a transcript quotes must be the meter's OWN line. The
        # first implementation synthesised ALL_WAVE_B_CHECKS_MATCH_SPEC whenever no FAIL line was
        # seen - which is exactly what a fail-closed exit 4 (missing refs/remotes/origin/main)
        # prints nothing at all, so the machine-readable line claimed a success marker the meter
        # never emitted.
        marker = [line for line in lines if line.startswith('RESULT:')]
        if not marker:
            raise ValueError('no "RESULT:" marker (a fail-closed wave_b_check exit prints none)')
        return passed, failed, marker[-1][:140]
    if tag == 'C':
        found = [re.search(r'RESULT: (\S+) \| probes=(\d+) failed=(\d+)', line) for line in lines]
        found = [m for m in found if m]
        if not found:
            raise ValueError('no "RESULT: ... | probes=n failed=n" line')
        m = found[-1]
        return int(m.group(2)) - int(m.group(3)), int(m.group(3)), m.group(0)
    if tag in ('D1', 'DSTAGE'):
        found = [re.search(r'SUMMARY checks=(\d+) failed=(\d+)', line) for line in lines]
        found = [m for m in found if m]
        if not found:
            raise ValueError('no "SUMMARY checks=n failed=n" line')
        m = found[-1]
        return int(m.group(1)) - int(m.group(2)), int(m.group(2)), m.group(0)
    if tag == 'LOADER':
        found = [re.search(r'REAL MAPS ok=(\d+)/(\d+) failures=(\d+)', line) for line in lines]
        found = [m for m in found if m]
        if not found:
            raise ValueError('no "REAL MAPS ok=n/n failures=n" line')
        m = found[-1]
        # `ok == total` alone would certify a shrunken corpus (measured: 100/100 with ten maps
        # deleted). AC-003 records 125/125, so 125 is asserted, not echoed.
        good = (m.group(1) == m.group(2) == str(LOADER_MAPS) and m.group(3) == '0')
        return (1 if good else 0), (0 if good else 1), m.group(0)
    raise ValueError(f'unknown verdict tag {tag}')


def meters_gate(root: Path, selected=None) -> dict:
    names = [name for name, _, _, _, _ in METERS]
    chosen = [name for name in names if not selected or name in selected]
    section = {'entries': [], 'problems': [], 'green': 0, 'selected': chosen,
               'skipped': [name for name in names if name not in chosen]}
    for name, script, extra, expected, tag in METERS:
        if name not in chosen:
            continue
        entry = {'name': name, 'script': script, 'expected': expected, 'argv': None, 'rc': None,
                 'passed': 0, 'failed': expected, 'green': False, 'verdict_line': '',
                 'seconds': 0.0, 'stderr_tail': ''}
        path = root / script
        if not path.is_file():
            section['problems'].append(f'{name}: meter script is absent ({script})')
            section['entries'].append(entry)
            continue
        argv = ([sys.executable, str(path)] if path.suffix == '.py'
                else ['bash', str(path)]) + list(extra)
        entry['argv'] = [str(a) for a in argv]
        started = time.time()
        try:
            proc = subprocess.run([str(a) for a in argv], cwd=str(root), capture_output=True,
                                  text=True, timeout=METER_TIMEOUT[tag])
            rc, out, err = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            rc, out, err = 124, '', f'timeout after {METER_TIMEOUT[tag]}s'
        except OSError as exc:
            rc, out, err = 127, '', f'{type(exc).__name__}: {exc}'
        entry['seconds'] = round(time.time() - started, 1)
        entry['rc'] = rc
        entry['stderr_tail'] = err.strip()[-200:]
        try:
            passed, failed, line = verdicts(tag, out)
        except ValueError as exc:
            section['problems'].append(f'{name}: verdict line unparsable ({exc}); '
                                        f'rc={rc} tail={out.strip()[-160:]!r}')
            entry['verdict_line'] = str(exc)
            section['entries'].append(entry)
            continue
        entry['passed'], entry['failed'], entry['verdict_line'] = passed, failed, line
        entry['green'] = rc == 0 and failed == 0 and passed == expected
        if not entry['green']:
            section['problems'].append(f'{name}: rc={rc} passed={passed}/{expected} failed={failed} '
                                        f'({line})')
        else:
            section['green'] += 1
        section['entries'].append(entry)
    return section


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

def summarize(doc: dict, out=sys.stdout) -> None:
    parse, att = doc['parse'], doc['attribution']
    if 'parse' in doc['sections_run']:
        print(f'SUMMARY parse       files={parse["total"]} (product={parse["product_files"]} '
              f'evidence={parse["evidence_files"]} deleted={len(parse["deleted"])}) '
              f'failures={parse["failures"]} '
              f'selftest={parse["selftest"].get("broken_reddens") and parse["selftest"].get("good_parses")}',
              file=out)
    if 'attribution' in doc['sections_run']:
        print(f'SUMMARY attribution   base={att["base"]} code_lines={att["code_lines"]} '
              f'files={att["files"]} violations={att["violations"]} '
              f'allow_list={",".join(att["constant_allow_list"])}', file=out)
        for bucket in att['buckets']:
            print(f'  bucket {bucket["name"]:<44} range={bucket["range"]:<18} '
                  f'files={bucket["files"]:<3} code_lines={bucket["code_lines"]:<5} '
                  f'violations={bucket["violations"]}', file=out)
    for entry in doc['meters']['entries']:
        print(f'SUMMARY meter       {entry["name"]:<22} expected={entry["expected"]:<3} '
              f'passed={entry["passed"]:<3} failed={entry["failed"]:<3} rc={entry["rc"]} '
              f'green={"yes" if entry["green"] else "NO"} {entry["seconds"]}s '
              f'{entry["verdict_line"][:60]}', file=out)
    if doc['meters']['skipped'] or doc['partial']:
        skipped = doc['meters']['skipped'] or [name for name, _, _, _, _ in METERS]
        print(f'SUMMARY meter       skipped={",".join(skipped)} (partial run, not the series '
              f'contour: sections={",".join(doc["sections_run"])})', file=out)
    disclosed = doc['attribution'].get('not_policed') or []
    if disclosed:
        print(f'SUMMARY not-policed {len(disclosed)} disclosed limits '
              f'(--json attribution.not_policed); first: {disclosed[0][:76]}...', file=out)
    totals = doc['totals']
    print(f'SUMMARY TOTAL       meters={totals["meters_green"]}/{totals["meters_run"]} green '
          f'parse_failures={totals["parse_failures"]} attribution_violations='
          f'{totals["attribution_violations"]} elapsed={doc["seconds"]}s '
          f'budget={doc["budget_seconds"]}s tree_writes={totals["tree_writes"] or "none"}',
          file=out)
    for problem in doc['problems'][:20]:
        print(f'  ! {problem}', file=out)
    print(f'RESULT: {doc["result"]}', file=out)


def sections_run_meters(sections: list) -> bool:
    return 'meters' in sections


def build_doc(root: Path, base: str, swiftc: str, sections: list, selected, budget: int) -> dict:
    started = time.time()
    dirty_before = set(git(root, 'status', '--porcelain').splitlines())
    parse = parse_gate(root, base, swiftc) if 'parse' in sections else {
        'total': 0, 'files': [], 'failures': 0, 'product_files': 0, 'evidence_files': 0,
        'skipped': 0, 'selftest': {}, 'problems': [], 'tool': swiftc}
    att = attribution_gate(root, base) if 'attribution' in sections else {
        'base': base, 'code_lines': 0, 'files': 0, 'file_list': [], 'buckets': [],
        'violations': 0, 'violation_details': [], 'constant_allow_list': list(CONSTANT_ALLOW),
        'problems': [], 'empty_buckets': []}
    meters = meters_gate(root, selected) if 'meters' in sections else {
        'entries': [], 'problems': [], 'green': 0, 'selected': [], 'skipped': [
            name for name, _, _, _, _ in METERS]}
    dirty_after = set(git(root, 'status', '--porcelain').splitlines())
    wrote = sorted({line[3:].split(' -> ')[-1] for line in dirty_after ^ dirty_before})
    elapsed = round(time.time() - started, 1)
    problems = list(parse['problems']) + list(att['problems']) + list(meters['problems'])
    if elapsed > budget:
        problems.append(f'over the {budget}s budget: {elapsed}s (SIG-001)')
    totals = {'meters_run': len(meters['entries']), 'meters_green': meters['green'],
              'parse_files': parse['total'], 'parse_failures': parse['failures'],
              'attribution_violations': att['violations'], 'tree_writes': wrote}
    full = (not selected and set(sections) >= {'parse', 'attribution', 'meters'}
            and totals['meters_run'] == len(METERS))
    clean = (not problems and totals['meters_green'] == totals['meters_run']
             and totals['meters_run'] > 0) or (not problems and not sections_run_meters(sections))
    result = 'WAVE_SCAN_GREEN' if (clean and full) else (
        'WAVE_SCAN_PARTIAL' if clean else 'WAVE_SCAN_RED')
    return {'tool': 'wave_scan', 'root': str(root), 'base': base, 'head': head_sha(root),
            'swiftc': swiftc, 'sections_run': sections, 'partial': bool(selected) or not full,
            'budget_seconds': budget, 'seconds': elapsed, 'parse': parse, 'attribution': att,
            'meters': meters, 'totals': totals, 'problems': problems, 'result': result}


def head_sha(root: Path) -> str:
    try:
        return git(root, 'rev-parse', 'HEAD').strip()
    except RuntimeError:
        return 'NO_HEAD'


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='wave_scan.py', description=__doc__.splitlines()[0])
    parser.add_argument('--root', default=None, help='repository root (default: this file\'s repo)')
    parser.add_argument('--base', default=DEFAULT_BASE,
                        help=f'root anchor for every contour (default {DEFAULT_BASE})')
    parser.add_argument('--only', default='parse,attribution,meters',
                        help='comma list of contours: parse,attribution,meters')
    parser.add_argument('--meter', action='append', default=[],
                        help='restrict the meter suite to this name (repeatable); the run is '
                             'reported as partial and never counts as the full suite')
    parser.add_argument('--swiftc', default=os.environ.get('SWIFTC', DEFAULT_SWIFTC))
    parser.add_argument('--budget', type=int, default=BUDGET_SECONDS)
    parser.add_argument('--json', action='store_true', help='machine-readable summary only')
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
    if not (root / '.git').exists() and not (root / 'Exolon').is_dir():
        print(f'root {root} is not this repository', file=sys.stderr)
        return 2
    sections = [item.strip() for item in args.only.split(',') if item.strip()]
    unknown = set(sections) - {'parse', 'attribution', 'meters'}
    names = {name for name, _, _, _, _ in METERS}
    if unknown or not sections:
        print(f'unknown contour(s): {sorted(unknown)}', file=sys.stderr)
        return 2
    if set(args.meter) - names:
        print(f'unknown meter(s): {sorted(set(args.meter) - names)}', file=sys.stderr)
        return 2
    try:
        git(root, 'rev-parse', '--verify', f'{args.base}^{{commit}}')
    except RuntimeError as exc:
        print(f'REFUSED: root anchor {args.base} is not a commit here ({exc})', file=sys.stderr)
        return 2
    doc = build_doc(root, args.base, args.swiftc, sections, args.meter, args.budget)
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True, default=str))
    else:
        summarize(doc)
    if doc['result'] == 'WAVE_SCAN_GREEN':
        return 0
    return 3 if doc['result'] == 'WAVE_SCAN_PARTIAL' else 1


if __name__ == '__main__':
    sys.exit(main())
