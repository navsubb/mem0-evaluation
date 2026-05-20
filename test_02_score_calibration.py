"""
Test 2 — Score Calibration

Evaluates whether Mem0's relevance scores are calibrated meaningfully and stable
across repeated identical queries.
"""
from client import clean_user, get_client, make_result, search_memories, wait_for_search, USER_IDS

TEST_NAME = "02_score_calibration"
USER_ID = USER_IDS["test_02"]


def run() -> dict:
    client = get_client()
    clean_user(
        USER_ID,
        verification_queries=[
            "Victor Harlow",
            "Elena Vasquez",
            "Northern Crest Holdings",
            "Gerald Ashworth",
        ],
    )

    # Store a fixed set of rulings
    rulings = [
        "Victor Harlow is BLOCKED — arms trafficking.",
        "Elena Vasquez is BLOCKED — financial fraud.",
        "Northern Crest Holdings is BLOCKED — money laundering.",
        "Gerald Ashworth is BLOCKED — arms trafficking.",
    ]
    for r in rulings:
        client.add([
            {"role": "user", "content": "Record screening decision."},
            {"role": "assistant", "content": r},
        ], user_id=USER_ID, infer=True)
    for query, needle in [
        ("Victor Harlow", "Harlow"),
        ("Elena Vasquez", "Vasquez"),
        ("Northern Crest Holdings", "Northern"),
        ("Gerald Ashworth", "Ashworth"),
    ]:
        wait_for_search(query, filters={"user_id": USER_ID}, threshold=0.0, contains=needle)

    # Calibration queries across the relevance spectrum
    queries = [
        ("Victor Harlow",      "exact_victor"),
        ("Elena Vasquez",      "exact_elena"),
        ("Harlow",             "partial_last"),
        ("Victor",             "partial_first"),
        ("John Smith",         "unrelated"),
        ("Acme Corporation",   "unrelated_company"),
        ("aaa bbb ccc",        "garbage"),
        ("12345",              "numeric_garbage"),
    ]

    # Run each query 3 times to test stability
    N_RUNS = 3
    findings = []
    raw = {}
    for query, kind in queries:
        scores = []
        for _ in range(N_RUNS):
            results = search_memories(query, filters={"user_id": USER_ID}, threshold=0.0)
            scores.append(results[0].get("score", 0.0) if results else 0.0)
        avg = sum(scores) / len(scores)
        spread = max(scores) - min(scores)
        raw[kind] = {"query": query, "scores": scores, "avg": avg, "spread": spread}
        findings.append(f"  [{kind:18s}] '{query:25s}' avg={avg:.3f}, spread={spread:.3f}")

    # Heuristic: are exact > unrelated > garbage in average score?
    avg_exact     = (raw["exact_victor"]["avg"] + raw["exact_elena"]["avg"]) / 2
    avg_unrelated = raw["unrelated"]["avg"]
    avg_garbage   = raw["garbage"]["avg"]
    max_spread    = max(v["spread"] for v in raw.values())

    findings.insert(0, f"Max score spread across 3 runs of same query: {max_spread:.3f}")
    findings.insert(1, f"Avg scores — exact: {avg_exact:.3f}, unrelated: {avg_unrelated:.3f}, garbage: {avg_garbage:.3f}")

    if avg_exact > avg_unrelated > avg_garbage and max_spread < 0.1:
        status = "PASS"
    elif avg_exact > avg_garbage:
        status = "PARTIAL"
    else:
        status = "FAIL"

    return make_result(TEST_NAME, status, findings, raw=raw)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(run())
