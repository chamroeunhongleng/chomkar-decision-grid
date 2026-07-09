# Contributing

Thanks for considering a contribution to **chomkar-decision-grid**. This is a synthetic-data
decision-intelligence project (see [README.md](README.md) and [CLAUDE.md](CLAUDE.md)) — the rules
below exist to keep every number in it auditable.

## Ground rules

1. **Deterministic core, AI shell.** All money/score math lives in stdlib-only Python under `tools/`.
   If you add or change a calculation, it belongs in `tools/`, not in a Claude skill or a notebook.
2. **Skills cite, never compute.** `.claude/skills/*/SKILL.md` must call a tool and cite its output —
   never compute a price, payout, or score in prose. `tools/lint_skills.py` enforces the structural
   half of this; use judgment for the rest.
3. **Business rules are human-owned.** [docs/business_rules.md](docs/business_rules.md) is the source
   of truth for formulas and parameters; `tools/config.py` is its code mirror — keep them in sync. A
   PR that changes a formula or parameter should say so explicitly, not bury it in a refactor.
4. **The 0%-cut invariant never regresses.** Farmer payout must always equal
   `Σ(farmer's ask price × allocated kg)`. Handling fees and spoilage buffers are platform-borne, added
   on top — never deducted from a farmer's payout. This is asserted in unit tests, the audit gate, and
   CI; a PR that breaks it will fail CI by design.
5. **Notebooks are experiments, not sources of truth.** They import `tools/` functions; they don't
   reimplement the math.

Full agent/human operating rules: [AGENTS.md](AGENTS.md).

## Setting up

Requires Python 3.10+ (the engine is stdlib-only — no third-party deps for `tools/`). On Windows use
the `py` launcher; on macOS/Linux/CI use `python`.

```bash
git clone https://github.com/chamroeunhongleng/chomkar-decision-grid.git
cd chomkar-decision-grid
py -m unittest discover -s tests -v   # confirm the baseline passes before you change anything
```

Notebooks are optional and need extra packages only if you want to re-execute them:

```bash
pip install nbformat nbclient ipykernel
```

## Making a change

1. **Keep it small.** One tool, one test file, one command/skill per change where possible.
2. **Write or update a test** in `tests/` for any change to `tools/` — especially anything touching
   pricing, payout, route risk, or grid scoring.
3. **Update the matching doc** if you touch a formula, parameter, column, or convention:
   - `docs/business_rules.md` — formulas/parameters
   - `docs/data_dictionary.md` — CSV schema
   - `docs/dera_framework.md` — stage/grid/resume contract
4. **Run the full local check before opening a PR:**
   ```bash
   py scripts/generate_synthetic_data.py   # must stay byte-identical (determinism)
   py -m unittest discover -s tests -v
   py tools/lint_skills.py
   py tools/run_dera.py --order order_001 --force
   ```
5. Open a PR describing **why**, not just what — especially for anything touching business parameters,
   per rule 3 above.

## What CI checks

See [.github/workflows/ci.yml](.github/workflows/ci.yml): unit tests, the skill/command lint, a Detect
smoke check, a full audited `run_dera.py` end-to-end run, notebook execution, and an artifact-invariant
check (status, audit pass, 0%-cut payout, price under cap). All of it must stay green.

## Reporting bugs / proposing features

Use the issue templates. All data in this repo is synthetic, so there's no sensitive-data disclosure
path to worry about — regular issues are fine for everything, including anything you'd otherwise treat
as a security report.
