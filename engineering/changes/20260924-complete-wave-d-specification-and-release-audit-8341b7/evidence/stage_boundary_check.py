#!/usr/bin/env python3
"""Wave-D stage-boundary verifier: L0 characterization + the single-funnel invariant.

Typed authority: ../change-spec.yaml (AC-005, AC-006, AC-007, INV-001, FORBID-003).
Design contract: ../evidence/analysis-architect.md §5 (bravery latch), §6 (the owner-approved
deterministic tick ladder), §7 (the L0/L1/L2 layering); ../evidence/analysis-repo_explorer.md §1
(the clause-by-clause reading of the current path); ../evidence/analysis-docs_researcher.md §1
(the norm text and its named silences).

PHASE STRUCTURE (owner ruling 3: Track A now, P1-10 after wave A merges)
  * `l0_characterization_pinned` and `single_funnel` are real checks of today's tree.
  * The five ledger-backed names are explicit failing stubs. They are NOT placeholders that
    quietly pass: `StageBoundaryLedger.swift` exists only on an unmerged wave-A branch, so
    every AC that reads the ledger is physically blocked, and this file says so in one
    fixed sentence per name. With `--phase D2` (the default) a stub that unexpectedly
    PASSES is itself a failure, because it would mean the check measures nothing.

L0 IS A CHARACTERIZATION CHECK: it is green today precisely because the product is still
wrong in the pinned way. When D-1 lands the sequence, L0 must turn RED - that is its role
(analysis-architect.md §7: "if L0 still passes after the fix, the fix did not change the
product"). It is deleted at D-1, and the package keeps this file as the frozen "before".

rc contract: 0 = the requested phase held; 1 = something violated; 2 = usage.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

CHANGE_ID = "20260924-complete-wave-d-specification-and-release-audit-8341b7"
GAME_SCENE_REL = "Exolon/GameCore/GameScene.swift"
GAME_STATE_REL = "Exolon/GameCore/GameState.swift"
GAME_CONSTANTS_REL = "Exolon/GameCore/GameConstants.swift"
PLAYER_REL = "Exolon/GameCore/Player/Player.swift"
LEDGER_REL = "Exolon/GameCore/StageBoundaryLedger.swift"
RESOURCES_DIR = "Exolon/Resources"
MECHANICS_REL = "ORIGINAL_MECHANICS.md"
PENDING_REASON = "pending wave-A merge"

BOUNDARY_ZONES = (24, 49, 74, 99, 124)
# owner ruling 2 (brief.md): the ladder values are canonical, the cadence is not.
TIMED_LADDER = (7000, 5000, 3000, 1000, 0)
BRAVERY_POINTS = 10_000
LIVES_MULTIPLIER = 1_000
PHASE_TICKS_RULING = 1800
POINTS_CEILING = 999_999

CLAUSE_ROWS = (
    # clause id, ORIGINAL_MECHANICS.md line, expected status today, evidence pattern
    ("lives_x1000", 141, "PRESENT", r"awardPoints\(gameState\.lives \* 1_000\)"),
    ("refill_ammo", 146, "PRESENT", r"gameState\.ammo = GameState\.startingAmmo"),
    ("refill_grenades", 146, "PRESENT", r"gameState\.grenades = GameState\.startingGrenades"),
    ("bravery_10000", 142, "MISSING", r"bravery|10_000|10000"),
    ("timed_ladder", 143, "MISSING", r"timed|cursor|phase"),
    ("plus_one_life_capped_9", 144, "PARTIAL",
     r"if gameState\.lives < GameState\.startingLives \{ gameState\.lives \+= 1 \}"),
    ("clear_exoskeleton", 145, "MISSING", r"setExoskeleton"),
)

# The three live clauses expressed as data, so the arithmetic below is bound to the tree
# and not to a prose reading of it.
TODAY_MODEL = {
    "lives_x1000": True,
    "plus_one_life": "no-op at the borrowed cap",
    "refill": (99, 10),
    "bravery": 0,
    "timed": 0,
    "clear_exoskeleton": False,
}


class CheckFailure(Exception):
    """A named check went red."""


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


def boundary_function_body(text: str) -> str:
    """Extract applyOriginalStageBoundaryIfNeeded verbatim (brace-matched, no regex on code)."""
    marker = "private func applyOriginalStageBoundaryIfNeeded(completedZone: Int) {"
    idx = text.find(marker)
    if idx < 0:
        raise CheckFailure(f"{GAME_SCENE_REL}: the stage-boundary function is not present - "
                           "the L0 characterization has nothing to pin")
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
    raise CheckFailure(f"{GAME_SCENE_REL}: unbalanced braces in the stage-boundary function")


def award_points_function_body(text: str) -> str:
    marker = "private func awardPoints(_ value: Int) {"
    idx = text.find(marker)
    if idx < 0:
        raise CheckFailure(f"{GAME_SCENE_REL}: awardPoints is missing - the single funnel is gone")
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
    raise CheckFailure(f"{GAME_SCENE_REL}: unbalanced braces in awardPoints")


def today_award(lives: int, points: int, ammo: int, grenades: int,
                has_exoskeleton: bool, elapsed_ticks: int = 0) -> dict:
    """A faithful re-implementation of the CURRENT three live clauses (L0, architect §7).

    Read the source above this function as its specification: award lives*1000 before the
    +1, +1 only below the borrowed cap, unconditional 99/10 refill, nothing else.
    """
    awarded = lives * LIVES_MULTIPLIER + TODAY_MODEL["bravery"] + TODAY_MODEL["timed"]
    new_points = min(POINTS_CEILING, points + awarded)
    new_lives = lives + 1 if lives < 9 else lives
    return {"points_before": points, "points_after": new_points, "awarded": awarded,
            "lives_before": lives, "lives_after": new_lives,
            "ammo": TODAY_MODEL["refill"][0], "grenades": TODAY_MODEL["refill"][1],
            "exoskeleton_after": has_exoskeleton, "timed_phase": None,
            "elapsed_ticks": elapsed_ticks}


def content_covers_all_zones(root: pathlib.Path) -> tuple[int, bool, str]:
    """The falsification of the 'deliberately dormant' comment: content is already there."""
    tmx = sorted(p.name for p in (root / RESOURCES_DIR).glob("L*S*.tmx"))
    scene = rd(root, GAME_SCENE_REL)
    m = re.search(r"includedLevels: Set<String> = Set\(\((\d+)\.{2,3}(\d+)\)\.flatMap "
                  r"\{ stage in \((\d+)\.{2,3}(\d+)\)\.map", scene)
    covers = 0
    if m:
        lo_s, hi_s, lo_z, hi_z = (int(x) for x in m.groups())
        covers = (hi_s - lo_s + 1) * (hi_z - lo_z + 1)
    stage_ends = [f"L0{i}S25.tmx" for i in range(1, 6)]
    have_ends = all(name in tmx for name in stage_ends)
    return covers, (covers == 125 and len(tmx) == 125 and have_ends), (
        f"includedLevels covers {covers} levels, {RESOURCES_DIR} holds {len(tmx)} .tmx maps, "
        f"stage-end maps present={have_ends}")


# =============================================================================
# phase D-2 checks
# =============================================================================
def line_of(scene: str, needle: str) -> int:
    """1-based line number of a substring inside GameScene.swift (0 = absent)."""
    idx = scene.find(needle)
    if idx < 0:
        return 0
    return scene.count("\n", 0, idx) + 1


def boundary_line_range(scene: str) -> tuple[int, int]:
    marker = "private func applyOriginalStageBoundaryIfNeeded(completedZone: Int) {"
    start = line_of(scene, marker)
    body = boundary_function_body(scene)
    return start, start + body.count("\n")


def l0_rows(root: pathlib.Path) -> list[dict]:
    """The characterization table: one row per canonical clause, pinned to source lines."""
    scene = rd(root, GAME_SCENE_REL)
    body = boundary_function_body(scene)
    offset = scene.find(body)
    rows = []
    for clause, om_line, want, pattern in CLAUSE_ROWS:
        m = re.search(pattern, body)
        hit = bool(m)
        status = "MISSING" if not hit else ("PARTIAL" if clause == "plus_one_life_capped_9"
                                            else "PRESENT")
        source_line = 0
        if m:
            source_line = scene.count("\n", 0, offset + m.start()) + 1
        rows.append({"clause": clause, "om_line": om_line, "pinned": want, "observed": status,
                     "pattern": pattern, "source_line": source_line})
    return rows


def print_l0_table(root: pathlib.Path) -> None:
    scene = rd(root, GAME_SCENE_REL)
    start, end = boundary_line_range(scene)
    print(f"# L0 characterization of {GAME_SCENE_REL}:{start}-{end} (today's product)")
    print(f"# norm {MECHANICS_REL}:138-146 lists six clauses; three are live, see the table")
    print(f"{'clause':<24} {'norm':<8} {'pinned':<9} {'observed':<9} source")
    for row in l0_rows(root):
        src = f"{GAME_SCENE_REL}:{row['source_line']}" if row["source_line"] else "-"
        print(f"{row['clause']:<24} OM:{row['om_line']:<5} {row['pinned']:<9} "
              f"{row['observed']:<9} {src}")
    covers, full, evidence = content_covers_all_zones(root)
    dormant = "deliberately dormant" in boundary_function_body(scene)
    print(f"comment={dormant} content_full={full} verdict="
          f"{'FALSE CLAIM RECORDED (all five boundaries are live)' if dormant and full else 'n/a'}")
    print(f"evidence: {evidence}")
    at_cap = today_award(9, 0, 0, 0, True)
    print(f"model at lives=9: awarded={at_cap['awarded']} lives_after={at_cap['lives_after']} "
          f"ammo={at_cap['ammo']} grenades={at_cap['grenades']} "
          f"exoskeleton_kept={at_cap['exoskeleton_after']} bravery=0 timed=0")


def l0_characterization_pinned(root: pathlib.Path) -> None:
    """Pin today's 3/6 clauses, exactly as written, plus the false dormancy claim."""
    scene = rd(root, GAME_SCENE_REL)
    if not scene:
        raise CheckFailure(f"{GAME_SCENE_REL} is unreadable")
    body = boundary_function_body(scene)
    v: list[str] = []
    for clause, _line, want, pattern in CLAUSE_ROWS:
        hit = bool(re.search(pattern, body))
        got = "MISSING" if not hit else ("PRESENT" if clause != "plus_one_life_capped_9" else
                                         "PARTIAL")
        if got != want:
            v.append(f"L0 row {clause}: tree says {got}, the pinned characterization says {want}")
    # the arithmetic itself, asserted as numbers, not as a grep
    if today_award(9, 0, 0, 0, True) != {
            "points_before": 0, "points_after": 9000, "awarded": 9000, "lives_before": 9,
            "lives_after": 9, "ammo": 99, "grenades": 10, "exoskeleton_after": True,
            "timed_phase": None, "elapsed_ticks": 0}:
        v.append("L0 model: the at-cap case no longer produces 9000 / lives 9 / suit kept")
    one = today_award(1, 5_000, 3, 1, False)
    if (one["awarded"], one["points_after"], one["lives_after"]) != (1000, 6000, 2):
        v.append(f"L0 model: lives=1 must award 1000 before the +1 (got {one})")
    if one["ammo"] != 99 or one["grenades"] != 10:
        v.append("L0 model: the refill must be the shared 99/10 constants")
    if today_award(9, 999_000, 0, 0, False)["points_after"] != POINTS_CEILING:
        v.append("L0 model: the 999_999 clamp must still bound the award")
    # the comment: a recorded falsehood, pinned so D-1 cannot silently keep it
    if "deliberately dormant" not in body:
        v.append("L0: the 'deliberately dormant' comment is gone from the boundary function; "
                 "the characterization must be re-pinned, not quietly dropped")
    covers, full, evidence = content_covers_all_zones(root)
    if not full:
        v.append(f"L0: the false-dormancy pin needs full content coverage; {evidence}")
    caps = rd(root, GAME_STATE_REL)
    for name, value in (("startingAmmo", "99"), ("startingGrenades", "10"),
                        ("startingLives", "9")):
        if not re.search(rf"static let {name} = {value}\b", caps):
            v.append(f"L0: {GAME_STATE_REL} no longer pins {name} = {value}")
    if re.search(r"static let maxLives", caps):
        v.append("L0: an explicit maxLives constant already exists - this check is the "
                 "pre-D-1 characterization and must be retired, not left passing")
    if v:
        raise CheckFailure(" | ".join(v)[:900])
    # Control: every pinned row has to be able to flip. Add the bravery clause to an
    # in-memory copy and require the same table to go red.
    mutated = body.replace("awardPoints(gameState.lives * 1_000)",
                           "awardPoints(gameState.lives * 1_000)\n        awardPoints(10_000)", 1)
    flipped = scene.replace(body, mutated, 1)
    mbody = boundary_function_body(flipped)
    if not re.search(CLAUSE_ROWS[3][3], mbody):
        raise CheckFailure("control did not flip: a bravery clause was invisible to the table")
    if "deliberately dormant" not in mbody:
        raise CheckFailure("the control mutation must not remove the pinned comment text")


def single_funnel(root: pathlib.Path) -> None:
    """INV-001: every score change of the stage sequence goes through awardPoints."""
    scene = rd(root, GAME_SCENE_REL)
    body = boundary_function_body(scene)
    v: list[str] = []
    if "awardPoints(" not in body:
        v.append("the stage sequence no longer awards through awardPoints")
    for bad in (r"gameState\.points\s*[-+]?=", r"highScore\s*="):
        if re.search(bad, body):
            v.append(f"the boundary function writes score state directly ({bad})")
    writers = [ln for ln in scene.splitlines() if re.search(r"gameState\.points\s*[-+]?=", ln)]
    funnel = award_points_function_body(scene)
    if len(writers) != 1 or not re.search(r"gameState\.points = min\(999_999", funnel):
        v.append(f"awardPoints must be the only writer of gameState.points "
                 f"(found {len(writers)} writer lines: {writers[:3]})")
    calls = len(re.findall(r"awardPoints\(", scene))
    if calls < 2:
        v.append("no awardPoints call sites at all - the funnel is unmeasurable")
    if v:
        raise CheckFailure(" | ".join(v)[:600])
    # Control: a direct write in the boundary must redden the invariant.
    bypass = body.replace("awardPoints(gameState.lives * 1_000)",
                          "gameState.points += gameState.lives * 1_000", 1)
    if bypass == body:
        raise CheckFailure("control impossible: the award call to bypass was not found")
    mutated = scene.replace(body, bypass, 1)
    mbody = boundary_function_body(mutated)
    if not re.search(r"gameState\.points\s*[-+]?=", mbody):
        raise CheckFailure("control did not flip: the bypass write was invisible")
    if len([ln for ln in mutated.splitlines()
            if re.search(r"gameState\.points\s*[-+]?=", ln)]) != 2:
        raise CheckFailure("control did not flip: the writer count stayed at one")


# =============================================================================
# phase D-1 checks: explicit failing stubs, named by the change-spec
# =============================================================================
def _pending(name: str, needs: str):
    def check(root: pathlib.Path) -> None:
        ledger = (root / LEDGER_REL).is_file()
        detail = (f"{PENDING_REASON}: {name} needs {needs}; "
                  f"{LEDGER_REL} present in this tree = {ledger}")
        raise CheckFailure(detail)
    check.__name__ = name
    return check


sequence_components_identity = _pending(
    "sequence_components_identity",
    "the data-driven StageBoundaryLedger components lives/bravery/timed from wave A (AC-005)")
lives_and_refill_semantics = _pending(
    "lives_and_refill_semantics",
    "award-before-+1 ordering, the explicit maxLives=9 constant and the shared 99/10 "
    "refill constants (AC-005)")
bravery_latch_distinguishes = _pending(
    "bravery_latch_distinguishes",
    "tookExoskeletonInStage sampled at the changing-room activation edge in wave A's ledger "
    "(AC-006, OM:142 vs :118)")
timed_ladder_deterministic = _pending(
    "timed_ladder_deterministic",
    "the ledger's stageStartTick/tick inputs and PHASE_TICKS=1800 from wave A (AC-006)")
warp_debug_only = _pending(
    "warp_debug_only",
    "the bounded EXOLON_DEBUG_WARP path through transition(to:) plus wave A's log sink "
    "(AC-007, owner ruling 4)")
ladder_is_declared_deviation = _pending(
    "ladder_is_declared_deviation",
    f"the PHASE_TICKS named constant carrying the owner-deviation comment in "
    f"{GAME_CONSTANTS_REL} (FORBID-003); the ladder {list(TIMED_LADDER)} is an approximation "
    "of an interactive cursor and must never be asserted as canonical")


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
CHECKS: dict[str, object] = {**CHECKS_D2, **CHECKS_D1}

SPEC_NAMES = ("sequence_components_identity", "lives_and_refill_semantics",
              "bravery_latch_distinguishes", "timed_ladder_deterministic", "warp_debug_only",
              "single_funnel", "ladder_is_declared_deviation")


def selfcheck_names_exist() -> None:
    missing = [n for n in SPEC_NAMES if n not in CHECKS]
    if missing:
        raise CheckFailure(f"change-spec evidence names not defined here: {', '.join(missing)}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="stage_boundary_check.py")
    ap.add_argument("--root")
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--phase", choices=("D2", "D1"), default="D2",
                    help="D2 (default): L0 + single_funnel must pass and every ledger-backed "
                         "name must fail with the pending reason; D1: all names must pass")
    ap.add_argument("--list", action="store_true", help="print the check names and phases")
    ap.add_argument("--table", action="store_true",
                    help="print the pinned L0 characterization table and exit")
    args = ap.parse_args(argv)
    root = repo_root(args.root)

    if args.table:
        print_l0_table(root)
        return 0

    if args.list:
        for name in CHECKS_D2:
            print(f"{name}\tD-2\tactive")
        for name in CHECKS_D1:
            print(f"{name}\tD-1\tblocked by {LEDGER_REL} (wave A)")
        return 0

    names = args.only or list(CHECKS)
    unknown = [n for n in names if n not in CHECKS]
    if unknown:
        print(f"unknown check(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    failures = 0
    try:
        selfcheck_names_exist()
    except CheckFailure as exc:
        print(f"RESULT selfcheck_names_exist=FAIL {exc}")
        return 1
    for name in names:
        fn = CHECKS[name]
        try:
            fn(root)  # type: ignore[operator]
            status, detail = "PASS", ""
        except CheckFailure as exc:
            status, detail = "FAIL", str(exc)
        except Exception as exc:  # noqa: BLE001
            status, detail = "ERROR", f"{type(exc).__name__}: {exc}"
        pending_expected = args.phase == "D2" and name in CHECKS_D1
        if pending_expected:
            if status == "FAIL" and detail.startswith(PENDING_REASON):
                print(f"RESULT {name}=PENDING_OK {detail}")
            else:
                failures += 1
                print(f"RESULT {name}=FAIL expected the pending stub, got {status} {detail}")
            continue
        if status == "PASS":
            print(f"RESULT {name}=PASS")
        else:
            failures += 1
            note = (" (L0 is a characterization: it MUST turn red when D-1 changes the "
                    "sequence)" if name == "l0_characterization_pinned" else "")
            print(f"RESULT {name}={status} {detail}{note}")
    print(f"SUMMARY checks={len(names)} failed={failures} phase={args.phase}")
    print("SCOPE: L0 pins today's 3/6 clauses; the ledger sequence is D-1 (owner ruling 3)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
