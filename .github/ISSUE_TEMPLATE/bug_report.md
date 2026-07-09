---
name: Bug report
about: Something in the pipeline, a skill, or a doc is wrong
title: "[BUG] "
labels: bug
assignees: ''
---

**What happened**
A clear description of the incorrect behavior.

**Which stage / tool**
e.g. `tools/calculate_price.py`, the `pricing-analyst` skill, `/run-dera`, a notebook, a report.

**Steps to reproduce**
```bash
py tools/run_dera.py --order order_00X --force
```

**Expected vs actual**
What you expected (cite the formula/parameter in [docs/business_rules.md](../../docs/business_rules.md)
if relevant) vs what you got.

**Environment**
- OS:
- Python version:

**Additional context**
Logs, `outputs/<order_id>/state.json`, or the generated report, if relevant.
