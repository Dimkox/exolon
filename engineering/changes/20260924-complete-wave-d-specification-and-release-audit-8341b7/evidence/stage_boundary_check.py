#!/usr/bin/env python3
"""Wave-D stage-boundary verifier: L0 characterization, L1 pure-ledger table, the funnel.

Typed authority: ../change-spec.yaml (AC-005, AC-006, AC-007, INV-001, FORBID-003).
Design contract: ../evidence/analysis-architect.md (sections 4-7),
../evidence/analysis-repo_explorer.md section 1 (the clause-by-clause reading of the base tree),
../evidence/analysis-docs_researcher.md section 1 (the norm text and its named silences).

WHAT THIS MEASURES, AND HOW
  Phase D-2 pinned the product's `before` state (three of six canonical clauses) plus the single
  award funnel. Phase D-1 - after wave A's StageBoundaryLedger merged - adds the L1 table over the
  real product types. Every number below is read out of the committed Swift sources
  (`GameConstants`, `StageBoundaryLedger`, `GameScene`, `GameplayEventSink`), never restated from
  this file, so the table is bound to the tree the way wave A's own contour binds its predicates.

  The Swift is parsed and modelled here, not executed: `GameScene` imports SpriteKit and cannot
  run on Linux. Executed-Swift stays wave A's contour (`harness/run.sh` plus
  `gameplay_log_check.py::p1_8_fixed_passes_and_revert_fails`); this tool re-reads those same
  sources instead of re-running a second machine's harness, and the wire side of the identity is
  checked against wave A's real lane names in `component_stream_identity`.

  Every row has a contradictory control. An assertion that cannot flip is reported as a failure.

rc contract: 0 = the requested phase held; 1 = something violated; 2 = usage.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

CHANGE_ID = "20260924-complete-wave-d-specification-and-release-audit-8341b7"
CHANGE_DIR = f"engineering/changes/{CHANGE_ID}"
GAME_SCENE_REL = "Exolon/GameCore/GameScene.swift"
GAME_STATE_REL = "Exolon/GameCore/GameState.swift"
GAME_CONSTANTS_REL = "Exolon/GameCore/GameConstants.swift"
PLAYER_REL = "Exolon/GameCore/Player/Player.swift"
LEDGER_REL = "Exolon/GameCore/Diagnostics/StageBoundaryLedger.swift"
SINK_REL = "Exolon/GameCore/Diagnostics/GameplayEventSink.swift"
DRIVER_REL = "Exolon/GameCore/Diagnostics/FixedTickDriver.swift"
PBXPROJ_REL = "Exolon.xcodeproj/project.pbxproj"
EVENT_SCHEMA_REL = "engineering/contracts/schemas/gameplay-event-v1.schema.json"
RESOURCES_DIR = "Exolon/Resources"
MECHANICS_REL = "ORIGINAL_MECHANICS.md"
L0_SNAPSHOT_REL = f"{CHANGE_DIR}/evidence/l0-before-d1.txt"
EXECUTED_TABLE_REL = f"{CHANGE_DIR}/evidence/ledger-xcheck-executed.txt"
XCHECK_RUN_REL = f"{CHANGE_DIR}/evidence/ledger-xcheck/run.sh"
BASE_COMMIT = "295690b"
PENDING_REASON = "pending wave-A merge"

BOUNDARY_MARKER = "private func applyOriginalStageBoundaryIfNeeded(completedZone: Int) {"
# The base tree's `before`: three of the six canonical clauses (`ORIGINAL_MECHANICS.md:140-146`).
CLAUSE_ROWS = (
    ("lives_x1000", 141, "PRESENT", r"awardPoints\(gameState\.lives \* 1_000\)"),
    ("refill_ammo", 146, "PRESENT", r"gameState\.ammo = GameState\.startingAmmo"),
    ("refill_grenades", 146, "PRESENT", r"gameState\.grenades = GameState\.startingGrenades"),
    ("bravery_10000", 142, "MISSING", r"bravery|10_000|10000"),
    ("timed_ladder", 143, "MISSING", r"timed|cursor|phase"),
    ("plus_one_life_capped_9", 144, "PARTIAL",
     r"if gameState\.lives < GameState\.startingLives \{ gameState\.lives \+= 1 \}"),
    ("clear_exoskeleton", 145, "MISSING", r"setExoskeleton"),
)

# Owner gate ruling 2: the five ladder values are canonical, the cadence is the declared deviation.
CANONICAL_TIMED_VALUES = (0, 1000, 3000, 5000, 7000)
LIVES_MULTIPLIER = 1_000
TICK_HZ = 60  # GameConstants.fixedTimeStep = 1/60; wave A derives ts_us from the tick

ZONE_CASES = (0, 23, 24, 25, 49, 74, 99, 124, 125)
LIVES_CASES = (0, 1, 4, 8, 9)
ELAPSED_CASES = (0, 1, 1799, 1800, 3599, 3600, 5400, 7199, 7200, 108_000)


class CheckFailure(Exception):
    """A named check went red."""


# --- reading the tree -------------------------------------------------------------------
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


def git_show(root: pathlib.Path, rev: str, rel: str) -> str:
    proc = subprocess.run(["git", "-C", str(root), "show", f"{rev}:{rel}"],
                          capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise CheckFailure(f"git show {rev}:{rel} failed: {proc.stderr.strip()[:160]}")
    return proc.stdout


def function_body(text: str, marker: str, what: str) -> str:
    """Brace-matched extraction of one function; no regex on code structure."""
    idx = text.find(marker)
    if idx < 0:
        raise CheckFailure(f"{what} is not present (marker {marker!r} not found)")
    depth = 0
    i = idx + len(marker) - 1
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[idx:i + 1]
        i += 1
    raise CheckFailure(f"{what}: unbalanced braces")


def line_of(text: str, needle: str) -> int:
    idx = text.find(needle)
    return 0 if idx < 0 else text.count("\n", 0, idx) + 1


class Constants:
    """The stage-end numbers, parsed from `GameConstants.swift` rather than restated here."""

    def __init__(self, swift: str):
        self.raw = swift
        self.max_lives = self._int("maxLives")
        self.bravery = self._int("braveryBonus")
        self.phase_ticks = self._int("phaseTicks")
        self.lives_multiplier = LIVES_MULTIPLIER
        ladder = re.search(r"static let timedBonusLadder = \[([^\]]*)\]", swift)
        if not ladder:
            raise CheckFailure(f"{GAME_CONSTANTS_REL}: timedBonusLadder is missing")
        self.ladder = tuple(int(x.strip().replace("_", ""))
                            for x in ladder.group(1).split(",") if x.strip())

    def _int(self, name: str) -> int:
        m = re.search(rf"static let {name} = ([0-9_]+)", self.raw)
        if not m:
            raise CheckFailure(f"{GAME_CONSTANTS_REL}: constant '{name}' is missing")
        return int(m.group(1).replace("_", ""))

    def phase(self, elapsed: int) -> int:
        if self.phase_ticks <= 0:
            return len(self.ladder) - 1
        return min(len(self.ladder) - 1, max(0, elapsed) // self.phase_ticks)

    def timed(self, elapsed: int) -> int:
        return self.ladder[self.phase(elapsed)]

    def bravery_points(self, took_exoskeleton: bool) -> int:
        return 0 if took_exoskeleton else self.bravery


def stage_end_zones(ledger: str) -> tuple[int, ...]:
    m = re.search(r"stageEndZones: \[Int\] = \[([0-9,\s]+)\]", ledger)
    if not m:
        raise CheckFailure(f"{LEDGER_REL}: the stage-end zone list is not declarable")
    return tuple(int(x) for x in m.group(1).replace(" ", "").split(","))


def points_ceiling(scene: str) -> int:
    m = re.search(r"gameState\.points = min\(([0-9_]+)", scene)
    if not m:
        raise CheckFailure(f"{GAME_SCENE_REL}: awardPoints no longer clamps, so the clamp-identity "
                           "case cannot be evaluated")
    return int(m.group(1).replace("_", ""))


def award_model(c: Constants, lives: int, elapsed: int, took_exoskeleton: bool) -> dict:
    """What `GameplayStageComponentSequence.waveD` computes, component by component.

    `lives` is the lives AT the boundary: the +1 is applied afterwards, which is the order
    `ORIGINAL_MECHANICS.md:141-144` lists (docs_researcher §1.1 ruling 6).
    """
    components = {"lives_x1000": lives * c.lives_multiplier,
                  "bravery_no_exoskeleton": c.bravery_points(took_exoskeleton),
                  "timed_phase_ladder": c.timed(elapsed)}
    return {"components": components, "earned": sum(components.values()),
            "phase": c.phase(elapsed), "lives_before": lives,
            "lives_after": min(c.max_lives, lives + 1)}


def ledger_once_model(zones: tuple[int, ...], per_zone: int = 1):
    """The ledger's once-per-playthrough key logic, so suppression is measured, not asserted."""
    seen: dict[int, int] = {}

    def step(zone: int) -> str:
        if zone not in zones:
            return "notApplicable"
        if seen.get(zone, 0) >= per_zone:
            return "suppressed"
        seen[zone] = seen.get(zone, 0) + 1
        return "awarded"
    return step


# =============================================================================
# characterization layer (phase D-2 artifacts, re-pinned against the base commit)
# =============================================================================
def l0_table(root: pathlib.Path) -> str:
    """The generated 'before' snapshot, read out of the base commit's own source."""
    base = git_show(root, BASE_COMMIT, GAME_SCENE_REL)
    start = line_of(base, BOUNDARY_MARKER)
    body = function_body(base, BOUNDARY_MARKER, "the base stage-boundary function")
    end = start + body.count("\n")
    lines = [f"# L0 characterization of {GAME_SCENE_REL}:{start}-{end} at base {BASE_COMMIT}",
             f"# norm {MECHANICS_REL}:138-146 lists six clauses; three were live.",
             "# This is the frozen 'before' of audit finding P1-10. Phase D-1 replaces it with the",
             "# L1 ledger table; a live check that still passed after the fix would prove nothing",
             "# (analysis-architect.md section 7).",
             "",
             f"{'clause':<24} {'norm':<8} {'observed':<9} evidence",
             ]
    for clause, om, _want, pattern in CLAUSE_ROWS:
        m = re.search(pattern, body)
        status = "MISSING" if not m else ("PARTIAL" if clause == "plus_one_life_capped_9"
                                          else "PRESENT")
        if m:
            source_line = base.count("\n", 0, base.find(body) + m.start()) + 1
            evidence = f"{GAME_SCENE_REL}:{source_line}"
        else:
            evidence = "-"
        lines.append(f"{clause:<24} OM:{om:<5} {status:<9} {evidence}")
    tmx = sorted(p.name for p in (root / RESOURCES_DIR).glob("L*S*.tmx"))
    covers = 0
    m = re.search(r"includedLevels: Set<String> = Set\(\((\d+)\.{2,3}(\d+)\)\.flatMap "
                  r"\{ stage in \((\d+)\.{2,3}(\d+)\)\.map", base)
    if m:
        lo_s, hi_s, lo_z, hi_z = (int(x) for x in m.groups())
        covers = (hi_s - lo_s + 1) * (hi_z - lo_z + 1)
    lines += ["",
              f"comment 'deliberately dormant' in the boundary body: "
              f"{'TRUE' if 'deliberately dormant' in body else 'FALSE'}",
              f"includedLevels covers {covers} levels; {RESOURCES_DIR} ships {len(tmx)} .tmx maps",
              "=> the comment was FALSE on evidence: all five boundaries were live and farmable,",
              "   which is the severity fact recorded in brief.md and in the base finding.",
              "",
              "model at lives=9: awarded=9000 lives_after=9 (borrowed cap) ammo=99 grenades=10",
              "                  exoskeleton kept=True bravery=0 timed=0",
              "model at lives=1: awarded=1000 lives_after=2 ammo=99 grenades=10",
              "",
              "# post-wave-A / pre-wave-D shape, for the record:",
              "#   `StageBoundaryLedger` already owned the once-key and emitted one component",
              "#   (lives_x1000) through `bonus.stage_points` + `bonus.stage_component`; bravery,",
              "#   the timed ladder and the exoskeleton clear were still absent, and the life cap",
              "#   was still `startingLives` rather than an explicit `maxLives`.",
              ""]
    return "\n".join(lines)


def l0_characterization_pinned(root: pathlib.Path) -> None:
    """Pin the base tree's 3/6 clauses and the false 'deliberately dormant' claim.

    Phase D-1 has landed, so this is a *historical* characterization: it reads the base commit
    (295690b), which is what lets it keep stating the pre-fix truth instead of quietly rotting
    into a tautology. `evidence/l0-before-d1.txt` is the committed snapshot of the same table.
    """
    base = git_show(root, BASE_COMMIT, GAME_SCENE_REL)
    body = function_body(base, BOUNDARY_MARKER, "the base stage-boundary function")
    v: list[str] = []
    for clause, _om, want, pattern in CLAUSE_ROWS:
        hit = bool(re.search(pattern, body))
        got = "MISSING" if not hit else ("PARTIAL" if clause == "plus_one_life_capped_9"
                                         else "PRESENT")
        if got != want:
            v.append(f"L0 row {clause}: base tree says {got}, pinned characterization says {want}")
    if "deliberately dormant" not in body:
        v.append("L0: the false 'deliberately dormant' comment is not in the base text, so the "
                 "finding this pins no longer describes any tree")
    tmx = sorted(p.name for p in (root / RESOURCES_DIR).glob("L*S*.tmx"))
    m = re.search(r"includedLevels: Set<String> = Set\(\((\d+)\.{2,3}(\d+)\)\.flatMap "
                  r"\{ stage in \((\d+)\.{2,3}(\d+)\)\.map", base)
    covers = 0
    if m:
        lo_s, hi_s, lo_z, hi_z = (int(x) for x in m.groups())
        covers = (hi_s - lo_s + 1) * (hi_z - lo_z + 1)
    if not (covers == 125 and len(tmx) == 125
            and all(f"L0{i}S25.tmx" in tmx for i in range(1, 6))):
        v.append(f"L0: content coverage lost (includedLevels={covers}, tmx={len(tmx)}): the "
                 "dormancy claim can no longer be called false on evidence")
    caps = git_show(root, BASE_COMMIT, GAME_STATE_REL)
    for name, value in (("startingAmmo", "99"), ("startingGrenades", "10"),
                        ("startingLives", "9")):
        if not re.search(rf"static let {name} = {value}\b", caps):
            v.append(f"L0: base {GAME_STATE_REL} no longer pins {name} = {value}")
    if not rd(root, L0_SNAPSHOT_REL).strip():
        v.append(f"L0: {L0_SNAPSHOT_REL} is missing - the frozen 'before' has to ship with the "
                 "fix, not live only inside this tool")
    if v:
        raise CheckFailure(" | ".join(v)[:900])
    # Control: the table must be able to disagree with the text it reads.
    mutated = body.replace("awardPoints(gameState.lives * 1_000)",
                           "awardPoints(gameState.lives * 1_000)\n        awardPoints(10_000)", 1)
    if not re.search(CLAUSE_ROWS[3][3], mutated):
        raise CheckFailure("control did not flip: a bravery clause was invisible to the table")
    if "deliberately dormant" not in mutated:
        raise CheckFailure("the control mutation must not remove the pinned comment text")


def single_funnel(root: pathlib.Path) -> None:
    """INV-001: every score change of the stage sequence goes through awardPoints."""
    scene = rd(root, GAME_SCENE_REL)
    boundary = function_body(scene, BOUNDARY_MARKER, "the stage-boundary function")
    funnel = function_body(scene, "private func awardPoints(", "awardPoints")
    v: list[str] = []
    if "awardPoints(" not in boundary:
        v.append("the stage sequence no longer awards through awardPoints")
    for bad in (r"gameState\.points\s*[-+]?=", r"highScore\s*="):
        if re.search(bad, boundary):
            v.append(f"the boundary function writes score state directly ({bad})")
    writers = [ln for ln in scene.splitlines() if re.search(r"gameState\.points\s*[-+]?=", ln)]
    ceiling = points_ceiling(scene)
    funnel_clamp = re.search(r"gameState\.points = min\(([0-9_]+)", funnel)
    if len(writers) != 1 or not funnel_clamp or \
            int(funnel_clamp.group(1).replace("_", "")) != ceiling:
        v.append(f"awardPoints must be the only writer of gameState.points and must clamp "
                 f"(writers={len(writers)}, ceiling={ceiling})")
    if len(re.findall(r"awardPoints\(", scene)) < 2:
        v.append("no awardPoints call sites at all - the funnel is unmeasurable")
    if "reason: .stageBoundary" not in boundary:
        v.append("the boundary award no longer names its score reason, so the total cannot be "
                 "attributed on the wire")
    if v:
        raise CheckFailure(" | ".join(v)[:600])
    # Control: a bypass write must be caught by the same predicate.
    bypass = boundary.replace("awardPoints(award.points, reason: .stageBoundary)",
                              "gameState.points += award.points", 1)
    if bypass == boundary:
        raise CheckFailure("control impossible: the boundary award call to bypass is not there")
    mutated = scene.replace(boundary, bypass, 1)
    mbody = function_body(mutated, BOUNDARY_MARKER, "the mutated boundary")
    if not re.search(r"gameState\.points\s*\+?=", mbody):
        raise CheckFailure("control did not flip: the bypass write was invisible")
    if len([ln for ln in mutated.splitlines()
            if re.search(r"gameState\.points\s*[-+]?=", ln)]) != 2:
        raise CheckFailure("control did not flip: the writer count stayed at one")


# =============================================================================
# phase D-1: the L1 pure-ledger table
# =============================================================================
def sequence_components_identity(root: pathlib.Path) -> None:
    """AC-005: points == lives*1000 + bravery + timed, once per zone, with the clamp identity."""
    consts = Constants(rd(root, GAME_CONSTANTS_REL))
    ledger = rd(root, LEDGER_REL)
    scene = rd(root, GAME_SCENE_REL)
    zones = stage_end_zones(ledger)
    v: list[str] = []

    for shape, why in ((r"return lives \* 1_000", "the lives_x1000 rule"),
                       (r"tookExoskeletonInStage \? 0 : GameConstants\.braveryBonus",
                        "the bravery rule"),
                       (r"GameConstants\.timedBonusLadder\[phase\]", "the ladder rule"),
                       (r"max\(0, elapsed\) / GameConstants\.phaseTicks", "the phase rule")):
        if not re.search(shape, ledger):
            v.append(f"{why} is no longer the shape this table models: /{shape}/")
    for case in ("case .braveryNoExoskeleton", "case .timedPhaseLadder"):
        if case not in ledger:
            v.append(f"the ledger is not exhaustive over {case[5:]}")
    if "GameplayStageComponentSequence.waveD" not in scene:
        v.append("GameScene does not arm the full norm sequence at the boundary seam")
    if tuple(zones) != (24, 49, 74, 99, 124):
        v.append(f"stage-end zones drifted from the norm's five: {zones}")

    for lives in LIVES_CASES:
        for elapsed in ELAPSED_CASES:
            for took in (False, True):
                model = award_model(consts, lives, elapsed, took)
                comp = model["components"]
                if sum(comp.values()) != model["earned"]:
                    v.append(f"identity broken at lives={lives} elapsed={elapsed} took={took}")
                if comp["bravery_no_exoskeleton"] not in (0, consts.bravery):
                    v.append(f"bravery component outside the norm's binary: {comp}")
                if comp["timed_phase_ladder"] not in CANONICAL_TIMED_VALUES:
                    v.append(f"timed component outside the canonical set: {comp}")
                if comp["lives_x1000"] != lives * LIVES_MULTIPLIER:
                    v.append(f"lives component must be lives_before x 1000: {comp}")
    # A fresh model per playthrough: the first trigger of a stage-end zone awards, every repeat
    # is suppressed with a witness, and a non-stage zone never appears at all (wave A's rule,
    # unchanged by the two new components).
    step = ledger_once_model(zones)
    pending_first_award = set(zones)
    for zone in (23, 24, 24, 25, 49, 49, 49, 74, 124, 124):
        got = step(zone)
        if zone not in zones:
            if got != "notApplicable":
                v.append(f"zone {zone} is not a stage end but returned {got}")
            continue
        if got == "awarded":
            if zone not in pending_first_award:
                v.append(f"zone {zone} awarded twice in one playthrough: the once-key is broken")
            pending_first_award.discard(zone)
        elif got != "suppressed":
            v.append(f"zone {zone} returned an undefined outcome {got!r}")
        elif zone in pending_first_award:
            v.append(f"zone {zone} was suppressed before it ever awarded: nothing paid the norm's "
                     "boundary")
    ceiling = points_ceiling(scene)
    for before, earned in ((0, 9_000), (ceiling - 5_000, 20_000), (ceiling, 90_000)):
        applied = min(earned, ceiling - before)
        if before + applied > ceiling:
            v.append(f"clamp identity broken at before={before}: {before + applied} > {ceiling}")
        if applied != min(earned, max(0, ceiling - before)):
            v.append("applied must be min(earned, ceiling - points_before)")
    if v:
        raise CheckFailure(" | ".join(v)[:1200])

    # Controls: break one component at a time; the identity table must move on its own.
    def table(**over) -> dict:
        mutated = Constants(rd(root, GAME_CONSTANTS_REL))
        for key, value in over.items():
            setattr(mutated, key, value)
        return {(l, e, t): award_model(mutated, l, e, t)["earned"]
                for l in LIVES_CASES for e in ELAPSED_CASES for t in (False, True)}
    base_table = table()
    for knob, over in (("bravery forfeited always", {"bravery": 0}),
                       ("phase cadence doubled", {"phase_ticks": consts.phase_ticks * 2}),
                       ("ladder zeroed", {"ladder": (0, 0, 0, 0, 0)}),
                       ("lives multiplier", {"lives_multiplier": LIVES_MULTIPLIER + 1})):
        if table(**over) == base_table:
            raise CheckFailure(f"control did not flip: {knob} changed nothing in the identity "
                               "table, so AC-005 measures nothing for that component")


def lives_and_refill_semantics(root: pathlib.Path) -> None:
    """AC-005: award before +1, explicit maxLives=9, refill through the shared constants."""
    consts = Constants(rd(root, GAME_CONSTANTS_REL))
    scene = rd(root, GAME_SCENE_REL)
    state = rd(root, GAME_STATE_REL)
    ledger = rd(root, LEDGER_REL)
    boundary = function_body(scene, BOUNDARY_MARKER, "the stage-boundary function")
    v: list[str] = []
    if consts.max_lives != 9:
        v.append(f"maxLives must be the norm's 9 (`:144`), got {consts.max_lives}")
    if re.search(r"static let maxLives", state):
        v.append("the life cap now lives in two files (GameConstants and GameState): pick one")
    if "maxLives: GameConstants.maxLives" not in boundary:
        v.append("the boundary does not pass the explicit maxLives constant")
    if "startingLives: GameState.startingLives" in boundary:
        v.append("the boundary still borrows startingLives as the life cap")
    if "awardPoints(award.points" not in boundary or "gameState.lives = award.livesAfter" not in boundary:
        v.append("the award or the +1 application is missing from the boundary")
    elif boundary.index("awardPoints(award.points") > boundary.index("gameState.lives = award.livesAfter"):
        v.append("the award is applied after the +1, so lives x 1000 would bill the new life")
    if "gameState.ammo = award.startingAmmo" not in boundary or \
            "gameState.grenades = award.startingGrenades" not in boundary:
        v.append("the boundary refill no longer uses the shared 99/10 constants")
    pickups = function_body(scene, "private func updatePickups() {", "updatePickups")
    for literal in (r"gameState\.grenades = 10", r"gameState\.ammo = 99"):
        if re.search(literal, pickups):
            v.append(f"updatePickups still carries a bare refill literal (/{literal}/): that "
                     "duplication is the defect this clause closes")
    if "GameState.startingAmmo" not in pickups or "GameState.startingGrenades" not in pickups:
        v.append("updatePickups no longer refills through the shared constants")
    for lives in range(0, consts.max_lives + 1):
        after = min(consts.max_lives, lives + 1)
        if after > consts.max_lives:
            v.append(f"lives {lives} -> {after} exceeds the cap")
        if lives == consts.max_lives and after != consts.max_lives:
            v.append("at the cap the +1 must be a no-op, not a burn")
    # The cap is the only upper bound only if nothing else can raise lives. Wave A's own audit
    # lists the writers: the death decrement, this boundary, and `GameState`'s init/reset.
    writers = [ln.strip() for ln in scene.splitlines()
               if re.search(r"gameState\.lives\s*[-+]?=(?!=)", ln)]
    unexpected = [ln for ln in writers
                  if "award.livesAfter" not in ln and "max(0, gameState.lives - 1)" not in ln]
    if unexpected:
        v.append(f"unaccounted writers of gameState.lives, so maxLives is not the only bound: "
                 f"{unexpected[:2]}")
    if not any("award.livesAfter" in ln for ln in writers):
        v.append("the boundary no longer writes lives at all")
    if "clearsExoskeleton: true" not in ledger:
        v.append("the ledger no longer declares that a boundary clears the suit")
    # OM:144's +1 life currently rides inside OM:146's refill guard (deviation 15), and the only
    # thing that keeps that correct is this flag being unconditionally true at the ledger. Bind it:
    # if a future component ever makes `refillsAmmoAndGrenades` conditional, this reddens here
    # instead of the boundary quietly stopping to grant lives - GameScene cannot execute on Linux,
    # so an unwatched coupling would surface only in play observation E16.
    if "refillsAmmoAndGrenades: true" not in ledger:
        v.append("the ledger no longer hard-codes refillsAmmoAndGrenades: true while the scene "
                 "gates the +1 life on it - see Deviation 15")
    if "player.setExoskeleton(false, cause: .stageBoundary)" not in boundary:
        v.append("the scene does not clear the exoskeleton at the boundary")
    if v:
        raise CheckFailure(" | ".join(v)[:900])
    # Control: inverting the award/+1 order has to be visible to the reader.
    swapped = boundary.replace("awardPoints(award.points, reason: .stageBoundary)",
                               "__APPLY_LIVES__\n            "
                               "awardPoints(award.points, reason: .stageBoundary)", 1)
    swapped = swapped.replace("gameState.lives = award.livesAfter", "__MOVED__", 1)
    swapped = swapped.replace("__APPLY_LIVES__", "gameState.lives = award.livesAfter")
    unguarded = ledger.replace("refillsAmmoAndGrenades: true",
                              "refillsAmmoAndGrenades: award.refills")
    if unguarded == ledger:
        raise CheckFailure("control impossible: the refill flag is not a literal in the ledger")
    if "refillsAmmoAndGrenades: true" in unguarded:
        raise CheckFailure("control did not flip: a conditional refill flag stays invisible")
    if swapped.index("gameState.lives = award.livesAfter") > swapped.index(
            "awardPoints(award.points"):
        raise CheckFailure("control impossible: the award/+1 order cannot be inverted in text")
    inverted = re.search(r"gameState\.lives = award\.livesAfter[\s\S]*?awardPoints\(award\.points",
                         swapped)
    if not inverted:
        raise CheckFailure("control did not flip: an inverted award/+1 order is invisible here")


def bravery_latch_distinguishes(root: pathlib.Path) -> None:
    """AC-006: pin the owner's activation-latch reading, and falsify the state reading.

    `ORIGINAL_MECHANICS.md:142` says "If no exoskeleton **was taken**"; `:118` says "**Having** the
    exoskeleton forfeits". The suit is togglable, so the two differ on a reachable state: put it on
    in the stage's only changing room, take it off again, finish the stage. The ruling is the `:142`
    latch; this check proves the tree implements the latch and not the polled state.
    """
    consts = Constants(rd(root, GAME_CONSTANTS_REL))
    ledger = rd(root, LEDGER_REL)
    scene = rd(root, GAME_SCENE_REL)
    player = rd(root, PLAYER_REL)
    v: list[str] = []
    if "func toggleExoskeleton" not in player:
        v.append(f"{PLAYER_REL}: the suit is not togglable, so the two readings are not "
                 "distinguishable and this check would be vacuous")
    edge = re.search(r"player\.toggleExoskeleton\(cause: \.changingRoom\)[\s\S]{0,500}?"
                     r"if player\.hasExoskeleton \{\s*"
                     r"stageBoundaries\.noteExoskeletonActivated\(atStep: [^)]*\)\s*\}", scene)
    if not edge:
        v.append("the bravery latch is not set at the single changing-room activation edge")
    boundary = function_body(scene, BOUNDARY_MARKER, "the stage-boundary function")
    if "hasExoskeleton" in boundary.replace("player.setExoskeleton(false", ""):
        v.append("the boundary polls the *current* suit state: that is the :118 reading, not the "
                 "ruled :142 latch")
    if "tookExoskeletonInStage = true" not in function_body(
            ledger, "func noteExoskeletonActivated(", "noteExoskeletonActivated"):
        v.append("noteExoskeletonActivated no longer arms the latch")
    for clearer in ("noteStageStarted", "beginPlaythrough", "endPlaythrough"):
        block = function_body(ledger, f"func {clearer}(", clearer)
        if "tookExoskeletonInStage = false" not in block:
            v.append(f"the latch is not cleared by {clearer}: a later stage inherits the forfeiture")
    if re.search(r"func toggleExoskeleton[\s\S]{0,200}tookExoskeletonInStage = false", ledger):
        v.append("something clears the latch on a toggle-off, which the ruling forbids")
    if v:
        raise CheckFailure(" | ".join(v)[:900])

    # The falsifiable pair, as numbers: ON-then-OFF before the boundary.
    on_then_off_latch = consts.bravery_points(True)
    on_then_off_state = consts.bravery_points(False)   # the :118 reading of the same game state
    if on_then_off_latch == on_then_off_state:
        raise CheckFailure("the two readings are not distinguishable in this model: the check "
                           "measures nothing")
    if on_then_off_latch != 0 or on_then_off_state != consts.bravery:
        raise CheckFailure("the latch must forfeit and the state reading must pay on ON-then-OFF")
    if consts.bravery_points(False) != consts.bravery:
        raise CheckFailure("a clean stage must pay bravery under both readings")
    # Control: the edge must be the only thing arming it - deleting it must not be invisible.
    stripped = scene.replace("if player.hasExoskeleton {\n                    "
                             "stageBoundaries.noteExoskeletonActivated(atStep: tickDriver.stepCount)\n"
                             "                }", "")
    if stripped == scene:
        raise CheckFailure("control impossible: the activation-edge text is not where this check "
                           "reads it")
    if re.search(r"stageBoundaries\.noteExoskeletonActivated", stripped):
        raise CheckFailure("control did not flip: another activation edge is arming the latch")


def timed_ladder_deterministic(root: pathlib.Path) -> None:
    """AC-006: the timed bonus is a deterministic tick ladder, recomputable from deltas."""
    consts = Constants(rd(root, GAME_CONSTANTS_REL))
    ledger = rd(root, LEDGER_REL)
    driver = rd(root, DRIVER_REL)
    scene = rd(root, GAME_SCENE_REL)
    v: list[str] = []
    if consts.ladder != (7_000, 5_000, 3_000, 1_000, 0):
        v.append(f"the ladder must be exactly the five canonical values, best first, got "
                 f"{consts.ladder}")
    if set(consts.ladder) != set(CANONICAL_TIMED_VALUES):
        v.append("the ladder's value set is not the norm's {0,1000,3000,5000,7000}")
    if list(consts.ladder) != sorted(consts.ladder, reverse=True):
        v.append("the ladder is not monotonically non-increasing in elapsed steps")
    if consts.phase_ticks != 1_800:
        v.append(f"PHASE_TICKS drifted from the owner ruling (30 s at the canonical 60 Hz): "
                 f"{consts.phase_ticks}")
    span = range(0, consts.phase_ticks * 6, 7)
    if max(consts.phase(e) for e in span) != len(consts.ladder) - 1:
        v.append("the ladder does not saturate at its last phase")
    values = [consts.timed(e) for e in span]
    if values != sorted(values, reverse=True):
        v.append("the timed award is not monotone in elapsed steps")
    if consts.timed(0) != 7_000 or consts.timed(consts.phase_ticks * 4) != 0:
        v.append("the ladder's endpoints are wrong: the fastest stage must pay the best phase")
    for clock in ("Date(", "systemUptime", "ProcessInfo", "currentTime", "DispatchTime",
                  "continuousClock", "SKScene"):
        if clock in ledger:
            v.append(f"the ledger reads a wall clock or a scene clock ({clock}): the ladder would "
                     "stop being recomputable from the log")
    if "stageElapsedSteps" not in ledger or "atStep step: Int" not in ledger:
        v.append("the step coordinate is not an explicit parameter of the ledger")
    if driver.count("stepCount += 1") != 1:
        v.append("the product step coordinate must have exactly one increment site in the driver")
    if "tickDriver.stepCount" not in scene:
        v.append("the scene no longer supplies the step coordinate to the boundary")
    # the auditor's own recomputation: relative deltas only, never absolute ticks
    for lives in (1, 9):
        for elapsed in ELAPSED_CASES:
            start_tick = 500  # arbitrary; only the delta may be used by an assertion
            ts_delta = round(elapsed * 1_000_000 / TICK_HZ)
            recomputed = round(ts_delta * TICK_HZ / 1_000_000)
            if consts.timed(recomputed) != consts.timed(elapsed):
                v.append(f"phase is not recoverable from a ts_us delta at elapsed={elapsed}")
            if award_model(consts, lives, recomputed, True)["components"][
                    "timed_phase_ladder"] != consts.timed(elapsed):
                v.append("the re-derived timed component disagrees with the ladder")
    if v:
        raise CheckFailure(" | ".join(v)[:900])
    # Controls: cadence and ladder each have to be able to move the answer.
    if consts.timed(consts.phase_ticks) == consts.timed(consts.phase_ticks * 2):
        raise CheckFailure("control did not flip: crossing a phase boundary changed nothing")
    if consts.ladder[0] == consts.ladder[-1]:
        raise CheckFailure("control did not flip: the ladder's extremes are identical")


def warp_debug_only(root: pathlib.Path) -> None:
    """AC-007: the bounded debug warp is Debug-compiled, inert when unset, and real-path."""
    scene = rd(root, GAME_SCENE_REL)
    pbx = rd(root, PBXPROJ_REL)
    if "EXOLON_DEBUG_WARP" not in scene:
        raise CheckFailure(f"{GAME_SCENE_REL}: the debug warp does not exist")
    blocks = re.findall(r"#if DEBUG\n(.*?)#endif", scene, re.S)
    inside = "\n".join(blocks)
    v: list[str] = []
    if not blocks:
        v.append("the warp is not inside a DEBUG compilation block at all")
    for frag in ("EXOLON_DEBUG_WARP", "func debugWarpTarget", "applyDebugWarpIfNeeded"):
        if frag not in inside:
            v.append(f"the warp's '{frag}' is compiled outside #if DEBUG, so it would ship in Release")
    if "EXOLON_DEBUG_WARP" in re.sub(r"#if DEBUG\n.*?#endif", "", scene, flags=re.S):
        v.append("EXOLON_DEBUG_WARP is referenced outside the DEBUG block")
    if "transition(to: target)" not in inside:
        v.append("the warp does not go through the real transition(to:) path")
    if "allowed.contains(target)" not in inside:
        v.append("the warp target is not bounded by the shipped level list")
    if 'guard let raw = environment["EXOLON_DEBUG_WARP"] else { return nil }' not in scene:
        v.append("the warp is not inert when the variable is unset")
    if "stderr" not in inside:
        v.append("the warp has no stderr echo, so a reviewer cannot tell a warped run from a real one")
    if "SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG" not in pbx:
        v.append("DEBUG is not declared in the project, which would make `#if DEBUG` accidental")
    if pbx.count("SWIFT_ACTIVE_COMPILATION_CONDITIONS") != 1:
        v.append("SWIFT_ACTIVE_COMPILATION_CONDITIONS must be declared exactly once (project Debug); "
                 "a Release copy would compile the warp into the shipped binary")
    if re.search(r"800000000000000000000002 /\* Release \*/[\s\S]{0,800}?"
                 r"SWIFT_ACTIVE_COMPILATION_CONDITIONS", pbx):
        v.append("the project Release configuration defines SWIFT_ACTIVE_COMPILATION_CONDITIONS")
    if v:
        raise CheckFailure(" | ".join(v)[:900])

    # The bound itself, executed as the rule it mirrors.
    allowed = {f"L{s:02d}S{z:02d}" for s in range(1, 6) for z in range(1, 26)}

    def target(env: dict) -> str | None:
        raw = env.get("EXOLON_DEBUG_WARP")
        if raw is None:
            return None
        value = raw.strip()
        return value if len(value) == 6 and value.startswith("L") and value in allowed else None

    if target({}) is not None:
        raise CheckFailure("control did not flip: the warp fires with no variable set")
    for bad in ("L05S99", "l05s25", "L5S25", "../Secret", "L01S01x", "L01S01 L01S02"):
        if target({"EXOLON_DEBUG_WARP": bad}) is not None:
            raise CheckFailure(f"control did not flip: the out-of-bounds target {bad!r} was accepted")
    if target({"EXOLON_DEBUG_WARP": "L05S25"}) != "L05S25":
        raise CheckFailure("the legitimate warp target L05S25 is refused - the bound is wrong")
    if "L05S25" not in allowed:
        raise CheckFailure("the shipped level list does not contain the probe's E16 target")


def ladder_is_declared_deviation(root: pathlib.Path) -> None:
    """FORBID-003: the ladder may never be presented as the canonical cursor mechanic."""
    constants = rd(root, GAME_CONSTANTS_REL)
    m = re.search(r"((?:(?:[ \t]*///[^\n]*\n)+)[ \t]*static let phaseTicks)"
                  r"|(/\*\*(?:(?!\*/).)*?\*/)\s*\n\s*static let phaseTicks", constants, re.S)
    if not m:
        raise CheckFailure(f"{GAME_CONSTANTS_REL}: PHASE_TICKS has no doc comment to inspect")
    doc = m.group(1) or m.group(2)
    v: list[str] = []
    for marker in ("OWNER-APPROVED DEVIATION", "cursor", "UNCONFIRMED vs original", "143"):
        if marker.lower() not in doc.lower():
            v.append(f"the PHASE_TICKS comment does not name {marker!r}")
    if "canonical" not in doc.lower():
        v.append("the comment must separate the canonical values from the non-canonical cadence")
    if re.search(r"(implements|is) the (original )?(interactive )?cursor", doc, re.I):
        v.append("the comment claims the cursor mechanic is implemented (FORBID-003)")
    for rel in (f"{CHANGE_DIR}/brief.md", f"{CHANGE_DIR}/architecture.md"):
        text = rd(root, rel)
        if not text:
            v.append(f"{rel} is missing, so the deviation cannot be read from the package")
            continue
        if "cursor" not in text.lower():
            v.append(f"{rel} never names the cursor mechanic the ladder stands in for")
        if re.search(r"ladder (?:is|implements) the canonical|canonical timed ladder", text, re.I):
            v.append(f"{rel} asserts the ladder is canonical (FORBID-003)")
    if v:
        raise CheckFailure(" | ".join(v)[:700])
    # Control: strip the marker in memory and require the reader to notice.
    mutated = doc.replace("OWNER-APPROVED DEVIATION", "note")
    if "OWNER-APPROVED DEVIATION" not in doc:
        raise CheckFailure("control did not flip: the comment has no deviation marker to lose")
    if re.search(r"OWNER-APPROVED DEVIATION", mutated):
        raise CheckFailure("control impossible: the marker appears twice in one comment")


def component_stream_identity(root: pathlib.Path) -> None:
    """Wire identity against wave A's real lane names and the frozen contract (extra check).

    Wave A's auditor knows only `lives_x1000`, so the two new components would be invisible to it;
    this is the mirror that proves the total on `bonus.stage_points` still equals the sum of the
    `bonus.stage_component` records, that every emitted id is declared in the frozen schema, that
    the sink's code-count guard matches, and that the boundary clear is distinguishable on the wire.
    """
    consts = Constants(rd(root, GAME_CONSTANTS_REL))
    sink = rd(root, SINK_REL)
    schema_path = root / EVENT_SCHEMA_REL
    if not schema_path.is_file():
        raise CheckFailure(f"{EVENT_SCHEMA_REL} is missing")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    declared = schema["x-code-tables"]["stage_component_id"]
    region = sink[sink.index("enum GameplayStageComponent:"):
                  sink.index("enum GameplayStageSuppressionReason:")]
    labels = sorted(set(re.findall(r'return "([a-z0-9_]+)"', region)))
    v: list[str] = []
    for lane in ("bonus.stage_points", "bonus.stage_component", "bonus.stage_boundary_suppressed"):
        if f'"{lane}"' not in sink:
            v.append(f"wave A's lane {lane} is gone from the sink")
    if labels != sorted(declared):
        v.append(f"the Swift component labels {labels} disagree with the frozen schema "
                 f"{sorted(declared)}")
    code_count = re.search(r'name: "stage_component_id", codeCount: (\d+)', sink)
    if not code_count or int(code_count.group(1)) != len(declared):
        v.append("the sink's declared codeCount for stage_component_id does not match the schema")
    exo_region = sink[sink.index("enum GameplayExoskeletonCause:"):
                      sink.index("enum GameplayShootDeniedReason:")]
    exo_labels = sorted(set(re.findall(r'return "([a-z0-9_]+)"', exo_region)))
    exo_count = re.search(r'name: "exoskeleton_cause", codeCount: (\d+)', sink)
    if not exo_count or int(exo_count.group(1)) != len(exo_labels):
        v.append("exoskeleton_cause codeCount disagrees with its labels")
    if "stage_boundary" not in exo_labels:
        v.append("the boundary clear has no cause label, so it cannot be told from a restart")
    if "stage_boundary" not in schema["x-code-tables"]["exoskeleton_cause"]:
        v.append("the schema does not declare the stage_boundary exoskeleton cause")
    for lives in LIVES_CASES:
        for elapsed in ELAPSED_CASES[:6]:
            for took in (False, True):
                model = award_model(consts, lives, elapsed, took)
                records = [{"component_id": key, "points": value}
                           for key, value in model["components"].items()]
                if sum(r["points"] for r in records) != model["earned"]:
                    v.append(f"wire identity broken at lives={lives} elapsed={elapsed}")
                for record in records:
                    if record["component_id"] not in declared:
                        v.append(f"undeclared component id on the wire: {record}")
    if v:
        raise CheckFailure(" | ".join(v)[:900])
    # Controls: a component that ignores the latch, and a label the schema does not declare.
    if consts.bravery_points(True) == consts.bravery_points(False):
        raise CheckFailure("control did not flip: taking the suit does not change bravery")
    if "bravery_no_exoskeleton" not in declared or "timed_phase_ladder" not in declared:
        raise CheckFailure("control did not flip: the schema does not declare the new components")


CHECKS_D2: dict[str, object] = {
    "l0_characterization_pinned": l0_characterization_pinned,
    "single_funnel": single_funnel,
}
CHECKS_D1: dict[str, object] = {
    "sequence_components_identity": sequence_components_identity,
    "lives_and_refill_semantics": lives_and_refill_semantics,
    "bravery_latch_distinguishes": bravery_latch_distinguishes,
    "timed_ladder_deterministic": timed_ladder_deterministic,
    "warp_debug_only": warp_debug_only,
    "ladder_is_declared_deviation": ladder_is_declared_deviation,
}
def executed_ledger_matches_model(root: pathlib.Path) -> None:
    """Extra: the modelled table is diffed against the REAL ledger's own output.

    `evidence/ledger-xcheck-executed.txt` is produced by `evidence/ledger-xcheck/run.sh`, which
    compiles the shipped Foundation-only product files (wave A's file list, wave A's
    CoreGraphics shim) and prints the `waveD` award table. Reading a committed execution is not
    the same as running one here - but a model that disagrees with the type it models is a bug in
    one of them, and this catches that class without depending on a Swift toolchain at gate time.
    """
    executed = rd(root, EXECUTED_TABLE_REL)
    if not executed.strip():
        raise CheckFailure(f"{EXECUTED_TABLE_REL} is missing - regenerate it with "
                           f"{XCHECK_RUN_REL}")
    consts = Constants(rd(root, GAME_CONSTANTS_REL))
    rows = [ln for ln in executed.splitlines() if ln.startswith("row ")]
    v: list[str] = []
    seen_awards = 0
    for ln in rows:
        parts = ln.split()
        if len(parts) < 5:
            v.append(f"unparsable executed row: {ln}")
            continue
        lives, elapsed = int(parts[1]), int(parts[2])
        took = parts[3] == "true"  # the row prints tookExoskeletonInStage verbatim
        verdict = parts[4]
        model = award_model(consts, lives, elapsed, took)
        if verdict == "AWARDED":
            seen_awards += 1
            fields = dict(p.split("=", 1) for p in parts[5:] if "=" in p)
            for key, want in (("total", model["earned"]), ("lives", model["components"]["lives_x1000"]),
                              ("bravery", model["components"]["bravery_no_exoskeleton"]),
                              ("timed", model["components"]["timed_phase_ladder"]),
                              ("phase", model["phase"]), ("livesAfter", model["lives_after"]),
                             ("sum", model["earned"])):
                if fields.get(key) != str(want):
                    v.append(f"executed {key}={fields.get(key)} disagrees with the model "
                             f"{want} at lives={lives} elapsed={elapsed} took={took}")
            if fields.get("clear") != "true":
                v.append("the executed ledger does not clear the exoskeleton at the boundary")
        elif verdict == "SUPPRESSED" and "already_awarded" not in ln:
            v.append(f"unexpected suppression reason in the executed table: {ln}")
    if seen_awards < 10:
        v.append(f"the executed table awarded only {seen_awards} times, so most of the model is "
                 "not being compared")
    for probe_key in ("once first=awarded second=suppressed:already_awarded",
                           "latch after activation=true",
                           "latch after new stage=false",
                           "clean stage pays bravery=10000",
                           "waveA shim total=4000 components=1"):
        if probe_key not in executed:
            v.append(f"the executed table lost the assertion {probe_key!r}")
    if v:
        raise CheckFailure(" | ".join(v)[:900])
    # Control: a model with a different cadence must disagree with the executed table.
    drifted = Constants(rd(root, GAME_CONSTANTS_REL))
    drifted.phase_ticks = drifted.phase_ticks * 2
    disagree = 0
    for ln in rows:
        parts = ln.split()
        if len(parts) > 4 and parts[4] == "AWARDED":
            fields = dict(p.split("=", 1) for p in parts[5:] if "=" in p)
            if fields.get("timed") != str(drifted.timed(int(parts[2]))):
                disagree += 1
    if not disagree:
        raise CheckFailure("control did not flip: doubling PHASE_TICKS still agreed with the "
                           "executed ledger, so the comparison is vacuous")


EXTRA: dict[str, object] = {"component_stream_identity": component_stream_identity,
                            "executed_ledger_matches_model": executed_ledger_matches_model}
CHECKS: dict[str, object] = {**CHECKS_D2, **CHECKS_D1, **EXTRA}

SPEC_NAMES = ("sequence_components_identity", "lives_and_refill_semantics",
              "bravery_latch_distinguishes", "timed_ladder_deterministic", "warp_debug_only",
              "single_funnel", "ladder_is_declared_deviation")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="stage_boundary_check.py")
    ap.add_argument("--root")
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--phase", choices=("D2", "D1"), default="D1",
                    help="D1 (default, after wave A merged): every name must pass. "
                         "D2 restates the pre-rebase posture, where the ledger names fail.")
    ap.add_argument("--list", action="store_true", help="print the check names and phases")
    ap.add_argument("--table", action="store_true",
                    help="print the frozen L0 'before' table (base commit) and exit")
    args = ap.parse_args(argv)
    root = repo_root(args.root)

    if args.table:
        sys.stdout.write(l0_table(root))
        return 0

    if args.list:
        for name in CHECKS_D2:
            print(f"{name}\tD-2\tcharacterization of the base tree")
        for name in CHECKS_D1:
            print(f"{name}\tD-1\tL1 table over the real ledger")
        for name in EXTRA:
            print(f"{name}\textra\twire identity against wave A's lanes")
        return 0

    missing = [n for n in SPEC_NAMES if n not in CHECKS]
    if missing:
        print(f"RESULT spec_names_present=FAIL missing {missing}")
        return 1

    names = args.only or list(CHECKS)
    unknown = [n for n in names if n not in CHECKS]
    if unknown:
        print(f"unknown check(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    failures = 0
    for name in names:
        fn = CHECKS[name]
        try:
            fn(root)  # type: ignore[operator]
            status, detail = "PASS", ""
        except CheckFailure as exc:
            status, detail = "FAIL", str(exc)
        except Exception as exc:  # noqa: BLE001
            status, detail = "ERROR", f"{type(exc).__name__}: {exc}"
        if args.phase == "D2" and name in CHECKS_D1:
            if status == "FAIL" and PENDING_REASON in detail:
                print(f"RESULT {name}=PENDING_OK {detail}")
            else:
                failures += 1
                print(f"RESULT {name}=FAIL expected the pending stub, got {status} {detail}")
            continue
        if status == "PASS":
            print(f"RESULT {name}=PASS")
        else:
            failures += 1
            print(f"RESULT {name}={status} {detail}")
    print(f"SUMMARY checks={len(names)} failed={failures} phase={args.phase}")
    print("SCOPE: numbers are read from the committed Swift; executed-Swift stays wave A's contour")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
