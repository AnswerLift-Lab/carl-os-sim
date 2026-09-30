"""Exp 1 — Event-driven efficiency (Carl-OS design principle 3).

Question: does threshold-gated loop initiation actually save computation
without missing genuine environmental events?

Setup: a SignalEnvironment emits mostly noise with occasional genuine
events. Two agents observe the same stream:
  (a) event-driven: full loop only when perceived change >= threshold tau
  (b) continuous baseline: full loop every tick (force=True)

Reference claim: at the operating threshold, the event-driven agent uses
<50% of the baseline's layer invocations while missing zero genuine events.
Falsifier: any missed genuine event at the operating point, or savings <50%.

A genuine event at tick t counts as MISSED if no full loop ran within
[t, t + RESPONSE_WINDOW].
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from carlos import ControlLoop, SignalEnvironment, default_layers
from carlos.layers import Cognition, Governance
from carlos.types import ProposedAction

TICKS = 2000
N_EVENTS = 40
RESPONSE_WINDOW = 3
SEEDS = [11, 22, 33]
THRESHOLDS = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.7]


def responder_policy(percept, ctx):
    # trivial responder: propose a no-op-ish action when triggered
    return [ProposedAction(tick=percept.tick, kind="acknowledge",
                           params={"priority": 1},
                           rationale="event acknowledged")]


def layer_invocations(layers) -> int:
    return sum(getattr(layers[k], "calls", 0)
               for k in ("perception", "memory", "cognition",
                         "governance", "orchestration", "actuation"))


def run_agent(env, threshold, force=False):
    layers = default_layers(
        environment=env,
        cognition=Cognition(policy=responder_policy),
        governance=Governance(),
    )
    loop = ControlLoop(layers=layers, threshold=threshold)
    loop.run(TICKS, force=force)
    return loop


def missed_events(env, loop) -> int:
    run_ticks = {t.tick for t in loop.stats.traces}
    missed = 0
    for t in sorted(env.event_ticks):
        if not any(rt in run_ticks for rt in range(t, t + RESPONSE_WINDOW + 1)):
            missed += 1
    return missed


def main():
    sweep = []
    for seed in SEEDS:
        # baseline first: continuous agent on its own environment twin
        env_b = SignalEnvironment(seed=seed, n_events=N_EVENTS)
        env_b.schedule_events(TICKS, tail=RESPONSE_WINDOW + 1)
        base = run_agent(env_b, threshold=0.0, force=True)
        base_compute = layer_invocations(base.layers)
        base_missed = missed_events(env_b, base)

        for tau in THRESHOLDS:
            env = SignalEnvironment(seed=seed, n_events=N_EVENTS)
            env.schedule_events(TICKS, tail=RESPONSE_WINDOW + 1)
            loop = run_agent(env, threshold=tau)
            compute = layer_invocations(loop.layers)
            sweep.append({
                "seed": seed, "threshold": tau,
                "runs": loop.stats.runs, "skips": loop.stats.skips,
                "compute": compute,
                "compute_fraction": compute / base_compute,
                "missed_genuine_events": missed_events(env, loop),
                "false_triggers": max(0, loop.stats.runs - N_EVENTS),
                "baseline_compute": base_compute,
                "baseline_missed": base_missed,
            })

    # operating point: largest compute saving with zero missed events
    # across ALL seeds (worst-case over seeds)
    by_tau = {}
    for row in sweep:
        by_tau.setdefault(row["threshold"], []).append(row)
    operating = None
    for tau in sorted(by_tau):
        rows = by_tau[tau]
        worst_missed = max(r["missed_genuine_events"] for r in rows)
        mean_frac = sum(r["compute_fraction"] for r in rows) / len(rows)
        if worst_missed == 0:
            operating = {"threshold": tau,
                         "worst_missed_events": worst_missed,
                         "mean_compute_fraction": mean_frac,
                         "mean_saving": 1 - mean_frac}

    claim_met = bool(operating and operating["mean_saving"] > 0.5)
    results = {
        "experiment": "exp1_event_driven",
        "ticks": TICKS, "n_events": N_EVENTS, "seeds": SEEDS,
        "response_window": RESPONSE_WINDOW,
        "reference_claim": ("event-driven initiation uses <50% of baseline "
                            "compute with zero missed genuine events"),
        "operating_point": operating,
        "claim_met": claim_met,
        "sweep": sweep,
    }
    outdir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print(json.dumps({"claim_met": claim_met,
                      "operating_point": operating}, indent=2))


if __name__ == "__main__":
    main()
