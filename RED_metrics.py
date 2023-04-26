from google.cloud import logging_v2
from google.oauth2 import service_account
import numpy as np
import datetime


def calculate_metrics():
    """Calculates RED metrics for the past 24 hours from the time it was called."""
    # Authenticate with service account key file
    creds = service_account.Credentials.from_service_account_file('google-credentials.json')

    # Create a logging client object
    client = logging_v2.Client(credentials=creds)

    # Set the time range to get the logs for the last 24 hours
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(hours=24)

    # Convert the time range to the correct format
    start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    # Construct a filter expression
    filter_exp = 'resource.type=gae_app AND logName=projects/{project_name}/logs/{type} AND ' \
                 f'timestamp >= "{start_time_str}" AND timestamp <= "{end_time_str}"'

    # Call the API to fetch logs
    results = client.list_entries(filter_=filter_exp)

    # Initialize counters for requests and errors
    num_requests = 0
    num_errors = 0

    # Initialize list for request durations
    request_durations = []

    # Iterate over log entries and extract relevant data
    for log_entry in results:
        # Extract HTTP status code from log entry
        entry = log_entry.to_api_repr()
        if 'response_status' in entry['jsonPayload']:
            http_status = int(entry['jsonPayload']['response_status'])

            # If HTTP status code is in the 200-299 range, count it as a successful request
            if 200 <= http_status < 300:
                num_requests += 1
            else:
                num_errors += 1

            # Compute duration of request and add to list
            duration = entry['jsonPayload']['response_time_ms']
            request_durations.append(duration)

    # Calculate p95 latency
    p95_latency = np.percentile(request_durations, 95)

    return [num_requests, num_errors, p95_latency]
