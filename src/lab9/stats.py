"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    categories = {
        (POS, POS): "tp",
        ("PASS", POS): "fp",
        (POS, "PASS"): "fn",
        ("PASS", "PASS"): "tn",
    }
    counts = dict.fromkeys(categories.values(), 0)
    for human_label, judge_label in zip(human, judge, strict=True):
        category = categories.get((human_label, judge_label))
        if category is None:
            raise ValueError("Expected PASS or FAIL labels")
        counts[category] += 1
    return counts


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    counts = confusion(human, judge)
    true_positives = counts["tp"]
    predicted_failures = true_positives + counts["fp"]
    human_failures = true_positives + counts["fn"]
    precision = true_positives / predicted_failures if predicted_failures else 0.0
    recall = true_positives / human_failures if human_failures else 0.0
    return precision, recall


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    counts = confusion(human, judge)
    n = sum(counts.values())
    if not n:
        raise ValueError("Kappa requires at least one label pair")

    human_failures = counts["tp"] + counts["fn"]
    judge_failures = counts["tp"] + counts["fp"]
    # Scale both agreement terms by n**2 to check for degeneracy exactly.
    observed_agreement = (counts["tp"] + counts["tn"]) * n
    expected_agreement = human_failures * judge_failures + (n - human_failures) * (n - judge_failures)
    denominator = n * n - expected_agreement
    if denominator == 0:
        raise ValueError("Kappa is undefined when expected agreement is 1")
    return (observed_agreement - expected_agreement) / denominator


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Return the corrected rate in [0, 1], or NaN if it is undefined."""
    denominator = sensitivity + specificity - 1
    if denominator == 0:
        return float("nan")
    corrected = (observed_rate + specificity - 1) / denominator
    return max(0.0, min(1.0, corrected))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    import numpy as np
    from scipy.stats import bootstrap

    current = np.asarray(a, dtype=float)
    baseline = np.asarray(b, dtype=float)
    if current.ndim != 1 or current.shape != baseline.shape or current.size == 0:
        raise ValueError("Paired bootstrap requires equally sized, nonempty vectors")
    if not np.isfinite(current).all() or not np.isfinite(baseline).all():
        raise ValueError("Paired bootstrap requires finite values")

    def mean_difference(x, y, axis=-1):
        return np.mean(x, axis=axis) - np.mean(y, axis=axis)

    delta = float(mean_difference(current, baseline))
    if np.array_equal(current, baseline) or current.size == 1:
        return delta, delta, delta

    interval = bootstrap(
        (current, baseline),
        mean_difference,
        paired=True,
        method="percentile",
        n_resamples=n_resamples,
        confidence_level=confidence,
        rng=np.random.default_rng(rng),
    ).confidence_interval
    return delta, float(interval.low), float(interval.high)


def _validate_pass_counts(n: int, c: int, k: int) -> None:
    if not all(type(value) is int for value in (n, c, k)):
        raise ValueError("n, c and k must be integers")
    if not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError("Expected 0 <= c <= n and 1 <= k <= n")


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that at least one of k draws passes."""
    from math import comb

    _validate_pass_counts(n, c, k)
    return 1.0 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """Probability that all k draws pass."""
    from math import comb

    _validate_pass_counts(n, c, k)
    return comb(c, k) / comb(n, k)
