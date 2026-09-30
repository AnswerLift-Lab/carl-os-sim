# Experiment 2b — Adversarial swarm conditions

Extends exp2 (benign random dropout) into the harsher regimes Carl-OS
limitation 5 names explicitly: *"adversarial environments, contested
airspace, signal jamming, cyber attack."*

## Conditions

N=12 drones, 500 ticks, seeds 7/21/42. Both architectures face identical
random streams within each (seed, condition) cell. Dynamics are the shared
`experiments/swarm_common.py` used by exp2/exp2c.

| Condition | What it is |
|---|---|
| `baseline` | Random dropout p=0.3 (reference point, comparable to exp2) |
| `blackout` | Bursty EW/weather: alternating 60-tick clear / 25-tick blackout windows (p=0.05 clear, p=0.95 blackout) |
| `jammer` | Pursuit jammer zone (radius 20) drifting toward the formation centroid; links with an endpoint inside drop with p=0.9, else p=0.1 |
| `byzantine` | Drone 0 is a sensor-spoofer: broadcasts position + centroid sightings offset by (40, 40); flies normally. **Exploratory.** |
| `silent` | Drone 0 goes comms-dark (never broadcasts), still flies. **Exploratory.** |

## Reference claims (pre-registered)

- **Directional:** decentralized honest-drone mean error ≤ centralized
  honest-drone error under `blackout` and `jammer`.
- **Exploratory (`byzantine`, `silent`):** no directional claim. Damage is
  quantified (honest-drone error vs baseline) and reported either way.

## Recorded results (2026-09-30, local run)

Mean honest-drone formation error (damage = × baseline):

| Condition | Decentralized | Centralized | Damage (dec / cen) |
|---|---|---|---|
| baseline | 0.77 | 1.04 | — |
| blackout | 0.86 | 2.26 | 1.11× / 2.17× |
| jammer | 1.38 | 11.24 | 1.79× / 10.77× |
| byzantine | 4.81 | 4.89 | 6.26× / 4.68× |
| silent | 0.80 | 1.08 | 1.05× / 1.04× |

**Directional claims: MET.** Under blackout the decentralized swarm barely
notices (1.11× damage vs 2.17×); under the pursuit jammer the centralized
formation disintegrates entirely (coherence 0.01, error 11.24) while the
decentralized swarm degrades gracefully (error 1.38, coherence 0.98).

**Exploratory findings (reported as found):**
- *Byzantine:* naive mean-aggregation breaks for **both** architectures —
  one liar poisons the shared centroid estimate (6.26× / 4.68× damage).
  Decentralized is marginally less bad (4.81 vs 4.89 honest error), but the
  real finding is that neither is robust to spoofing. Follow-up work:
  robust aggregation (median / trimmed mean) in the sensing fusion.
- *Silent:* a comms-dark drone is handled gracefully by decentralization
  (1.05× damage — the dark drone flies fine on its own sighting). The
  centralized controller loses the drone itself (all-drone error 4.69:
  it commands the dark drone from a stale position estimate).

## Disclosed limitations

- Same oracle-fallback note as exp2 (see `swarm_common.py`): on ticks where
  the centralized controller has never received an uplink it uses the true
  centroid. Under blackout this is a mild conservative bias *toward* the
  baseline — results favouring decentralization are conservative.
- Single attacker / single dark drone; coordinated multi-attacker
  scenarios untested.
- Simulation scale; no real radios, no real flight dynamics.

## Reproduce

```
python3 experiments/exp2b_adversarial/run.py
```
