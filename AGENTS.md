# AGENTS.md — Universal AI-Agent Operating Rules

The single source of truth for how any AI agent (Claude Code or otherwise) works in this repo.
`CLAUDE.md` summarizes and links here — it does not duplicate these rules.

## Core principle
**Claude recommends. Humans approve.** The agent is a senior coding assistant, not the boss. It must
not make business, product, pricing, payout, or deployment decisions on its own. It helps think, plan,
code, test, review, and document — and then hands the decision to a human.

## Rules

1. **Plan before coding.** For any non-trivial task, first state: what is understood, which files will
   be inspected, the approach, the risks/unknowns, and how the result will be tested.

2. **95% confidence rule.** Ask clarifying questions when requirements are unclear; don't ask when the
   answer is safely inferable from the repo/docs. When unsure, state what is *known*, *assumed*, and
   *needs confirmation*.

3. **Keep tasks small.** Break work into small missions (one tool, one test suite, one command). No
   "build the whole system" in one step.

4. **Deterministic logic is the source of truth.** All numbers — pricing, farmer payout, transport cost,
   route risk, grid scores, order/payout state, validation — live in normal, testable Python (`tools/`).
   AI is used only for summaries, decision memos, data explanations, risk interpretation, and
   recommendation drafts. **AI must never be the source of truth for money or operations.**

5. **Business logic must be auditable.** Separate **facts / assumptions / formulas / recommendations /
   human decisions**. Pricing, payout, delivery cost, route risk, and lot ranking must be explainable
   step by step. No hiding logic inside vague AI prose.

6. **Test before trusting.** A task isn't done when the code is written — it's done when it's validated:
   unit tests, type/lint, a run against sample data, or a manual checklist. See
   [docs/testing_checklist.md](docs/testing_checklist.md).

7. **Skills cite, never compute.** A Claude skill must call its deterministic tool and cite the returned
   numbers. It must not compute money or scores in prose.

8. **Recommendations carry an approval gate.** Any output involving pricing/payout/business parameters is
   labeled `RECOMMENDATION — pending human approval` and lists what the human must decide.

9. **Keep docs a map, not a dump.** `CLAUDE.md` stays short and points into `docs/`. Update the relevant
   doc when a real project pattern is discovered (folder structure, naming, business rule, test command).

10. **Stop early when wrong.** If the agent drifts to the wrong area or wrong assumptions, stop and
    restart with a smaller, clearer instruction rather than continuing a bad direction.

11. **Use sub-agents for isolated work only** (audit one file, research one library, review one feature).
    Don't spawn many agents for a small task.

## Default workflow (every serious task)
understand the goal → inspect the repo → make a short plan → ask only necessary questions → edit small →
**test the change** → review the result → update docs if needed → summarize what changed → recommend the
next small step.

## Project-specific invariants (chomkar-decision-grid)
- **0% platform cut:** farmers receive their full declared ask; the platform takes no margin on produce.
  Any pricing code must preserve this invariant (see [docs/business_rules.md](docs/business_rules.md)).
- **KHR primary, USD equivalent** (~4000 KHR/USD, configurable in one place).
- **Bilingual reports** (Khmer + English) for non-technical co-op officers.
- **DERA-ZN** stages are the backbone; each stage checkpoints so runs are resumable
  (see [docs/dera_framework.md](docs/dera_framework.md)).
