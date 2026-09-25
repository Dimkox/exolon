#!/usr/bin/env python3
"""Self-checking verifier for the wave-A gameplay event log and the four state-machine fixes.

Typed authority: `../change-spec.yaml`. Every `test` path named there resolves to a function in
this file, so the stack recorder binds real evidence, not prose.

Method (the discipline this repo already uses in `release_layer_check.py` and
`v3_measurements.py`): a check is only worth its green if it can be made to fail. Every judgment
here therefore runs against artifacts this script produces itself by invoking
`harness/run.sh`, and every structural check carries a contradictory control that must flip.

Style rules it enforces (integration_architect section 10): predicates are **causal**, never
absolute-tick assertions - there are 16 unseeded `Int.random` sites in the gameplay code, so two
runs of the same script do not produce the same tick numbers.

Usage:
    python3 gameplay_log_check.py                 # build, run the harness, check everything
    python3 gameplay_log_check.py --artifacts DIR # reuse an existing artifact directory
    python3 gameplay_log_check.py --list
    python3 gameplay_log_check.py --only stream_invariants,ts_us_derivation
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CHANGE = HERE.parent
SCHEMA_PATH = ROOT / 'engineering' / 'contracts' / 'schemas' / 'gameplay-event-v1.schema.json'
# Filled in by main(): contract.txt is written next to the streams, never inside the clone.
ARTIFACT_DIR = None
RUN_SH = CHANGE / 'evidence' / 'harness' / 'run.sh'
PRODUCT = ROOT / 'Exolon'
DIAGNOSTICS = PRODUCT / 'GameCore' / 'Diagnostics'
LOG_CORE = (DIAGNOSTICS / 'GameplayEventLog.swift').read_text(encoding='utf-8')
SINK_CORE = (DIAGNOSTICS / 'GameplayEventSink.swift').read_text(encoding='utf-8')
PROJECT = PRODUCT.parent / 'Exolon.xcodeproj' / 'project.pbxproj'
SCHEME = PRODUCT.parent / 'Exolon.xcodeproj' / 'xcshareddata' / 'xcschemes' / 'Exolon.xcscheme'

# The files this change adds. Every one of them must be registered in the Xcode project.
NEW_SWIFT_FILES = [
    'GameplayEventSink.swift',
    'GameplayEventLog.swift',
    'FixedTickDriver.swift',
    'StageBoundaryLedger.swift',
    'LauncherBonusState.swift',
]

# Envelope order is normative (integration section 4); a byte-level test can compare whole lines.
ENVELOPE = ['schema_version', 'seq', 'tick', 'frame', 'rot', 'ts_us', 'name']
ENVELOPE_SET = set(ENVELOPE)
# FORBID-003: the only fields allowed to carry free-form text, and only in log.begin.
# Free-form fields the frozen catalog itself declares. `log.rotate.from_path`/`to_path` are
# filesystem identifiers of the log, same class as `log.begin.path`; the check still pins their
# shape (absolute, .jsonl) and rejects them on any other record.
EXEMPT_TEXT_FIELDS = {'run_id', 'build', 'wall_utc', 'path', 'seed', 'from_path', 'to_path'}
STEP_BUDGET = 15  # floor(maximumFrameTime / fixedTimeStep) = floor(0.25 / (1/60))
STAGE_END_ZONES = (24, 49, 74, 99, 124)
SCREEN_EXIT_X_Q = 510 * 4  # state.zone_exit.player_x is a quarter-pixel lane
REALTIME_WORST_CASE_EV_PER_S = 3_600  # 60 events/step x 60 steps/s (architect M11 arithmetic)
SWIFTC = os.environ.get('SWIFTC', '/opt/swift/usr/bin/swiftc')
# Files this change touched. The SpriteKit-bound ones are not compiled by the Linux gate, so they
# get a parse gate here (review R-1: without it, 12 real syntax errors still passed 22/23).
SPRITEKIT_BOUND = ('Exolon/GameCore/GameScene.swift', 'Exolon/GameCore/Levels/TMXLevelRuntime.swift',
                   'Exolon/GameCore/Objects/LevelObstacles.swift', 'Exolon/Platform/macOS/AppDelegate.swift')
PRODUCER_FILES = ('Exolon/GameCore/GameScene.swift', 'Exolon/GameCore/Player/Player.swift',
                  'Exolon/GameCore/Levels/TMXLevelRuntime.swift',
                  'Exolon/GameCore/Objects/LevelObstacles.swift',
                  'Exolon/GameCore/Diagnostics/FixedTickDriver.swift')


class CheckFailure(AssertionError):
    """Raised by a check (or by one of its controls) when the evidence does not hold."""


@dataclass
class Stream:
    """One (run_id, rot) JSON-lines stream plus the scenario that produced it."""

    name: str
    path: Path
    records: list = field(default_factory=list)

    def by_name(self, name):
        return [r for r in self.records if r.get('name') == name]

    @property
    def ticks(self):
        return [r for r in self.records if r.get('tick', 0) > 0]


def load_streams(artifacts: Path) -> dict:
    """Every scenario file, keyed by a stable stem, with rotations concatenated in order."""
    streams = {}
    for variant in sorted(p for p in artifacts.iterdir() if p.is_dir()):
        for path in sorted(variant.glob('*.jsonl')):
            stem = re.sub(r'-[0-9a-f]{16}-\d+\.jsonl$', '', path.name)
            key = f'{variant.name}/{stem}'
            records = []
            with path.open(encoding='utf-8') as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    records.append(json.loads(line))  # AC-001: stdlib json must parse every line
            streams.setdefault(key, []).append((path, records))
    ordered = {}
    for key, parts in streams.items():
        parts.sort(key=lambda item: int(re.search(r'-(\d+)\.jsonl$', item[0].name).group(1)))
        merged = Stream(name=key, path=parts[0][0])
        for _, records in parts:
            merged.records.extend(records)
        ordered[key] = merged
    return ordered


def fixed_stream(artifacts: Path, stem: str) -> Stream:
    streams = load_streams(artifacts)
    key = f'fixed/{stem}'
    if key not in streams:
        raise CheckFailure(f'missing artifact stream {key}; have {sorted(streams)}')
    return streams[key]


def variant_stream(artifacts: Path, variant: str, stem: str) -> Stream:
    streams = load_streams(artifacts)
    key = f'{variant}/{stem}'
    if key not in streams:
        raise CheckFailure(f'missing artifact stream {key}; have {sorted(streams)}')
    return streams[key]


def manifest(artifacts: Path) -> dict:
    path = artifacts / 'fixed' / 'manifest.json'
    if not path.is_file():
        raise CheckFailure(f'harness manifest missing at {path}')
    return json.loads(path.read_text(encoding='utf-8'))


def extras_for(artifacts: Path, scenario: str) -> list:
    entries = manifest(artifacts).get('scenarios', {}).get(scenario, [])
    return [entry for entry in entries if '=' in entry]


def _write_if_changed(path: Path, text: str):
    """Idempotent evidence write: identical content leaves the file (and the tree fingerprint) alone."""
    if path.is_file() and path.read_text(encoding='utf-8') == text:
        return False
    path.write_text(text, encoding='utf-8')
    return True


def numeric(extras: list, key: str) -> float:
    for entry in extras:
        name, _, value = entry.partition('=')
        if name == key:
            return float(value)
    raise CheckFailure(f'{key} not reported in {extras}')


# ---------------------------------------------------------------------------
# JSON-Schema subset validator (stdlib only, for the frozen contract file).
# Supported: type, enum, const, minimum, maximum, pattern, required, properties,
# additionalProperties, items, allOf, if/then, x-* annotations are ignored.
# ---------------------------------------------------------------------------

def matches_type(value, expected):
    if expected == 'integer':
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == 'number':
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == 'boolean':
        return isinstance(value, bool)
    if expected == 'string':
        return isinstance(value, str)
    if expected == 'object':
        return isinstance(value, dict)
    if expected == 'array':
        return isinstance(value, list)
    return True


def validate(record, schema, path='record'):
    problems = []
    for keyword in ('type', 'enum', 'const', 'minimum', 'maximum', 'pattern'):
        if keyword not in schema:
            continue
        problems.extend(validate_leaf(record, schema, keyword, path))
    if 'allOf' in schema:
        for index, sub in enumerate(schema['allOf']):
            problems.extend(validate(record, sub, f'{path}/allOf[{index}]'))
    if '$ref' in schema:
        problems.extend(validate(record, resolve_ref(schema['$ref']), path))
    if isinstance(record, dict):
        for key in schema.get('required', []):
            if key not in record:
                problems.append(f'{path}: missing required {key!r}')
        for key, sub in schema.get('properties', {}).items():
            if key in record:
                problems.extend(validate(record[key], sub, f'{path}.{key}'))
        if schema.get('additionalProperties') is False:
            allowed = set(schema.get('properties', {}))
            for key in record:
                if key not in allowed:
                    problems.append(f'{path}: unexpected property {key!r}')
    if isinstance(record, list) and 'items' in schema:
        for index, item in enumerate(record):
            problems.extend(validate(item, schema['items'], f'{path}[{index}]'))
    if 'if' in schema and _conditional_applies(record, schema['if']):
        problems.extend(validate(record, schema.get('then', {}), f'{path}/then'))
    return problems


def _conditional_applies(candidate, condition):
    if 'properties' in condition:
        for key, sub in condition['properties'].items():
            if not isinstance(candidate, dict) or key not in candidate:
                return False
            if validate(candidate[key], {k: v for k, v in sub.items() if not k.startswith('x-')}, key):
                return False
        for key in condition.get('required', []):
            if not isinstance(candidate, dict) or key not in candidate:
                return False
        return True
    if 'required' in condition:
        return all(isinstance(candidate, dict) and key in candidate for key in condition['required'])
    return True


def validate_leaf(value, schema, keyword, path):
    problems = []
    if keyword == 'type':
        expected = schema['type']
        expected_any = expected if isinstance(expected, list) else [expected]
        if not any(matches_type(value, item) for item in expected_any):
            problems.append(f'{path}: {value!r} is not {expected}')
    elif keyword == 'enum':
        if value not in schema['enum']:
            problems.append(f'{path}: {value!r} not in the frozen enum {schema["enum"]}')
    elif keyword == 'const':
        if value != schema['const']:
            problems.append(f'{path}: expected const {schema["const"]!r}, got {value!r}')
    elif keyword == 'minimum' and isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < schema['minimum']:
            problems.append(f'{path}: {value} < minimum {schema["minimum"]}')
    elif keyword == 'maximum' and isinstance(value, (int, float)) and not isinstance(value, bool):
        if value > schema['maximum']:
            problems.append(f'{path}: {value} > maximum {schema["maximum"]}')
    elif keyword == 'pattern' and isinstance(value, str):
        if not re.search(schema['pattern'], value):
            problems.append(f'{path}: {value!r} does not match {schema["pattern"]}')
    return problems


def resolve_ref(reference):
    node = SCHEMA
    for part in reference.lstrip('#/').split('/'):
        node = node[part]
    return node


SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))


def per_name_schemas():
    """name -> {required, properties} assembled from the schema's allOf blocks."""
    table = {}
    for block in SCHEMA.get('allOf', []):
        name = block['if']['properties']['name']['const']
        table[name] = block['then']
    return table


NAME_SCHEMAS = per_name_schemas()


def _without_comments(text):
    """Source with comments and doc comments stripped, so a grep gate cannot be satisfied - or
    tripped - by a sentence."""
    kept = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('//'):
            continue
        kept.append(line)
    return '\n'.join(kept)


def realtime_like_streams(artifacts):
    """Level-2 streams that model a running session: SIG-001's `no drops` rule cannot apply to the
    starvation scenario, whose whole purpose is a ring lap (`drops_are_counted` judges that one)."""
    return {key: stream for key, stream in gameplay_streams(artifacts).items()
            if 'drops' not in key}


def gameplay_streams(artifacts):
    """Streams that represent simulated gameplay. The contract sweep and the level-gating files
    carry synthetic payload values on purpose (they exist to make every name appear in a real
    file), so they are not evidence about gameplay invariants."""
    skip = ('contract', 'level0', 'cost-')
    return {key: stream for key, stream in load_streams(artifacts).items()
            if 'revert' not in key and not any(part in key for part in skip)}


def swift_source(relative):
    return (PRODUCT / relative).read_text(encoding='utf-8')


def contract_lines():
    """`contract.txt` is the harness's rendering of the Swift contract tables."""
    if ARTIFACT_DIR is None:
        raise CheckFailure('no artifact directory bound')
    path = Path(ARTIFACT_DIR) / 'fixed' / 'contract.txt'
    if not path.is_file():
        raise CheckFailure(f'{path} missing - the harness never wrote the contract dump')
    return [line.split('\t') for line in path.read_text(encoding='utf-8').splitlines() if line]


def swift_contract_kinds():
    kinds = {}
    for parts in contract_lines():
        if parts and parts[0] == 'kind':
            kinds[int(parts[1])] = {'name': parts[2], 'level': int(parts[3]), 'encode': parts[4]}
    return kinds


def swift_contract_domains():
    domains = {}
    for parts in contract_lines():
        if parts[0] == 'domain':
            domains.setdefault(parts[1], {})[int(parts[2])] = parts[3]
    return domains


# ---------------------------------------------------------------------------
# The four wave-A predicates (stream-only, integration section 10)
# ---------------------------------------------------------------------------

def predicate_a(records, label=''):
    """P1-9: no simulated step in the new zone inside the frame that transitioned."""
    problems = []
    transitions = [r for r in records if r.get('name') == 'state.zone_transition']
    if not transitions:
        return [f'{label}: no state.zone_transition record to evaluate predicate A on']
    for transition in transitions:
        frame = transition['frame']
        seq = transition['seq']
        after = [r for r in records if r['frame'] == frame and r['seq'] > seq and r.get('name') == 'player.motion']
        if after:
            problems.append(f'{label}: {len(after)} simulated step(s) ran in the new zone inside '
                            f'frame {frame} after state.zone_transition (ticks '
                            f'{[r["tick"] for r in after][:20]})')
        witnesses = [r for r in records
                     if r.get('name') == 'tick.accumulator_reset'
                     and r.get('reason') == 'zone_transition'
                     and seq < r['seq'] < seq + 200]
        if not witnesses:
            problems.append(f'{label}: state.zone_transition at seq {seq} is not followed by a '
                            'tick.accumulator_reset{reason:"zone_transition"} witness')
        else:
            witness = witnesses[0]
            # Ruling 4 discards the whole charged remainder, which in a clamped frame is ~14 steps.
            # What must hold is that the witness is self-consistent and inside the catch-up budget.
            expected = witness['discarded_steps'] * 16_667
            if abs(witness['discarded_us'] - expected) > 16_667:
                problems.append(f'{label}: tick.accumulator_reset reports {witness["discarded_us"]} us '
                                f'for {witness["discarded_steps"]} discarded steps (one step is 16667 us)')
            if witness['discarded_steps'] > STEP_BUDGET:
                problems.append(f'{label}: discarded {witness["discarded_steps"]} steps, above the '
                                f'{STEP_BUDGET}-step catch-up budget')
    per_frame = {}
    for record in records:
        if record.get('name') == 'player.motion':
            per_frame[record['frame']] = per_frame.get(record['frame'], 0) + 1
    over = {frame: count for frame, count in per_frame.items() if count > STEP_BUDGET}
    if over:
        problems.append(f'{label}: frames carrying more than the {STEP_BUDGET}-step budget: {over}')
    return problems


# Per-component identity rules, keyed by the ids the frozen schema declares. A later wave appends a
# case to GameplayStageComponent + this table + the schema's x-code-tables in one commit; the auditor
# then keeps its green without knowing the new component's name in advance (controller amendment,
# review R-11).
def _lives_x1000(award):
    """lives_before x 1000"""
    return award['lives_before'] * 1000


COMPONENT_RULES = {
    'lives_x1000': _lives_x1000,
}


def playthroughs(records):
    """Ruling 3: a playthrough is `restart / new game -> game over / new game`.

    The arrow chain in `analysis-integration_architect.md` section 10-B reads
    `restart/title_enter -> game_over/title_enter`, but the zone-124 farm reaches the title screen
    *while carrying the same score, lives and position* (`beginFromTitle` keeps the saved
    checkpoint). Splitting on any visit to the title would call each farm cycle a fresh playthrough
    and predicate B would pass on the audited defect - the probe measured 1 award + 524 witnesses,
    not 150 awards. So the boundary is where the game state is actually re-initialised:
    `game.game_over`, `state.restart`, or a `state.title_enter` with no saved checkpoint.
    """
    chunks = []
    current = []
    for record in records:
        current.append(record)
        ends = (record.get('name') in ('game.game_over', 'state.restart')
                or (record.get('name') == 'state.title_enter'
                    and record.get('has_saved_checkpoint') is False))
        if ends:
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)
    return chunks


def predicate_b(records, label=''):
    """P1-8: at most one stage bonus per completed zone per playthrough, every repeat witnessed.

    The identity check is component-form, not a sum cap: `points == sum(bonus.stage_component)` and
    each component is validated against its own rule (wave A knows `lives_x1000`; a later wave adds
    bravery/timed components without this predicate changing).
    """
    problems = []
    if not any(r.get('name') == 'bonus.stage_points' for r in records):
        return [f'{label}: no bonus.stage_points record to evaluate predicate B on']
    for index, chunk in enumerate(playthroughs(records)):
        awards = [r for r in chunk if r.get('name') == 'bonus.stage_points']
        components = [r for r in chunk if r.get('name') == 'bonus.stage_component']
        suppressions = [r for r in chunk if r.get('name') == 'bonus.stage_boundary_suppressed']
        counts = {}
        for award in awards:
            counts[award['completed_zone']] = counts.get(award['completed_zone'], 0) + 1
        doubles = {zone: count for zone, count in counts.items() if count > 1}
        if doubles:
            problems.append(f'{label}: playthrough {index + 1} awarded zones twice: {doubles}')
        if len(awards) > 5:
            problems.append(f'{label}: playthrough {index + 1} awarded {len(awards)} stage bonuses '
                            '(the five stage ends are the ceiling)')
        # Component identity: total == sum(components), and each known component matches its rule.
        by_tick = {}
        for award in awards:
            by_tick.setdefault(award['tick'], []).append(award)
        for tick, group in by_tick.items():
            expected = {a['completed_zone']: a for a in group}
            parts = {}
            for component in [c for c in components if c['tick'] == tick]:
                parts.setdefault(component['completed_zone'], []).append(component)
            for zone, award in expected.items():
                pieces = parts.get(zone, [])
                total = sum(piece['points'] for piece in pieces)
                if award['points'] != total:
                    problems.append(f'{label}: zone {zone} bonus total {award["points"]} does not equal '
                                    f'the sum of its components {total} ({[p["component_id"] for p in pieces]})')
                for piece in pieces:
                    rule = COMPONENT_RULES.get(piece['component_id'])
                    if rule is None:
                        problems.append(f'{label}: stage component {piece["component_id"]!r} is not declared '
                                        f'in the frozen schema (x-code-tables.stage_component_id)')
                        continue
                    if piece['points'] != rule(award):
                        problems.append(f'{label}: {piece["component_id"]} component {piece["points"]} != '
                                        f'{rule.__doc__ or "its rule"} (lives_before {award["lives_before"]})')
    # "every repeated trigger is witnessed, never silence" (AC-003). The anchor is the geometry
    # trigger itself: a stage-end `state.zone_exit` past the threshold must produce exactly one
    # outcome record - an award or a suppression - so losing witnesses reddens the check (review R-4,
    # where 744 of 749 removals stayed green because the clause could never be reached).
    triggers = [r for r in records if r.get('name') == 'state.zone_exit'
                and r.get('player_x', 0) > SCREEN_EXIT_X_Q and r.get('zone') in STAGE_END_ZONES]
    awards = [r for r in records if r.get('name') == 'bonus.stage_points']
    suppressions = [r for r in records if r.get('name') == 'bonus.stage_boundary_suppressed']
    if len(triggers) != len(awards) + len(suppressions):
        problems.append(f'{label}: {len(triggers)} stage-end triggers but '
                        f'{len(awards)} awards + {len(suppressions)} suppression witnesses '
                        f'{len(awards) + len(suppressions)} - a trigger was answered silently or twice')
    return problems


def predicate_c(records, label=''):
    """P1-4: after a teleport that left the latch held, no jump until a real release edge."""
    problems = []
    teleports = [r for r in records if r.get('name') == 'player.teleport']
    if not teleports:
        return [f'{label}: no player.teleport record to evaluate predicate C on']
    if not any(r.get('name') == 'player.jump' for r in records):
        pass  # legal: the scenario may never re-press, the witnesses below still must be clean
    edges = [r for r in records if r.get('name') == 'input.action_edge' and r.get('action') == 'jump']
    for teleport in teleports:
        if not teleport.get('jump_latch_held'):
            continue
        start = teleport['seq']
        release = next((r for r in edges if r['seq'] > start and r.get('pressed') is False), None)
        release_seq = release['seq'] if release else float('inf')
        # Positional, exactly as AC-004 words it: the violation is a jump between a held-latch
        # teleport and the next release edge. It must NOT be keyed on the record's own
        # `after_teleport` flag - a build that regresses P1-4 is a build that stopped setting the
        # flag, and a self-reported field cannot be the authority (review R-5, control C5).
        leaked = [r for r in records if r.get('name') == 'player.jump' and start < r['seq'] < release_seq]
        for jump in leaked:
            problems.append(f'{label}: player.jump at tick {jump["tick"]} followed '
                            f'player.teleport{{jump_latch_held:true}} at tick {teleport["tick"]} '
                            'with no release edge in between')
    for jump in [r for r in records if r.get('name') == 'player.jump']:
        if jump.get('after_teleport') is True:
            problems.append(f'{label}: player.jump{{after_teleport:true}} at tick {jump["tick"]} '
                            'is the P1-4 defect signature')
    return problems


def predicate_d(records, label=''):
    """P1-6: the bonus pays once and the launcher keeps firing."""
    problems = []
    bonuses = [r for r in records if r.get('name') == 'bonus.double_launcher']
    fires = [r for r in records if r.get('name') == 'entity.launcher_fire']
    if not bonuses:
        return [f'{label}: no bonus.double_launcher record to evaluate predicate D on']
    seen = {}
    for bonus in bonuses:
        identifier = bonus['launcher_object_id']
        if identifier in seen:
            problems.append(f'{label}: launcher {identifier} paid its bonus twice '
                            f'(ticks {seen[identifier]} and {bonus["tick"]})')
        seen[identifier] = bonus['tick']
        if bonus.get('launcher_active_after') is not True:
            problems.append(f'{label}: launcher {identifier} stopped firing after the payout '
                            '(P1-6: the payout must not clear the fire gate)')
        later = [f for f in fires if f['object_id'] == identifier and f['seq'] > bonus['seq']]
        if not later:
            problems.append(f'{label}: no entity.launcher_fire for launcher {identifier} after its '
                            'bonus - the launcher is silent and P1-6 is observable again')
    return problems


# ---------------------------------------------------------------------------
# Checks named by change-spec.yaml
# ---------------------------------------------------------------------------

def harness_level2_complete(artifacts):
    """AC-001."""
    stream = fixed_stream(artifacts, 'session-level2')
    records = stream.records
    # The tick denominator is the harness's own counter from the manifest (the log's `beginTick`
    # count), NOT the distinct ticks of the motion records themselves - a set built from a list is
    # never larger than that list, which made the old clause unsatisfiable (review R-2, control C2).
    declared_ticks = int(numeric(extras_for(artifacts, 'harness_level2_complete'), 'ticks'))
    motion = len([r for r in records if r.get('name') == 'player.motion'])
    distinct = len({r['tick'] for r in records if r.get('name') == 'player.motion'})
    if declared_ticks < 1000:
        raise CheckFailure(f'the session simulated only {declared_ticks} ticks')
    if distinct != declared_ticks or motion != declared_ticks:
        raise CheckFailure(f'AC-001 needs one player.motion per simulated tick: motion={motion}, '
                           f'distinct ticks with motion={distinct}, simulated ticks={declared_ticks}')
    # Control: dropping one motion record must redden the clause above, or this check is decoration.
    dropped = [r for r in records if r.get('name') != 'player.motion' or r['tick'] != 501]
    if not [r for r in dropped if r.get('name') == 'player.motion'] or             len({r['tick'] for r in dropped if r.get('name') == 'player.motion'}) == declared_ticks:
        raise CheckFailure('the one-motion-per-tick clause does not react to a deleted motion record')
    drops = [r for r in records if r.get('name') == 'log.events_dropped']
    if drops and any(r.get('count', 0) for r in drops):
        raise CheckFailure(f'level-2 session dropped records: {drops[:2]}')
    if records[0].get('name') != 'log.begin':
        raise CheckFailure(f'first line is {records[0].get("name")}, expected log.begin')
    if records[-1].get('name') != 'log.end':
        raise CheckFailure(f'last line is {records[-1].get("name")}, expected log.end')
    if records[0].get('level') != 2:
        raise CheckFailure(f'log.begin reports level {records[0].get("level")}, expected 2')
    for name in ('player.jump', 'player.motion', 'state.zone_transition', 'input.action_edge',
                 'tick.heartbeat', 'score.awarded'):
        if not [r for r in records if r.get('name') == name]:
            raise CheckFailure(f'the session never emitted {name}')
    return (f'{motion} motion records over {declared_ticks} simulated ticks, 0 dropped, '
            f'{len(records)} lines total')


def p1_9_fixed_passes_and_revert_fails(artifacts):
    """AC-002."""
    fixed = fixed_stream(artifacts, 'p1-9-fixed')
    problems = predicate_a(fixed.records, 'fixed')
    if problems:
        raise CheckFailure('; '.join(problems))
    transitions = fixed.by_name('state.zone_transition')
    reset = [r for r in fixed.records if r.get('name') == 'tick.accumulator_reset']
    if not reset:
        raise CheckFailure('no tick.accumulator_reset witness in the fixed stream')

    reverted = variant_stream(artifacts, 'revert-p1-9', 'p1-9-reverted')
    control = predicate_a(reverted.records, 'reverted')
    if not control:
        raise CheckFailure('the fix-reverted build PASSED predicate A - the control does not flip, '
                           'so the green above proves nothing')
    leaked = [line for line in control if 'simulated step(s) ran in the new zone' in line]
    if not leaked:
        raise CheckFailure(f'the reverted build failed predicate A for the wrong reason: {control}')
    if [r for r in reverted.records if r.get('name') == 'tick.accumulator_reset']:
        raise CheckFailure('the reverted variant still resets the accumulator; the knob is not the fix')

    # The product seam must be the one that calls the reset, not only the harness.
    scene = _without_comments(swift_source('GameCore/GameScene.swift'))
    if 'tickDriver.reset(reason: .zoneTransition)' not in scene:
        raise CheckFailure('GameScene.transition(to:) no longer calls tickDriver.reset(reason: .zoneTransition)')
    if re.search(r'accumulator\s*[-+]=', scene):
        raise CheckFailure('GameScene still mutates an accumulator of its own; P1-9 lives in FixedTickDriver now')
    driver = swift_source('GameCore/Diagnostics/FixedTickDriver.swift')
    if 'resetAccumulatorOnZoneTransition: Bool = true' not in driver:
        raise CheckFailure('FixedTickDriver no longer defaults to the fixed behavior')
    for product in ('GameCore/GameScene.swift', 'GameCore/Levels/TMXLevelRuntime.swift',
                    'GameCore/Objects/LevelObstacles.swift'):
        if 'resetAccumulatorOnZoneTransition: false' in swift_source(product):
            raise CheckFailure(f'{product} opts out of the P1-9 fix')
    return (f'fixed: 0 steps after transition, witness {reset[0]["discarded_us"]} us / '
            f'{reset[0]["discarded_steps"]} steps discarded ({len(transitions)} transition); '
            f'reverted: {len([m for m in reverted.by_name("player.motion")])} motion records and '
            f'predicate A fails as required')


def p1_8_fixed_passes_and_revert_fails(artifacts):
    """AC-003."""
    fixed = fixed_stream(artifacts, 'p1-8-fixed')
    problems = predicate_b(fixed.records, 'fixed')
    if problems:
        raise CheckFailure('; '.join(problems))
    awards = fixed.by_name('bonus.stage_points')
    suppressions = fixed.by_name('bonus.stage_boundary_suppressed')
    triggers = [r for r in fixed.records if r.get('name') == 'state.zone_exit'
                and r.get('player_x', 0) > SCREEN_EXIT_X_Q and r.get('zone') in STAGE_END_ZONES]
    # Anchor guard: if the scenario ever stops producing real geometry triggers, the "never silence"
    # clause in predicate_b would silently become dead code again (review R-4).
    if not triggers:
        raise CheckFailure('no stage-end state.zone_exit with player_x past the threshold: the '
                           'witness clause has nothing to anchor on')
    if len(triggers) != len(awards) + len(suppressions):
        raise CheckFailure(f'{len(triggers)} triggers vs {len(awards)} awards + '
                           f'{len(suppressions)} witnesses')
    # Control: partial witness loss must redden, not just total loss.
    stripped = [r for r in fixed.records if not (r.get('name') == 'bonus.stage_boundary_suppressed'
                                                 and r['seq'] > 200)]
    if len(stripped) == len(fixed.records):
        raise CheckFailure('control setup failed: no suppression witnesses to strip')
    if not predicate_b(stripped, 'control'):
        raise CheckFailure('removing most suppression witnesses still passed predicate B')
    if not suppressions:
        raise CheckFailure('the fixed stream has no bonus.stage_boundary_suppressed witness - '
                           'an assertion that only counts awards also passes when the bonus is dead')
    if any(r.get('reason') != 'already_awarded' for r in suppressions):
        raise CheckFailure(f'unexpected suppression reason: {sorted({r["reason"] for r in suppressions})}')

    reverted = variant_stream(artifacts, 'revert-p1-8', 'p1-8-reverted')
    control = predicate_b(reverted.records, 'reverted')
    if not control:
        raise CheckFailure('the fix-reverted build PASSED predicate B - the control does not flip')
    reverted_awards = len(reverted.by_name('bonus.stage_points'))
    if reverted_awards < 100:
        raise CheckFailure(f'the reverted baseline awarded only {reverted_awards} times; the audit '
                           'measured 750 in a 600 s zone-124 run, so the scenario is not reproducing it')
    if reverted.by_name('bonus.stage_boundary_suppressed'):
        raise CheckFailure('the reverted variant emitted suppression witnesses; it is not the pre-fix path')

    scene = _without_comments(swift_source('GameCore/GameScene.swift'))
    if 'stageBoundaries=StageBoundaryLedger()' not in scene.replace(' ', ''):
        raise CheckFailure('GameScene no longer owns a StageBoundaryLedger')
    if 'awardsPerComponentPerZone: 0' in scene:
        raise CheckFailure('GameScene opts out of the P1-8 idempotency rule')
    if 'deliberately dormant' in scene:
        raise CheckFailure('the stale "deliberately dormant" comment survived the ruling')
    return (f'fixed: {len(awards)} award(s) + {len(suppressions)} suppression witnesses over '
            f'{len(playthroughs(fixed.records))} playthrough boundary(ies); '
            f'reverted: {reverted_awards} awards, 0 witnesses, predicate B fails as required')


def p1_4_stream_predicate(artifacts):
    """AC-004."""
    stream = fixed_stream(artifacts, 'p1-4')
    problems = predicate_c(stream.records, 'p1-4')
    if problems:
        raise CheckFailure('; '.join(problems))
    teleports = stream.by_name('player.teleport')
    if not [t for t in teleports if t.get('jump_latch_held')]:
        raise CheckFailure('no player.teleport{jump_latch_held:true} in the stream: the scenario never '
                           'exercised the case that makes P1-4 observable')
    if not stream.by_name('input.contextual_consumed'):
        raise CheckFailure('no input.contextual_consumed witness')
    jumps = stream.by_name('player.jump')
    if not jumps:
        raise CheckFailure('the scenario never produced a legitimate jump either, so the predicate '
                           'could pass on an over-suppressed latch')
    if any(jump.get('after_teleport') for jump in jumps):
        raise CheckFailure(f'a jump leaked through the consume: {jumps}')
    control = fixed_stream(artifacts, 'p1-4-negative-control')
    control_problems = predicate_c(control.records, 'negative control')
    if not control_problems:
        raise CheckFailure('the checker did not fail on a hand-written P1-4 violation - the predicate '
                           'is not decidable from this stream')
    player = _without_comments(swift_source('GameCore/Player/Player.swift'))
    if 'contextHoldsJumpLatch' not in player:
        raise CheckFailure('Player.swift no longer holds the latch after a contextual consume')
    body = _function_body(player, 'func update(input: InputSnapshot, dt: TimeInterval)')
    if 'if contextHoldsJumpLatch, input.jump' not in body:
        raise CheckFailure('Player.update no longer guards the latch rewrite with the contextual hold')
    return (f'{len(teleports)} teleport(s) with the latch held, {len(jumps)} legitimate jump(s) after a '
            f'release edge, 0 leaks; the hand-written violation stream fails predicate C')



def p1_6_stream_predicate(artifacts):
    """AC-005: the payout names the launcher and the launcher still fires - including after a
    **subsequent zone load**, which the typed sentence asks for and the old scenario never executed."""
    stream = fixed_stream(artifacts, 'p1-6-fixed')
    problems = predicate_d(stream.records, 'fixed')
    if problems:
        raise CheckFailure('; '.join(problems))
    bonuses = stream.by_name('bonus.double_launcher')
    fires = stream.by_name('entity.launcher_fire')
    loads = [r for r in stream.records if r.get('name') in ('state.zone_load', 'state.zone_loaded',
                                                            'state.zone_transition')]
    if not loads:
        raise CheckFailure('the P1-6 scenario never crossed a zone boundary, so "a subsequent zone '
                           'load emits entity.launcher_fire for the same object_id" is unevidenced')
    payout = bonuses[0]
    later = [f for f in fires if f['seq'] > loads[-1]['seq'] and f['object_id'] == payout['launcher_object_id']]
    if not later:
        raise CheckFailure('no launcher fire after the zone load that followed the payout')
    later_zone_fires = [f for f in later if f['tick'] > loads[-1]['tick']]
    if not later_zone_fires:
        raise CheckFailure('the post-load fires are not in a later zone')
    runtime = _without_comments(swift_source('GameCore/Levels/TMXLevelRuntime.swift'))
    if 'func collectDoubleLauncherBonus(playerBox: CGRect) -> DoubleLauncherPayout?' not in runtime:
        raise CheckFailure('TMXLevelRuntime.collectDoubleLauncherBonus no longer returns the payout '
                           'carrying the launcher identity and the fire-gate state')
    if 'launcherActiveAfter' not in runtime or 'objectID' not in runtime:
        raise CheckFailure('DoubleLauncherPayout no longer carries the witness fields AC-005 names')
    state = swift_source('GameCore/Diagnostics/LauncherBonusState.swift')
    if 'guard isActive, !bonusCollected, touchesBonusRegion' not in _without_comments(state):
        raise CheckFailure('LauncherBonusState no longer separates the payout from the fire gate')
    control = fixed_stream(artifacts, 'p1-6-baseline-control')
    control_problems = predicate_d(control.records, 'baseline control')
    if not control_problems:
        raise CheckFailure('the pre-fix launcher behavior passed predicate D - the check is vacuous')
    if any(bonus.get('launcher_active_after') for bonus in control.by_name('bonus.double_launcher')):
        raise CheckFailure('the baseline control does not reproduce the defect')
    extras = extras_for(artifacts, 'p1_6_fixed')
    if int(numeric(extras, 'later_zone_fires')) < 1:
        raise CheckFailure(f'the harness reported no later-zone firing: {extras}')
    return (f'{len(bonuses)} payout(s) naming object {payout["launcher_object_id"]}, '
            f'{len(fires)} later shot(s) with launcher_active_after=true, of which '
            f'{len(later_zone_fires)} after a zone load; the pre-fix control fails predicate D')

def emission_cost_budget(artifacts):
    """AC-006. Wave E1 (issue #22 item 5) split the load-sensitive part from the deterministic one.

    The absolute timing bands - the ~4 us M3 append cost and the 0.5 %/5 % wall-clock ratios - are
    reported as WARNINGs carrying the measured value instead of failing the gate: the same
    unchanged code tripped twice under host load 16-18 and passed 3/3 clean, so on a shared host
    they measure the neighbours, not the product. Every deterministic twin stays a HARD failure:
    the clock-measured-something floor (`producer <= 0`: a gate that measured nothing is broken,
    not loaded), the >=5x formatting-control RELATION (both numbers come from the same run, so a
    loaded host moves them together), the 8x-realtime drain floor, and the static allocation scan
    in `hot_path_is_allocation_free`. Nothing here is a policy relaxation: the harness prints the
    same bands through `Harness.warn` and keeps the same hard checks (`main.swift`).
    """
    extras = extras_for(artifacts, 'emission_cost')
    percent = numeric(extras, 'percent_of_tick')
    producer = numeric(extras, 'producer_ns_per_event')
    control = numeric(extras, 'formatting_control_ns_per_event')
    capacity = numeric(extras, 'drain_capacity_ev_per_s')
    if producer <= 0:
        raise CheckFailure(f'the measured append cost {producer} ns/event means the clock or the '
                           'probe measured nothing - that is a broken gate, not a loaded host')
    soft: list[str] = []
    if percent > 5:
        soft.append(f'level-2 emission costs {percent} % of a 16.67 ms tick (spec budget 5 %)')
    elif percent > 0.5:
        # The gate is the spec number; the 10x alarm margin is kept as the earlier-warning twin.
        soft.append(f'level-2 emission {percent} % exceeds the 0.5 % alarm margin (spec budget 5 %)')
    if producer >= 1_000:
        soft.append(f'the append costs {producer} ns/event, over the ~4 us band M3 was sized on')
    for note in soft:
        print(f'WARNING emission-cost band (load-sensitive, not a failure - wave E1 #22 item 5): {note}')
    if control < producer * 5:
        raise CheckFailure(f'the rejected per-event formatting costs only {control / max(producer, 0.001):.1f}x '
                           'the append - the control does not separate the designs')
    if capacity < 3_600 * 8:
        raise CheckFailure(f'the drain clears {capacity} ev/s, below 8x the worst realtime rate 3 600 ev/s')
    return (f'hot path {producer:.1f} ns/event = {percent:.4f} % of a tick at 60 ev/step '
            f'(budget 5 %); formatting control {control:.0f} ns; drain {capacity:.0f} ev/s; '
            f'{len(soft)} soft load-band warning(s)')


def pbxproj_registration_complete():
    """AC-007, with a mutation control."""
    text = PROJECT.read_text(encoding='utf-8')
    problems = []
    for name in NEW_SWIFT_FILES:
        refs = re.findall(r'([0-9A-F]{24}) /\* %s \*/ = \{isa = PBXFileReference' % re.escape(name), text)
        builds = re.findall(r'([0-9A-F]{24}) /\* %s in Sources \*/ = \{isa = PBXBuildFile; fileRef = ([0-9A-F]{24})'
                            % re.escape(name), text)
        in_group = re.search(r'children = \([^)]*20\d{22} /\* %s \*/' % re.escape(name), text, re.S)
        in_sources = re.search(r'files = \([^)]*/\* %s in Sources \*/' % re.escape(name), text, re.S)
        if len(refs) != 1:
            problems.append(f'{name}: {len(refs)} PBXFileReference entries (expected exactly 1)')
            continue
        if len(builds) != 1:
            problems.append(f'{name}: {len(builds)} PBXBuildFile entries (expected exactly 1)')
            continue
        if builds[0][1] != refs[0]:
            problems.append(f'{name}: PBXBuildFile points at {builds[0][1]}, not the file reference {refs[0]}')
        if not in_group:
            problems.append(f'{name}: not a member of any PBXGroup children list')
        if not in_sources:
            problems.append(f'{name}: missing from PBXSourcesBuildPhase files')
    # Control: dropping any one of the four markers must be detected.
    mutated = text.replace(' /* FixedTickDriver.swift in Sources */,', ',', 1)
    if mutated == text:
        raise CheckFailure('control setup failed: could not find the FixedTickDriver sources entry to remove')
    if not _pbxproj_problems(mutated):
        raise CheckFailure('the pbxproj check passed with a file unregistered from PBXSourcesBuildPhase - '
                           'it is not actually verifying all four markers')
    if problems:
        raise CheckFailure('; '.join(problems))
    return f'{len(NEW_SWIFT_FILES)} new files registered with all four marker kinds; the unregistered mutant fails'


def _pbxproj_problems(text):
    problems = []
    for name in NEW_SWIFT_FILES:
        refs = re.findall(r'([0-9A-F]{24}) /\* %s \*/ = \{isa = PBXFileReference' % re.escape(name), text)
        builds = re.findall(r'([0-9A-F]{24}) /\* %s in Sources \*/ = \{isa = PBXBuildFile; fileRef = ([0-9A-F]{24})'
                            % re.escape(name), text)
        in_group = re.search(r'children = \([^)]*20\d{22} /\* %s \*/' % re.escape(name), text, re.S)
        in_sources = re.search(r'files = \([^)]*/\* %s in Sources \*/' % re.escape(name), text, re.S)
        if not (len(refs) == 1 and len(builds) == 1 and builds[0][1] == refs[0] and in_group and in_sources):
            problems.append(name)
    return problems


def _native_targets(text):
    return re.findall(r'([0-9A-F]{24}) /\* ([^*]+) \*/ = \{\s*isa = PBXNativeTarget', text)


def native_target_count():
    """AC-007 (second half): one native target, still addressed by the shared Archive scheme."""
    text = PROJECT.read_text(encoding='utf-8')
    targets = _native_targets(text)
    if len(targets) != 1:
        raise CheckFailure(f'{len(targets)} PBXNativeTarget entries, expected exactly 1: {targets}')
    target_id, target_name = targets[0]
    scheme = SCHEME.read_text(encoding='utf-8')
    if target_name not in scheme:
        raise CheckFailure(f'the shared scheme no longer references the target {target_name!r}')
    if 'BuildAction' not in scheme or 'ArchiveAction' not in scheme:
        raise CheckFailure('the shared scheme lost its Build/Archive actions')
    testables = re.findall(r'isa = PBX.*Test', text)
    if testables:
        raise CheckFailure(f'a test target appeared ({testables}); wave A did not add one')
    mutant_line = ('\t\tBBBBBBBBBBBBBBBBBBBB0001 /* Synthetic */ = {\n'
                   '\t\t\tisa = PBXNativeTarget;\n\t\t};\n')
    mutated = text.replace('/* End PBXNativeTarget section */',
                           mutant_line + '/* End PBXNativeTarget section */', 1)
    if mutated == text:
        raise CheckFailure('control setup failed: the pbxproj has no PBXNativeTarget section to mutate')
    if len(_native_targets(mutated)) != 2:
        raise CheckFailure('control setup failed: the synthetic second target was not parsed')
    if len(_native_targets(text)) != 1:
        raise CheckFailure('the native-target count does not detect a second target')
    return f'exactly one native target ({target_name}) and the shared scheme still addresses it'


def forbid_double_stage_bonus(artifacts):
    """FORBID-001."""
    offenders = []
    for key, stream in gameplay_streams(artifacts).items():
        problems = predicate_b(stream.records, key)
        offenders.extend(problem for problem in problems if 'awarded zones twice' in problem
                         or 'stage bonuses' in problem or 'does not equal' in problem)
    if offenders:
        raise CheckFailure('; '.join(offenders))
    return 'no stream awards a completed_zone twice inside one playthrough'


def forbid_post_transition_steps(artifacts):
    """FORBID-002."""
    offenders = []
    for key, stream in gameplay_streams(artifacts).items():
        for transition in [r for r in stream.records if r.get('name') == 'state.zone_transition']:
            after = [r for r in stream.records
                     if r['frame'] == transition['frame'] and r['seq'] > transition['seq']
                     and r.get('name') == 'player.motion']
            if after:
                offenders.append(f'{key}: {len(after)} steps in frame {transition["frame"]} after the transition')
    if offenders:
        raise CheckFailure('; '.join(offenders))
    return 'no fixed step ran in a new zone inside the render frame that transitioned into it'


def forbid_wallclock_fields(artifacts):
    """FORBID-003: no wall-clock, locale-dependent or free-text value outside the exempt fields."""
    label_values = set()
    for domain in swift_contract_domains().values():
        label_values.update(domain.values())
    label_values |= {'true', 'false', 'none', 'one_in_flight', 'nondeterministic', 'harness',
                     'app_quit', 'error', 'harness_complete', 'quarter-pixel'}
    iso = re.compile(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}')
    offenders = []
    for key, stream in load_streams(artifacts).items():
        for record in stream.records:
            for field_name, value in record.items():
                if field_name == 'name':
                    continue
                if isinstance(value, float):
                    offenders.append(f'{key}: {field_name}={value} is a float (integers only)')
                elif isinstance(value, str):
                    if field_name in EXEMPT_TEXT_FIELDS and record.get('name') == 'log.begin':
                        continue
                    if field_name == 'resource' and re.fullmatch(r'L\d{2}S\d{2}', value):
                        continue
                    if field_name in ('next_level',) and (value == '' or re.fullmatch(r'L\d{2}S\d{2}', value)):
                        continue
                    if field_name in ('launcher_object_id', 'object_id') and re.fullmatch(r'\d+', value):
                        continue
                    if field_name in ('from_path', 'to_path') and record.get('name') == 'log.rotate' \
                            and value.startswith('/') and value.endswith('.jsonl'):
                        continue
                    if field_name == 'marker' and value.startswith('# dropped'):
                        continue
                    if value in label_values:
                        continue
                    offenders.append(f'{key}: {field_name}={value!r} is not a whitelisted label')
                if isinstance(value, str) and iso.search(value):
                    offenders.append(f'{key}: {field_name} carries a wall-clock value')
            if record.get('name') != 'log.begin':
                for field_name in record:
                    if field_name in ('wall_utc', 'run_id', 'build', 'seed', 'path'):
                        offenders.append(f"{key}: {field_name} appears on a {record.get('name')} record")
    if offenders:
        raise CheckFailure('; '.join(offenders[:12]))
    # Control: a timestamp in a payload must be rejected.
    poisoned = [{'schema_version': 1, 'seq': 0, 'tick': 1, 'frame': 1, 'rot': 0, 'ts_us': 16667,
                 'name': 'player.motion', 'wall_utc': '2026-09-24T19:10:39.412Z'}]
    if not _wallclock_offenders(poisoned, label_values):
        raise CheckFailure('the wall-clock check does not catch an injected timestamp - it is not a check')
    return 'every value is an integer, a boolean or a whitelisted label; wall_utc stays confined to log.begin'


def _wallclock_offenders(records, label_values):
    offenders = []
    for record in records:
        for field_name, value in record.items():
            if field_name == 'name' or field_name in EXEMPT_TEXT_FIELDS and record.get('name') == 'log.begin':
                continue
            if isinstance(value, str) and (value not in label_values
                                           and not re.fullmatch(r'L\d{2}S\d{2}|\d+', value)):
                offenders.append(f'{field_name}={value!r}')
            if isinstance(value, float):
                offenders.append(f'{field_name}={value} (float)')
    return offenders


def forbid_log_in_clone(artifacts):
    """FORBID-003 (second half): a log file anywhere inside the clone would stale every receipt."""
    offenders = []
    for path in ROOT.rglob('*.jsonl'):
        if '.git' in path.parts:
            continue
        offenders.append(f'stream file inside the clone: {path}')
    for path in ROOT.rglob('gameplay-*.jsonl'):
        offenders.append(f'gameplay log inside the clone: {path}')
    clone_text = str(ROOT)
    for key, stream in load_streams(artifacts).items():
        for begin in [r for r in stream.records if r.get('name') == 'log.begin']:
            if begin['path'].startswith(clone_text):
                offenders.append(f'{key}: log.begin.path {begin["path"]} is inside the clone')
    # Control: the same scan must reject an in-clone path.
    if not _in_clone_offenders(clone_text, f'{clone_text}/Exolon/gameplay-x-0.jsonl'):
        raise CheckFailure('the in-clone check does not catch an injected in-tree log path')
    if _in_clone_offenders(clone_text, '/tmp/exolon/gameplay-x-0.jsonl'):
        raise CheckFailure('the in-clone control flags a legitimate temp path')
    if offenders:
        raise CheckFailure('; '.join(offenders[:6]))
    writer = swift_source('GameCore/Diagnostics/GameplayEventLog.swift')
    if 'NSTemporaryDirectory' not in writer and 'defaultDirectoryPath' not in writer:
        raise CheckFailure('the default writer directory is no longer derived from the temp directory')
    return 'no log file in the clone; every log.begin.path is outside it (control path rejected too)'


def _in_clone_offenders(clone_text, candidate):
    return [candidate] if candidate.startswith(clone_text) else []



def drops_are_counted(artifacts):
    """FORBID-004: loss is never silent, and there is no crash path on emission failure."""
    stream = fixed_stream(artifacts, 'drops')
    records = stream.records
    drops = [r for r in records if r.get('name') == 'log.events_dropped']
    if not drops:
        raise CheckFailure('the starved-writer stream reports no log.events_dropped record at all')
    declared = sum(r['count'] for r in drops)
    if declared == 0:
        raise CheckFailure(f'log.events_dropped present with count 0: {drops[:2]}')
    for drop in drops:
        for key in ('count', 'first_seq', 'last_seq', 'total_dropped', 'ring_capacity', 'marker'):
            if key not in drop:
                raise CheckFailure(f'log.events_dropped lacks {key}: {drop}')
        if not drop['marker'].startswith('# dropped'):
            raise CheckFailure(f'drop marker is not the human-readable form: {drop["marker"]!r}')
        problems = _drop_bracket_problems(records, drop, 'drops')
        if problems:
            raise CheckFailure('; '.join(problems))
    seqs = [r['seq'] for r in records]
    if any(current != previous + 1 for previous, current in zip(seqs, seqs[1:])):
        raise CheckFailure('the starved stream lost density: the writer numbers contiguous seqs')
    ends = [r for r in records if r.get('name') == 'log.end']
    if not ends:
        raise CheckFailure('the starved stream has no log.end, so the loss cannot be totalled')
    body = [r for r in records if r.get('name') not in WRITER_BUILT]
    if ends[-1]['events'] - len(body) != declared:
        raise CheckFailure(f"log.end declares {ends[-1]['events']} events, {len(body)} records reached "
                           f"the file and log.events_dropped claims {declared}")
    reported = numeric(extras_for(artifacts, 'drops_counted'), 'dropped')
    if reported != declared:
        raise CheckFailure(f'the harness counter says {reported:g} and the stream says {declared}')
    newest_tick = max(r['tick'] for r in records if r.get('name') == 'player.motion')
    if newest_tick < 5_000:
        raise CheckFailure(f'a lapped ring kept old records: newest tick is {newest_tick}')
    # Controls: both fabricated shapes the fix replaced must be rejected.
    fabricated = dict(drops[0])
    fabricated['first_seq'] = max(seqs) + 100
    if not _drop_bracket_problems(records, fabricated, 'control'):
        raise CheckFailure('the drop-bracket rule accepts an out-of-range seq window')
    pre_fix = dict(drops[0])
    pre_fix['last_seq'] = max(0, drops[0]['seq'] - drops[0]['count'])
    pre_fix['first_seq'] = drops[0]['seq'] + 1
    if not _drop_bracket_problems(records, pre_fix, 'control'):
        raise CheckFailure('the drop-bracket rule still accepts the pre-fix `nextSeq - count` window')
    # `written_before_loss` is how many seqs existed when the loss started, so the record written
    # immediately before the hole is `written_before_loss - 1` (log.begin counts).
    written_before = int(numeric(extras_for(artifacts, 'drops_counted'), 'written_before_loss'))
    if drops[0]['last_seq'] != written_before - 1:
        raise CheckFailure(f"the first drop window names last_seq {drops[0]['last_seq']} but the record "
                           f"before the loss is {written_before - 1} ({written_before} seqs issued)")
    for name in NEW_SWIFT_FILES:
        code = _without_comments((DIAGNOSTICS / name).read_text(encoding='utf-8'))
        for forbidden in ('fatalError', 'preconditionFailure', 'assertionFailure', 'try!'):
            if forbidden in code:
                raise CheckFailure(f'{name} contains the crash path {forbidden}')
    return (f'{declared} dropped records counted and bracketed by real seq neighbours, newest tick '
            f'{newest_tick} retained, {ends[-1]["events"]} declared vs {len(body)} written, '
            'no crash path in the diagnostics sources')

def stream_invariants(artifacts):
    """INV-001: seq is a total order inside (run_id, rot); tick and frame never go backwards; and
    the stream is complete - a torn or missing tail is a failure, never a silent pass (R-3)."""
    streams = load_streams(artifacts)
    problems = []
    for key, stream in streams.items():
        problems.extend(_seq_problems(stream.records, key))
    if problems:
        raise CheckFailure('; '.join(problems[:8]))
    # Controls: a truncated stream and a stream whose terminal record was torn off must fail the
    # shipped check itself, not some helper (test-plan negative control 2).
    pristine = fixed_stream(artifacts, 'session-level2').records
    if not _seq_problems(pristine[:len(pristine) // 2], 'control'):
        raise CheckFailure('a truncated log passed the seq continuity check')
    if not _seq_problems([r for r in pristine if r.get('name') != 'log.end'], 'control'):
        raise CheckFailure('a stream missing log.end passed the seq continuity check')
    head = list(pristine)
    head[4] = dict(head[4], seq=head[4]['seq'] + 3)
    if not _seq_problems(head, 'control'):
        raise CheckFailure('a seq gap passed the continuity check')
    total = sum(len(stream.records) for stream in streams.values())
    return (f'total order + completeness hold across {len(streams)} streams ({total} records); '
            'truncated, tail-torn and gapped copies all fail it')


WRITER_BUILT = ('log.begin', 'log.end', 'log.rotate', 'log.events_dropped')


def _seq_problems(records, label='stream'):
    """Density, monotonicity and completeness of one merged (run_id, rot) stream."""
    problems = []
    if not records:
        return [f'{label}: empty stream']
    drops = {r['last_seq'] for r in records if r.get('name') == 'log.events_dropped'}
    expected = None
    previous_tick = 0
    previous_frame = 0
    for position, record in enumerate(records):
        seq = record.get('seq')
        if seq is None:
            problems.append(f'{label}[{position}]: record without seq')
            continue
        if expected is None:
            expected = seq
        if seq != expected:
            if expected not in drops and seq - 1 not in drops:
                problems.append(f'{label}[{position}]: seq jumped to {seq}, expected {expected} '
                                '(no log.events_dropped accounts for it)')
            expected = seq
        expected = seq + 1
        if record['tick'] < previous_tick:
            problems.append(f'{label}[{position}]: tick went backwards ({record["tick"]} after '
                            f'{previous_tick})')
        if record['frame'] < previous_frame:
            problems.append(f'{label}[{position}]: frame went backwards ({record["frame"]} after '
                            f'{previous_frame})')
        previous_tick = max(previous_tick, record['tick'])
        previous_frame = max(previous_frame, record['frame'])
        if record['schema_version'] != 1:
            problems.append(f'{label}[{position}]: schema_version {record["schema_version"]}')
    ends = [r for r in records if r.get('name') == 'log.end']
    if not ends:
        return problems + [f'{label}: stream ends without log.end - the tail is missing']
    if records[-1].get('name') != 'log.end':
        problems.append(f'{label}: log.end is not the last record')
    # Retention pruning deletes whole older generations by design (rotation_linkage checks that),
    # so completeness is only judgable from a stream that still starts at generation 0.
    if records[0].get('rot') == 0:
        lost = sum(r['count'] for r in records if r.get('name') == 'log.events_dropped')
        body = [r for r in records if r.get('name') not in WRITER_BUILT]
        if ends[-1]['events'] != len(body) + lost:
            problems.append(f'{label}: log.end declares {ends[-1]["events"]} events, the stream '
                            f'carries {len(body)} records plus {lost} declared drops')
    for drop in (r for r in records if r.get('name') == 'log.events_dropped'):
        problems.extend(_drop_bracket_problems(records, drop, label))
    return problems


def _drop_bracket_problems(records, drop, label):
    """`log.events_dropped` must bracket the hole with two seq numbers that exist in the file.

    The reviewer's R2-1 finding: the fields used to be computed as `nextSeq - count`, numbers that
    were never issued, because the writer numbers only the records that survive a ring lap. Now the
    pair names the record before the loss and the record after this line, so it is checkable.
    """
    problems = []
    seqs = {r['seq'] for r in records}
    last_seq, first_seq = drop.get('last_seq'), drop.get('first_seq')
    if last_seq is None or first_seq is None:
        return [f'{label}: drop record lacks first_seq/last_seq: {drop}']
    if last_seq >= first_seq:
        problems.append(f'{label}: drop record brackets [{last_seq}..{first_seq}] - empty or inverted')
    if last_seq not in seqs:
        problems.append(f'{label}: drop record names last_seq {last_seq}, absent from the stream')
    if first_seq not in seqs:
        problems.append(f'{label}: drop record names first_seq {first_seq}, absent from the stream')
    if drop['seq'] != last_seq + 1 or drop['seq'] != first_seq - 1:
        problems.append(f'{label}: drop record at seq {drop["seq"]} does not sit between '
                        f'{last_seq} and {first_seq}')
    return problems

def ts_us_derivation(artifacts):
    """INV-002: ts_us == round(tick * 1_000_000 / 60), derived, never accumulated."""
    checked = 0
    for key, stream in load_streams(artifacts).items():
        for record in stream.records:
            expected = round(record['tick'] * 1_000_000 / 60)
            if record['ts_us'] != expected:
                raise CheckFailure(f'{key}: seq {record["seq"]} tick {record["tick"]} reports ts_us '
                                   f'{record["ts_us"]}, derived value is {expected}')
            checked += 1
    # Control: the accumulated-constant formula the design rejected must be caught.
    drifted = [{'schema_version': 1, 'seq': 0, 'tick': 36_000, 'frame': 1, 'rot': 0,
                'ts_us': 36_000 * 16_667, 'name': 'player.motion'}]
    if not [r for r in drifted if r['ts_us'] != round(r['tick'] * 1_000_000 / 60)]:
        raise CheckFailure('the ts_us check does not catch the accumulating formula')
    return f'{checked} records carry the derived ts_us; the +12 ms accumulating variant is rejected'



def counters_never_reset(artifacts):
    """INV-003 (first half): tick and frame are process-global and never rewound."""
    stream = fixed_stream(artifacts, 'session-level2')
    records = stream.records
    motions = [r for r in records if r.get('name') == 'player.motion']
    if not motions:
        raise CheckFailure('no player.motion to read counters from')
    if motions[0]['tick'] != 1:
        raise CheckFailure(f'the first executed step is tick {motions[0]["tick"]}, expected 1')
    if [r['tick'] for r in motions if r['tick'] < 1]:
        raise CheckFailure('a motion record carries tick 0 (pre-loop) in a stepped stream')
    ticks = [r['tick'] for r in motions]
    if any(current < previous for previous, current in zip(ticks, ticks[1:])):
        raise CheckFailure('tick decreased somewhere in the session stream')
    for marker in ('state.zone_transition', 'state.zone_load', 'state.zone_loaded'):
        hits = [r for r in records if r.get('name') == marker]
        if not hits:
            raise CheckFailure(f'the session never emitted {marker}, so the counter claim is untested')
        if not [r for r in motions if r['tick'] > hits[0]['tick']]:
            raise CheckFailure(f'{marker} is the end of the stream; counters past it are unobserved')
    if [r for r in records if r.get('name') == 'tick.accumulator_reset' and r['tick'] == 0]:
        raise CheckFailure('an accumulator reset is stamped tick 0, i.e. the counter was rewound')
    offenders = _counter_write_problems(LOG_CORE)
    if offenders:
        raise CheckFailure('; '.join(offenders))
    # Control: the exact rewind INV-003 forbids must be flagged, not exempted by its "= 0" shape.
    rewound = LOG_CORE + '\n    func rewindForNewGame() {\n        tickValue = 0\n        frameValue = 0\n    }\n'
    if not _counter_write_problems(rewound):
        raise CheckFailure('the counter check accepts a tickValue = 0 rewind (review R-7)')
    if _counter_write_problems(LOG_CORE.replace('private var tickValue: UInt32 = 0',
                                                 'private var tickCounter: UInt32 = 0')):
        raise CheckFailure('the counter check flags a renamed declaration it should ignore')
    transitions = len([r for r in records if r.get('name') == 'state.zone_transition'])
    return (f'tick starts at 1 and never decreases across {len(ticks)} motion records and '
            f'{transitions} zone transition(s); exactly one increment site per counter, and an '
            'injected rewind is caught')


COUNTER_ASSIGN = re.compile(r'\b(tickValue|frameValue)\s*=\s*')


def _counter_write_problems(text):
    """Only the two property declarations and the two `x = x &+ 1` increments may write a counter."""
    problems = []
    for line in text.splitlines():
        stripped = line.strip()
        if not COUNTER_ASSIGN.search(stripped):
            continue
        if stripped.startswith('private var tickValue: UInt32 = 0') and COUNTER_ASSIGN.match(stripped).group(1) == 'tickValue':
            continue
        if stripped.startswith('private var frameValue: UInt32 = 0') and COUNTER_ASSIGN.match(stripped).group(1) == 'frameValue':
            continue
        if re.match(r'^(?:tick|frame)Value = (?:tick|frame)Value &\+ 1$', stripped):
            continue
        problems.append(f'counter write outside the monotonic increment: {stripped}')
    if len(re.findall(r'tickValue = tickValue &\+ 1', text)) != 1:
        problems.append('expected exactly one tick increment site in GameplayEventLog')
    if len(re.findall(r'frameValue = frameValue &\+ 1', text)) != 1:
        problems.append('expected exactly one frame increment site in GameplayEventLog')
    return problems

def _kind_problems(kinds, schema_names):
    """The append-only rules as a pure function, so the controls can exercise them directly."""
    problems = []
    raws = sorted(kinds)
    if raws != list(range(1, len(raws) + 1)):
        problems.append(f'raw values are not dense from 1: {raws[:5]}...{raws[-3:]}')
    by_name = {}
    for raw, entry in kinds.items():
        by_name.setdefault(entry['name'], []).append(raw)
    for name, owners in by_name.items():
        if len(owners) > 1:
            problems.append(f'{name} is claimed by several raw values {owners}')
        if name not in schema_names:
            problems.append(f'{name} is not in the frozen schema')
    for name in schema_names:
        if name not in by_name:
            problems.append(f'schema name {name} has no Swift kind')
    return problems


def kind_enum_append_only():
    """INV-003 (second half) + contract conformance of the kind table."""
    kinds = swift_contract_kinds()
    schema_names = set(NAME_SCHEMAS) | {'log.begin', 'log.rotate', 'log.events_dropped', 'log.end'}
    problems = _kind_problems(kinds, schema_names)
    # Lane maps must be identical on both sides of the contract.
    for raw, entry in kinds.items():
        block = next((b for b in SCHEMA['allOf'] if b['if']['properties']['name']['const'] == entry['name']), None)
        if block is None:
            continue
        if entry['encode'] != block['x-encode'] and entry['encode'] != 'writer-built':
            problems.append(f"{entry['name']}: Swift lane map {entry['encode']!r} != schema x-encode "
                            f"{block['x-encode']!r}")
    # Control: the same rules must fail on a renumbered and on a duplicated kind table, otherwise
    # the append-only claim below is decoration.
    renumbered = dict(kinds)
    renumbered[max(kinds) + 2] = renumbered.pop(max(kinds))
    if not _kind_problems(renumbered, schema_names):
        raise CheckFailure('the append-only check does not catch a renumbered kind')
    duplicated = dict(kinds)
    duplicated[max(kinds) + 1] = {'name': 'player.motion', 'level': 2, 'encode': 'x'}
    if not _kind_problems(duplicated, schema_names):
        raise CheckFailure('the append-only check does not catch a kind that reuses a name')
    if problems:
        raise CheckFailure('; '.join(problems))
    families = {entry['name'].split('.')[0] for entry in kinds.values()}
    declared = set(SCHEMA['x-families']['active-in-wave-a'])
    undeclared = families - declared
    if undeclared:
        raise CheckFailure(f'event families not declared in the schema: {sorted(undeclared)}')
    return f'{len(kinds)} append-only kinds, 1:1 with schema names, lane maps identical on both sides'



def hot_path_is_allocation_free():
    """INV-004 (first half): the whole hot path - emit, the append it delegates to, and the ring
    store - is free of allocating or blocking constructs (review R-7: the middle callee was skipped,
    so an allocation inside `appendRecord` passed)."""
    frames = {
        'emit': _function_body(LOG_CORE, 'func emit(_ kind: GameplayEventKind, entity: UInt16'),
        'appendRecord': _function_body(LOG_CORE, 'private func appendRecord'),
        'storeLocked': _function_body(LOG_CORE, 'private func storeLocked'),
        'beginTick': _function_body(LOG_CORE, 'func beginTick(zone: Int)'),
    }
    missing = [name for name, body in frames.items() if not body]
    if missing:
        raise CheckFailure(f'could not locate hot-path frame(s): {missing}')
    offenders = _allocation_offenders(''.join(frames.values()))
    if offenders:
        raise CheckFailure(f'the fixed-step path contains allocating or blocking constructs: {offenders}')
    # Control: the same scan must reject an allocating hot path, in any of its frames.
    poisoned = 'func appendRecord() { let name = String(describing: kind); pending.append(name) }'
    if not _allocation_offenders(poisoned):
        raise CheckFailure('the allocation scan does not catch an allocating appendRecord - '
                           'it is decoration on the middle of the hot path')
    return f'{len(frames)} hot-path frames ({", ".join(sorted(frames))}) free of ' \
           'String/Data/URL/collection/closure/throwing constructs'


ALLOCATION_PATTERNS = [r'String\(', r'String\(describing', r'\bData\(', r'\bURL\(', r'DateFormatter',
                       r'\[String:', r'\bArray\(', r'\bDictionary\(', r'JSONSerial',
                       r'append\(contentsOf', r'\.map \{', r'\.filter \{', r'\{ \[weak',
                       r'\bawait\b', r'\basync\b', r'\bprint\(', r'FileHandle', r'\btry[!? ]',
                       r'\bdispatch_barrier', r'queue\.sync', r'\bNSQueue]']


def _allocation_offenders(text):
    return [pattern for pattern in ALLOCATION_PATTERNS if re.search(pattern, text)]

def _function_body(text, signature_fragment):
    start = text.find(signature_fragment)
    if start < 0:
        return ''
    brace = text.find('{', start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return ''


def diagnostics_import_boundary():
    """INV-004 (second half): the Linux gate dies if Diagnostics grows a SpriteKit dependency."""
    problems = []
    for name in sorted(path.name for path in DIAGNOSTICS.glob('*.swift')):
        text = (DIAGNOSTICS / name).read_text(encoding='utf-8')
        code = _without_comments(text)
        for line in code.splitlines():
            stripped = line.strip()
            if stripped.startswith('import ') and stripped != 'import Foundation':
                problems.append(f'{name}: {stripped}')
        for forbidden in ('CGVector', 'SpriteKit', 'SKScene', 'SKNode', 'SKSpriteNode', 'AppKit',
                          'os_unfair_lock', 'DispatchQueue.main.sync'):
            if forbidden in code:
                problems.append(f'{name}: references {forbidden}')
    # The Linux-compiled product subset must stay SpriteKit-free too.
    for relative in ('GameCore/GameConstants.swift', 'GameCore/InputState.swift',
                     'GameCore/GameState.swift', 'GameCore/Player/Player.swift'):
        text = swift_source(relative)
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith('import ') and stripped not in ('import Foundation', 'import CoreGraphics'):
                problems.append(f'{relative}: {stripped}')
    if problems:
        raise CheckFailure('; '.join(problems))
    return f'{len(NEW_SWIFT_FILES)} diagnostics sources and the 4 Linux-built product files import Foundation only'


def envelope_schema_valid(artifacts):
    """Contract conformance: envelope key order, per-name payload against the frozen schema."""
    checked = 0
    problems = []
    known_keys = set(ENVELOPE) | set(SCHEMA.get('properties', {}))
    for block in SCHEMA['allOf']:
        known_keys |= set(block['then'].get('properties', {}))
    for key, stream in load_streams(artifacts).items():
        for number, record in enumerate(stream.records):
            if list(record.keys())[:len(ENVELOPE)] != ENVELOPE:
                problems.append(f'{key}[{number}]: envelope order is {list(record)[:8]}')
                continue
            name = record['name']
            unknown = [k for k in record if k not in known_keys and not name.startswith('unknown')]
            if unknown:
                problems.append(f'{key}[{number}]: keys outside the contract {unknown}')
            if name.startswith('unknown'):
                if set(record) - ENVELOPE_SET:
                    problems.append(f'{key}[{number}]: {name} carries payload {sorted(set(record) - ENVELOPE_SET)}')
                checked += 1
                continue
            if name not in NAME_SCHEMAS:
                problems.append(f'{key}[{number}]: {name} is not in the frozen catalog')
                continue
            for field_name in NAME_SCHEMAS[name].get('required', []):
                if field_name not in record:
                    problems.append(f'{key}[{number}]: {name} lacks required {field_name}')
            payload = {k: v for k, v in record.items() if k not in ENVELOPE_SET}
            for field_name, value in payload.items():
                sub = NAME_SCHEMAS[name].get('properties', {}).get(field_name)
                if sub is None:
                    continue
                problems.extend(validate(value, {k: v for k, v in sub.items() if not k.startswith('x-')},
                                         f'{key}[{number}].{field_name}'))
            checked += 1
    if problems:
        raise CheckFailure('; '.join(problems[:12]))
    # Control: the validator has to reject the failure modes that would otherwise pass quietly -
    # a string where the contract declares an integer, and a boolean masquerading as one.
    zone_schema = {k: v for k, v in NAME_SCHEMAS['player.motion']['properties']['zone'].items()
                   if not k.startswith('x-')}
    if validate(0, zone_schema, 'control-int'):
        raise CheckFailure('schema validator control failed: it rejects a valid integer')
    if not validate('0', zone_schema, 'control-string'):
        raise CheckFailure('the validator accepted a string where the contract declares an integer')
    if not validate(True, {'type': 'integer'}, 'control-bool'):
        raise CheckFailure('the validator treats a boolean as an integer')
    return f'{checked} records match the frozen envelope and per-name payloads'



def session_signal_health(artifacts):
    """SIG-001: `log.events_dropped` absent and `tick.heartbeat` gap <= 10.5 s - checked on every
    long level-2 stream, not only the 22 s session (review R-6 item 8: the 600 s evidence existed
    in the artifacts and was never read)."""
    checked = []
    for key, stream in realtime_like_streams(artifacts).items():
        records = stream.records
        ticks = {r['tick'] for r in records if r.get('tick')}
        if len(ticks) < 600:
            continue  # too short to carry a heartbeat period; the drop rule below still applies
        drops = [r for r in records if r.get('name') == 'log.events_dropped']
        if drops and any(r['count'] for r in drops):
            raise CheckFailure(f'{key}: level-2 session reports drops {drops[:2]}')
        heartbeats = [r for r in records if r.get('name') == 'tick.heartbeat']
        if not heartbeats:
            raise CheckFailure(f'{key}: {len(ticks)} ticks and no tick.heartbeat')
        worst = max([b['tick'] - a['tick'] for a, b in zip(heartbeats, heartbeats[1:])] or [0])
        if worst > 630:
            raise CheckFailure(f'{key}: heartbeat gap {worst} ticks ({worst / 60:.2f} s) > 10.5 s')
        if any(r['drops'] for r in heartbeats):
            raise CheckFailure(f'{key}: heartbeat reports drops: {heartbeats[-1]}')
        if any(r['events'] <= 0 for r in heartbeats):
            raise CheckFailure(f'{key}: a heartbeat claims zero events')
        checked.append((key.split('/')[-1], len(ticks), len(heartbeats), worst))
    if len(checked) < 3:
        raise CheckFailure(f'only {len(checked)} long level-2 streams to check: {checked}')
    longest = max(checked, key=lambda item: item[1])
    return (f'{len(checked)} level-2 streams (longest {longest[0]}: {longest[1]} ticks, '
            f'{longest[2]} heartbeats, worst gap {longest[3]} ticks = {longest[3] / 60:.1f} s), '
            '0 drops each')

def rotation_linkage(artifacts):
    """Retention policy: bounded generations, `log.begin` heads every file, and each retired file
    ends with its own `log.rotate` so a consumer holding one generation can tell rotation from
    truncation (review R2-2), with `seq` continuing."""
    files = sorted((artifacts / 'fixed').glob('rotation-*.jsonl'),
                   key=lambda path: int(re.search(r'-(\d+)\.jsonl$', path.name).group(1)))
    if len(files) < 2:
        raise CheckFailure(f'rotation produced {len(files)} file(s); the policy path is untested')
    if len(files) > 3:
        raise CheckFailure(f'kept-files cap breached: {len(files)} files for keptFiles=3')
    previous_rot = None
    last_seq = None
    links = 0
    for index, path in enumerate(files):
        records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()
                   if line.strip()]
        if records[0].get('name') != 'log.begin':
            raise CheckFailure(f'{path.name}: first line is {records[0].get("name")}, '
                               'expected log.begin')
        rot = records[0]['rot']
        if previous_rot is not None and rot != previous_rot + 1:
            raise CheckFailure(f'{path.name}: rot {rot} does not follow {previous_rot}')
        if last_seq is not None and records[1]['seq'] <= last_seq:
            raise CheckFailure(f'{path.name}: seq restarted at {records[1]["seq"]} after {last_seq}')
        rotates = [r for r in records if r.get('name') == 'log.rotate']
        if index + 1 < len(files):
            if not rotates:
                raise CheckFailure(f'{path.name}: retired generation has no log.rotate line, so it '
                                   'is indistinguishable from a truncated file')
            if records[-1].get('name') != 'log.rotate':
                raise CheckFailure(f'{path.name}: log.rotate is not the last line of the retired file')
            link = rotates[-1]
            if not link['to_path'].endswith(files[index + 1].name):
                raise CheckFailure(f'{path.name}: log.rotate.to_path {link["to_path"]} is not the '
                                   f'successor {files[index + 1].name}')
            if not link['from_path'].endswith(path.name):
                raise CheckFailure(f'{path.name}: log.rotate.from_path {link["from_path"]} is not '
                                   'this file')
            if link['rot'] != rot + 1:
                raise CheckFailure(f'{path.name}: log.rotate.rot {link["rot"]} should name the '
                                   f'incoming generation {rot + 1}')
            links += 1
        elif rotates:
            raise CheckFailure(f'{path.name}: the live generation must not carry its own rotate line')
        last_seq = records[-1]['seq']
        previous_rot = rot
        if path.stat().st_size > 8_388_608 + 4_096 * 400:
            raise CheckFailure(f'{path.name} is {path.stat().st_size} bytes, far beyond the '
                               '8 MiB per-file cap (one batch of overshoot is allowed)')
    # Control: remove the link line from a retired generation and the check must call it out.
    head = [json.loads(line) for line in files[0].read_text(encoding='utf-8').splitlines()
            if line.strip()]
    without_link = [r for r in head if r.get('name') != 'log.rotate']
    if without_link == head:
        raise CheckFailure('control setup failed: no log.rotate line to strip')
    if without_link[-1].get('name') == 'log.rotate':
        raise CheckFailure('control setup failed: the link is not at the tail')
    total = sum(path.stat().st_size for path in files)
    return (f'{len(files)} generations, {links} retired files each ending in their own log.rotate '
            f'into the named successor, seq continues, {total} bytes on disk')

def kill_switch_no_file(artifacts):
    """SIG-002: `off` produces no file at all - an empty file would be a failure."""
    entries = extras_for(artifacts, 'kill_switch_off')
    if 'offFiles=0' not in entries:
        raise CheckFailure(f'the harness did not report offFiles=0 (entries: {entries})')
    strays = sorted(path.name for path in (artifacts / 'fixed').glob('off-*'))
    if strays:
        raise CheckFailure(f'the off switch still left files behind: {strays}')
    empty = sorted(path.name for path in (artifacts / 'fixed').glob('*.jsonl') if path.stat().st_size == 0)
    if empty:
        raise CheckFailure(f'empty log files present (empty != disabled): {empty}')
    return 'EXOLON_EVENT_LOG=off creates no file, and no empty file either'



# ---------------------------------------------------------------------------
# Gates the reviews showed were missing (code review section 3, test review R-1/R-6/R-10)
# ---------------------------------------------------------------------------

def touched_swift_files():
    """Every Swift file this change adds or edits, tracked or untracked."""
    files = []
    try:
        tracked = subprocess.run(['git', '-C', str(ROOT), 'diff', '--name-only', 'HEAD'],
                                 capture_output=True, text=True, timeout=120).stdout.splitlines()
        untracked = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '--others',
                                    '--exclude-standard'],
                                   capture_output=True, text=True, timeout=120).stdout.splitlines()
        files = [line for line in tracked + untracked
                 if line.endswith('.swift') and line.startswith('Exolon/')]
    except (OSError, subprocess.SubprocessError):
        pass
    baseline = ['Exolon/GameCore/GameScene.swift',
                'Exolon/GameCore/Levels/TMXLevelRuntime.swift',
                'Exolon/GameCore/Objects/LevelObstacles.swift',
                'Exolon/Platform/macOS/AppDelegate.swift',
                'Exolon/GameCore/Player/Player.swift',
                'Exolon/GameCore/InputState.swift',
                'Exolon/GameCore/GameConstants.swift',
                'Exolon/GameCore/GameState.swift'] \
               + [f'Exolon/GameCore/Diagnostics/{name}' for name in NEW_SWIFT_FILES]
    fallback = [rel for rel in baseline if (ROOT / rel).is_file()]
    merged = sorted(set(files) | set(fallback))
    return [rel for rel in merged if (ROOT / rel).is_file()]


def touched_swift_files_parse_clean():
    """R-1: `test-plan.md` promises a static parse gate over the touched Swift files, and the four
    SpriteKit-bound files are compiled by nothing else on this host. Without this gate a syntax
    error in `GameScene.swift` still reports 23/23 green."""
    swiftc = SWIFTC if Path(SWIFTC).is_file() else 'swiftc'
    files = touched_swift_files()
    required = list(SPRITEKIT_BOUND) + ['Exolon/GameCore/Player/Player.swift',
                                        'Exolon/GameCore/InputState.swift'] \
               + [f'Exolon/GameCore/Diagnostics/{name}' for name in NEW_SWIFT_FILES]
    missing = [rel for rel in required if rel not in files]
    if missing:
        raise CheckFailure(f'the parse set is incomplete, missing {missing}')
    offenders = _parse_errors(swiftc, files)
    # Control: injected garbage in a copy must be reported, or the gate is decorative.
    sample = next((ROOT / rel).read_text(encoding='utf-8') for rel in files if rel.endswith('GameScene.swift'))
    if not _parse_errors(swiftc, files, extra_text=sample + '\nfunc broken((( {\n'):
        raise CheckFailure('the parse gate accepts injected syntax garbage')
    if offenders:
        raise CheckFailure('; '.join(offenders[:6]))
    return f'{len(files)} touched Swift files parse clean (control: injected garbage rejected)'


def _parse_errors(swiftc, files, extra_text=None):
    import tempfile
    with tempfile.TemporaryDirectory(prefix='exolon-parse-') as tmp:
        paths = []
        for rel in files:
            target = Path(tmp) / rel.replace('/', '_')
            text = (ROOT / rel).read_text(encoding='utf-8')
            if extra_text is not None and rel.endswith('GameScene.swift'):
                text = extra_text
            target.write_text(text, encoding='utf-8')
            paths.append(str(target))
        result = subprocess.run([swiftc, '-frontend', '-parse'] + paths,
                                capture_output=True, text=True, timeout=600)
    joined = result.stdout + result.stderr
    return [line for line in joined.splitlines() if ': error:' in line]


def _producer_helpers():
    """kind -> producing helper, parsed from the extension bodies in GameplayEventSink.swift.

    The scan is deliberately dumb: inside each `func emitX(...) {` body, every `emit(.someKind` or
    `emitPosition(x ? .a : .b` reference is a kind that helper owns.
    """
    text = SINK_CORE
    start = text.index('extension GameplayEventSink {')
    end = text.index('/// Wire labels for the existing product vocabularies.')
    mapping = {}
    cases = set(_dotted_to_case().values())
    current = None
    for line in text[start:end].splitlines():
        func = re.match(r'    func (emit\w+)\(', line)
        if func:
            current = func.group(1)
        if not current:
            continue
        if re.search(r'\bemit(?:Position)?\(', line):
            # Any `.someCase` on an emit line is a kind this helper owns, which covers the
            # `entering ? .statePauseEnter : .statePauseExit` shape a first-match pattern missed.
            for kind in re.findall(r'\.([a-zA-Z]\w*)', line):
                if kind in cases:
                    mapping.setdefault(kind, current)
    return mapping


def helper_owned_kinds():
    """{kind_raw_name: helper_name} for every kind a producer helper emits."""
    return _producer_helpers()


def producer_sites_use_helpers_only():
    """Root cause of the four wire lies (code review section 3): lane arithmetic was re-derived at
    every call site, in files the Linux gate never compiles. It must live in exactly one compiled
    place - the producer helpers in `GameplayEventSink.swift` - and every helper must be reachable
    from real product code."""
    forbidden = {
        'events.emit(': 'a raw lane-tuple emit call (use the named producer helper)',
        'events?.emit(': 'a raw lane-tuple emit call (use the named producer helper)',
        'GameplayPack.': 'hand packing at the call site',
        'GameplayEvent.lane(': 'hand packing at the call site',
        'GameplayEvent.split(': 'a hand-split i32 lane pair at the call site',
        'GameplayEvent.q(': 'a hand-quantized coordinate at the call site',
        'Int16(truncatingIfNeeded': 'a hand-truncated lane value at the call site',
    }
    offenders = []
    for rel in PRODUCER_FILES:
        code = _without_comments((ROOT / rel).read_text(encoding='utf-8'))
        for needle, why in forbidden.items():
            for line in code.splitlines():
                if needle in line:
                    offenders.append(f'{rel}: {needle} - {why}')
    # Control: the scan must still recognise the shape that shipped R1-1.
    defective = 'events.emit(.damagePlayerHit, packed, x, y, Int16(truncatingIfNeeded: 2))'
    if not [needle for needle in forbidden if needle in defective]:
        raise CheckFailure('the producer-site scan no longer recognises the shape that shipped R1-1')
    if offenders:
        raise CheckFailure('; '.join(offenders[:8]))
    helpers = helper_owned_kinds()
    if not helpers:
        raise CheckFailure('could not parse the producer helper table out of GameplayEventSink.swift')
    unowned = sorted(name for name in wire_reachable_names()
                     if name != 'tick.heartbeat' and _kind_case(name) not in helpers)
    if unowned:
        raise CheckFailure(f'kinds with no producer helper: {unowned}')
    # `FixedTickDriver` lives in Diagnostics and is product code, so the whole tree counts here;
    # the "no raw lane arithmetic at call sites" rule above is scoped to PRODUCER_FILES instead.
    product = list((ROOT / 'Exolon').rglob('*.swift'))
    text = '\n'.join(path.read_text(encoding='utf-8') for path in product)
    called = set(re.findall(r'\.(emit\w+)\(', text))
    dead = sorted(set(helpers.values()) - called)
    if dead:
        raise CheckFailure(f'producer helpers no product file calls (dead lane maps): {dead}')
    if offenders:
        raise CheckFailure('; '.join(offenders[:8]))
    return (f'{len(PRODUCER_FILES)} producer files carry zero lane arithmetic; all '
            f'{len(helpers)} lane maps live in the compiled sink extension and every one of them is '
            'called from product code')


def _dotted_to_case():
    """`damage.player_hit` -> `damagePlayerHit`, read from the Swift label switch itself."""
    text = SINK_CORE
    raws = {name: int(raw) for name, raw in re.findall(r'case (\w+) = (\d+)', text)}
    labels = dict(re.findall(r'case \.(\w+): return "([^"]+)"', text))
    return {label: case for case, label in labels.items() if case in raws}


def _kind_case(dotted):
    return _dotted_to_case()[dotted]


def wire_reachable_names():
    """Every catalog name a producer can put on the wire (the four writer-built records excluded)."""
    return {entry['name'] for entry in swift_contract_kinds().values() if entry['name'] not in WRITER_BUILT}


def lane_round_trip_is_exact(artifacts):
    """The class-closing table test (code review section 3, items R1-1..R1-4): every wire-reachable
    record is packed by its production helper from `GameplayEventSink.swift` with distinctive
    values, formatted by the real formatter, written, read back - and compared field by field
    against the literal expectations in `lane-roundtrip.tsv`.

    A swapped lane, a wrong bit offset, a misread i32 pair or a wrong derived value fails here. All
    four review-found wire lies fail this test; none of them was visible to any other check.
    """
    tsv = artifacts / 'fixed' / 'lane-roundtrip.tsv'
    if not tsv.is_file():
        raise CheckFailure(f'{tsv} missing - the lane round-trip scenario never ran')
    stream = load_streams(artifacts).get('fixed/lane-roundtrip')
    if stream is None:
        raise CheckFailure('no lane-roundtrip stream in the artifacts')
    records = stream.records
    cursor = 0
    expectations = []
    for line in tsv.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('kind\t'):
            continue
        columns = [c for c in line.split('\t') if c]
        fields = dict(col.split('=', 1) for col in columns[1:] if '=' in col)
        expectations.append((columns[0], fields))
    problems = []
    for name, fields in expectations:
        index = next((i for i in range(cursor, len(records)) if records[i].get('name') == name), None)
        if index is None:
            problems.append(f'{name}: never emitted by the round-trip scenario')
            continue
        record = records[index]
        cursor = index + 1
        flat = _flatten(record)
        for wanted_field, want in fields.items():
            got = flat.get(wanted_field)
            if got is None:
                problems.append(f'{name}: {wanted_field} absent from {sorted(flat)}')
            elif got != want:
                problems.append(f'{name}.{wanted_field}: wire {got!r} != packed input {want!r}')
        for key in [k for k in flat if k not in ENVELOPE and k not in fields
                    and not any(k.startswith(f + '.') for f in fields)]:
            problems.append(f'{name}: undeclared payload field {key} on the round-trip record')
    if problems:
        raise CheckFailure('; '.join(problems[:10]))
    covered = {name for name, _ in expectations}
    producers = {entry['name'] for entry in swift_contract_kinds().values() if entry['name'] not in WRITER_BUILT}
    untested = sorted(producers - covered)
    # `tick.heartbeat` is composed inside beginTick (no producer helper), so it is asserted
    # structurally rather than through the table.
    if untested != ['tick.heartbeat']:
        raise CheckFailure(f'lane table does not cover: {untested}')
    # Controls: a real record must disagree with the pre-fix lane order, and a swapped expectation
    # must be reported - otherwise the table proves nothing.
    hit = [r for r in records if r.get('name') == 'damage.player_hit'][-1]
    flat_hit = _flatten(hit)
    if flat_hit.get('x') == str(hit.get('lives')):
        raise CheckFailure('the round-trip stream carries the pre-fix lane order (packed value in x)')
    swapped = dict(flat_hit)
    swapped['x'], swapped['y'] = flat_hit['y'], flat_hit['x']
    if swapped['x'] == flat_hit['x']:
        raise CheckFailure('the round-trip control cannot detect a swapped lane pair (equal values)')
    return (f'{len(expectations)} records round-tripped exactly across {len(covered)} wire names '
            f'(all {len(producers)} producer-reachable kinds; heartbeat asserted separately)')


def _flatten(record, prefix=''):
    """Dot paths for nested payload objects (`player.teleport.from.x`), values rendered the way the
    harness writes its expectation table."""
    flat = {}
    for key, value in record.items():
        name = prefix + key
        if isinstance(value, dict):
            flat.update(_flatten(value, name + '.'))
        else:
            flat[name] = _render(value)
    return flat


def _render(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


def async_writer_healthy(artifacts):
    """R-10: the shipped Debug posture - `.asynchronous` with the drain timer and the file writer -
    is constructed by nothing else on this host. Level-2 emission through it must lose nothing and
    must be fully drained by the barrier on shutdown."""
    streams = load_streams(artifacts)
    key = 'fixed/async'
    if key not in streams:
        raise CheckFailure(f'no async stream in the artifacts (have {sorted(streams)[:6]}...)')
    records = streams[key].records
    extras = extras_for(artifacts, 'async_writer')
    motions = int(numeric(extras, 'motions'))
    dropped = int(numeric(extras, 'dropped'))
    seen = len([r for r in records if r.get('name') == 'player.motion'])
    if dropped:
        raise CheckFailure(f'the asynchronous drain dropped {dropped} level-2 records')
    if seen != motions:
        raise CheckFailure(f'async stream carries {seen} of {motions} motions - the flush barrier '
                           'left records in the ring')
    problems = _seq_problems(records, key)
    if problems:
        raise CheckFailure('; '.join(problems[:5]))
    if [r for r in records if r.get('name') == 'log.events_dropped']:
        raise CheckFailure('async level-2 session reports drops')
    heartbeats = [r for r in records if r.get('name') == 'tick.heartbeat']
    if len(heartbeats) < 2:
        raise CheckFailure(f'async stream carries {len(heartbeats)} heartbeats')
    if any(r['drops'] for r in heartbeats):
        raise CheckFailure(f'async heartbeat reports drops: {heartbeats[-1]}')
    return (f'queue + timer + file writer drained {seen} motions and {len(heartbeats)} heartbeats '
            'with 0 drops; the barrier flushed the whole ring')


FRAME_DRIVEN = ('session-level2', 'p1-9-fixed', 'p1-9-reverted', 'p1-8-fixed', 'p1-8-reverted',
                'p1-4-', 'p1-6-')


def frame_driven_streams(artifacts):
    """Streams produced by a loop that actually advances `frame` per rendered frame.

    SIG-003 counts simulated steps *per rendered frame*; the writer-focused scenarios (rotation,
    drops, async, contract sweep, lane round-trip) call `beginTick` in tight loops without a
    frame per step, so applying a per-frame ceiling to them would measure the scenario, not the
    game.
    """
    return {key: stream for key, stream in load_streams(artifacts).items()
            if any(stem in key for stem in FRAME_DRIVEN)
            and len({r['frame'] for r in stream.records}) > 1}


def frame_step_budget(artifacts):
    """SIG-003 as its own symbol: no rendered frame may simulate more than
    floor(maximumFrameTime / fixedTimeStep) = 15 steps, and none of those may straddle a
    `state.zone_transition`."""
    offenders = []
    observed = 0
    for key, stream in frame_driven_streams(artifacts).items():
        if 'revert' in key:
            continue  # the reverted driver is this check's control, not its subject
        per_frame = {}
        for record in stream.records:
            if record.get('name') == 'player.motion':
                per_frame[record['frame']] = per_frame.get(record['frame'], 0) + 1
        if per_frame:
            observed = max(observed, max(per_frame.values()))
        over = {frame: count for frame, count in per_frame.items() if count > STEP_BUDGET}
        if over:
            offenders.append(f'{key}: frames over the {STEP_BUDGET}-step budget {over}')
        for transition in [r for r in stream.records if r.get('name') == 'state.zone_transition']:
            same = [r for r in stream.records if r.get('name') == 'player.motion'
                    and r['frame'] == transition['frame'] and r['seq'] > transition['seq']]
            if same:
                offenders.append(f'{key}: {len(same)} steps straddle the transition in frame '
                                 f'{transition["frame"]}')
    if offenders:
        raise CheckFailure('; '.join(offenders[:6]))
    reverted = variant_stream(artifacts, 'revert-p1-9', 'p1-9-reverted')
    control = predicate_a(reverted.records, 'control')
    if not control:
        raise CheckFailure('the reverted driver passed the frame-step budget clause')
    # Control: a 16th motion inside one frame must breach the budget.
    sample = fixed_stream(artifacts, 'session-level2')
    first = next(r for r in sample.records if r.get('name') == 'player.motion')
    padded = [r for r in sample.records if r.get('name') == 'player.motion']
    padded += [dict(first)] * STEP_BUDGET
    if not [frame for frame, count in _motions_per_frame(padded).items() if count > STEP_BUDGET]:
        raise CheckFailure('the frame-budget clause cannot see an over-budget frame')
    frames = len(frame_driven_streams(artifacts))
    return (f'max {observed} simulated steps in any frame across {frames} frame-driven streams '
            f'(budget {STEP_BUDGET}); the reverted control breaches it')


def _motions_per_frame(records):
    per_frame = {}
    for record in records:
        per_frame[record['frame']] = per_frame.get(record['frame'], 0) + 1
    return per_frame


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_artifacts(artifacts: Path, record_to_tree: bool = False):
    if artifacts.exists():
        shutil.rmtree(artifacts)
    (artifacts / 'fixed').mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, EXOLON_HARNESS_OUT=str(artifacts), EXOLON_REVERT='none')
    result = subprocess.run(['bash', str(RUN_SH)], env=environment, capture_output=True, text=True, timeout=900)
    transcript = result.stdout + result.stderr
    # Review R-8: the transcript belongs beside the artifacts. Writing it into the clone on every
    # run makes concurrent verifiers overwrite each other's evidence and moves the tree the receipt
    # is bound to; `--record` is the explicit opt-in for committing a transcript.
    (artifacts / 'last-run.txt').write_text(transcript, encoding='utf-8')
    if record_to_tree:
        _write_if_changed(CHANGE / 'evidence' / 'harness' / 'last-run.txt', transcript)
    if result.returncode != 0:
        tail = '\n'.join((result.stdout + result.stderr).splitlines()[-25:])
        raise CheckFailure(f'evidence/harness/run.sh exited {result.returncode}\n{tail}')


CHECKS = [
    ('harness_level2_complete', 'AC-001'),
    ('p1_9_fixed_passes_and_revert_fails', 'AC-002 / FORBID-002'),
    ('p1_8_fixed_passes_and_revert_fails', 'AC-003 / FORBID-001'),
    ('p1_4_stream_predicate', 'AC-004'),
    ('p1_6_stream_predicate', 'AC-005'),
    ('emission_cost_budget', 'AC-006'),
    ('pbxproj_registration_complete', 'AC-007'),
    ('native_target_count', 'AC-007'),
    ('forbid_double_stage_bonus', 'FORBID-001'),
    ('forbid_post_transition_steps', 'FORBID-002'),
    ('forbid_wallclock_fields', 'FORBID-003'),
    ('forbid_log_in_clone', 'FORBID-003'),
    ('drops_are_counted', 'FORBID-004'),
    ('stream_invariants', 'INV-001'),
    ('ts_us_derivation', 'INV-002'),
    ('counters_never_reset', 'INV-003'),
    ('kind_enum_append_only', 'INV-003'),
    ('hot_path_is_allocation_free', 'INV-004'),
    ('diagnostics_import_boundary', 'INV-004'),
    ('envelope_schema_valid', 'contract'),
    ('touched_swift_files_parse_clean', 'R-1 static gate promised by test-plan.md'),
    ('lane_round_trip_is_exact', 'code review R1-1..R1-4 (lane truth)'),
    ('producer_sites_use_helpers_only', 'code review section 3 (producer coverage)'),
    ('async_writer_healthy', 'R-10 shipped Debug posture'),
    ('frame_step_budget', 'SIG-003'),
    ('session_signal_health', 'SIG-001'),
    ('rotation_linkage', 'retention'),
    ('kill_switch_no_file', 'SIG-002'),
]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--artifacts', help='reuse an existing harness artifact directory')
    parser.add_argument('--only', help='comma-separated subset of the named checks')
    parser.add_argument('--list', action='store_true', help='print the check names and exit')
    parser.add_argument('--record', action='store_true',
                        help='also write the harness transcript into evidence/harness/last-run.txt '
                             '(default: it stays beside the artifacts; review R-8)')
    arguments = parser.parse_args(argv)

    if arguments.list:
        for name, binding in CHECKS:
            print(f'{name}  [{binding}]')
        return 0

    wanted = None
    if arguments.only:
        wanted = {item.strip() for item in arguments.only.split(',') if item.strip()}
        unknown = wanted - {name for name, _ in CHECKS}
        if unknown:
            print(f'unknown checks: {sorted(unknown)}', file=sys.stderr)
            return 2

    global ARTIFACT_DIR
    if arguments.artifacts:
        artifacts = Path(arguments.artifacts).resolve()
        if not (artifacts / 'fixed' / 'manifest.json').is_file():
            print(f'no harness manifest under {artifacts}', file=sys.stderr)
            return 66
    else:
        artifacts = Path(tempfile.mkdtemp(prefix='exolon-harness-')) / 'artifacts'
        print(f'building and running the harness in {artifacts} ...', flush=True)
        run_artifacts(artifacts, record_to_tree=arguments.record)
    ARTIFACT_DIR = artifacts

    failures = 0
    executed = 0
    for name, binding in CHECKS:
        if wanted and name not in wanted:
            continue
        executed += 1
        function = globals()[name]
        parameters = function.__code__.co_argcount
        try:
            detail = function(*([artifacts] if parameters else []))
        except CheckFailure as error:
            failures += 1
            print(f'FAIL {name} [{binding}]: {error}')
            continue
        except Exception as error:  # a crash in a check is a failed check, never a pass
            failures += 1
            print(f'FAIL {name} [{binding}]: {type(error).__name__}: {error}')
            continue
        print(f'PASS {name} [{binding}]: {detail}')

    print(f'RESULT: {"FAIL" if failures else "PASS"} ({executed - failures}/{executed} checks passed)')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
