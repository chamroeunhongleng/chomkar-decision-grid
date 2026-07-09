---
name: Feature request
about: Propose a new capability, tool, skill, or dataset extension
title: "[FEATURE] "
labels: enhancement
assignees: ''
---

**Problem**
What's missing or awkward today? (e.g. a new commodity, a new risk factor, a new report section)

**Proposed solution**
What you'd add, and where it belongs:
- New/changed math → `tools/` (+ tests)
- New/changed reasoning → `.claude/skills/`
- New/changed parameter → `docs/business_rules.md` + `tools/config.py`
- New/changed data → `data/` + [docs/data_dictionary.md](../../docs/data_dictionary.md)

**Alternatives considered**
Any other approach you thought about and why you didn't pick it.

**Does this touch a business parameter or formula?**
If yes, per [AGENTS.md](../../AGENTS.md) this needs an explicit human decision — say what the current
value is and what you're proposing instead.
