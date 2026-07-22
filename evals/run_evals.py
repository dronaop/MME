#!/usr/bin/env python3
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from answer import answer_question  


def check(case, result):
    problems = []
    if result["answered"] != case["expected_answered"]:
        problems.append(
            f"answered={result['answered']!r}, expected {case['expected_answered']!r}"
        )
    got_citations = set(result.get("citations") or [])
    expected = set(case.get("expected_citations") or [])
    if not expected.issubset(got_citations):
        problems.append(f"missing citations {expected - got_citations}")
    forbidden = set(case.get("forbidden_citations") or [])
    if forbidden & got_citations:
        problems.append(f"forbidden citations present: {forbidden & got_citations}")
    answer_lower = (result.get("answer") or "").lower()
    for kw in case.get("expected_keywords", []):
        if kw.lower() not in answer_lower:
            problems.append(f"answer missing expected keyword {kw!r}")
    return problems


def main():
    path = os.path.join(os.path.dirname(__file__), "questions.json")
    with open(path) as f:
        cases = json.load(f)

    passed = 0
    for case in cases:
        result = answer_question(case["question"])
        problems = check(case, result)
        status = "PASS" if not problems else "FAIL"
        if status == "PASS":
            passed += 1
        print(f"[{status}] {case['id']}: {case['question']}")
        if problems:
            for p in problems:
                print(f"         - {p}")
            print(f"         got: {json.dumps(result, ensure_ascii=False)}")

    print(f"\n{passed}/{len(cases)} passed ({100 * passed / len(cases):.0f}%)")


if __name__ == "__main__":
    main()
