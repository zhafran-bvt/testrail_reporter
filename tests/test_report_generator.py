
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from testrail_daily_report import generate_report, build_test_table

class TestReportGenerator(unittest.TestCase):

    @patch('testrail_daily_report.get_project')
    @patch('testrail_daily_report.get_plan')
    @patch('testrail_daily_report.get_plan_runs')
    @patch('testrail_daily_report.get_tests_for_run')
    @patch('testrail_daily_report.download_attachment')
    @patch('testrail_daily_report.get_attachments_for_test')
    @patch('testrail_daily_report.get_results_for_run')
    @patch('testrail_daily_report.get_users_map')
    @patch('testrail_daily_report.get_priorities_map')
    @patch('testrail_daily_report.get_statuses_map')
    @patch('testrail_daily_report.render_html')
    @patch('testrail_daily_report.env_or_die')
    def test_generate_report_plan(self, mock_env_or_die, mock_render_html, mock_statuses_map, mock_priorities_map,
                                  mock_users_map, mock_results_for_run, mock_get_attachments_for_test,
                                  mock_download_attachment, mock_tests_for_run, mock_plan_runs, mock_plan, mock_project):
        # Mock environment variables
        mock_env_or_die.side_effect = lambda key: {
            "TESTRAIL_BASE_URL": "http://fake-testrail.com",
            "TESTRAIL_USER": "user",
            "TESTRAIL_API_KEY": "key"
        }[key]

        # Mock API responses
        mock_project.return_value = {"name": "Test Project"}
        mock_plan.return_value = {
            "name": "Test Plan",
            "entries": [
                {"runs": [
                    {"id": 101, "name": "Daily Run"},
                    {"id": 202, "name": "Spare Run"},
                ]}
            ]
        }
        mock_plan_runs.return_value = [101, 202]
        mock_tests_for_run.return_value = [
            {"id": 1, "title": "Test Case 1", "status_id": 1, "priority_id": 1, "assignedto_id": 1},
            {"id": 2, "title": "Test Case 2", "status_id": 5, "priority_id": 2, "assignedto_id": 2},
        ]
        mock_results_for_run.return_value = [
            {"id": 11, "test_id": 1, "status_id": 1, "comment": "Looks good"},
            {"id": 12, "test_id": 2, "status_id": 5, "comment": "Needs fix"},
        ]
        def attachments_side_effect(_session, _base_url, test_id):
            mapping = {
                1: [{"id": 101, "name": "pass.png", "result_id": 11}],
                2: [{"id": 102, "name": "fail.png", "result_id": 12}, {"id": 103, "name": "fail.png", "result_id": 12}],
            }
            return mapping.get(test_id, [])
        mock_get_attachments_for_test.side_effect = attachments_side_effect
        mock_download_attachment.return_value = (b"fake-bytes", "image/png")
        mock_users_map.return_value = {1: "User A", 2: "User B"}
        mock_priorities_map.return_value = {1: "P1", 2: "P2"}
        mock_statuses_map.return_value = {1: "Passed", 5: "Failed"}
        mock_render_html.return_value = "/path/to/report.html"

        # Run the report generator
        report_path = generate_report(project=1, plan=241, run_ids=[101])

        # Assertions
        self.assertEqual(report_path, "/path/to/report.html")
        mock_render_html.assert_called_once()
        context = mock_render_html.call_args[0][0]
        self.assertEqual(context['project_name'], "Test Project")
        self.assertEqual(context['plan_name'], "Test Plan")
        self.assertEqual(len(context['tables']), 1)
        self.assertEqual(context['tables'][0]['total'], 2)
        # Overall donut present and looks like a conic-gradient
        self.assertIn('donut_style', context)
        self.assertIn('donut_legend', context)
        self.assertIsInstance(context['donut_legend'], list)
        self.assertTrue(str(context['donut_style']).startswith('conic-gradient'))
        # Per-run donut fields exist
        run_card = context['tables'][0]
        self.assertIn('donut_style', run_card)
        self.assertIn('donut_legend', run_card)
        self.assertIsInstance(run_card['donut_legend'], list)
        # Expected segments include Passed and Failed
        labels = {seg.get('label') for seg in run_card['donut_legend']}
        self.assertIn('Passed', labels)
        self.assertIn('Failed', labels)
        first_row = run_card['rows'][0]
        self.assertEqual(first_row.get('comment'), "Needs fix")
        attachments = first_row.get('attachments', [])
        self.assertEqual(len(attachments), 2)
        for att in attachments:
            self.assertTrue(att.get('data_url', '').startswith('data:image/png;base64,'))
        paths = {att['path'] for att in attachments}
        self.assertEqual(paths, {
            "attachments/run_101/test_2_att_102.png",
            "attachments/run_101/test_2_att_103.png",
        })

    @patch('testrail_daily_report.get_project')
    @patch('testrail_daily_report.get_plan')
    @patch('testrail_daily_report.get_plan_runs')
    @patch('testrail_daily_report.get_tests_for_run')
    @patch('testrail_daily_report.download_attachment')
    @patch('testrail_daily_report.get_attachments_for_test')
    @patch('testrail_daily_report.get_results_for_run')
    @patch('testrail_daily_report.get_users_map')
    @patch('testrail_daily_report.get_priorities_map')
    @patch('testrail_daily_report.get_statuses_map')
    @patch('testrail_daily_report.render_html')
    @patch('testrail_daily_report.env_or_die')
    def test_generate_report_attachments_failure(self, mock_env_or_die, mock_render_html, mock_statuses_map, mock_priorities_map,
                                                 mock_users_map, mock_results_for_run, mock_get_attachments_for_test,
                                                 mock_download_attachment, mock_tests_for_run, mock_plan_runs, mock_plan, mock_project):
        mock_env_or_die.side_effect = lambda key: {
            "TESTRAIL_BASE_URL": "http://fake-testrail.com",
            "TESTRAIL_USER": "user",
            "TESTRAIL_API_KEY": "key"
        }[key]
        mock_project.return_value = {"name": "Project"}
        mock_plan.return_value = {
            "name": "Plan",
            "entries": [
                {"runs": [{"id": 99, "name": "Only Run"}]}
            ]
        }
        mock_plan_runs.return_value = [99]
        mock_tests_for_run.return_value = [
            {"id": 7, "title": "Sample Test", "status_id": 1, "priority_id": 3, "assignedto_id": 9},
        ]
        mock_results_for_run.return_value = [
            {"id": 701, "test_id": 7, "status_id": 1, "comment": "Commented"},
        ]
        mock_users_map.return_value = {9: "User Nine"}
        mock_priorities_map.return_value = {3: "Medium"}
        mock_statuses_map.return_value = {1: "Passed"}
        mock_get_attachments_for_test.side_effect = RuntimeError("boom")
        mock_download_attachment.return_value = (b"", "image/png")
        mock_render_html.return_value = "/tmp/report.html"

        path = generate_report(project=1, plan=55)
        self.assertEqual(path, "/tmp/report.html")
        context = mock_render_html.call_args[0][0]
        self.assertIn('tables', context)
        self.assertGreater(len(context['tables']), 0)
        rows = context['tables'][0]['rows']
        self.assertEqual(rows[0]['attachments'], [])
        self.assertEqual(rows[0]['comment'], "Commented")

    @patch('testrail_daily_report.get_project')
    @patch('testrail_daily_report.get_plan')
    @patch('testrail_daily_report.get_plan_runs')
    @patch('testrail_daily_report.get_tests_for_run')
    @patch('testrail_daily_report.get_results_for_run')
    @patch('testrail_daily_report.get_users_map')
    @patch('testrail_daily_report.get_priorities_map')
    @patch('testrail_daily_report.get_statuses_map')
    @patch('testrail_daily_report.render_html')
    @patch('testrail_daily_report.env_or_die')
    def test_generate_report_invalid_run_ids(self, mock_env_or_die, mock_render_html, mock_statuses_map, mock_priorities_map,
                                             mock_users_map, mock_results_for_run, mock_get_tests_for_run,
                                             mock_get_plan_runs, mock_get_plan, mock_get_project):
        mock_env_or_die.side_effect = lambda key: {
            "TESTRAIL_BASE_URL": "http://fake-testrail.com",
            "TESTRAIL_USER": "user",
            "TESTRAIL_API_KEY": "key"
        }[key]
        mock_get_project.return_value = {"name": "Project"}
        mock_get_plan.return_value = {
            "name": "Plan",
            "entries": [
                {"runs": [{"id": 200, "name": "Valid Run"}]}
            ]
        }
        mock_get_plan_runs.return_value = [200]
        with self.assertRaises(ValueError):
            generate_report(project=1, plan=99, run_ids=[111])

    def test_build_test_table(self):
        tests_df = pd.DataFrame([
            {'id': 1, 'title': 'Test A', 'status_id': 1, 'priority_id': 1, 'assignedto_id': 10},
            {'id': 2, 'title': 'Test B', 'status_id': 5, 'priority_id': 2, 'assignedto_id': 20},
        ])
        results_df = pd.DataFrame([
            {'test_id': 1, 'comment': 'Passed'},
            {'test_id': 2, 'comment': 'Failed'},
        ])
        users_map = {10: 'User X', 20: 'User Y'}
        priorities_map = {1: 'High', 2: 'Medium'}
        status_map = {1: 'Passed', 5: 'Failed'}

        table = build_test_table(tests_df, results_df, status_map, users_map, priorities_map)

        self.assertEqual(len(table), 2)
        self.assertEqual(table.iloc[0]['title'], 'Test B') # Failed tests first
        self.assertEqual(table.iloc[1]['title'], 'Test A')
        self.assertEqual(table.iloc[0]['assignee'], 'User Y')
        self.assertEqual(table.iloc[1]['priority'], 'High')

if __name__ == '__main__':
    unittest.main()
