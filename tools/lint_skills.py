"""lint_skills.py — DERA-ZN M13: validate skills and commands against repo conventions.

Enforces the structure the project relies on (AGENTS.md rules 5, 7, 9):
  Skills   — YAML frontmatter with a substantive `description`; a "cite the tool, don't
             compute" contract; a Verification checklist; and the human-approval boundary.
  Commands — frontmatter with a `description`; reference a tool or a skill.

Deterministic, stdlib-only. Pure lint_* functions are testable. Exit non-zero if any issue.

Run:  py tools/lint_skills.py
"""
import argparse
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _frontmatter(text):
    """Return (frontmatter_str, body_str) or (None, text) if no frontmatter."""
    if not text.startswith("---"):
        return None, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    return parts[1], parts[2]


def _fm_value(fm, key):
    for line in fm.splitlines():
        s = line.strip()
        if s.startswith(key + ":"):
            return s[len(key) + 1:].strip()
    return None


def lint_skill(text):
    """Return a list of issue strings for one SKILL.md content."""
    issues = []
    fm, body = _frontmatter(text)
    if fm is None:
        return ["missing YAML frontmatter"]
    desc = _fm_value(fm, "description")
    if not desc:
        issues.append("frontmatter missing `description`")
    elif len(desc) < 30:
        issues.append("`description` too short (be specific / trigger-first)")
    low = body.lower()
    if "tools/" not in body:
        issues.append("does not reference a tool (`tools/...`) — skills should call deterministic tools")
    if "checklist" not in low:
        issues.append("missing a Verification checklist")
    if "human" not in low or "approv" not in low:
        issues.append("missing the human-approval boundary")
    if ("do not compute" not in low and "never compute" not in low
            and "cite" not in low and "prefer" not in low):
        issues.append("missing the 'cite the tool, don't compute in prose' contract")
    return issues


def lint_command(text):
    """Return a list of issue strings for one command .md content."""
    issues = []
    fm, body = _frontmatter(text)
    if fm is None:
        return ["missing YAML frontmatter"]
    if not _fm_value(fm, "description"):
        issues.append("frontmatter missing `description`")
    if "tools/" not in body and "skill" not in body.lower():
        issues.append("references neither a tool nor a skill")
    return issues


def run(root=None):
    root = root or ROOT
    results = {}
    for path in sorted(glob.glob(os.path.join(root, ".claude", "skills", "*", "SKILL.md"))):
        with open(path, encoding="utf-8") as fh:
            results[os.path.relpath(path, root)] = lint_skill(fh.read())
    for path in sorted(glob.glob(os.path.join(root, ".claude", "commands", "*.md"))):
        with open(path, encoding="utf-8") as fh:
            results[os.path.relpath(path, root)] = lint_command(fh.read())
    return results


def _cli(argv=None):
    argparse.ArgumentParser(description="Lint DERA-ZN skills and commands.").parse_args(argv)
    results = run()
    ok = True
    for path, issues in results.items():
        if issues:
            ok = False
            print(f"XX {path}")
            for i in issues:
                print(f"     - {i}")
        else:
            print(f"ok {path}")
    n_files = len(results)
    n_bad = sum(1 for v in results.values() if v)
    print(f"\n{n_files - n_bad}/{n_files} clean.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
