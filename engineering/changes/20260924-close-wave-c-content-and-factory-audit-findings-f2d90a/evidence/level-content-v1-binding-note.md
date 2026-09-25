# `level-content-v1` integrity binding — what `self_check.body_sha256` does and does not prove

Contract: [`../../contracts/level-content-v1.json`](../../contracts/level-content-v1.json)
Checker: [`wave_c_check.py`](wave_c_check.py) (`INTEGRITY_BIND`, `body_digest`, `reseal`,
`validate_manifest`, `manifest_selfcheck`)
Trigger: test review finding **F1** (BLOCKING) — `evidence/review-test.md` §6.

## What was wrong

The first revision sealed the contract with `sha256(json.dumps(body, sort_keys=True))`. That is an
**accident** guard: it catches a stale or half-edited file, and nothing else. Anyone who changes a
value can recompute the same expression and the committed contract looks sealed again. Worse, the
probe named in AC-004 (`manifest_selfcheck`) called `validate_manifest(manifest)` **without** the
`corpus_hashes` argument, so the branch that compares the manifest to the shipped data never ran in
the probe at all — it only ran inside `--write-manifest`. And `maps[*].background_sha256` was never
compared to anything, while `maps[*].background` was only tested for emptiness.

The reviewer demonstrated the consequence: claiming `L02S16.background = zone_999_original.png`
(a file that does not exist) or `L02S16.background_sha256 = abab…` (a fabricated digest), then
recomputing the digest, left **all nine probes green with rc=0**. AC-004's own wording makes an
unflippable tamper case fatal, so that was blocking.

## What it is now

1. **Live re-derivation, in the probe.** `validate_manifest` re-derives every data claim from
   `Exolon/Resources`: the canonical digest of each map, the backdrop file the map actually
   references, the sha256 of that backdrop's bytes (resolved by basename, the way
   `TMXTileMapRenderer.swift:84-85` resolves it), the `imagelayer` count, and whether each declared
   identical pair really hashes equal. `corpus_hashes` now defaults to a fresh recomputation, so no
   call site can skip it.
2. **Keyed seal.** `body_digest` mixes an embedded constant (`INTEGRITY_BIND`) into the hashed
   bytes. The tamper controls deliberately **re-seal with `reseal()` before being judged**, so they
   assert that the *content* is rejected, not that the checksum moved. A re-seal done the old
   unkeyed way is rejected too (`unkeyed_reseal_rejected`).
3. **AC-004 traceability fixed.** The divergent-pair case now lives in the probe AC-004 names:
   `declare_nonidentical_pair_rejected` replaces one declared pair with `L01S01/L01S02`, which are
   **not** identical in the shipped data, re-seals, and requires rejection.

## The honest limit — read this before citing the digest as protection

| Claim | True? |
| --- | --- |
| Editing a manifest value without regenerating it is detected | **Yes** — accident/staleness guard. |
| Forging a data value (map digest, backdrop name/bytes, pair identity) is detected | **Yes**, but by the **live-corpus comparison**, not by the digest. The digest only has to be self-consistent for the probe to get as far as the content checks. |
| A forger who reads `INTEGRITY_BIND` in this public file cannot re-seal | **No.** The constant is in the repository. This is a construction barrier against accidental or lazy tamper, not a cryptographic one. |
| Prose fields (`ruling.*`, `pair_notes.*`) are protected from a re-sealed edit | **No.** Anyone who re-seals can rewrite the narrative. What protects the narrative is `level_pair_manifest_pinned`, which asserts the disclosures exist and that `ruling.decision` is labelled as a ruling, plus human review of the diff. |
| `body_sha256` binds `canonicalization_version` to every hash (INV-001 wording) | **Only in the sense that changing the version invalidates the seal.** It does not make the version tamper-evident against someone who re-seals. |

So: **do not** cite `body_sha256` as evidence that the contract cannot be forged. Cite the
`Exolon/Resources` blob comparison (`no_invented_content`) plus the live re-derivation above. The
digest's real job is to make an unnoticed edit loud.

## Reproduction of the tamper matrix

See [`f1-tamper-proof.txt`](f1-tamper-proof.txt): the reviewer's cases C7–C11 plus K10–K12 (same
tamper, re-sealed with the genuine embedded key), each run as an edit to the committed JSON in an
isolated copy followed by the **whole** nine-probe net, with a pristine meta-control run first.
Every row is red; restoring the authentic contract returns the net to green.
