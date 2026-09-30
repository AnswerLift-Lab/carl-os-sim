"""Exp 2 — Swarm duality-sensing tolerance (Carl-OS limitation 5).

The paper states the duality-sensing model "would need tolerance testing"
under communication degradation. This is that test.

Setup: N drones hold a ring formation around a slowly drifting centroid.
Two coordination architectures face identical comms dropout p and
identical sensing (each drone gets a noisy centroid sighting each tick):
  (a) decentralized duality sensing: each drone fuses its own noisy
      sighting with peer-broadcast sightings (per-link per-tick reception
      dropout p; last-known fallback).
  (b) centralized baseline: one controller receives position uplinks and
      centroid sightings (dropout p), computes velocity commands, sends
      them down (dropout p; drones hold last command).

Both get identical safety clamps (max speed, arena bounds) so the comparison
isolates the coordination architecture, not safety. Swarm dynamics live in
../swarm_common.py (shared with exp2b/exp2c so the experiment family runs
identical dynamics).

Reference claim: at degraded regimes (p >= 0.3) the decentralized swarm's
mean formation error is <= the centralized baseline's (emergent stabilization
without central control).
Falsifier: centralized strictly better at every dropout level.

NOTE (disclosed): the centralized controller falls back to the true
centroid on ticks where it has never received any uplink — a mild
conservative bias toward the baseline (see swarm_common.py).
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

N = 12
TICKS = 400
DROPOUTS = [0.0, 0.1, 0.3, 0.5, 0.7]
SEEDS = [7, 21, 42]


def main():
    rows = []
    for seed in SEEDS:
        for p in DROPOUTS:
            stream = seed * 1000 + int(p * 100)
            # same stream -> identical init & dropout draws per architecture
            dec = run_trial(DecentralizedSwarm, stream, N, TICKS,
                            lambda: RandomDropout(p))
            cen = run_trial(CentralizedSwarm, stream, N, TICKS,
                            lambda: RandomDropout(p))
            rows.append({"seed": seed, "dropout": p,
                         "decentralized": dec, "centralized": cen,
                         "dec_better_or_equal":
                             dec["mean_error"] <= cen["mean_error"]})

    by_p = {}
    for r in rows:
        by_p.setdefault(r["dropout"], []).append(r)
    summary = {}
    for p in sorted(by_p):
        rs = by_p[p]
        summary[str(p)] = {
            "mean_dec_error": sum(r["decentralized"]["mean_error"] for r in rs) / len(rs),
            "mean_cen_error": sum(r["centralized"]["mean_error"] for r in rs) / len(rs),
            "dec_wins": sum(1 for r in rs if r["dec_better_or_equal"]),
            "n": len(rs),
        }
    degraded = [p for p in DROPOUTS if p >= 0.3]
    claim_met = all(summary[str(p)]["mean_dec_error"] <= summary[str(p)]["mean_cen_error"]
                    for p in degraded)
    results = {
        "experiment": "exp2_swarm_tolerance",
        "n_drones": N, "ticks": TICKS, "seeds": SEEDS, "dropouts": DROPOUTS,
        "reference_claim": ("decentralized duality sensing formation error <= "
                            "centralized at dropout >= 0.3"),
        "claim_met": claim_met,
        "summary_by_dropout": summary,
        "trials": rows,
    }
    outdir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print(json.dumps({"claim_met": claim_met,
                      "summary_by_dropout": summary}, indent=2))


if __name__ == "__main__":
    main()
