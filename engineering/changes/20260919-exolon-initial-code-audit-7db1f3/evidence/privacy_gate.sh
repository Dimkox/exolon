#!/usr/bin/env bash
# Исключение: сам этот файл содержит шаблоны поиска как текст — он исключён из
# собственных проверок (строка SELF_EXCLUDE ниже), всё остальное сканируется полностью.
# Шлюз приватности перед коммитом в публичный репозиторий.
# Проверяет и отслеживаемые, и добавляемые (untracked) файлы: git grep видит только
# индексируемое содержимое, а утечки этого прогона жили именно в новых отчётах.
# Обязан иметь положительный контроль: без него «пусто» ничего не значит.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT" || exit 66

# «/home/» само по себе не утечка: отчёт обязан цитировать шаблон поиска. Поэтому после
# префикса требуется символ реального имени (буква/цифра/_/-): `/home/...`, `/home/<user>`,
# `/home/[A-Za-z…` не совпадут, `/home/ivanov/projects` — совпадёт.
PATTERNS='/home/[a-zA-Z0-9_-]|/Users/[a-zA-Z0-9_-]|/root/[a-zA-Z0-9_-]|[A-Za-z0-9._%+-]+@(gmail|mail\.ru|yandex|outlook|icloud)|BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-'
HOST="$(hostname)"
[ -n "$HOST" ] && PATTERNS="$PATTERNS|$HOST"
USER_NAME="${USER:-}"
[ -n "$USER_NAME" ] && PATTERNS="$PATTERNS|/home/$USER_NAME|$USER_NAME@|<login:$USER_NAME>"

hits=0
echo "== 1. отслеживаемое содержимое (git grep) =="
SELF_EXCLUDE=':(exclude)engineering/changes/*/evidence/privacy_gate.sh'
if out=$(git grep -nIE "$PATTERNS" -- . "$SELF_EXCLUDE" 2>/dev/null); then
  printf '%s\n' "$out" | head -40; hits=$((hits + $(printf '%s\n' "$out" | wc -l)))
else
  echo '  чисто'
fi

echo "== 2. добавляемое сейчас (untracked + staged, включая новые отчёты лагов) =="
tmp=$(mktemp)
git ls-files --others --exclude-standard -z | grep -zv 'privacy_gate.sh' | xargs -0 -r grep -InHE "$PATTERNS" 2>/dev/null > "$tmp" || true
git diff --cached -U0 --name-only -z | xargs -0 -r grep -InHE "$PATTERNS" 2>/dev/null >> "$tmp" || true
if [ -s "$tmp" ]; then
  head -40 "$tmp"; hits=$((hits + $(wc -l < "$tmp")))
else
  echo '  чисто'
fi
rm -f "$tmp"

echo "== 3. положительный контроль (шлюз обязан находить подсаженное) =="
probe_dir=".git/qwen-privacy-probe.$$"
mkdir -p "$probe_dir"
printf 'path /home/%s/projects/x line\n' "${USER_NAME:-someone}" > "$probe_dir/probe.txt"
if grep -InHE "$PATTERNS" "$probe_dir/probe.txt" >/dev/null 2>&1; then
  echo '  контроль сработал: подсаженная строка найдена'
else
  echo '  BAD: контроль НЕ сработал — шлюз сломан, результат выше недействителен' >&2
  hits=$((hits + 1000))
fi
rm -rf "$probe_dir"

if [ "$hits" -gt 0 ]; then
  echo "RESULT: FAIL ($hits совпадений) — scrub перед коммитом обязателен"
  exit 1
fi
echo "RESULT: PASS (0 совпадений, контроль перевернулся)"
