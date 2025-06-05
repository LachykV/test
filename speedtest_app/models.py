from django.db import models
from django.utils import timezone

class SpeedTestResult(models.Model):
    download_speed = models.FloatField()
    upload_speed = models.FloatField()
    ping = models.FloatField()
    timestamp = models.DateTimeField(default=timezone.now)
    server_location = models.CharField(max_length=255, blank=True)
    server_name = models.CharField(max_length=255, blank=True)
    server_country = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-timestamp']