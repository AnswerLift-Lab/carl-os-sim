"""
Shared swarm simulation primitives for the Carl-OS swarm experiments.

Faithful port of the exp2 dynamics (pure P-control, correlated centroid
drift, default_rng streams), parametrized by swarm size n and with
pluggable comms models + per-drone fault behaviours so exp2b
(adversarial) and exp2c (scale) run the *same* dynamics as exp2.

Architectures:
- DecentralizedSwarm: each drone estimates the target centroid from its own
  noisy sighting fused with peer-broadcast sightings (duality sensing).
  No hub; last-known fallback per peer.
- CentralizedSwarm: one controller collects uplinks (position + centroid
  sighting), computes P-control commands from the averaged estimate, sends
  them down. Drones hold their last command when the downlink drops.

Comms models expose: link_up(rng, tick, pos_a, pos_b) -> bool
  - RandomDropout(p): independent per-link dropout.
  - BlackoutWindows: deterministic alternating clear/blackout schedule.
  - JammerZone: pursuit jammer; links with an endpoint inside the radius
    drop with p_inside, else p_outside.

Faults (byzantine / silent) are configured on the constructors:
  - byzantine: {drone_id: offset} -- broadcasts false position + false
    centroid sightings, flies normally (sensor-spoofing attack).
  - silent: ids that never broadcast (comms-dark, still fly).

Metrics report all-drone error and honest-drone error (excluding faulty
units) so an attack's damage to the *rest* of the swarm is visible.

NOTE (disclosed limitation, inherited from exp2): when the centralized
controller has *never* received any uplink, it falls back to the true
centroid for that tick. In exp2 this is rare; under blackout conditions it
is a mild conservative bias *toward* the centralized baseline (it gets an
oracle glimpse while decentralized drones use their own noisy sightings).
Results that favour decentralization despite this bias are conservative.
"""

import math

import numpy as np

ARENA = 100.0
FORM_RADIUS = 15.0
MAX_SPEED = 3.0
K_GAIN = 0.5
CENTROID_NOISE = 2.0
COHERENCE_BOUND = 6.0


def slot_offsets(n):
    return np.array([[FORM_RADIUS * math.cos(2 * math.pi * i / n),
                      FORM_RADIUS * math.sin(2 * math.pi * i / n)]
                     for i in range(n)])


def clamp_speed(v):
    nrm = np.linalg.norm(v)
    return v if nrm <= MAX_SPEED else v * (MAX_SPEED / nrm)


# ---------------------------------------------------------------------------
# Comms models
# ---------------------------------------------------------------------------
class RandomDropout:
    """Independent per-link dropout with probability p."""

    def __init__(self, p):
        self.p = p

    def link_up(self, rng, tick, pos_a, pos_b):
        return rng.random() >= self.p

    def tick_update(self, info):
        pass


class BlackoutWindows:
    """Deterministic alternating clear / blackout schedule (bursty EW or
    weather). Same schedule for both architectures within a trial."""

    def __init__(self, clear=60, blackout=25, p_clear=0.05, p_black=0.95):
        self.clear = clear
        self.blackout = blackout
        self.p_clear = p_clear
        self.p_black = p_black

    def _in_blackout(self, tick):
        return (tick % (self.clear + self.blackout)) >= self.clear

    def link_up(self, rng, tick, pos_a, pos_b):
        p = self.p_black if self._in_blackout(tick) else self.p_clear
        return rng.random() >= p

    def tick_update(self, info):
        pass


class JammerZone:
    """Pursuit jammer: drifts toward the formation centroid each tick. Any
    link with an endpoint inside the jammer radius drops with p_inside,
    otherwise with p_outside."""

    def __init__(self, radius=20.0, p_inside=0.9, p_outside=0.1, speed=0.5):
        self.center = np.array([50.0, 50.0])
        self.radius = radius
        self.p_inside = p_inside
        self.p_outside = p_outside
        self.speed = speed

    def tick_update(self, info):
        target = info["centroid"]
        d = target - self.center
        dist = float(np.linalg.norm(d))
        if dist > 1e-9:
            self.center = self.center + d / dist * min(self.speed, dist)

    def _inside(self, pos):
        return pos is not None and float(np.linalg.norm(pos - self.center)) <= self.radius

    def link_up(self, rng, tick, pos_a, pos_b):
        jammed = self._inside(pos_a) or self._inside(pos_b)
        p = self.p_inside if jammed else self.p_outside
        return rng.random() >= p


# ---------------------------------------------------------------------------
# Swarms (dynamics identical to exp2/run.py, parametrized by n)
# ---------------------------------------------------------------------------
class DecentralizedSwarm:
    def __init__(self, rng, n, comms, byzantine=None, silent=()):
        self.rng = rng
        self.n = n
        self.comms = comms
        self.byzantine = dict(byzantine or {})
        self.silent = set(silent)
        self.pos = rng.uniform(20, 80, size=(n, 2))
        self.offsets = slot_offsets(n)
        self.known_pos = {i: {j: self.pos[j].copy() for j in range(n) if j != i}
                          for i in range(n)}
        self.known_cen = {i: {} for i in range(n)}

    def _on_wire(self, j, true_pos_j, true_obs_j):
        if j in self.byzantine:
            off = self.byzantine[j]
            return true_pos_j + off, true_obs_j + off
        return true_pos_j, true_obs_j

    def step(self, centroid, tick):
        rng, n = self.rng, self.n
        self.comms.tick_update({"centroid": centroid})
        obs = {i: centroid + rng.normal(0, CENTROID_NOISE, 2) for i in range(n)}
        for i in range(n):
            for j in range(n):
                if i != j and j not in self.silent:
                    if self.comms.link_up(rng, tick, self.pos[i], self.pos[j]):
                        bpos, bcen = self._on_wire(j, self.pos[j], obs[j])
                        self.known_pos[i][j] = bpos.copy()
                        self.known_cen[i][j] = bcen
        for i in range(n):
            all_obs = [obs[i]] + list(self.known_cen[i].values())
            est_centroid = np.mean(all_obs, axis=0)
            slot = est_centroid + self.offsets[i]
            v = K_GAIN * (slot - self.pos[i])
            self.pos[i] += clamp_speed(v)
            self.pos[i] = np.clip(self.pos[i], 0, ARENA)

    def _errors(self, centroid, honest_only):
        slots = centroid + self.offsets
        err = np.linalg.norm(self.pos - slots, axis=1)
        if honest_only:
            err = err[list(honest_only)]
        return err

    def formation_error(self, centroid, honest_only=None):
        return float(np.mean(self._errors(centroid, honest_only)))


class CentralizedSwarm:
    def __init__(self, rng, n, comms, byzantine=None, silent=()):
        self.rng = rng
        self.n = n
        self.comms = comms
        self.byzantine = dict(byzantine or {})
        self.silent = set(silent)
        self.pos = rng.uniform(20, 80, size=(n, 2))
        self.offsets = slot_offsets(n)
        self.est = self.pos.copy()
        self.cen_obs = {}
        self.cmd = np.zeros((n, 2))

    def _on_wire(self, j, true_pos_j, true_obs_j):
        if j in self.byzantine:
            off = self.byzantine[j]
            return true_pos_j + off, true_obs_j + off
        return true_pos_j, true_obs_j

    def step(self, centroid, tick):
        rng, n = self.rng, self.n
        self.comms.tick_update({"centroid": centroid})
        for i in range(n):  # uplink
            if i in self.silent:
                continue
            if self.comms.link_up(rng, tick, self.pos[i], None):
                true_obs = centroid + rng.normal(0, CENTROID_NOISE, 2)
                bpos, bcen = self._on_wire(i, self.pos[i], true_obs)
                self.est[i] = bpos.copy()
                self.cen_obs[i] = bcen
        est_centroid = (np.mean(list(self.cen_obs.values()), axis=0)
                        if self.cen_obs else centroid)
        for i in range(n):  # downlink
            if self.comms.link_up(rng, tick, None, self.pos[i]):
                slot = est_centroid + self.offsets[i]
                self.cmd[i] = clamp_speed(K_GAIN * (slot - self.est[i]))
            self.pos[i] += self.cmd[i]
            self.pos[i] = np.clip(self.pos[i], 0, ARENA)

    def _errors(self, centroid, honest_only):
        slots = centroid + self.offsets
        err = np.linalg.norm(self.pos - slots, axis=1)
        if honest_only:
            err = err[list(honest_only)]
        return err

    def formation_error(self, centroid, honest_only=None):
        return float(np.mean(self._errors(centroid, honest_only)))


# ---------------------------------------------------------------------------
# Trial driver (identical stream structure to exp2/run.py)
# ---------------------------------------------------------------------------
def run_trial(swarm_cls, seed_stream, n, ticks, comms_factory,
              byzantine=None, silent=()):
    rng = np.random.default_rng(seed_stream)
    swarm = swarm_cls(rng, n, comms_factory(),
                      byzantine=byzantine, silent=silent)
    honest = [i for i in range(n)
              if i not in (byzantine or {}) and i not in set(silent)]
    centroid = np.array([50.0, 50.0])
    drift_angle = rng.uniform(0, 2 * math.pi)
    errors, errors_honest = [], []
    for tick in range(ticks):
        drift_angle += rng.normal(0, 0.02)
        centroid += np.array([math.cos(drift_angle),
                              math.sin(drift_angle)]) * 0.35
        centroid = np.clip(centroid, 25, 75)
        swarm.step(centroid, tick)
        e = swarm.formation_error(centroid)
        errors.append(e)
        errors_honest.append(swarm.formation_error(centroid, honest_only=honest))
    errors = np.array(errors)
    return {
        "mean_error": float(errors.mean()),
        "mean_error_honest": float(np.mean(errors_honest)),
        "final_error": float(errors[-1]),
        "coherence_fraction": float((errors < COHERENCE_BOUND).mean()),
    }
