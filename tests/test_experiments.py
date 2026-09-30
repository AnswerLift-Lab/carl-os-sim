"""Smoke + property tests for the three experiments."""
import json
import os
import subprocess
import sys

EXP = os.path.join(os.path.dirname(__file__), "..", "experiments")


def run_exp(name):
    r = subprocess.run([sys.executable, os.path.join(EXP, name, "run.py")],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, f"{name} failed:\n{r.stderr[-2000:]}"
    with open(os.path.join(EXP, name, "results", "results.json")) as f:
        return json.load(f)


def test_exp1_event_driven():
    res = run_exp("exp1_event_driven")
    assert res["claim_met"] is True
    op = res["operating_point"]
    assert op["worst_missed_events"] == 0
    assert op["mean_saving"] > 0.5
    # every threshold row has the required fields
    for row in res["sweep"]:
        assert row["compute_fraction"] > 0


def test_exp2_swarm():
    res = run_exp("exp2_swarm")
    assert res["claim_met"] is True
    s = res["summary_by_dropout"]
    for p in ("0.3", "0.5", "0.7"):
        assert s[p]["mean_dec_error"] <= s[p]["mean_cen_error"]


def test_exp3_governance():
    res = run_exp("exp3_governance")
    assert res["claim_a_met"] is True
    assert res["claim_b_met"] is True
    assert res["part_a_governance_invariant"]["bypass_executed"] == 0


def test_exp2b_adversarial():
    res = run_exp("exp2b_adversarial")
    # directional claims (blackout, jammer) held
    assert res["claim_met"] is True
    s = res["summary_by_condition"]
    for c in ("blackout", "jammer"):
        assert (s[c]["mean_dec_honest_error"]
                <= s[c]["mean_cen_honest_error"])
    # exploratory conditions ran and reported damage ratios either way
    for c in ("byzantine", "silent"):
        assert s[c]["dec_damage_vs_baseline"] is not None
        assert s[c]["cen_damage_vs_baseline"] is not None


def test_exp2c_scale():
    res = run_exp("exp2c_scale")
    # NOTE: the pre-registered claim (gap non-shrinking with N) did NOT
    # hold — the gap narrows as N grows because sensor averaging helps the
    # centralized controller more. That negative result is preserved in
    # results.json ("claim_met": false). What DID hold, and what this test
    # pins as regression properties:
    s = res["summary_by_n"]
    # decentralized advantage persists at every tested scale
    for n in ("6", "12", "24", "48"):
        assert s[n]["gap"] > 0
        assert s[n]["dec_wins"] == 3
    # the observed narrowing trend (the actual finding)
    assert s["48"]["gap"] < s["6"]["gap"]
