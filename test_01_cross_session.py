"""
Test 1 — Cross-Session Persistence

Evaluates whether a memory stored under a user_id with a run_id is retrievable
later when queried without that run_id.
"""
from client import clean_user, get_client, make_result, rank_containing, search_memories, wait_for_search, USER_IDS

TEST_NAME = "01_cross_session"
USER_ID = USER_IDS["test_01"]
RUN_ID = "mem0_eval_01_session_alpha"


def run() -> dict:
    client = get_client()
    clean_user(
        USER_ID,
        run_ids=[RUN_ID, "session_alpha"],
        verification_queries=["Gerald Ashworth"],
    )

    # Setup: store a ruling in "session alpha"
    setup_messages = [
        {"role": "user", "content": "Gerald Ashworth is BLOCKED — arms trafficking."},
    ]
    client.add(setup_messages, user_id=USER_ID, run_id=RUN_ID, infer=False)
    wait_for_search(
        "Gerald Ashworth",
        filters={"user_id": USER_ID},
        threshold=0.0,
        contains="Ashworth",
    )

    # Query: in a new "session" (no run_id)
    results = search_memories("Gerald Ashworth", filters={"user_id": USER_ID})

    # Inspect: what came back?
    findings = []
    if not results:
        return make_result(TEST_NAME, "FAIL",
                          ["No memories returned across session boundary."],
                          raw={"results": results})

    top = results[0]
    score = top.get("score", 0.0)
    memory_text = top.get("memory", "")

    findings.append(f"Top result: '{memory_text}' (score: {score:.3f})")
    findings.append(f"Total memories returned: {len(results)}")

    expected_rank = rank_containing(results, "Ashworth")
    findings.append(f"Expected memory rank: {expected_rank if expected_rank is not None else 'not returned'}")

    if expected_rank == 1:
        status = "PASS"
        findings.append("Expected memory ranked first across the session boundary.")
    elif expected_rank is not None:
        status = "PARTIAL"
        findings.append(f"Expected memory appeared at rank {expected_rank}, not first.")
    else:
        status = "FAIL"
        findings.append("Expected memory was not returned.")

    return make_result(TEST_NAME, status, findings, raw={"results": results})


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(run())
