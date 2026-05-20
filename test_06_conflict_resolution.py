"""
Test 6 — Conflict Resolution

Evaluates how Mem0 handles two contradicting rulings stored for the same entity.
Uses direct import so the test isolates retrieval/ranking behavior from Mem0's
extraction decisions.
"""
import time
from client import clean_user, get_client, make_result, rank_containing, search_memories, wait_for_search, USER_IDS

TEST_NAME = "06_conflict_resolution"
USER_ID = USER_IDS["test_06"]


def run() -> dict:
    client = get_client()
    clean_user(
        USER_ID,
        verification_queries=["Marcus Webb"],
    )

    # First ruling: CLEAR. Direct import keeps this to one controlled memory.
    client.add([
        {"role": "user", "content": "Marcus Webb is CLEARED — no match found on restricted list."},
    ], user_id=USER_ID, infer=False)
    wait_for_search(
        "Marcus Webb cleared",
        filters={"user_id": USER_ID},
        threshold=0.0,
        contains="Marcus",
    )

    # Small delay to ensure separate creation timestamps
    time.sleep(2)

    # Contradicting ruling: BLOCK.
    client.add([
        {"role": "user", "content": "Marcus Webb is BLOCKED — export control violation confirmed."},
    ], user_id=USER_ID, infer=False)
    wait_for_search(
        "Marcus Webb blocked",
        filters={"user_id": USER_ID},
        threshold=0.0,
        contains="block",
    )

    # Query
    results = search_memories("Marcus Webb ruling", filters={"user_id": USER_ID}, threshold=0.0)

    findings = [f"Total memories about Marcus Webb after conflict: {len(results)}"]

    # Categorize each result
    for i, r in enumerate(results):
        mem = r.get("memory", "")
        score = r.get("score", 0.0)
        findings.append(f"  [{i}] '{mem}' (score: {score:.3f})")

    block_rank = rank_containing(results, "block")
    clear_rank = rank_containing(results, "clear")
    findings.append(f"BLOCK ruling rank: {block_rank if block_rank is not None else 'not returned'}")
    findings.append(f"CLEAR ruling rank: {clear_rank if clear_rank is not None else 'not returned'}")

    if block_rank == 1:
        status = "PASS"
        findings.append("BLOCK ruling ranked first — newer contradicting fact won.")
    elif clear_rank == 1:
        status = "FAIL"
        findings.append("CLEAR (older) ruling ranked above BLOCK (newer).")
    else:
        status = "PARTIAL"
        findings.append("Ranking ambiguous — both rulings present without clear precedence.")

    return make_result(TEST_NAME, status, findings, raw={"results": results})


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(run())
