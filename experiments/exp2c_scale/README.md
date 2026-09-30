# Experiment 2c — Swarm scale sweep

exp2 showed a decentralized advantage at N=12. This asks whether that
advantage is fundamental or a small-N artifact: N ∈ {6, 12, 24, 48} at
fixed dropout p=0.5, seeds 7/21/42, 400 ticks. Dynamics are the shared
`experiments/swarm_common.py` used by exp2/exp2b.

## Architectural prediction

The centralized controller is an O(N) comms bottleneck (2N lossy links
through one node per tick); decentralized duality sensing costs each drone
a flat amount of work. If the advantage is structural, the error gap should
persist or widen with N.

## Reference claim (pre-registered)

gap(N) = mean centralized error − mean decentralized error stays positive
at every N **and** gap(48) ≥ gap(6) (non-shrinking).

## Recorded results (2026-09-30, local run) — claim NOT met

| N | Decentralized | Centralized | Gap |
|---|---|---|---|
| 6 | 0.97 | 2.41 | 1.44 |
| 12 | 0.86 | 2.02 | 1.17 |
| 24 | 0.77 | 1.65 | 0.88 |
| 48 | 0.68 | 1.33 | 0.65 |

Decentralized won all 12 trials (3/3 seeds at every N) — the advantage is
real at every tested scale. But the gap **narrows** with N: gap(48) <
gap(6), so the pre-registered claim is recorded as **not met**.

### What actually happened

Both architectures get *better* with N — the centralized one just improves
faster. Mechanism: more drones mean more independent noisy sightings, and
averaging loves samples. The centralized controller pools all N sightings
globally each tick, so its centroid estimate sharpens rapidly with N;
each decentralized drone hears only a subset of peers, so its estimate
sharpens more slowly. The O(N) comms bottleneck does not bind, because the
controller only needs the *average* — and averages get better with N
despite dropout.

### Reading of the negative result

The decentralized advantage concentrates where information is scarcest:
small swarms, bad comms — exactly the regime where you need it most.
Throw 48 drones at the problem and even the hub-and-spoke design does
okay, because with that many eyes, averaging smooths out the damage.
That is a useful boundary condition on the exp2 finding, not a refutation
of it: the advantage persists (positive gap, 12/12 trials) but attenuates
with scale.

## Disclosed limitations

- N > 48 untested; whether the gap asymptotes or eventually reverses is
  open.
- Formation radius fixed at 15 for all N (denser packing at large N;
  drones are points, no collision model).
- Same oracle-fallback note as exp2 (see `swarm_common.py`).
- Simulation scale; no real radios, no real flight dynamics.

## Reproduce

```
python3 experiments/exp2c_scale/run.py
```
