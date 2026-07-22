
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

## Design choices

**Two LLM calls per question, not one.**

Call #1 (`query_parser.py`) is
small and narrow: extract the student's stated score, budget + its unit
(year/semester/total-course), a named college if any, into a fixed JSON
schema.

Call #2 is the generation call, with the prompt additionally
containing `checks.py`'s pre-computed facts 
**Retrieval: structural filters + semantic search, not a naive top-k.**
At 15 records, exact structural filtering (course keyword, government
flag, hostel flag) is on logic basis , I try to make things more code handled, then Semantic embedding search handles the
free-text cases structural filtering can't reach.

**Grounding is enforced in the prompt, not hoped for.** 

The system
prompt in `prompt_builder.py` encodes every trap in `DATA_DICTIONARY.md`
explicitly fees are annual, cutoff is a hard floor, `avg_placement_lpa
== 0` means "not reported," Diploma ≠ degree, extra costs live only in
`about`  rather than relying on the model to infer them. `answer.py`
also fails safe: if the model doesn't return parseable JSON, the
response is `answered: false` with an internal error reason, never a
guess dressed up as an answer.

**Unit handling (fees).** `annual_fees_inr` is per year. When a question
uses per-semester, lakhs, or total-course-cost framing, `checks.py`
converts explicitly (assuming 2 semesters/year, stated as an assumption
since course duration isn't in the dataset) and the model is instructed
to surface that assumption in the answer rather than silently answering
with the annual figure.

**Diploma vs. degree.** One college offers only Diplomas. Course-keyword
filtering excludes it from degree-seeking searches by construction (its
course list simply doesn't contain "B.Tech," etc.), and the prompt
instructs the model to state its judgment explicitly if asked directly
about it, rather than silently including or excluding it.

**Cheap, fast refusal for nonexistent colleges.** If `query_parser`
extracts a named college that matches nothing in the full dataset, the
pipeline refuses immediately

Most of the above changes are done because I have small dataset , I was able to perform structural filtering

## What I'd do differently with more time
- Add a second-pass verifier call that checks a drafted answer's cited
  numbers against the source records before returning it — the two-call
  pipeline currently prevents *known* arithmetic traps but doesn't catch
  a wrong claim the model invents for some other reason.
- Route by question complexity to control cost as usage grows — cheap
  structural questions don't need the same model as open-ended ones 
- Swap the embedding model / retrieval backend for something persistent
  (e.g. a vector store that caches embeddings across runs) once the
  catalog is large enough that recomputing embeddings per run matters.

---

## Part B — Proof I've shipped


- I have created few projects that are currently running in prod , eg. In house ETL pipeline with complete Hadoop infrastructure locally using Airflow and AWS.
- **My role:** I have personally created from scratch a LSTM model for time series forecasting , CNN for image detection and currently wokring of self-train emotion detection system.
- **What broke / surprised me in production:** There are plenty of things; like while I was desigining LTM(long term memory) system in my current role, I was facing issue in saving relevant imformation for any conversation , as I dont want to fill up database with chats. In begining I approached this problem by summarizing list of messages but it comes out failure in long conversation say 500 messages 
- **Cost, and what brought it down:** Most of my work was for cost optimization wether in deployment or inferencing , that ETL pipeline I created has waived off 100% cost for DataBricks

## Part C — Reflection

**How would you keep per-query cost low as usage grows?**
Since I am using provider I was able to route my model selection and also in current setup of two LLM call one call still be directed to small model. If I  got time I would have tried it out.
Route by question complexity rather than sending everything to the same
model structural questions (fees, eligibility, course lists) can be
answered by a cheap model, or skip the LLM entirely once `query_parser`
extracts clean structured intent, while only genuinely open-ended
questions need a stronger model. Cache repeated/near-duplicate questions,
since real usage will cluster around popular colleges, and keep prompts
lean — retrieved records only, not the full catalog, so cost doesn't
scale linearly with catalog size.

**How would you stop the system from ever stating a wrong fee or cutoff?**
Two layers. First, ground the model with explicit rules about the data's
known ambiguities. Second — and more important — don't trust the model's
own arithmetic for anything that's actually just arithmetic:
I could have also explore agentic approach for every single airthmatic code based decisions

**If I joined tomorrow, what would I build first, and why?**
I would do required changes in this , but firstly I will design the database and all required things to monitor responses critics and improvement.That includes ETL too

**How would I measure whether AI is actually helping students?**
HIL(human in the loop) but my personal choice would be as I have data ready to examine 
I would use it and may be go with judge LLM approach to see Recall and Precison.

## Part D — Cost, with numbers



| Metric | Value |
|---|---|
| Avg input tokens/query (both calls combined) | 2,404 |
| Avg output tokens/query (both calls combined) | 425 |
| Avg end-to-end latency/query | 2.91s |
| Model used, cost per 1M tokens | openai/gpt-oss-120b (Groq) — $0.15/M input, $0.60/M output |
| Cost per 1,000 queries (₹) | ≈ ₹59 (≈ $0.62, at USD/INR ≈ 96.4) |
| One-time embedding cost for the full dataset | $0 — all-MiniLM-L6-v2 runs locally via sentence-transformers, not a billed API call |

**At 50,000 queries/month, what breaks first?**
With a 15-college catalog and a two-call pipeline, latency (two sequential
round trips per query, ~2.9s combined) and the operational cost of
*verifying* accuracy at scale are more likely pressure points than raw
token cost — 50,000 queries/month comes to roughly ₹2,950, trivial for
this pipeline. Caching repeated questions and routing simple structural
queries (e.g. "list government colleges with hostels") away from the LLM
entirely would be the first lever, followed by checking Groq's RPM/TPM
rate limits against a bursty 50k/month traffic pattern.