"""Tests for QuantumOptics-Lab: distributions vs closed forms, Mandel Q
and g2 receipts, quadrature laws, the squeezing sweep, the Husimi grid,
the detector loss laws, the kNN policy, HOLD gates, and determinism."""
import math

import main


ZOO = main.zoo_by_name()


# ---------------------------------------------------------------- states
def test_fock_space_has_41_levels():
    assert len(ZOO["fock_1"]["probs"]) == 41


def test_all_states_normalised():
    for state in ZOO.values():
        assert abs(sum(state["probs"]) - 1.0) < 1e-12


def test_vacuum_has_no_statistics():
    vac = ZOO["vacuum"]
    assert vac["mean_n"] == 0.0
    assert vac["mandel_q"] is None and vac["g2"] is None
    assert abs(vac["var_x"] - 0.5) < 1e-12
    assert abs(vac["var_p"] - 0.5) < 1e-12


# ---------------------------------------------------------------- distributions
def test_coherent_distribution_is_poisson():
    lam = abs(main.COHERENT_ALPHA) ** 2
    for n in range(main.DIM):
        assert abs(ZOO["coherent"]["probs"][n]
                   - main.poisson_pmf(n, lam)) < 1e-12


def test_thermal_distribution_is_geometric():
    for n in range(main.DIM):
        assert abs(ZOO["thermal"]["probs"][n]
                   - main.thermal_pmf(n, main.THERMAL_NBAR)) < 1e-7


def test_squeezed_distribution_matches_tanh_law():
    for n in range(main.DIM):
        assert abs(ZOO["squeezed_vacuum"]["probs"][n]
                   - main.squeezed_pmf(n, main.SQUEEZED_R)) < 1e-5


def test_squeezed_odd_orders_exactly_zero():
    sqz = ZOO["squeezed_vacuum"]
    assert all(sqz["probs"][n] == 0.0 for n in range(1, main.DIM, 2))


# ---------------------------------------------------------------- statistics
def test_fock1_mandel_q_and_g2():
    f1 = ZOO["fock_1"]
    assert abs(f1["mandel_q"] + 1.0) < 1e-12
    assert f1["g2"] == 0.0


def test_fock2_g2_is_half():
    assert abs(ZOO["fock_2"]["g2"] - 0.5) < 1e-12


def test_coherent_is_the_classical_boundary():
    coh = ZOO["coherent"]
    assert abs(coh["mandel_q"]) < 1e-9
    assert abs(coh["g2"] - 1.0) < 1e-9


def test_thermal_statistics():
    the = ZOO["thermal"]
    assert abs(the["mandel_q"] - main.THERMAL_NBAR) < 1e-4
    assert abs(the["g2"] - 2.0) < 1e-4


def test_squeezed_mean_and_g2_laws():
    sqz = ZOO["squeezed_vacuum"]
    assert abs(sqz["mean_n"] - math.sinh(main.SQUEEZED_R) ** 2) < 1e-3
    assert abs(sqz["g2"] - (3.0 + 1.0 / sqz["mean_n"])) < 5e-3


def test_photon_added_coherent_is_sub_poissonian():
    spacs = ZOO["photon_added_coherent"]
    assert abs(spacs["mean_n"] - 11.0 / 3.0) < 1e-9
    assert spacs["mandel_q"] < 0.0 and spacs["g2"] < 1.0


# ---------------------------------------------------------------- quadratures
def test_fock1_quadrature_variance():
    assert abs(ZOO["fock_1"]["var_x"] - 1.5) < 1e-12
    assert abs(ZOO["fock_1"]["var_p"] - 1.5) < 1e-12


def test_squeezed_quadrature_laws():
    sqz = ZOO["squeezed_vacuum"]
    r = main.SQUEEZED_R
    assert abs(sqz["var_x"] - math.exp(-2.0 * r) / 2.0) < 1e-4
    assert abs(sqz["var_p"] - math.exp(2.0 * r) / 2.0) < 1e-3


def test_heisenberg_floor_for_whole_zoo():
    for state in ZOO.values():
        assert state["var_product"] >= 0.25 - 1e-12


def test_minimum_uncertainty_states():
    assert abs(ZOO["coherent"]["var_product"] - 0.25) < 1e-9
    assert abs(ZOO["squeezed_vacuum"]["var_product"] - 0.25) < 1e-3


# ---------------------------------------------------------------- squeezing sweep
def test_sweep_db_matches_formula_through_r1():
    for row in main.squeezing_sweep():
        if row["r"] <= 1.0:
            assert abs(row["db_computed"] - row["db_formula"]) < 0.01


def test_sweep_r15_truncation_shortfall_is_visible():
    row = {r["r"]: r for r in main.squeezing_sweep()}[1.5]
    assert row["tail_discarded"] > 1e-3
    assert 0.0 < row["db_formula"] - row["db_computed"] < 3.0


# ---------------------------------------------------------------- Husimi
def test_husimi_nonnegative_and_normalised():
    hus = main.husimi_report()
    assert hus["fock_1"]["grid_min"] >= 0.0
    assert hus["squeezed_vacuum"]["grid_min"] >= 0.0
    assert abs(hus["fock_1"]["grid_integral"] - 1.0) < 0.02
    assert abs(hus["squeezed_vacuum"]["grid_integral"] - 1.0) < 0.05


def test_husimi_single_photon_dark_centre():
    assert main.husimi_report()["fock_1"]["q_at_zero"] == 0.0


def test_husimi_squeezed_value_at_origin():
    expected = 1.0 / (math.pi * math.cosh(main.SQUEEZED_R))
    got = main.husimi_report()["squeezed_vacuum"]["q_at_zero"]
    assert abs(got - expected) < 1e-5


# ---------------------------------------------------------------- detector
def test_pure_loss_leaves_g2_invariant():
    for name in ("fock_1", "thermal", "squeezed_vacuum"):
        state = ZOO[name]
        mean, _, fact = main.distribution_moments(
            main.loss_probs(state["probs"], 0.5))
        assert abs(fact / (mean * mean) - state["g2"]) < 1e-9


def test_pure_loss_scales_mandel_q_by_eta():
    mean, var, _ = main.distribution_moments(
        main.loss_probs(ZOO["fock_1"]["probs"], 0.5))
    assert abs((var - mean) / mean + 0.5) < 1e-12


def test_dark_counts_drag_single_photon_g2_up():
    table = main.detector_report()["table"]["fock_1"]
    assert 0.0 < table[0]["g2"] < table[3]["g2"] < 1.0


def test_detector_click_probability_falls_with_eta():
    table = main.detector_report()["table"]["coherent"]
    assert table[0]["click_probability"] > table[3]["click_probability"]


# ---------------------------------------------------------------- classifier
def test_classifier_verdicts():
    rep = main.classifier_report()
    assert rep["fock_1"] == "sub-poissonian-quantum"
    assert rep["fock_2"] == "sub-poissonian-quantum"
    assert rep["coherent"] == "coherent-classical-boundary"
    assert rep["thermal"] == "super-poissonian-thermal"
    assert rep["squeezed_vacuum"] == "squeezed-nonclassical"
    assert rep["photon_added_coherent"] == "sub-poissonian-quantum"


def test_classifier_matches_policy_on_grid():
    for features, label in main.TRAINING_GRID:
        assert main.classify_state(*features) == label


def test_classifier_matches_policy_on_scenarios():
    for name, verdict in main.classifier_report().items():
        assert verdict == main.model_label(*main.state_features(ZOO[name]))


# ---------------------------------------------------------------- gates + seats
def test_hold_gates():
    assert len(main.HOLD_GATES) == 14
    assert main.gate("real_laser_control") == "HOLD"
    assert main.gate("real_detector_operation") == "HOLD"
    assert main.gate("qkd_deployment") == "HOLD"
    assert main.gate("single_photon_source_certification") == "HOLD"
    assert main.gate("run_simulation") == "PROCEED"


def test_hold_demo_exits_2():
    assert main.main(["hold-demo"]) == 2
    assert main.main(["hold-demo", "qkd_deployment"]) == 2
    assert main.main(["hold-demo", "run_simulation"]) == 0


def test_council_seats_never_override():
    brains = main.brains_report()
    assert brains["decider"]["seat"] == "Gemini Argon 4 Extended Thinking"
    assert brains["decider"]["can_override_hold"] is False
    assert brains["advisor"]["can_override_hold"] is False
    assert brains["flow"]["rendered"] is False
    assert brains["flow"]["live"] == 0


# ---------------------------------------------------------------- determinism
def test_checks_all_pass():
    checks = main.run_checks()
    assert all(ok for _, ok in checks), [n for n, ok in checks if not ok]


def test_demo_is_deterministic(capsys):
    main.demo()
    first = capsys.readouterr().out
    main.demo()
    second = capsys.readouterr().out
    assert first == second
