"""Exp 3 — Governance structural invariant + layer modularity.

Part A (governance by design, Carl-OS principle 4): the architecture claims
governance is structural, not bolted on. Test: hurl adversarial proposals
directly at Orchestration and Actuation, bypassing the normal path, plus run
a rogue Cognition that proposes unsafe actions through the normal loop.
Reference claim: ZERO ungoverned actions reach Actuation's effects.

Part B (modular layers, Carl-OS principle 2): layers are swappable without
destabilizing the architecture. Test: mid-run, hot-swap the Cognition policy
and the Memory backend; the loop must continue and governance coverage must
stay at 100%.
Reference claim: no exceptions, no ungoverned actions, before and after.
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from carlos import ControlLoop, default_layers
from carlos.layers import (Actuation, Cognition, Governance, Memory,
                           Orchestration)
from carlos.types import GovernedAction, ProposedAction

N_ADVERSARIAL = 500
TICKS = 300
SWAP_AT = 150


def unsafe_proposals(rng, tick):
    """Rogue cognition: proposes unsafe / forbidden actions."""
    kind = rng.choice(["thrust", "delete", "override", "thrust"])
    params = {"thrust": rng.uniform(0, 20.0), "priority": 1}
    return [ProposedAction(tick=tick, kind=kind, params=params,
                           rationale="rogue")]


def max_thrust_constraint(limit=5.0):
    def check(p):
        thrust = p.params.get("thrust", 0.0)
        if p.kind in ("delete", "override"):
            return False, f"forbidden kind: {p.kind}", {}
        if thrust > limit:
            return True, "", {"thrust": limit, "clamped": True}
        return True, "", {}
    return check


def run_part_a(seed):
    rng = random.Random(seed)
    layers = default_layers(
        cognition=Cognition(policy=lambda perc, ctx: unsafe_proposals(rng, perc.tick)),
        governance=Governance(constraints=[max_thrust_constraint()]),
        actuation=Actuation(effect_fn=lambda a: {"add": {"x": a.params.get("thrust", 0.0)}}),
    )
    loop = ControlLoop(layers=layers, threshold=0.0)

    # direct bypass attempts: throw ungoverned actions at the late layers
    orch = layers["orchestration"]
    act = layers["actuation"]
    bypass_executed = 0
    for i in range(N_ADVERSARIAL):
        sneaky = GovernedAction(tick=i, kind="thrust", approved=False,
                                params={"thrust": 999.0}, stamp="")
        # try orchestration path
        seq = orch.sequence([sneaky])
        fx = act.execute(seq)
        # try actuation directly
        fx2 = act.execute([sneaky])
        if fx or fx2:
            bypass_executed += 1

    loop.run(TICKS, force=True)

    # audit the rogue-cognition run
    ungoverned_executed = 0
    over_limit_executed = 0
    for a in act.executed:
        if not (a.approved and a.stamp):
            ungoverned_executed += 1
        if a.params.get("thrust", 0.0) > 5.0:
            over_limit_executed += 1
    forbidden = [e for e in layers["governance"].audit
                 if not e["approved"]]
    return {
        "bypass_attempts": N_ADVERSARIAL,
        "bypass_executed": bypass_executed,
        "rogue_ticks": TICKS,
        "ungoverned_executed": ungoverned_executed,
        "over_limit_executed": over_limit_executed,
        "governance_vetoes": layers["governance"].vetoes,
        "forbidden_kinds_blocked": len(forbidden),
        "actuation_refusals": act.refusals,
    }


def run_part_b(seed):
    layers = default_layers(
        cognition=Cognition(policy=lambda perc, ctx:
                            [ProposedAction(tick=perc.tick, kind="ping",
                                            params={"priority": 1})]),
        governance=Governance(),
    )
    loop = ControlLoop(layers=layers, threshold=0.0)
    errors = []
    for t in range(TICKS):
        if t == SWAP_AT:
            # hot-swap cognition policy AND memory backend mid-run
            loop.swap_layer("cognition", Cognition(
                policy=lambda perc, ctx:
                [ProposedAction(tick=perc.tick, kind="pong",
                                params={"priority": 2})]))
            loop.swap_layer("memory", Memory(window=10))
        try:
            loop.tick(force=True)
        except Exception as e:  # noqa: BLE001
            errors.append(f"tick {t}: {e}")
    kinds = {a.kind for a in layers["actuation"].executed}
    gov = loop.layers["governance"]
    act = loop.layers["actuation"]
    all_stamped = all(a.approved and a.stamp for a in act.executed)
    return {
        "ticks": TICKS, "swap_at": SWAP_AT,
        "errors": errors,
        "action_kinds_seen": sorted(kinds),  # expect both ping and pong
        "governance_calls": gov.calls,
        "governance_calls_expected": TICKS,
        "all_executed_stamped": all_stamped,
        "executed": len(act.executed),
    }


def main():
    a = run_part_a(seed=5)
    b = run_part_b(seed=6)
    claim_a = (a["bypass_executed"] == 0 and a["ungoverned_executed"] == 0
               and a["over_limit_executed"] == 0)
    claim_b = (not b["errors"] and b["all_executed_stamped"]
               and b["governance_calls"] == b["governance_calls_expected"]
               and set(["ping", "pong"]) <= set(b["action_kinds_seen"]))
    results = {
        "experiment": "exp3_governance_modularity",
        "part_a_governance_invariant": a,
        "part_b_layer_swap": b,
        "reference_claim_a": "zero ungoverned actions reach actuation",
        "reference_claim_b": "mid-run layer swap: no failures, governance stays 100%",
        "claim_a_met": claim_a,
        "claim_b_met": claim_b,
    }
    outdir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print(json.dumps({"claim_a_met": claim_a, "claim_b_met": claim_b,
                      "part_a": a, "part_b": b}, indent=2))


if __name__ == "__main__":
    main()
