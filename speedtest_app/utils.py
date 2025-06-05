import json
import csv
import os
from datetime import datetime

class SpeedTestAnalyzer:
    def __init__(self, download_speed, upload_speed, ping):
        # Initialize speed test results
        self.download_speed = download_speed
        self.upload_speed = upload_speed
        self.ping = ping

    def is_fast_connection(self):
        # Define what qualifies as a "fast" internet connection
        return self.download_speed >= 50 and self.upload_speed >= 20 and self.ping <= 50

    def summary(self):
        # Provide a human-readable summary of the connection quality
        if self.is_fast_connection():
            return "Інтернет-з'єднання хороше."
        return "Інтернет-з'єднання повільне або нестабільне."

    def to_dict(self):
        # Return the test results as a dictionary, with formatted values
        return {
            'timestamp': datetime.now().isoformat(),
            'download_speed': round(self.download_speed, 2),
            'upload_speed': round(self.upload_speed, 2),
            'ping': round(self.ping, 2),
            'is_fast': self.is_fast_connection(),
            'summary': self.summary()
        }

    def export_to_json(self, file_path="speedtest_results.json"):
        # Export the test results to a JSON file
        data = self.to_dict()
        if os.path.exists(file_path):
            # If file exists, load existing data and append the new result
            with open(file_path, "r+", encoding="utf-8") as f:
                try:
                    existing = json.load(f)
                except json.JSONDecodeError:
                    existing = []
                existing.append(data)
                f.seek(0)
                json.dump(existing, f, indent=2, ensure_ascii=False)
        else:
            # If file doesn't exist, create it with the current result
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump([data], f, indent=2, ensure_ascii=False)

    def export_to_csv(self, file_path="speedtest_results.csv"):
        # Export the test results to a CSV file
        data = self.to_dict()
        file_exists = os.path.isfile(file_path)
        with open(file_path, mode='a', newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            if not file_exists:
                # Write headers if the file is new
                writer.writeheader()
            writer.writerow(data)
