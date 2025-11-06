import unittest
from unittest.mock import patch
import pandas as pd

from testrail_daily_report import summarize_results, build_test_table, get_plans_for_project, extract_refs


class TestSummarizeResults(unittest.TestCase):
    def test_empty_results(self):
        s = summarize_results([])
        self.assertEqual(s["total"], 0)
        self.assertEqual(s["by_status"], {})
        self.assertEqual(s["pass_rate"], 0.0)
        self.assertTrue(isinstance(s["df"], pd.DataFrame))

    def test_dedup_latest_per_test(self):
        # two results for same test_id; latest (higher created_on) should win
        results = [
            {"id": 1, "test_id": 10, "status_id": 5, "created_on": 100},
            {"id": 2, "test_id": 10, "status_id": 1, "created_on": 200},
            {"id": 3, "test_id": 11, "status_id": 1, "created_on": 150},
        ]
        s = summarize_results(results, status_map={1: "Passed", 5: "Failed"})
        self.assertEqual(s["total"], 2)
        # latest per test: 10 -> Passed, 11 -> Passed
        self.assertEqual(s["by_status"].get("Passed"), 2)
        self.assertEqual(s["pass_rate"], 100.0)


class TestBuildTestTable(unittest.TestCase):
    def test_mapping_and_sorting(self):
        tests = pd.DataFrame([
            {"id": 1, "title": "A ok", "status_id": 1, "priority_id": 2, "assignedto_id": 20},
            {"id": 2, "title": "B fail", "status_id": 5, "priority_id": 1, "assignedto_id": 10},
            {"id": 3, "title": "C untested", "status_id": None, "priority_id": 2, "assignedto_id": None},
        ])
        results = pd.DataFrame([
            {"test_id": 1, "comment": "ok"},
            {"test_id": 2, "comment": "not ok"},
        ])
        users = {10: "U10", 20: "U20"}
        prios = {1: "P1", 2: "P2"}
        status_map = {1: "Passed", 5: "Failed", 3: "Untested"}

        table = build_test_table(tests, results, status_map, users, prios)
        # order: Failed first, then Untested, then Passed
        self.assertEqual(table.iloc[0]["status_name"], "Failed")
        self.assertEqual(table.iloc[-1]["status_name"], "Passed")
        # mappings
        self.assertEqual(table[table["test_id"] == 2].iloc[0]["assignee"], "U10")
        self.assertEqual(table[table["test_id"] == 1].iloc[0]["priority"], "P2")


class TestPlansAPIShapes(unittest.TestCase):
    @patch("testrail_daily_report.api_get")
    def test_get_plans_list_and_dict(self, mock_api_get):
        # first page returns dict shape
        mock_api_get.side_effect = [
            {"plans": [{"id": 1}, {"id": 2}]},
            [],
        ]
        plans = get_plans_for_project(object(), "http://x", 1)
        self.assertEqual([p.get("id") for p in plans], [1, 2])

        # list shape
        mock_api_get.side_effect = [
            [{"id": 5}],
            [],
        ]
        plans = get_plans_for_project(object(), "http://x", 2)
        self.assertEqual([p.get("id") for p in plans], [5])

class TestExtractRefs(unittest.TestCase):
    def test_extract_refs_from_dicts(self):
        items = [
            {"refs": "ORB-1, ORB-2"},
            {"refs": "ORB-2, ORB-3"},
            {"refs": None},
            {},
        ]
        refs = extract_refs(items)
        self.assertEqual(refs, ["ORB-1", "ORB-2", "ORB-3"])

    def test_extract_refs_from_dataframe(self):
        df = pd.DataFrame([
            {"refs": "ABC-1"},
            {"refs": "ABC-2, ABC-3"},
        ])
        refs = extract_refs(df)
        self.assertEqual(refs, ["ABC-1", "ABC-2", "ABC-3"])

if __name__ == "__main__":
    unittest.main()
