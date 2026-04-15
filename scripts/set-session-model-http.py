#!/usr/bin/env python3
"""
Set session model via HTTP API.

This script sends a POST request to the Hermes Agent management API
to set the session-level model override.

Prerequisites:
1. Gateway must be running with management server enabled
   (GATEWAY_MANAGEMENT_SERVER=1 or gateway.management_server_port in config)
2. Know your session_key (format: "platform:chat_id", e.g., "telegram:123456789")

Usage:
    ./scripts/set-session-model-http.py SESSION_KEY PROVIDER MODEL

Examples:
    # Set model for Telegram session
    ./scripts/set-session-model-http.py "telegram:123456789" openrouter sonnet

    # Set model using provider:model format
    ./scripts/set-session-model-http.py "telegram:@hermes_bot" nous mimo

Environment variables:
    GATEWAY_MANAGEMENT_URL - Management API URL (default: http://localhost:8080)
"""

import sys
import os
import requests
from typing import Optional


def get_management_url() -> str:
    """Get management API URL from environment or default."""
    url = os.environ.get('GATEWAY_MANAGEMENT_URL', 'http://localhost:8080')
    return url.rstrip('/')


def set_session_model(session_key: str, provider: str, model: str, api_url: str) -> bool:
    """Set session model via HTTP API."""
    endpoint = f"{api_url}/admin/sessions/{session_key}/model"

    payload = {
        "provider": provider,
        "model": model
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return True
            else:
                print(f"API error: {data.get('error', 'Unknown error')}", file=sys.stderr)
                return False
        elif response.status_code == 404:
            print(f"Error: Session '{session_key}' not found", file=sys.stderr)
            print("  Make sure the session exists and gateway is running.", file=sys.stderr)
            return False
        else:
            print(f"API request failed with status {response.status_code}", file=sys.stderr)
            print(response.text, file=sys.stderr)
            return False
    except requests.RequestException as e:
        print(f"Failed to connect to management API: {e}", file=sys.stderr)
        print(f"  Check that gateway is running with management server enabled.", file=sys.stderr)
        print(f"  Set GATEWAY_MANAGEMENT_SERVER=1 or configure in config.yaml", file=sys.stderr)
        return False


def main():
    if len(sys.argv) < 4:
        print("Usage: ./scripts/set-session-model-http.py SESSION_KEY PROVIDER MODEL")
        print("")
        print("Examples:")
        print('  ./scripts/set-session-model-http.py "telegram:123456789" openrouter sonnet')
        print('  ./scripts/set-session-model-http.py "telegram:@hermes_bot" nous mimo')
        print("")
        print("Environment variables:")
        print("  GATEWAY_MANAGEMENT_URL - Management API URL (default: http://localhost:8080)")
        sys.exit(1)

    # Parse arguments
    session_key = sys.argv[1]
    provider = sys.argv[2]
    model = sys.argv[3]

    # Get management URL
    api_url = get_management_url()

    print(f"Setting model for session: {session_key}")
    print(f"Provider: {provider}")
    print(f"Model: {model}")
    print(f"API URL: {api_url}")

    # Set session model
    success = set_session_model(session_key, provider, model, api_url)

    if success:
        print(f"✓ Successfully set session model")
        print("  The new model will be used for the next message in this session.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
