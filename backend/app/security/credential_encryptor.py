"""
Fernet-based credential encryption for data source connection configs.

Encrypts sensitive fields (passwords, tokens, API keys) before persistence
and decrypts them only within the controlled connector execution path.
API responses use mask_config() which never exposes plaintext credentials.

Security boundary:
- encrypt_config() → called before storing to database
- decrypt_config() → called ONLY at connector execution boundary (Phase 2)
- mask_config() → called for ALL API responses (produces *_configured booleans)
"""

from cryptography.fernet import Fernet, InvalidToken


class CredentialDecryptionError(Exception):
    """
    Raised when decryption of a credential field fails.

    This indicates corrupted ciphertext, key rotation issues, or data
    tampering. NEVER silently swallowed — callers must handle explicitly.
    """

    def __init__(self, field_name: str, detail: str | None = None) -> None:
        self.field_name = field_name
        self.detail = detail
        message = f"Failed to decrypt field '{field_name}'"
        if detail:
            message += f": {detail}"
        super().__init__(message)


# Fields considered sensitive — values are encrypted at rest and masked in responses
SENSITIVE_FIELDS: frozenset[str] = frozenset(
    {"password", "token", "secret", "api_key", "api_token", "private_key"}
)


class CredentialEncryptor:
    """
    Encrypts and decrypts sensitive fields in connection config dictionaries.

    Constructor validates the Fernet key eagerly — an invalid key raises
    ValueError immediately rather than failing later during encrypt/decrypt.
    """

    def __init__(self, fernet_key: str) -> None:
        """
        Initialize with a base64-encoded Fernet key.

        Raises:
            ValueError: If fernet_key is empty or not a valid Fernet key.
        """
        if not fernet_key or not fernet_key.strip():
            raise ValueError("Fernet key must not be empty")

        try:
            self._fernet = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
        except (ValueError, Exception) as exc:
            raise ValueError(f"Invalid Fernet key: {exc}") from exc

    def encrypt_config(self, config: dict) -> dict:
        """
        Encrypt sensitive field values in a connection config dictionary.

        Non-sensitive fields are passed through unchanged. Sensitive field
        values are replaced with their Fernet-encrypted ciphertext (as str).

        Args:
            config: Connection config dictionary with potential sensitive fields.

        Returns:
            New dictionary with sensitive values encrypted.
        """
        result: dict = {}
        for key, value in config.items():
            if key in SENSITIVE_FIELDS and value is not None:
                encrypted = self._fernet.encrypt(str(value).encode())
                result[key] = encrypted.decode()
            else:
                result[key] = value
        return result

    def decrypt_config(self, config: dict) -> dict:
        """
        Decrypt sensitive field values in a connection config dictionary.

        Non-sensitive fields are passed through unchanged. Raises
        CredentialDecryptionError on any decryption failure — NEVER
        silently swallows corrupted data.

        Args:
            config: Connection config dictionary with encrypted sensitive fields.

        Returns:
            New dictionary with sensitive values decrypted.

        Raises:
            CredentialDecryptionError: If any sensitive field cannot be decrypted.
        """
        result: dict = {}
        for key, value in config.items():
            if key in SENSITIVE_FIELDS and value is not None:
                try:
                    decrypted = self._fernet.decrypt(value.encode())
                    result[key] = decrypted.decode()
                except (InvalidToken, Exception) as exc:
                    raise CredentialDecryptionError(
                        field_name=key,
                        detail=str(exc),
                    ) from exc
            else:
                result[key] = value
        return result

    def mask_config(self, config: dict) -> dict:
        """
        Produce a masked version of a connection config for API responses.

        Sensitive fields are REMOVED and replaced with explicit
        *_configured boolean indicators. Non-sensitive fields are
        preserved unchanged.

        Example:
            {"host": "db.example.com", "password": "gAAAAAB..."} →
            {"host": "db.example.com", "password_configured": True}

        Args:
            config: Connection config dictionary (may contain encrypted values).

        Returns:
            New dictionary with sensitive keys removed and *_configured booleans added.
        """
        result: dict = {}
        for key, value in config.items():
            if key in SENSITIVE_FIELDS:
                # Replace sensitive field with a boolean presence indicator
                result[f"{key}_configured"] = value is not None and value != ""
            else:
                result[key] = value
        return result
