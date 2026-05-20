"""
Test 4 — Multi-Entity Ambiguity

Evaluates whether Mem0 correctly distinguishes between two different entities
with overlapping first names. Uses direct import to isolate retrieval/ranking
behavior from Mem0's extraction decisions.
"""
from client import clean_user, get_client, make_result, rank_containing, search_memories, wait_for_search, USER_IDS

TEST_NAME = "04_multi_entity_ambiguity"
USER_ID = USER_IDS["test_04"]


def run() -> dict:
    client = get_client()
    clean_user(
        USER_ID,
        verification_queries=["Elena Vasquez", "Elena Kovac"],
    )

    # Two distinct entities sharing a first name. Direct import keeps setup to
    # one controlled memory per entity so this test measures retrieval ambiguity,
    # not extraction behavior.
    client.add([
        {"role": "user", "content": "Elena Vasquez is BLOCKED — financial fraud."},
    ], user_id=USER_ID, infer=False)
    wait_for_search(
        "Elena Vasquez",
        filters={"user_id": USER_ID},
        threshold=0.0,
        contains="Vasquez",
    )

    client.add([
        {"role": "user", "content": "Elena Kovac is BLOCKED — export control violation."},
    ], user_id=USER_ID, infer=False)
    wait_for_search(
        "Elena Kovac",
        filters={"user_id": USER_ID},
        threshold=0.0,
        contains="Kovac",
    )

    queries = [
        ("Elena Vasquez",        "specific_a"),
        ("Elena Kovac",          "specific_b"),
        ("Elena V.",             "ambiguous_initial"),
        ("Elena",                "first_only"),
    ]

    findings = []
    raw = {}
    for query, kind in queries:
        results = search_memories(query, filters={"user_id": USER_ID}, threshold=0.0)
        top_mem = results[0].get("memory", "") if results else "(none)"
        top_score = results[0].get("score", 0) if results else 0
        vasquez_rank = rank_containing(results, "Vasquez")
        kovac_rank = rank_containing(results, "Kovac")
        findings.append(
            f"  [{kind:18s}] '{query}' → '{top_mem}' "
            f"(score: {top_score:.3f}, Vasquez rank: {vasquez_rank}, Kovac rank: {kovac_rank})"
        )
        raw[kind] = {
            "query": query,
            "vasquez_rank": vasquez_rank,
            "kovac_rank": kovac_rank,
            "results": results,
        }

    # Specific queries should return the right entity at the top.
    spec_a_correct = raw["specific_a"]["vasquez_rank"] == 1
    spec_b_correct = raw["specific_b"]["kovac_rank"] == 1

    if spec_a_correct and spec_b_correct:
        status = "PASS"
        findings.append("Specific queries correctly distinguished entities.")
    elif spec_a_correct or spec_b_correct:
        status = "PARTIAL"
    else:
        status = "FAIL"
        findings.append("Specific queries failed to distinguish entities.")

    return make_result(TEST_NAME, status, findings, raw=raw)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(run())
