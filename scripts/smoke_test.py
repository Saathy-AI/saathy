"""Smoke test for the Saathy application."""

import argparse
import json
import sys
import time
from http import HTTPStatus

import requests
from colorama import Fore, Style, init
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


def main() -> None:
    """Run the smoke test."""
    init(autoreset=True)
    parser = create_parser()
    args = parser.parse_args()

    print_info(f"🚀 Starting smoke test for {args.base_url}...")

    session = create_session_with_retries()
    health_check_url = f"{args.base_url}/healthz"
    max_response_time = args.timeout

    try:
        start_time = time.monotonic()
        response = session.get(health_check_url, timeout=args.timeout)
        end_time = time.monotonic()
        response_time = end_time - start_time

        check_response_status(response)
        check_response_time(response_time, max_response_time)
        check_health_payload(response)

        print_success("✅ Smoke test passed successfully!")
        sys.exit(0)

    except requests.exceptions.RequestException as e:
        print_error(f"Failed to connect to the server: {e}")
        sys.exit(1)
    except AssertionError as e:
        print_error(f"Smoke test failed: {e}")
        sys.exit(1)


def create_parser() -> argparse.ArgumentParser:
    """Create a command-line argument parser."""
    parser = argparse.ArgumentParser(description="Saathy API Smoke Test")
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000",
        help="Base URL of the API to test",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=1.0,
        help="Timeout for requests in seconds",
    )
    return parser


def create_session_with_retries() -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def check_response_status(response: requests.Response) -> None:
    """Check if the response status is OK."""
    assert (
        response.status_code == HTTPStatus.OK
    ), f"Expected status code {HTTPStatus.OK}, but got {response.status_code}."
    print_success("✓ Status code is OK (200)")


def check_response_time(response_time: float, max_response_time: float) -> None:
    """Check if the response time is within the allowed limit."""
    assert (
        response_time <= max_response_time
    ), f"Response time {response_time:.4f}s exceeds the limit of {max_response_time}s."
    print_success(f"✓ Response time is {response_time:.4f}s (within limit)")


def check_health_payload(response: requests.Response) -> None:
    """Check the health check JSON payload."""
    try:
        payload = response.json()
    except json.JSONDecodeError as e:
        raise AssertionError("Response is not valid JSON.") from e

    assert (
        payload.get("status") == "healthy"
    ), f"Expected status 'healthy', but got '{payload.get('status')}'."
    print_success("✓ API status is healthy")

    dependencies = payload.get("dependencies", {})
    qdrant_status = dependencies.get("qdrant")
    assert (
        qdrant_status == "healthy"
    ), f"Expected Qdrant status 'healthy', but got '{qdrant_status}'."
    print_success("✓ Qdrant dependency is healthy")


def print_info(message: str) -> None:
    """Print an informational message."""
    print(f"{Style.BRIGHT}{message}{Style.RESET_ALL}")


def print_success(message: str) -> None:
    """Print a success message in green."""
    print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")


def print_error(message: str) -> None:
    """Print an error message in red."""
    print(f"{Fore.RED}{message}{Style.RESET_ALL}", file=sys.stderr)


if __name__ == "__main__":
    main()
