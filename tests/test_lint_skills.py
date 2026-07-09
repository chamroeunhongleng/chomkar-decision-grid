"""Unit tests for tools/lint_skills.py (M13) + a lint of the real skills/commands.

Run:  py -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import lint_skills as ls  # noqa: E402

GOOD_SKILL = """---
description: Use this skill to do one clear specific job for a Chomkar order with a proper trigger sentence.
argument-hint: [order_id]
---
# X
Run `py tools/validate_data.py --order <id>`. Cite the tool output; do not compute in prose.
## Verification checklist
- [ ] tool run
## Boundary
Claude supports; the human approves.
"""


class TestLintSkill(unittest.TestCase):
    def test_good_skill_clean(self):
        self.assertEqual(ls.lint_skill(GOOD_SKILL), [])

    def test_missing_frontmatter(self):
        self.assertIn("missing YAML frontmatter", ls.lint_skill("# no frontmatter"))

    def test_short_description_flagged(self):
        bad = GOOD_SKILL.replace(
            "Use this skill to do one clear specific job for a Chomkar order with a proper trigger sentence.",
            "helps")
        self.assertTrue(any("description" in i for i in ls.lint_skill(bad)))

    def test_missing_tool_reference(self):
        bad = GOOD_SKILL.replace("`py tools/validate_data.py --order <id>`", "some prose")
        self.assertTrue(any("tool" in i for i in ls.lint_skill(bad)))

    def test_missing_boundary(self):
        bad = GOOD_SKILL.replace("Claude supports; the human approves.", "the end")
        self.assertTrue(any("boundary" in i for i in ls.lint_skill(bad)))


class TestRealRepoClean(unittest.TestCase):
    def test_all_skills_and_commands_lint_clean(self):
        results = ls.run()
        self.assertTrue(results, "no skills/commands found")
        bad = {p: v for p, v in results.items() if v}
        self.assertEqual(bad, {}, f"lint issues: {bad}")


if __name__ == "__main__":
    unittest.main()
