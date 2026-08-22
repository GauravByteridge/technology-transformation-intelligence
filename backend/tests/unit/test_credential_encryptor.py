"""
Unit tests for CredentialEncryptor.

Validates:
- Encrypt/decrypt round-trip preserves all fields
- Corrupted ciphertext raises CredentialDecryptionError (never silently swallowed)
- mask_config produces *_configured booleans and removes sensitive keys
- Non-sensitive fields preserved through all operations
- Constructor rejects empty/invalid Fernet key
"""

import pytest
from cryptography.fernet import Fernet

from app.security.credential_encryptor import (
    SENSITIVE_FIELDS,
    CredentialDecryptionError,
    CredentialEncryptor,
)


@pytest.fixture
def fernet_key() -> str:
    """Generate a valid Fernet key for testing."""
    return Fernet.generate_key().decode()


@pytest.fixture
def encryptor(fernet_key: str) -> CredentialEncryptor:
    """Create a CredentialEncryptor instance with a test key."""
    return CredentialEncryptor(fernet_key)


class TestConstructor:
    """Tests for CredentialEncryptor initialization."""

    def test_rejects_empty_key(self) -> None:
        """Empty string key raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            CredentialEncryptor("")

    def test_rejects_whitespace_only_key(self) -> None:
        """Whitespace-only key raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            CredentialEncryptor("   ")

    def test_rejects_invalid_key(self) -> None:
        """Non-base64 key raises ValueError."""
        with pytest.raises(ValueError, match="Invalid Fernet key"):
            CredentialEncryptor("not-a-valid-fernet-key")

    def test_accepts_valid_key(self, fernet_key: str) -> None:
        """Valid Fernet key creates encryptor successfully."""
        encryptor = CredentialEncryptor(fernet_key)
        assert encryptor is not None


class TestEncryptDecryptRoundTrip:
    """Tests for encrypt_config/decrypt_config round-trip preservation."""

    def test_round_trip_preserves_sensitive_fields(self, encryptor: CredentialEncryptor) -> None:
        """Encrypt then decrypt returns original sensitive values."""
        config = {
            "host": "db.example.com",
            "port": 5432,
            "password": "super-secret-password",
            "token": "my-api-token",
        }
        encrypted = encryptor.encrypt_config(config)
        decrypted = encryptor.decrypt_config(encrypted)

        assert decrypted == config

    def test_round_trip_preserves_all_sensitive_field_types(
        self, encryptor: CredentialEncryptor
    ) -> None:
        """All defined sensitive fields survive round-trip."""
        config = {
            "password": "pass123",
            "token": "tok456",
            "secret": "sec789",
            "api_key": "key000",
            "private_key": "pk111",
            "host": "example.com",
        }
        encrypted = encryptor.encrypt_config(config)
        decrypted = encryptor.decrypt_config(encrypted)

        assert decrypted == config

    def test_round_trip_preserves_non_sensitive_fields(
        self, encryptor: CredentialEncryptor
    ) -> None:
        """Non-sensitive fields pass through unchanged during encrypt/decrypt."""
        config = {"host": "db.example.com", "port": 5432, "database": "mydb"}
        encrypted = encryptor.encrypt_config(config)
        decrypted = encryptor.decrypt_config(encrypted)

        assert decrypted == config

    def test_encrypt_changes_sensitive_values(self, encryptor: CredentialEncryptor) -> None:
        """Sensitive values are actually different after encryption."""
        config = {"password": "my-password", "host": "localhost"}
        encrypted = encryptor.encrypt_config(config)

        assert encrypted["password"] != "my-password"
        assert encrypted["host"] == "localhost"

    def test_none_sensitive_values_preserved(self, encryptor: CredentialEncryptor) -> None:
        """None values in sensitive fields are not encrypted."""
        config = {"password": None, "host": "localhost"}
        encrypted = encryptor.encrypt_config(config)

        assert encrypted["password"] is None
        assert encrypted["host"] == "localhost"


class TestDecryptErrors:
    """Tests for decrypt_config error handling."""

    def test_raises_on_corrupted_ciphertext(self, encryptor: CredentialEncryptor) -> None:
        """Corrupted ciphertext raises CredentialDecryptionError."""
        config = {"password": "not-valid-ciphertext", "host": "localhost"}

        with pytest.raises(CredentialDecryptionError) as exc_info:
            encryptor.decrypt_config(config)

        assert exc_info.value.field_name == "password"

    def test_raises_on_tampered_ciphertext(self, encryptor: CredentialEncryptor) -> None:
        """Tampered (modified) ciphertext raises CredentialDecryptionError."""
        config = {"token": "my-token"}
        encrypted = encryptor.encrypt_config(config)

        # Tamper with the ciphertext
        encrypted["token"] = encrypted["token"][:-5] + "XXXXX"

        with pytest.raises(CredentialDecryptionError) as exc_info:
            encryptor.decrypt_config(encrypted)

        assert exc_info.value.field_name == "token"

    def test_raises_on_wrong_key(self, fernet_key: str) -> None:
        """Decrypting with a different key raises CredentialDecryptionError."""
        encryptor1 = CredentialEncryptor(fernet_key)
        encryptor2 = CredentialEncryptor(Fernet.generate_key().decode())

        config = {"password": "secret"}
        encrypted = encryptor1.encrypt_config(config)

        with pytest.raises(CredentialDecryptionError):
            encryptor2.decrypt_config(encrypted)


class TestMaskConfig:
    """Tests for mask_config producing *_configured booleans."""

    def test_produces_configured_booleans(self, encryptor: CredentialEncryptor) -> None:
        """Sensitive fields replaced with *_configured: True booleans."""
        config = {
            "password": "encrypted-value",
            "token": "encrypted-value",
            "host": "db.example.com",
        }
        masked = encryptor.mask_config(config)

        assert masked["password_configured"] is True
        assert masked["token_configured"] is True
        assert masked["host"] == "db.example.com"

    def test_removes_original_sensitive_keys(self, encryptor: CredentialEncryptor) -> None:
        """Original sensitive keys are removed from masked output."""
        config = {
            "password": "encrypted-value",
            "token": "encrypted-value",
            "secret": "encrypted-value",
            "api_key": "encrypted-value",
            "private_key": "encrypted-value",
        }
        masked = encryptor.mask_config(config)

        for field in SENSITIVE_FIELDS:
            assert field not in masked
            assert f"{field}_configured" in masked

    def test_none_value_produces_false(self, encryptor: CredentialEncryptor) -> None:
        """None sensitive value produces *_configured: False."""
        config = {"password": None, "host": "localhost"}
        masked = encryptor.mask_config(config)

        assert masked["password_configured"] is False
        assert masked["host"] == "localhost"

    def test_empty_string_produces_false(self, encryptor: CredentialEncryptor) -> None:
        """Empty string sensitive value produces *_configured: False."""
        config = {"password": "", "host": "localhost"}
        masked = encryptor.mask_config(config)

        assert masked["password_configured"] is False

    def test_preserves_non_sensitive_fields(self, encryptor: CredentialEncryptor) -> None:
        """Non-sensitive fields pass through unchanged in masked output."""
        config = {
            "host": "db.example.com",
            "port": 5432,
            "database": "mydb",
            "ssl": True,
        }
        masked = encryptor.mask_config(config)

        assert masked == config

    def test_all_sensitive_fields_masked(self, encryptor: CredentialEncryptor) -> None:
        """All five defined sensitive fields produce correct *_configured keys."""
        config = {
            "password": "val1",
            "token": "val2",
            "secret": "val3",
            "api_key": "val4",
            "private_key": "val5",
        }
        masked = encryptor.mask_config(config)

        assert masked == {
            "password_configured": True,
            "token_configured": True,
            "secret_configured": True,
            "api_key_configured": True,
            "private_key_configured": True,
        }
