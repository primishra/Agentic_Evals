# Tool Use Benchmark

A domain-independent, agent-independent benchmark for whether AI agents select
and use tools correctly — not whether they use a *particular* tool, but
whether they perform the right operation, with the right arguments, at the
right time, with the right consequences. Full design rationale in
[`Agentic_Evals_Tool_Use_Benchmark_Design.md`](../../Agentic_Evals_Tool_Use_Benchmark_Design.md).

**Status: Phase 1 (Specification) + Phase 2 (10-task pilot) + Phase 3 (40
additional tasks) + Phase 4 (50 additional tasks, T51–T100) complete. 100
tasks total in `tasks.json`, covering all 11 benchmark categories.** The
original pilot results in `results/` are from the 10-task pilot run only;
running `run_pilot.py` will execute and score all 100 tasks against both
agents and write updated results (requires `GROQ_API_KEY`). Tracked in
[issue #1](https://github.com/abhineer/Agentic_Evals/issues/1).

In the meantime, [`notebooks/tools/tool_eval_v2.ipynb`](../../notebooks/tools/tool_eval_v2.ipynb)
still covers tool selection precision/recall, success rate, and cost-per-task
on its own smaller, ad-hoc set of generic scenarios (calculator, string
utilities). That notebook and this benchmark are separate efforts: the
notebook's tools can't exercise `CREATE`/`UPDATE`/`DELETE`/`EXECUTE`, side
effects, or risk, which is exactly what this benchmark's domain-grounded tool
set was built to cover.

## What's Here

| File | What it is |
|---|---|
| [`SCHEMA.md`](SCHEMA.md) | The finalized tool/task/trace schema and tool-use failure taxonomy (Phase 1) |
| `store.py` | In-memory retail backend (`RetailStore`) tools operate against |
| `tools.py` | The 10 pilot tools — full schema representation + real implementation, enforcing preconditions against `RetailStore` |
| `tasks.json` | 100 tasks total — the original 10 pilot tasks (T01–T10), 40 Phase 3 additions (T11–T50), and 50 Phase 4 additions (T51–T100) — prompt, seed world state, expected trajectory, stress-test tag |
| `harness/runner.py` | Executes an agent adapter against the task set, produces standard traces |
| `harness/scorer.py` | Scores traces against the mechanically-checkable evaluation dimensions |
| `harness/agents/langchain_groq_agent.py` | Agent A — LangChain `bind_tools` loop, `openai/gpt-oss-120b` |
| `harness/agents/manual_react_agent.py` | Agent B — hand-rolled ReAct prompt loop, raw Groq client, `qwen/qwen3.6-27b` |
| `run_pilot.py` | Runs both agents against every task in `tasks.json` (currently 100), writes `results/` including traces, per-task scores, and aggregate metrics (precision, recall, success rate, tokens per task) |
| `results/` | Traces, scores, and the by-hand spot-check (`results/spot_check.md`) |

## Running It

```bash
pip install -r requirements.txt
export GROQ_API_KEY=...
python run_pilot.py
```

Deterministic (`temperature=0`) but not guaranteed byte-identical across runs
— Groq's `on_demand` tier doesn't guarantee reproducible sampling even at
temperature 0. Three runs during this pilot produced identical mechanical
scores on 18 of 20 (task, agent) pairs and the same qualitative behavior on
the remaining 2 (T07, T08 — see below); nothing in the results changed
conclusions between runs.

## The Tool Set

10 retail/e-commerce tools, covering all 7 primitives from `SCHEMA.md`:

| Tool | Primitive | Side Effect | Risk |
|---|---|---|---|
| `search_products` | SEARCH | NONE | NONE |
| `check_inventory` | READ | NONE | NONE |
| `get_order_status` | READ | NONE | NONE |
| `add_item_to_cart` | CREATE | STATE_CHANGE | LOW |
| `update_shipping_address` | UPDATE | STATE_CHANGE | LOW |
| `cancel_order` | DELETE | STATE_CHANGE | MEDIUM |
| `place_order` | EXECUTE | FINANCIAL_TRANSACTION | HIGH |
| `issue_refund` | EXECUTE | FINANCIAL_TRANSACTION | HIGH |
| `calculate_order_total` | COMPUTE | NONE | NONE |
| `create_support_ticket` | CREATE | RESOURCE_ALLOCATION | LOW |

6 of the 10 carry real side effects, well above the design doc's "at least
2–3" floor — preconditions and risk-awareness need tools that can actually
fail or actually cost something, and `place_order`/`issue_refund` genuinely
mutate a shared `RetailStore` (inventory decrements, orders get created,
refunds get recorded against a real order total).

## The Pilot's 10 Tasks (T01–T10)

Not an even split of Phase 3's ~12 categories — the design doc is explicit
that 10 tasks should stress-test the schema, not pre-enumerate every future
category. Picked instead: 2 baseline correct-selection tasks, 3 wrong-tool
temptations, 1 argument-correctness stress test, 2 sequential-dependency
tasks (one unconditional, one conditional on a precondition), 1 tool-failure
task, and 1 high-risk-action task. Full task definitions with expected
trajectories in `tasks.json`. (T11–T50, the 40 Phase 3 additions, are
described in "Phase 3 Tasks" below.)

## Pilot Results

Both agents run against the identical 10 tasks and identical `RetailStore`
seed data, scored against the mechanical dimensions in `SCHEMA.md` section 7.
Every row below was spot-checked by hand against the raw trace —
see `results/spot_check.md` for the full verification and the manual
verdicts on the two tasks that need judgment rather than mechanical scoring.

### Agent A — LangChain `bind_tools`, `openai/gpt-oss-120b`

```
Tool Selection        90%
Argument Accuracy     90%
Sequence Accuracy     90%
Completeness          90%
Efficiency           100%
Task Completion        8/10 pass, 2 needs manual review (T07, T08)

Failure tags:
- WRONG_TOOL:           1  (T08 — no order-status check before cancel_order)
- MISSING_PREREQUISITE: 1  (T08 — same root cause)
```

### Agent B — manual ReAct loop, `qwen/qwen3.6-27b`

```
Tool Selection         80%
Argument Accuracy      80%
Sequence Accuracy      80%
Completeness           90%
Efficiency              95%
Task Completion         8/10 pass, 2 needs manual review (T07, T08)

Failure tags:
- WRONG_TOOL:            2  (T07 — tried place_order before add_item_to_cart;
                               T08 — same root cause as Agent A)
- UNNECESSARY_CALL:      1  (T07 — the place_order false start)
- MISSING_PREREQUISITE:  1  (T08)
```

Both agents got every task right except T07 (tool failure / recovery) and
T08 (high-risk cancellation) — and both handled those two identically in
substance: correct final answers once the tool rejected the call, but
neither agent proactively checked state before attempting the risky
operation. See `results/spot_check.md` for the full trace-level read of
both.

## Phase 3 Tasks (T11–T50)

40 additional tasks, merged into `tasks.json` alongside the original 10
(T01–T10), taking the live task set to 50 — content-complete against the
real `tools.py`/`store.py` (real SKUs, real preconditions, real enum
values) and fully scorable by `harness/scorer.py`. Getting there required
closing two harness gaps the draft tasks surfaced — a hardcoded
per-task-ID postcondition checker that silently defaulted unscored tasks to
"passed," and a strict-order-only trajectory scorer with no way to express
order-independent or partially-ordered calls — both resolved and validated
(regression-tested against the pilot's recorded traces, golden-trace
simulation of all 40, and explicit reordering tests). Full detail in
`SCHEMA.md` section 9.

**Not yet run against a real agent.** `run_pilot.py` will execute and
score all 100 tasks, but the `results/` directory on disk still only reflects
the original 10-task pilot run — running it again requires `GROQ_API_KEY`
and will overwrite/extend those results.

## Phase 4 Tasks (T51–T100)

50 additional tasks, bringing the benchmark to the 100-task target from
[issue #1](https://github.com/abhineer/Agentic_Evals/issues/1). Extends
every category the pilot and Phase 3 established, with emphasis on:

- **Multi-item complexity**: tasks with 3+ tool calls (T52, T54, T64, T67,
  T87, T96, T97, T100) exercise deeper trajectories than Phase 3's maximum
- **Explicit recovery paths**: T86 gives the agent a concrete fallback
  instruction (cancel → fail → refund) — the first task where correct
  recovery is mechanically checkable without an LLM judge
- **New failure modes**: ORDER_PAID (T80), CART_EXISTS (T81),
  ALL_PRODUCTS_EXIST (T82) — precondition failures the pilot and Phase 3
  never triggered
- **Same-tool-different-args alignment**: T56, T58, T96, T98 call the same
  tool twice with different arguments, stress-testing the scorer's ANY-block
  argument-content matching
- **Richer argument parsing**: "half a dozen" → 6 (T76), "7.5%" → 0.075
  (T78), DUPLICATE_CHARGE enum (T77), partial refund amounts (T74)

**Aggregate metrics** added to `run_pilot.py`: tool invocation precision
(avg efficiency), tool invocation recall (avg tool selection), success rate,
and per-task token usage. Written to `results/summary.json` alongside the
existing per-task scores.

**Category breakdown** (40 new + 10 reused/kept from the pilot = 50 total),
weighted toward categories the pilot showed actually discriminate agent
quality (wrong-tool, argument errors, failure recovery) rather than pure
production-frequency, plus three categories the pilot never touched at all
(no-tool, ambiguous, parallel):

| Category | Total | From pilot | Phase 3 | Phase 4 |
|---|---|---|---|---|
| single-tool | 6 | 1 | 2 | 3 |
| multi-tool | 10 | 1 | 4 | 5 |
| dependency | 10 | 1 | 4 | 5 |
| sequential | 10 | 1 | 4 | 5 |
| wrong-tool | 11 | 3 | 3 | 5 |
| argument errors | 10 | 1 | 4 | 5 |
| tool failures | 8 | 1 | 3 | 4 |
| failure recovery | 11 | 1 | 5 | 5 |
| no-tool | 8 | 0 | 4 | 4 |
| ambiguous | 8 | 0 | 4 | 4 |
| parallel | 8 | 0 | 3 | 5 |
| **Total** | **100** | **10** | **40** | **50** |

**The pilot's "unguarded risk" gap closed without a new tool.** The pilot
flagged that all 10 tools self-protect via preconditions, so no task could
tell "agent checked first" apart from "agent got caught by the tool and
recovered." T35/T36 close this using the *existing* tool set: two orders (or
two paid orders) for the same customer that satisfy `cancel_order`'s or
`issue_refund`'s preconditions equally, where only the agent confirming
which one matches the customer's description — not any tool-level guard —
prevents cancelling/refunding the wrong one. A wrong-target outcome is
mechanically checkable (world state shows the wrong order mutated); the
residual case (right outcome, no verification, i.e. a lucky guess) is what
still needs a judge to read from the trace.

## What This Surfaced

The point of running 10 tasks against 2 independently-built agents before
writing 90 more, per the design doc: find out where the schema/trace format
breaks *before* it's expensive to fix.

**The schema held.** Every field in the tool/task/trace representation
(`SCHEMA.md` sections 1–5) was exercised by at least one pilot task, and
nothing needed to change. Both agents' very different execution paths —
LangChain's native `bind_tools` message loop vs. a hand-rolled text-parsed
ReAct loop on a different model from a different lineage — normalized into
the same trace shape without a framework-specific escape hatch, which was
the actual thing Phase 2 was supposed to prove.

**Recovery and risk awareness genuinely need a judge, not a proxy metric.**
This was a hypothesis in `SCHEMA.md` section 7 going in; the pilot confirmed
it isn't avoidable. A mechanical score for T07 correctly says "the expected
tool call failed" but can't distinguish Agent A's clean, honest response from
Agent B's overshoot-then-recover — both "failed" the same call, only one of
the two needed a second attempt to get there. This has to stay a manual
(Phase 3: LLM-judge) read.

**The task design, not just the agent, decides whether risk awareness is
even testable.** Both agents handled T08 identically: neither checked order
status before attempting `cancel_order`, both got caught by the tool's own
`ORDER_NOT_SHIPPED` precondition, both then answered honestly. That's not
evidence both agents are equally risk-aware — it's evidence this task
doesn't discriminate between "agent that checks first" and "agent that
attempts and handles rejection," because the tool's precondition check
catches the mistake either way. Phase 3 needs at least one high-risk task
where skipping the proactive check actually causes irreversible harm (e.g. a
tool with no precondition guard, so the only thing preventing damage is the
agent's own judgment) — this pilot's tools all self-protect, which was the
right conservative default for a first pilot but understates real risk.

**Running two real agents caught two real bugs in the harness, not the
tools under test.** A non-greedy JSON regex silently truncated nested
arguments, and an unescaped tool name (`` `calculate_order_total` `` with
markdown backticks) broke exact-match tool lookup — both are now fixed and
covered in `results/spot_check.md`. Both would have been invisible running
only one agent, since Agent A's structured `bind_tools` output never goes
through free-text parsing at all. This is the concrete payoff of the design
doc's "test against at least two different agent implementations"
requirement — it's not just about proving portability, it's about exercising
code paths a single well-behaved agent never touches.

**Next:** Phase 3 (25–50 tasks) should keep the wrong-tool-temptation and
sequential-dependency categories that worked cleanly here, add a task whose
risk depends entirely on the agent's own judgment rather than a
tool-enforced precondition, and put a real LLM judge behind Recovery and
Risk Awareness instead of manual review. Tracked in issue #1 (not closed —
spec + pilot is one milestone within it, not the whole scope).
