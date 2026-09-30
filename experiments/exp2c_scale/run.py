"""Exp 2c — Swarm scale sweep (extends exp2).

exp2 showed the decentralized advantage at N=12. This asks whether that
advantage is fundamental or a small-N artifact: sweep N in {6, 12, 24, 48}
at fixed dropout p=0.5 (a degraded regime where exp2 found a clear gap),
3 seeds, 400 ticks.

Architectural prediction: the centralized controller is an O(N) comms
bottleneck (2N lossy links through one node per tick); decentralized
duality sensing is flat per drone. If the advantage is structural, the
error gap should persist or widen with N.

Reference claim: gap(N) = mean_cen_error - mean_dec_error is
non-shrinking with N; specifically gap(48) >= gap(6), and gap stays
positive at every N.
Falsifier: the gap shrinks substantially or reverses at larger N (the
exp2 advantage was a small-N artifact).
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from swarm_common import (  # noqa: E402
    CentralizedSwarm,
    DecentralizedSwarm,
    RandomDropout,
    run_trial,
)

SIZES = [6, 12, 24, 48]
TICKS = 400
P = 0.5
SEEDS = [7, 21, 42]


def main():
    rows = []
    for ni, n in enumerate(SIZES):
        for seed in SEEDS:
            stream = seed * 1000 + ni
            dec = run_trial(DecentralizedSwarm, stream, n, TICKS,
                            lambda: RandomDropout(P))
            cen = run_trial(CentralizedSwarm, stream, n, TICKS,
                            lambda: RandomDropout(P))
            rows.append({"seed": seed, "n": n,
                         "decentralized": dec, "centralized": cen})

    by_n = {}
    for r in rows:
        by_n.setdefault(r["n"], []).append(r)
    summary = {}
    for n in sorted(by_n):
        rs = by_n[n]
        md = sum(r["decentralized"]["mean_error"] for r in rs) / len(rs)
        mc = sum(r["centralized"]["mean_error"] for r in rs) / len(rs)
        summary[str(n)] = {
            "mean_dec_error": md,
            "mean_cen_error": mc,
            "gap": mc - md,
            "dec_wins": sum(1 for r in rs
                            if r["decentralized"]["mean_error"] <= r["centralized"]["mean_error"]),
            "n_seeds": len(rs),
        }
    gaps = [summary[str(n)]["gap"] for n in sorted(by_n)]
    claim_met = (all(g > 0 for g in gaps)
                 and summary["48"]["gap"] >= summary["6"]["gap"])
    results = {
        "experiment": "exp2c_scale",
        "sizes": SIZES, "ticks": TICKS, "dropout": P, "seeds": SEEDS,
        "reference_claim": ("centralized-minus-decentralized error gap stays "
                            "positive and non-shrinking with swarm size N"),
        "claim_met": claim_met,
        "summary_by_n": summary,
        "trials": rows,
    }
    outdir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print(json.dumps({"claim_met": claim_met,
                      "summary_by_n": summary}, indent=2))


if __name__ == "__main__":
    main()
