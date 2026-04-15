#!/usr/bin/env python3
"""
Set session model via Telegram Bot API.

This script sends a /model command to the Telegram bot, which updates
the session-level model override in gateway memory.

Usage:
    ./scripts/set-session-model.py PROVIDER:MODEL CHAT_ID [--token BOT_TOKEN]

Examples:
    # Using token from environment/.env (auto-detected)
    ./scripts/set-session-model.py openrouter:sonnet 123456789

    # Explicitly specify bot token (useful for multi-bot setups)
    ./scripts/set-session-model.py nous:mimo "@hermes_bot" --token 123456:ABC-DEF...

Arguments:
    PROVIDER:MODEL  Model specification (e.g., openrouter:sonnet, nous:mimo)
    CHAT_ID         Telegram chat ID or username (e.g., 123456789 or @username)
    --token         Optional: explicitly specify bot token
"""

import sys
import os
import requests
from typing import Optional
from pathlib import Path


def get_telegram_bot_token(explicit_token: str = None) -> str:
    """Get Telegram bot token.

    Args:
        explicit_token: Token from --token argument (highest priority)

    Resolution order:
        1. explicit_token argument
        2. TELEGRAM_BOT_TOKEN / TELEGRAM_TOKEN environment variable
        3. ~/.hermes/.env file

    Returns:
        Bot token string

    Raises:
        SystemExit: If no token is found
    """
    # Priority 1: explicit --token argument
    if explicit_token:
        return explicit_token

    # Priority 2: environment variables
    token = os.environ.get('TELEGRAM_BOT_TOKEN') or os.environ.get('TELEGRAM_TOKEN')

    if not token:
        # Try to load from ~/.hermes/.env
        hermes_home = Path.home() / '.hermes'
        env_path = hermes_home / '.env'

        if env_path.exists():
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('TELEGRAM_BOT_TOKEN='):
                            token = line.split('=', 1)[1].strip().strip('"\'')
                            break
                        elif line.startswith('TELEGRAM_TOKEN='):
                            token = line.split('=', 1)[1].strip().strip('"\'')
                            break
            except Exception as e:
                print(f"Warning: Failed to read .env file: {e}", file=sys.stderr)

    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found", file=sys.stderr)
        print("  Set it with one of these methods:", file=sys.stderr)
        print("    1. Export environment variable: export TELEGRAM_BOT_TOKEN='your_bot_token'", file=sys.stderr)
        print("    2. Add to ~/.hermes/.env: TELEGRAM_BOT_TOKEN=your_bot_token", file=sys.stderr)
        print("    3. Use 'hermes config set TELEGRAM_BOT_TOKEN <token>' command", file=sys.stderr)
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
    import argparse

    parser = argparse.ArgumentParser(
        description="Send /model command to Telegram bot for session model switching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using token from environment/.env (auto-detected)
  ./scripts/set-session-model.py openrouter:sonnet 123456789

  # Explicitly specify bot token (useful for multi-bot setups)
  ./scripts/set-session-model.py nous:mimo "@hermes_bot" --token 123456:ABC-DEF...

Token Resolution Order:
  1. --token argument (highest priority)
  2. TELEGRAM_BOT_TOKEN / TELEGRAM_TOKEN environment variable
  3. ~/.hermes/.env file
        """)
    parser.add_argument("provider_model", metavar="PROVIDER:MODEL",
                        help="Model specification (e.g., openrouter:sonnet)")
    parser.add_argument("chat_id", help="Telegram chat ID or username")
    parser.add_argument("--token", "-t", metavar="BOT_TOKEN",
                        help="Explicitly specify Telegram bot token (overrides auto-detection)")

    args = parser.parse_args()

    provider_model = args.provider_model
    chat_id = args.chat_id

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

    # Get bot token (prioritize --token argument, then auto-detect)
    bot_token = get_telegram_bot_token(explicit_token=args.token)

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
