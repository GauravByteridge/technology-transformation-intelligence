"""Unit tests for app.connectors.sanitizer module."""

import pytest
from app.connectors.sanitizer import sanitize_message


class TestSanitizeMessage:
    def test_password_assignment_redacted(self):
        assert "secret" not in sanitize_message("password=secret123 host=db.example.com")
        assert "[REDACTED]" in sanitize_message("password=secret123")

    def test_password_colon_redacted(self):
        assert "mysecret" not in sanitize_message("password: mysecret")
        assert "[REDACTED]" in sanitize_message("password: mysecret")

    def test_api_key_redacted(self):
        assert "mykey" not in sanitize_message("api_key=mykey123")
        assert "[REDACTED]" in sanitize_message("api_key=mykey123")

    def test_api_key_hyphen_redacted(self):
        assert "abc" not in sanitize_message("api-key=abc")
        assert "[REDACTED]" in sanitize_message("api-key=abc")

    def test_secret_key_redacted(self):
        assert "skey" not in sanitize_message("secret_key=skey999")
        assert "[REDACTED]" in sanitize_message("secret_key=skey999")

    def test_token_redacted(self):
        assert "tok123" not in sanitize_message("token=tok123")
        assert "[REDACTED]" in sanitize_message("token=tok123")

    def test_bearer_redacted(self):
        assert "bearval" not in sanitize_message("bearer=bearval")
        assert "[REDACTED]" in sanitize_message("bearer=bearval")

    def test_private_key_redacted(self):
        assert "pkey" not in sanitize_message("private_key=pkey123")
        assert "[REDACTED]" in sanitize_message("private_key=pkey123")

    def test_postgresql_uri_redacted(self):
        msg = "failed: postgresql://admin:supersecret@db.example.com:5432/mydb"
        result = sanitize_message(msg)
        assert "supersecret" not in result
        assert "admin" not in result
        assert "[REDACTED]" in result

    def test_mongodb_uri_redacted(self):
        msg = "error connecting mongodb://user:pass123@mongo.host:27017"
        result = sanitize_message(msg)
        assert "pass123" not in result
        assert "[REDACTED]" in result

    def test_mongodb_srv_uri_redacted(self):
        msg = "mongodb+srv://admin:secret@cluster.mongodb.net failed"
        result = sanitize_message(msg)
        assert "secret" not in result
        assert "[REDACTED]" in result

    def test_no_credentials_unchanged(self):
        msg = "Connection refused to host db.example.com port 5432"
        assert sanitize_message(msg) == msg

    def test_plain_error_message_unchanged(self):
        msg = "timeout after 30 seconds waiting for response"
        assert sanitize_message(msg) == msg

    def test_multiple_patterns(self):
        msg = "password=abc token=xyz postgresql://u:p@h:5432"
        result = sanitize_message(msg)
        assert "abc" not in result
        assert "xyz" not in result
        assert "u:p" not in result

    def test_case_insensitive(self):
        assert "[REDACTED]" in sanitize_message("PASSWORD=secret")
        assert "[REDACTED]" in sanitize_message("Token=abc")
        assert "[REDACTED]" in sanitize_message("API_KEY=xyz")

    def test_redacted_replacement_text(self):
        result = sanitize_message("password=hidden")
        assert "[REDACTED]" in result
        assert "hidden" not in result
