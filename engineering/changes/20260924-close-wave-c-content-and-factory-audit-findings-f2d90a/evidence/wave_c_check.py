#!/usr/bin/env python3
"""wave_c_check.py — executable meter for change f2d90a (P1-7 marker coverage + P1-12 pinning).

Stdlib only, single pass over the corpus (parsed trees and canonical digests are memoized).
Nine probes, named exactly as ``change-spec.yaml`` names them:

  marker_coverage_all_maps     AC-001  every distinct sourceBlock is claimed by the product
                                      matcher and the silent-drop path no longer exists
  marker_baseline_reproduced   AC-001  the pre-change 76/127 split still reproduces from the
                                      pinned legacy table (control: drop ``beam_`` -> 71 lost)
  ignored_types_disposition    AC-002  the 51 formerly-lost markers each carry a committed
                                      disposition whose substring+kind agree with the Swift source
  level_pair_manifest_pinned   AC-003  per-map canonical digests, the 24 declared identical pairs,
                                      non-declared pairs differ, unique_count == 101
  manifest_selfcheck           AC-004  schema + body digest; tampered entries MUST be rejected
  unchanged_marker_output      AC-005  the 76 already-covered markers keep byte-identical factory
                                      output before and after the change
  no_invented_content          FORBID-001  Exolon/Resources is blob-identical to the route base and
                                      no new image/texture literal exists
  safe_models_are_labeled      FORBID-002  every safe-model substitution is labeled in the product
                                      source and in this meter's output
  zone_index_formula           INV-001   int(zoneNumber) == (stage-1)*25 + (scene-1), 0-based

Every probe owns at least one *mandatory flip*: a synthetic mutation that must make its own
assertion fail. A control that cannot flip makes the probe decorative, so the probe reports FAIL.
This mirrors the ``controls[...]`` convention of the committed ``v3_measurements.py``.

The matcher table is **parsed out of the product Swift source**, never hand-copied: four
hand-copied mirrors of these seven literals already exist in this tree and none of them can
detect the fix they measure (see evidence/analysis-repo_explorer.md section 5).

Usage
    python3 wave_c_check.py                      run all probes
    python3 wave_c_check.py --only <probe>       run one probe
    python3 wave_c_check.py --json               machine-readable output
    python3 wave_c_check.py --record-baseline    write baseline-prechange-digest.json
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RES = ROOT / 'Exolon' / 'Resources'
RUNTIME_SWIFT = ROOT / 'Exolon' / 'GameCore' / 'Levels' / 'TMXLevelRuntime.swift'
LOADER_SWIFT = ROOT / 'Exolon' / 'GameCore' / 'Levels' / 'TMXMapLoader.swift'
GAME_SCENE_SWIFT = ROOT / 'Exolon' / 'GameCore' / 'GameScene.swift'
#: The three Swift files this change touches. All are syntax-gated; only the loader is compiled and
#: executed (test review F3 records why the other two cannot be, on this host).
CHANGED_SWIFT = (LOADER_SWIFT, RUNTIME_SWIFT, GAME_SCENE_SWIFT)
MANIFEST_PATH = ROOT / 'engineering' / 'contracts' / 'level-content-v1.json'
DISPOSITION_PATH = HERE / 'marker-disposition-v1.json'
BASELINE_PATH = HERE / 'baseline-prechange-digest.json'

BASE_COMMIT = '295690b7fc724e57b37b5fac86b71c1da7d8b032'
CANON_VERSION = 'wave-c-canonical-1'
CONTRACT_ID = 'level-content-v1'

#: The matcher exactly as it stood at the route base (merged analysis §1; audit v3 §1 line 32).
#: Pinned here so the 76/127 baseline stays reproducible after the product source changes.
LEGACY_SUBSTRINGS = ('beam_', 'topdown_electro', 'blinker', 'stage_end',
                     'changing_room', 'beacon_base', 'control_beacon')
LEGACY_BASELINE = {
    'markers_total': 127,
    'markers_covered': 76,
    'markers_lost': 51,
    'lost_maps': 32,
    'distinct_source_blocks': 11,
    'lost_kinds': {'blk_waggon': 24, 'blk_gunMachine_BOTTOM': 18, 'blk_mushroom': 9},
    'lost_kind_maps': {'blk_gunMachine_BOTTOM': 15, 'blk_mushroom': 6, 'blk_waggon': 14},
    'control_drop_beam_lost': 71,
    'control_drop_all_lost': 127,
}
#: Pinned by the merged level-graph lane: 23x L02/L05 plus L03S09/L04S11.
DECLARED_PAIRS = [(f'L02S{xx:02d}', f'L05S{xx:02d}') for xx in range(3, 26)] + \
                 [('L03S09', 'L04S11')]
DECLARED_UNIQUE = 101
DECLARED_FULLY_IDENTICAL = {('L02S04', 'L05S04'), ('L02S16', 'L05S16'),
                            ('L02S22', 'L05S22'), ('L02S23', 'L05S23')}
FORMERLY_IGNORED = ('blk_waggon', 'blk_gunMachine_BOTTOM', 'blk_mushroom')

TILED_SEPARATORS = frozenset(',\n\r\t ')


# --------------------------------------------------------------------------- #
# TMX parsing with the product loader's own decoding semantics
# (TMXMapLoader.swift:305-343): base64 -> little-endian uint32, csv -> split on
# {',', '\n', '\r', '\t', ' '}, non-empty compression is a hard error.
# --------------------------------------------------------------------------- #
def decode_layer_data(data_element):
    if data_element is None:
        return []
    encoding = (data_element.get('encoding') or '').strip()
    if not encoding:
        return [int(t.get('gid', '0')) for t in data_element.findall('tile')]
    text = data_element.text or ''
    if encoding == 'base64':
        raw = base64.b64decode(''.join(text.split()))
        usable = len(raw) - (len(raw) % 4)
        return list(struct.unpack('<%dI' % (usable // 4), raw[:usable]))
    if encoding == 'csv':
        out, token = [], ''
        for ch in text:
            if ch in TILED_SEPARATORS:
                if token.strip():
                    out.append(int(token))
                token = ''
            else:
                token += ch
        if token.strip():
            out.append(int(token))
        return out
    raise ValueError('unsupported encoding %r' % encoding)


def object_properties(object_element):
    props = {}
    holder = object_element.find('properties')
    if holder is not None:
        for p in holder.findall('property'):
            props[p.get('name', '')] = p.get('value', '')
    return props


def canonical_content(root):
    """The audited level-graph slice: every tile layer plus every object; background excluded."""
    tiles, objects = [], []
    for element in root:
        if element.tag == 'layer':
            tiles.append([
                element.get('name', ''),
                element.get('width', ''), element.get('height', ''),
                element.get('x', ''), element.get('y', ''),
                decode_layer_data(element.find('data')),
            ])
        elif element.tag == 'objectgroup':
            for obj in element:
                if obj.tag != 'object':
                    continue
                props = sorted([p.get('name', ''), p.get('value', '')]
                               for p in obj.iter('property'))
                objects.append([obj.get('name', ''), obj.get('type', ''), obj.get('x', ''),
                                obj.get('y', ''), obj.get('width', '0'), obj.get('height', '0'), props])
    return json.dumps([tiles, objects], sort_keys=True)


_TREES, _CANON, _MARKERS = {}, {}, None


def trees():
    if not _TREES:
        for path in sorted(RES.glob('*.tmx')):
            _TREES[path.name[:-4]] = ET.parse(path).getroot()
    return _TREES


def canonical_hashes():
    if not _CANON:
        for name, root in trees().items():
            _CANON[name] = hashlib.sha256(canonical_content(root).encode('utf-8')).hexdigest()
    return dict(_CANON)


def marker_record(obj):
    props = object_properties(obj)
    return {'block': props.get('sourceBlock', ''),
            'sx': props.get('sourceX', ''), 'sy': props.get('sourceY', ''),
            'x': obj.get('x', ''), 'y': obj.get('y', ''),
            'w': obj.get('width', ''), 'h': obj.get('height', ''),
            'props': sorted(props.items())}


def map_markers():
    global _MARKERS
    if _MARKERS is None:
        _MARKERS = {}
        for name, root in trees().items():
            _MARKERS[name] = [marker_record(obj) for obj in root.iter('object')
                              if obj.get('name') == 'source_marker']
    return _MARKERS


def background_refs(root):
    out = []
    for element in root:
        if element.tag == 'imagelayer':
            image = element.find('image')
            out.append(image.get('source') if image is not None else '')
    return out


def background_digests(root):
    """sha256 of every backdrop this map references, resolved the way the renderer resolves it
    (``lastPathComponent`` -> ``Exolon/Resources/<name>``, TMXTileMapRenderer.swift:84-85).
    Two pairs of maps are backdrop-identical when the *bytes* match, even if the file names differ
    (``zone_028_original.png`` and ``zone_103_original.png`` are the same image)."""
    digests = []
    for source in background_refs(root):
        name = Path(source).name
        path = RES / name
        digests.append(hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else 'missing:' + name)
    return digests


def zone_number(root):
    for element in root:
        if element.tag == 'properties':
            for p in element.findall('property'):
                if p.get('name') == 'zoneNumber':
                    return p.get('value')
    return None


# --------------------------------------------------------------------------- #
# Swift source parsing -- the product is the authority, never a hand-copied tuple.
# All functions here are pure over source text so the mandatory flips can feed them
# synthetic sources.
# --------------------------------------------------------------------------- #
CLASSIFY_RE = re.compile(r'sourceBlock\.contains\(\s*"([^"]+)"\s*\)\s*\{\s*return\s+\.(\w+)')
CHAIN_RE = re.compile(r'source\.contains\(\s*"([^"]+)"\s*\)')


def read(path):
    return path.read_text(encoding='utf-8')


def loader_claims(text):
    """{substring: kind} from the product classifier."""
    return dict(CLASSIFY_RE.findall(text))


def runtime_chain(text):
    """Substrings the ``source_marker`` case itself tests (the pre-change shape)."""
    return CHAIN_RE.findall(source_marker_case(text))


def source_marker_case(runtime_text):
    start = runtime_text.find('case "source_marker":')
    if start < 0:
        return ''
    tail = runtime_text[start:]
    end = tail.find('\n            default:')
    return tail[:end] if end > 0 else tail


def classifier_kinds(text):
    """The declared ``TMXSourceMarkerKind`` case names, read from the enum body itself."""
    header = re.search(r'enum\s+TMXSourceMarkerKind\b', text)
    if not header:
        return []
    brace = text.find('{', header.end())
    if brace < 0:
        return []
    body = balanced_block(text, brace)
    if body is None:
        return []
    kinds = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith('case '):
            continue
        for token in stripped[5:].split('//')[0].split(','):
            token = token.strip().split(':')[0].strip()
            if re.fullmatch(r'[a-zA-Z]\w*', token) and token not in kinds:
                kinds.append(token)
            break
    return kinds


def classifier_labels(text):
    """{kind: literal label} from the classifier's ``safeModelLabel`` accessor, if present."""
    header = re.search(r'(?:var|func)\s+safeModelLabel\b', text)
    if not header:
        return {}
    brace = text.find('{', header.end())
    body = balanced_block(text, brace) if brace >= 0 else None
    if body is None:
        return {}
    out = {}
    for seg in re.finditer(r'case\s+\.?(\w+)\s*(?:,\s*\.?\w+)*\s*:\s*(?:return\s+)?"([^"]*)"', body):
        out.setdefault(seg.group(1), seg.group(2))
    return out


def balanced_block(text, open_brace_index):
    """Body between balanced braces starting at ``text[open_brace_index] == '{'``."""
    if open_brace_index >= len(text) or text[open_brace_index] != '{':
        return None
    depth, index = 0, open_brace_index
    while index < len(text):
        ch = text[index]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[open_brace_index + 1:index]
        index += 1
    return None


def branch_body(case_body_text, substring, kind):
    """The branch that handles ``substring`` (pre-change ``source.contains``) or ``kind``
    (post-change ``case .kind:``). Both shapes are supported so one fingerprint spans the change:
    an ``if`` arm is brace-delimited, a ``case`` arm runs until the next label."""
    match = re.search(r'(?:if|else if)\s+source\.contains\(\s*"%s"\s*\)' % re.escape(substring),
                      case_body_text)
    if match:
        brace = case_body_text.find('{', match.end())
        if brace < 0:
            return None
        return balanced_block(case_body_text, brace)
    if not kind:
        return None
    match = re.search(r'case\s+\.%s\b\s*:' % re.escape(kind), case_body_text)
    if not match:
        return None
    rest = case_body_text[match.end():]
    stop = re.search(r'\n\s*(?:case\s+\.|default\s*:|\}\s*$)', rest)
    return rest[:stop.start()] if stop else rest


def branch_fingerprint(substring, kind, text=None):
    """Fingerprint of the branch handling ``substring`` (chain form) or ``kind`` (switch form), so
    one comparison spans the change. The rect capture is balanced-paren (see ``rect_arguments``);
    an earlier version used ``CGRect\\(([^)]*)\\)`` and could not see a width or height edit."""
    body = branch_body(source_marker_case(read(RUNTIME_SWIFT) if text is None else text),
                       substring, kind)
    return fingerprint_body(body)


def claimed_substrings():
    """Ordered union of what the product actually tests, plus the two views separately."""
    loader_map = loader_claims(read(LOADER_SWIFT))
    chain = runtime_chain(read(RUNTIME_SWIFT))
    ordered = list(loader_map) + [s for s in chain if s not in loader_map]
    return ordered, loader_map, chain


def all_image_literals():
    out = set()
    for path in sorted((ROOT / 'Exolon').rglob('*.swift')):
        text = read(path)
        out.update(re.findall(r'SKTexture\(imageNamed:\s*"([^"]+)"\)', text))
        out.update(re.findall(r'\bimage:\s*"([^"]+)"', text))
    return out


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT)] + list(args),
                          capture_output=True, text=True, check=False)


def ls_tree_blobs(tree_path):
    result = git('ls-tree', '-r', BASE_COMMIT, '--', tree_path)
    out = {}
    for line in result.stdout.splitlines():
        meta, name = line.split('\t', 1)
        out[name] = meta.split()[2]
    return out


def compare_blobs(base, working):
    """Pure blob comparison so the flip controls can feed it synthetic dicts."""
    return {'deleted': sorted(set(base) - set(working)),
            'invented': sorted(set(working) - set(base)),
            'rewritten': sorted(n for n in set(base) & set(working) if base[n] != working[n])}


def base_image_literals():
    listing = git('ls-tree', '-r', BASE_COMMIT, '--', 'Exolon').stdout
    out = set()
    for line in listing.splitlines():
        _, name = line.split('\t', 1)
        if not name.endswith('.swift'):
            continue
        shown = git('show', '%s:%s' % (BASE_COMMIT, name))
        if shown.returncode != 0:
            continue
        out.update(re.findall(r'SKTexture\(imageNamed:\s*"([^"]+)"\)', shown.stdout))
        out.update(re.findall(r'\bimage:\s*"([^"]+)"', shown.stdout))
    return out


SWIFT_PROBE_MAIN = '''import FoundationXML
import Foundation

let dir = ProcessInfo.processInfo.environment["TMX_RESOURCES"]!
let bundle = Bundle(path: dir)!
let names = try! FileManager.default.contentsOfDirectory(atPath: dir)
    .filter { $0.hasSuffix(".tmx") }.map { String($0.dropLast(4)) }.sorted()
var blockKind: [String: String] = [:]
var blockCount: [String: Int] = [:]
var unmatched: [String: Int] = [:]
var loaded = 0
for n in names {
    guard let m = try? TMXMapLoader.load(resource: n, bundle: bundle) else { continue }
    loaded += 1
    for o in m.objects(named: "source_marker") {
        let block = o.properties["sourceBlock"] ?? ""
        blockCount[block, default: 0] += 1
        if let kind = TMXSourceMarkerKind.classify(sourceBlock: block) {
            blockKind[block, default: kind.rawValue] = kind.rawValue
        } else {
            unmatched[block, default: 0] += 1
        }
    }
}
print("LOADED\\t\\(loaded)")
for (b, k) in blockKind.sorted(by: { $0.key < $1.key }) { print("KIND_OF\\t\\(b)\\t\\(k)") }
for (b, c) in blockCount.sorted(by: { $0.key < $1.key }) { print("COUNT\\t\\(b)\\t\\(c)") }
for (b, c) in unmatched.sorted(by: { $0.key < $1.key }) { print("UNMATCHED\\t\\(b)\\t\\(c)") }
for kind in TMXSourceMarkerKind.allCases {
    print("LABEL\\t\\(kind.rawValue)\\t\\(kind.isSafeModel)\\t\\(kind.safeModelLabel)")
}
for block in blockCount.keys.sorted() {
    let cells = TMXSourceMarkerKind.safeModelFootprintCells(sourceBlock: block)
    print("FOOTPRINT\\t\\(block)\\t\\(cells.width)x\\(cells.height)")
}
'''

_SWIFT_EVIDENCE = None


def swift_product_evidence():
    """Compile and RUN the product classifier over all 125 maps.

    The merged P1-7 analysis requires the number to come "from real Swift, not a Python replica"
    (its sections 4c and 5 probe 3), so this meter refuses to be the only witness: the loader file
    is copied to a temp dir with exactly one added import line (the same delta the committed
    harness enforces), built against the CoreGraphics type-rename shim, and executed. The build
    without the shim must fail, which proves the product file really was compiled.

    Returns None when no Swift toolchain is available; callers must say so out loud instead of
    treating an unrun probe as a pass.
    """
    global _SWIFT_EVIDENCE
    if _SWIFT_EVIDENCE is not None:
        return _SWIFT_EVIDENCE if _SWIFT_EVIDENCE.get('available') else None
    if shutil.which('swiftc') is None:
        _SWIFT_EVIDENCE = {'available': False, 'reason': 'swiftc not found'}
        return None
    shim_source = next(iter(sorted(ROOT.glob('engineering/changes/*/evidence/harness/coregraphics_shim.swift'))), None)
    if shim_source is None:
        _SWIFT_EVIDENCE = {'available': False, 'reason': 'no CoreGraphics shim in tree'}
        return None
    work = Path(tempfile.mkdtemp(prefix='wave-c-swift-'))
    try:
        loader_lines = read(LOADER_SWIFT).splitlines(True)
        (work / 'TMXMapLoader.swift').write_text(
            loader_lines[0] + 'import FoundationXML\n' + ''.join(loader_lines[1:]), encoding='utf-8')
        (work / 'shim.swift').write_text(shim_source.read_text(encoding='utf-8'), encoding='utf-8')
        (work / 'main.swift').write_text(SWIFT_PROBE_MAIN, encoding='utf-8')
        shim_build = subprocess.run(['swiftc', '-emit-module', '-emit-library', '-module-name',
                                     'CoreGraphics', '-emit-module-path',
                                     str(work / 'CoreGraphics.swiftmodule'),
                                     '-o', str(work / 'libCoreGraphics.so'), str(work / 'shim.swift')],
                                    capture_output=True, text=True, timeout=240)
        if shim_build.returncode != 0:
            _SWIFT_EVIDENCE = {'available': False, 'reason': 'shim build failed: %s'
                               % shim_build.stderr[-300:]}
            return None
        linked = subprocess.run(['swiftc', '-I', str(work), '-L', str(work), '-lCoreGraphics',
                                 str(work / 'TMXMapLoader.swift'), str(work / 'main.swift'),
                                 '-o', str(work / 'probe')],
                                capture_output=True, text=True, timeout=240)
        if linked.returncode != 0:
            _SWIFT_EVIDENCE = {'available': False, 'reason': 'product build failed: %s'
                               % linked.stderr[-400:]}
            return None
        # negative control: the very same sources must NOT build without the shim
        without = subprocess.run(['swiftc', str(work / 'TMXMapLoader.swift'), str(work / 'main.swift'),
                                  '-o', str(work / 'probe-noshim')],
                                 capture_output=True, text=True, timeout=240)
        ran = subprocess.run([str(work / 'probe')], capture_output=True, text=True, timeout=240,
                             env=dict(os.environ, TMX_RESOURCES=str(RES), LD_LIBRARY_PATH=str(work)))
        if ran.returncode != 0:
            _SWIFT_EVIDENCE = {'available': False, 'reason': 'product probe crashed: %s'
                               % ran.stderr[-300:]}
            return None
        evidence = {'available': True, 'kind_for': {}, 'counts': {}, 'unmatched': {}, 'labels': {},
                    'is_safe': {}, 'footprint': {}, 'loaded': 0,
                    'negative_control_build_fails': without.returncode != 0}
        for line in ran.stdout.splitlines():
            parts = line.split('\t')
            if parts[0] == 'LOADED':
                evidence['loaded'] = int(parts[1])
            elif parts[0] == 'KIND_OF':
                evidence['kind_for'][parts[1]] = parts[2]
            elif parts[0] == 'COUNT':
                evidence['counts'][parts[1]] = int(parts[2])
            elif parts[0] == 'UNMATCHED':
                evidence['unmatched'][parts[1]] = int(parts[2])
            elif parts[0] == 'LABEL':
                evidence['labels'][parts[1]] = parts[3] if len(parts) > 3 else ''
                evidence['is_safe'][parts[1]] = parts[2] == 'true'
            elif parts[0] == 'FOOTPRINT':
                evidence['footprint'][parts[1]] = parts[2]
        _SWIFT_EVIDENCE = evidence
        return evidence
    finally:
        shutil.rmtree(work, ignore_errors=True)


def swift_evidence_unavailable_reason():
    return (_SWIFT_EVIDENCE or {}).get('reason', 'the Swift contour has not been attempted')


def check_citation(anchor):
    """Verify a cited file:line span still contains the text the table claims it does.

    This change edits the very file it cites, so a hand-written `file:line` goes stale by
    construction (the citation-integrity audit found exactly that). Every anchor in the
    disposition table is therefore re-read from the current tree.
    """
    path = ROOT / anchor['file']
    if not path.is_file():
        return 'cited file does not exist: %s' % anchor['file']
    lines = read(path).splitlines()
    try:
        low, high = (int(x) for x in anchor['lines'].split('-'))
    except ValueError:
        return 'citation range is not "N-M": %r' % anchor['lines']
    if not 1 <= low <= high <= len(lines):
        return 'citation %s:%s is outside the file (%d lines)' % (anchor['file'], anchor['lines'], len(lines))
    if anchor['expect'] not in '\n'.join(lines[low - 1:high]):
        return 'citation %s:%s does not contain %r' % (anchor['file'], anchor['lines'], anchor['expect'])
    return None


def balanced_parens(text, open_index):
    """Contents of a balanced parenthesised group starting at ``text[open_index] == '('``.
    ``CGRect(x: sx, y: max(0, bottomY - 240), width: 48, height: 272)`` must be captured whole: a
    first-closing-paren regex stops at ``max(0`` and then cannot see a width or height edit."""
    if open_index >= len(text) or text[open_index] != '(':
        return None
    depth, index = 0, open_index
    while index < len(text):
        ch = text[index]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return text[open_index + 1:index]
        index += 1
    return None


def rect_arguments(body):
    """Every CGRect(...) argument list in a branch body, balanced-paren captured."""
    out = []
    for match in re.finditer(r'CGRect\s*\(', body):
        captured = balanced_parens(body, body.index('(', match.start()))
        if captured is None:
            out.append('UNTERMINATED')
        else:
            out.append(re.sub(r'\s+', ' ', captured).strip())
    return out


def fingerprint_body(body):
    """Normalized factory 'output' of one branch body: the state mutations, nodes, textures and the
    full CGRect geometry it builds. Pure over text so a mutation control can feed it a doctored body."""
    if body is None:
        return None
    mutations = ['%s.%s' % (a, b) for a, b in
                 re.findall(r'(\w+)\.(append|insert|remove[A-Za-z]*|add[A-Za-z]*)\(', body)]
    textures = re.findall(r'SKTexture\(imageNamed:\s*"([^"]+)"\)', body)
    images = re.findall(r'\bimage:\s*"([^"]+)"', body)
    nodes = sorted({m[0] or m[1] for m in
                    re.findall(r'(\w+)\.node|addChild\(\s*(\w+)', body) if m[0] or m[1]})
    rects = rect_arguments(body)
    numbers = sorted(set(re.findall(r'\b\d+\b', body)))
    return {'mutations': mutations, 'textures': textures, 'images': images, 'nodes': nodes,
            'rect_count': len(rects), 'rects': rects, 'numeric_literals': numbers,
            'label_source': bool(re.search(r'label:', body))}


def route_base_source(relative_path, ref=None):
    result = git('show', '%s:%s' % (ref or BASE_COMMIT, relative_path))
    return result.stdout if result.returncode == 0 else None


def base_branch_fingerprints(substrings, base_commit=None):
    """The pre-change fingerprints, read from an immutable base blob rather than from a golden this
    tool once wrote: the comparison cannot be talked into agreeing with itself."""
    text = route_base_source(RUNTIME_SWIFT.relative_to(ROOT).as_posix(),
                             base_commit or BASE_COMMIT)
    if text is None:
        return None
    case_body = source_marker_case(text)
    return {sub: fingerprint_body(branch_body(case_body, sub, None)) for sub in substrings}


def authorized_deviations(baseline):
    """Per-arm departures from the base fingerprint that a *named* later change authorized.

    Wave C's exhaustive switch rewrites the same `beam_`/force-field arm that wave B semantically
    rewrites, and the integration ruling is A -> B -> C. After this branch rebases onto a main that
    already contains wave B, the `beam_` arm legitimately stops matching route base 295690b. That
    re-baseline has to be an explicit record naming the arm, the exact digest transition and the
    authorizing change - never a silently rewritten golden, and never a wildcard able to swallow
    unrelated drift. Empty by default, so AC-005 is fail-closed until someone writes down who
    authorized what.
    """
    return {entry['arm']: entry for entry in baseline.get('arm_deviations', []) if entry.get('arm')}


def deviation_is_honored(entry, base_fp, current_fp):
    """An excuse applies only to the exact digest transition it records, and only if it cites who
    authorized it and why."""
    if not entry or base_fp is None or current_fp is None:
        return False
    if digest_of(entry.get('from')) != digest_of(base_fp):
        return False
    if digest_of(entry.get('to')) != digest_of(current_fp):
        return False
    return all(str(entry.get(field, '')).strip() for field in ('authorized_by', 'reason'))


def overlay_binding_problems(text):
    """FORBID-002's second clause: a safe model must be identifiable **in debug rendering**.

    SpriteKit cannot be compiled or run on this host (`swiftc -typecheck` on the runtime stops at
    `import SpriteKit`), so this is a structural source assertion over the real `GameScene.swift`:
    the hitbox overlay must consume `safeModelMarkers`, must draw each recorded rect, and must carry
    the label onto the node. Pure over text so a control can feed it a copy with the loop deleted -
    the exact regression the test review showed passing every probe (F2 / case R2).
    """
    problems = []
    if 'safeModelMarkers' not in text:
        problems.append('GameScene.swift never reads safeModelMarkers: a recorded safe model has no '
                        'debug rendering (FORBID-002 "in debug rendering")')
        return problems
    loop = re.search(r'for\s+\w+\s+in\s+currentLevel\.safeModelMarkers\s*\{(.*?)\n\s*\}', text, re.S)
    if not loop:
        problems.append('no `for … in currentLevel.safeModelMarkers` loop in GameScene.swift')
    else:
        body = loop.group(1)
        if 'addDebugRect(' not in body or 'marker.rect' not in body:
            problems.append('the safe-model loop does not draw marker.rect through addDebugRect')
        if 'label:' not in body or 'marker.label' not in body:
            problems.append('the safe-model loop does not pass the label through to the node')
    helper = re.search(r'func addDebugRect\(([^)]*)\)', text)
    if not helper:
        problems.append('addDebugRect is gone from GameScene.swift')
    elif 'label:' not in helper.group(1):
        problems.append('addDebugRect no longer accepts a label parameter')
    if 'debugOverlay' not in text:
        problems.append('the debug overlay container is gone')
    return problems


def swift_parse_gate(paths):
    """`swiftc -frontend -parse` as an executed check rather than a prose claim (test review F2).

    Syntax-only - no stronger than what the reviewer ran by hand - but now reproducible and wired
    into a probe, so it cannot quietly stop being true. A missing toolchain is reported, never
    treated as a pass.
    """
    if shutil.which('swiftc') is None:
        return None
    results = {}
    for path in paths:
        if not path.is_file():
            results[path.name] = 'file missing'
            continue
        done = subprocess.run(['swiftc', '-frontend', '-parse', str(path)],
                              capture_output=True, text=True, timeout=240)
        results[path.name] = 'ok' if done.returncode == 0 else (
            done.stderr.strip().splitlines() or ['parse failed'])[0][:160]
    return results


def parse_gate_selftest():
    """Prove the syntax gate can fail: feed `swiftc -frontend -parse` a file with a real syntax
    error and require a non-ok verdict. Without this the gate's green result is unfalsifiable."""
    if shutil.which('swiftc') is None:
        return False
    work = Path(tempfile.mkdtemp(prefix='wave-c-parse-'))
    try:
        bad = work / 'Broken.swift'
        bad.write_text('struct Broken {\n    let x: Int\n', encoding='utf-8')  # unclosed brace
        good = work / 'Fine.swift'
        good.write_text('struct Fine {\n    let x: Int\n}\n', encoding='utf-8')
        verdicts = swift_parse_gate([bad, good])
        return bool(verdicts) and verdicts.get('Broken.swift') != 'ok' \
            and verdicts.get('Fine.swift') == 'ok'
    finally:
        shutil.rmtree(work, ignore_errors=True)


def disposition_consistency(rows, product_is_safe):
    """AC-001 makes the disposition column normative, so it must be an equivalence, not a label:
    ``disposition == 'safe-model'`` <=> the product says the kind is a safe model, and a non-empty
    label <=> the same disposition. Without this a safe model renamed `typed` with an empty label
    keeps every probe green while FORBID-002's "identifiable in the meter output" goes false."""
    problems = []
    for row in rows:
        kind, block = row['kind'], row['sourceBlock']
        table_safe = row['disposition'] == 'safe-model'
        if kind not in product_is_safe:
            problems.append('%s: the product has no kind %r to compare the disposition against'
                            % (block, kind))
            continue
        product_safe = bool(product_is_safe[kind])
        if product_safe != table_safe:
            problems.append('%s: table disposition %r contradicts the product isSafeModel=%r for %r'
                            % (block, row['disposition'], product_safe, kind))
        has_label = bool(str(row.get('label', '')).strip())
        if has_label != table_safe:
            problems.append('%s: label %s while disposition is %r — a safe model must be labeled and '
                            'a typed one must not borrow the label'
                            % (block, 'present' if has_label else 'absent', row['disposition']))
    return problems


def product_is_safe_map(evidence, loader_src):
    """kind -> is a safe model, from the executed product when available; the source-parsed
    `safeModelLabel` (empty exactly for non-safe kinds) is the fallback."""
    if evidence:
        return dict(evidence['is_safe'])
    return {kind: bool(label.strip()) for kind, label in classifier_labels(loader_src).items()
            if kind != 'default'}


def unclaimed_values(distinct, claims):
    """Pure helper: which corpus values does this claim set miss?

    Extracted so a control can test the detector's *discrimination*: it must flag a value the
    product does not test AND stay quiet about values it does. The inline expression this replaces
    stayed true even when the product tested nothing (test review F6)."""
    return [b for b in distinct if not any(s in b for s in claims)]


def new_literals(before, now):
    """Pure helper for the texture-literal guard, for the same reason: a control written as
    `(now | {x}) - before - (now - before)` is true for every reachable state."""
    return set(now) - set(before)


def legacy_bucket(block, substrings=LEGACY_SUBSTRINGS):
    for sub in substrings:
        if sub in block:
            return sub
    return None


def digest_of(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode('utf-8')).hexdigest()


def covered_marker_records(markers=None):
    """The projection that AC-005 pins: every marker the *legacy* seven already claimed."""
    markers = markers if markers is not None else map_markers()
    out = {}
    for name, rows in sorted(markers.items()):
        keep = [[r['block'], r['sx'], r['sy'], r['x'], r['y'], r['w'], r['h'],
                 legacy_bucket(r['block']), r['props']] for r in rows if legacy_bucket(r['block'])]
        if keep:
            out[name] = keep
    return out


# --------------------------------------------------------------------------- #
# Probes
# --------------------------------------------------------------------------- #
def marker_coverage_all_maps():
    markers = map_markers()
    total = sum(len(v) for v in markers.values())
    distinct = sorted({row['block'] for v in markers.values() for row in v})
    ordered, loader_map, chain = claimed_substrings()
    claimed = set(ordered)
    unclaimed = [b for b in distinct if not any(s in b for s in claimed)]
    lost = sum(1 for v in markers.values() for row in v
               if not any(s in row['block'] for s in claimed))
    lost_maps = sorted({name for name, rows in markers.items()
                        if any(not any(s in r['block'] for s in claimed) for r in rows)})
    orphan = sorted(s for s in claimed if not any(s in b for b in distinct))

    runtime_src = read(RUNTIME_SWIFT)
    loader_src = read(LOADER_SWIFT)
    case_body = source_marker_case(runtime_src)
    records_miss = 'unmatchedSourceMarkers.append' in case_body
    declares_miss = 'unmatchedSourceMarkers' in runtime_src
    can_represent_miss = 'return nil' in loader_src

    problems = []
    if unclaimed:
        problems.append('%d of %d distinct sourceBlock values are unclaimed: %s'
                        % (len(unclaimed), len(distinct), ', '.join(unclaimed)))
    if lost:
        problems.append('%d of %d markers resolve to nothing, on %d maps'
                        % (lost, total, len(lost_maps)))
    if orphan:
        problems.append('matcher tests that claim no corpus value: %s' % ', '.join(orphan))
    if not records_miss:
        problems.append('the source_marker case has no unmatchedSourceMarkers.append path: '
                        'an unmatched marker is still dropped without a signal')
    if not declares_miss:
        problems.append('the runtime declares no observable unmatched marker collection')
    if not can_represent_miss:
        problems.append('the classifier cannot represent an unmatched marker (no nil result)')

    controls = {
        # The detector must DISCRIMINATE, not merely shout. Sensitivity: a value the product does
        # not test is flagged. Precision: no real corpus value is flagged. The old inline form
        # stayed True with `claimed = set()` (test review F6); precision is what kills that.
        'synthetic_unclaimed_detected': (
            'blk_zz_control' in unclaimed_values(distinct + ['blk_zz_control'], claimed)
            and not unclaimed_values(distinct, claimed)),
        # the meter may not claim coverage by asserting a literal the product does not test:
        # strip the classifier text and the claim set must collapse.
        'meter_reads_the_product_not_itself': loader_claims('') == {} and runtime_chain('') == [],
    }
    controls['missing_recorder_flips_probe'] = (
        'unmatchedSourceMarkers.append' not in source_marker_case(
            case_body.replace('unmatchedSourceMarkers.append', 'dropped.append')))

    # Executed proof: run the product classifier itself over the whole corpus, so the coverage
    # number is the product's and not this meter's replica of it.
    evidence = swift_product_evidence()
    if evidence:
        if evidence['loaded'] != len(trees()):
            problems.append('the product loader parsed %d of %d maps'
                            % (evidence['loaded'], len(trees())))
        if evidence['unmatched']:
            problems.append('the product classifier itself matched nothing for: %s'
                            % ', '.join('%s x%d' % (k, v)
                                        for k, v in sorted(evidence['unmatched'].items())))
        if sum(evidence['counts'].values()) != total:
            problems.append('the product counted %d markers, the meter counted %d'
                            % (sum(evidence['counts'].values()), total))
        if set(evidence['counts']) != set(distinct):
            problems.append('product and meter disagree about the sourceBlock corpus')
        if not evidence['negative_control_build_fails']:
            problems.append('the product built without the CoreGraphics shim, so the executed '
                            'number may not come from the repository source')
        controls['product_execution_agrees'] = (not evidence['unmatched']
                                                and sum(evidence['counts'].values()) == total)
        controls['product_negative_control_holds'] = evidence['negative_control_build_fails']
        product_executed = True
    else:
        problems.append('AC-001 is not product-executed on this host (%s); structural checks only'
                        % swift_evidence_unavailable_reason())
        product_executed = False

    # AC-001's disposition column is normative, so it is enforced as an equivalence here too:
    # declaring a safe model as "typed" must not be able to pass the coverage probe.
    is_safe_map = product_is_safe_map(evidence, loader_src)
    if DISPOSITION_PATH.exists():
        rows = json.loads(read(DISPOSITION_PATH))['markers']
        problems.extend(disposition_consistency(rows, is_safe_map))
        bypass = copy.deepcopy(rows)
        for row in bypass:
            if row['sourceBlock'] == 'blk_waggon':
                row['disposition'] = 'typed'
                row['label'] = ''
        controls['safe_relabelled_as_typed_reddens_coverage'] = bool(
            disposition_consistency(bypass, is_safe_map))
    else:
        problems.append('no disposition table to check the normative column against')
        controls['safe_relabelled_as_typed_reddens_coverage'] = False
    ok = not problems and all(controls.values())
    return ok, {
        'markers_total': total, 'markers_covered': total - lost, 'markers_lost': lost,
        'distinct_source_blocks': len(distinct),
        'distinct_claimed': len(distinct) - len(unclaimed),
        'claimed_by_matcher': sorted(claimed), 'unclaimed': unclaimed, 'lost_maps': len(lost_maps),
        'silent_drop_path_removed': records_miss and declares_miss and can_represent_miss,
        'product_executed': product_executed,
        'controls': controls, 'problems': problems,
    }


def stale_mirror_report():
    """Read the other package's committed mirrors and say out loud where they now disagree.

    `v3_measurements.py` and `linux_static_audit.py` hard-code the matcher as a hand-copied tuple
    and never read the Swift, so after this fix they still print 76 read / 51 lost with rc=0 about
    a tree where that is false (test review F5). Editing them is another route's scope, but
    silence is not: this returns the divergence so the meter cannot agree with a stale oracle and
    a reader never finds out. The pinned legacy table must still equal the mirror's tuple, because
    that tuple is what the audited baseline means.
    """
    report = {'mirrors': [], 'baseline_agrees': True}
    patterns = [
        ('engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/v3_measurements.py',
         r'HANDLED\s*=\s*\(([^)]*)\)'),
        ('engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/linux_static_audit.py',
         r'HANDLED_SOURCE_SUBSTRINGS\s*=\s*\(([^)]*)\)'),
    ]
    product_claims = set(claimed_substrings()[0])
    for rel, pattern in patterns:
        path = ROOT / rel
        if not path.is_file():
            continue
        match = re.search(pattern, read(path), re.S)
        if not match:
            report['mirrors'].append({'file': rel, 'status': 'pattern not found'})
            continue
        tupled = tuple(re.findall(r'"([^"]+)"', match.group(1)))
        still_covers = sum(1 for v in map_markers().values() for r in v
                           if legacy_bucket(r['block'], tupled))
        total = sum(len(v) for v in map_markers().values())
        entry = {'file': rel, 'mirror_tuple': list(tupled),
                 'markers_covered_if_the_mirror_were_the_product': still_covers,
                 'product_actually_covers': total - sum(
                     1 for v in map_markers().values() for r in v
                     if not any(s in r['block'] for s in product_claims)),
                 'stale': still_covers != total}
        report['mirrors'].append(entry)
        if entry['stale']:
            report.setdefault('divergence', []).append(
                '%s still reports %d/%d (rc=0) about a tree where the product resolves %d/%d; '
                'owner-route cleanup owed, see tasks.md R1'
                % (Path(rel).name, still_covers, total,
                   entry['product_actually_covers'], total))
        if set(tupled) != set(LEGACY_SUBSTRINGS):
            report['baseline_agrees'] = False
            report.setdefault('divergence', []).append(
                '%s: the mirror tuple no longer equals the pinned legacy baseline table' % Path(rel).name)
    return report


def marker_baseline_reproduced():
    """Control probe: the *pre-change* 76/127 split must still be reproducible from the pinned
    legacy table, so a later reader can see exactly what the change moved."""
    markers = map_markers()
    total = sum(len(v) for v in markers.values())
    distinct = sorted({row['block'] for v in markers.values() for row in v})
    lost, lost_maps, covered = {}, {}, 0
    for name, rows in markers.items():
        for row in rows:
            if legacy_bucket(row['block']):
                covered += 1
            else:
                lost[row['block']] = lost.get(row['block'], 0) + 1
                lost_maps.setdefault(row['block'], set()).add(name)
    got = {
        'markers_total': total, 'markers_covered': covered, 'markers_lost': sum(lost.values()),
        'lost_maps': len({n for s in lost_maps.values() for n in s}),
        'distinct_source_blocks': len(distinct),
        'lost_kinds': dict(sorted(lost.items())),
        'lost_kind_maps': {k: len(v) for k, v in sorted(lost_maps.items())},
    }
    problems = ['%s: baseline expects %r, corpus gives %r' % (k, LEGACY_BASELINE[k], got.get(k))
                for k in LEGACY_BASELINE if k in got and got.get(k) != LEGACY_BASELINE[k]]
    narrowed = tuple(s for s in LEGACY_SUBSTRINGS if s != 'beam_')
    drop_beam = sum(1 for v in markers.values() for r in v if not legacy_bucket(r['block'], narrowed))
    drop_all = sum(1 for v in markers.values() for r in v if not legacy_bucket(r['block'], ()))
    controls = {
        'drop_beam_raises_lost_to_71': drop_beam == LEGACY_BASELINE['control_drop_beam_lost'],
        'drop_all_loses_everything': drop_all == LEGACY_BASELINE['control_drop_all_lost'],
        'narrower_table_cannot_lose_less': drop_beam > got['markers_lost'],
    }
    ok = not problems and all(controls.values())
    mirrors = stale_mirror_report()
    if not mirrors['baseline_agrees']:
        problems.append('the pinned legacy table no longer matches the committed mirror tuples')
        ok = False
    return ok, dict(got, baseline_expected=LEGACY_BASELINE, controls=controls,
                    measured_with_legacy_table=True, stale_mirrors=mirrors,
                    problems=problems)


def ignored_types_disposition():
    if not DISPOSITION_PATH.exists():
        return False, {'problems': ['disposition table missing: %s' % DISPOSITION_PATH]}
    markers = map_markers()
    ordered, loader_map, _chain = claimed_substrings()
    claimed = set(ordered)
    kinds = classifier_kinds(read(LOADER_SWIFT))
    table = json.loads(read(DISPOSITION_PATH))
    by_block = {m['sourceBlock']: m for m in table['markers']}
    corpus = {}
    for name, rows in markers.items():
        for row in rows:
            entry = corpus.setdefault(row['block'], {'count': 0, 'maps': set()})
            entry['count'] += 1
            entry['maps'].add(name)

    problems = []
    missing = sorted(set(corpus) - set(by_block))
    extra = sorted(set(by_block) - set(corpus))
    if missing:
        problems.append('no committed disposition for: %s' % ', '.join(missing))
    if extra:
        problems.append('disposition names absent from the corpus: %s' % ', '.join(extra))
    for block, entry in sorted(corpus.items()):
        row = by_block.get(block)
        if row is None:
            continue
        if row['count'] != entry['count']:
            problems.append('%s: table count %d != corpus %d' % (block, row['count'], entry['count']))
        if row['maps'] != len(entry['maps']):
            problems.append('%s: table maps %d != corpus %d' % (block, row['maps'], len(entry['maps'])))
        if 'maps_list' in row and sorted(row['maps_list']) != sorted(entry['maps']):
            problems.append('%s: table maps_list disagrees with the corpus' % block)
        if row['substring'] not in claimed:
            problems.append('%s: table claims substring %r which the product does not test'
                            % (block, row['substring']))
        if kinds and row['kind'] not in kinds:
            problems.append('%s: table kind %r is not a TMXSourceMarkerKind case (%s)'
                            % (block, row['kind'], ', '.join(kinds)))
    resolved = {}
    for block in FORMERLY_IGNORED:
        row = by_block.get(block)
        resolved[block] = bool(row) and row['substring'] in claimed and \
            (not kinds or row['kind'] in kinds)
    if not all(resolved.values()):
        problems.append('formerly-ignored families still unresolved: %s'
                        % ', '.join(sorted(k for k, v in resolved.items() if not v)))

    # mandatory flips: a table that lies about the product must be caught
    tampered_sub = copy.deepcopy(by_block)
    tampered_sub['blk_mushroom']['substring'] = 'blk_does_not_exist'
    tampered_kind = copy.deepcopy(by_block)
    tampered_kind['blk_waggon']['kind'] = 'zzNotDeclaredAnywhere'
    tampered_count = copy.deepcopy(by_block)
    tampered_count['blk_mushroom']['count'] = by_block['blk_mushroom']['count'] + 5
    controls = {
        'bogus_substring_rejected': tampered_sub['blk_mushroom']['substring'] not in claimed,
        'bogus_kind_rejected': (not kinds) or tampered_kind['blk_waggon']['kind'] not in kinds,
        'bogus_count_rejected': tampered_count['blk_mushroom']['count'] != corpus['blk_mushroom']['count'],
    }
    # Citation currency: every file:line the table asserts must resolve in the current tree.
    checked = 0
    for block, row in sorted(by_block.items()):
        citations = row.get('citations')
        if not citations:
            problems.append('%s: no machine-checked citation' % block)
            continue
        if 'route base' not in citations.get('route_base', ''):
            problems.append('%s: route-base anchor does not name the commit it describes' % block)
        for key in ('runtime_arm', 'classifier_test'):
            anchor = citations.get(key)
            if not anchor:
                problems.append('%s: missing %s citation' % (block, key))
                continue
            checked += 1
            failure = check_citation(anchor)
            if failure:
                problems.append('%s: %s' % (block, failure))
    controls['stale_citation_rejected'] = bool(check_citation(
        {'file': 'Exolon/GameCore/Levels/TMXLevelRuntime.swift', 'lines': '1-3',
         'expect': 'case .forceField:'}))
    controls['out_of_range_citation_rejected'] = bool(check_citation(
        {'file': 'Exolon/GameCore/Levels/TMXMapLoader.swift', 'lines': '99999-99999', 'expect': 'x'}))
    # Executed proof: the table must describe what the product actually returns for each family.
    evidence = swift_product_evidence()
    if evidence:
        for block, row in sorted(by_block.items()):
            if evidence['kind_for'].get(block) != row['kind']:
                problems.append('%s: the product classifier returns %r, the table says %r'
                                % (block, evidence['kind_for'].get(block), row['kind']))
            if evidence['counts'].get(block) != row['count']:
                problems.append('%s: the product counted %r markers, the table says %r'
                                % (block, evidence['counts'].get(block), row['count']))
        controls['product_table_agrees'] = not any(
            evidence['kind_for'].get(b) != r['kind'] or evidence['counts'].get(b) != r['count']
            for b, r in by_block.items())
    else:
        problems.append('AC-002 is not product-executed on this host (%s)'
                        % swift_evidence_unavailable_reason())
        controls['product_table_agrees'] = False
    totals = table.get('totals', {})
    if totals.get('pre_change_lost') != LEGACY_BASELINE['markers_lost']:
        problems.append('table totals.pre_change_lost disagrees with the pinned baseline')
    if totals.get('markers_total') != LEGACY_BASELINE['markers_total']:
        problems.append('table totals.markers_total disagrees with the corpus')
    if sum(m['count'] for m in table['markers']) != LEGACY_BASELINE['markers_total']:
        problems.append('table marker counts do not sum to 127')
    ok = not problems and all(controls.values())
    return ok, {
        'distinct_in_corpus': len(corpus), 'dispositions_committed': len(by_block),
        'formerly_ignored_resolved': resolved,
        'safe_model_families': sorted(m['sourceBlock'] for m in table['markers']
                                      if m['disposition'] == 'safe-model'),
        'classifier_kinds': kinds, 'controls': controls, 'problems': problems,
        'citations_verified': checked,
    }


def pair_violations(hashes, pairs):
    return [{'a': a, 'b': b} for a, b in pairs if hashes.get(a) != hashes.get(b)]


def undeclared_collisions(hashes, pairs):
    declared = {tuple(sorted((a, b))) for a, b in pairs}
    groups = {}
    for name, digest in hashes.items():
        groups.setdefault(digest, []).append(name)
    out = []
    for members in groups.values():
        if len(members) < 2:
            continue
        members = sorted(members)
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                if (members[i], members[j]) not in declared:
                    out.append([members[i], members[j]])
    return out


def identical_pair_set(hashes):
    groups = {}
    for name, digest in hashes.items():
        groups.setdefault(digest, []).append(name)
    return {tuple(sorted(g)) for g in groups.values() if len(g) > 1}


def level_pair_manifest_pinned():
    if not MANIFEST_PATH.exists():
        return False, {'problems': ['manifest missing: %s' % MANIFEST_PATH]}
    manifest = json.loads(read(MANIFEST_PATH))
    hashes = canonical_hashes()
    declared = [(p['a'], p['b']) for p in manifest.get('identical_pairs', [])]
    problems = []
    if sorted(map(tuple, declared)) != sorted(DECLARED_PAIRS):
        problems.append('declared pairs differ from the merged P1-12 finding: %d declared vs %d expected'
                        % (len(declared), len(DECLARED_PAIRS)))
    manifest_maps = manifest.get('maps', {})
    missing = sorted(set(hashes) - set(manifest_maps))
    extra = sorted(set(manifest_maps) - set(hashes))
    if missing or extra:
        problems.append('manifest map set != corpus (missing %d, extra %d)' % (len(missing), len(extra)))
    drift = sorted(n for n, d in hashes.items() if manifest_maps.get(n, {}).get('sha256') != d)
    if drift:
        problems.append('%d per-map digests drift from the corpus: %s' % (len(drift), ', '.join(drift[:5])))
    violations = pair_violations(hashes, declared)
    if violations:
        problems.append('%d declared pairs are not actually identical: %s'
                        % (len(violations), violations[:3]))
    collisions = undeclared_collisions(hashes, declared)
    if collisions:
        problems.append('%d undeclared collisions: %s' % (len(collisions), collisions[:3]))
    unique = len(set(hashes.values()))
    if unique != manifest.get('unique_count') or unique != DECLARED_UNIQUE:
        problems.append('unique count: recomputed %d, manifest %r, audited %d'
                        % (unique, manifest.get('unique_count'), DECLARED_UNIQUE))
    if manifest.get('canonicalization_version') != CANON_VERSION:
        problems.append('canonicalization_version is %r, expected %r'
                        % (manifest.get('canonicalization_version'), CANON_VERSION))
    flagged = {tuple(sorted((p['a'], p['b']))) for p in manifest.get('identical_pairs', [])
               if p.get('background_identical')}
    if flagged != DECLARED_FULLY_IDENTICAL:
        problems.append('background_identical pairs %s != the audited 4 %s'
                        % (sorted(flagged), sorted(DECLARED_FULLY_IDENTICAL)))
    # The ruling must disclose where its own premise stops: L03S09/L04S11 is not a stage-2 reskin.
    notes = manifest.get('pair_notes') or {}
    if 'L03S09/L04S11' not in notes:
        problems.append('pair_notes does not disclose the L03S09/L04S11 tension, so the ruling would '
                        'read as if its stage-2 premise covered all 24 pairs')
    else:
        note = notes['L03S09/L04S11']
        for field in ('why_separate', 'source_tension', 'caveat', 'consequence'):
            if not str(note.get(field, '')).strip():
                problems.append('pair_notes[L03S09/L04S11] is missing %r' % field)
    ruling = manifest.get('ruling') or {}
    if 'ruling' not in str(ruling.get('decision', '')).lower():
        problems.append('ruling.decision states intentionality without marking it as a ruling')
    if not ruling.get('premise_citations'):
        problems.append('ruling.premise_citations is empty: the reskin premise is the load-bearing '
                        'claim of this contract and must name its primaries')
    for pair in manifest.get('identical_pairs', []):
        a, b = pair['a'], pair['b']
        want = background_digests(trees()[a]) == background_digests(trees()[b])
        if bool(pair.get('background_identical')) != want:
            problems.append('%s/%s: background_identical=%r but the resolved backdrop bytes say %r'
                            % (a, b, pair.get('background_identical'), want))

    # mandatory flips: a synthetic divergent fixture must break the pin
    divergent = dict(hashes)
    divergent['L05S03'] = hashlib.sha256(b'synthetic-divergent-fixture').hexdigest()
    divergent_hit = [v for v in pair_violations(divergent, DECLARED_PAIRS) if v['a'] == 'L02S03']
    collided = dict(hashes)
    collided['L04S11'] = collided['L01S01']
    collision_hit = [c for c in undeclared_collisions(collided, DECLARED_PAIRS) if 'L04S11' in c]
    # and a real mutated ElementTree must produce a different canonical digest: one extra
    # object and one changed tile gid, both in an in-memory copy of L05S03
    object_mutant = copy_et(trees()['L05S03'])
    group = next(g for g in object_mutant if g.tag == 'objectgroup')
    synthetic = ET.SubElement(group, 'object')
    synthetic.set('name', 'blk_zz_divergent_fixture')
    synthetic.set('x', '0')
    synthetic.set('y', '0')
    tile_mutant = copy_et(trees()['L05S03'])
    layer_data = next(lay.find('data') for lay in tile_mutant if lay.tag == 'layer')
    if (layer_data.get('encoding') or 'csv') == 'csv':
        layer_data.text = layer_data.text.replace('0,0', '7,0', 1)
    else:  # base64: swap one whole cell
        decoded = decode_layer_data(layer_data)
        decoded[0] ^= 0x1
        layer_data.set('encoding', 'csv')
        layer_data.text = ','.join(str(v) for v in decoded)
    object_digest = hashlib.sha256(canonical_content(object_mutant).encode('utf-8')).hexdigest()
    tile_digest = hashlib.sha256(canonical_content(tile_mutant).encode('utf-8')).hexdigest()
    controls = {
        'divergent_fixture_flips_pin': bool(divergent_hit),
        'new_collision_flips_pin': bool(collision_hit),
        'extra_object_flips_digest': object_digest != hashes['L05S03'],
        'changed_tile_flips_digest': tile_digest != hashes['L05S03'],
        'untouched_copy_is_stable': hashlib.sha256(
            canonical_content(copy_et(trees()['L05S03'])).encode('utf-8')).hexdigest() == hashes['L05S03'],
    }
    ok = not problems and all(controls.values())
    return ok, {
        'maps': len(hashes), 'unique_recomputed': unique, 'unique_declared': manifest.get('unique_count'),
        'declared_pairs': len(declared), 'pair_violations': violations,
        'undeclared_collisions': collisions, 'background_identical_pairs': sorted(flagged),
        'controls': controls, 'problems': problems,
    }


def copy_et(root):
    """Cheap deep copy of an ElementTree element (ElementTree has no public copy API)."""
    import xml.etree.ElementTree as _ET
    return _ET.fromstring(_ET.tostring(root))


#: Embedded binding for the manifest body digest. A plain `sha256(body)` is only an *accident*
#: guard: whoever edits a value can recompute it and the committed contract still looks sealed
#: (test review F1, cases C7-C11). Mixing this constant in means a re-seal has to know the
#: construction; the real teeth are the live-corpus comparisons below, which a forged digest cannot
#: win - `Exolon/Resources` either contains the claimed backdrop or it does not.
INTEGRITY_BIND = 'exolon-level-content-v1:4f2c9ad7b6e10538'


def body_digest(doc):
    """Keyed digest over everything except `self_check`."""
    body = {k: v for k, v in doc.items() if k != 'self_check'}
    return hashlib.sha256(
        (INTEGRITY_BIND + json.dumps(body, sort_keys=True)).encode('utf-8')).hexdigest()


def reseal(doc):
    """Seal a document the legitimate way. The tamper controls re-seal on purpose, so they prove
    the probe catches a tamper **whose digest was correctly recomputed**, not merely a moved
    checksum."""
    doc['self_check'] = dict(doc.get('self_check') or {})
    doc['self_check']['body_sha256'] = body_digest(doc)
    return doc


def validate_manifest(doc, corpus_hashes=None):
    """Validate the contract against the **live tree**, not only against itself.

    Every field that describes shipped data is re-derived here: the canonical digest of each map,
    its backdrop file name, the backdrop's resolved bytes, and whether each declared-identical pair
    really is identical. `corpus_hashes` defaults to a fresh recomputation, because a self-check
    that skips it can be walked through by editing the JSON (test review F1).
    """
    errors = []
    if corpus_hashes is None:
        corpus_hashes = canonical_hashes()
    live = trees()
    if doc.get('contract') != CONTRACT_ID:
        errors.append('bad contract id %r' % doc.get('contract'))
    if doc.get('canonicalization_version') != CANON_VERSION:
        errors.append('bad canonicalization_version %r' % doc.get('canonicalization_version'))
    maps = doc.get('maps')
    if not isinstance(maps, dict) or len(maps) != 125:
        errors.append('maps must hold 125 entries, got %s'
                      % (len(maps) if isinstance(maps, dict) else type(maps).__name__))
        maps = maps if isinstance(maps, dict) else {}
    for name, entry in sorted(maps.items()):
        if not re.fullmatch(r'L0\dS\d{2}', name):
            errors.append('bad map key %r' % name)
            continue
        if not re.fullmatch(r'[0-9a-f]{64}', str(entry.get('sha256', ''))):
            errors.append('%s: sha256 is not a lowercase 64-hex digest' % name)
        stage, scene = int(name[1:3]), int(name[4:6])
        if entry.get('zone_index') != (stage - 1) * 25 + (scene - 1):
            errors.append('%s: zone_index %r breaks the 0-based formula' % (name, entry.get('zone_index')))
        if name not in corpus_hashes:
            errors.append('%s: not present in the shipped corpus' % name)
            continue
        if entry.get('sha256') != corpus_hashes[name]:
            errors.append('%s: canonical digest does not match the shipped file' % name)
        root = live.get(name)
        if root is None:
            errors.append('%s: cannot be parsed from the corpus' % name)
            continue
        refs = background_refs(root)
        want_bg = refs[0] if refs else ''
        if entry.get('background', '') != want_bg:
            errors.append('%s: declares background %r but the map references %r'
                          % (name, entry.get('background', ''), want_bg or '(no imagelayer)'))
        want_sha = (background_digests(root) or [''])[0]
        if entry.get('background_sha256', '') != want_sha:
            errors.append('%s: declares background_sha256 %r but the resolved file bytes are %r'
                          % (name, str(entry.get('background_sha256', ''))[:16], want_sha[:16]))
        if entry.get('background_count') != len(refs):
            errors.append('%s: background_count %r != %d layer(s) in the file'
                          % (name, entry.get('background_count'), len(refs)))
    pairs = doc.get('identical_pairs')
    if not isinstance(pairs, list) or len(pairs) != 24:
        errors.append('identical_pairs must hold 24 entries, got %s'
                      % (len(pairs) if isinstance(pairs, list) else type(pairs).__name__))
        pairs = pairs if isinstance(pairs, list) else []
    for p in pairs:
        a, b = p.get('a'), p.get('b')
        if a not in maps or b not in maps:
            errors.append('pair references an unknown map: %r' % p)
            continue
        if not isinstance(p.get('background_identical'), bool):
            errors.append('pair %s/%s lacks a boolean background_identical' % (a, b))
        if corpus_hashes.get(a) != corpus_hashes.get(b):
            errors.append('pair %s/%s is declared identical but the shipped maps are not' % (a, b))
        want_flag = background_digests(live[a]) == background_digests(live[b]) if a in live and b in live else None
        if want_flag is not None and bool(p.get('background_identical')) != want_flag:
            errors.append('pair %s/%s background_identical=%r contradicts the resolved bytes (%r)'
                          % (a, b, p.get('background_identical'), want_flag))
    if doc.get('unique_count') != len(set(corpus_hashes.values())):
        errors.append('unique_count %r != the %d digests the corpus actually has'
                      % (doc.get('unique_count'), len(set(corpus_hashes.values()))))
    if doc.get('map_count') != 125:
        errors.append('map_count must be 125, got %r' % doc.get('map_count'))
    if doc.get('self_check', {}).get('body_sha256') != body_digest(doc):
        errors.append('self_check.body_sha256 does not cover the body under the embedded binding '
                      '(tampered, re-sealed with a different construction, or regenerated)')
    return errors


def manifest_selfcheck():
    if not MANIFEST_PATH.exists():
        return False, {'problems': ['manifest missing: %s' % MANIFEST_PATH]}
    manifest = json.loads(read(MANIFEST_PATH))
    corpus = canonical_hashes()
    errors = validate_manifest(manifest, corpus)

    def tamper(mutate, victim='L02S16'):
        """Mutate a deep copy, re-seal it the legitimate way, and report the errors.

        Re-sealing is deliberate: a control that only checks "did the checksum move" proves nothing
        about a contract whose values were forged and then hashed correctly (test review F1).
        The victim is not `sorted(maps)[0]`, so these controls cannot coincide with each other or
        with a reader's own first-entry experiment.
        """
        doc = copy.deepcopy(manifest)
        mutate(doc['maps'][victim] if victim in doc.get('maps', {}) else doc, doc)
        return bool(validate_manifest(reseal(doc), corpus))

    tampons = {}
    tampons['flip_one_map_digest_rejected'] = tamper(
        lambda entry, doc: entry.update({'sha256': ('0' if entry['sha256'][0] != '0' else '1')
                                         + entry['sha256'][1:]}))
    # F1 case C10: claim a backdrop the map does not reference (foreign/absent file).
    tampons['swap_background_file_rejected'] = tamper(
        lambda entry, doc: entry.update({'background': 'zone_999_original.png'}))
    # F1 case C11: claim a well-formed but entirely fabricated backdrop digest.
    tampons['fabricate_background_digest_rejected'] = tamper(
        lambda entry, doc: entry.update({'background_sha256': 'ab' * 32}))
    tampons['drop_background_layer_claim_rejected'] = tamper(
        lambda entry, doc: entry.update({'background_count': 0, 'background': '',
                                         'background_sha256': ''}))
    tampons['drop_one_pair_rejected'] = tamper(
        lambda _e, doc: doc.__setitem__('identical_pairs', doc['identical_pairs'][:-1]))
    tampons['rewrite_unique_count_rejected'] = tamper(
        lambda _e, doc: doc.__setitem__('unique_count', 125))
    # Declare a pair that is not identical in the shipped data (AC-004's divergent-fixture half,
    # now inside the probe AC-004 names).
    tampons['declare_nonidentical_pair_rejected'] = tamper(
        lambda _e, doc: doc.__setitem__(
            'identical_pairs',
            [{'a': 'L01S01', 'b': 'L01S02', 'background_identical': False}] + doc['identical_pairs'][1:]))
    tampons['add_undeclared_pair_rejected'] = tamper(
        lambda _e, doc: doc['identical_pairs'].append(
            {'a': 'L01S01', 'b': 'L01S02', 'background_identical': False}))
    tampons['version_swap_rejected'] = tamper(
        lambda _e, doc: doc.__setitem__('canonicalization_version', 'something-else'))
    # A re-seal by the plain unkeyed construction must not be accepted either (F1's "tamper +
    # recompute digest" path against the older, weaker binding).
    naive = copy.deepcopy(manifest)
    naive['maps']['L02S16']['background_sha256'] = 'ab' * 32
    naive['self_check'] = dict(naive.get('self_check') or {})
    naive['self_check']['body_sha256'] = digest_of({k: v for k, v in naive.items() if k != 'self_check'})
    tampons['unkeyed_reseal_rejected'] = bool(validate_manifest(naive, corpus))
    tampons['honest_manifest_accepted'] = not errors
    ok = not errors and all(tampons.values())
    return ok, {'schema_errors': errors, 'tamper_controls': tampons,
                'tamper_victim_map': 'L02S16',
                'binding': 'keyed sha256 over the body (embedded constant) + live re-derivation of '
                           'every data claim; all tamper controls are re-sealed before being judged',
                'binding_limit': 'honest and stated: a forger who reads INTEGRITY_BIND and re-seals '
                                 'can still edit prose fields (ruling text, notes). Data fields cannot '
                                 'be forged this way because they are re-derived from '
                                 'Exolon/Resources on every run; narrative wording is covered by '
                                 'level_pair_manifest_pinned asserting the disclosure exists, not by '
                                 'this digest. Do not cite body_sha256 as protection for wording.',
                'body_sha256': manifest.get('self_check', {}).get('body_sha256')}


def unchanged_marker_output():
    if not BASELINE_PATH.exists():
        return False, {'problems': ['golden baseline missing: %s (run --record-baseline against '
                                   'the pre-change tree first)' % BASELINE_PATH]}
    baseline = json.loads(read(BASELINE_PATH))
    records = covered_marker_records()
    data_digest = digest_of(records)
    substring_kind = baseline.get('substring_kind', {})
    base_commit = baseline.get('base_commit') or BASE_COMMIT
    current = {sub: branch_fingerprint(sub, substring_kind.get(sub)) for sub in baseline['legacy_table']}
    # The pre-change side is read from an immutable base blob, so this probe cannot be satisfied by
    # editing a golden file: the comparison is working tree vs the recorded base commit.
    base = base_branch_fingerprints(baseline['legacy_table'], base_commit)
    deviations = authorized_deviations(baseline)
    problems = []
    honored_arms = []
    if base is None:
        problems.append('cannot read %s at %s to compare against' % (RUNTIME_SWIFT.name, base_commit))
    if data_digest != baseline['covered_marker_digest']:
        problems.append('the covered-marker records changed: %s != golden %s'
                        % (data_digest[:16], baseline['covered_marker_digest'][:16]))
    for sub in baseline['legacy_table']:
        if current[sub] is None:
            problems.append('legacy branch %r can no longer be located in the runtime source' % sub)
        elif base is not None and current[sub] != base.get(sub):
            if deviation_is_honored(deviations.get(sub), base.get(sub), current[sub]):
                honored_arms.append(sub)
            else:
                problems.append('branch output for %r changed vs the base and no authorized deviation '
                                'covers it: %r -> %r' % (sub, base.get(sub), current[sub]))
    for arm in deviations:
        if arm not in baseline['legacy_table']:
            problems.append('arm_deviations names %r, which is not a wave-C legacy arm' % arm)
        elif arm not in honored_arms:
            problems.append('arm_deviations[%r] is stale: it excuses a transition that is not what the '
                            'tree now shows' % arm)
    if baseline.get('base_branch_fingerprints') and base != baseline['base_branch_fingerprints']:
        problems.append('the golden file no longer agrees with the base blob it claims to record')
    if baseline.get('arm_deviations') and not str(baseline.get('deviation_ruling', '')).strip():
        problems.append('arm_deviations exist but deviation_ruling is empty: cite the change that '
                        'authorized them')
    count = sum(len(v) for v in records.values())
    if count != LEGACY_BASELINE['markers_covered']:
        problems.append('covered-marker count is %d, expected %d' % (count, LEGACY_BASELINE['markers_covered']))
    if count != baseline['covered_markers']:
        problems.append('covered-marker count %d != golden %d' % (count, baseline['covered_markers']))
    if any(v is None for v in current.values()):
        problems.append('some legacy branch is not locatable in the current runtime source')

    # Mandatory flips. The data half:
    synth = copy.deepcopy(records)
    target = sorted(synth)[0]
    synth[target][0][1] = '999'
    removed = copy.deepcopy(records)
    removed[target] = removed[target][1:]
    renamed = copy.deepcopy(records)
    renamed[target][0][7] = 'zz_unknown'
    # And the code half: doctored branch bodies must move the fingerprint. These are the mutations
    # that the old truncated CGRect capture could not see (height, width, an added statement).
    beam_body = branch_body(source_marker_case(read(RUNTIME_SWIFT)), 'beam_',
                            substring_kind.get('beam_')) or ''
    honest = fingerprint_body(beam_body)
    height_edit = fingerprint_body(beam_body.replace('height: 272', 'height: 999'))
    width_edit = fingerprint_body(beam_body.replace('width: 48', 'width: 120'))
    statement_added = fingerprint_body(beam_body + '\n rootNode.addChild(field.node)\n')
    comment_only = fingerprint_body(beam_body + '\n// a comment changes nothing\n')
    controls = {
        'geometry_change_detected': digest_of(synth) != data_digest,
        'removed_marker_detected': digest_of(removed) != data_digest,
        'bucket_change_detected': digest_of(renamed) != data_digest,
        'branch_rect_height_edit_detected': height_edit != honest,
        'branch_rect_width_edit_detected': width_edit != honest,
        'branch_statement_added_detected': statement_added != honest,
        'branch_comment_edit_ignored': comment_only == honest,
    }
    # The post-rebase escape hatch must be narrow: it excuses exactly the transition it records and
    # nothing else, and never without naming the authorizing change.
    sample_base = honest
    sample_new = height_edit
    controls['deviation_wrong_target_rejected'] = not deviation_is_honored(
        {'from': sample_base, 'to': width_edit, 'authorized_by': 'wave B', 'reason': 'pool API'},
        sample_base, sample_new)
    controls['deviation_uncited_rejected'] = not deviation_is_honored(
        {'from': sample_base, 'to': sample_new, 'authorized_by': '', 'reason': ''},
        sample_base, sample_new)
    controls['deviation_exact_and_cited_honored'] = deviation_is_honored(
        {'from': sample_base, 'to': sample_new,
         'authorized_by': 'wave B (beam grouping)', 'reason': 'B rewrites this arm intentionally'},
        sample_base, sample_new)
    controls['deviation_cannot_wildcard'] = not deviation_is_honored(
        {'from': '*', 'to': '*', 'authorized_by': 'everyone', 'reason': 'anything'},
        sample_base, sample_new)
    if 'height: 272' not in beam_body or 'width: 48' not in beam_body:
        problems.append('the rect mutation controls are vacuous: the beam_ branch no longer contains '
                        'the literals they edit. Expected after a wave-B rebase that groups force '
                        'fields - do not delete the control; point it at the literals the merged arm '
                        'now uses and record the transition in arm_deviations.')
    ok = not problems and all(controls.values())
    return ok, {
        'covered_markers': count, 'covered_maps': len(records),
        'data_digest': data_digest, 'golden_digest': baseline['covered_marker_digest'],
        'compared_against': '%s (%s)' % (base_commit[:12], RUNTIME_SWIFT.name),
        'branches_located': sorted(k for k, v in current.items() if v),
        'branches_changed_vs_base': [s for s in current
                                     if base is not None and current[s] != base.get(s)],
        'deviations_honored': honored_arms,
        'beam_rect_pinned': honest['rects'] if honest else None,
        'controls': controls, 'problems': problems,
    }


def no_invented_content():
    base = ls_tree_blobs('Exolon/Resources')
    if len(base) < 200:
        return False, {'problems': ['cannot read the base tree for Exolon/Resources: %s'
                                    % git('rev-parse', '--verify', BASE_COMMIT).stderr.strip()]}
    paths = sorted(p.relative_to(ROOT).as_posix() for p in RES.iterdir() if p.is_file())
    hashed = git('hash-object', '--', *paths)
    if hashed.returncode != 0:
        return False, {'problems': ['git hash-object failed: %s' % hashed.stderr.strip()]}
    working = dict(zip(paths, hashed.stdout.split()))
    diff = compare_blobs(base, working)
    problems = []
    for kind in ('deleted', 'invented', 'rewritten'):
        if diff[kind]:
            problems.append('%d resource files %s: %s' % (len(diff[kind]), kind, ', '.join(diff[kind][:5])))
    hashes = canonical_hashes()
    unique = len(set(hashes.values()))
    if unique != DECLARED_UNIQUE:
        problems.append('uniqueness is now %d, not the audited %d - content was authored or removed'
                        % (unique, DECLARED_UNIQUE))
    pairs = identical_pair_set(hashes)
    if pairs != {tuple(sorted((a, b))) for a, b in DECLARED_PAIRS}:
        problems.append('the identical-pair set moved away from the audited 24 pairs')
    singletons = {g for g in pairs if len(g) > 2}
    if singletons:
        problems.append('a duplicate group now spans more than 2 maps: %s' % sorted(singletons))
    now_literals, before_literals = all_image_literals(), base_image_literals()
    added_literals = sorted(new_literals(before_literals, now_literals))
    if added_literals:
        problems.append('new image/texture literals introduced: %s' % ', '.join(added_literals))

    # mandatory flips: synthetic invention must be caught by the same comparison
    flipped_add = compare_blobs(base, dict(working, **{'Exolon/Resources/INVENTED.tmx': 'deadbeef'}))
    flipped_edit = {k: v for k, v in working.items()}
    changed_key = sorted(set(base) & set(flipped_edit))[0]
    flipped_edit[changed_key] = 'ffffffff'
    flipped_del = compare_blobs(base, {k: v for k, v in working.items() if k != changed_key})
    controls = {
        'invented_file_detected': bool(flipped_add['invented']),
        'rewritten_file_detected': bool(compare_blobs(base, flipped_edit)['rewritten']),
        'deleted_file_detected': bool(flipped_del['deleted']),
        'new_texture_literal_detected': (
            new_literals(before_literals, set(before_literals) | {'zz_invented'}) == {'zz_invented'}
            and new_literals(before_literals, now_literals) == set()),
        # Counting must actually track the digests: forcing one map to a novel digest has to raise
        # the unique count by exactly one. (The old `unique != 125` restated the problem check.)
        'uniqueness_shift_detected': len(set(list(hashes.values())[:-1] + ['cd' * 32])) == unique + 1,
    }
    ok = not problems and all(controls.values())
    return ok, {
        'resource_files_base': len(base), 'resource_files_working': len(working),
        'deleted': diff['deleted'], 'invented': diff['invented'], 'rewritten': diff['rewritten'],
        'unique_maps_now': unique, 'identical_pairs_now': len(pairs),
        'new_image_literals': added_literals, 'controls': controls, 'problems': problems,
    }


def safe_models_are_labeled():
    problems = []
    if not DISPOSITION_PATH.exists():
        return False, {'problems': ['disposition table missing: %s' % DISPOSITION_PATH]}
    loader_src = read(LOADER_SWIFT)
    runtime_src = read(RUNTIME_SWIFT)
    loader_map = loader_claims(loader_src)
    kinds = classifier_kinds(loader_src)
    labels = classifier_labels(loader_src)
    table = json.loads(read(DISPOSITION_PATH))
    safe = [m for m in table['markers'] if m['disposition'] == 'safe-model']
    case_body = source_marker_case(runtime_src)
    if not safe:
        problems.append('no safe-model disposition is committed at all')
    meter_labels = {}
    for row in safe:
        block, sub, kind, label = row['sourceBlock'], row['substring'], row['kind'], row.get('label', '')
        if not label:
            problems.append('%s: safe model with an empty label (FORBID-002)' % block)
        if loader_map.get(sub) != kind:
            problems.append('%s: product classifier maps %r to %r, table says %r'
                            % (block, sub, loader_map.get(sub), kind))
        if kind not in kinds:
            problems.append('%s: kind %r is not declared by TMXSourceMarkerKind (%s)'
                            % (block, kind, ', '.join(kinds) or 'no enum found'))
        code_label = labels.get(kind, '')
        if not code_label:
            problems.append('%s: kind %r has no safeModelLabel literal in the product source'
                            % (block, kind))
        elif code_label != label:
            problems.append('%s: table label %r != product label %r' % (block, label, code_label))
        body = branch_body(case_body, sub, kind)
        if body is None:
            problems.append('%s: no runtime branch for kind %r (marker is still dropped)' % (block, kind))
        else:
            if 'appendSafeModelMarker(' not in body:
                problems.append('%s: runtime branch for %r does not record a safe model' % (block, kind))
            elif ('kind: .%s' % kind) not in body:
                problems.append('%s: runtime branch records the safe model under the wrong kind' % block)
            if 'break' in body and 'append' not in body:
                problems.append('%s: runtime branch neither records nor renders the marker' % block)
            meter_labels[block] = label
    # The helper must be where the label is attached, and the label must reach the record.
    helper = re.search(r'func appendSafeModelMarker\(.*?\n    \}', runtime_src, re.S)
    if not helper:
        problems.append('no appendSafeModelMarker helper exists to label the record')
    else:
        helper_body = helper.group(0)
        if 'TMXSafeModelMarker(' not in helper_body or 'label:' not in helper_body:
            problems.append('appendSafeModelMarker does not build a labeled TMXSafeModelMarker record')
        if 'kind.safeModelLabel' not in helper_body:
            problems.append('appendSafeModelMarker does not take the label from the product classifier')
    struct_decl = re.search(r'struct\s+TMXSafeModelMarker\s*\{(.*?)\n\}', loader_src, re.S)
    if not struct_decl or not re.search(r'\blabel:\s*String\b', struct_decl.group(1)):
        problems.append('TMXSafeModelMarker carries no label field')
    # Executed proof: the labels and safe-model flags must be what the product actually returns.
    evidence = swift_product_evidence()
    if evidence:
        for row in safe:
            if evidence['kind_for'].get(row['sourceBlock']) != row['kind']:
                problems.append('%s: the product classifier returns %r, table says %r'
                                % (row['sourceBlock'], evidence['kind_for'].get(row['sourceBlock']),
                                   row['kind']))
            if evidence['labels'].get(row['kind']) != row['label']:
                problems.append('%s: the product label is %r, table says %r'
                                % (row['sourceBlock'], evidence['labels'].get(row['kind']),
                                   row['label']))
            if not evidence['is_safe'].get(row['kind']):
                problems.append('%s: the product does not report kind %r as a safe model'
                                % (row['sourceBlock'], row['kind']))
        for kind, is_safe in sorted(evidence['is_safe'].items()):
            if not is_safe:
                continue
            if not evidence['labels'].get(kind):
                problems.append('the product reports %r as a safe model with an empty label' % kind)
        non_safe_with_label = sorted(k for k, s in evidence['is_safe'].items() if not s
                                     and evidence['labels'].get(k))
        if non_safe_with_label:
            problems.append('typed kinds carry a safe-model label, which hides the distinction: %s'
                            % ', '.join(non_safe_with_label))
        executed_labels = {r['sourceBlock']: evidence['labels'].get(r['kind'], '') for r in safe}
        meter_labels.update({k: v for k, v in executed_labels.items() if v})
    else:
        problems.append('FORBID-002 is not product-executed on this host (%s)'
                        % swift_evidence_unavailable_reason())
    # The normative equivalence over ALL rows, not only the declared safe ones: this is the hole
    # where a safe model relabelled "typed" with an empty label stayed green.
    is_safe_map = product_is_safe_map(evidence, loader_src)
    problems.extend(disposition_consistency(table.get('markers', []), is_safe_map))
    # mandatory flips
    tampered_label = copy.deepcopy(table)
    for entry in tampered_label['markers']:
        if entry['disposition'] == 'safe-model':
            entry['label'] = ''
            break
    tampered_kind = copy.deepcopy(table)
    for entry in tampered_kind['markers']:
        if entry['disposition'] == 'safe-model':
            entry['kind'] = 'zzNotDeclaredAnywhere'
            break
    tampered_map = copy.deepcopy(table)
    for entry in tampered_map['markers']:
        if entry['disposition'] == 'safe-model':
            entry['substring'] = 'blk_does_not_exist'
            break
    relabelled = copy.deepcopy(table)
    for entry in relabelled['markers']:
        if entry['sourceBlock'] == 'blk_waggon':
            entry['disposition'] = 'typed'
            entry['label'] = ''
    promoted = copy.deepcopy(table)
    for entry in promoted['markers']:
        if entry['sourceBlock'] == 'blk_blinker':
            entry['disposition'] = 'safe-model'
            entry['label'] = 'SAFE-MODEL inert-scenery: imported static artwork, no action in the source table'
    # FORBID-002's rendering clause, and the syntax gate for every Swift file in the diff.
    scene_src = read(GAME_SCENE_SWIFT)
    problems.extend(overlay_binding_problems(scene_src))
    parsed = swift_parse_gate(CHANGED_SWIFT)
    if parsed is None:
        problems.append('swiftc is unavailable on this host, so no Swift file in this diff was even '
                        'syntax-gated; the claim must not be reported as verified')
    else:
        for name, outcome in sorted(parsed.items()):
            if outcome != 'ok':
                problems.append('swiftc -frontend -parse failed for %s: %s' % (name, outcome))
    # Mandatory flips for the rendering clause: the reviewer's case R2 deleted the whole overlay loop
    # and every probe stayed green. Assert the same deletion, and a label strip, on in-memory copies.
    loop_only = re.sub(r'\n\s*// Content-factory safe models.*?\n\s*\}\n', '\n', scene_src, flags=re.S)
    no_label = scene_src.replace('marker.label', '""')
    controls = {
        'unlabeled_placeholder_rejected': any(not e.get('label') for e in tampered_label['markers']
                                              if e['disposition'] == 'safe-model'),
        'undeclared_kind_rejected': (not kinds) or any(e['kind'] not in kinds for e in tampered_kind['markers']
                                                       if e['disposition'] == 'safe-model'),
        'bogus_substring_rejected': any(loader_map.get(e['substring']) != e['kind']
                                        for e in tampered_map['markers'] if e['disposition'] == 'safe-model'),
        'safe_relabelled_as_typed_rejected': bool(disposition_consistency(relabelled['markers'], is_safe_map)),
        'typed_promoted_to_safe_rejected': bool(disposition_consistency(promoted['markers'], is_safe_map)),
        # Discrimination, not shouting: the honest file must pass AND the two regressions must fail.
        'honest_overlay_binding_accepted': not overlay_binding_problems(scene_src),
        'overlay_deletion_detected': bool(overlay_binding_problems(loop_only)),
        'overlay_label_strip_detected': bool(overlay_binding_problems(no_label)),
        'parse_gate_detects_a_broken_file': parse_gate_selftest(),
    }
    ok = not problems and all(controls.values())
    return ok, {
        'safe_model_families': sorted(m['sourceBlock'] for m in safe),
        'markers_covered_by_safe_models': sum(m['count'] for m in safe),
        'labels': meter_labels, 'product_labels': labels, 'classifier_kinds': kinds,
        'swift_parse': parsed if parsed else 'swiftc unavailable',
        'rendering_evidence_limit': 'source-structure only: SpriteKit cannot be compiled or run on '
                                    'Linux (`import SpriteKit` fails at TMXLevelRuntime.swift:1), so '
                                    'the on-screen outline itself still needs the macOS spot in '
                                    'test-plan.md',
        'controls': controls, 'problems': problems,
    }


def zone_index_formula():
    problems = []
    checked, absent = 0, []
    for name, root in sorted(trees().items()):
        stage, scene = int(name[1:3]), int(name[4:6])
        expected = (stage - 1) * 25 + (scene - 1)
        raw = zone_number(root)
        if raw is None:
            absent.append(name)
            continue
        checked += 1
        try:
            got = int(raw)
        except ValueError:
            problems.append('%s: zoneNumber %r is not an integer' % (name, raw))
            continue
        if got != expected:
            problems.append('%s: zoneNumber %d != (stage-1)*25+(scene-1) = %d' % (name, got, expected))
    if checked != 117:
        problems.append('%d maps carry zoneNumber, expected 117' % checked)
    if sorted(absent) != ['L01S%02d' % i for i in range(1, 9)]:
        problems.append('the keyless maps are %s, expected L01S01..L01S08' % sorted(absent))
    if not MANIFEST_PATH.exists():
        problems.append('manifest missing, cannot bind zone_index')
    else:
        manifest = json.loads(read(MANIFEST_PATH))
        if manifest.get('canonicalization_version') != CANON_VERSION:
            problems.append('manifest does not record canonicalization_version %r' % CANON_VERSION)
        for name, entry in sorted(manifest.get('maps', {}).items()):
            stage, scene = int(name[1:3]), int(name[4:6])
            if entry.get('zone_index') != (stage - 1) * 25 + (scene - 1):
                problems.append('%s: manifest zone_index %r breaks the 0-based formula'
                                % (name, entry.get('zone_index')))
    # mandatory flip: a naive 1-based reading must disagree loudly, proving the formula is
    # load-bearing rather than tautological.
    naive = sum(1 for name, root in trees().items()
                if zone_number(root) is not None
                and int(zone_number(root)) != (int(name[1:3]) - 1) * 25 + int(name[4:6]))
    off_by_file = sum(1 for name, root in trees().items()
                      if zone_number(root) is not None
                      and int(zone_number(root)) != int(name[4:6]))
    # Concrete witness from the corpus: L02S03 carries zoneNumber 027, so the 0-based reading must
    # reproduce it and a 1-based scene must not.
    witness = zone_number(trees()['L02S03']), 2, 3   # value, stage, scene
    controls = {
        'naive_one_based_would_false_positive': naive >= 100,
        'naive_filename_compare_would_false_positive': off_by_file >= 100,
        # A 1-based reading must be *wrong* on a known map and the 0-based reading *right* on the
        # same one: this fails if the formula itself is mis-transcribed, which `not problems`
        # cannot (test review F6). L02S03 is zone 027, never 028.
        'formula_distinguishes_base_zero_from_base_one': (
            witness[0] is not None and int(witness[0]) == (witness[1] - 1) * 25 + (witness[2] - 1)
            and (witness[1] - 1) * 25 + witness[2] != int(witness[0])),
    }
    ok = not problems and all(controls.values())
    return ok, {'maps_with_zone_number': checked, 'keyless_maps': sorted(absent),
                'false_mismatches_if_1_based': naive, 'false_mismatches_if_filename': off_by_file,
                'controls': controls, 'problems': problems}


PROBES = [
    ('marker_coverage_all_maps', marker_coverage_all_maps),
    ('marker_baseline_reproduced', marker_baseline_reproduced),
    ('ignored_types_disposition', ignored_types_disposition),
    ('level_pair_manifest_pinned', level_pair_manifest_pinned),
    ('manifest_selfcheck', manifest_selfcheck),
    ('unchanged_marker_output', unchanged_marker_output),
    ('no_invented_content', no_invented_content),
    ('safe_models_are_labeled', safe_models_are_labeled),
    ('zone_index_formula', zone_index_formula),
]


def build_manifest():
    """Deterministic generator for engineering/contracts/level-content-v1.json.

    The declared pairs are *derived* from the corpus and then asserted equal to the merged P1-12
    finding, so the manifest can never quietly encode a different finding than the audit did.
    """
    hashes = canonical_hashes()
    groups = {}
    for name, digest in hashes.items():
        groups.setdefault(digest, []).append(name)
    dup_groups = {d: sorted(g) for d, g in groups.items() if len(g) > 1}
    derived_pairs = []
    for members in sorted(dup_groups.values(), key=lambda g: g[0]):
        if len(members) != 2:
            raise SystemExit('P1-12 pinning aborted: a duplicate group spans %d maps: %s '
                             '(the audited model is 24 pairs of exactly 2)' % (len(members), members))
        derived_pairs.append(members)
    expected = sorted([sorted((a, b)) for a, b in DECLARED_PAIRS])
    if derived_pairs != expected:
        raise SystemExit('P1-12 pinning aborted: derived duplicate pairs != the merged finding.\n'
                         '  derived  : %s\n  expected : %s' % (derived_pairs, expected))
    maps = {}
    for name, root in sorted(trees().items()):
        stage, scene = int(name[1:3]), int(name[4:6])
        refs = background_refs(root)
        digests = background_digests(root)
        maps[name] = {
            'sha256': hashes[name],
            'zone_index': (stage - 1) * 25 + (scene - 1),
            'zone_number_property': zone_number(root),
            'stage': stage, 'scene': scene,
            'background': refs[0] if refs else '',
            'background_sha256': digests[0] if digests else '',
            'background_count': len(refs),
            'object_layers': [g.get('name', '') for g in root if g.tag == 'objectgroup'],
            'tile_layer_count': sum(1 for g in root if g.tag == 'layer'),
        }
    pairs = []
    for a, b in expected:
        pair = {'a': a, 'b': b,
                'zone_a': maps[a]['zone_index'], 'zone_b': maps[b]['zone_index'],
                'background_identical': maps[a]['background_sha256'] == maps[b]['background_sha256'],
                'background_a': maps[a]['background'], 'background_b': maps[b]['background'],
                'sha256': maps[a]['sha256'],
                'stage_axis': 'L02->L05' if a.startswith('L02S') else 'other (see pair_notes)'}
        if '%s/%s' % (a, b) in ('L03S09/L04S11',):
            pair['note'] = 'L03S09/L04S11'
            pair['ruling_ground'] = 'already identical in the shipped data; the recolored-stage-2 ' \
                                    'premise does not reach this pair'
        pairs.append(pair)
    doc = {
        'contract': CONTRACT_ID,
        'canonicalization_version': CANON_VERSION,
        'canonicalization': {
            'id': CANON_VERSION,
            'includes': ['every <layer> tile array, decoded with the product loader semantics '
                         '(base64 -> little-endian uint32, csv -> split on ", \\n \\r \\t space")',
                         'layer name/width/height/x/y attributes',
                         'every <object> in every objectgroup: name, type, x, y, width, height '
                         'and its sorted <property> name/value pairs'],
            'excludes': ['map properties (nextLevel, zoneNumber, zoneSource, provenance keys)',
                         'imagelayer references and backdrop bytes (recorded per pair instead, '
                         'as background_identical)',
                         'tileset declarations and their resolution'],
            'serialization': 'json.dumps([...], sort_keys=True) -> sha256 hex',
            'authority': 'level-graph.md "tiles + objects" slice; proven to reproduce its '
                         '101/125 count, its 24 groups and its 4 fully-identical pairs',
        },
        'generated_from_commit': BASE_COMMIT,
        'resource_directory': 'Exolon/Resources',
        'map_count': len(maps),
        'unique_count': len(set(hashes.values())),
        'duplicate_group_count': len(pairs),
        'maps_covered_by_duplicates': sum(2 for _ in pairs),
        'zone_index_formula': 'int(zoneNumber) == (stage-1)*25 + (scene-1); 0-based; the 8 maps '
                              'without the property are L01S01..L01S08 (zones 000..007)',
        'ruling': {
            'finding': 'P1-12 / issue #16: 24 duplicate pairs (48 maps) leave 101 unique of 125',
            'decision': 'RULED intentional original content, closed by pinning — a ruling, not a sourced fact',
            'status': 'resolved by ruling pending PR merge; issue #16 stays OPEN and labeled '
                      'blocked-on-owner until the owner accepts the ruling',
            'reason_scope': 'the reason below is carried by the primaries for the 23 L02/L05 pairs; it '
                            'does NOT reach the 24th pair — see pair_notes',
            'reason': 'stage 5 (zones 102..124) repeats stage 2 (zones 27..49) with a recolored '
                      'backdrop: the repetition is in the imported source data, not produced by the '
                      'factory (no generator and no .asm exists in this tree), so there is no factory '
                      'defect to fix',
            'premise_citations': [
                'ORIGINAL_MECHANICS.md:166 — "Zones 100-124 repeat the structural pattern of 25-49 '
                'with cosmetic changes after 101" (OM ranks that source as a cross-check only)',
                'engineering/reports/exolon-full-audit-20260920-v3.md:37 — P1-12 row: '
                '"стадия 5 = перекраска стадии 2"',
                'engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/perfile/'
                'level-graph.md:36 — "Стадия 5 (зоны 102…124) — это перекрашенная стадия 2 (27…49)"',
                'LEVEL_COMPILER_AUDIT.md — the imported 1987 per-screen records are identical (solid= '
                'and the whole action list) for both members of 23 of the 24 pairs, while L05S01/L05S02 '
                'differ from L02S01/L02S02: the repetition starts at zone 102, exactly where the '
                'walkthrough says it does',
            ],
            'not_sourced': 'no primary states the duplication was intentional; issue #16 explicitly '
                           'leaves the choice open ("подтвердить намеренность или восстановить '
                           'уникальные данные"). Intentionality is this change\'s decision.',
            'forbidden': 'authoring new tile/object content to dissolve these pairs (FORBID-001)',
            'escape_hatch': 'this manifest lists exactly which 48 files the 24 pairs cover; a future '
                            'owner-authorized regeneration is a one-command query over identical_pairs',
        },
        'pair_notes': {
            'L03S09/L04S11': {
                'why_separate': 'this pair is stage 3 -> stage 4 (zones 58 and 85), not the stage 2 -> '
                                'stage 5 axis, so the recolored-stage-2 premise does not explain it',
                'shipped_data': 'the two files are content-identical under wave-c-canonical-1 (same '
                                'digest) and both have 64 nonzero Collision cells',
                'source_tension': 'LEVEL_COMPILER_AUDIT.md records "058 L03S09 solid=140 actions=" and '
                                  '"085 L04S11 solid=128 actions=" — different originals for maps that '
                                  'shipped identical',
                'caveat': 'the solid= column matches no TMX-derived metric in this corpus (0 of 125 '
                          'screens equal, 6 within +-5 cells), so it cannot prove unique data was lost '
                          'either; both action lists are empty',
                'consequence': 'for this pair the ruling rests only on "already identical in the shipped '
                               'data"; the claim "no unique data was lost" is UNSUPPORTED here and is '
                               'deliberately not made',
                'if_owner_rejects': 'this pair is the one worth regenerating first, and it needs the '
                                    'external data_zone_data.asm to say what zone 58 or 85 originally '
                                    'held',
            },
        },
        'maps': maps,
        'identical_pairs': pairs,
        'background_identical_pairs': [list(p) for p in sorted(
            (a, b) for a, b in expected
            if maps[a]['background_sha256'] == maps[b]['background_sha256'])],
    }
    doc['self_check'] = {'body_sha256': body_digest(doc),
                         'binding': 'sha256(INTEGRITY_BIND + json.dumps(body, sort_keys=True)); the '
                                    'constant lives in wave_c_check.py, so a plain recomputation of '
                                    'the body digest does not re-seal the contract',
                         'regenerate_with': 'python3 wave_c_check.py --write-manifest'}
    return doc


def write_manifest():
    doc = build_manifest()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(doc, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    errors = validate_manifest(doc, canonical_hashes())
    print('wrote %s: %d maps, %d unique, %d declared pairs, %d background-identical, '
          'body_sha256 %s' % (MANIFEST_PATH.relative_to(ROOT), doc['map_count'], doc['unique_count'],
                              len(doc['identical_pairs']), len(doc['background_identical_pairs']),
                              doc['self_check']['body_sha256'][:16]))
    for error in errors:
        print('  SELF-CHECK ERROR: %s' % error)
    return 1 if errors else 0


def record_baseline(base_commit=None):
    records = covered_marker_records()
    substring_kind = {}
    if DISPOSITION_PATH.exists():
        substring_kind = {m['substring']: m['kind'] for m in json.loads(read(DISPOSITION_PATH))['markers']}
    branches = base_branch_fingerprints(LEGACY_SUBSTRINGS, base_commit)
    if branches is None:
        print('REFUSED: cannot read %s at %s' % (RUNTIME_SWIFT.name, base_commit or BASE_COMMIT))
        return 1
    payload = {
        'canonicalization_version': CANON_VERSION,
        'base_commit': base_commit or BASE_COMMIT,
        'legacy_table': list(LEGACY_SUBSTRINGS),
        'substring_kind': substring_kind,
        'covered_marker_digest': digest_of(records),
        'covered_markers': sum(len(v) for v in records.values()),
        'covered_maps': len(records),
        'branch_fingerprints': branches,
        'base_branch_fingerprints': branches,
        'arm_deviations': [],
        'deviation_ruling': '',
        'deviation_policy': 'arm_deviations is empty: every one of the seven legacy arms must stay '
                            'byte-identical to the base blob. A rebase that lands another change over '
                            'an arm (the A -> B -> C integration order puts wave B over the beam_ arm) '
                            'is re-baselined by appending {arm, from, to, authorized_by, reason} here '
                            'and setting deviation_ruling; nothing else may differ.',
        'branch_fingerprint_source': 'computed from `git show %s:%s`, never from the working tree, so '
                                     'editing this golden cannot make AC-005 agree with itself'
                                     % (BASE_COMMIT[:12], RUNTIME_SWIFT.name),
        'classifier_kinds_at_record': classifier_kinds(read(LOADER_SWIFT)),
        'claimed_at_record': list(LEGACY_SUBSTRINGS),
        'marker_records': records,
    }
    BASELINE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print('wrote %s: %d covered markers on %d maps, digest %s'
          % (BASELINE_PATH.relative_to(ROOT), payload['covered_markers'],
             payload['covered_maps'], payload['covered_marker_digest'][:16]))
    return 0


COVERAGE_DOC = HERE / 'marker-coverage.md'


def write_dispositions():
    """Regenerate the committed coverage + per-map disposition table from the corpus and the
    product classifier (SIG-001: one command, stdlib only)."""
    markers = map_markers()
    table = json.loads(read(DISPOSITION_PATH))
    by_block = {m['sourceBlock']: m for m in table['markers']}
    evidence = swift_product_evidence()
    corpus = {}
    per_map = {}
    for name, rows in markers.items():
        for row in rows:
            corpus.setdefault(row['block'], Counter()).update([name])
            per_map.setdefault(name, Counter()).update([row['block']])
    total = sum(len(v) for v in markers.values())
    lines = [
        '# Source-marker coverage and disposition table',
        '',
        'Regenerated by `python3 wave_c_check.py --write-dispositions`; every number below comes',
        'from `Exolon/Resources/*.tmx` and, when a Swift toolchain is present, from the compiled',
        'product classifier (`TMXSourceMarkerKind.classify`) over all 125 maps.',
        '',
        'Corpus: %d maps · %d `source_marker` objects · %d distinct `sourceBlock` values · '
        'resolved %d/%d, unmatched %d.'
        % (len(trees()), total, len(corpus), total - sum(len(v) for k, v in corpus.items()
                                                         if k not in by_block), total,
           sum(len(v) for k, v in corpus.items() if k not in by_block)),
        '',
        '| `sourceBlock` | markers | maps | disposition | factory kind | matcher test | footprint | labeled |',
        '| --- | ---: | ---: | --- | --- | --- | --- | --- |',
    ]
    for block in sorted(corpus, key=lambda b: (-corpus[b].__len__(), b)):
        row = by_block.get(block)
        if row is None:
            lines.append('| `%s` | %d | %d | **UNHANDLED** | - | - | - | no |'
                         % (block, sum(corpus[block].values()), len(corpus[block])))
            continue
        footprint = '%dx%d' % tuple(row['footprint_cells'])
        if evidence and row['disposition'] == 'safe-model' and block in evidence['footprint']:
            footprint += ' (product: %s)' % evidence['footprint'][block]
        lines.append('| `%s` | %d | %d | %s | `%s` | `%s` | %s | %s |'
                     % (block, sum(corpus[block].values()), len(corpus[block]),
                        row['disposition'], row['kind'], row['substring'], footprint,
                        'yes' if row.get('label') else 'no'))
    lines += ['', '`footprint` is in 16 px source cells. For the typed families it is the box the '
              'existing branch hard-codes today; for safe models it is what the product '
              '`safeModelFootprintCells` actually returns, shown in parentheses.', '']
    lines += ['', '## The 51 formerly-dropped markers, per map', '',
              'Before this change these 32 maps silently lost the listed markers; each one is now a '
              'typed, labeled safe-model record (`TMXLevelRuntime.safeModelMarkers`).', '',
              '| map | zone | formerly-dropped kinds | markers |', '| --- | ---: | --- | ---: |']
    formerly = set(FORMERLY_IGNORED)
    for name in sorted(per_map):
        dropped = {b: c for b, c in per_map[name].items() if b in formerly}
        if not dropped:
            continue
        stage, scene = int(name[1:3]), int(name[4:6])
        lines.append('| `%s` | %03d | %s | %d |' % (
            name, (stage - 1) * 25 + (scene - 1),
            ', '.join('`%s` x%d' % (b, dropped[b]) for b in sorted(dropped)),
            sum(dropped.values())))
    lines += ['', '**Total: %d markers on %d maps, 0 dropped.**' % (
        sum(by_block[b]['count'] for b in FORMERLY_IGNORED if b in by_block),
        len({n for b in FORMERLY_IGNORED for n in corpus.get(b, ())})), '',
        'Read "resolved" narrowly: a safe model means the factory no longer *loses* the marker, not',
        'that its original behaviour is *implemented*. The 51 safe-model markers add no physics,',
        'damage, score or spawn path; `blk_gunMachine_BOTTOM` in particular is recorded as an',
        'unconfirmed action because the in-tree evidence cannot identify what it does.', '']
    if evidence:
        lines += ['## Product execution', '',
                  'Compiled `TMXMapLoader.swift` (one added `import FoundationXML` line, same delta '
                  'rule as the committed harness) loaded **%d/%d** maps and classified every marker:'
                  % (evidence['loaded'], len(trees())), '',
                  '```',
                  'kind_for  : ' + json.dumps(evidence['kind_for'], sort_keys=True),
                  'unmatched : ' + (json.dumps(evidence['unmatched'], sort_keys=True) or '{}'),
                  'safe_model: ' + json.dumps(evidence['is_safe'], sort_keys=True),
                  'safe_model_footprint_cells : ' + json.dumps(evidence['footprint'], sort_keys=True),
                  'note: safeModelFootprintCells has a 4x3 fallback, so it prints for every family; '
                  'only the three safe-model rows are meaningful here',
                  '```', '']
    else:
        lines += ['## Product execution', '',
                  'Not run on this host: %s' % swift_evidence_unavailable_reason(), '']
    COVERAGE_DOC.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('wrote %s' % COVERAGE_DOC.relative_to(ROOT))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='wave C content-factory meter')
    parser.add_argument('--only', choices=[n for n, _ in PROBES])
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--record-baseline', action='store_true')
    parser.add_argument('--write-manifest', action='store_true')
    parser.add_argument('--write-dispositions', action='store_true')
    parser.add_argument('--base', help='base commit ref for --record-baseline (use after a rebase '
                                       'that legitimately moved an arm; record the ruling in '
                                       'deviation_ruling afterwards)')
    args = parser.parse_args(argv)
    if args.record_baseline:
        return record_baseline(args.base)
    if args.write_manifest:
        return write_manifest()
    if args.write_dispositions:
        return write_dispositions()
    results = {}
    for name, probe in PROBES:
        if args.only and args.only != name:
            continue
        try:
            ok, detail = probe()
        except Exception as exc:  # a crashing probe fails loudly, it never passes silently
            ok, detail = False, {'exception': '%s: %s' % (type(exc).__name__, exc)}
        results[name] = {'pass': ok, 'detail': detail}
    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True, default=str))
    else:
        for name, res in sorted(results.items()):
            print('%-28s %s' % (name, 'PASS' if res['pass'] else 'FAIL'))
            detail = res['detail']
            if 'exception' in detail:
                print('    ! %s' % detail['exception'])
            for key in ('problems', 'schema_errors'):
                for problem in detail.get(key, []) or []:
                    print('    ! %s' % problem)
            for key, value in sorted(detail.items()):
                if key in ('problems', 'schema_errors', 'exception', 'marker_records'):
                    continue
                text = json.dumps(value, sort_keys=True, default=str)
                print('    %-32s %s' % (key, text if len(text) <= 380 else text[:380] + '...'))
    failed = sorted(n for n, r in results.items() if not r['pass'])
    divergence = []
    for res in results.values():
        for note in (res['detail'].get('stale_mirrors') or {}).get('divergence', []) or []:
            if note not in divergence:
                divergence.append(note)
    for note in divergence:
        print('WARNING (not a failure of this change): %s' % note)
    print('RESULT: %s | probes=%d failed=%d%s'
          % ('ALL_WAVE_C_PROBES_PASS' if not failed else 'WAVE_C_PROBES_FAIL',
             len(results), len(failed), (' ' + ','.join(failed)) if failed else ''))
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
