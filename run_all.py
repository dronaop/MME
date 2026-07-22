#!/usr/bin/env python3
"""Regenerates answers.md by running answer.py against the 7 published
questions from the Task Sheet. Output is written verbatim, not edited."""
import json
import subprocess
import sys

QUESTIONS = [
    "I scored 78% and have a budget of Rs 1.5 lakh/year — which engineering colleges can I consider?",
    "Which colleges offer an MBA, and what do they cost?",
    "List the government colleges that have hostel facilities.",
    "What's the average placement package at North Ridge Institute of Technology?",
    "Does Ganga Valley University offer a PhD in Physics?",
    "Which colleges offer scholarships for students from low-income families?",
    "Which college is best for me? I have Rs 1 lakh per semester.",
]


def main():
    lines = ["# Answers — Published Questions\n"]
    for i, q in enumerate(QUESTIONS, 1):
        proc = subprocess.run(
            [sys.executable, "answer.py", q], capture_output=True, text=True
        )
        lines.append(f"## Q{i}: {q}\n")
        if proc.returncode != 0:
            lines.append(f"```\nERROR:\n{proc.stderr}\n```\n")
            continue
        try:
            parsed = json.loads(proc.stdout.strip())
            lines.append("```json\n" + json.dumps(parsed, indent=2, ensure_ascii=False) + "\n```\n")
        except json.JSONDecodeError:
            lines.append(f"```\n{proc.stdout}\n```\n")

    with open("answers.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Wrote answers.md")


if __name__ == "__main__":
    main()
