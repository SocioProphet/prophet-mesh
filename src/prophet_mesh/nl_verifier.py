"""A baseline natural-language claim verifier — deliberately imperfect, honestly measured.

The estate has no natural-language supported/refuted verifier or labelled set (only
the synthetic SP-TRACE-CFR structural verifier). This is a *baseline*: a transparent
lexical-entailment heuristic that decides whether a claim is supported by its evidence.
It is intentionally not clever — it misses paraphrases and is fooled by entity swaps —
so that calibrating it produces a realistic (< 1.0) AssayStandard and demonstrates the
framework correctly refusing to let an ok verdict ride on a mediocre judge.

It is NOT a production verifier. Its value is the pipeline: a real NL corpus + a real
(imperfect) verifier → a measured AssayStandard whose F1 is earned, not assumed.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

_STOP = frozenset(
    "a an the is are was were be been being of to in on at for and or but with as by "
    "that this these those it its from into over under than then so such can could will "
    "would should may might do does did has have had".split()
)
_NEG = frozenset("not no never none cannot n't without fails failed fail nor".split())
_COVERAGE_BAR = 0.6


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower())]


def _content(text: str) -> set[str]:
    return {t for t in _tokens(text) if t not in _STOP and t not in _NEG}


def _has_negation(text: str) -> bool:
    toks = _tokens(text)
    return any(t in _NEG for t in toks) or "n't" in text.lower()


def verify(claim: str, evidence: str) -> str:
    """Return 'supported' or 'refuted' for a claim against its evidence.

    Heuristic: the claim is supported when most of its content words appear in the
    evidence AND the two agree on polarity (both negated or both not). Coverage below
    the bar, or a polarity mismatch, reads as refuted. Naive by design — high lexical
    overlap with a swapped subject still reads 'supported' (a false positive), and a
    heavy paraphrase reads 'refuted' (a false negative)."""
    claim_content = _content(claim)
    if not claim_content:
        return "refuted"
    evidence_content = _content(evidence)
    coverage = len(claim_content & evidence_content) / len(claim_content)
    polarity_mismatch = _has_negation(claim) != _has_negation(evidence)
    if coverage >= _COVERAGE_BAR and not polarity_mismatch:
        return "supported"
    return "refuted"


def predict_labelled(items: Sequence[dict]) -> list[dict]:
    """Attach this verifier's prediction to each {claim, evidence, gold} item."""
    return [{"predicted": verify(it["claim"], it["evidence"]), "gold": it["gold"], "id": it.get("id")}
            for it in items]
