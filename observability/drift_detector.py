"""
Phase 7 — Drift Detection
Compares the latest eval run against the baseline (first eval run).
Fires an alert if pass rate drops more than 5% from baseline.
"""

import os
import json
import glob
from datetime import datetime, timezone

RESULTS_DIR    = os.path.join(os.path.dirname(__file__), "..", "eval", "results")
DRIFT_THRESHOLD = 0.05   # 5% drop triggers alert


def load_eval_results() -> list[dict]:
    """Load all eval result files sorted by timestamp (oldest first)."""
    files = sorted(glob.glob(os.path.join(RESULTS_DIR, "eval_*.json")))
    results = []
    for f in files:
        with open(f) as fp:
            results.append(json.load(fp))
    return results


def detect_drift() -> dict:
    """
    Compare latest eval run to baseline.

    Returns:
    {
        "has_drift":       bool,
        "baseline_rate":   float,
        "latest_rate":     float,
        "delta":           float,
        "alert":           str,
        "category_drift":  dict,   # categories that dropped
        "recommendation":  str,
    }
    """
    results = load_eval_results()

    if len(results) < 2:
        return {
            "has_drift":      False,
            "baseline_rate":  None,
            "latest_rate":    None,
            "delta":          None,
            "alert":          "Not enough eval runs to detect drift (need at least 2)",
            "category_drift": {},
            "recommendation": "Run eval harness again to establish a comparison point",
        }

    baseline = results[0]
    latest   = results[-1]

    baseline_rate = baseline["pass_rate"]
    latest_rate   = latest["pass_rate"]
    delta         = latest_rate - baseline_rate
    has_drift     = delta < -DRIFT_THRESHOLD

    # Category-level drift
    category_drift = {}
    for cat, stats in latest.get("categories", {}).items():
        latest_cat_rate   = stats["passed"] / stats["total"]
        baseline_cat      = baseline.get("categories", {}).get(cat, {})
        if baseline_cat:
            baseline_cat_rate = baseline_cat["passed"] / baseline_cat["total"]
            cat_delta         = latest_cat_rate - baseline_cat_rate
            if cat_delta < -DRIFT_THRESHOLD:
                category_drift[cat] = {
                    "baseline": round(baseline_cat_rate, 3),
                    "latest":   round(latest_cat_rate, 3),
                    "delta":    round(cat_delta, 3),
                }

    # Build alert message
    if has_drift:
        alert = (
            f"DRIFT DETECTED: pass rate dropped {abs(delta)*100:.1f}% "
            f"(baseline={baseline_rate*100:.1f}% → latest={latest_rate*100:.1f}%)"
        )
        recommendation = (
            "Review recent prompt changes. "
            "Run prompt comparison script to identify regression. "
            "Consider rollback if delta > 10%."
        )
    else:
        alert          = f"No drift detected (delta={delta*100:+.1f}%)"
        recommendation = "System is stable."

    return {
        "has_drift":       has_drift,
        "baseline_rate":   round(baseline_rate, 4),
        "latest_rate":     round(latest_rate, 4),
        "delta":           round(delta, 4),
        "baseline_run":    baseline.get("timestamp", ""),
        "latest_run":      latest.get("timestamp", ""),
        "alert":           alert,
        "category_drift":  category_drift,
        "recommendation":  recommendation,
    }


def print_drift_report():
    """Print a human-readable drift report."""
    report = detect_drift()

    print("\n" + "=" * 60)
    print("Phase 7 — Drift Detection Report")
    print(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    if report["baseline_rate"] is None:
        print(f"\n{report['alert']}")
        return

    print(f"\nBaseline run : {report['baseline_run']}")
    print(f"Latest run   : {report['latest_run']}")
    print(f"\nBaseline rate: {report['baseline_rate']*100:.1f}%")
    print(f"Latest rate  : {report['latest_rate']*100:.1f}%")
    print(f"Delta        : {report['delta']*100:+.1f}%")
    print(f"\nStatus: {'⚠ ' + report['alert'] if report['has_drift'] else '✓  ' + report['alert']}")

    if report["category_drift"]:
        print(f"\nCategories with drift:")
        for cat, stats in report["category_drift"].items():
            print(f"  {cat}: {stats['baseline']*100:.0f}% → {stats['latest']*100:.0f}% ({stats['delta']*100:+.0f}%)")

    print(f"\nRecommendation: {report['recommendation']}")
    print("=" * 60)
