"""Generator tests; every test file stays in project/work/test-datasets-* ."""
import csv
from contextlib import closing
from datetime import datetime
import json
from pathlib import Path
import random
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from lab.datasets import GENERATORS, KINDS, PROJECT_ROOT, generate

PRINCIPAL = {"commerce": "orders", "logistics": "shipments", "events": "events", "imperfect": "raw_orders"}


class DatasetTests(unittest.TestCase):
    def setUp(self):
        work = PROJECT_ROOT / "work"
        work.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="test-datasets-", dir=work)
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def dbpath(self, name):
        return self.root / name / "lab.sqlite"

    def dump(self, path):
        with closing(sqlite3.connect(path)) as db:
            return "\n".join(db.iterdump())

    def test_reproducible_databases_and_exports(self):
        for kind in KINDS:
            for dirty in (False, True):
                with self.subTest(kind=kind, anomalies=dirty):
                    a, b = self.dbpath("a"), self.dbpath("b")
                    self.assertEqual(generate(a, kind, 456, 31, dirty), generate(b, kind, 456, 31, dirty))
                    self.assertEqual(self.dump(a), self.dump(b))
                    for filename in ("source.csv", "source.json"):
                        self.assertEqual((a.parent / filename).read_bytes(), (b.parent / filename).read_bytes())
                    generate(b, kind, 457, 31, dirty)
                    self.assertNotEqual(self.dump(a), self.dump(b))

    def test_sizes_foreign_keys_and_integrity(self):
        for kind in KINDS:
            for size in (0, 1, 27):
                for seed in (0, 2025, 2147483647):
                    with self.subTest(kind=kind, size=size, seed=seed):
                        path = self.dbpath("integrity")
                        result = generate(path, kind, seed, size)
                        self.assertEqual(result["anomalies"], [])
                        self.assertEqual(result["tables"][PRINCIPAL[kind]], size)
                        with closing(sqlite3.connect(path)) as db:
                            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
                            for table, count in result["tables"].items():
                                self.assertEqual(db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0], count)
                                if size == 0:
                                    self.assertEqual(count, 0)

    def test_commerce_totals_match_details(self):
        path = self.dbpath("commerce")
        generate(path, "commerce", 8, 73)
        with closing(sqlite3.connect(path)) as db:
            for total, calculated in db.execute("SELECT o.total_amount, SUM(i.line_total) FROM orders o JOIN order_items i ON i.order_id=o.id GROUP BY o.id"):
                self.assertAlmostEqual(total, calculated, places=2)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM order_items WHERE quantity <= 0 OR ABS(line_total-quantity*unit_price)>0.001").fetchone()[0], 0)

    def test_logistics_and_event_chronology(self):
        path = self.dbpath("chronology")
        generate(path, "logistics", 17, 101)
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM shipments WHERE weight_kg<=0 OR delivered_at<shipped_at OR (status='delivered' AND delivered_at IS NULL)").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM tracking_events t JOIN shipments s ON s.id=t.shipment_id WHERE t.event_time<s.shipped_at").fetchone()[0], 0)
        generate(path, "events", 17, 101)
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM events e JOIN sessions s ON s.id=e.session_id WHERE e.occurred_at<s.started_at OR e.duration_ms<0").fetchone()[0], 0)
            previous = {}
            for session, timestamp, properties in db.execute("SELECT session_id, occurred_at, properties_json FROM events ORDER BY id"):
                self.assertTrue(json.loads(properties)["synthetic"])
                datetime.fromisoformat(timestamp)
                if session in previous:
                    self.assertGreater(timestamp, previous[session])
                previous[session] = timestamp

    def test_imperfect_clean_baseline(self):
        path = self.dbpath("imperfect")
        generate(path, "imperfect", 17, 51)
        with closing(sqlite3.connect(path)) as db:
            for amount, date, currency in db.execute("SELECT amount_text,order_date,currency FROM raw_orders"):
                self.assertGreater(float(amount), 0)
                datetime.fromisoformat(date)
                self.assertEqual(currency, "EUR")
            for email in db.execute("SELECT email FROM raw_customers"):
                self.assertTrue(email[0].endswith("@example.test"))

    def test_anomalies_are_real_reported_and_reversible(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                path = self.dbpath(kind)
                generate(path, kind, 19, 33)
                clean = self.dump(path)
                result = generate(path, kind, 19, 33, True)
                self.assertTrue(result["anomalies"])
                self.assertNotEqual(clean, self.dump(path))
                with closing(sqlite3.connect(path)) as db:
                    if kind == "commerce":
                        self.assertTrue(db.execute("PRAGMA foreign_key_check").fetchall())
                        self.assertLess(db.execute("SELECT total_amount FROM orders WHERE id=1").fetchone()[0], 0)
                        self.assertIsNone(db.execute("SELECT email FROM customers WHERE id=1").fetchone()[0])
                    elif kind == "logistics":
                        weight, departure, arrival = db.execute("SELECT weight_kg, shipped_at, delivered_at FROM shipments WHERE id=1").fetchone()
                        self.assertLess(weight, 0)
                        self.assertLess(arrival, departure)
                    elif kind == "events":
                        duration, properties = db.execute("SELECT duration_ms,properties_json FROM events WHERE id=1").fetchone()
                        self.assertLess(duration, 0)
                        with self.assertRaises(json.JSONDecodeError):
                            json.loads(properties)
                        self.assertEqual(db.execute("SELECT COUNT(*) FROM events WHERE event_key='event-00000001'").fetchone()[0], 2)
                    else:
                        self.assertTrue(db.execute("PRAGMA foreign_key_check").fetchall())
                        self.assertIsNone(db.execute("SELECT currency FROM raw_orders WHERE id=1").fetchone()[0])
                        self.assertEqual(db.execute("SELECT COUNT(*) FROM raw_orders WHERE order_ref='ORDER-000001'").fetchone()[0], 2)
                self.assertEqual(generate(path, kind, 19, 33)["anomalies"], [])
                self.assertEqual(clean, self.dump(path))
                self.assertEqual(generate(path, kind, 19, 0, True)["anomalies"], [])

    def test_exports_match_principal_table(self):
        for kind in KINDS:
            for size in (0, 1, 20):
                with self.subTest(kind=kind, size=size):
                    path = self.dbpath("exports")
                    generate(path, kind, 44, size, True)
                    with closing(sqlite3.connect(path)) as db:
                        db.row_factory = sqlite3.Row
                        cursor = db.execute(f'SELECT * FROM "{PRINCIPAL[kind]}" ORDER BY id')
                        columns = [column[0] for column in cursor.description]
                        expected = [dict(row) for row in cursor]
                    actual_json = json.loads((path.parent / "source.json").read_text(encoding="utf-8"))
                    self.assertEqual(expected, actual_json)
                    with (path.parent / "source.csv").open(encoding="utf-8", newline="") as stream:
                        reader = csv.DictReader(stream)
                        self.assertEqual(columns, reader.fieldnames)
                        actual_csv = list(reader)
                    self.assertEqual(len(actual_csv), size)
                    for expected_row, actual_row in zip(expected, actual_csv):
                        self.assertEqual({key: "" if value is None else str(value) for key, value in expected_row.items()}, actual_row)

    def test_generation_preserves_global_random_state(self):
        before = random.getstate()
        generate(self.dbpath("rng"), "commerce", 51, 25)
        self.assertEqual(before, random.getstate())

    def test_validation_does_not_modify_existing_database(self):
        path = self.dbpath("validation")
        generate(path, "commerce", 5, 20)
        original = {filename: (path.parent / filename).read_bytes() for filename in ("lab.sqlite", "source.csv", "source.json")}
        invalid = [("unknown", 5, 20, False), ("commerce", -1, 20, False),
                   ("commerce", 2147483648, 20, False), ("commerce", True, 20, False),
                   ("commerce", 5, -1, False), ("commerce", 5, 10001, False),
                   ("commerce", 5, 1.5, False), ("commerce", 5, True, False),
                   ("commerce", 5, 20, "yes")]
        for args in invalid:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    generate(path, *args)
        for filename, content in original.items():
            self.assertEqual(content, (path.parent / filename).read_bytes())
        with self.assertRaises(ValueError):
            generate(PROJECT_ROOT.parent / "forbidden-dataset.sqlite", "commerce", 0, 0)
        with self.assertRaises(ValueError):
            generate(path.parent / "source.csv", "commerce", 0, 0)
        with self.assertRaises(ValueError):
            generate(path.parent, "commerce", 0, 0)

    def test_failure_cleans_temporary_files_and_preserves_old_database(self):
        path = self.dbpath("failure")
        generate(path, "commerce", 5, 20)
        original = {entry.name: entry.read_bytes() for entry in path.parent.iterdir()}
        def broken(db, rng, size, dirty):
            db.execute("CREATE TABLE interrupted (id INTEGER)")
            raise RuntimeError("intentional generator failure")
        with patch.dict(GENERATORS, {"commerce": broken}):
            with self.assertRaises(RuntimeError):
                generate(path, "commerce", 5, 20)
        self.assertEqual(original, {entry.name: entry.read_bytes() for entry in path.parent.iterdir()})

    def test_replacing_existing_database_removes_old_schema(self):
        path = self.dbpath("replacement")
        generate(path, "commerce", 5, 20)
        with closing(sqlite3.connect(path)) as db:
            db.execute("CREATE TABLE obsolete (id INTEGER)")
            db.commit()
        generate(path, "events", 5, 20)
        with closing(sqlite3.connect(path)) as db:
            names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(names, {"users", "sessions", "events"})
        self.assertEqual({entry.name for entry in path.parent.iterdir()}, {"lab.sqlite", "source.csv", "source.json"})

    def test_active_sqlite_sidecars_reject_replacement(self):
        path = self.dbpath("sidecar")
        generate(path, "commerce", 5, 20)
        original = path.read_bytes()
        wal = Path(str(path) + "-wal")
        wal.write_bytes(b"active")
        with self.assertRaises(ValueError):
            generate(path, "events", 5, 20)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(wal.read_bytes(), b"active")

    def test_maximum_size(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                result = generate(self.dbpath("max"), kind, 2147483647, 10000)
                self.assertEqual(result["tables"][PRINCIPAL[kind]], 10000)


if __name__ == "__main__":
    unittest.main()
