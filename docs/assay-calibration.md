# Calibrating a real AssayStandard

`examples/assay_standard.narration_fidelity.json` is **not a fixture** — it is the
measured reliability of a real verifier, emitted by `prophet_mesh.assay_calibrate`
from an actual calibration run. This is what turns "ok" from assertable into earned:
a `ReasoningAssay` can only project `ok` when its `verifier.calibrationRef` points at
a standard like this one, whose numbers came from measurement.

## The verifier

The **SP-TRACE-CFR narration-fidelity verifier** (`agentplane/tools/narration_fidelity_verifier.py`,
`verify_claim`) decides whether a trace narration is faithful: `POS` (supported),
`NEG` (refuted — a lie / structural mismatch), or `ZERO` (undecidable / abstain).

## How the standard was derived

The eval harness `agentplane/tools/eval_trace_cfr.py` authors programs with a
deterministic emitter — **the emitted structure IS the ground truth** — and runs the
full pipeline (ingest → CFG → normalize → recover-hammock → verifier) over ~48 items
grouped into strata with a known gold verdict each:

| stratum | n | gold | meaning |
|---|---|---|---|
| S8 | 8 | refuted (`NEG`) | claim off by one primitive class — a lie |
| S1 | 8 | not-refuted (`POS`) | truthful canonical primitives |
| S4 | 6 | not-refuted | threaded / reused decision site, truthful |
| S7 | 8 | not-refuted (`ZERO`) | latent decision — undecidable |
| S8z | 6 | not-refuted | zero-trip loop, truthful |
| S9 | 6 | not-refuted (`ZERO`) | vague / unanchored |

(S5 is a different detector — region reducibility — and is excluded.)

**Binarisation: refutation detection.** The positive class is `refuted` (`NEG`). This is
the verifier's actual discriminative task, and it puts abstentions (`ZERO`) correctly in
the negative/not-refuted class rather than miscounting them as support.

Running `verify_claim` over the 42 items (S1+S4+S7+S8+S8z+S9) against their gold:

```
truePositive  = 8   (every S8 lie caught)
falsePositive = 0   (no false accusations)
trueNegative  = 34
falseNegative = 0
→ F1 = 1.0, Cohen's kappa = 1.0 (almost-perfect) → calibrated (≥ 0.6)
```

The verifier hits its SPEC §6 acceptance (S8 lie-recall ≥ 0.95 at FP = 0), so the
standard is calibrated.

## Reproduce

```bash
# read-only: drives agentplane's verifier through prophet-mesh's emitter
python3 - <<'PY'
import sys
sys.path.insert(0, "/Users/michaelheller/dev/agentplane/tools")
sys.path.insert(0, "/Users/michaelheller/dev/prophet-mesh/src")
import eval_trace_cfr as ev, narration_fidelity_verifier as nfv
from prophet_mesh.assay_calibrate import calibrate
GOLD = {"S1":("POS",ev.stratum_S1),"S7":("ZERO",ev.stratum_S7),"S8":("NEG",ev.stratum_S8),
        "S8z":("ZERO",ev.stratum_S8z),"S4":("POS",ev.stratum_S4),"S9":("ZERO",ev.stratum_S9)}
lab=[{"predicted":"refuted" if v==nfv.NEG else "supported",
      "gold":"refuted" if g=="NEG" else "supported"} for g,fn in GOLD.values() for v in fn()]
print(calibrate("urn:srcos:verifier:narration-fidelity","cfr-eval-001",lab,positive="refuted"))
PY
```

## Honest caveat

The gold here is **synthetic and deterministic** (machine-authored structural claims),
not human- or LLM-judge labels over natural-language claims. F1 = 1.0 reflects a
clean-room eval the verifier is built to pass; a natural-language calibration set gives a
more conservative number — see below.

---

# A natural-language standard (`nl-lexical-baseline:v1`)

The estate had no natural-language supported/refuted corpus. `examples/calibration/nl_claim_verification.jsonl`
is one: **32 balanced items** (16 supported / 16 refuted) with deliberate hard cases —
paraphrases, negations, entity swaps, and numeric contradictions.

`prophet_mesh.nl_verifier` is a **baseline** lexical-entailment verifier: it supports a claim
when its content words are mostly covered by the evidence and polarity agrees. It is naive by
design — it misses paraphrases (false negatives) and is fooled by high-overlap entity swaps and
numeric contradictions (false positives).

Calibrated over the corpus (positive = `supported`):

```
truePositive 12 · falsePositive 6 · trueNegative 10 · falseNegative 4
→ F1 0.706 · precision 0.667 · recall 0.75 · kappa 0.375 (fair)
→ calibrated (just clears the 0.6 bar)
```

This is the point of the framework in one number: a mediocre verifier that *barely* earns
`calibrated`. A verdict riding on it can reach `ok`, but the fleet's `AssayRollup` will show it
sitting near the calibration floor — visibly weaker than a claim behind `narration-fidelity`.
The two committed standards bracket the reliability spectrum: **1.0 (synthetic-perfect)** and
**0.71 (real, fair)**.

The next step to a *production* NL standard is a larger, human- or LLM-judged corpus and a real
verifier (not this lexical baseline); the pipeline that turns either into a measured AssayStandard
is already here.
