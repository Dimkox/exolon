#!/usr/bin/env bash
# Исполняемый Linux-контур якоря поршней (находка P1-1).
#
# Даёт число, какой `groundY` выдаёт НАСТОЯЩИЙ
# Exolon/GameCore/Levels/TMXMapLoader.swift :: worldBottomLeft(for:) для каждого
# из 46 объектов `piston` корпуса. Это нужно потому, что закоммиченный
# измеритель корректуры
#   engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/v3_measurements.py
# моделирует якорь как `PH - y - height`, а продукт для объектов без
# `coordinateMode=tiledRect` возвращает `PH - y`; для 45 rect-маркеров поршня
# (height=64) это расхождение ровно 64 px.
#
# Техника — копия закоммиченного харнеса того же аудита: продуктовый исходник
# не правится, в сборочный каталог кладётся копия с ровно одной добавленной
# строкой `import FoundationXML`, дельта проверяется байт-в-байт; без стаба
# сборка обязана упасть (негативный контроль).
#
# Запуск:  ./run.sh > ../piston-anchor-swift.txt
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT=""
probe="$HERE"
while [ "$probe" != "/" ]; do
  probe="$(dirname "$probe")"
  if [ -d "$probe/Exolon/Resources" ] && [ -d "$probe/.git" ]; then ROOT="$probe"; break; fi
done
if [ -z "$ROOT" ]; then
  printf 'FATAL: корень репозитория не найден от %s\n' "$HERE" >&2
  exit 66
fi
printf 'root=%s\n' "$ROOT" >&2

BUILD="${TMPDIR:-/tmp}/exolon-piston-anchor.$$"
mkdir -p "$BUILD"
trap 'rm -rf "$BUILD"' EXIT

if [ "$(uname -s)" = "Darwin" ]; then
  printf 'FATAL: на macOS этот контур не нужен — собирай таргет Exolon\n' >&2
  exit 75
fi
command -v swiftc >/dev/null 2>&1 || { printf 'FATAL: нет swiftc\n' >&2; exit 69; }

SRC="$ROOT/Exolon/GameCore/Levels/TMXMapLoader.swift"
[ -f "$SRC" ] || { printf 'FATAL: %s не найден\n' "$SRC" >&2; exit 66; }

SHIM="$ROOT/engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/harness/coregraphics_shim.swift"
[ -f "$SHIM" ] || { printf 'FATAL: нет стаба CoreGraphics (%s)\n' "$SHIM" >&2; exit 66; }

swiftc -emit-module -emit-library -module-name CoreGraphics \
  -emit-module-path "$BUILD/CoreGraphics.swiftmodule" \
  -o "$BUILD/libCoreGraphics.so" "$SHIM"

awk 'NR==1 { print; print "import FoundationXML"; next } { print }' "$SRC" > "$BUILD/TMXMapLoader.swift"
if diff -q <(sed '2d' "$BUILD/TMXMapLoader.swift") "$SRC" >/dev/null; then
  printf 'OK: дельта сборочной копии = ровно 1 строка импорта\n' >&2
else
  printf 'FATAL: сборочная копия отличается от репозиторной не только импортом\n' >&2
  exit 65
fi

swiftc -I "$BUILD" -L "$BUILD" -lCoreGraphics \
  "$BUILD/TMXMapLoader.swift" "$HERE/main.swift" -o "$BUILD/probe"

TMX_RESOURCES="$ROOT/Exolon/Resources" LD_LIBRARY_PATH="$BUILD" "$BUILD/probe"

if swiftc "$BUILD/TMXMapLoader.swift" "$HERE/main.swift" -o "$BUILD/no-shim" 2>"$BUILD/no-shim.err"; then
  printf 'FATAL: собралось без стаба — контроль не перевернулся, вывод выше невалиден\n' >&2
  exit 1
fi
printf 'OK: без стаба не собирается (%s)\n' "$(head -1 "$BUILD/no-shim.err" | cut -c1-90)" >&2
