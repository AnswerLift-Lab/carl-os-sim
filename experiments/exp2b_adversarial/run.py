"""Exp 2b — Adversarial swarm conditions (extends exp2, Carl-OS limitation 5).

exp2 tested benign random dropout. The paper's limitation 5 names harsher
regimes explicitly: "adversarial environments, contested airspace, signal
jamming, cyber attack." This experiment runs those.

Conditions (N=12 drones, 500 ticks, 3 seeds; both architectures face
identical streams within a (seed, condition) cell):
  - baseline:  random dropout p=0.3 (reference point, comparable to exp2).
  - blackout:  bursty EW/weather — alternating 60-tick clear / 25-tick
               blackout windows (p=0.05 clear, p=0.95 blackout).
  - jammer:    pursuit jammer zone (radius 20) that drifts toward the
               formation centroid; links with an endpoint inside drop
               with p=0.9, else p=0.1.
  - byzantine: drone 0 is a sensor-spoofer: broadcasts position and
               centroid sightings offset by (40, 40), flies normally.
  - silent:    drone 0 goes comms-dark (never broadcasts), still flies.

Reference claims (directional, pre-registered):
  - blackout, jammer: decentralized honest-drone mean error <= centralized
    honest-drone mean error (graceful degradation extends to bursty and
    spatially-correlated comms attacks).
  - byzantine, silent: EXPLORATORY — no directional claim. We quantify the
    damage (honest-drone error vs baseline) and report it either way. If
    naive averaging breaks under spoofing, that is the finding (it would
    motivate robust aggregation as follow-up work), not a failed test.

Falsifier (directional claims): centralized honest error strictly lower
under blackout or jammer.

Metrics use honest-drone error (excluding the faulty unit) so the attack's
damage to the *rest* of the swarm is what is compared.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np  # noqa: E402

from swarm_common import (  # noqa: E402
    BlackoutWindows,
    CentralizedSwarm,
    DecentralizedSwarm,
    JammerZone,
    RandomDropout,
    run_trial,
)

N = 12
TICKS = 500
SEEDS = [7, 21, 42]
BYZANTINE_OFFSET = np.array([40.0, 40.0])

CONDITIONS = [
    ("baseline", lambda: RandomDropout(0.3), {}, ()),
    ("blackout", lambda: BlackoutWindows(), {}, ()),
    ("jammer", lambda: JammerZone(), {}, ()),
    ("byzantine", lambda: RandomDropout(0.3), {0: BYZANTINE_OFFSET}, ()),
    ("silent", lambda: RandomDropout(0.3), {}, (0,)),
]


def main():
    rows = []
    for ci, (cname, comms_factory, byz, sil) in enumerate(CONDITIONS):
        for seed in SEEDS:
            stream = seed * 1000 + ci
            dec = run_trial(DecentralizedSwarm, stream, N, TICKS,
                            comms_factory, byzantine=byz, silent=sil)
            cen = run_trial(CentralizedSwarm, stream, N, TICKS,
                            comms_factory, byzantine=byz, silent=sil)
            rows.append({"seed": seed, "condition": cname,
                         "decentralized": dec, "centralized": cen})

    by_cond = {}
    for r in rows:
        by_cond.setdefault(r["condition"], []).append(r)
    summary = {}
    for cname, rs in by_cond.items():
        md = sum(r["decentralized"]["mean_error_honest"] for r in rs) / len(rs)
        mc = sum(r["centralized"]["mean_error_honest"] for r in rs) / len(rs)
        summary[cname] = {
            "mean_dec_honest_error": md,
            "mean_cen_honest_error": mc,
            "mean_dec_all_error": sum(r["decentralized"]["mean_error"] for r in rs) / len(rs),
            "mean_cen_all_error": sum(r["centralized"]["mean_error"] for r in rs) / len(rs),
            "mean_dec_coherence": sum(r["decentralized"]["coherence_fraction"] for r in rs) / len(rs),
            "mean_cen_coherence": sum(r["centralized"]["coherence_fraction"] for r in rs) / len(rs),
            # damage ratio vs baseline (exploratory conditions)
            "dec_damage_vs_baseline": None,
            "cen_damage_vs_baseline": None,
            "n": len(rs),
        }
    base = summary["baseline"]
    for cname in ("byzantine", "silent", "blackout", "jammer"):
        s = summary[cname]
        s["dec_damage_vs_baseline"] = s["mean_dec_honest_error"] / base["mean_dec_honest_error"]
        s["cen_damage_vs_baseline"] = s["mean_cen_honest_error"] / base["mean_cen_honest_error"]

    directional = ["blackout", "jammer"]
    claim_met = all(summary[c]["mean_dec_honest_error"] <= summary[c]["mean_cen_honest_error"]
                    for c in directional)
    results = {
        "experiment": "exp2b_adversarial",
        "n_drones": N, "ticks": TICKS, "seeds": SEEDS,
        "conditions": [c[0] for c in CONDITIONS],
        "reference_claim": ("decentralized honest-drone error <= centralized "
                            "under blackout and jammer conditions; "
                            "byzantine/silent exploratory"),
        "claim_met": claim_met,
        "summary_by_condition": summary,
        "trials": rows,
    }
    outdir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print(json.dumps({"claim_met": claim_met,
                      "summary_by_condition":
                          {k: {kk: vv for kk, vv in v.items() if kk != "n"}
                           for k, v in summary.items()}}, indent=2))


if __name__ == "__main__":
    main()
