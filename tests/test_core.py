"""Core tests: layer contracts, loop sequencing, structural invariants."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from carlos import ControlLoop, SignalEnvironment, default_layers
from carlos.layers import (Actuation, Cognition, Environment, Governance,
                           Memory, Orchestration, Perception)
from carlos.types import GovernedAction, ProposedAction


def make_loop(**overrides):
    return ControlLoop(layers=default_layers(**overrides), threshold=0.0)


def test_layer_sequence_order():
    order = []
    class Tracer(Perception):
        def process(self, obs):
            order.append("perception")
            return super().process(obs)
    class TracerM(Memory):
        def recall(self, p):
            order.append("memory")
            return super().recall(p)
    class TracerC(Cognition):
        def decide(self, p, c):
            order.append("cognition")
            return super().decide(p, c)
    class TracerG(Governance):
        def validate(self, ps, p):
            order.append("governance")
            return super().validate(ps, p)
    class TracerO(Orchestration):
        def sequence(self, a):
            order.append("orchestration")
            return super().sequence(a)
    class TracerA(Actuation):
        def execute(self, a):
            order.append("actuation")
            return super().execute(a)
    loop = make_loop(perception=Tracer(), memory=TracerM(), cognition=TracerC(),
                     governance=TracerG(), orchestration=TracerO(),
                     actuation=TracerA())
    loop.tick(force=True)
    assert order == ["perception", "memory", "cognition", "governance",
                     "orchestration", "actuation"]


def test_threshold_gating_skips_downstream():
    loop = ControlLoop(layers=default_layers(), threshold=999.0)
    loop.tick()
    L = loop.layers
    assert L["perception"].calls == 1
    assert L["cognition"].calls == 0
    assert L["governance"].calls == 0
    assert L["actuation"].calls == 0
    assert loop.stats.skips == 1 and loop.stats.runs == 0


def test_force_runs_full_loop():
    loop = ControlLoop(layers=default_layers(), threshold=999.0)
    loop.tick(force=True)
    assert loop.stats.runs == 1
    assert loop.layers["governance"].calls == 1


def test_actuation_refuses_unstamped():
    act = Actuation()
    bad = GovernedAction(tick=0, kind="x", approved=False, stamp="")
    assert act.execute([bad]) == []
    assert act.refusals == 1
    assert act.executed == []


def test_actuation_refuses_approved_without_stamp():
    act = Actuation()
    sneaky = GovernedAction(tick=0, kind="x", approved=True, stamp="")
    assert act.execute([sneaky]) == []
    assert act.refusals == 1


def test_orchestration_drops_unstamped():
    orch = Orchestration()
    bad = GovernedAction(tick=0, kind="x", approved=True, stamp="")
    assert orch.sequence([bad]) == []


def test_governance_veto_and_clamp():
    def no_delete(p):
        if p.kind == "delete":
            return False, "forbidden", {}
        return True, "", {}
    def cap(p):
        v = p.params.get("v", 0)
        return (True, "", {"v": 10}) if v > 10 else (True, "", {})
    gov = Governance(constraints=[no_delete, cap])
    props = [ProposedAction(tick=0, kind="delete", params={}),
             ProposedAction(tick=0, kind="move", params={"v": 99})]
    out = gov.validate(props, None)
    assert out[0].approved is False and out[0].stamp == ""
    assert out[1].approved is True and out[1].params["v"] == 10
    assert gov.vetoes == 1 and gov.approvals == 1


def test_memory_persists_across_ticks():
    loop = make_loop()
    loop.run(5, force=True)
    mem = loop.layers["memory"]
    assert len(mem.percepts) == 5


def test_environment_recursion():
    # actuation effects change the next observation: the loop recurses
    seen = []
    class RecEnv(Environment):
        def __init__(self):
            super().__init__({"x": 0.0})
    def policy(percept, ctx):
        seen.append(percept.features["x"])
        return [ProposedAction(tick=percept.tick, kind="inc", params={})]
    act = Actuation(effect_fn=lambda a: {"add": {"x": 1.0}})
    loop = make_loop(environment=RecEnv(),
                     cognition=Cognition(policy=policy), actuation=act)
    loop.run(3, force=True)
    assert seen == [0.0, 1.0, 2.0]


def test_swap_layer_replaces():
    loop = make_loop()
    new = Cognition()
    old = loop.swap_layer("cognition", new)
    assert loop.layers["cognition"] is new and old is not new
    loop.tick(force=True)  # still runs


def test_swap_unknown_layer_raises():
    loop = make_loop()
    try:
        loop.swap_layer("nope", object())
    except KeyError:
        return
    raise AssertionError("expected KeyError")


def test_determinism_same_seed():
    def build():
        env = SignalEnvironment(seed=123, n_events=10)
        env.schedule_events(200)
        return ControlLoop(layers=default_layers(environment=env),
                           threshold=0.2)
    a, b = build(), build()
    a.run(200)
    b.run(200)
    assert a.stats.runs == b.stats.runs
    assert [t.percept.change for t in a.stats.traces] == \
           [t.percept.change for t in b.stats.traces]


def test_signal_environment_events_fire():
    env = SignalEnvironment(seed=1, n_events=10)
    env.schedule_events(500)
    assert len(env.event_ticks) == 10
    loop = ControlLoop(layers=default_layers(environment=env), threshold=0.0)
    loop.run(500, force=True)
    assert loop.stats.runs == 500
