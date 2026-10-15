"""Contrôles des contrats et des références du contenu, indépendants des solutions."""
import json
import re
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT / "content/catalog.json").read_text(encoding="utf-8"))
        cls.exercises = json.loads((ROOT / "content/exercises.json").read_text(encoding="utf-8"))["exercises"]
        cls.skills = {x["id"]: x for x in cls.catalog["skills"]}

    def test_stable_ids_and_domains_are_unambiguous(self):
        self.assertEqual(len(self.skills), len(self.catalog["skills"]))
        domains = {x["id"] for x in self.catalog["domains"]}
        self.assertEqual(len(domains), 8)
        self.assertEqual(domains, {x["domain"] for x in self.skills.values()})
        for item in [*self.catalog["sources"], *self.catalog["domains"], *self.skills.values(), *self.exercises]:
            self.assertRegex(item["id"], r"^[a-z][a-z0-9-]*$")

    def test_source_pages_and_fingerprints_are_credible(self):
        sources = {x["id"]: x for x in self.catalog["sources"]}
        self.assertEqual(len(sources), 2)
        for source in sources.values():
            self.assertEqual(source["kind"], "study_plan")
            self.assertEqual(source["pages"], 14)
            self.assertRegex(source["sha256"], r"^[a-f0-9]{64}$")
        self.assertNotEqual(*[x["sha256"] for x in sources.values()])
        for skill in self.skills.values():
            with self.subTest(skill=skill["id"]):
                self.assertTrue(skill["program_referenced"])
                self.assertFalse(skill["detailed_content_analyzed"])
                self.assertTrue(skill["needs_deepening"])
                self.assertTrue(skill["sources"])
                for ref in skill["sources"]:
                    self.assertIn(ref["source_id"], sources)
                    self.assertTrue(ref["pages"])
                    self.assertEqual(ref["pages"], sorted(set(ref["pages"])))
                    self.assertTrue(all(type(p) is int and 1 <= p <= sources[ref["source_id"]]["pages"] for p in ref["pages"]))

    def test_prerequisites_exist_and_have_no_cycles(self):
        completed, visiting = set(), set()
        def visit(identifier):
            self.assertIn(identifier, self.skills)
            self.assertNotIn(identifier, visiting, f"Cycle de prérequis : {identifier}")
            if identifier in completed:
                return
            visiting.add(identifier)
            prereqs = self.skills[identifier]["prerequisites"]
            self.assertEqual(len(prereqs), len(set(prereqs)))
            for prerequisite in prereqs:
                visit(prerequisite)
            visiting.remove(identifier)
            completed.add(identifier)
        for identifier in self.skills:
            visit(identifier)

    def test_exercise_skill_references_and_engine_contracts(self):
        expected = {
            "py-normaliser-evenements", "py-total-categories", "py-bilan-qualite", "py-extraire-journal",
            "sql-filtrer-alertes", "sql-joindre-commandes", "sql-agreger-ventes", "sql-debug-classement",
            "schema-atelier", "schema-stocks",
        }
        self.assertEqual({x["id"] for x in self.exercises}, expected)
        self.assertEqual(len(self.exercises), len(expected))
        for exercise in self.exercises:
            with self.subTest(exercise=exercise["id"]):
                self.assertEqual(exercise["validator_id"], exercise["id"])
                self.assertIn(exercise["engine"], {"python", "sql", "schema"})
                self.assertTrue(exercise["skill_ids"])
                for key in ["skill_ids", "prerequisite_skill_ids"]:
                    self.assertEqual(len(exercise[key]), len(set(exercise[key])))
                    self.assertTrue(set(exercise[key]).issubset(self.skills))
                self.assertIn(exercise["domain"], {self.skills[i]["domain"] for i in exercise["skill_ids"]})

    def test_guidance_has_a_contract_and_progressive_hints(self):
        for exercise in self.exercises:
            with self.subTest(exercise=exercise["id"]):
                for key in ["title", "objective", "statement", "input_contract", "starter"]:
                    self.assertIsInstance(exercise[key], str)
                    self.assertTrue(exercise[key].strip())
                for key in ["constraints", "success_criteria", "hints"]:
                    self.assertIsInstance(exercise[key], list)
                    self.assertTrue(all(isinstance(x, str) and x.strip() for x in exercise[key]))
                    self.assertEqual(len(exercise[key]), len(set(exercise[key])))
                self.assertEqual(len(exercise["hints"]), 3)
                self.assertGreaterEqual(exercise["estimated_minutes"], 5)
                self.assertNotIn("solution", exercise)
                self.assertNotIn("expected_results", exercise)
                self.assertIsInstance(exercise["sample"]["content"], str)
                self.assertEqual(Path(exercise["sample"]["filename"]).name, exercise["sample"]["filename"])
                self.assertNotIn("/", exercise["sample"]["filename"])
                self.assertNotIn(chr(92), exercise["sample"]["filename"])

    def test_formats_and_levels_are_real_metadata(self):
        self.assertEqual({x["kind"] for x in self.exercises}, {"targeted", "challenge", "professional", "debug", "mini_project"})
        self.assertEqual({x["level"] for x in self.exercises}, {"beginner", "intermediate", "advanced"})
        self.assertEqual(sum(x["engine"] == "python" for x in self.exercises), 4)
        self.assertEqual(sum(x["engine"] == "sql" for x in self.exercises), 4)
        self.assertEqual(sum(x["engine"] == "schema" for x in self.exercises), 2)

    def test_python_starters_compile_without_running_them(self):
        for exercise in self.exercises:
            if exercise["engine"] == "python":
                with self.subTest(exercise=exercise["id"]):
                    compile(exercise["starter"], exercise["id"], "exec")

    def test_samples_are_autonomous_and_parseable(self):
        fixture_tables = {
            "sql-filtrer-alertes": {"alerts"},
            "sql-joindre-commandes": {"customers", "orders"},
            "sql-agreger-ventes": {"sales"},
            "sql-debug-classement": {"scores"},
        }
        for exercise in self.exercises:
            with self.subTest(exercise=exercise["id"]):
                sample = exercise["sample"]
                if sample["filename"].endswith(".json"):
                    self.assertIsInstance(json.loads(sample["content"]), (list, dict))
                if exercise["engine"] == "sql":
                    con = sqlite3.connect(":memory:")
                    try:
                        con.executescript(sample["content"])
                        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                        self.assertEqual(tables, fixture_tables[exercise["id"]])
                        for table in tables:
                            self.assertGreater(con.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0], 0)
                    finally:
                        con.close()

    def test_no_personal_paths_or_imported_progress_in_public_content(self):
        for filename in ["catalog.json", "exercises.json"]:
            text = (ROOT / "content" / filename).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"(?i)[a-z]:[/\\]users[/\\]")
            self.assertNotIn("apapi", text.lower())
            self.assertNotIn("Learned topics", text)
            self.assertNotIn("Applied topics", text)

    def test_future_domains_are_referenced_without_fake_engines(self):
        referenced = {"math", "nosql", "infrastructure", "ai", "etl"}
        self.assertTrue(referenced.issubset({x["domain"] for x in self.skills.values()}))
        self.assertFalse(referenced.intersection(x["domain"] for x in self.exercises))
        self.assertTrue(all(x["engine"] in {"python", "sql", "schema"} for x in self.exercises))


if __name__ == "__main__":
    unittest.main()
