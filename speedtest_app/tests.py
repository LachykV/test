import json
import os
import tempfile
from django.test import TestCase as DjangoTestCase, Client
from django.urls import reverse
from unittest import mock, TestCase
from datetime import datetime, timedelta, timezone
from .models import SpeedTestResult
from .utils import SpeedTestAnalyzer, SpeedTestLogger

class SpeedTestAnalyzerTests(TestCase):
    def setUp(self):
        # Initialize the analyzer with typical good connection values
        self.analyzer_fast = SpeedTestAnalyzer(download_speed=100, upload_speed=30, ping=10)
        # Initialize an analyzer with typical poor connection values
        self.analyzer_slow = SpeedTestAnalyzer(download_speed=10, upload_speed=5, ping=100)

    def test_is_fast_connection_true(self):
        # Test that the analyzer correctly identifies a fast connection
        self.assertTrue(self.analyzer_fast.is_fast_connection())

    def test_is_fast_connection_false_low_download(self):
        # Test that the analyzer correctly identifies a slow connection due to low download speed
        analyzer = SpeedTestAnalyzer(download_speed=40, upload_speed=30, ping=10)
        self.assertFalse(analyzer.is_fast_connection())

    def test_is_fast_connection_false_low_upload(self):
        # Test that the analyzer correctly identifies a slow connection due to low upload speed
        analyzer = SpeedTestAnalyzer(download_speed=100, upload_speed=15, ping=10)
        self.assertFalse(analyzer.is_fast_connection())

    def test_is_fast_connection_false_high_ping(self):
        # Test that the analyzer correctly identifies a slow connection due to high ping
        analyzer = SpeedTestAnalyzer(download_speed=100, upload_speed=30, ping=60)
        self.assertFalse(analyzer.is_fast_connection())

    @mock.patch('speedtest_app.utils.datetime')
    def test_summary_good_connection(self, mock_datetime):
        # Mock datetime.now() for consistency, although not directly used by summary()
        mock_datetime.now.return_value = datetime(2025, 6, 11, 10, 0, 0, tzinfo=timezone.utc)
        # Test that the summary message for a good connection is correct
        self.assertEqual(self.analyzer_fast.summary(), "Інтернет-з'єднання хороше.")

    @mock.patch('speedtest_app.utils.datetime')
    def test_summary_poor_connection(self, mock_datetime):
        # Mock datetime.now() for consistency, although not directly used by summary()
        mock_datetime.now.return_value = datetime(2025, 6, 11, 10, 0, 0, tzinfo=timezone.utc)
        # Test the summary message when the connection is slow or unstable
        self.assertEqual(self.analyzer_slow.summary(), "Інтернет-з'єднання повільне або нестабільне.")

    @mock.patch('speedtest_app.utils.datetime')
    def test_to_dict_structure_and_content(self, mock_datetime):
        # Mock datetime.now() to ensure consistent timestamp for testing
        mock_datetime.now.return_value = datetime(2025, 6, 11, 10, 0, 0, tzinfo=timezone.utc)

        # Test that the output dictionary from to_dict contains all expected keys and correct values
        result = self.analyzer_fast.to_dict()
        self.assertIn('timestamp', result)
        self.assertIn('download_speed', result)
        self.assertIn('upload_speed', result)
        self.assertIn('ping', result)
        self.assertIn('is_fast', result)
        self.assertIn('summary', result)
        # Fix: Expect the timezone offset in the timestamp string
        self.assertEqual(result['timestamp'], '2025-06-11T10:00:00+00:00')
        self.assertEqual(result['download_speed'], 100)
        self.assertEqual(result['upload_speed'], 30)
        self.assertEqual(result['ping'], 10)
        self.assertTrue(result['is_fast'])
        self.assertEqual(result['summary'], "Інтернет-з'єднання хороше.")


class SpeedTestLoggerTests(TestCase):
    def setUp(self):
        self.logger = SpeedTestLogger()
        self.test_data = {
            'timestamp': '2023-01-01T12:00:00',
            'download_speed': 100.5,
            'upload_speed': 50.2,
            'ping': 15.1,
            'is_fast': True,
            'summary': 'Good connection'
        }
        self.json_file = "test_results.json"
        self.csv_file = "test_results.csv"

    def tearDown(self):
        # Clean up test files
        if os.path.exists(self.json_file):
            os.remove(self.json_file)
        if os.path.exists(self.csv_file):
            os.remove(self.csv_file)

    def test_log_to_json_creates_file(self):
        # Test that log_to_json creates a JSON file with correct data
        self.logger.log_to_json(self.test_data, file_path=self.json_file)
        self.assertTrue(os.path.exists(self.json_file))

        with open(self.json_file, "r", encoding="utf-8") as f:
            logged_data = json.load(f)

        self.assertIsInstance(logged_data, list)
        self.assertEqual(len(logged_data), 1)
        self.assertAlmostEqual(logged_data[0]['download_speed'], self.test_data['download_speed'])
        self.assertAlmostEqual(logged_data[0]['ping'], self.test_data['ping'])

    def test_log_to_json_appends_to_existing_file(self):
        # Test that log_to_json appends data to an existing JSON file
        initial_data = {'timestamp': '2023-01-01T11:00:00', 'download_speed': 10, 'upload_speed': 5, 'ping': 50, 'is_fast': False, 'summary': 'Slow'}
        self.logger.log_to_json(initial_data, file_path=self.json_file)
        self.logger.log_to_json(self.test_data, file_path=self.json_file)

        with open(self.json_file, "r", encoding="utf-8") as f:
            logged_data = json.load(f)

        self.assertEqual(len(logged_data), 2)
        self.assertAlmostEqual(logged_data[0]['download_speed'], initial_data['download_speed'])
        self.assertAlmostEqual(logged_data[1]['download_speed'], self.test_data['download_speed'])

    def test_log_to_json_handles_empty_or_malformed_file(self):
        # Test that log_to_json handles an empty or malformed JSON file gracefully
        # Test behavior with an empty file first
        with open(self.json_file, "w", encoding="utf-8") as f:
            f.write("") # Create an empty JSON file
        self.logger.log_to_json(self.test_data, file_path=self.json_file)
        with open(self.json_file, "r", encoding="utf-8") as f:
            logged_data = json.load(f)
        self.assertEqual(len(logged_data), 1)
        self.assertAlmostEqual(logged_data[0]['download_speed'], self.test_data['download_speed'])

        # Now test with malformed JSON
        with open(self.json_file, "w", encoding="utf-8") as f:
            f.write("invalid json") # Create a malformed JSON file
        self.logger.log_to_json(self.test_data, file_path=self.json_file)
        with open(self.json_file, "r", encoding="utf-8") as f:
            logged_data = json.load(f)
        self.assertEqual(len(logged_data), 1)
        self.assertAlmostEqual(logged_data[0]['download_speed'], self.test_data['download_speed'])


    def test_log_to_csv_creates_file_with_header(self):
        # Test that log_to_csv creates a CSV file with a header and data
        self.logger.log_to_csv(self.test_data, file_path=self.csv_file)
        self.assertTrue(os.path.exists(self.csv_file))

        with open(self.csv_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 2) # Header + 1 data row
        self.assertIn("download_speed", lines[0]) # Check header
        # Check data using f-string to match potential float output in CSV
        self.assertIn(f"{self.test_data['download_speed']}", lines[1])

    def test_log_to_csv_appends_to_existing_file_without_duplicate_header(self):
        # Test that log_to_csv appends data to an existing CSV file without duplicating the header
        initial_data = {'timestamp': '2023-01-01T11:00:00', 'download_speed': 10, 'upload_speed': 5, 'ping': 50, 'is_fast': False, 'summary': 'Slow'}
        self.logger.log_to_csv(initial_data, file_path=self.csv_file)
        self.logger.log_to_csv(self.test_data, file_path=self.csv_file)

        with open(self.csv_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 3) # Header + 2 data rows
        self.assertIn("download_speed", lines[0]) # Header is present
        self.assertNotIn("download_speed", lines[1]) # Header is not duplicated in data row 1
        self.assertNotIn("download_speed", lines[2]) # Header is not duplicated in data row 2


class ViewsTestCase(DjangoTestCase):
    def setUp(self):
        self.client = Client()

    def test_index_view(self):
        # Test that the index view renders successfully and contains some expected content
        response = self.client.get(reverse('speedtest_app:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'speedtest_app/index.html')
        self.assertContains(response, "Internet Speed Test")

        # Optionally test that latest_results context is passed
        self.assertIn('latest_results', response.context)
        self.assertEqual(len(response.context['latest_results']), 0) # Initially no results

        # Add a result and check again
        SpeedTestResult.objects.create(download_speed=10, upload_speed=5, ping=20,
                                       server_name="Test", server_location="Loc", server_country="C")
        response = self.client.get(reverse('speedtest_app:index'))
        self.assertEqual(len(response.context['latest_results']), 1)


    # Fix: Corrected patch path for SpeedTestLogger
    @mock.patch("speedtest_app.views.SpeedTestLogger") # Patch SpeedTestLogger in views.py
    @mock.patch("speedtest.Speedtest")                 # Patch speedtest.Speedtest class
    def test_check_speed_mocked_success(self, mock_st_cls, mock_speedtest_logger_cls):
        # Arguments order: `mock_st_cls` comes from the last decorator, `mock_speedtest_logger_cls` from the first
        # So `mock_st_cls` is for speedtest.Speedtest
        # `mock_speedtest_logger_cls` is for speedtest_app.views.SpeedTestLogger

        # Configure the mock Speedtest instance
        mock_st_instance = mock_st_cls.return_value
        mock_st_instance.download.return_value = 100_000_000
        mock_st_instance.upload.return_value = 50_000_000
        mock_st_instance.results.ping = 5
        mock_st_instance.get_best_server.return_value = {
            'name': 'TestServer',
            'sponsor': 'TestSponsor',
            'country': 'TestCountry'
        }

        # Configure the mock SpeedTestLogger instance
        mock_speedtest_logger_instance = mock_speedtest_logger_cls.return_value
        # No need to configure return values for log_to_json/csv, just track calls

        # Ensure no SpeedTestResult objects exist before the test
        self.assertEqual(SpeedTestResult.objects.count(), 0)

        # Use GET request as per the current views.py
        response = self.client.get(reverse("speedtest_app:check_speed"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertAlmostEqual(data["download_speed"], 100.0, places=2)
        self.assertAlmostEqual(data["upload_speed"], 50.0, places=2)
        self.assertEqual(data["ping"], 5)
        self.assertTrue(data["is_fast"])
        self.assertEqual(data["summary"], "Інтернет-з'єднання хороше.")
        self.assertEqual(data["server_location"], "TestServer, TestCountry")

        # Verify that a SpeedTestResult object was created in the database
        self.assertEqual(SpeedTestResult.objects.count(), 1)
        result = SpeedTestResult.objects.first()
        self.assertAlmostEqual(result.download_speed, 100.0, places=2)
        self.assertAlmostEqual(result.upload_speed, 50.0, places=2)
        self.assertEqual(result.ping, 5)
        self.assertEqual(result.server_name, "TestServer")
        self.assertEqual(result.server_location, "TestServer, TestCountry")
        self.assertEqual(result.server_country, "TestCountry")

        # Verify that SpeedTestLogger methods were called
        self.assertTrue(mock_speedtest_logger_instance.log_to_json.called)
        self.assertTrue(mock_speedtest_logger_instance.log_to_csv.called)
        # You can add more specific assertions for call arguments if needed
        # For example: mock_speedtest_logger_instance.log_to_json.assert_called_once_with(mock.ANY, file_path="speedtest_results.json")


    @mock.patch("speedtest.Speedtest", side_effect=Exception("Mocked speedtest error"))
    def test_check_speed_handles_error(self, mock_speedtest):
        # Simulate a failure during speed test and ensure proper error response is returned
        response = self.client.get(reverse("speedtest_app:check_speed")) # Use GET
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Mocked speedtest error")
        self.assertEqual(SpeedTestResult.objects.count(), 0) # No DB entry on error

    def test_export_results_json(self):
        # Create some test data with distinct timestamps for reliable ordering
        SpeedTestResult.objects.create(
            download_speed=100,
            upload_speed=50,
            ping=10,
            server_name="Server1",
            server_location="Location1",
            server_country="Country1",
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=1) # Older record
        )
        SpeedTestResult.objects.create(
            download_speed=200,
            upload_speed=80,
            ping=5,
            server_name="Server2",
            server_location="Location2",
            server_country="Country2",
            timestamp=datetime.now(timezone.utc) # Newer record
        )
        response = self.client.get(reverse("speedtest_app:export_results", args=["json"]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2) # Check if all records are exported (up to 100)
        self.assertEqual(data[0]['download_speed'], 200.0) # Check ordering (latest first)
        self.assertEqual(data[1]['download_speed'], 100.0)


    def test_export_results_csv(self):
        # Create some test data
        SpeedTestResult.objects.create(
            download_speed=100,
            upload_speed=50,
            ping=10,
            server_name="Server1",
            server_location="Location1",
            server_country="Country1"
        )
        response = self.client.get(reverse("speedtest_app:export_results", args=["csv"]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn('attachment; filename="speedtest_results.csv"', response["Content-Disposition"])
        decoded_content = response.content.decode('utf-8')
        lines = decoded_content.strip().split('\n')
        self.assertEqual(len(lines), 2) # Header + 1 data row
        self.assertIn("Download (Mbps)", lines[0]) # Check header
        self.assertIn("100.0", lines[1]) # Check data - corrected to 100.0


    def test_export_results_invalid_format(self):
        # Test that an unsupported export format returns a 400 Bad Request response
        response = self.client.get(reverse("speedtest_app:export_results", args=["xml"]))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content.decode('utf-8'), "Invalid format")