# Exp 3 — Governance invariant + layer modularity

## Part A — Governance by design (principle 4)

The architecture claims governance is *structural*, not bolted on: no
decision reaches execution without passing through the Governance layer.

- 500 adversarial proposals (unstamped, unapproved) are hurled directly
  at Orchestration and Actuation, bypassing the normal path.
- A rogue Cognition proposes forbidden action kinds and over-limit
  parameters through the normal loop for 300 ticks.

Reference claim: **zero** ungoverned actions reach Actuation's effects;
forbidden kinds are vetoed, over-limit parameters clamped.

Falsifier: any ungoverned action executed, or any over-limit value
passing through unclamped.

## Part B — Modular layers (principle 2)

Layers are swappable without destabilizing the architecture. Mid-run
(tick 150/300), the Cognition policy and the Memory backend are hot-swapped.

Reference claim: no exceptions; every executed action still carries a
governance stamp; both pre- and post-swap action kinds appear in the trace.

Falsifier: any exception, any unstamped execution, or governance missing
a tick.

## Reproduce

```bash
python experiments/exp3_governance/run.py
# results → experiments/exp3_governance/results/results.json
```
