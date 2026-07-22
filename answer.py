#!/usr/bin/env python3
"""
Usage:
    pip install -r requirements.txt
    export GROQ_API_KEY=...
    python answer.py "Which colleges offer an MBA, and what do they cost?"

Prints exactly one JSON object to stdout:
    {"answer": "...", "citations": [...], "answered": true|false, "reason_if_unanswered": null|"..."}

All logging/diagnostics go to stderr so stdout stays parseable.

Pipeline: two LLM calls per question, not one.
    1. query_parser.parse_query()  — cheap, narrow: extract structured intent
       from the raw question (student's score, budget + its period, a named
       college, etc). See src/query_parser.py for why this exists.
    2. The main generation call — same as before, except it now also
       receives src/checks.py's code-computed eligibility/budget facts
       inline, so it reports pre-verified numbers instead of redoing that
       arithmetic itself.
If step 1 finds a college name that matches nothing in the dataset, we
skip step 2 entirely and refuse immediately — cheaper and more reliable
than trusting the generation model to notice and self-refuse.
"""
import json
import sys

from src.data_loader import load_colleges
from src.retriever import retrieve
from src.prompt_builder import build_messages
from src.llm_client import call_llm
from src.query_parser import parse_query
from src.checks import eligibility_lines, budget_conversion_lines, no_match_signal
from src.debug import log


def answer_question(question: str) -> dict:
    records = load_colleges()
    query_signals = parse_query(question)
    log("4. parsed query signals", query_signals)

    reason = no_match_signal(records, query_signals)
    if reason:
        log("5. named-college validation", reason)
        print(f"[metrics] short-circuited before generation: {reason}", file=sys.stderr)
        return {"answer": "", "citations": [], "answered": False, "reason_if_unanswered": reason}

    retrieved = retrieve(records, question, parsed=query_signals)
    log("&&. retrieved records", [{"college_id": r["college_id"], "name": r["name"]} for r in retrieved])

    check_lines = eligibility_lines(retrieved, query_signals.get("student_score_pct"))
    check_lines += budget_conversion_lines(
        retrieved, query_signals.get("budget_amount_inr"), query_signals.get("budget_period")
    )
    log("6. code-verified checks", check_lines or "No eligibility or budget checks requested")

    system_prompt, user_prompt = build_messages(question, retrieved, check_lines=check_lines)
    log("generation user prompt", user_prompt)
    result = call_llm(system_prompt, user_prompt)
    log("1 generation result", {
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "latency_s": round(result.latency_s, 2),
        "text": result.text,
    })

    try:
        parsed_answer = json.loads(result.text)
    except json.JSONDecodeError:
        parsed_answer = {
            "answer": "",
            "citations": [],
            "answered": False,
            "reason_if_unanswered": "internal error: model response was not valid JSON",
        }

    parsed_answer.setdefault("answer", "")
    parsed_answer.setdefault("citations", [])
    parsed_answer.setdefault("answered", False)
    parsed_answer.setdefault("reason_if_unanswered", None)
    log("final parsed answer", parsed_answer)

    print(
        f"[metrics] model={result.model} in_tok={result.input_tokens} "
        f"out_tok={result.output_tokens} latency={result.latency_s:.2f}s "
        f"parsed_signals={query_signals}",
        file=sys.stderr,
    )
    return parsed_answer


def main():
    if len(sys.argv) != 2:
        print('Usage: python answer.py "your question"', file=sys.stderr)
        sys.exit(1)
    result = answer_question(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
