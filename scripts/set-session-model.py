#!/usr/bin/env python3
"""
Set session model via Telegram Bot API.

This script sends a /model command to the Telegram bot, which updates
the session-level model override in gateway memory.

Prerequisites:
1. Set TELEGRAM_BOT_TOKEN environment variable
2. Know your chat_id (can be found by messaging @userinfobot or similar)

Usage:
    # Direct switch using provider:model format
    ./scripts/set-session-model.py PROVIDER:MODEL CHAT_ID

    Examples:
        ./scripts/set-session-model.py openrouter:sonnet 123456789
        ./scripts/set-session-model.py nous:mimo "@hermes_bot"
"""

import sys
import os
import requests
from typing import Optional


def get_telegram_bot_token() -> str:
    """Get Telegram bot token from environment."""
    token = os.environ.get('TELEGRAM_BOT_TOKEN') or os.environ.get('TELEGRAM_TOKEN')
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set", file=sys.stderr)
        print("Set it with: export TELEGRAM_BOT_TOKEN='your_bot_token'", file=sys.stderr)
        sys.exit(1)
    return token


def send_telegram_message(bot_token: str, chat_id: str, message: str) -> bool:
    """Send a message to Telegram chat."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("ok"):
            return True
        else:
            print(f"Telegram API error: {data.get('description', 'Unknown error')}", file=sys.stderr)
            return False
    except requests.RequestException as e:
        print(f"Failed to send message: {e}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) < 3:
        print("Usage: ./scripts/set-session-model.py PROVIDER:MODEL CHAT_ID")
        print("")
        print("Examples:")
        print("  ./scripts/set-session-model.py openrouter:sonnet 123456789")
        print("  ./scripts/set-session-model.py nous:mimo '@hermes_bot'")
        print("")
        print("Environment variables required:")
        print("  TELEGRAM_BOT_TOKEN - Your Telegram bot token")
        sys.exit(1)

    # Parse arguments
    provider_model = sys.argv[1]
    chat_id = sys.argv[2]

    # Validate provider:model format
    if ':' not in provider_model:
        print("Error: First argument must be in PROVIDER:MODEL format")
        print("Example: openrouter:sonnet", file=sys.stderr)
        sys.exit(1)

    parts = provider_model.split(':', 1)
    provider, model = parts

    # Build /model command
    command = f"/model {model} --provider {provider}"

    print(f"Sending command: {command}")
    print(f"To chat: {chat_id}")

    # Get bot token
    bot_token = get_telegram_bot_token()

    # Send the /model command
    success = send_telegram_message(bot_token, chat_id, command)

    if success:
        print(f"✓ Successfully sent /model command to Telegram")
        print("  The session model will be updated once the bot processes the message.")
        print("  Check your Telegram chat for confirmation.")
    else:
        print("✗ Failed to send command", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
