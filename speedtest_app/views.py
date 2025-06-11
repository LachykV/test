from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import speedtest
import logging
from .utils import SpeedTestAnalyzer, SpeedTestLogger
from django.http import JsonResponse, HttpResponse
import csv
from .models import SpeedTestResult

logger = logging.getLogger(__name__)


def index(request):
    """
    Renders the homepage, displaying the 5 most recent internet speed test results from the database.
    """
    latest_results = SpeedTestResult.objects.all()[:5]
    return render(request, 'speedtest_app/index.html', {'latest_results': latest_results})


@csrf_exempt
def check_speed(request):
    """
    Performs an internet speed test, analyzes the results, stores them in the database,
    and returns a JSON response containing the measured values and analysis summary.
    """
    if request.method == 'GET':
        try:
            st = speedtest.Speedtest()

            # Identifies the most optimal server based on latency
            server = st.get_best_server()

            # Formats the server's name and country for display and storage
            server_full_location = f"{server['name']}, {server['country']}"

            # Runs download and upload speed tests, converting from bits/sec to Mbps
            download_speed = st.download() / 1_000_000
            upload_speed = st.upload() / 1_000_000
            ping = st.results.ping

            # Analyzes results using a custom utility class
            analyzer = SpeedTestAnalyzer(download_speed, upload_speed, ping)
            analysis = analyzer.to_dict()

            # Creates a logger instance and saves the results to JSON and CSV files
            logger_instance = SpeedTestLogger()
            logger_instance.log_to_json(analysis)
            logger_instance.log_to_csv(analysis)

            # Records the speed test results in the database
            SpeedTestResult.objects.create(
                download_speed=download_speed,
                upload_speed=upload_speed,
                ping=ping,
                server_name=server['name'],
                server_location=server_full_location,
                server_country=server['country']
            )

            # Responds to the client with key metrics and a summary of the analysis
            return JsonResponse({
                'success': True,
                'download_speed': analysis['download_speed'],
                'upload_speed': analysis['upload_speed'],
                'ping': analysis['ping'],
                'is_fast': analysis['is_fast'],
                'summary': analysis['summary'],
                'server_location': server_full_location
            })

        except Exception as e:
            # Logs the error message for debugging purposes and returns a failure response
            logger.error(f"Speed test error: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    else:
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


def export_results(request, format):
    """
    Exports up to the 100 most recent speed test results in either JSON or CSV format.
    """
    results = SpeedTestResult.objects.all().order_by('-timestamp')[:100]

    if format == 'json':
        # Converts the queryset to a list of dictionaries and returns it as a JSON response
        data = list(results.values())
        return JsonResponse(data, safe=False)

    elif format == 'csv':
        # Prepares a CSV file for download with appropriate headers
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="speedtest_results.csv"'

        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'Download (Mbps)', 'Upload (Mbps)', 'Ping (ms)', 'Server Name', 'Location', 'Country'])

        # Writes each result row into the CSV file
        for r in results:
            writer.writerow([
                r.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                round(r.download_speed, 2),
                round(r.upload_speed, 2),
                round(r.ping, 2),
                r.server_name,
                r.server_location,
                r.server_country
            ])
        return response

    # Returns an error if the requested format is unsupported
    return HttpResponse("Invalid format", status=400)