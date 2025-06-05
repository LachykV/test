from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import speedtest
import logging
from .utils import SpeedTestAnalyzer
from django.http import JsonResponse, HttpResponse
import csv
from .models import SpeedTestResult

# Configure logger to track and report runtime errors
logger = logging.getLogger(__name__)


def index(request):
    """
    Render the homepage and display the 5 most recent internet speed test results.
    """
    latest_results = SpeedTestResult.objects.all()[:5]  # Retrieve the latest 5 entries from the database
    return render(request, 'speedtest_app/index.html', {'latest_results': latest_results})


@csrf_exempt
def check_speed(request):
    """
    Perform an internet speed test, analyze the results, store them in the database,
    and return a JSON response containing the measured values and analysis summary.
    """
    try:
        st = speedtest.Speedtest()

        # Identify the most optimal server based on latency
        st.get_best_server()
        server = st.get_best_server()

        # Format the server's name and country for easier user interpretation
        server_location = f"{server['name']}, {server['country']}"

        # Run the download and upload speed tests; convert from bits/sec to Mbps
        download_speed = st.download() / 1_000_000
        upload_speed = st.upload() / 1_000_000
        ping = st.results.ping

        # Analyze results using custom utility class
        analyzer = SpeedTestAnalyzer(download_speed, upload_speed, ping)
        analysis = analyzer.to_dict()

        # Save the results to JSON and CSV files (optional export step)
        analyzer.export_to_json()
        analyzer.export_to_csv()

        # Record the speed test results in the database
        SpeedTestResult.objects.create(
            download_speed=download_speed,
            upload_speed=upload_speed,
            ping=ping,
            server_name=server['name'],
            server_location=server['sponsor'],
            server_country=server['country']
        )

        # Respond to the client with key metrics and summary of the analysis
        return JsonResponse({
            'success': True,
            'download_speed': analysis['download_speed'],
            'upload_speed': analysis['upload_speed'],
            'ping': analysis['ping'],
            'is_fast': analysis['is_fast'],
            'summary': analysis['summary'],
            'server_location': server_location
        })

    except Exception as e:
        # Log the error message for debugging purposes and return a failure response
        logger.error(f"Speed test error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def export_results(request, format):
    """
    Export up to the 100 most recent speed test results in either JSON or CSV format.
    """
    results = SpeedTestResult.objects.all().order_by('-timestamp')[:100]  # Limit the export to the latest 100 records

    if format == 'json':
        # Convert queryset to a list of dictionaries and return as JSON
        data = list(results.values())
        return JsonResponse(data, safe=False)

    elif format == 'csv':
        # Prepare CSV file download with appropriate headers
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="speedtest_results.csv"'

        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'Download (Mbps)', 'Upload (Mbps)', 'Ping (ms)', 'Server Name', 'Location', 'Country'])

        # Write each result row into the CSV file
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

    # If the requested format is unsupported, return an error
    return HttpResponse("Invalid format", status=400)
