"""
Configuration module — environment-variable-driven settings.

SECURITY INVARIANT: All configuration values, especially secrets, are loaded
exclusively from environment variables via pydantic-settings. No config files,
no CLI arguments, no hard-coded defaults for sensitive values.

The Settings class (settings.py) validates that all required variables are
present at startup. Missing required secrets cause a startup failure with
a clear error message identifying which variable is absent — without
revealing expected values.
"""
