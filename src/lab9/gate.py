"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    import math

    problems: list[str] = []

    from lab9.eval import aggregate
    from lab9.graders import GRADERS

    rows = pr.get("rows", [])
    manifest = pr.get("manifest", {})
    pairs = [(r.get("item_id"), r.get("seed")) for r in rows]
    base_pairs = {(r.get("item_id"), r.get("seed")) for r in base.get("rows", [])}
    if len(set(pairs)) != len(pairs):
        problems.append("duplicate (item, seed) rows")
    if set(pairs) != base_pairs:
        problems.append("(item, seed) coverage differs from baseline")
    seeds = manifest.get("seeds", [])
    items = manifest.get("items")
    if type(items) is not int or items <= 0 or len(set(seeds)) != len(seeds):
        problems.append("invalid manifest item count or seeds")
    elif len(rows) != items * len(seeds):
        problems.append("row count differs from manifest items x seeds")
    actual_items = {item for item, seed in pairs}
    if items != len(actual_items) or set(pairs) != {(item, seed) for item in actual_items for seed in seeds}:
        problems.append("manifest does not describe a complete item x seed grid")
    if pr.get("evaluator_failures"):
        problems.append("evaluator failures present")

    for metric, value in pr.get("metrics", {}).items():
        if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
            problems.append(f"invalid aggregate metric {metric}")
    graded = [m["id"] for m in spec.get("metrics", []) if m["id"] in GRADERS]
    for row in rows:
        for metric in graded:
            if type(row.get(metric)) is not bool:
                problems.append(f"row {row.get('item_id')}@{row.get('seed')} missing or invalid {metric}")
        if "cost" in row and (not isinstance(row["cost"], (int, float)) or not math.isfinite(row["cost"])):
            problems.append("invalid row cost")

    baseline_tags = {(r["item_id"], r["seed"]): set(r.get("slices") or []) for r in base.get("rows", [])}
    for row in rows:
        pair = (row.get("item_id"), row.get("seed"))
        if pair in baseline_tags and set(row.get("slices") or []) != baseline_tags[pair]:
            problems.append(f"slice tags differ for {pair}")

    if not problems and rows and all("cost" in row for row in rows):
        computed = aggregate(rows, graded, k_values=spec.get("pass_k", []))
        for metric, expected in computed.items():
            actual = pr.get("metrics", {}).get(metric)
            if expected is not None and (actual is None or not math.isclose(actual, expected, abs_tol=1e-9)):
                problems.append(f"aggregate {metric} differs from rows")

    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        for section, identity in (("metrics", "id"), ("slices", "name")):
            current = {(entry[identity], entry.get("metric")): entry for entry in spec.get(section, [])}
            for previous in base_spec.get(section, []):
                key = (previous[identity], previous.get("metric"))
                entry = current.get(key)
                if entry is None:
                    problems.append(f"removed {section} entry {key}")
                    continue
                if previous.get("blocking") and not entry.get("blocking"):
                    problems.append(f"disabled blocking for {key}")
                old = previous.get("threshold", {}) if section == "metrics" else previous
                new = entry.get("threshold", {}) if section == "metrics" else entry
                for threshold in ("min", "max", "max_increase"):
                    if threshold in old:
                        if threshold not in new:
                            problems.append(f"removed {threshold} for {key}")
                        elif (threshold == "min" and new[threshold] < old[threshold]) or (threshold != "min" and new[threshold] > old[threshold]):
                            problems.append(f"loosened {threshold} for {key}")
                if old.get("no_significant_drop") and not new.get("no_significant_drop"):
                    problems.append(f"removed no_significant_drop for {key}")

    return problems


def _paired_interval(current: dict[str, float], baseline: dict[str, float], options: dict) -> tuple[float, float, float]:
    keys = sorted(current.keys() & baseline.keys())
    return stats.paired_bootstrap(
        [current[k] for k in keys],
        [baseline[k] for k in keys],
        n_resamples=options.get("n_resamples", 1000),
        rng=options.get("rng", 2027),
        confidence=options.get("confidence", 0.95),
    )


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    for rule in spec.get("slices", []):
        name, metric = rule["name"], rule["metric"]
        slice_id = f"slice:{name}/{metric}"
        current = per_item(pr, metric, slice_name=name)
        floor = rule.get("min")
        score = sum(current.values()) / len(current) if current else None
        failed = score is None or (floor is not None and score < floor)
        details = ["missing scores" if score is None else f"{score:.4f}"]
        if floor is not None:
            details.append(f"min {floor:.2f}")
        if current and rule.get("no_significant_drop"):
            baseline = per_item(base, metric, slice_name=name)
            if current.keys() == baseline.keys():
                delta, lo, hi = _paired_interval(current, baseline, spec.get("bootstrap", {}))
                details.append(f"Δ {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]")
                failed |= hi < 0
            else:
                details.append("slice items differ from baseline")
                failed = True

        verdict = "ok"
        if failed:
            verdict = "warn"
            if rule.get("blocking"):
                verdict = "BLOCK"
                blocked.append(slice_id)
        lines.append(f"  {slice_id:<35} {'  '.join(details)}  {verdict}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            d, lo, hi = _paired_interval(a, b, bs)
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
