# Agentic Evals — Repository Deep Dive

> Reference document for understanding the full repo structure, components, data flows, and current state. Intended for future improvement planning.

---

## 1. Project Purpose

This repo is a **practical evaluation toolkit for production AI agents**. It answers the question: "Is my agent reliable enough for production?" — not with vibes, but with concrete, reproducible experiments across seven evaluation areas:

| Area                      | Status                                     |
| ------------------------- | ------------------------------------------ |
| Prompt Evaluation         | Notebook complete                          |
| Tool Calling              | Notebook + standalone benchmark (100 tasks) |
| RAG                       | Notebook complete                          |
| Planning & Reasoning      | Notebook complete                          |
| Memory                    | Notebook complete                          |
| Synthetic Data Generation | Notebook complete                          |
| Error Analysis            | Notebook complete                          |

The overarching philosophy is an **evaluation loop**: build → test → evaluate → error analysis → fix → re-evaluate → production → feed production traces back into eval.

---

## 2. Repository Structure

```
Agentic_Evals/
├── README.md                    # Project overview, quick start
├── ROADMAP.md                   # Q3/Q4 2026 plans
├── CONTRIBUTING.md              # Contribution guidelines
├── LICENSE
│
├── docs/
│   ├── resources.md             # Curated papers behind each eval area
│   └── images/                  # Architecture diagrams
│
├── notebooks/                   # Self-contained Colab-ready evaluation notebooks
│   ├── prompt/                  # Prompt optimization evaluation
│   ├── tools/                   # Tool-calling precision/recall
│   ├── rag/                     # RAG retrieval + generation quality
│   ├── planning/                # ReAct vs Direct reasoning comparison
│   ├── memory/                  # Key-value memory recall/update/forget
│   ├── synthetic_data/          # Dimension-based eval dataset generation
│   └── error_analysis/          # Failure taxonomy → prompt improvement loop
│
└── benchmarks/
    └── tool_use/                # Standalone, reproducible tool-use benchmark
        ├── SCHEMA.md            # Formal schema + failure taxonomy
        ├── store.py             # In-memory RetailStore (mock backend)
        ├── tools.py             # 10 retail tools with schemas + implementations
        ├── tasks.json           # 50 tasks (10 pilot + 40 Phase 3)
        ├── run_pilot.py         # Entry point: runs agents, writes results
        ├── harness/
        │   ├── runner.py        # Task runner (seeds store, captures traces)
        │   ├── scorer.py        # Mechanical scoring across 10 dimensions
        │   └── agents/
        │       ├── langchain_groq_agent.py   # Agent A (LangChain bind_tools)
        │       └── manual_react_agent.py     # Agent B (hand-rolled ReAct)
        └── results/
            ├── *_traces.json    # Raw execution traces
            ├── *_scores.json    # Per-task scores
            ├── all_scores.json  # Combined scores for both agents
            └── spot_check.md    # Hand-verified analysis of all 20 pilot pairs
```

---

## 3. Notebooks — Detailed Breakdown

### 3.1 Prompt Evaluation (`prompt_evals_v2.ipynb`)

- **Domain**: Physics education (common misconceptions)
- **LLM**: Groq `llama-3.1-8b-instant`, temperature=0.3
- **Dataset**: 10 synthetic physics Q&A pairs with expected key points and nuance traps
- **Metrics**: Accuracy, Clarity, Completeness — all binary (0/1) via LLM-as-judge
- **Pattern**: Agent factory `physics_teacher(system_prompt, question)` — compares performance across prompt variations
- **Key insight**: Shows how different system prompts affect the same model's factual correctness

### 3.2 Tool Calling Evaluation (`tool_eval_v2.ipynb`)

- **Domain**: Generic utilities (calculator, sqrt, temp converter, string reverser, word counter, date info)
- **LLM**: LangChain + ChatGroq
- **Metrics**: Tool Invocation Precision/Recall, Avg Tool Calls per Task, Tool Success Rate, Cost per Successful Task
- **Pattern**: Uses LangChain's `create_tool_calling_agent` with `@tool` decorated functions
- **Note**: This is the **notebook** eval — separate from the standalone benchmark below. These tools are simpler (no side effects, no risk, no preconditions)

### 3.3 RAG Evaluation (`rag_evals_v1.ipynb`)

- **Domain**: Physics tutoring with a 12-document knowledge corpus
- **LLM**: Groq `llama-3.1-8b-instant`, Sentence Transformers for embeddings
- **Metrics**: Context Relevance (0-1), Answer Groundedness (0-1), Answer Correctness (0-1)
- **Scoring**: Binary LLM-as-judge per metric
- **Pattern**: Separate retrieval → generation pipeline; evaluator checks retrieval quality, hallucination, and factual accuracy independently
- **Reference paper**: Ragas (arXiv:2309.15217)

### 3.4 Planning Evaluation (`planning_evals.ipynb`)

- **Domain**: Fact-based questions requiring calculation or lookup (Earth radius, light speed, etc.)
- **LLM**: Groq `llama-3.1-8b-instant` (agent), `llama-3.3-70b-versatile` (judge)
- **Metrics**: Answer Correctness, Reasoning Quality, Tool Use Appropriateness — binary LLM-as-judge
- **Pattern**: Compares **Direct** (answer immediately) vs **ReAct** (Thought → Action → Observation loop)
- **Tools**: `calculator()` and `search()` with a predefined knowledge base
- **Reference paper**: ReAct (arXiv:2210.03629)

### 3.5 Memory Evaluation (`memory_evals.ipynb`)

- **Domain**: Multi-turn conversations with explicit key-value memory
- **LLM**: Groq `llama-3.1-8b-instant`, temperature=0.2
- **Metrics**: Memory Recall Accuracy (MRA), Memory Update Correctness (MUC), Forgetting Appropriateness (FAS)
- **Pattern**: Explicit `dict` memory store; agent emits `Memory Action: SET key=value`, `DELETE key`, or `NONE` each turn
- **Key insight**: Tests whether agents actually retain, update, and forget facts correctly — not just whether they can parrot back info
- **Reference paper**: LoCoMo (arXiv:2402.17753)

### 3.6 Synthetic Data Generation (`synthetic_data_gen.ipynb`)

- **Domain**: E-commerce product search queries
- **LLM**: Groq `llama-3.1-8b-instant`, temperature=0.7 (higher for diversity)
- **Approach**: Dimension-based generation — define axes (category, price intent, specificity, user context, urgency, failure modes), create manual seed tuples for coverage, then use LLM to generate natural language phrasings
- **Key insight**: Separates combinatorial logic from linguistic variation; avoids the repetitive patterns you get from naive "generate 100 examples" prompting

### 3.7 Error Analysis (`error_analysis_v1.ipynb`)

- **Domain**: Product description generation from titles
- **LLM**: Groq `llama-3.1-8b-instant`
- **Process**: 6-step loop — define criteria → build baseline agent → collect expert feedback → extract failure modes → analyze frequency → improve prompt
- **Metrics**: Factual Consistency, No Hallucinations, Clarity, Appropriate Tone, Completeness
- **Key insight**: This is the **meta-notebook** — it shows how to go from "my agent fails sometimes" to "here's exactly what fails, how often, and what prompt change fixes it"

---

## 4. Tool Use Benchmark — Deep Dive

The most significant piece beyond the notebooks. A domain-independent, agent-independent benchmark where the goal is comparing *any* agent's tool-calling behavior against a fixed task set.

### 4.1 Architecture

```
tasks.json ──┐
             ├──► runner.py ──► agent.run(store, prompt)
store.py ────┘        │              │
  (RetailStore)       │         tool calls mutate store
                      ▼              │
                  trace.json ◄───────┘
                      │       (steps + world_state_before/after)
                      ▼
                  scorer.py ──► scores.json
                      │
                  SCHEMA.md (defines dimensions, taxonomy)
```

### 4.2 The Mock Backend (`store.py`)

`RetailStore` — an in-memory dataclass holding `products`, `inventory`, `carts`, `orders`, `tickets`. Each task seeds a fresh store from its `seed` field. Tool calls mutate this store, and before/after snapshots let the scorer verify postconditions independently of what the agent *claims* happened.

**Default product catalog:**

| SKU      | Product                     | Price   | Category    |
| -------- | --------------------------- | ------- | ----------- |
| SKU-1001 | Wireless Earbuds Pro        | $79.99  | audio       |
| SKU-2004 | Noise Cancelling Headphones | $149.99 | audio       |
| SKU-3001 | USB-C Charging Cable        | $12.99  | accessories |
| SKU-4002 | Bluetooth Speaker Mini      | $39.99  | audio       |
| SKU-5003 | Smartwatch Series 3         | $199.99 | wearables   |

### 4.3 Tool Set (`tools.py`)

10 retail tools covering all 7 primitives, with real precondition enforcement:

| Tool                        | Primitive | Side Effect           | Risk   | Preconditions                                     |
| --------------------------- | --------- | --------------------- | ------ | ------------------------------------------------- |
| `search_products`         | SEARCH    | NONE                  | NONE   | —                                                |
| `check_inventory`         | READ      | NONE                  | NONE   | PRODUCT_EXISTS                                    |
| `get_order_status`        | READ      | NONE                  | NONE   | ORDER_EXISTS                                      |
| `add_item_to_cart`        | CREATE    | STATE_CHANGE          | LOW    | CART_EXISTS, PRODUCT_EXISTS, SUFFICIENT_INVENTORY |
| `update_shipping_address` | UPDATE    | STATE_CHANGE          | LOW    | ORDER_EXISTS, ORDER_NOT_SHIPPED                   |
| `cancel_order`            | DELETE    | STATE_CHANGE          | MEDIUM | ORDER_EXISTS, ORDER_NOT_SHIPPED                   |
| `place_order`             | EXECUTE   | FINANCIAL_TRANSACTION | HIGH   | CART_EXISTS, CART_NOT_EMPTY, CUSTOMER_VALID       |
| `issue_refund`            | EXECUTE   | FINANCIAL_TRANSACTION | HIGH   | ORDER_EXISTS, ORDER_PAID                          |
| `calculate_order_total`   | COMPUTE   | NONE                  | NONE   | —                                                |
| `create_support_ticket`   | CREATE    | RESOURCE_ALLOCATION   | LOW    | —                                                |

Each tool has two representations:

1. **`TOOL_SCHEMAS[name]`** — full JSON schema (primitive, domain, inputs/outputs, side effects, risk, pre/postconditions)
2. **`TOOL_IMPLS[name]`** — real Python function `(store, **kwargs) -> dict` that enforces preconditions and mutates the store

`build_langchain_tools(store)` wraps implementations as LangChain tools for Agent A. Agent B uses `call_tool(store, name, args)` directly.

### 4.4 Task Set (`tasks.json`)

100 tasks total (10 pilot T01–T10, 40 Phase 3 T11–T50, 50 Phase 4 T51–T100). Each task specifies:

- `task_id`, `type`, `description`, `stress_tests` (what failure mode it targets)
- `prompt` — the natural language request given to the agent
- `seed` — initial world state for `RetailStore.from_seed()`
- `expected_trajectory` — ordered list of expected `{tool_name, arguments}` calls
- `expected_postconditions` — what should be true in world state after
- `trajectory_order` — `STRICT` (default), `ANY`, or `PARTIAL`
- `distractor_tools` (optional) — tools that are tempting but wrong
- `requires_llm_judge` (optional) — dimensions 7 & 9 need manual review

**Category distribution (100 tasks):**

| Category         | Count | What it tests                             |
| ---------------- | ----- | ----------------------------------------- |
| single-tool      | 6     | Basic correct selection                   |
| multi-tool       | 10    | Multiple tools for one request            |
| dependency       | 10    | Output of one tool feeds into next        |
| sequential       | 10    | Ordered multi-step operations             |
| wrong-tool       | 11    | Resisting distractor tools                |
| argument errors  | 10    | Getting values/types/enums right          |
| tool failures    | 8     | Handling precondition failures            |
| failure recovery | 11    | Adapting after tool errors                |
| no-tool          | 8     | Recognizing when no tool is needed        |
| ambiguous        | 8     | Asking for clarification vs guessing      |
| parallel         | 8     | Independent calls with no data dependency |

### 4.5 Scoring (`scorer.py`)

10 evaluation dimensions, most mechanically scored:

| #  | Dimension             | How scored                                                                    |
| -- | --------------------- | ----------------------------------------------------------------------------- |
| 1  | Tool selection        | Compare called tool(s) vs `expected_trajectory`                             |
| 2  | Argument accuracy     | Compare arg values per step (float-tolerant)                                  |
| 3  | Tool execution        | Read `result.status` from trace                                             |
| 4  | Sequence accuracy     | Step order vs `expected_trajectory` (respects `trajectory_order`)         |
| 5  | Completeness          | Did every expected step occur?                                                |
| 6  | Efficiency            | Any extra calls not in expected trajectory?                                   |
| 7  | Recovery              | **Needs LLM judge** — detecting silent give-up or hallucinated success |
| 8  | Side-effect awareness | Partly mechanical (precondition checks), partly judgment                      |
| 9  | Risk awareness        | **Needs LLM judge** — did agent check before risky operations?         |
| 10 | Task completion       | Postconditions met in `world_state_after`                                   |

**Trajectory alignment** supports `STRICT`, `ANY`, and `PARTIAL` ordering via block-based permutation matching. Postconditions use a generic `POSTCONDITION_PREDICATES` registry (no more per-task-ID hardcoding).

### 4.6 Agent Adapters

Two deliberately different implementations to prove schema/trace format generality:

**Agent A** — `langchain_groq_agent.py`

- LangChain `bind_tools` message loop
- Model: `openai/gpt-oss-120b` via Groq
- Framework-native tool calling (structured tool-call messages)

**Agent B** — `manual_react_agent.py`

- Hand-rolled ReAct prompt loop, raw Groq client, no LangChain
- Model: `qwen/qwen3.6-27b`
- Text parsing (`Action: tool_name\nAction Input: {json}`)
- Brace-balanced JSON parser (handles nested arguments)
- Rate-limit retry logic for free-tier Groq

Both produce the same standard trace format, proving agent-independence. Both
now track per-task token usage (prompt + completion tokens) for cost analysis.

### 4.7 Pilot Results (10-task run)

| Dimension         | Agent A   | Agent B   |
| ----------------- | --------- | --------- |
| Tool Selection    | 90%       | 80%       |
| Argument Accuracy | 90%       | 80%       |
| Sequence Accuracy | 90%       | 80%       |
| Completeness      | 90%       | 90%       |
| Efficiency        | 100%      | 95%       |
| Task Completion   | 8/10 pass | 8/10 pass |

Both failed on T07 (tool failure/recovery) and T08 (high-risk cancellation) — neither checked state before attempting risky operations.

**Key findings from the pilot:**

1. The schema held — every field was exercised, nothing needed to change
2. Both agents' different execution paths normalized into the same trace shape
3. Risk awareness gap: neither agent proactively checked preconditions — both relied on tool-level guards
4. Two harness bugs caught and fixed: non-greedy JSON regex and markdown-wrapped tool names

---

## 5. Failure Taxonomy (Tool-Use Scoped)

```
WRONG_TOOL              Called wrong tool for the task
WRONG_ARGUMENTS         Right tool, wrong/missing/malformed arguments
MISSING_PREREQUISITE    Called tool before required precondition satisfied
UNNECESSARY_CALL        Called a tool not needed for the task
NO_RECOVERY             Tool failed and agent didn't adapt (silent give-up, hallucinated success, identical retry)
IGNORED_SIDE_EFFECT_RISK  Invoked risky tool without appropriate caution
```

---

## 6. Tech Stack

| Component          | Technology                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------------ |
| LLM Provider       | **Groq** (all notebooks + benchmark)                                                 |
| Models (notebooks) | `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`                                      |
| Models (benchmark) | `openai/gpt-oss-120b` (Agent A), `qwen/qwen3.6-27b` (Agent B)                          |
| Agent Framework    | LangChain (Agent A, notebook tool eval), raw Groq client (Agent B)                         |
| Embeddings         | Sentence Transformers (RAG notebook)                                                       |
| Scoring            | LLM-as-judge (notebooks), mechanical + manual (benchmark)                                  |
| Language           | Python 3.8+                                                                                |
| Dependencies       | `langchain-core`, `langchain-groq`, `groq`, `pydantic`, `pandas`, `matplotlib` |
| Environment        | Google Colab (notebooks), local (benchmark)                                                |

---

## 7. Cross-Cutting Patterns

| Pattern                              | Where used                                                                     |
| ------------------------------------ | ------------------------------------------------------------------------------ |
| **LLM-as-Judge**               | 6/7 notebooks; binary 0/1 scoring with structured extraction                   |
| **Binary Metrics**             | Most evals use pass/fail; tool eval uses precision/recall                      |
| **Synthetic Datasets**         | All use structured, non-production data for reproducibility                    |
| **Temperature Control**        | 0 for deterministic scoring, 0.2-0.3 for reproducibility, 0.7 for diversity    |
| **World-State Snapshots**      | Benchmark verifies postconditions against actual store state, not agent claims |
| **Agent-Independent Traces**   | Standard trace format decouples agent framework from scoring                   |
| **Failure-Mode-Driven Design** | Tasks are designed around specific failure modes, not random coverage          |

---

## 8. Current State & Known Gaps

### What's done

- 7 self-contained evaluation notebooks covering prompt, tools, RAG, planning, memory, synthetic data, error analysis
- Tool use benchmark: schema finalized, 100 tasks authored (Phase 4 complete), harness works, 10-task pilot run verified
- Aggregate metrics: tool invocation precision/recall, success rate, tokens per task
- Token tracking in both agent adapters
- Postcondition checker generalized (no more per-task-ID hardcoding)
- Trajectory alignment supports STRICT/ANY/PARTIAL ordering

### What's not done yet

- **100 tasks not yet run against real agents** — `results/` only reflects the 10-task pilot
- **No LLM judge** — dimensions 7 (Recovery) and 9 (Risk awareness) still need manual review (26 tasks flagged NEEDS_REVIEW)
- **No agent trajectory evaluation** — planned for Q3 2026 (issue #2)
- **No safety evaluation** — planned for Q4 2026 (issue #4)
- **No production trace evaluation** — planned Q4 2026
- **No cost/latency evaluation** — planned Q4 2026
- **No memory benchmark** — only a notebook, dedicated benchmark planned Q4 2026
- **No community benchmarks or leaderboard** — future roadmap item

### Known issues surfaced by the pilot

1. **Risk awareness is indistinguishable with self-protecting tools** — all 10 tools enforce their own preconditions, so "agent checked first" vs "tool caught it" look the same. T35/T36 (Phase 3) partially close this with ambiguous-target scenarios
2. **Groq free-tier rate limits** — the manual ReAct agent hits 8000 TPM budget running 10+ tasks back-to-back
3. **Temperature 0 doesn't guarantee reproducibility** on Groq's `on_demand` tier

---

## 9. Key Papers & References

| Area        | Paper                                        | How it's used                                                  |
| ----------- | -------------------------------------------- | -------------------------------------------------------------- |
| RAG         | Ragas (arXiv:2309.15217)                     | Context precision/recall, faithfulness metrics in RAG notebook |
| Tool Use    | Berkeley Function-Calling Leaderboard (BFCL) | Direction for tool_use benchmark                               |
| Planning    | ReAct (arXiv:2210.03629)                     | Thought→Action→Observation loop in planning notebook         |
| Memory      | LoCoMo (arXiv:2402.17753)                    | Multi-session recall/update/forgetting in memory notebook      |
| Safety      | InjecAgent (arXiv:2403.02691)                | Background for planned safety benchmark                        |
| Judging     | MT-Bench (arXiv:2306.05685)                  | LLM-as-judge pattern used across notebooks                     |
| Methodology | Hamel Husain's eval posts                    | Error analysis workflow in error_analysis notebook             |
| Benchmarks  | AgentBench (arXiv:2308.03688)                | Trajectory evaluation direction                                |

---

## 10. How to Run

### Notebooks

```bash
# Each notebook is Colab-ready, or run locally:
pip install groq langchain langchain-groq pandas matplotlib
# Set GROQ_API_KEY, open any notebook
```

### Tool Use Benchmark

```bash
cd benchmarks/tool_use
pip install -r requirements.txt   # langchain-core, langchain-groq, groq, pydantic
export GROQ_API_KEY=...
python run_pilot.py               # Runs both agents against all 100 tasks, writes results/
```

---

## 11. For Future Improvements — Areas to Consider

1. **Run the full 100-task benchmark** — all tasks authored, harness ready, needs `GROQ_API_KEY`
2. **Implement LLM judge** — automate dimensions 7 and 9 scoring instead of manual spot-checks
3. **Add more agent adapters** — test OpenAI function calling, Anthropic tool use, etc.
4. **Memory benchmark** — graduate from notebook to standalone reproducible benchmark
5. **Safety evaluation** — InjecAgent-style indirect prompt injection testing
6. **Production trace evaluation** — feed real agent traces back into the eval loop
7. **Cross-model comparison** — leaderboard across models on the same task set
8. **CI integration** — automated eval runs on agent code changes
