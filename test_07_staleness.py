"""
Test 7 — Temporal / Staleness Handling

Evaluates whether Mem0 applies explicit timestamps and whether timestamped
memories rank newer contradictory rulings above older ones.
"""
from datetime import datetime, timezone
from client import clean_user, get_client, make_result, memory_text, rank_containing, search_memories, wait_for_search, USER_IDS

TEST_NAME = "07_staleness"
BASE_USER_ID = USER_IDS["test_07"]
OLD_FACT = "Stefan Brenner is CLEARED — removed from restricted list."
NEW_FACT = "Stefan Brenner is BLOCKED — arms trafficking confirmed."
OLD_DATE = "2024-05-01"
NEW_DATE = "2025-05-01"
REFERENCE_DATE = "2025-05-15T00:00:00Z"


def _first_containing(results: list, needle: str) -> dict | None:
    needle = needle.lower()
    for result in results:
        if needle in memory_text(result).lower():
            return result
    return None


def _timestamp_applied(result: dict | None, expected_date: str) -> bool:
    if not result:
        return False
    return str(result.get("created_at", "")).startswith(expected_date)


def _run_mode(label: str, user_id: str, infer: bool) -> dict:
    client = get_client()
    clean_user(
        user_id,
        verification_queries=["Stefan Brenner"],
    )

    old_ts = int(datetime(2024, 5, 1, tzinfo=timezone.utc).timestamp())
    old_add = client.add([
        {"role": "user", "content": OLD_FACT},
    ], user_id=user_id, timestamp=old_ts, infer=infer)
    wait_for_search(
        "Stefan Brenner cleared",
        filters={"user_id": user_id},
        threshold=0.0,
        contains="clear",
    )

    new_ts = int(datetime(2025, 5, 1, tzinfo=timezone.utc).timestamp())
    new_add = client.add([
        {"role": "user", "content": NEW_FACT},
    ], user_id=user_id, timestamp=new_ts, infer=infer)
    wait_for_search(
        "Stefan Brenner blocked",
        filters={"user_id": user_id},
        threshold=0.0,
        contains="block",
    )

    results = search_memories(
        "What is Stefan Brenner's current status as of May 15, 2025?",
        filters={"user_id": user_id},
        reference_date=REFERENCE_DATE,
        threshold=0.0,
    )

    block_rank = rank_containing(results, "block")
    clear_rank = rank_containing(results, "clear")
    block_result = _first_containing(results, "block")
    clear_result = _first_containing(results, "clear")
    block_timestamp_applied = _timestamp_applied(block_result, NEW_DATE)
    clear_timestamp_applied = _timestamp_applied(clear_result, OLD_DATE)
    timestamps_applied = block_timestamp_applied and clear_timestamp_applied

    findings = [f"{label}: total memories returned: {len(results)}"]
    for i, r in enumerate(results):
        mem = r.get("memory", "")
        score = r.get("score", 0.0)
        ts = r.get("created_at", "unknown")
        findings.append(f"  [{label}][{i}] '{mem}' (score: {score:.3f}, ts: {ts})")

    findings.append(
        f"{label}: timestamp applied? clear={clear_timestamp_applied}, "
        f"block={block_timestamp_applied}"
    )
    findings.append(f"{label}: newer BLOCK rank: {block_rank if block_rank is not None else 'not returned'}")
    findings.append(f"{label}: older CLEAR rank: {clear_rank if clear_rank is not None else 'not returned'}")

    if block_rank is None or clear_rank is None:
        status = "FAIL"
        findings.append(f"{label}: one or both expected rulings were not returned.")
    elif not timestamps_applied:
        status = "INCONCLUSIVE"
        findings.append(f"{label}: custom timestamps were not reflected in returned created_at values.")
    elif block_rank == 1:
        status = "PASS"
        findings.append(f"{label}: newer BLOCK ruling ranked first with timestamps applied.")
    elif clear_rank == 1:
        status = "FAIL"
        findings.append(f"{label}: older CLEAR ruling ranked above newer BLOCK despite timestamps.")
    else:
        status = "PARTIAL"
        findings.append(f"{label}: both rulings returned with timestamps, but neither ranked first cleanly.")

    return {
        "status": status,
        "findings": findings,
        "timestamps_applied": timestamps_applied,
        "block_rank": block_rank,
        "clear_rank": clear_rank,
        "raw": {
            "old_add": old_add,
            "new_add": new_add,
            "results": results,
        },
    }


def run() -> dict:
    direct = _run_mode("Direct Import", f"{BASE_USER_ID}_direct", infer=False)
    inferred = _run_mode("Inferred Memory", f"{BASE_USER_ID}_inferred", infer=True)

    findings = []
    findings.extend(direct["findings"])
    findings.extend(inferred["findings"])

    findings.insert(
        0,
        "Comparison: direct import timestamp application = "
        f"{direct['timestamps_applied']}; inferred timestamp application = "
        f"{inferred['timestamps_applied']}."
    )

    statuses = [direct["status"], inferred["status"]]
    if all(status == "PASS" for status in statuses):
        status = "PASS"
    elif any(status == "FAIL" for status in statuses):
        status = "FAIL"
    elif all(status == "INCONCLUSIVE" for status in statuses):
        status = "INCONCLUSIVE"
    else:
        status = "PARTIAL"

    return make_result(
        TEST_NAME,
        status,
        findings,
        raw={
            "direct_import": direct["raw"],
            "inferred": inferred["raw"],
        },
    )


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(run())
