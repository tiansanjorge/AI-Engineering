# Project Integrator Report — Module 1

## Architecture

The system is a single CLI entrypoint (`src/run_query.py`) with three
separated concerns:

- `src/llm_client.py` — builds the prompt (system prompt from
  `prompts/main_prompt.txt` + user question) and calls the OpenAI Chat
  Completions API with `response_format={"type": "json_object"}`, forcing
  the model to return a syntactically valid JSON object. If the first
  response doesn't parse as JSON, it makes **one repair call** (a second,
  cheap request asking the model to fix its own broken JSON, `temperature=0`)
  before giving up — a common two-step pattern for structured LLM outputs
  (generate, then repair if needed), instead of assuming the first
  attempt is always valid.
- `src/schema.py` — defines the business contract (`answer`, `confidence`,
  `actions`, with an optional `reasoning`) independently from JSON syntax
  validity, and validates it. It also defines `fallback_response`, a safe
  degraded response used when the model's output doesn't satisfy the
  contract even after the repair attempt.
- `src/metrics.py` — computes `estimated_cost_usd` from a static pricing
  table and appends one row per execution to `metrics/metrics.csv`.

`run_query.py` wires these together: it never trusts the model's output
blindly — it validates the parsed JSON against the contract, and only
passes it through if valid; otherwise it substitutes the fallback response
and still logs the execution (with `valid_json=False`) so failures are
auditable, not silent.

## Prompting technique: chosen by measurement, not by assumption

Prompt engineering technique selection is treated as an empirical
question rather than a design-time assumption: *design multiple prompt
variants, measure them on tokens/latency/quality, and only then choose
one* — instead of picking a technique upfront and justifying it after the
fact. `src/compare_prompt_techniques.py`
implements exactly that workflow as real, reusable code (not a throwaway
script): it defines three **pure** prompt variants in `prompts/variants/`
(zero-shot, few-shot, chain-of-thought — never combined, so each result
can be attributed to one technique) and runs all three against the same
5-question test set covering every action in the catalog, logging every
result to `metrics/prompt_comparison.csv`.

### Real results (`gpt-4o-mini`, 15 calls, 3 variants × 5 questions)

| variant | accuracy | avg tokens | avg latency (ms) | total cost (USD) |
|---|---|---|---|---|
| chain_of_thought | 100% | 553.6 | 1498.9 | 0.000633 |
| few_shot | 100% | 703.0 | 1222.3 | 0.000665 |
| zero_shot | 100% | 430.4 | 1605.9 | 0.000455 |

All three variants tied on accuracy against this test set — 5 questions is
too small a sample to separate them on correctness alone. Where they do
separate is cost: zero-shot is ~35% cheaper than few-shot and ~22% cheaper
than chain-of-thought, simply because it carries no examples and no
reasoning trace.

### Why chain-of-thought was chosen despite not being the cheapest

With accuracy tied, the deciding factor was **auditability**, not raw
token cost. Chain-of-thought is the only variant that returns a
`reasoning` field — a short list of the steps the model followed before
picking `confidence`/`actions`. In a Help Desk product, a human agent
reviewing a borderline case (low confidence, an escalation) needs to see
*why* the assistant reached that conclusion, not just the conclusion
itself. The cost premium over zero-shot is marginal in absolute terms
(~$0.0002 per additional 1,000 questions) and smaller than few-shot's
premium, while few-shot's extra tokens (the worked examples) bought no
measurable accuracy improvement on this test set. This follows a general
engineering principle: don't reach for the most expensive option by
default, but also don't optimize for cost when it trades away something
the product actually needs — here, that's the audit trail, not raw
correctness.

This choice is reproducible: rerunning `python src/compare_prompt_techniques.py`
regenerates the comparison with the current test set and prompt variants,
appending new rows to `metrics/prompt_comparison.csv` rather than
overwriting the evidence.

## Example metrics (real production runs, `gpt-4o-mini`)

Captured from `metrics/metrics.csv` (using the final chain-of-thought prompt,
`prompts/main_prompt.txt` — no worked examples, only the step-by-step
instruction, which is why `tokens_prompt` here is lower than the few-shot
variant tested in the comparison above):

| question | tokens_prompt | tokens_completion | latency_ms | estimated_cost_usd | valid_json | repaired |
|---|---|---|---|---|---|---|
| "No puedo acceder a mi cuenta..." | 462 | 132 | 2189.5 | $0.0001485 | True | False |
| "che quiero cancelar" | 442 | 82 | 1640.6 | $0.0001155 | True | False |

Both runs produced contract-valid JSON on the first attempt (no repair
call was needed, `repaired=False`).

## Trade-offs

- **Small test set for the technique comparison.** 5 questions per variant
  is enough to expose the cost trade-off but not enough to statistically
  separate accuracy between techniques (all three hit 100%). A production
  decision would want a larger labeled set (on the order of hundreds of
  examples is a common rule of thumb for this kind of evaluation) before
  fully trusting the accuracy numbers; here it was scoped to keep the
  exercise's API spend
  and turnaround small while still being a real, run-it-yourself
  comparison instead of an assumption.
- **`response_format=json_object` + one repair attempt vs. schema drift.**
  Forcing JSON mode guarantees syntactic validity but not business
  validity (a model could still omit a field or invent an action outside
  the catalog). `schema.py` validates the contract as a separate step from
  JSON parsing, and there's still a `fallback_response` path for the case
  where even the repair call doesn't produce a valid contract.
- **Static pricing table.** `estimate_cost_usd` uses hardcoded per-model
  prices instead of querying a pricing API, because OpenAI doesn't expose
  one; this is a known staleness risk documented in the README.
- **No safety/moderation layer yet.** The bonus objective (`src/safety.py`)
  was deliberately deferred to keep the first iteration focused on the
  required flow (JSON contract + metrics + prompting technique + test)
  end-to-end before adding a second layer of defense. A defense-in-depth
  approach (input sanitization, output gating, a moderation contract with
  its own JSON schema) is the standard reference pattern for implementing
  it.

## Next steps

- Add `src/safety.py`: a moderation/fallback layer for adversarial inputs
  (prompt injection attempts inside the "question"), following a
  defense-in-depth pattern — input sanitization, an output gate, and a
  moderation contract (`action`, `reasons`, `severity`) logged separately
  from business metrics.
- Grow the test set in `src/compare_prompt_techniques.py` beyond 5
  questions per variant to get a statistically meaningful accuracy
  comparison, not just a cost comparison.
- Consider prompt caching for the system prompt once it stabilizes, to
  reduce the fixed per-call cost noted above.
