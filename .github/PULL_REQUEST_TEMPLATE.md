## What this changes and why

<!-- The "why" matters more than the "what" here — see CONTRIBUTING.md. -->

## Checklist

- [ ] `py -m unittest discover -s tests -v` passes
- [ ] `py tools/lint_skills.py` passes (if you touched `.claude/skills/` or `.claude/commands/`)
- [ ] `py tools/run_dera.py --order order_001 --force` still ends in
      `RECOMMENDATION - pending human approval` with `audit: PASSED` (if you touched `tools/`)
- [ ] Added/updated a unit test for any change to `tools/`
- [ ] Updated the matching doc (`docs/business_rules.md`, `docs/data_dictionary.md`, or
      `docs/dera_framework.md`) if a formula, parameter, column, or convention changed
- [ ] No money/score figure is computed in a skill or report prose — only cited from a tool's output

## Does this change a business parameter or formula?

- [ ] No
- [ ] Yes — described below, flagged as a **human decision** (see [AGENTS.md](../AGENTS.md) rule 8)

<!-- If yes: current value, proposed value, and the evidence/reasoning behind the change. -->
