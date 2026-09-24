#!/usr/bin/env bash
# Исполняемый Linux-контур wave B (P1-1/P1-2/P1-3/P1-5): сборка НАСТОЯЩИХ
# SpriteKit-free продуктовых исходников (Exolon/GameCore/GameConstants.swift и
# Exolon/GameCore/Levels/TMXMapLoader.swift с ровно одной добавленной строкой
# импорта) и прогон по всем 125 картам корпуса. Вывод — артефакт
# ../wave_b_swift.txt, который измеритель ../wave_b_check.py сверяет со своей
# python-формулой пиксель-в-пиксель; расхождение = зеркало измерителя врёт.
#
# Техника copied из закоммиченного piston-anchor-harness пакета
# 20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698 (стаб
# CoreGraphics из 20260919-аудита, байт-контроль дельты, негативный контроль
# сборки без стаба).
#
# Запуск:  ./run.sh > ../wave_b_swift.txt
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=""
probe="$HERE"
while [ "$probe" != "/" ]; do
  probe="$(dirname "$probe")"
  if [ -d "$probe/Exolon/Resources" ] && [ -e "$probe/.git" ]; then ROOT="$probe"; break; fi
done
if [ -z "$ROOT" ]; then
  printf 'FATAL: корень репозитория не найден от %s\n' "$HERE" >&2
  exit 66
fi
printf 'root=%s\n' "$ROOT" >&2

BUILD="${TMPDIR:-/tmp}/exolon-wave-b.$$"
mkdir -p "$BUILD"
trap 'rm -rf "$BUILD"' EXIT

if [ "$(uname -s)" = "Darwin" ]; then
  printf 'FATAL: на macOS этот контур не нужен — собирай таргет Exolon\n' >&2
  exit 75
fi
command -v swiftc >/dev/null 2>&1 || { printf 'FATAL: нет swiftc\n' >&2; exit 69; }

LOADER="$ROOT/Exolon/GameCore/Levels/TMXMapLoader.swift"
CONSTANTS="$ROOT/Exolon/GameCore/GameConstants.swift"
[ -f "$LOADER" ] || { printf 'FATAL: %s не найден\n' "$LOADER" >&2; exit 66; }
[ -f "$CONSTANTS" ] || { printf 'FATAL: %s не найден\n' "$CONSTANTS" >&2; exit 66; }

SHIM="$ROOT/engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/harness/coregraphics_shim.swift"
[ -f "$SHIM" ] || { printf 'FATAL: нет стаба CoreGraphics (%s)\n' "$SHIM" >&2; exit 66; }

swiftc -emit-module -emit-library -module-name CoreGraphics \
  -emit-module-path "$BUILD/CoreGraphics.swiftmodule" \
  -o "$BUILD/libCoreGraphics.so" "$SHIM"

awk 'NR==1 { print; print "import FoundationXML"; next } { print }' "$LOADER" > "$BUILD/TMXMapLoader.swift"
if diff -q <(sed '2d' "$BUILD/TMXMapLoader.swift") "$LOADER" >/dev/null; then
  printf 'OK: дельта сборочной копии загрузчика = ровно 1 строка импорта\n' >&2
else
  printf 'FATAL: сборочная копия отличается от репозиторной не только импортом\n' >&2
  exit 65
fi
cmp -s "$CONSTANTS" "$BUILD/GameConstants.swift" 2>/dev/null || cp "$CONSTANTS" "$BUILD/GameConstants.swift"

swiftc -I "$BUILD" -L "$BUILD" -lCoreGraphics \
  "$BUILD/GameConstants.swift" "$BUILD/TMXMapLoader.swift" "$HERE/main.swift" -o "$BUILD/probe"

TMX_RESOURCES="$ROOT/Exolon/Resources" LD_LIBRARY_PATH="$BUILD" "$BUILD/probe"

if swiftc "$BUILD/TMXMapLoader.swift" "$BUILD/GameConstants.swift" "$HERE/main.swift" \
     -o "$BUILD/no-shim" 2>"$BUILD/no-shim.err"; then
  printf 'FATAL: собралось без стаба — контроль не перевернулся, вывод выше невалиден\n' >&2
  exit 1
fi
printf 'OK: без стаба не собирается (%s)\n' "$(head -1 "$BUILD/no-shim.err" | cut -c1-90)" >&2
