# Golden-set flip report

Baseline: name=jaccard@0.85, address=jaccard@0.8, confidence>=0.95
Corpus size: 34; golden (AUTO_APPROVED) pairs: 18

A *flip* is a golden pair whose decision is no longer AUTO_APPROVED under the
candidate configuration. Flips are a tripwire: each must be classified as an
acceptable correction or a regression in tests/golden/signed_off_flips.json.

## Candidate: active-config

name=jaccard@0.85, address=jaccard@0.8

Flipped decisions: **0** (unsigned: 0)

No flips - every golden pair still resolves to AUTO_APPROVED.

## Candidate: levenshtein

name=levenshtein@0.97, address=levenshtein@0.98

Flipped decisions: **0** (unsigned: 0)

No flips - every golden pair still resolves to AUTO_APPROVED.

## Candidate: levenshtein-names-only

name=levenshtein@0.97, address=jaccard@0.8

Flipped decisions: **0** (unsigned: 0)

No flips - every golden pair still resolves to AUTO_APPROVED.

## Candidate: levenshtein-addresses-only

name=jaccard@0.85, address=levenshtein@0.98

Flipped decisions: **0** (unsigned: 0)

No flips - every golden pair still resolves to AUTO_APPROVED.
