#!/usr/bin/env bash
# One-command re-certification of wave E1 (route 8f7b02) on the CURRENT head.
#
# Why this exists (review-test M3 / review-code R1): the first wave E1 freeze recorded
# `wave_scan`/`wave_e1_check`/`grok_verify` transcripts while the change was still uncommitted, so
# the shipped evidence certified `0b0dea9` while the head it sat in was `32e61e8`. Every artifact
# written here carries `head=<sha>` and `dirty=<n>` in its header, and this script FAILS at the end
# if any of them does not name the head the freeze started on.
#
# Order matters: grok_verify's own source-stability check requires that nothing writes to the tree
# while it runs, so it goes last; the checker then names `EXOLON_E1_FREEZE=1` so it does not flag
# the verify transcript that is written after it.
#
# Usage: bash engineering/changes/20260925-wave-e1-verification-tooling-from-the-a-d-chain-8f7b02/evidence/freeze.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# evidence -> package -> changes -> engineering -> repository root
R="$(cd "$HERE/../../../.." && pwd)"
cd "$R" || exit 66
git rev-parse --git-dir >/dev/null 2>&1 || { printf 'FREEZE FAIL: %s is not a git repository\n' "$R" >&2; exit 66; }
HEAD_SHA="$(git rev-parse HEAD)"
DIRTY="$(git status --porcelain | wc -l | tr -d ' ')"
STAMP="$(date -u +%FT%TZ)"
scrub() { sed -e "s#$R#<repo>#g" -e 's/[ \t]\+$//'; }
fail() { printf 'FREEZE FAIL: %s\n' "$1" >&2; exit 1; }

[ -n "$HEAD_SHA" ] || fail 'no HEAD sha resolved'
printf '== 1/5 wave_scan end-to-end (head %s, dirty %s) ==\n' "${HEAD_SHA:0:7}" "$DIRTY"
s=$SECONDS; python3 engineering/tools/wave_scan.py > /tmp/e1-freeze-scan.txt 2>&1; rc_scan=$?; w_scan=$((SECONDS-s))
{ printf '# wave_scan.py end-to-end on the wave E1 tree\n'
  printf '# head=%s  date=%s  dirty=%s  rc=%s  wall=%ss\n' "$HEAD_SHA" "$STAMP" "$DIRTY" "$rc_scan" "$w_scan"
  printf '# command: python3 engineering/tools/wave_scan.py\n'
  scrub < /tmp/e1-freeze-scan.txt; } > "$HERE/wave-scan-end-to-end.txt"
[ "$rc_scan" -eq 0 ] || fail "wave_scan is not green (rc=$rc_scan); see $HERE/wave-scan-end-to-end.txt"

printf '== 2/5 ruff on the new tools ==\n'
{ printf '# ruff check with the repository'"'"'s own ruff.toml (select E4,E7,E9,F; line-length 120; target py310)\n'
  printf '# head=%s  date=%s  dirty=%s\n' "$HEAD_SHA" "$STAMP" "$DIRTY"
  printf '# NOTE: ruff.toml excludes engineering/, so the files are passed explicitly.\n\n'
  printf '## 1. wave E1'"'"'s new tools (must be clean)\n'
  printf '$ python3 -m ruff check --output-format concise engineering/tools/wave_scan.py \\\n'
  printf '      engineering/changes/20260925-…-8f7b02/evidence/wave_e1_check.py\n'
  python3 -m ruff check --output-format concise engineering/tools/wave_scan.py \
      "$HERE/wave_e1_check.py"; echo "rc=$?"
  printf '\n## 2. merged tools wave E1 touched (findings below are PRE-EXISTING lines of those files,\n'
  printf '##    not wave E1 edits; E1 deliberately did not "fix" them - they belong to their routes)\n'
  printf '$ python3 -m ruff check --output-format concise <the five merged files>\n'
  python3 -m ruff check --output-format concise \
      "$R/engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/v3_measurements.py" \
      "$R/engineering/changes/20260924-close-wave-c-content-and-factory-audit-findings-f2d90a/evidence/wave_c_check.py" \
      "$R/engineering/changes/20260924-fix-wave-b-map-data-and-physics-audit-findings-i-35bac2/evidence/wave_b_check.py" \
      "$R/engineering/changes/20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c/evidence/gameplay_log_check.py" \
      "$R/engineering/changes/20260924-complete-wave-d-specification-and-release-audit-8341b7/evidence/stage_boundary_check.py"
  echo "rc=$?"; } > "$HERE/ruff-new-tools.txt"
grep -q 'All checks passed!' "$HERE/ruff-new-tools.txt" || fail 'ruff is not clean on the new tools'

printf '== 3/5 wave_e1_check (all 11 probes, real ref topology) ==\n'
s=$SECONDS
# one run, both transcripts: --json keeps stdout pure JSON and writes the progress lines and the
# RESULT line to stderr (a second full pass would double the freeze for nothing)
EXOLON_E1_FREEZE=1 python3 -u "$HERE/wave_e1_check.py" --json > /tmp/e1-freeze-check.json 2>/tmp/e1-freeze-check.progress
rc_check=$?; w_check=$((SECONDS-s)); rc_json=$rc_check
{ printf '# wave_e1_check.py full run (11 probes + their flipping controls)\n'
  printf '# head=%s  date=%s  dirty=%s  rc=%s  wall=%ss\n' "$HEAD_SHA" "$STAMP" "$DIRTY" "$rc_check" "$w_check"
  printf '# command: EXOLON_E1_FREEZE=1 python3 evidence/wave_e1_check.py --json\n'
  printf '# (progress lines and the RESULT line are the run\'"'"'s stderr; the JSON is the sibling\n'
  printf '#  artifact wave-e1-check.json, so the two cannot disagree - same process)\n'
  scrub < /tmp/e1-freeze-check.progress; } > "$HERE/wave-e1-check-green.txt"
python3 - "$HEAD_SHA" "$STAMP" "$DIRTY" "$rc_json" "$R" /tmp/e1-freeze-check.json "$HERE/wave-e1-check.json" <<'PYEOF'
import json, re, sys
head, stamp, dirty, rc, root, src, dst = sys.argv[1:8]
raw = open(src, encoding='utf-8').read()
if root in raw:                       # no absolute host path may reach a tracked artifact
    raw = raw.replace(root, '<repo>')
doc = json.loads(raw)
doc['certified_head'] = head
doc['recorded_at'] = stamp
doc['recorded_rc'] = int(rc)
doc['recorded_dirty_paths'] = int(dirty)
text = json.dumps(doc, indent=2, sort_keys=True) + '\n'
if '/home/' in text or '/Users/' in text:
    sys.stderr.write('FREEZE FAIL: unscrubbed path in wave-e1-check.json\n')
    raise SystemExit(9)
open(dst, 'w', encoding='utf-8').write(text)
PYEOF
[ "$rc_check" -eq 0 ] && [ "$rc_json" -eq 0 ] \
  || fail "wave_e1_check is not green (rc=$rc_check/$rc_json); see $HERE/wave-e1-check-green.txt"

printf '== 4/5 grok_verify --mode pr --no-record (nothing else writes during it) ==\n'
s=$SECONDS; python3 scripts/grok_verify.py --mode pr --no-record > /tmp/e1-freeze-verify.txt 2>&1; rc_verify=$?; w_verify=$((SECONDS-s))
{ printf '# python3 scripts/grok_verify.py --mode pr --no-record\n'
  printf '# head=%s  date=%s  dirty=%s  rc=%s  wall=%ss\n' "$HEAD_SHA" "$STAMP" "$DIRTY" "$rc_verify" "$w_verify"
  printf '# run last, after every other artifact was written (source-stability is one of its checks)\n'
  scrub < /tmp/e1-freeze-verify.txt; } > "$HERE/grok-verify-pr.txt"
[ "$rc_verify" -eq 0 ] || fail "grok_verify did not pass (rc=$rc_verify)"

printf '== 5/5 head binding + privacy gate on the recorded artifacts ==\n'
for artifact in wave-scan-end-to-end.txt wave-e1-check-green.txt wave-e1-check.json \
                ruff-new-tools.txt grok-verify-pr.txt; do
  grep -q "$HEAD_SHA" "$HERE/$artifact" || fail "$artifact does not name the frozen head ${HEAD_SHA:0:7}"
done
if grep -rn "$R" "$HERE"/*.txt "$HERE"/*.json 2>/dev/null | grep -v freeze.sh >/dev/null; then
  fail 'an absolute repository path leaked into a recorded artifact'
fi
git diff --check >/dev/null 2>&1 || fail 'git diff --check is not clean'
printf 'FREEZE OK head=%s dirty=%s scan=%ss check=%ss verify=%ss\n' \
       "${HEAD_SHA:0:7}" "$DIRTY" "$w_scan" "$w_check" "$w_verify"
