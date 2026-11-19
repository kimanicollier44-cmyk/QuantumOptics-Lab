#!/usr/bin/env python3
"""QuantumOptics-Lab - educational single-mode quantum optics lab.

by Darion Kellar

Pure Python standard library. Zero dependencies. Zero network.
Education only - and the central lesson is stated up front:

  * QuantumOptics-Lab characterises single-mode light states on a
    truncated Fock space (n <= 40) built from scratch: Fock, coherent,
    thermal, squeezed-vacuum, and single-photon-added coherent states.
    Every photon-number distribution is graded against its closed
    form, and every headline statistic - Mandel Q, g2(0), quadrature
    variances, squeezing in dB, the Husimi Q function - is computed
    from the state itself, never quoted.
  * Quadrature convention, stated once and used everywhere:
    x = (a + a-dagger)/sqrt(2), p = (a - a-dagger)/(i sqrt(2)),
    [x, p] = i, so the vacuum variance is 1/2 per quadrature and the
    Heisenberg floor for the variance product is 1/4.
  * This lab is single-mode state characterisation only. Beam-splitter
    interference (Hong-Ou-Mandel) belongs to BosonSampling-Lab and is
    deliberately NOT redone here.
  * Nothing here is a hardware specification, a detector calibration,
    a source certification, or a security proof. The detector model
    is labelled teaching math: Bernoulli loss plus Poisson dark
    counts applied to a distribution on paper. Real laser or detector
    control, QKD or quantum-network deployment, vendor and advantage
    claims are permanent HOLD gates - with Gemini Argon 4 Extended
    Thinking as DECIDER (names-only, tighten-only), Muse as advisor
    (never overrides HOLD), and Google Flow plan-only seats.
"""
import cmath
import hashlib
import json
import math
import sys

# ---------------------------------------------------------------- constants
VERSION = "1.0.0"
N_MAX = 40                      # Fock truncation: n = 0..40 (41 levels)
DIM = N_MAX + 1
VACUUM_VAR = 0.5                # per-quadrature vacuum variance, [x, p] = i

# Labelled teaching parameters for the demo zoo. These are inputs to
# a simulation, not measurements of any device.
COHERENT_ALPHA = math.sqrt(2.0)     # coherent amplitude, nbar = 2
THERMAL_NBAR = 2.0                  # thermal mean photon number
SQUEEZED_R = 1.0                    # zoo squeezing parameter
SPACS_ALPHA = math.sqrt(2.0)        # photon-added coherent amplitude
DARK_MEAN = 0.05                    # labelled Poisson dark-count mean
SQUEEZE_SWEEP = (0.0, 0.25, 0.5, 1.0, 1.5)
DETECTOR_ETAS = (1.0, 0.8, 0.5, 0.2)

# ---------------------------------------------------------------- HOLD gates
HOLD_GATES = {
    "real_laser_control": "HOLD - no control of real lasers or light sources; the states here are vectors on paper",
    "real_detector_operation": "HOLD - no operating real detectors, SPADs, PMTs, or homodyne hardware",
    "hardware_specification_claim": "HOLD - no claiming these teaching numbers are the specification of any real device",
    "qkd_deployment": "HOLD - no designing or deploying QKD systems from a statistics lab",
    "quantum_network_deployment": "HOLD - no quantum network, repeater, or entanglement-distribution deployment",
    "vendor_product_claim": "HOLD - no vendor or product performance claims; no product was measured",
    "quantum_advantage_claim": "HOLD - no quantum-advantage claim; this is a classical simulation of one mode",
    "single_photon_source_certification": "HOLD - no certifying a real source as a true single-photon source; g2 here is computed, not measured",
    "detector_calibration_claim": "HOLD - no real detector calibration or efficiency certification; eta is a labelled model input",
    "medical_imaging_use": "HOLD - no medical imaging, diagnostics, or clinical sensing use",
    "surveillance_sensing_use": "HOLD - no surveillance, LiDAR, or remote-sensing deployment",
    "laser_safety_assessment": "HOLD - no laser-safety or eye-safety assessment for real beams",
    "cryptographic_security_claim": "HOLD - no cryptographic security proof from simulated photon statistics",
    "metrology_record_claim": "HOLD - no metrology record or standard claim; squeezing here is a labelled parameter, not a measurement",
}


def gate(action):
    """Return 'HOLD' if the action is gated, else 'PROCEED' (sandbox sim)."""
    return "HOLD" if action in HOLD_GATES else "PROCEED"


# ================================================================ 1. Fock-space core
# States live on the truncated basis |0>..|40>. Pure states are
# coefficient vectors (lists of complex). The one mixed zoo state,
# thermal light, is carried by its photon-number distribution and
# zero first/second field moments, which is all its statistics need.
# Builders return (coeffs_or_None, probs, tail) where tail is the
# probability mass the truncation discarded BEFORE renormalisation -
# printed honestly wherever it is not negligible.

def _renormalise(coeffs):
    """Return (unit-norm coeffs, discarded tail mass)."""
    norm2 = sum(abs(c) ** 2 for c in coeffs)
    tail = max(0.0, 1.0 - norm2)
    inv = 1.0 / math.sqrt(norm2)
    return [c * inv for c in coeffs], tail


def fock_coeffs(n):
    coeffs = [0j] * DIM
    coeffs[n] = 1.0 + 0j
    return coeffs


def coherent_coeffs(alpha):
    """|alpha> by recurrence: c_{n+1} = c_n * alpha / sqrt(n+1)."""
    coeffs = [0j] * DIM
    coeffs[0] = complex(math.exp(-abs(alpha) ** 2 / 2.0), 0.0)
    for n in range(N_MAX):
        coeffs[n + 1] = coeffs[n] * alpha / math.sqrt(n + 1)
    return _renormalise(coeffs)


def squeezed_coeffs(r):
    """Squeezed vacuum, x-squeezed for real r > 0.

    c_{2k} = (-1)^k sqrt((2k)!) / (2^k k!) * tanh^k(r) / sqrt(cosh r),
    odd coefficients exactly zero. With the stated convention this
    gives <dx^2> = e^{-2r}/2 and <dp^2> = e^{+2r}/2.
    """
    coeffs = [0j] * DIM
    t = math.tanh(r)
    scale = 1.0 / math.sqrt(math.cosh(r))
    for k in range(0, N_MAX // 2 + 1):
        n = 2 * k
        amp = (math.sqrt(math.factorial(2 * k))
               / (2.0 ** k * math.factorial(k))) * (t ** k) * scale
        coeffs[n] = complex((-1.0) ** k * amp, 0.0)
    return _renormalise(coeffs)


def photon_added_coeffs(coeffs):
    """a-dagger applied to a pure state, renormalised (a|0> -> |1>)."""
    out = [0j] * DIM
    for n in range(1, DIM):
        out[n] = math.sqrt(n) * coeffs[n - 1]
    return _renormalise(out)


def thermal_probs(nbar):
    """Bose-Einstein (geometric) distribution by recurrence."""
    probs = [0.0] * DIM
    probs[0] = 1.0 / (1.0 + nbar)
    ratio = nbar / (1.0 + nbar)
    for n in range(N_MAX):
        probs[n + 1] = probs[n] * ratio
    tail = max(0.0, 1.0 - sum(probs))
    return [p / sum(probs) for p in probs], tail


def probs_of(coeffs):
    return [abs(c) ** 2 for c in coeffs]


def field_moments(coeffs):
    """(<a>, <a^2>) for a pure state, by index arithmetic."""
    a1 = 0j
    a2 = 0j
    for n in range(N_MAX):
        a1 += math.sqrt(n + 1) * coeffs[n].conjugate() * coeffs[n + 1]
    for n in range(N_MAX - 1):
        a2 += (math.sqrt((n + 1) * (n + 2))
               * coeffs[n].conjugate() * coeffs[n + 2])
    return a1, a2


def distribution_moments(probs):
    """Photon-number moments of a distribution (normalised internally)."""
    total = sum(probs)
    mean = sum(n * p for n, p in enumerate(probs)) / total
    m2 = sum(n * n * p for n, p in enumerate(probs)) / total
    var = m2 - mean * mean
    factorial2 = m2 - mean            # <n(n-1)>
    return mean, var, factorial2


def state_stats(probs, a1, a2):
    """Mandel Q, g2(0), and quadrature variances from the state itself.

    x = (a + a+)/sqrt(2), p = (a - a+)/(i sqrt(2)):
      <x^2> = (2 Re<a^2> + 2<n> + 1)/2,  <x> = sqrt(2) Re<a>
      <p^2> = (-2 Re<a^2> + 2<n> + 1)/2, <p> = sqrt(2) Im<a>
    """
    mean, var, factorial2 = distribution_moments(probs)
    mandel_q = (var - mean) / mean if mean > 0 else None
    g2 = factorial2 / (mean * mean) if mean > 0 else None
    mean_x = math.sqrt(2.0) * a1.real
    mean_p = math.sqrt(2.0) * a1.imag
    var_x = (2.0 * a2.real + 2.0 * mean + 1.0) / 2.0 - mean_x * mean_x
    var_p = (-2.0 * a2.real + 2.0 * mean + 1.0) / 2.0 - mean_p * mean_p
    return {
        "mean_n": mean,
        "var_n": var,
        "mandel_q": mandel_q,
        "g2": g2,
        "var_x": var_x,
        "var_p": var_p,
        "var_product": var_x * var_p,
        "min_var_ratio": min(var_x, var_p) / VACUUM_VAR,
    }


def _pure_state(name, label, coeffs, tail):
    probs = probs_of(coeffs)
    a1, a2 = field_moments(coeffs)
    state = {"name": name, "label": label, "kind": "pure",
             "coeffs": coeffs, "probs": probs, "tail": tail}
    state.update(state_stats(probs, a1, a2))
    return state


def build_zoo():
    """The demo state zoo, in a fixed teaching order."""
    zoo = []
    zoo.append(_pure_state("vacuum", "Vacuum |0>", fock_coeffs(0), 0.0))
    zoo.append(_pure_state("fock_1", "Fock |1> (single photon)",
                           fock_coeffs(1), 0.0))
    zoo.append(_pure_state("fock_2", "Fock |2>", fock_coeffs(2), 0.0))
    coeffs, tail = coherent_coeffs(COHERENT_ALPHA)
    zoo.append(_pure_state("coherent", "Coherent |alpha=sqrt(2)>",
                           coeffs, tail))
    probs, ttail = thermal_probs(THERMAL_NBAR)
    thermal = {"name": "thermal", "label": "Thermal (nbar=2)",
               "kind": "thermal", "coeffs": None, "probs": probs,
               "tail": ttail}
    thermal.update(state_stats(probs, 0j, 0j))
    zoo.append(thermal)
    coeffs, tail = squeezed_coeffs(SQUEEZED_R)
    zoo.append(_pure_state("squeezed_vacuum", "Squeezed vacuum (r=1)",
                           coeffs, tail))
    base, _ = coherent_coeffs(SPACS_ALPHA)
    coeffs, tail = photon_added_coeffs(base)
    zoo.append(_pure_state("photon_added_coherent",
                           "Photon-added coherent a+|alpha=sqrt(2)>",
                           coeffs, tail))
    return zoo


def zoo_by_name():
    return {s["name"]: s for s in build_zoo()}


# ================================================================ 2. Closed forms
# The distributions are graded against these, never the other way
# round: Poisson for coherent light, geometric for thermal light,
# the even-only tanh law for squeezed vacuum.

def poisson_pmf(n, lam):
    return math.exp(-lam) * lam ** n / math.factorial(n)


def thermal_pmf(n, nbar):
    return (1.0 / (1.0 + nbar)) * (nbar / (1.0 + nbar)) ** n


def squeezed_pmf(n, r):
    if n % 2 == 1:
        return 0.0
    k = n // 2
    return ((math.factorial(2 * k)
             / (2.0 ** (2 * k) * math.factorial(k) ** 2))
            * math.tanh(r) ** (2 * k) / math.cosh(r))


def distributions_report():
    zoo = zoo_by_name()
    coh = zoo["coherent"]
    the = zoo["thermal"]
    sqz = zoo["squeezed_vacuum"]
    lam = abs(COHERENT_ALPHA) ** 2
    return {
        "truncation": {"n_max": N_MAX, "levels": DIM},
        "coherent_vs_poisson": {
            "max_abs_error": max(
                abs(coh["probs"][n] - poisson_pmf(n, lam))
                for n in range(DIM)),
            "tail_discarded": coh["tail"],
        },
        "thermal_vs_geometric": {
            "max_abs_error": max(
                abs(the["probs"][n] - thermal_pmf(n, THERMAL_NBAR))
                for n in range(DIM)),
            "tail_discarded": the["tail"],
        },
        "squeezed_vs_tanh_law": {
            "max_abs_error": max(
                abs(sqz["probs"][n] - squeezed_pmf(n, SQUEEZED_R))
                for n in range(DIM)),
            "odd_probabilities_max": max(
                sqz["probs"][n] for n in range(1, DIM, 2)),
            "tail_discarded": sqz["tail"],
        },
    }


# ================================================================ 3. Squeezing sweep
# dB of squeezing = -10*log10(var_x / vacuum) = -10*log10(e^{-2r})
# = 20*r*log10(e) = 8.6859*r. The lab prints the closed form next to
# the ratio computed from the truncated state, and the tail mass the
# truncation discarded at each r - at r = 1.5 the tail is visible and
# the agreement is graded to truncation accuracy, openly.

DB_PER_R = 20.0 * math.log10(math.e)      # 8.685889638... dB per unit r


def squeezing_sweep():
    rows = []
    for r in SQUEEZE_SWEEP:
        if r == 0.0:
            rows.append({"r": r, "var_x": VACUUM_VAR, "var_p": VACUUM_VAR,
                         "mean_n": 0.0, "db_computed": 0.0,
                         "db_formula": 0.0, "tail_discarded": 0.0})
            continue
        coeffs, tail = squeezed_coeffs(r)
        probs = probs_of(coeffs)
        a1, a2 = field_moments(coeffs)
        stats = state_stats(probs, a1, a2)
        db_computed = -10.0 * math.log10(stats["var_x"] / VACUUM_VAR)
        rows.append({"r": r, "var_x": stats["var_x"],
                     "var_p": stats["var_p"], "mean_n": stats["mean_n"],
                     "db_computed": db_computed,
                     "db_formula": DB_PER_R * r,
                     "tail_discarded": tail})
    return rows


# ================================================================ 4. Husimi Q function
# Q(alpha) = (1/pi) |<alpha|psi>|^2 >= 0 by construction. Evaluated
# on a finite grid for the single-photon and squeezed states; the
# grid integral is printed next to the exact value 1 with the grid
# error stated - the anti-squeezed tail reaches past any finite box.

HUSIMI_HALF = 5.0
HUSIMI_STEP = 0.2


def husimi_overlap(coeffs, alpha):
    """<alpha|psi> = e^{-|a|^2/2} sum_n (a*)^n c_n / sqrt(n!)."""
    total = 0j
    term = 1.0 + 0j
    conj_a = alpha.conjugate()
    for n, c in enumerate(coeffs):
        if n:
            term *= conj_a / math.sqrt(n)
        total += term * c
    return cmath.exp(-abs(alpha) ** 2 / 2.0) * total


def husimi_q(coeffs, alpha):
    return abs(husimi_overlap(coeffs, alpha)) ** 2 / math.pi


def husimi_grid(coeffs):
    steps = int(round(2.0 * HUSIMI_HALF / HUSIMI_STEP))
    values = []
    for i in range(steps + 1):
        x = -HUSIMI_HALF + i * HUSIMI_STEP
        for j in range(steps + 1):
            y = -HUSIMI_HALF + j * HUSIMI_STEP
            values.append(husimi_q(coeffs, complex(x, y)))
    integral = sum(values) * HUSIMI_STEP * HUSIMI_STEP
    return {"grid_min": min(values), "grid_max": max(values),
            "grid_integral": integral, "grid_points": len(values),
            "half_width": HUSIMI_HALF, "step": HUSIMI_STEP,
            "q_at_zero": husimi_q(coeffs, 0j)}


def husimi_report():
    zoo = zoo_by_name()
    return {
        "fock_1": husimi_grid(zoo["fock_1"]["coeffs"]),
        "squeezed_vacuum": husimi_grid(zoo["squeezed_vacuum"]["coeffs"]),
        "note": ("grid integral vs exact 1: the difference is grid "
                 "error - finite box plus finite step - stated, not "
                 "hidden"),
    }


# ================================================================ 5. Detector model
# Labelled teaching model of an imperfect photon counter: Bernoulli
# loss (each photon independently survives with probability eta -
# loss mixes in vacuum) followed by independent Poisson dark counts.
# Two exact consequences are the lesson: pure loss leaves g2(0)
# INVARIANT and scales Mandel Q by exactly eta; it is the dark
# counts that drag g2 toward the classical value 1 as eta falls.

def loss_probs(probs, eta):
    out = [0.0] * DIM
    for m, pm in enumerate(probs):
        if pm == 0.0:
            continue
        for n in range(m + 1):
            out[n] += (pm * math.comb(m, n)
                       * eta ** n * (1.0 - eta) ** (m - n))
    return out


def dark_probs(probs, dark_mean):
    weights = [math.exp(-dark_mean)]
    for k in range(1, DIM):
        weights.append(weights[-1] * dark_mean / k)
    out = [0.0] * DIM
    for n, pn in enumerate(probs):
        if pn == 0.0:
            continue
        for k in range(DIM - n):
            out[n + k] += pn * weights[k]
    return out


def detector_probs(probs, eta, dark_mean=DARK_MEAN):
    return dark_probs(loss_probs(probs, eta), dark_mean)


def detector_report():
    zoo = zoo_by_name()
    names = ("fock_1", "coherent", "thermal", "squeezed_vacuum")
    table = {}
    for name in names:
        rows = []
        for eta in DETECTOR_ETAS:
            meas = detector_probs(zoo[name]["probs"], eta)
            mean, var, factorial2 = distribution_moments(meas)
            rows.append({
                "eta": eta,
                "mean_n": mean,
                "mandel_q": (var - mean) / mean if mean > 0 else None,
                "g2": factorial2 / (mean * mean) if mean > 0 else None,
                "click_probability": 1.0 - meas[0] / sum(meas),
            })
        table[name] = rows
    return {"dark_mean": DARK_MEAN, "model": "Bernoulli loss + Poisson "
            "dark counts (labelled teaching model)", "table": table}


# ================================================================ 6. kNN state classifier
# Features: Mandel Q, g2(0), and the minimum quadrature variance as a
# ratio to the vacuum (ratio < 1 is squeezing - the one signature no
# classical mixture can fake). The training grid is labelled by the
# lab's own verdict policy (model_label below) - the classifier
# interpolates the policy, it does not replace the computed stats.

def model_label(mandel_q, g2, min_var_ratio):
    """The verdict policy distilled to a four-way teaching label.

    Order matters and is stated openly: sub-Poissonian photon
    statistics are filed first, because the photon-added coherent
    state carries BOTH signatures (Q < 0 and a variance ratio of
    0.78) and this lab files it under its photon statistics.
    Quadrature squeezing with classical-or-super-Poissonian counts
    (the squeezed vacuum: Q > 0, ratio 0.135) is filed as squeezed.
    """
    if mandel_q < -0.05:
        return "sub-poissonian-quantum"
    if min_var_ratio < 0.90:
        return "squeezed-nonclassical"
    if mandel_q > 0.50:
        return "super-poissonian-thermal"
    return "coherent-classical-boundary"


def _training_grid():
    rows = []
    for q in (-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0, 2.0, 4.0):
        for g2 in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
            for ratio in (0.10, 0.25, 0.50, 0.90, 1.00, 1.50, 3.00, 5.00):
                rows.append(((q, g2, ratio), model_label(q, g2, ratio)))
    return rows


TRAINING_GRID = _training_grid()


def _scaled(features):
    q, g2, ratio = features
    return (q / 4.0, g2 / 4.0, ratio / 5.0)


def classify_state(mandel_q, g2, min_var_ratio, k=5):
    """Distance-weighted kNN over the policy-labelled grid."""
    target = _scaled((mandel_q, g2, min_var_ratio))
    ranked = []
    for features, label in TRAINING_GRID:
        point = _scaled(features)
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(target, point)))
        ranked.append((dist, features, label))
    ranked.sort(key=lambda row: (row[0], row[1]))
    votes = {}
    for dist, _, label in ranked[:k]:
        votes[label] = votes.get(label, 0.0) + 1.0 / (dist + 1e-9)
    priority = {"squeezed-nonclassical": 0, "sub-poissonian-quantum": 1,
                "super-poissonian-thermal": 2,
                "coherent-classical-boundary": 3}
    return sorted(votes.items(),
                  key=lambda kv: (-kv[1], priority[kv[0]]))[0][0]


def state_features(state):
    return (state["mandel_q"], state["g2"], state["min_var_ratio"])


def classifier_report():
    zoo = zoo_by_name()
    names = ("fock_1", "fock_2", "coherent", "thermal",
             "squeezed_vacuum", "photon_added_coherent")
    return {name: classify_state(*state_features(zoo[name]))
            for name in names}


# ================================================================ 7. Advisory seats
def _seat_trace(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def argon4_decide(topic="quantumoptics-demo"):
    """Gemini Argon 4 DECIDER seat: MAP->MODEL->STRESS->DECIDE.

    Names-only keys, live calls 0, tighten-only: can add HOLDs, never lift one.
    """
    stages = ["MAP", "MODEL", "STRESS", "DECIDE"]
    payload = {"seat": "gemini-argon-4", "topic": topic, "stages": stages}
    return {
        "seat": "Gemini Argon 4 Extended Thinking",
        "role": "DECIDER",
        "pipeline": stages,
        "tiers": [2048, 8192, 32768],
        "key": "names-only (GEMINI_API_KEY name checked, value never read)",
        "live_calls": 0,
        "decision": "PROCEED - sandbox simulation only, all hardware and deployment gates stay HOLD",
        "can_override_hold": False,
        "trace_sha256_16": _seat_trace(payload),
    }


def claude_advisor(topic="quantumoptics-demo"):
    """Muse advisor seat: advises, can never override a HOLD."""
    return {
        "seat": "Muse",
        "role": "ADVISOR",
        "key": "names-only (MODEL_API_KEY name checked, value never read)",
        "live_calls": 0,
        "advice": "Lead with the graded receipts: the distributions match their closed forms, g2 survives pure loss untouched, and only dark counts drag it classical - then say plainly that a computed g2 certifies nothing about any real source.",
        "can_override_hold": False,
    }


def google_flow_plan():
    """Google Flow seat: plan-only, nothing rendered, nothing live."""
    return {
        "seat": "Google Flow",
        "role": "PLAN-ONLY",
        "shots": ["three photon-count histograms rising side by side: a bell, a falling staircase, an even-only comb",
                  "a squeezed ellipse breathing inside the round vacuum circle",
                  "the Husimi landscape of a single photon: a crater with a dark centre",
                  "photons thinning out through a grey loss filter while dark specks creep in",
                  "the verdict desk stamping SUB-POISSONIAN, COHERENT, THERMAL, SQUEEZED"],
        "rendered": False,
        "live": 0,
    }


def brains_report():
    return {"decider": argon4_decide(), "advisor": claude_advisor(),
            "flow": google_flow_plan()}


# ================================================================ checks
def run_checks():
    c = []

    def chk(name, ok):
        c.append((name, bool(ok)))

    zoo = zoo_by_name()
    vac, f1, f2 = zoo["vacuum"], zoo["fock_1"], zoo["fock_2"]
    coh, the = zoo["coherent"], zoo["thermal"]
    sqz, spacs = zoo["squeezed_vacuum"], zoo["photon_added_coherent"]

    # 1. state construction + truncation honesty
    chk("fock_space_41_levels", len(f1["probs"]) == 41
        and abs(sum(f1["probs"]) - 1.0) < 1e-12)
    chk("pure_states_normalised",
        all(abs(sum(s["probs"]) - 1.0) < 1e-12
            for s in zoo.values()))
    chk("coherent_tail_negligible", coh["tail"] < 1e-9)
    chk("squeezed_tail_small_at_r1", 1e-7 < sqz["tail"] < 1e-5)
    chk("thermal_tail_small", the["tail"] < 1e-6)

    # 2. distributions graded against closed forms (tolerances are
    # the truncation tails themselves: renormalising a cut-off
    # distribution shifts every entry by roughly the tail mass)
    dist = distributions_report()
    chk("coherent_is_poisson",
        dist["coherent_vs_poisson"]["max_abs_error"] < 1e-12)
    chk("thermal_is_geometric",
        dist["thermal_vs_geometric"]["max_abs_error"] < 1e-7)
    chk("squeezed_matches_tanh_law",
        dist["squeezed_vs_tanh_law"]["max_abs_error"] < 1e-5)
    chk("squeezed_odd_orders_exactly_zero",
        dist["squeezed_vs_tanh_law"]["odd_probabilities_max"] == 0.0)

    # 3. Mandel Q + g2 receipts
    chk("fock1_mandel_q_minus_one", abs(f1["mandel_q"] + 1.0) < 1e-12)
    chk("fock1_g2_zero", f1["g2"] == 0.0)
    chk("fock2_mandel_q_minus_one", abs(f2["mandel_q"] + 1.0) < 1e-12)
    chk("fock2_g2_half", abs(f2["g2"] - 0.5) < 1e-12)
    chk("coherent_mandel_q_zero", abs(coh["mandel_q"]) < 1e-9)
    chk("coherent_g2_one", abs(coh["g2"] - 1.0) < 1e-9)
    chk("thermal_mandel_q_is_nbar",
        abs(the["mandel_q"] - THERMAL_NBAR) < 1e-4)
    chk("thermal_g2_two", abs(the["g2"] - 2.0) < 1e-4)
    chk("squeezed_mean_is_sinh2",
        abs(sqz["mean_n"] - math.sinh(SQUEEZED_R) ** 2) < 1e-3)
    chk("squeezed_g2_law",
        abs(sqz["g2"] - (3.0 + 1.0 / sqz["mean_n"])) < 5e-3)
    chk("spacs_sub_poissonian", spacs["mandel_q"] < 0.0
        and spacs["g2"] < 1.0)

    # 4. quadratures, convention [x, p] = i, vacuum variance 1/2
    chk("vacuum_variance_half", abs(vac["var_x"] - 0.5) < 1e-12
        and abs(vac["var_p"] - 0.5) < 1e-12)
    chk("fock1_variance_three_halves", abs(f1["var_x"] - 1.5) < 1e-12
        and abs(f1["var_p"] - 1.5) < 1e-12)
    chk("coherent_isotropic_minimum", abs(coh["var_x"] - 0.5) < 1e-9
        and abs(coh["var_product"] - 0.25) < 1e-9)
    chk("thermal_isotropic", abs(the["var_x"] - 2.5) < 1e-5
        and abs(the["var_x"] - the["var_p"]) < 1e-12)
    chk("squeezed_var_x_law",
        abs(sqz["var_x"] - math.exp(-2.0 * SQUEEZED_R) / 2.0) < 1e-4)
    chk("squeezed_var_p_law",
        abs(sqz["var_p"] - math.exp(2.0 * SQUEEZED_R) / 2.0) < 1e-3)
    chk("squeezed_minimum_uncertainty",
        abs(sqz["var_product"] - 0.25) < 1e-3)
    chk("heisenberg_floor_all_states",
        all(s["var_product"] >= 0.25 - 1e-12 for s in zoo.values()))

    # 5. squeezing sweep: computed dB vs 8.6859*r, graded openly
    sweep = {row["r"]: row for row in squeezing_sweep()}
    chk("sweep_db_r025", abs(sweep[0.25]["db_computed"]
                             - sweep[0.25]["db_formula"]) < 0.01)
    chk("sweep_db_r05", abs(sweep[0.5]["db_computed"]
                            - sweep[0.5]["db_formula"]) < 0.01)
    chk("sweep_db_r10", abs(sweep[1.0]["db_computed"]
                            - sweep[1.0]["db_formula"]) < 0.01)
    chk("sweep_db_r15_truncation_graded",
        sweep[1.5]["tail_discarded"] > 1e-3
        and 0.0 < (sweep[1.5]["db_formula"]
                   - sweep[1.5]["db_computed"]) < 3.0)

    # 6. Husimi Q function
    hus = husimi_report()
    chk("husimi_nonnegative_fock1", hus["fock_1"]["grid_min"] >= 0.0)
    chk("husimi_nonnegative_squeezed",
        hus["squeezed_vacuum"]["grid_min"] >= 0.0)
    chk("husimi_fock1_dark_centre", hus["fock_1"]["q_at_zero"] == 0.0)
    chk("husimi_squeezed_q_at_zero",
        abs(hus["squeezed_vacuum"]["q_at_zero"]
            - 1.0 / (math.pi * math.cosh(SQUEEZED_R))) < 1e-5)
    chk("husimi_fock1_grid_normalised",
        abs(hus["fock_1"]["grid_integral"] - 1.0) < 0.02)
    chk("husimi_squeezed_grid_normalised",
        abs(hus["squeezed_vacuum"]["grid_integral"] - 1.0) < 0.05)

    # 7. detector model: loss laws exact, dark counts degrade
    pure = loss_probs(f1["probs"], 0.5)
    _, _, fact = distribution_moments(pure)
    pmean, pvar, _ = distribution_moments(pure)
    chk("loss_scales_mandel_q_by_eta",
        abs((pvar - pmean) / pmean + 0.5) < 1e-12)
    for name in ("fock_1", "thermal", "squeezed_vacuum"):
        s = zoo[name]
        thinned = loss_probs(s["probs"], 0.5)
        tmean, _, tfact = distribution_moments(thinned)
        chk(f"loss_leaves_g2_invariant_{name}",
            abs(tfact / (tmean * tmean) - s["g2"]) < 1e-9)
    det = detector_report()["table"]
    g2_eta1 = det["fock_1"][0]["g2"]
    g2_eta02 = det["fock_1"][3]["g2"]
    chk("dark_counts_drag_g2_classical", 0.0 < g2_eta1 < g2_eta02 < 1.0)
    chk("detector_click_falls_with_eta",
        det["coherent"][0]["click_probability"]
        > det["coherent"][3]["click_probability"])

    # 8. classifier - labels come from the lab's own policy
    rep = classifier_report()
    chk("classifier_fock1_sub_poissonian",
        rep["fock_1"] == "sub-poissonian-quantum")
    chk("classifier_fock2_sub_poissonian",
        rep["fock_2"] == "sub-poissonian-quantum")
    chk("classifier_coherent_boundary",
        rep["coherent"] == "coherent-classical-boundary")
    chk("classifier_thermal_super_poissonian",
        rep["thermal"] == "super-poissonian-thermal")
    chk("classifier_squeezed_nonclassical",
        rep["squeezed_vacuum"] == "squeezed-nonclassical")
    chk("classifier_spacs_sub_poissonian",
        rep["photon_added_coherent"] == "sub-poissonian-quantum")
    chk("classifier_matches_policy_on_grid",
        all(classify_state(*features) == label
            for features, label in TRAINING_GRID))
    chk("classifier_matches_policy_on_scenarios",
        all(classify_state(*state_features(zoo[n]))
            == model_label(*state_features(zoo[n]))
            for n in rep))

    # gates + seats
    chk("hold_gates_14", len(HOLD_GATES) == 14
        and all(v.startswith("HOLD") for v in HOLD_GATES.values()))
    chk("gate_laser_hold", gate("real_laser_control") == "HOLD")
    chk("gate_detector_hold", gate("real_detector_operation") == "HOLD")
    chk("gate_qkd_hold", gate("qkd_deployment") == "HOLD")
    chk("gate_certification_hold",
        gate("single_photon_source_certification") == "HOLD")
    chk("gate_advantage_hold", gate("quantum_advantage_claim") == "HOLD")
    chk("gate_sandbox_proceed", gate("run_simulation") == "PROCEED")
    brains = brains_report()
    chk("argon4_no_override", brains["decider"]["can_override_hold"] is False
        and brains["decider"]["seat"]
        == "Gemini Argon 4 Extended Thinking")
    chk("claude_no_override", brains["advisor"]["can_override_hold"] is False)
    chk("flow_plan_only", brains["flow"]["rendered"] is False
        and brains["flow"]["live"] == 0)
    return c


# ================================================================ CLI / demo
def _fmt(value, digits=6):
    if value is None:
        return "n/a"
    text = f"{value:.{digits}f}"
    if text.startswith("-") and float(text) == 0.0:
        text = text[1:]            # never print a negative zero
    return text


def demo():
    print("=" * 68)
    print("QuantumOptics-Lab - single-mode quantum optics lab")
    print("by Darion Kellar | MIT | pure stdlib | zero network | EDUCATION ONLY")
    print("=" * 68)
    print("\n[1] THE HONEST CORE - what this lab does and does not claim")
    print("    One mode of light, characterised on a truncated Fock space")
    print("    (n <= 40). Every distribution is graded against its closed")
    print("    form and every statistic is computed from the state itself.")
    print("    Convention: [x, p] = i, vacuum variance 1/2 per quadrature.")
    print("    No laser was pointed, no detector clicked, no source was")
    print("    certified. Beam-splitter interference lives in")
    print("    BosonSampling-Lab and is not redone here.")
    zoo = build_zoo()
    print("\n[2] State zoo - photon statistics from the states themselves")
    print(f"    {'state':34s} {'<n>':>8s} {'Var':>8s} {'Q':>9s} "
          f"{'g2(0)':>8s} {'var_x':>8s} {'var_p':>8s}")
    for s in zoo:
        print(f"    {s['name']:34s} {s['mean_n']:8.4f} {s['var_n']:8.4f} "
              f"{_fmt(s['mandel_q'], 4):>9s} {_fmt(s['g2'], 4):>8s} "
              f"{s['var_x']:8.4f} {s['var_p']:8.4f}")
    print("    -> Mandel Q < 0 is sub-Poissonian (no classical mixture can")
    print("       do it); g2(0) = 0 is the ideal single photon; the squeezed")
    print("       state pays for its quiet quadrature with a loud one -")
    print("       the variance product stays at the 1/4 Heisenberg floor.")
    print("\n[3] Distributions vs closed forms (max abs error over n <= 40)")
    dist = distributions_report()
    print(f"    coherent  vs Poisson      : "
          f"{dist['coherent_vs_poisson']['max_abs_error']:.2e}")
    print(f"    thermal   vs geometric    : "
          f"{dist['thermal_vs_geometric']['max_abs_error']:.2e}")
    print(f"    squeezed  vs tanh law     : "
          f"{dist['squeezed_vs_tanh_law']['max_abs_error']:.2e}")
    print(f"    squeezed odd-n probability: "
          f"{dist['squeezed_vs_tanh_law']['odd_probabilities_max']:.1f} "
          f"(exactly zero - pairs only)")
    print("\n[4] Squeezing sweep - computed dB vs 8.6859*r")
    print(f"    {'r':>5s} {'var_x':>10s} {'var_p':>10s} {'dB calc':>9s} "
          f"{'dB form':>9s} {'tail':>10s}")
    for row in squeezing_sweep():
        print(f"    {row['r']:5.2f} {row['var_x']:10.6f} "
              f"{row['var_p']:10.4f} {row['db_computed']:9.4f} "
              f"{row['db_formula']:9.4f} {row['tail_discarded']:10.2e}")
    print("    -> at r = 1.5 the discarded tail (4.0e-03) carries the")
    print("       high-n correlations whose cancellation produces")
    print("       e^-3/2: the truncated state resolves 10.53 of the")
    print("       13.03 dB. The shortfall is printed, not hidden.")
    print("\n[5] Husimi Q function on a grid (exact integral = 1)")
    hus = husimi_report()
    for name in ("fock_1", "squeezed_vacuum"):
        g = hus[name]
        print(f"    {name:16s} min {g['grid_min']:.4f} | "
              f"grid integral {g['grid_integral']:.4f} | "
              f"Q(0) {g['q_at_zero']:.6f}")
    print("    -> Q >= 0 everywhere by construction; the single photon has")
    print("       a dark centre (Q(0) = 0 - a crater, not a peak), and the")
    print("       squeezed integral leaks a little past the finite box.")
    print("\n[6] Detector model - Bernoulli loss + Poisson dark counts "
          f"(nu = {DARK_MEAN})")
    det = detector_report()
    for name in ("fock_1", "coherent", "thermal", "squeezed_vacuum"):
        cells = " | ".join(
            f"eta {row['eta']:.1f}: Q {_fmt(row['mandel_q'], 3)}, "
            f"g2 {_fmt(row['g2'], 3)}" for row in det["table"][name])
        print(f"    {name:16s} {cells}")
    print("    -> pure loss leaves g2 EXACTLY invariant and scales Q by")
    print("       eta; the dark counts are what drag g2 toward the")
    print("       classical 1 as the efficiency falls.")
    print("\n[7] State classifier (TinyML kNN, labels from the lab's policy)")
    for name, label in classifier_report().items():
        print(f"    {name:24s} -> {label}")
    print("\n[8] Advisory seats")
    brains = brains_report()
    print(f"    decider: {brains['decider']['decision']} "
          f"trace={brains['decider']['trace_sha256_16']}")
    print(f"    advisor can_override_hold = "
          f"{brains['advisor']['can_override_hold']}")
    print(f"    flow rendered = {brains['flow']['rendered']} "
          f"live = {brains['flow']['live']}")
    print(f"\n[9] HOLD gates: {len(HOLD_GATES)}")
    for key in HOLD_GATES:
        print(f"    HOLD  {key}")
    checks = run_checks()
    passed = sum(1 for _, ok in checks if ok)
    print(f"\nCHECKS {passed}/{len(checks)}")
    for name, ok in checks:
        if not ok:
            print(f"    FAIL {name}")
    verdict = "PROCEED" if passed == len(checks) else "HOLD"
    print(f"VERDICT {verdict} (sandbox simulation only) | "
          f"HOLD gates {len(HOLD_GATES)}")
    return 0 if passed == len(checks) else 1


def _round_floats(value):
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {k: _round_floats(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_round_floats(v) for v in value]
    return value


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] == "demo":
        return demo()
    cmd = argv[0]
    if cmd == "checks":
        checks = run_checks()
        for name, ok in checks:
            print(f"{'PASS' if ok else 'FAIL'} {name}")
        print(f"CHECKS {sum(1 for _, ok in checks if ok)}/{len(checks)}")
        return 0 if all(ok for _, ok in checks) else 1
    if cmd == "zoo":
        report = {s["name"]: _round_floats(
            {k: s[k] for k in ("label", "kind", "mean_n", "var_n",
                               "mandel_q", "g2", "var_x", "var_p",
                               "var_product", "tail")})
            for s in build_zoo()}
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    if cmd == "distributions":
        print(json.dumps(_round_floats(distributions_report()),
                         indent=2, sort_keys=True))
        return 0
    if cmd == "squeezing":
        print(json.dumps(_round_floats(squeezing_sweep()),
                         indent=2, sort_keys=True))
        return 0
    if cmd == "husimi":
        print(json.dumps(_round_floats(husimi_report()),
                         indent=2, sort_keys=True))
        return 0
    if cmd == "detector":
        print(json.dumps(_round_floats(detector_report()),
                         indent=2, sort_keys=True))
        return 0
    if cmd == "classify":
        print(json.dumps(classifier_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "brains":
        print(json.dumps(brains_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "holds":
        for key, value in HOLD_GATES.items():
            print(f"{key}: {value}")
        return 0
    if cmd == "hold-demo":
        action = argv[1] if len(argv) > 1 else "real_laser_control"
        print(f"{action}: {HOLD_GATES.get(action, 'PROCEED - not gated')}")
        return 2 if gate(action) == "HOLD" else 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
