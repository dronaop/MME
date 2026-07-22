
## Quickstart
```bash
pip install -r requirements.txt
export GROQ_API_KEY=gsk_...
python answer.py "Which colleges offer an MBA, and what do they cost?"
```
Outputs a single JSON object on stdout (metrics go to stderr, so stdout stays parseable):
```json
{"answer": "...", "citations": ["C002","C004"], "answered": true, "reason_if_unanswered": null}
```

Regenerate the published answers and run the eval suite:
```bash
python run_all.py             # writes answers.md from the 7 published questions
python evals/run_evals.py     # runs evals/questions.json, prints a pass rate
```

To run the evaluator without a Groq key or network access, use the
deterministic local test provider:
```bash
LLM_PROVIDER=mock python evals/run_evals.py
```

## Architecture

```
answer.py               CLI entrypoint — the required interface
run_all.py               regenerates answers.md
src/data_loader.py       loads + type-coerces sample_colleges.csv
src/query_parser.py      call #1: extracts structured intent from the raw
                          question (score, budget+period, named college...)
src/checks.py            deterministic Python: eligibility + budget-unit
                          conversion, computed from query_parser's output
src/retriever.py         hybrid retrieval — structural filters + sentence
                          now informed by query_parser's structured signals
src/prompt_builder.py    grounding rules + record formatting + injects
                          checks.py's pre-verified facts into the prompt
src/llm_client.py        raw httpx call to Groq's Chat Completions API (no SDK)
evals/                   10 question/expected pairs targeting the data
                          dictionary's trap cases, + a scoring script
```

