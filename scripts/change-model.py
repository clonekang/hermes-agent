#!/usr/bin/env python3
"""
External script to switch the model for Hermes Agent.

IMPORTANT: This script modifies the GLOBAL default model in config.yaml,
NOT the session-level model override used by Telegram/gateway.

Session-level overrides are stored in the gateway process memory and cannot
be modified externally. To switch the model for an active Telegram session,
use `/model` command inside the Telegram chat itself.

Usage:
    Global mode (modifies config.yaml - affects ALL new sessions):
        python scripts/change-model.py --global provider:model   # Auto-switch + persist
        python scripts/change-model.py -g anthropic:sonnet        # Short form

Examples:
    # Switch global default model (affects new sessions)
    ./scripts/change-model.py --global openrouter:sonnet

    # To switch session model in active Telegram chat, use /model command
"""

import sys
import os
import logging
from pathlib import Path

# Suppress noisy logs
logging.getLogger('hermes_cli.config').setLevel(logging.ERROR)
logging.getLogger('hermes_cli.runtime_provider').setLevel(logging.ERROR)

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def get_hermes_home():
    """Get HERMES_HOME path."""
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))


def load_current_config():
    """Load the current model and provider from config."""
    hermes_home = get_hermes_home()
    cfg_path = hermes_home / "config.yaml"

    if not cfg_path.exists():
        return {'model': '', 'provider': 'openrouter', 'base_url': ''}

    try:
        import yaml
        content = cfg_path.read_text(encoding='utf-8')
        config = yaml.safe_load(content)
        if not config:
            return {'model': '', 'provider': 'openrouter', 'base_url': ''}

        model_cfg = config.get('model', {})
        if isinstance(model_cfg, str):
            return {
                'model': model_cfg,
                'provider': config.get('provider', 'openrouter') or 'openrouter',
                'base_url': '',
            }
        elif not isinstance(model_cfg, dict):
            model_cfg = {}

        return {
            'model': model_cfg.get('default', ''),
            'provider': model_cfg.get('provider', '') or 'openrouter',
            'base_url': model_cfg.get('base_url', ''),
        }
    except Exception as e:
        print(f"Warning: Error loading config: {e}", file=sys.stderr)
        return {'model': '', 'provider': 'openrouter', 'base_url': ''}


def save_global_config(new_provider: str, new_model: str, base_url: str = ""):
    """Save the new model and provider to config.yaml (GLOBAL change)."""
    hermes_home = get_hermes_home()
    cfg_path = hermes_home / "config.yaml"

    if not cfg_path.exists():
        print(f"Error: Config file not found: {cfg_path}", file=sys.stderr)
        return False

    try:
        import yaml
        content = cfg_path.read_text(encoding='utf-8')
        try:
            config = yaml.safe_load(content)
            if not config or not isinstance(config, dict):
                config = {}
        except yaml.YAMLError:
            print("Warning: Config file has YAML errors. Using empty config.")
            config = {}

        # Ensure model section exists as a dict
        if 'model' not in config:
            config['model'] = {}
        elif not isinstance(config['model'], dict):
            config['model'] = {}

        # Update model configuration
        config['model']['provider'] = new_provider
        config['model']['default'] = new_model
        if base_url:
            config['model']['base_url'] = base_url

        # Write back to config
        cfg_path.write_text(yaml.dump(config, allow_unicode=True, default_flow_style=False), encoding='utf-8')
        return True
    except Exception as e:
        print(f"Error saving config: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def switch_model_direct(provider: str, model: str, is_global: bool = True):
    """Switch model using the shared pipeline from hermes_cli.model_switch."""

    # Load current configuration
    current_config = load_current_config()

    current_provider = current_config['provider'] or 'openrouter'
    current_model = current_config['model'] or ''
    current_base_url = current_config.get('base_url', '')

    # Load config for custom providers
    hermes_home = get_hermes_home()
    cfg_path = hermes_home / "config.yaml"
    user_providers = {}
    custom_providers = []

    try:
        import yaml
        with open(cfg_path, 'r', encoding='utf-8') as f:
            full_config = yaml.safe_load(f) or {}
        user_providers = full_config.get('providers', {}) or {}
        custom_providers = full_config.get('custom_providers', []) or []
    except Exception:
        pass

    # Use the shared model_switch pipeline
    from hermes_cli.model_switch import switch_model

    result = switch_model(
        raw_input=model,
        current_provider=current_provider,
        current_model=current_model,
        current_base_url=current_base_url,
        current_api_key="",
        is_global=is_global,
        explicit_provider=provider,
        user_providers=user_providers,
        custom_providers=custom_providers,
    )

    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Switch model for Hermes Agent (GLOBAL mode - modifies config.yaml)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        epilog="""
IMPORTANT: This script modifies the GLOBAL default model in config.yaml.
It does NOT affect active Telegram sessions. Session-level overrides are stored
in gateway memory and cannot be modified externally.

Usage:
  %(prog)s --global PROVIDER:MODEL   Switch global default (e.g., -g openrouter:sonnet)
  %(prog)s -g PROVIDER:MODEL          Short form

Examples:
  %(prog)s -g openrouter:sonnet       Switch to Sonnet via OpenRouter
  %(prog)s -g nous:mimo               Switch to MiMo via Nous Portal

To switch model for an ACTIVE Telegram session, use `/model` command in chat.
"""
    )
    parser.add_argument("--global", "-g", dest="global_mode", metavar="PROVIDER:MODEL",
                        help="Switch global default using provider:model format (e.g., anthropic:sonnet)")

    args = parser.parse_args()

    if not args.global_mode:
        print("Usage: %(prog)s --global PROVIDER:MODEL")
        print("")
        print("Example:")
        print("  %(prog)s -g openrouter:sonnet")
        print("  %(prog)s -g nous:mimo")
        print("")
        print("This switches the GLOBAL default model in config.yaml.")
        print("For active Telegram sessions, use `/model` command in the chat.")
        sys.exit(1)

    # Parse provider:model
    parts = args.global_mode.split(':', 1)
    if len(parts) != 2:
        print("Error: --global requires PROVIDER:MODEL format (e.g., openrouter:sonnet)", file=sys.stderr)
        sys.exit(1)

    provider, model = parts
    print(f"Switching global default to {provider}:{model}")

    # Execute switch
    result = switch_model_direct(provider, model, is_global=True)

    if not result.success:
        print(f"Error: {result.error_message}", file=sys.stderr)
        sys.exit(1)

    # Save to config
    if save_global_config(result.target_provider, result.new_model, result.base_url):
        print(f"✓ Global default switched to {result.provider_label}: {result.new_model}")
        print("  (This affects NEW sessions. Active Telegram sessions are not affected.)")
        print("  To switch an active session's model, use `/model` command in the chat.")
    else:
        print("✗ Failed to save configuration.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
