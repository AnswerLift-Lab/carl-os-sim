# carl-os-sim

Reference implementation of the **Carl-OS** modular agent architecture
(M. McGarvey, *Carl-OS: A Modular Architecture for Intelligent Systems*,
May 2026): the seven-layer recursive control loop, running in simulation.

## What this is

The paper's limitation #1 is stated plainly: *"Carl-OS has not been
implemented. No prototype exists."* This repo is the first loop back —
a working implementation of the architecture, with its core mechanisms
executable and inspectable.

**This is a reference implementation, not a validation claim.** It shows
the architecture executes: layers are swappable, the loop recurses,
governance sits structurally between cognition and actuation. Each
experiment states a *reference claim* and what would count against it,
in the lab's standing policy: positive, negative, and null findings all
get published.

## The seven layers

| # | Layer | Role |
|---|-------|------|
| 7 | Environment | Operational context; source of stimuli, recipient of acts |
| 4 | Perception | Raw signals → structured percept + change magnitude |
| 3 | Memory | Contextual state; temporal comparator for each percept |
| 1 | Cognition | Reasoning & planning; proposes, never executes |
| 5 | Governance | Validates every proposal; issues execution stamps |
| 2 | Orchestration | Sequences approved actions only |
| 6 | Actuation | Executes; **structurally refuses unstamped actions** |

The loop is event-driven: the environment is sensed every tick, but the
full sequence runs only on meaningful state change (percept change ≥
threshold). Actuation's effects become the next tick's environment —
that is the recursion.

## Experiments

1. **`exp1_event_driven`** — Threshold-gated initiation vs. continuous
   polling. Reference claim: <50% of baseline compute with zero missed
   genuine events. *(Design principle 3: event-driven operation.)*
2. **`exp2_swarm`** — Duality-sensing swarm formation under comms
   degradation vs. centralized control. Reference claim: decentralized
   error ≤ centralized at dropout ≥ 0.3. *(The paper's limitation 5
   explicitly requests this tolerance test.)*
   - **`exp2b_adversarial`** — The harsher regimes limitation 5 names:
     bursty blackout windows, a pursuit jammer zone, a byzantine
     sensor-spoofer (exploratory), and a comms-dark drone (exploratory).
     Directional claims (blackout, jammer) met; the byzantine test found
     naive mean-aggregation breaks for *both* architectures — reported
     as found, with robust aggregation noted as follow-up work.
   - **`exp2c_scale`** — N ∈ {6, 12, 24, 48} at fixed dropout. The
     pre-registered claim (gap non-shrinking with N) was **not met**:
     the decentralized advantage persists at every scale (12/12 trials)
     but narrows, because sensor averaging helps the centralized
     controller more. A useful boundary condition, published as found.
   All three swarm experiments share `experiments/swarm_common.py` so
   the family runs identical dynamics.
3. **`exp3_governance`** — (a) 500 adversarial governance-bypass attempts;
   (b) mid-run hot-swap of the Cognition and Memory layers. Reference
   claims: zero ungoverned actions reach actuation; swap causes no
   failures and governance stays complete. *(Principles 2 & 4:
   modular layers, governance by design.)*

Each experiment has its own README with the claim, the falsifier, and
how to reproduce. Results are stored as JSON under `results/`.

## Reproduce

```bash
pip install -r requirements.txt
pytest                              # full suite (core + experiments)
python experiments/exp1_event_driven/run.py
python experiments/exp2_swarm/run.py
python experiments/exp2b_adversarial/run.py
python experiments/exp2c_scale/run.py
python experiments/exp3_governance/run.py
```

## Layout

```
carlos/                 # the architecture: types, layers, control loop
experiments/swarm_common.py   # shared swarm dynamics (exp2/2b/2c)
experiments/exp1_event_driven/
experiments/exp2_swarm/
experiments/exp2b_adversarial/
experiments/exp2c_scale/
experiments/exp3_governance/
tests/                  # layer contracts, loop invariants, experiment checks
```

## Related

- Source paper: *Carl-OS: A Modular Architecture for Intelligent Systems* —
  https://doi.org/10.5281/zenodo.20173216
- Evaluation protocol (DOI'd, published before this repo): *Carl-OS Reference
  Implementation: Evaluation Protocol* —
  https://doi.org/10.5281/zenodo.23071051
- [brs-validation](https://github.com/AnswerLift-Lab/brs-validation) —
  BRS is the Carl-OS governance layer worked out in detail; its
  simulation-scale mechanism tests live there.
