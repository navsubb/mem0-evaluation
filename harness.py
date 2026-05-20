"""
Mem0 Evaluation Harness — runs all tests, prints summary, writes results.json.
"""
import json
import traceback
from dotenv import load_dotenv

load_dotenv()

import test_01_cross_session
import test_02_score_calibration
import test_03_name_variation
import test_04_multi_entity_ambiguity
import test_05_alias_handling
import test_06_conflict_resolution
import test_07_staleness

TESTS = [
    ("Cross-Session Persistence",   test_01_cross_session.run),
    ("Score Calibration",           test_02_score_calibration.run),
    ("Name Variation Retrieval",    test_03_name_variation.run),
    ("Multi-Entity Ambiguity",      test_04_multi_entity_ambiguity.run),
    ("Alias Handling",              test_05_alias_handling.run),
    ("Conflict Resolution",         test_06_conflict_resolution.run),
    ("Temporal / Staleness",        test_07_staleness.run),
]

DIVIDER = "─" * 70

STATUS_COLORS = {
    "PASS":         "\033[92m",
    "FAIL":         "\033[91m",
    "PARTIAL":      "\033[93m",
    "INCONCLUSIVE": "\033[90m",
    "ERROR":        "\033[91m",
}
RESET = "\033[0m"


def run_all() -> list:
    results = []
    for label, fn in TESTS:
        print(f"\n{DIVIDER}")
        print(f"Running: {label}")
        print(DIVIDER)
        try:
            result = fn()
        except Exception as e:
            traceback.print_exc()
            result = {
                "test":     fn.__module__,
                "status":   "ERROR",
                "findings": [f"Exception: {e}"],
                "raw":      {},
            }

        status = result.get("status", "INCONCLUSIVE")
        color = STATUS_COLORS.get(status, "")
        print(f"\n  Status: {color}{status}{RESET}")
        for f in result.get("findings", []):
            print(f"  {f}")
        results.append({"label": label, **result})
    return results


def print_summary(results: list) -> None:
    print(f"\n{DIVIDER}")
    print("SUMMARY")
    print(DIVIDER)
    counts = {}
    for r in results:
        status = r.get("status", "INCONCLUSIVE")
        counts[status] = counts.get(status, 0) + 1
        color = STATUS_COLORS.get(status, "")
        print(f"  {r['label']:35s} {color}{status}{RESET}")
    print(DIVIDER)
    print(f"  Totals: {counts}")
    print(DIVIDER)


def main():
    results = run_all()
    print_summary(results)
    with open("results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults written to results.json")


if __name__ == "__main__":
    main()
