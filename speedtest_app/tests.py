import json
import os
import tempfile
from django.test import TestCase as DjangoTestCase, Client
from django.urls import reverse
from unittest import mock, TestCase
from .models import SpeedTestResult
from .utils import SpeedTestAnalyzer, SpeedTestResultData, SpeedTestLogger

class SpeedTestAnalyzerTests(TestCase):
    def setUp(self):
        # Initialize the analyzer with typical good connection values
        self.analyzer = SpeedTestAnalyzer(download_speed=100, upload_speed=30, ping=10)

    def test_is_fast_connection_true(self):
        # Test that the analyzer correctly identifies a fast connection
        self.assertTrue(self.analyzer.is_fast_connection())

    def test_summary_good_connection(self):
        # Test that the summary message for a good connection is correct
        self.assertEqual(self.analyzer.summary(), "Інтернет-з'єднання хороше.")

    def test_summary_poor_connection(self):
        # Test the summary message when the connection is slow or unstable
        analyzer = SpeedTestAnalyzer(download_speed=10, upload_speed=5, ping=100)
        self.assertEqual(analyzer.summary(), "Інтернет-з'єднання повільне або нестабільне.")

    def test_to_dict_structure(self):
        # Test that the output dictionary from to_dict contains all expected keys
        result = self.analyzer.to_dict()
        self.assertIn('download_speed', result)
        self.assertIn('upload_speed', result)
        self.assertIn('ping', result)
        self.assertIn('is_fast', result)
        self.assertIn('summary', result)

    def test_export_to_json_creates_file(self):
        # Test that export_to_json creates a valid JSON file with the correct structure
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as temp_file:
            self.analyzer.export_to_json(file_path=temp_file.name)
            temp_file.seek(0)
            content = json.load(temp_file)
        os.unlink(temp_file.name)  # Clean up the file afterward
        self.assertIsInstance(content, list)
        self.assertIsInstance(content[0], dict)
        self.assertEqual(content[0]['is_fast'], True)

    def test_export_to_csv_creates_file(self):
        # Test that export_to_csv writes a file with at least a header and one data line
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            temp_file_name = temp_file.name

        self.analyzer.export_to_csv(file_path=temp_file_name)

        with open(temp_file_name, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        os.unlink(temp_file_name)  # Remove the file after reading
        self.assertGreater(len(lines), 1)  # Should be more than 1 line: header + data


class SpeedTestLoggerTests(DjangoTestCase):
    def test_log_result_creates_db_entry(self):
        # Test that log_to_json creates a JSON file with a dictionary structure and required keys
        data = SpeedTestResultData(100, 50, 5)
        SpeedTestLogger().log_to_json(data.as_dict(), file_path="test_result.json")

        self.assertTrue(os.path.exists("test_result.json"))  # Ensure file was created

        with open("test_result.json", "r", encoding="utf-8") as f:
            logged_data = json.load(f)

        os.remove("test_result.json")  # Clean up after test

        self.assertIsInstance(logged_data, list)
        self.assertIn("download_speed", logged_data[0])
        self.assertIn("timestamp", logged_data[0])


class ViewsTestCase(DjangoTestCase):
    def setUp(self):
        # Initialize Django test client for making requests to views
        self.client = Client()

    @mock.patch("speedtest.Speedtest")
    def test_check_speed_mocked(self, mock_speedtest):
        # Simulate speed test and test if API responds correctly with mocked values
        instance = mock_speedtest.return_value
        instance.download.return_value = 100_000_000
        instance.upload.return_value = 50_000_000
        instance.results.ping = 5
        instance.get_best_server.return_value = {
            'name': 'TestServer',
            'sponsor': 'TestSponsor',
            'country': 'TestCountry'
        }

        response = self.client.post(reverse("speedtest_app:check_speed"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("download_speed", data)
        self.assertIn("upload_speed", data)
        self.assertIn("ping", data)
        self.assertIn("summary", data)

    @mock.patch("speedtest.Speedtest", side_effect=Exception("Mocked error"))
    def test_check_speed_handles_error(self, mock_speedtest):
        # Simulate a failure during speed test and ensure proper error response is returned
        response = self.client.post(reverse("speedtest_app:check_speed"))
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("error", data)

    def test_export_results_json(self):
        # Test that JSON export endpoint returns correct data format and status
        SpeedTestResult.objects.create(
            download_speed=100,
            upload_speed=50,
            ping=10,
            server_name="Server1",
            server_location="Location1",
            server_country="Country1"
        )
        response = self.client.get(reverse("speedtest_app:export_results", args=["json"]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_export_results_csv(self):
        # Test that CSV export endpoint returns response with proper MIME type
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

    def test_export_results_invalid_format(self):
        # Test that an unsupported export format returns a 400 Bad Request response
        response = self.client.get(reverse("speedtest_app:export_results", args=["xml"]))
        self.assertEqual(response.status_code, 400)
