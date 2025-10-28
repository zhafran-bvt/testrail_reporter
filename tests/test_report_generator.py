
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from testrail_daily_report import generate_report, build_test_table

class TestReportGenerator(unittest.TestCase):

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
    def test_generate_report_plan(self, mock_env_or_die, mock_render_html, mock_statuses_map, mock_priorities_map, mock_users_map, mock_results_for_run, mock_tests_for_run, mock_plan_runs, mock_plan, mock_project):
        # Mock environment variables
        mock_env_or_die.side_effect = lambda key: {
            "TESTRAIL_BASE_URL": "http://fake-testrail.com",
            "TESTRAIL_USER": "user",
            "TESTRAIL_API_KEY": "key"
        }[key]

        # Mock API responses
        mock_project.return_value = {"name": "Test Project"}
        mock_plan.return_value = {"name": "Test Plan"}
        mock_plan_runs.return_value = [101]
        mock_tests_for_run.return_value = [
            {"id": 1, "title": "Test Case 1", "status_id": 1, "priority_id": 1, "assignedto_id": 1},
            {"id": 2, "title": "Test Case 2", "status_id": 5, "priority_id": 2, "assignedto_id": 2},
        ]
        mock_results_for_run.return_value = [
            {"test_id": 1, "status_id": 1},
            {"test_id": 2, "status_id": 5},
        ]
        mock_users_map.return_value = {1: "User A", 2: "User B"}
        mock_priorities_map.return_value = {1: "P1", 2: "P2"}
        mock_statuses_map.return_value = {1: "Passed", 5: "Failed"}
        mock_render_html.return_value = "/path/to/report.html"

        # Run the report generator
        report_path = generate_report(project=1, plan=241)

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
