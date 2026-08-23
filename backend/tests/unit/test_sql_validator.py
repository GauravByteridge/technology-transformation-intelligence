"""Unit tests for app.connectors.sql_validator module."""

import pytest

from app.connectors.sql_validator import (
    PROHIBITED_STATEMENTS,
    _get_first_token,
    _is_multi_statement,
    _strip_comments,
    validate_read_only_sql,
)
from app.errors.datasource_errors import QueryValidationError


class TestValidateReadOnlySql:
    """Tests for the main validate_read_only_sql function."""

    def test_valid_select_passes(self) -> None:
        """Simple SELECT queries pass without raising."""
        validate_read_only_sql("SELECT * FROM users")

    def test_valid_select_with_where_passes(self) -> None:
        validate_read_only_sql("SELECT id, name FROM orders WHERE status = 'active'")

    def test_valid_with_cte_passes(self) -> None:
        """WITH (CTE) queries pass token inspection — Layer 2 handles data-modifying CTEs."""
        validate_read_only_sql("WITH cte AS (SELECT 1) SELECT * FROM cte")

    def test_empty_string_raises(self) -> None:
        with pytest.raises(QueryValidationError, match="Query must not be empty"):
            validate_read_only_sql("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(QueryValidationError, match="Query must not be empty"):
            validate_read_only_sql("   \n\t  ")

    def test_multi_statement_raises(self) -> None:
        with pytest.raises(QueryValidationError, match="Multi-statement queries are not permitted"):
            validate_read_only_sql("SELECT 1; SELECT 2")

    @pytest.mark.parametrize("keyword", list(PROHIBITED_STATEMENTS))
    def test_prohibited_first_token_raises(self, keyword: str) -> None:
        sql = f"{keyword} INTO users VALUES (1)"
        with pytest.raises(QueryValidationError, match=f"Prohibited: {keyword}"):
            validate_read_only_sql(sql)

    def test_prohibited_case_insensitive(self) -> None:
        with pytest.raises(QueryValidationError, match="Prohibited: INSERT"):
            validate_read_only_sql("insert into users values (1)")

    def test_prohibited_mixed_case(self) -> None:
        with pytest.raises(QueryValidationError, match="Prohibited: DELETE"):
            validate_read_only_sql("DeLeTe FROM users")

    def test_source_type_included_in_error(self) -> None:
        with pytest.raises(QueryValidationError) as exc_info:
            validate_read_only_sql("", source_type="postgresql")
        assert exc_info.value.source_type == "postgresql"

    def test_custom_source_type(self) -> None:
        with pytest.raises(QueryValidationError) as exc_info:
            validate_read_only_sql("", source_type="custom_db")
        assert exc_info.value.source_type == "custom_db"

    def test_comment_before_select_passes(self) -> None:
        """Comments are stripped before token detection."""
        validate_read_only_sql("-- This is a comment\nSELECT 1")

    def test_block_comment_before_select_passes(self) -> None:
        validate_read_only_sql("/* block comment */ SELECT * FROM t")

    def test_comment_disguising_prohibited_passes(self) -> None:
        """A commented-out DELETE followed by SELECT should pass."""
        validate_read_only_sql("-- DELETE FROM users\nSELECT * FROM users")

    def test_semicolon_inside_string_not_multi_statement(self) -> None:
        """Semicolons inside single-quoted literals are not separators."""
        validate_read_only_sql("SELECT * FROM t WHERE name = 'hello; world'")

    def test_trailing_semicolon_no_content_passes(self) -> None:
        """A single trailing semicolon (no meaningful content after) is acceptable."""
        validate_read_only_sql("SELECT 1;")

    def test_trailing_semicolon_with_whitespace_passes(self) -> None:
        validate_read_only_sql("SELECT 1;   \n  ")


class TestStripComments:
    """Tests for _strip_comments helper."""

    def test_removes_line_comment(self) -> None:
        result = _strip_comments("SELECT 1 -- comment")
        assert result == "SELECT 1 "

    def test_removes_block_comment(self) -> None:
        result = _strip_comments("SELECT /* hidden */ 1")
        assert result == "SELECT  1"

    def test_removes_multiline_block_comment(self) -> None:
        result = _strip_comments("SELECT /* line1\nline2 */ 1")
        assert result == "SELECT  1"

    def test_preserves_normal_sql(self) -> None:
        sql = "SELECT * FROM users WHERE id = 1"
        assert _strip_comments(sql) == sql


class TestIsMultiStatement:
    """Tests for _is_multi_statement helper."""

    def test_single_statement(self) -> None:
        assert _is_multi_statement("SELECT 1") is False

    def test_multi_statement(self) -> None:
        assert _is_multi_statement("SELECT 1; SELECT 2") is True

    def test_trailing_semicolon_only(self) -> None:
        assert _is_multi_statement("SELECT 1;") is False

    def test_semicolon_in_string(self) -> None:
        assert _is_multi_statement("SELECT 'a;b'") is False

    def test_semicolon_in_string_with_content_after(self) -> None:
        assert _is_multi_statement("SELECT 'a;b'; DROP TABLE x") is True

    def test_escaped_quotes_in_string(self) -> None:
        """Escaped single quotes ('') don't prematurely close the string."""
        assert _is_multi_statement("SELECT 'it''s ok'") is False


class TestGetFirstToken:
    """Tests for _get_first_token helper."""

    def test_simple(self) -> None:
        assert _get_first_token("SELECT * FROM t") == "SELECT"

    def test_leading_whitespace(self) -> None:
        assert _get_first_token("   INSERT INTO t") == "INSERT"

    def test_empty_string(self) -> None:
        assert _get_first_token("") == ""

    def test_whitespace_only(self) -> None:
        assert _get_first_token("   ") == ""
