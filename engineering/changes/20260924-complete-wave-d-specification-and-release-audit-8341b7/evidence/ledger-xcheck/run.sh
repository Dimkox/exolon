#!/usr/bin/env bash
# Wave D cross-check: compile and run the REAL StageBoundaryLedger (the Foundation-only product
# files, the same list and the same CoreGraphics shim wave A's contour uses) with a driver that
# prints the waveD award table. stage_boundary_check.py compares its modelled table against
# evidence/ledger-xcheck-executed.txt, so "modelled" never silently means "assumed".
#
# Artifacts go outside the clone (route rule + wave A's own lesson); refuses on Darwin because the
# product builds there with Xcode, not here.
set -uo pipefail
# engineering/changes/<id>/evidence/ledger-xcheck -> repository root is five levels up
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT="$ROOT/engineering/changes/20260924-complete-wave-d-specification-and-release-audit-8341b7/evidence"
HERE="$OUT/ledger-xcheck"
AP="$ROOT/engineering/changes/20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c/evidence"
[ "$(uname -s)" = "Darwin" ] && { printf 'FATAL: этот контур linux-only (на macOS собирает Xcode)\n' >&2; exit 75; }
for need in "$AP/harness/coregraphics_shim.swift" "$HERE/main.swift" "$ROOT/Exolon/GameCore/Diagnostics/StageBoundaryLedger.swift"; do
  [ -f "$need" ] || { printf 'FATAL: нет %s\n' "$need" >&2; exit 66; }
done
command -v swiftc >/dev/null 2>&1 || { printf 'FATAL: swiftc не установлен\n' >&2; exit 77; }
ART=$(mktemp -d /tmp/exolon-ledger-xcheck-XXXXXX)
trap 'rm -rf "$ART"' EXIT
swiftc -emit-module -emit-library -module-name CoreGraphics \
  -emit-module-path "$ART/CoreGraphics.swiftmodule" -o "$ART/libCoreGraphics.so" \
  "$AP/harness/coregraphics_shim.swift" || exit 1
swiftc -O -I "$ART" -L "$ART" -lCoreGraphics \
  "$ROOT/Exolon/GameCore/GameConstants.swift" \
  "$ROOT/Exolon/GameCore/InputState.swift" \
  "$ROOT/Exolon/GameCore/GameState.swift" \
  "$ROOT/Exolon/GameCore/Player/Player.swift" \
  "$ROOT/Exolon/GameCore/Diagnostics/GameplayEventSink.swift" \
  "$ROOT/Exolon/GameCore/Diagnostics/GameplayEventLog.swift" \
  "$ROOT/Exolon/GameCore/Diagnostics/FixedTickDriver.swift" \
  "$ROOT/Exolon/GameCore/Diagnostics/StageBoundaryLedger.swift" \
  "$ROOT/Exolon/GameCore/Diagnostics/LauncherBonusState.swift" \
  "$HERE/main.swift" -o "$ART/xcheck" || exit 1
LD_LIBRARY_PATH="$ART" "$ART/xcheck"
