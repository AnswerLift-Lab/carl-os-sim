# Carl-OS Reference Implementation: Evaluation Protocol

**DOI:** https://doi.org/10.5281/zenodo.23071051
**Supplement to:** *Carl-OS: A Modular Architecture for Intelligent Systems* —
DOI: https://doi.org/10.5281/zenodo.20173216

M. McGarvey, Principal Researcher, AnswerLift Research Lab — September 2026

> This file mirrors the DOI'd protocol record. The PDF is the record of truth.

## Purpose

The Carl-OS paper (*Carl-OS: A Modular Architecture for Intelligent Systems*,
May 2026) presents an unimplemented architecture and requests tolerance testing
for its swarm communication model. It does not contain named evaluation protocols
or predeclared falsification conditions.

## Round-1 Criteria

Shared conditions; all swarm experiments (2, 2b, 2c) run identical dynamics
(pure P-control, correlated centroid drift). Safety clamps (max speed 3.0, arena
bounds) are identical across architectures so comparisons isolate coordination
architecture, not safety.

### Experiment 1 — Event-Driven Efficiency

Setup: 2,000 ticks, 40 genuine events hidden in noise, seeds 11 / 22 / 33,
threshold sweep against a continuously polling baseline.

- **Reference Claim:** At operating threshold 0.5, the gated loop uses <50% of
  baseline compute with zero missed genuine events.
- **Falsifier:** Any missed genuine event, or compute saving <50%.

### Experiment 2 — Swarm Tolerance Under Random Dropout

Setup: N=12 drones hold a ring formation around a drifting centroid;
decentralized duality sensing compared to centralized; per link dropout
p ∈ {0.0, 0.1, 0.3, 0.5, 0.7}; 400 ticks; seeds 7 / 21 / 42.

- **Reference Claims:** At degraded regimes (p > 0.3), decentralized mean
  formation error < centralized mean formation level.
- **Falsifier:** Centralized mean error strictly lower than decentralized at any
  degraded level (p > 0.3).

### Experiment 2b — Adversarial Swarm Conditions

Setup: N=12, 500 ticks, seeds 7 / 21 / 42. Conditions:

- **Baseline:** random dropout p=0.3
- **Blackout:** bursty weather, alternating 60 tick clear, 25 tick blackout
  windows (p=0.05, p=0.95 blackout)
- **Jammer:** pursuit jammer zone (radius 20) drifting toward the formation
  centroid; links with an endpoint inside drop with p=0.9
- **Byzantine:** exploratory; drone 0 broadcasts false position and centroid
  sightings (offset 40,40), flies normally
- **Silent:** exploratory; drone 0 never broadcasts, but still flies

- **Reference Claims:** Decentralized honest drone mean error < centralized
  honest drone mean error under blackout and under jammer.
- **Falsifier:** Centralized honest error strictly lower under either condition.

### Experiment 2c — Scale Sweep

Setup: N ∈ {6, 12, 24, 48} at fixed dropout p=0.5; 400 ticks; seeds 7 / 21 / 42.

- **Reference Claim:** Gap(N) = mean centralized error − mean decentralized
  error stays positive at every N and gap(48) > gap(6) (non-shrinking; tests
  whether the experiment 2 advantage is structural).
- **Falsifier:** The gap shrinks substantially or reverses at larger N.

### Experiment 3 — Governance Invariant and Layer Modularity

Setup: (a) 500 adversarial governance bypass attempts plus a rogue cognition
layer proposing forbidden / over limit actions for 300 ticks; (b) hot swap of
the cognition and memory layers mid run (ticks 150 / 300).

- **Reference Claim A:** Zero ungoverned actions reach actuation; every executed
  action carries a governance stamp; actuation refuses all unstamped actions.
- **Falsifier A:** Bypass execution, any unstamped execution, any over limit
  action executed unclamped.
- **Reference Claim B:** Layer hot swap completes with zero swap errors,
  governance is invoked on 100% of post swap ticks, and every executed action
  remains stamped.
- **Falsifier B:** Any swap error, any tick where governance is skipped, any
  unstamped post swap execution.

## Round-2 Criteria

These experiments are not planned to be run. Their criteria are locked here in
advance should they ever become viable.

### R2a — Robust Aggregation Under Spoofing

Replace mean-fusion with median / trimmed mean fusion in the sensing layer.
Rerun Experiment 2b byzantine condition unchanged otherwise (N=12, 500 ticks,
seeds 7 / 21 / 42).

- **Reference Claim:** Decentralized honest drone error < 2x its Experiment 2b
  baseline under the same spoofing attack.
- **Falsifier:** Honest error remains > 2x baseline, median fusion is
  insufficient and stronger byzantine tolerant fusion is required.

### R2b — Scale Extension

Rerun Experiment 2c at N ∈ {48, 96} (192 if computationally feasible), p=0.5,
seeds 7 / 21 / 42.

- **Reference Claim:** The centralized minus decentralized gap stays positive
  at every tested N.
- **Exploratory:** Whether the gap asymptotes, stabilizes, or reverses beyond
  N=48, reported either way.

## Interpretation Rules

1. A reference claim is met only if the recorded numbers satisfy it as written.
   Near misses are still misses.
2. Falsification claims and negative results are published alongside positive
   ones, with mechanism discussed.
3. Exploratory conditions carry no directional claim. Their job is to find
   breakages, and breakages are reported as findings.
4. All results are simulation scale. No claim is made about real radios, real
   flight dynamics, or deployed systems.
5. Expected outcomes may partly be built into the compared configurations
   (informational asymmetries under dropout). Known asymmetries are disclosed
   per experiment; results that favour the architecture despite a conservative
   bias are noted as such.
