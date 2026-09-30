# Exp 2 — Swarm duality-sensing tolerance

The paper's limitation 5 states the duality-sensing model *"would need
tolerance testing"* under communication degradation. This is that test.

## Setup

12 drones hold a ring formation around a slowly drifting centroid (400
ticks). Both architectures get identical sensing — each drone takes a
noisy centroid sighting (σ=2.0) every tick — and identical safety clamps
(max speed, arena bounds), so the comparison isolates the *coordination
architecture*:

- **decentralized** (Carl-OS duality sensing): each drone averages its own
  sighting with peers' shared sightings (per-link per-tick reception
  dropout *p*; last-known fallback), then P-controls to its slot.
- **centralized**: one controller receives position + sighting uplinks
  (dropout *p*), averages, computes velocity commands, sends them down
  (dropout *p*; drones hold last command).

Dropout levels: 0, 0.1, 0.3, 0.5, 0.7. Three seeds. Identical initial
conditions per (seed, *p*) pair.

## Reference claim

At degraded regimes (*p* ≥ 0.3), decentralized mean formation error ≤
centralized mean formation error — emergent stabilization without
central control.

## Falsifier

Centralized strictly better at every dropout level.

## Why the decentralized design wins under degradation

Each drone always has its own fresh local sighting; only the *shared*
supplement degrades. In the centralized design *all* information must
survive the uplink. That asymmetry is the architectural point, not a
rigged comparison — the baseline is tied with decentralized at *p*=0.

Swarm dynamics live in `experiments/swarm_common.py`, shared with
exp2b/exp2c so the experiment family runs identical dynamics (verified:
refactored run reproduces the original results bit-for-bit).

## Reproduce

```bash
python experiments/exp2_swarm/run.py
# results → experiments/exp2_swarm/results/results.json
```
