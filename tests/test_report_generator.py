import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from testrail_daily_report import build_test_table, generate_report


class TestReportGenerator(unittest.TestCase):
    @patch("testrail_daily_report.download_attachment")
    @patch("testrail_daily_report.render_html")
    def test_generate_report_plan(self, mock_render_html, mock_download_attachment):
        fake_client = MagicMock()
        fake_client.base_url = "http://fake-testrail.com"
        fake_client.timeout = 5.0
        fake_client.max_attempts = 2
        fake_client.backoff = 1.0
        fake_client.get_project.return_value = {"name": "Test Project"}
        fake_client.get_plan.return_value = {
            "name": "Test Plan",
            "entries": [
                {
                    "runs": [
                        {"id": 101, "name": "Daily Run"},
                        {"id": 202, "name": "Spare Run"},
                    ]
                }
            ],
        }
        fake_client.get_plan_runs.return_value = [101, 202]

        def tests_side_effect(rid):
            if rid == 101:
                return [
                    {
                        "id": 1,
                        "title": "Test Case 1",
                        "status_id": 1,
                        "priority_id": 1,
                        "assignedto_id": 1,
                    },
                    {
                        "id": 2,
                        "title": "Test Case 2",
                        "status_id": 5,
                        "priority_id": 2,
                        "assignedto_id": 2,
                    },
                ]
            if rid == 202:
                return [
                    {
                        "id": 10,
                        "title": "Spare Test",
                        "status_id": 1,
                        "priority_id": 3,
                        "assignedto_id": 3,
                    },
                ]
            return []

        def results_side_effect(rid):
            if rid == 101:
                return [
                    {"id": 11, "test_id": 1, "status_id": 1, "comment": "Looks good"},
                    {"id": 12, "test_id": 2, "status_id": 5, "comment": "Needs fix"},
                ]
            if rid == 202:
                return [
                    {"id": 21, "test_id": 10, "status_id": 1, "comment": "Spare pass"},
                ]
            return []

        def attachments_side_effect(test_id):
            mapping = {
                1: [{"id": 101, "name": "pass.png", "result_id": 11}],
                2: [
                    {"id": 102, "name": "fail.png", "result_id": 12},
                    {"id": 103, "name": "fail.png", "result_id": 12},
                ],
            }
            return mapping.get(test_id, [])

        fake_client.get_tests_for_run.side_effect = tests_side_effect
        fake_client.get_results_for_run.side_effect = results_side_effect
        fake_client.get_attachments_for_test.side_effect = attachments_side_effect
        fake_client.get_users_map.return_value = {1: "User A", 2: "User B", 3: "User C"}
        fake_client.get_priorities_map.return_value = {1: "P1", 2: "P2", 3: "P3"}
        fake_client.get_statuses_map.return_value = {1: "Passed", 5: "Failed"}
        mock_download_attachment.return_value = (b"fake-bytes", "image/png")
        mock_render_html.return_value = "/path/to/report.html"

        # Run the report generator
        report_path = generate_report(project=1, plan=241, run_ids=[101], api_client=fake_client)

        # Assertions
        self.assertEqual(report_path, "/path/to/report.html")
        mock_render_html.assert_called_once()
        context = mock_render_html.call_args[0][0]
        self.assertEqual(context["project_name"], "Test Project")
        self.assertEqual(context["plan_name"], "Test Plan")
        self.assertEqual(len(context["tables"]), 1)
        self.assertEqual(context["tables"][0]["total"], 2)
        # Overall donut present and looks like a conic-gradient
        self.assertIn("donut_style", context)
        self.assertIn("donut_legend", context)
        self.assertIsInstance(context["donut_legend"], list)
        self.assertTrue(str(context["donut_style"]).startswith("conic-gradient"))
        # Per-run donut fields exist
        run_card = context["tables"][0]
        self.assertIn("donut_style", run_card)
        self.assertIn("donut_legend", run_card)
        self.assertIsInstance(run_card["donut_legend"], list)
        # Expected segments include Passed and Failed
        labels = {seg.get("label") for seg in run_card["donut_legend"]}
        self.assertIn("Passed", labels)
        self.assertIn("Failed", labels)
        first_row = run_card["rows"][0]
        self.assertEqual(first_row.get("comment"), "Needs fix")
        attachments = first_row.get("attachments", [])
        self.assertEqual(len(attachments), 2)
        self.assertTrue(all(att.get("data_url", "").startswith("data:") for att in attachments))

    @patch("testrail_daily_report.download_attachment")
    @patch("testrail_daily_report.render_html")
    def test_generate_report_attachments_failure(self, mock_render_html, mock_download_attachment):
        fake_client = MagicMock()
        fake_client.base_url = "http://fake-testrail.com"
        fake_client.timeout = 5.0
        fake_client.max_attempts = 2
        fake_client.backoff = 1.0
        fake_client.get_project.return_value = {"name": "Project"}
        fake_client.get_plan.return_value = {
            "name": "Plan",
            "entries": [{"runs": [{"id": 99, "name": "Only Run"}]}],
        }
        fake_client.get_plan_runs.return_value = [99]
        fake_client.get_tests_for_run.return_value = [
            {
                "id": 7,
                "title": "Sample Test",
                "status_id": 1,
                "priority_id": 3,
                "assignedto_id": 9,
            },
        ]
        fake_client.get_results_for_run.return_value = [
            {"id": 701, "test_id": 7, "status_id": 1, "comment": "Commented"},
        ]
        fake_client.get_users_map.return_value = {9: "User Nine"}
        fake_client.get_priorities_map.return_value = {3: "Medium"}
        fake_client.get_statuses_map.return_value = {1: "Passed"}
        fake_client.get_attachments_for_test.side_effect = RuntimeError("boom")
        mock_download_attachment.return_value = (b"", "image/png")
        mock_render_html.return_value = "/tmp/report.html"

        path = generate_report(project=1, plan=55, api_client=fake_client)
        self.assertEqual(path, "/tmp/report.html")
        context = mock_render_html.call_args[0][0]
        self.assertIn("tables", context)
        self.assertGreater(len(context["tables"]), 0)
        rows = context["tables"][0]["rows"]
        self.assertEqual(rows[0]["attachments"], [])
        self.assertEqual(rows[0]["comment"], "Commented")

    @patch("testrail_daily_report.transcode_video_file")
    @patch("testrail_daily_report.download_attachment")
    @patch("testrail_daily_report.render_html")
    def test_generate_report_video_attachment_paths(
        self, mock_render_html, mock_download_attachment, mock_transcode_video
    ):
        fake_client = MagicMock()
        fake_client.base_url = "http://fake-testrail.com"
        fake_client.timeout = 5.0
        fake_client.max_attempts = 2
        fake_client.backoff = 1.0
        fake_client.get_project.return_value = {"name": "Project"}
        fake_client.get_plan.return_value = {
            "name": "Video Plan",
            "entries": [{"runs": [{"id": 301, "name": "Video Run"}]}],
        }
        fake_client.get_plan_runs.return_value = [301]
        fake_client.get_tests_for_run.return_value = [
            {
                "id": 5,
                "title": "Has Video",
                "status_id": 1,
                "priority_id": 2,
                "assignedto_id": 11,
            },
        ]
        fake_client.get_results_for_run.return_value = [
            {"id": 501, "test_id": 5, "status_id": 1, "comment": "See clip"},
        ]
        fake_client.get_attachments_for_test.return_value = [
            {"id": 201, "name": "clip.mp4", "result_id": 501, "size": 1234},
        ]

        def fake_transcode(input_path, output_path, **kwargs):
            Path(output_path).write_bytes(b"video")

        mock_transcode_video.side_effect = fake_transcode
        mock_download_attachment.return_value = (b"video-bytes", "video/mp4")
        fake_client.get_users_map.return_value = {11: "User Eleven"}
        fake_client.get_priorities_map.return_value = {2: "P2"}
        fake_client.get_statuses_map.return_value = {1: "Passed"}
        mock_render_html.return_value = "/tmp/video-report.html"

        path = generate_report(project=1, plan=77, run_ids=[301], api_client=fake_client)

        self.assertEqual(path, "/tmp/video-report.html")
        context = mock_render_html.call_args[0][0]
        rows = context["tables"][0]["rows"]
        self.assertEqual(len(rows), 1)
        attachments = rows[0].get("attachments", [])
        self.assertEqual(len(attachments), 1)
        video = attachments[0]
        self.assertTrue(video["is_video"])
        self.assertTrue(video.get("data_url", "").startswith("data:"))
        self.assertFalse(video.get("skipped"))
        self.assertEqual(rows[0].get("assignee"), "User Eleven")
        self.assertTrue(mock_transcode_video.called)

    @patch("testrail_daily_report.download_attachment")
    @patch("testrail_daily_report.render_html")
    def test_generate_report_multiple_runs_snapshot(self, mock_render_html, mock_download_attachment):
        fake_client = MagicMock()
        fake_client.base_url = "http://fake-testrail.com"
        fake_client.timeout = 5.0
        fake_client.max_attempts = 2
        fake_client.backoff = 1.0
        fake_client.get_project.return_value = {"name": "Project"}
        fake_client.get_plan.return_value = {
            "name": "Plan",
            "entries": [{"runs": [{"id": 10, "name": "Alpha"}, {"id": 20, "name": "Beta"}]}],
        }
        fake_client.get_plan_runs.return_value = [10, 20]

        def tests_side_effect(rid):
            if rid == 10:
                return [
                    {
                        "id": 1,
                        "title": "A",
                        "status_id": 1,
                        "priority_id": 1,
                        "assignedto_id": 1,
                    }
                ]
            return [
                {
                    "id": 2,
                    "title": "B",
                    "status_id": 5,
                    "priority_id": 2,
                    "assignedto_id": 2,
                }
            ]

        fake_client.get_tests_for_run.side_effect = tests_side_effect
        fake_client.get_results_for_run.side_effect = lambda rid: [{"id": 100, "test_id": 1, "status_id": 1}]
        fake_client.get_attachments_for_test.return_value = []
        mock_download_attachment.return_value = (b"", "image/png")
        fake_client.get_users_map.return_value = {1: "U1", 2: "U2"}
        fake_client.get_priorities_map.return_value = {1: "P1", 2: "P2"}
        fake_client.get_statuses_map.return_value = {1: "Passed", 5: "Failed"}
        mock_render_html.return_value = "/tmp/multi.html"

        path = generate_report(project=1, plan=77, run_ids=[10, 20], api_client=fake_client)
        self.assertEqual(path, "/tmp/multi.html")
        context = mock_render_html.call_args[0][0]
        self.assertEqual(len(context["tables"]), 2)
        run_ids = [card["run_id"] for card in context["tables"]]
        self.assertEqual(run_ids, [10, 20])

    @patch("testrail_daily_report.download_attachment")
    @patch("testrail_daily_report.render_html")
    def test_generate_report_mixed_attachment_runs(self, mock_render_html, mock_download_attachment):
        fake_client = MagicMock()
        fake_client.base_url = "http://fake-testrail.com"
        fake_client.timeout = 5.0
        fake_client.max_attempts = 2
        fake_client.backoff = 1.0
        fake_client.get_project.return_value = {"name": "Project"}
        fake_client.get_plan.return_value = {
            "name": "Plan",
            "entries": [
                {
                    "runs": [
                        {"id": 30, "name": "NoFiles"},
                        {"id": 40, "name": "WithFiles"},
                    ]
                }
            ],
        }
        fake_client.get_plan_runs.return_value = [30, 40]

        def tests_side_effect(rid):
            return [
                {
                    "id": rid,
                    "title": f"Run {rid}",
                    "status_id": 1,
                    "priority_id": 1,
                    "assignedto_id": 1,
                }
            ]

        fake_client.get_tests_for_run.side_effect = tests_side_effect

        def results_side_effect(rid):
            return [{"id": 200 + rid, "test_id": rid, "status_id": 1}]

        fake_client.get_results_for_run.side_effect = results_side_effect

        def attachments_side_effect(test_id):
            if test_id == 30:
                return []
            return [{"id": 400, "name": "pic.png", "result_id": 200 + test_id, "size": 10}]

        fake_client.get_attachments_for_test.side_effect = attachments_side_effect
        mock_download_attachment.return_value = (b"bytes", "image/png")
        fake_client.get_users_map.return_value = {1: "Solo"}
        fake_client.get_priorities_map.return_value = {1: "P1"}
        fake_client.get_statuses_map.return_value = {1: "Passed"}
        mock_render_html.return_value = "/tmp/mixed.html"

        path = generate_report(project=1, plan=88, run_ids=[30, 40], api_client=fake_client)
        self.assertEqual(path, "/tmp/mixed.html")
        context = mock_render_html.call_args[0][0]
        self.assertEqual(len(context["tables"]), 2)
        no_files = context["tables"][0]["rows"][0]["attachments"]
        with_files = context["tables"][1]["rows"][0]["attachments"]
        self.assertEqual(no_files, [])
        self.assertEqual(len(with_files), 1)

    @patch("testrail_daily_report.download_attachment")
    def test_generate_report_html_contains_runs(self, mock_download_attachment):
        fake_client = MagicMock()
        fake_client.base_url = "http://fake-testrail.com"
        fake_client.timeout = 5.0
        fake_client.max_attempts = 2
        fake_client.backoff = 1.0
        fake_client.get_project.return_value = {"name": "Project"}
        fake_client.get_plan.return_value = {
            "name": "Plan",
            "entries": [{"runs": [{"id": 50, "name": "First"}, {"id": 60, "name": "Second"}]}],
        }
        fake_client.get_plan_runs.return_value = [50, 60]

        def tests_side_effect(rid):
            return [
                {
                    "id": rid,
                    "title": f"Test {rid}",
                    "status_id": 1,
                    "priority_id": 1,
                    "assignedto_id": 1,
                }
            ]

        fake_client.get_tests_for_run.side_effect = tests_side_effect
        fake_client.get_results_for_run.return_value = [{"id": 300, "test_id": 50, "status_id": 1}]
        fake_client.get_attachments_for_test.return_value = []
        mock_download_attachment.return_value = (b"bytes", "image/png")
        fake_client.get_users_map.return_value = {1: "Solo"}
        fake_client.get_priorities_map.return_value = {1: "P1"}
        fake_client.get_statuses_map.return_value = {1: "Passed"}

        path = generate_report(project=1, plan=200, run_ids=[50, 60], api_client=fake_client)
        html_path = Path(path)
        self.assertTrue(html_path.exists())
        html = html_path.read_text(encoding="utf-8")
        self.assertIn("Run #50", html)
        self.assertIn("Run #60", html)
        html_path.unlink(missing_ok=True)
        attachments_dir = Path("out") / "attachments"
        if attachments_dir.exists():
            shutil.rmtree(attachments_dir)

    @patch("testrail_daily_report.transcode_video_file")
    @patch("testrail_daily_report.download_attachment")
    @patch("testrail_daily_report.render_html")
    def test_video_transcode_disabled(self, mock_render_html, mock_download_attachment, mock_transcode_video):
        fake_client = MagicMock()
        fake_client.base_url = "http://fake-testrail.com"
        fake_client.timeout = 5.0
        fake_client.max_attempts = 2
        fake_client.backoff = 1.0
        fake_client.get_project.return_value = {"name": "Project"}
        fake_client.get_plan.return_value = {
            "name": "Video Plan",
            "entries": [{"runs": [{"id": 401, "name": "Video"}]}],
        }
        fake_client.get_plan_runs.return_value = [401]
        fake_client.get_tests_for_run.return_value = [
            {
                "id": 9,
                "title": "Clip",
                "status_id": 1,
                "priority_id": 1,
                "assignedto_id": 1,
            },
        ]
        fake_client.get_results_for_run.return_value = [{"id": 900, "test_id": 9, "status_id": 1}]
        fake_client.get_attachments_for_test.return_value = [
            {"id": 700, "name": "clip.mov", "result_id": 900, "size": 1000}
        ]
        mock_download_attachment.return_value = (b"video", "video/quicktime")
        fake_client.get_users_map.return_value = {1: "User"}
        fake_client.get_priorities_map.return_value = {1: "P1"}
        fake_client.get_statuses_map.return_value = {1: "Passed"}
        mock_render_html.return_value = "/tmp/video-disabled.html"

        with patch.dict(os.environ, {"ATTACHMENT_VIDEO_TRANSCODE": "0"}):
            path = generate_report(project=1, plan=900, run_ids=[401], api_client=fake_client)

        self.assertEqual(path, "/tmp/video-disabled.html")
        self.assertFalse(mock_transcode_video.called)

    @patch("testrail_daily_report.download_attachment")
    @patch("testrail_daily_report.render_html")
    def test_keep_attachment_files_flag(self, mock_render_html, mock_download_attachment):
        fake_client = MagicMock()
        fake_client.base_url = "http://fake-testrail.com"
        fake_client.timeout = 5.0
        fake_client.max_attempts = 2
        fake_client.backoff = 1.0
        fake_client.get_project.return_value = {"name": "Project"}
        fake_client.get_plan.return_value = {
            "name": "Plan",
            "entries": [{"runs": [{"id": 501, "name": "Inline"}]}],
        }
        fake_client.get_plan_runs.return_value = [501]
        fake_client.get_tests_for_run.return_value = [
            {
                "id": 42,
                "title": "Attachment",
                "status_id": 1,
                "priority_id": 1,
                "assignedto_id": 1,
            }
        ]
        fake_client.get_results_for_run.return_value = [{"id": 42, "test_id": 42, "status_id": 1}]
        fake_client.get_attachments_for_test.return_value = [
            {"id": 600, "name": "pic.png", "result_id": 42, "size": 512}
        ]
        mock_download_attachment.return_value = (b"\x89PNG\r\n\x1a\n", "image/png")
        fake_client.get_users_map.return_value = {1: "User"}
        fake_client.get_priorities_map.return_value = {1: "P1"}
        fake_client.get_statuses_map.return_value = {1: "Passed"}
        mock_render_html.return_value = "/tmp/no-files.html"

        path = generate_report(project=1, plan=777, run_ids=[501], api_client=fake_client)

        self.assertEqual(path, "/tmp/no-files.html")
        self.assertFalse((Path("out") / "attachments").exists())
        html = Path(path)
        if html.exists():
            html.unlink()

    @patch("testrail_daily_report.download_attachment")
    @patch("testrail_daily_report.render_html")
    def test_generate_report_snapshot_disabled(self, mock_render_html, mock_download_attachment):
        fake_client = MagicMock()
        fake_client.base_url = "http://fake-testrail.com"
        fake_client.timeout = 5.0
        fake_client.max_attempts = 2
        fake_client.backoff = 1.0
        fake_client.get_project.return_value = {"name": "Project"}
        fake_client.get_plan.return_value = {
            "name": "Plan",
            "entries": [{"runs": [{"id": 400, "name": "Single"}]}],
        }
        fake_client.get_plan_runs.return_value = [400]
        fake_client.get_tests_for_run.return_value = [
            {
                "id": 1,
                "title": "Only",
                "status_id": 1,
                "priority_id": 1,
                "assignedto_id": 5,
            },
        ]
        fake_client.get_results_for_run.return_value = [
            {"id": 11, "test_id": 1, "status_id": 1},
        ]
        fake_client.get_users_map.return_value = {5: "User"}
        fake_client.get_priorities_map.return_value = {1: "P1"}
        fake_client.get_statuses_map.return_value = {1: "Passed"}
        fake_client.get_attachments_for_test.return_value = []
        mock_download_attachment.return_value = (b"", "image/png")
        mock_render_html.return_value = "/tmp/report-no-snapshot.html"

        with patch.dict(os.environ, {"REPORT_TABLE_SNAPSHOT": "0"}):
            path = generate_report(project=1, plan=44, api_client=fake_client)

        self.assertEqual(path, "/tmp/report-no-snapshot.html")
        context = mock_render_html.call_args[0][0]
        self.assertEqual(context.get("tables"), [])

    @patch("testrail_daily_report.download_attachment")
    @patch("testrail_daily_report.render_html")
    def test_generate_report_snapshot_limit(self, mock_render_html, mock_download_attachment):
        fake_client = MagicMock()
        fake_client.base_url = "http://fake-testrail.com"
        fake_client.timeout = 5.0
        fake_client.max_attempts = 2
        fake_client.backoff = 1.0
        fake_client.get_project.return_value = {"name": "Project"}
        fake_client.get_plan.return_value = {
            "name": "Plan",
            "entries": [{"runs": [{"id": 500, "name": "One"}, {"id": 600, "name": "Two"}]}],
        }
        fake_client.get_plan_runs.return_value = [500, 600]

        def _tests_for_run(rid):
            return [
                {
                    "id": rid,
                    "title": f"Run {rid}",
                    "status_id": 1,
                    "priority_id": 1,
                    "assignedto_id": 7,
                }
            ]

        fake_client.get_tests_for_run.side_effect = _tests_for_run
        fake_client.get_results_for_run.return_value = [{"id": 21, "test_id": 500, "status_id": 1}]
        fake_client.get_users_map.return_value = {7: "User Seven"}
        fake_client.get_priorities_map.return_value = {1: "P1"}
        fake_client.get_statuses_map.return_value = {1: "Passed"}
        fake_client.get_attachments_for_test.return_value = []
        mock_download_attachment.return_value = (b"", "image/png")
        mock_render_html.return_value = "/tmp/report-snapshot-limit.html"

        with patch.dict(os.environ, {"REPORT_TABLE_SNAPSHOT": "1", "TABLE_SNAPSHOT_LIMIT": "1"}):
            path = generate_report(project=1, plan=55, api_client=fake_client)

        self.assertEqual(path, "/tmp/report-snapshot-limit.html")
        context = mock_render_html.call_args[0][0]
        self.assertEqual(len(context.get("tables", [])), 1)

    @patch("testrail_daily_report.download_attachment")
    @patch("testrail_daily_report.compress_image_data")
    @patch("testrail_daily_report.render_html")
    def test_attachment_batching_respects_env(self, mock_render_html, mock_compress_image, mock_download_attachment):
        fake_client = MagicMock()
        fake_client.base_url = "http://fake-testrail.com"
        fake_client.timeout = 5.0
        fake_client.max_attempts = 2
        fake_client.backoff = 1.0
        fake_client.get_project.return_value = {"name": "Project"}
        fake_client.get_plan.return_value = {
            "name": "Plan",
            "entries": [{"runs": [{"id": 700, "name": "Batch"}]}],
        }
        fake_client.get_plan_runs.return_value = [700]
        fake_client.get_tests_for_run.return_value = [
            {
                "id": 77,
                "title": "Has attachments",
                "status_id": 1,
                "priority_id": 1,
                "assignedto_id": 1,
            },
        ]
        fake_client.get_results_for_run.return_value = [
            {"id": 501, "test_id": 77, "status_id": 1, "comment": "ok"},
        ]
        attachments_payload = [
            {"id": 1000 + i, "name": f"pic_{i}.png", "result_id": 501, "size": 1234} for i in range(5)
        ]
        fake_client.get_attachments_for_test.return_value = attachments_payload
        mock_download_attachment.return_value = (b"bytes", "image/png")
        fake_client.get_users_map.return_value = {1: "User One"}
        fake_client.get_priorities_map.return_value = {1: "P1"}
        fake_client.get_statuses_map.return_value = {1: "Passed"}
        mock_render_html.return_value = "/tmp/batch.html"

        def fake_compress(data, content_type):
            return b"img", "image/png"

        mock_compress_image.side_effect = fake_compress

        class RecordingExecutor:
            instances = []

            def __init__(self, max_workers):
                self.max_workers = max_workers
                self.futures = []
                RecordingExecutor.instances.append(self)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

            def submit(self, fn, *args, **kwargs):
                result = fn(*args, **kwargs)
                future = MagicMock()
                future.result.return_value = result
                self.futures.append(future)
                return future

        def fake_as_completed(futures):
            if isinstance(futures, dict):
                iterable = list(futures.keys())
            else:
                iterable = list(futures)
            for fut in iterable:
                yield fut

        with patch("testrail_daily_report.ThreadPoolExecutor", RecordingExecutor), patch(
            "testrail_daily_report.as_completed", fake_as_completed
        ):
            with patch.dict(
                os.environ,
                {
                    "ATTACHMENT_BATCH_SIZE": "2",
                    "ATTACHMENT_WORKERS": "3",
                    "RUN_WORKERS": "1",
                    "RUN_WORKERS_MAX": "1",
                },
            ):
                path = generate_report(project=1, plan=700, api_client=fake_client)

        self.assertEqual(path, "/tmp/batch.html")
        # First executor handles metadata, remaining executors correspond to batches.
        self.assertGreaterEqual(len(RecordingExecutor.instances), 4)
        batch_workers = [inst.max_workers for inst in RecordingExecutor.instances[1:]]
        self.assertEqual(batch_workers, [2, 2, 1])
        total_jobs = sum(len(inst.futures) for inst in RecordingExecutor.instances[1:])
        self.assertEqual(total_jobs, 5)

    def test_generate_report_invalid_run_ids(self):
        fake_client = MagicMock()
        fake_client.base_url = "http://fake-testrail.com"
        fake_client.timeout = 5.0
        fake_client.max_attempts = 2
        fake_client.backoff = 1.0
        fake_client.get_project.return_value = {"name": "Project"}
        fake_client.get_plan.return_value = {
            "name": "Plan",
            "entries": [{"runs": [{"id": 200, "name": "Valid Run"}]}],
        }
        fake_client.get_plan_runs.return_value = [200]
        with self.assertRaises(ValueError):
            generate_report(project=1, plan=99, run_ids=[111], api_client=fake_client)

    def test_build_test_table(self):
        tests_df = pd.DataFrame(
            [
                {
                    "id": 1,
                    "title": "Test A",
                    "status_id": 1,
                    "priority_id": 1,
                    "assignedto_id": 10,
                },
                {
                    "id": 2,
                    "title": "Test B",
                    "status_id": 5,
                    "priority_id": 2,
                    "assignedto_id": 20,
                },
            ]
        )
        results_df = pd.DataFrame(
            [
                {"test_id": 1, "comment": "Passed"},
                {"test_id": 2, "comment": "Failed"},
            ]
        )
        users_map = {10: "User X", 20: "User Y"}
        priorities_map = {1: "High", 2: "Medium"}
        status_map = {1: "Passed", 5: "Failed"}

        table = build_test_table(tests_df, results_df, status_map, users_map, priorities_map)

        self.assertEqual(len(table), 2)
        self.assertEqual(table.iloc[0]["title"], "Test B")  # Failed tests first
        self.assertEqual(table.iloc[1]["title"], "Test A")
        self.assertEqual(table.iloc[0]["assignee"], "User Y")
        self.assertEqual(table.iloc[1]["priority"], "High")


if __name__ == "__main__":
    unittest.main()
