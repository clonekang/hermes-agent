#!/usr/bin/env python3
"""
External script to switch the model for Hermes Agent session.

This script provides an external interface to the /model command functionality,
allowing users to switch models from outside the CLI session using a Python script.

Usage:
    Direct mode (automatic):
        python scripts/change-model.py --direct provider:model       # Auto-switch with provider:model format
        python scripts/change-model.py -d anthropic:sonnet            # Short form

    Legacy mode (manual/interactive):
        python scripts/change-model.py <model-name>                   # Switch to model on current provider
        python scripts/change-model.py <model-name> --provider <name> # Switch with explicit provider
        python scripts/change-model.py                               # Interactive picker

Examples:
    Direct mode:
        python scripts/change-model.py --direct anthropic:sonnet      # Switch to Sonnet via Anthropic
        python scripts/change-model.py -d openai:gpt-5.4              # Switch to GPT-5.4 via OpenAI

    Legacy mode:
        python scripts/change-model.py sonnet                        # Switch to Sonnet on current provider
        python scripts/change-model.py qwen3.5:72b                   # Switch using colon syntax (legacy)
"""

import sys
import os
from pathlib import Path

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
        # Return defaults if no config exists
        return {
            'model': '',
            'provider': 'openrouter',
            'base_url': '',
        }

    try:
        import yaml
        with open(cfg_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Try to parse as YAML
        try:
            config = yaml.safe_load(content)
        except yaml.YAMLError:
            print("Warning: Config file has YAML syntax errors. Using defaults.", file=sys.stderr)
            return {
                'model': '',
                'provider': 'openrouter',
                'base_url': '',
            }

        if not config:
            return {
                'model': '',
                'provider': 'openrouter',
                'base_url': '',
            }

        model_config = config.get('model', {})

        # Handle both string and dict formats for model config
        if isinstance(model_config, str):
            # Format: model: "sonnet"
            return {
                'model': model_config,
                'provider': config.get('provider', 'openrouter') or 'openrouter',
                'base_url': '',
            }
        elif not isinstance(model_config, dict):
            model_config = {}

        current_model = model_config.get('default', '')
        current_provider = model_config.get('provider', '')
        current_base_url = model_config.get('base_url', '')

        return {
            'model': current_model,
            'provider': current_provider or 'openrouter',
            'base_url': current_base_url,
        }
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return {
            'model': '',
            'provider': 'openrouter',
            'base_url': '',
        }


def save_new_config(new_provider: str, new_model: str, base_url: str = "", api_key: str = ""):
    """Save the new model and provider to config."""
    hermes_home = get_hermes_home()
    cfg_path = hermes_home / "config.yaml"

    if not cfg_path.exists():
        print(f"Config file not found: {cfg_path}", file=sys.stderr)
        return False

    try:
        import yaml

        # Try to read and parse the config
        content = cfg_path.read_text(encoding='utf-8')
        try:
            config = yaml.safe_load(content)
            if not config or not isinstance(config, dict):
                config = {}
        except yaml.YAMLError:
            print("Warning: Config file has YAML errors. Creating new config structure.")
            config = {}

        # Ensure model section exists
        if 'model' not in config or not isinstance(config['model'], dict):
            config['model'] = {}

        # Update model configuration
        config['model']['provider'] = new_provider
        config['model']['default'] = new_model
        if base_url:
            config['model']['base_url'] = base_url
        if api_key:
            config['model']['api_key'] = api_key

        # Write back to config with proper YAML formatting
        cfg_path.write_text(yaml.dump(config, allow_unicode=True, default_flow_style=False), encoding='utf-8')

        return True
    except Exception as e:
        print(f"Error saving config: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def switch_model_external(raw_input: str, explicit_provider: str = "", global_flag: bool = False):
    """Core function to switch model using the shared pipeline."""

    # Suppress warnings from config loading
    import logging
    logging.getLogger('hermes_cli.config').setLevel(logging.ERROR)
    logging.getLogger('hermes_cli.runtime_provider').setLevel(logging.ERROR)

    # Load current configuration
    current_config = load_current_config()
    if current_config is None:
        print("Error: Could not load current configuration.", file=sys.stderr)
        return False

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
            full_config = yaml.safe_load(f)
        user_providers = full_config.get('providers', {}) or {}
        custom_providers = full_config.get('custom_providers', []) or []
    except Exception:
        pass

    # Use the shared model_switch pipeline
    from hermes_cli.model_switch import switch_model, parse_model_flags

    # Parse any flags from raw_input
    model_input, parsed_provider, parsed_global = parse_model_flags(raw_input)

    # Combine explicit provider with parsed one
    final_provider = explicit_provider or parsed_provider
    final_global = global_flag or parsed_global

    # Execute the switch
    result = switch_model(
        raw_input=model_input,
        current_provider=current_provider,
        current_model=current_model,
        current_base_url=current_base_url,
        current_api_key="",  # API key will be resolved internally
        is_global=final_global,
        explicit_provider=final_provider,
        user_providers=user_providers,
        custom_providers=custom_providers,
    )

    return result


def list_available_models():
    """List available providers and models for selection."""
    import logging
    logging.getLogger('hermes_cli.config').setLevel(logging.ERROR)
    logging.getLogger('hermes_cli.runtime_provider').setLevel(logging.ERROR)

    current_config = load_current_config()
    current_provider = current_config['provider'] if current_config else 'openrouter'

    hermes_home = get_hermes_home()
    cfg_path = hermes_home / "config.yaml"
    user_providers = {}
    custom_providers = []

    try:
        import yaml
        content = cfg_path.read_text(encoding='utf-8')
        full_config = yaml.safe_load(content) or {}
        user_providers = full_config.get('providers', {}) or {}
        custom_providers = full_config.get('custom_providers', []) or []
    except Exception:
        pass

    from hermes_cli.model_switch import list_authenticated_providers

    providers_list = list_authenticated_providers(
        current_provider=current_provider,
        user_providers=user_providers,
        custom_providers=custom_providers,
        max_models=10,
    )

    if not providers_list:
        print("No authenticated providers found. Please configure a provider first.")
        return None

    print("\nAvailable providers and models:\n")
    print(f"{'#':<3} {'Provider':<20} {'Models'}")
    print("-" * 80)

    for idx, provider in enumerate(providers_list, 1):
        slug = provider['slug']
        name = provider['name']
        is_current = " [CURRENT]" if provider.get('is_current') else ""
        models_str = ", ".join(provider.get('models', [])[:3])
        total = provider.get('total_models', 0)
        if total > 3:
            models_str += f" (+{total-3} more)"
        print(f"{idx:<3} {name}{is_current:<22} {models_str}")

    print()
    return providers_list


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Switch model for Hermes Agent session",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        epilog="""
Direct mode (automatic switch):
  %(prog)s --direct provider:model   Switch using provider:model format
  %(prog)s -d anthropic:sonnet       Short form

Legacy mode:
  %(prog)s sonnet                    Switch to Sonnet on current provider
  %(prog)s --global                  Show help
"""
    )
    parser.add_argument("--direct", "-d", metavar="PROVIDER:MODEL",
                        help="Direct switch using provider:model format (e.g., anthropic:sonnet)")
    parser.add_argument("model", nargs="?",
                        help="Model name or alias to switch to (legacy mode)")
    parser.add_argument("--provider", "-p",
                        help="Explicit provider to use (e.g., anthropic, openrouter)")
    parser.add_argument("--global", "-g", dest="persist_global", action="store_true",
                        help="Persist the model switch globally")

    args = parser.parse_args()

    # Direct mode: provider:model format for automatic switching
    if args.direct:
        print(f"Direct mode: Switching to {args.direct}")
        parts = args.direct.split(':', 1)
        if len(parts) != 2:
            print("Error: --direct requires provider:model format (e.g., anthropic:sonnet)", file=sys.stderr)
            sys.exit(1)

        direct_provider, direct_model = parts

        # Suppress warnings
        import logging
        logging.getLogger('hermes_cli.config').setLevel(logging.ERROR)
        logging.getLogger('hermes_cli.runtime_provider').setLevel(logging.ERROR)

        # Load current config
        current_config = load_current_config()
        if current_config is None:
            print("Error: Could not load current configuration.", file=sys.stderr)
            sys.exit(1)

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
                full_config = yaml.safe_load(f)
            user_providers = full_config.get('providers', {}) or {}
            custom_providers = full_config.get('custom_providers', []) or []
        except Exception:
            pass

        # Execute switch via shared pipeline
        from hermes_cli.model_switch import switch_model

        result = switch_model(
            raw_input=direct_model,
            current_provider=current_provider,
            current_model=current_model,
            current_base_url=current_base_url,
            current_api_key="",
            is_global=False,
            explicit_provider=direct_provider,
            user_providers=user_providers,
            custom_providers=custom_providers,
        )

        if not result.success:
            print(f"Error: {result.error_message}", file=sys.stderr)
            sys.exit(1)

        # Save to config
        if save_new_config(result.target_provider, result.new_model, result.base_url):
            print(f"✓ Switched to {result.provider_label}: {result.new_model}")
        else:
            print("✗ Failed to save configuration.", file=sys.stderr)
            sys.exit(1)
        return

    # Legacy mode: without --direct flag, use interactive/manual switching

    if not args.model:
        # Show available models interactively
        providers_list = list_available_models()
        if providers_list is None:
            sys.exit(1)
        print("\nSelect a provider number (or press Ctrl+C to cancel): ", end="", flush=True)
        try:
            choice = input().strip()
            if not choice.isdigit():
                print("Invalid selection.")
                return
            idx = int(choice) - 1
            if idx < 0 or idx >= len(providers_list):
                print("Invalid selection.")
                return
            selected = providers_list[idx]
            if not selected.get('models'):
                print(f"No models available for {selected['name']}")
                return
            model_to_use = selected['models'][0]  # Use first available model
            print(f"\nSwitching to: {selected['name']} -> {model_to_use}")
            args.model = model_to_use
            args.provider = selected['slug']
        except KeyboardInterrupt:
            print("\nCancelled.")
            return

    # Execute the model switch
    result = switch_model_external(args.model, args.provider or "", args.persist_global)

    # Handle case where result is False (boolean) instead of ModelSwitchResult
    if result is False:
        print("Error: Could not perform model switch.", file=sys.stderr)
        sys.exit(1)

    if not result.success:
        print(f"Error: {result.error_message}", file=sys.stderr)
        sys.exit(1)

    # Display result
    print(f"Switching to model: {result.new_model}")
    print(f"Provider: {result.provider_label} ({result.target_provider})")

    if result.resolved_via_alias:
        print(f"Resolved via alias: {result.resolved_via_alias}")

    if result.base_url:
        print(f"Base URL: {result.base_url}")

    if result.warning_message:
        print(f"Warning: {result.warning_message}")

    # Save to config
    if save_new_config(result.target_provider, result.new_model, result.base_url):
        print("")
        print("✓ Model switched successfully!")
    else:
        print("")
        print("✗ Failed to save configuration.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
