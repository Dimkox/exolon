#!/usr/bin/env bash
# Исполняемый Linux-контур продуктового загрузчика уровней (TMXMapLoader.swift).
# Доказывает цифру «125/125 карт загружаются настоящим Swift-кодом» и поведение
# отказоустойчивости на malformed-фикстурах — вместо «только -frontend -parse».
#
# Продуктовые исходники НЕ изменяются: из репозитарного файла делается сборочная
# копия, в которую добавляется ровно одна строка импорта (дельта проверяется).
#
# Запуск: ./run.sh            (артефакты сборки — во временном каталоге)
#         ./run.sh | tee last-run.txt
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../../../.." && pwd)"
BUILD="${TMPDIR:-/tmp}/exolon-loader-harness.$$"
mkdir -p "$BUILD"
trap 'rm -rf "$BUILD"' EXIT

if [ "$(uname -s)" = "Darwin" ]; then
  printf 'FATAL: на macOS этот контур не нужен — собирай таргет Exolon (xcodebuild -project Exolon.xcodeproj -target Exolon -configuration Debug build)\n' >&2
  exit 75
fi
for tool in swiftc python3; do
  command -v "$tool" >/dev/null 2>&1 || { printf 'FATAL: нет %s (нужен Linux-toolchain Swift 6.x)\n' "$tool" >&2; exit 69; }
done

SRC="$ROOT/Exolon/GameCore/Levels/TMXMapLoader.swift"
[ -f "$SRC" ] || { printf 'FATAL: %s не найден — запускай из клона репозитория\n' "$SRC" >&2; exit 66; }

printf '== 1. стаб модуля CoreGraphics (только переименование типов, логики нет) ==\n'
swiftc -emit-module -emit-library -module-name CoreGraphics \
  -emit-module-path "$BUILD/CoreGraphics.swiftmodule" \
  -o "$BUILD/libCoreGraphics.so" "$HERE/coregraphics_shim.swift"
printf 'shim built: %s\n' "$BUILD/libCoreGraphics.so"

printf '\n== 2. сборочная копия загрузчика: дельта против репозитория ==\n'
awk 'NR==1 { print; print "import FoundationXML"; next } { print }' "$SRC" > "$BUILD/TMXMapLoader.swift"
if diff -q <(sed '2d' "$BUILD/TMXMapLoader.swift") "$SRC" >/dev/null; then
  printf 'OK: удаление строки 2 возвращает файл к репозиторному байт-в-байт (дельта = ровно 1 импорт)\n'
else
  printf 'FATAL: сборочная копия отличается от репозиторной не только импортом\n' >&2
  diff <(sed '2d' "$BUILD/TMXMapLoader.swift") "$SRC" | head -10 >&2
  exit 65
fi

printf '\n== 3. malformed-фикстуры ==\n'
python3 "$HERE/gen_fixtures.py"

printf '\n== 4. сборка контура ==\n'
swiftc -I "$BUILD" -L "$BUILD" -lCoreGraphics \
  "$BUILD/TMXMapLoader.swift" "$HERE/main.swift" -o "$BUILD/loader"
printf 'built: %s/loader\n' "$BUILD"

printf '\n== 5. прогон: фикстуры + весь корпус + геометрия зоны 009 ==\n'
TMX_FIXTURES="$HERE/fixtures" TMX_RESOURCES="$ROOT/Exolon/Resources" \
  LD_LIBRARY_PATH="$BUILD" "$BUILD/loader"

printf '\n== 6. негативный контроль: без стаба сборка обязана упасть ==\n'
if swiftc "$BUILD/TMXMapLoader.swift" "$HERE/main.swift" -o "$BUILD/no-shim" 2>"$BUILD/no-shim.err"; then
  printf 'FATAL: собралось без стаба — контроль не перевернулся, вывод выше невалиден\n' >&2
  exit 1
fi
printf 'OK: без стаба не собирается (%s)\n' "$(head -1 "$BUILD/no-shim.err" | cut -c1-90)"
