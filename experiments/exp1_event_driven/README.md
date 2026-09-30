# Exp 1 — Event-driven efficiency

Tests Carl-OS design principle 3: the loop is initiated by *meaningful
state change*, not run continuously against all input.

## Setup

A `SignalEnvironment` emits mostly noise (Gaussian, σ=0.05, mean-reverting)
with 40 scheduled genuine events (impulses of magnitude 0.6–1.0) over 2000
ticks. Two agents observe identical streams (same seed):

- **event-driven**: full 7-layer loop only when perceived change ≥ τ
- **continuous**: full loop every tick

## Reference claim

At the operating threshold, the event-driven agent uses **<50% of the
baseline's layer invocations** while missing **zero genuine events**.
A genuine event at tick *t* counts as missed if no full loop ran within
*[t, t+3]*.

## Falsifier

Any missed genuine event at the operating point, or compute savings <50%.

## Method notes

- Events are not scheduled in the final ticks of the horizon: an event on
  the last tick could never be observed, which would fake a miss.
- The operating point is the largest τ with zero misses across all seeds
  (worst-case over seeds, not average).

## Reproduce

```bash
python experiments/exp1_event_driven/run.py
# results → experiments/exp1_event_driven/results/results.json
```
