"""检查本地交接资料是否能按约定解析和关联。"""

import json
from pathlib import Path
import sqlite3
import unittest


DATA = Path(__file__).resolve().parents[1] / "data"


class InputFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.format = json.loads((DATA / "format.json").read_text(encoding="utf-8"))
        cls.sources = {
            name: json.loads((DATA / (name + ".json")).read_text(encoding="utf-8"))
            for name in cls.format["documents"]
        }

    def test_json_records_use_the_documented_fields_and_identity(self):
        for name, records in self.sources.items():
            with self.subTest(source=name):
                self.assertTrue(records)
                scope = self.format["scoped_ids"].get(name)
                ids = set()
                for row in records:
                    self.assertEqual(set(row), set(self.format["documents"][name]))
                    self.assertIsInstance(row["id"], str)
                    self.assertTrue(row["id"])
                    key = (row[scope] if scope else None, row["id"])
                    self.assertNotIn(key, ids)
                    ids.add(key)

    def test_references_name_actual_source_records(self):
        for source, field, target in self.format["references"]:
            ids = {row["id"] for row in self.sources[target]}
            for row in self.sources[source]:
                references = row[field] if isinstance(row[field], list) else [row[field]]
                for key in references:
                    if key is not None and key != "*":
                        with self.subTest(source=source, record=row["id"], field=field):
                            self.assertIn(key, ids)

    def test_utf8_documents_round_trip_via_sqlite(self):
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE input (name TEXT PRIMARY KEY, content TEXT NOT NULL)")
            db.executemany("INSERT INTO input VALUES (?, ?)", [
                (name, json.dumps(records, ensure_ascii=False)) for name, records in self.sources.items()
            ])
            restored = {name: json.loads(content) for name, content in db.execute("SELECT * FROM input")}
            self.assertEqual(restored, self.sources)


if __name__ == "__main__":
    unittest.main()
