#!/usr/bin/env bash
# One-command re-certification of wave E1 (route 8f7b02) on the CURRENT state of this tree.
#
# Why this exists (review-test M3 / review-code R1, and review-test-recheck §3a): the first wave E1
# freeze recorded transcripts while the change was still uncommitted, so the shipped evidence
# certified `0b0dea9` while the head it sat in was `32e61e8`. Binding by commit identity alone then
# either fails its own gate after the commit or demands an endless re-freeze - an artifact cannot
# certify the tree that contains it. Binding is therefore BY CONTENT: this pass computes one digest
# over the change surface (route-base..HEAD ∪ working ∪ untracked, minus the derived files this pass
# and the reviewers write) and stamps `certified_head`, `cert_digest`, `certified_files` and the
# stack `tree_fingerprint` into every artifact. A freeze on a dirty parent tree and the clean commit
# carrying exactly those bytes share the same digest - which is what makes "certify the parent,
# commit once" non-circular - while any content change moves the digest. Outside the freeze window a
# bare `wave_e1_check.py` treats a digest mismatch as a RED gate, so stale evidence can never be
# read as green; inside this pass the notes are informational, because the artifacts are written after
# the probes run.
#
# Order matters: grok_verify's own source-stability check requires that nothing writes to the tree
# while it runs, so it goes last; `EXOLON_E1_FREEZE=1` marks the recording window.
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
# one binding for the whole pass, taken from the checker's own implementation (no second copy)
bind() {
  python3 - "$HERE" <<'PYBIND'
import importlib.util, sys
spec = importlib.util.spec_from_file_location('e1', sys.argv[1] + '/wave_e1_check.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
digest, files = mod.cert_state()
print(digest, files, mod.tree_fingerprint_now() or 'unavailable')
PYBIND
}
stamp() {
  printf '# certified_head=%s  cert_digest=%s  certified_files=%s  tree_fingerprint=%s\n' \
         "$HEAD_SHA" "$CERT_DIGEST" "$CERT_FILES" "$TREE_FP"
}

[ -n "$HEAD_SHA" ] || fail 'no HEAD sha resolved'
read -r CERT_DIGEST CERT_FILES TREE_FP <<<"$(bind)"
[ -n "$CERT_DIGEST" ] || fail 'no cert_digest computed'
printf 'binding cert_digest=%s certified_files=%s tree_fingerprint=%s\n' \
       "$CERT_DIGEST" "$CERT_FILES" "${TREE_FP:0:16}"

printf '== 1/5 wave_scan end-to-end (head %s, dirty %s) ==\n' "${HEAD_SHA:0:7}" "$DIRTY"
s=$SECONDS; python3 engineering/tools/wave_scan.py > /tmp/e1-freeze-scan.txt 2>&1; rc_scan=$?; w_scan=$((SECONDS-s))
{ printf '# wave_scan.py end-to-end on the wave E1 tree\n'
  printf '# head=%s  date=%s  dirty=%s  rc=%s  wall=%ss\n' "$HEAD_SHA" "$STAMP" "$DIRTY" "$rc_scan" "$w_scan"
  stamp
  printf '# command: python3 engineering/tools/wave_scan.py\n'
  scrub < /tmp/e1-freeze-scan.txt; } > "$HERE/wave-scan-end-to-end.txt"
[ "$rc_scan" -eq 0 ] || fail "wave_scan is not green (rc=$rc_scan); see $HERE/wave-scan-end-to-end.txt"

printf '== 2/5 ruff on the new tools ==\n'
{ printf '# ruff check with the repository'"'"'s own ruff.toml (select E4,E7,E9,F; line-length 120; target py310)\n'
  printf '# head=%s  date=%s  dirty=%s\n' "$HEAD_SHA" "$STAMP" "$DIRTY"
  stamp
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
# one run, both transcripts: --json keeps stdout pure JSON and writes progress + RESULT to stderr
EXOLON_E1_FREEZE=1 python3 -u "$HERE/wave_e1_check.py" --json > /tmp/e1-freeze-check.json \
    2>/tmp/e1-freeze-check.progress
rc_check=$?; w_check=$((SECONDS-s))
{ printf '# wave_e1_check.py full run (11 probes + their flipping controls)\n'
  printf '# head=%s  date=%s  dirty=%s  rc=%s  wall=%ss\n' "$HEAD_SHA" "$STAMP" "$DIRTY" "$rc_check" "$w_check"
  stamp
  printf '# command: EXOLON_E1_FREEZE=1 python3 evidence/wave_e1_check.py --json\n'
  printf '# (the RESULT line and progress are this run\'"'"'s stderr; the same process wrote the\n'
  printf '#  sibling artifact wave-e1-check.json, so the two cannot disagree)\n'
  scrub < /tmp/e1-freeze-check.progress; } > "$HERE/wave-e1-check-green.txt"
python3 - "$HEAD_SHA" "$STAMP" "$DIRTY" "$rc_check" "$R" "$CERT_DIGEST" "$CERT_FILES" "$TREE_FP" \
        /tmp/e1-freeze-check.json "$HERE/wave-e1-check.json" <<'PYBIND'
import json, sys
head, stamp_v, dirty, rc, root, digest, files, fp, src, dst = sys.argv[1:11]
raw = open(src, encoding='utf-8').read()
if root in raw:                       # no absolute host path may reach a tracked artifact
    raw = raw.replace(root, '<repo>')
doc = json.loads(raw)
doc['certified_head'] = head
doc['cert_digest'] = digest
doc['certified_files'] = int(files)
doc['tree_fingerprint'] = fp
doc['recorded_at'] = stamp_v
doc['recorded_rc'] = int(rc)
doc['recorded_dirty_paths'] = int(dirty)
text = json.dumps(doc, indent=2, sort_keys=True) + '\n'
if '/home/' in text or '/Users/' in text:
    sys.stderr.write('FREEZE FAIL: unscrubbed path in wave-e1-check.json\n')
    raise SystemExit(9)
open(dst, 'w', encoding='utf-8').write(text)
PYBIND
[ "$rc_check" -eq 0 ] || fail "wave_e1_check is not green (rc=$rc_check); see $HERE/wave-e1-check-green.txt"

printf '== 4/5 grok_verify --mode pr --no-record (nothing else writes during it) ==\n'
s=$SECONDS; python3 scripts/grok_verify.py --mode pr --no-record > /tmp/e1-freeze-verify.txt 2>&1; rc_verify=$?; w_verify=$((SECONDS-s))
{ printf '# python3 scripts/grok_verify.py --mode pr --no-record\n'
  printf '# head=%s  date=%s  dirty=%s  rc=%s  wall=%ss\n' "$HEAD_SHA" "$STAMP" "$DIRTY" "$rc_verify" "$w_verify"
  stamp
  printf '# run last, after every other artifact was written (source-stability is one of its checks)\n'
  scrub < /tmp/e1-freeze-verify.txt; } > "$HERE/grok-verify-pr.txt"
[ "$rc_verify" -eq 0 ] || fail "grok_verify did not pass (rc=$rc_verify)"

printf '== 5/5 binding, self-acceptance and privacy checks on the recorded artifacts ==\n'
for artifact in wave-scan-end-to-end.txt wave-e1-check-green.txt wave-e1-check.json \
                ruff-new-tools.txt grok-verify-pr.txt; do
  grep -q "$HEAD_SHA" "$HERE/$artifact" \
    || fail "$artifact does not name the frozen head ${HEAD_SHA:0:7}"
  grep -q "$CERT_DIGEST" "$HERE/$artifact" \
    || fail "$artifact does not carry the certified content digest $CERT_DIGEST"
done
read -r NOW_DIGEST _ <<<"$(bind)"
[ "$NOW_DIGEST" = "$CERT_DIGEST" ] \
  || fail "the state moved during the pass: certified $CERT_DIGEST, now $NOW_DIGEST - re-run"
# a bare (non-freeze) run must accept the binding this pass wrote - that is the post-commit case
python3 "$HERE/wave_e1_check.py" --only scan_covers_committed_union > /tmp/e1-freeze-rebind.txt 2>&1
rc_rebind=$?
grep -q "cert_bound=5" /tmp/e1-freeze-rebind.txt && [ "$rc_rebind" -eq 0 ] \
  || fail "a bare run does not accept the fresh certification (rc=$rc_rebind)"
if grep -rn "$R" "$HERE"/*.txt "$HERE"/*.json 2>/dev/null | grep -v freeze.sh >/dev/null; then
  fail 'an absolute repository path leaked into a recorded artifact'
fi
git diff --check >/dev/null 2>&1 || fail 'git diff --check is not clean'
printf 'FREEZE OK head=%s dirty=%s cert_digest=%s certified_files=%s scan=%ss check=%ss verify=%ss\n' \
       "${HEAD_SHA:0:7}" "$DIRTY" "$CERT_DIGEST" "$CERT_FILES" "$w_scan" "$w_check" "$w_verify"
