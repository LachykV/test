import json
import csv
import os
from datetime import datetime


class SpeedTestResultData:
    """
    Helper class for storing speed test results.
    Stores download speed, upload speed, ping, and the timestamp of the test.
    """
    def __init__(self, download_speed: float, upload_speed: float, ping: float):
        self.download_speed = download_speed
        self.upload_speed = upload_speed
        self.ping = ping
        self.timestamp = datetime.now()

    def as_dict(self):
        # Returns the result as a dictionary for later use (e.g., logging)
        return {
            'timestamp': self.timestamp.isoformat(),
            'download_speed': round(self.download_speed, 2),
            'upload_speed': round(self.upload_speed, 2),
            'ping': round(self.ping, 2)
        }


class SpeedTestLogger:
    """
    Logger class to save speed test results into JSON or CSV files.
    Supports appending new results to an existing log or creating a new one.
    """
    def log_to_json(self, data: dict, file_path="speedtest_results.json"):
        # Appends result to a JSON file; creates the file if it doesn't exist.
        if os.path.exists(file_path):
            with open(file_path, "r+", encoding="utf-8") as f:
                try:
                    # Try loading existing data from the file
                    existing = json.load(f)
                except json.JSONDecodeError:
                    # If file is empty or corrupted, initialize with an empty list
                    existing = []
                existing.append(data)
                f.seek(0)
                json.dump(existing, f, indent=2, ensure_ascii=False)
        else:
            # If the file does not exist, create it and write the first entry as a list
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump([data], f, indent=2, ensure_ascii=False)

    def log_to_csv(self, data: dict, file_path="speedtest_results.csv"):
        # Appends result to a CSV file; writes headers only if file is empty or new
        write_header = not os.path.isfile(file_path) or os.path.getsize(file_path) == 0
        with open(file_path, mode='a', newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            if write_header:
                writer.writeheader()
            writer.writerow(data)


class SpeedTestAnalyzer:
    """
    Core class for analyzing the speed test results.
    Provides evaluation methods and export functionalities.
    """
    def __init__(self, download_speed, upload_speed, ping, timestamp=None):
        self.download_speed = download_speed
        self.upload_speed = upload_speed
        self.ping = ping

    def is_fast_connection(self):
        # Determines whether the connection is considered fast based on thresholds:
        # download >= 50 Mbps, upload >= 20 Mbps, ping <= 50 ms
        return self.download_speed >= 50 and self.upload_speed >= 20 and self.ping <= 50

    def summary(self):
        # Returns a textual assessment of the internet connection quality
        if self.is_fast_connection():
            return "Інтернет-з'єднання хороше."
        return "Інтернет-з'єднання повільне або нестабільне."

    def to_dict(self):
        # Returns a dictionary with all test parameters, evaluation, and current timestamp
        return {
            'timestamp': datetime.now().isoformat(),
            'download_speed': round(self.download_speed, 2),
            'upload_speed': round(self.upload_speed, 2),
            'ping': round(self.ping, 2),
            'is_fast': self.is_fast_connection(),
            'summary': self.summary()
        }

    def export_to_json(self, file_path="speedtest_results.json"):
        # Exports the current analysis to a JSON file using SpeedTestLogger
        logger = SpeedTestLogger()
        logger.log_to_json(self.to_dict(), file_path)

    def export_to_csv(self, file_path="speedtest_results.csv"):
        # Exports the current analysis to a CSV file using SpeedTestLogger
        logger = SpeedTestLogger()
        logger.log_to_csv(self.to_dict(), file_path)
