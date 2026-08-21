"""
Property-based test for Text Normalization Produces Valid Plain Text (Property 5).

**Validates: Requirements 4.2**

For any text content extracted from a file, the normalized output SHALL contain
only valid plain text characters (no binary data, control characters other than
newlines/tabs, or encoding artifacts).
"""

import string

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from services.file_processor import FileProcessor


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def processor():
    """Create a FileProcessor instance for testing."""
    return FileProcessor()


# Singleton instance for use in hypothesis tests (cannot use fixtures directly)
_processor = FileProcessor()


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Strategy for arbitrary text including control characters, binary data,
# null bytes, and encoding artifacts that might appear in extracted text
arbitrary_text = st.text(
    alphabet=st.characters(min_codepoint=0, max_codepoint=0xFFFF),
    min_size=0,
    max_size=500,
)

# Strategy for text with embedded null bytes
text_with_nulls = st.builds(
    lambda parts, nulls: "\x00".join(parts),
    parts=st.lists(
        st.text(min_size=0, max_size=50),
        min_size=1,
        max_size=10,
    ),
    nulls=st.none(),
)

# Strategy for text with various control characters
control_chars = "".join(chr(c) for c in range(0, 32) if c not in (9, 10, 13))  # exclude \t, \n, \r
text_with_control_chars = st.text(
    alphabet=string.printable + control_chars,
    min_size=1,
    max_size=300,
)

# Strategy for text with mixed line endings
text_with_mixed_line_endings = st.builds(
    lambda parts: "".join(parts),
    parts=st.lists(
        st.one_of(
            st.text(alphabet=string.printable.replace("\r", "").replace("\n", ""), min_size=0, max_size=30),
            st.sampled_from(["\n", "\r\n", "\r"]),
        ),
        min_size=1,
        max_size=20,
    ),
)

# Strategy for text with many consecutive blank lines
text_with_many_blank_lines = st.builds(
    lambda parts, blanks: ("\n" * blanks).join(parts),
    parts=st.lists(
        st.text(alphabet=string.ascii_letters + " ", min_size=1, max_size=30),
        min_size=2,
        max_size=5,
    ),
    blanks=st.integers(min_value=3, max_value=10),
)


# ---------------------------------------------------------------------------
# Helper: define what constitutes valid plain text
# ---------------------------------------------------------------------------

def is_valid_plain_text_char(ch: str) -> bool:
    """
    Check if a character is a valid plain text character.

    Valid characters are:
    - Tab (0x09)
    - Newline (0x0A)
    - Printable ASCII (0x20-0x7E)
    - Extended characters (0x80-0xFFFF) — valid Unicode beyond ASCII
    """
    code = ord(ch)
    if code == 0x09:  # tab
        return True
    if code == 0x0A:  # newline
        return True
    if 0x20 <= code <= 0x7E:  # printable ASCII
        return True
    if 0x80 <= code <= 0xFFFF:  # valid Unicode beyond ASCII
        return True
    return False


def assert_valid_plain_text(text: str):
    """Assert that every character in the text is a valid plain text character."""
    for i, ch in enumerate(text):
        assert is_valid_plain_text_char(ch), (
            f"Invalid character at position {i}: "
            f"U+{ord(ch):04X} (repr: {repr(ch)})"
        )


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------


class TestTextNormalizationProperty:
    """
    Property 5: Text Normalization Produces Valid Plain Text

    **Validates: Requirements 4.2**

    For any text content extracted from a file, the normalized output SHALL
    contain only valid plain text characters (no binary data, control characters
    other than newlines/tabs, or encoding artifacts).
    """

    @given(text=arbitrary_text)
    @settings(max_examples=200)
    def test_normalization_removes_all_invalid_characters(self, text):
        """
        Property: For any arbitrary text input (including binary data, control
        characters, null bytes), normalization produces output containing only
        valid plain text characters.
        """
        result = _processor._normalize_text(text)
        assert_valid_plain_text(result)

    @given(text=text_with_nulls)
    @settings(max_examples=100)
    def test_normalization_removes_null_bytes(self, text):
        """
        Property: For any text containing null bytes, normalization removes
        all null bytes and the output contains no null characters.
        """
        result = _processor._normalize_text(text)
        assert "\x00" not in result
        assert_valid_plain_text(result)

    @given(text=text_with_control_chars)
    @settings(max_examples=100)
    def test_normalization_removes_control_characters(self, text):
        """
        Property: For any text containing control characters (other than
        tab and newline), normalization removes them all.
        """
        result = _processor._normalize_text(text)
        assert_valid_plain_text(result)

    @given(text=text_with_mixed_line_endings)
    @settings(max_examples=100)
    def test_normalization_normalizes_line_endings(self, text):
        """
        Property: For any text with mixed line endings (\\r\\n, \\r, \\n),
        normalization converts all to \\n only — no \\r remains.
        """
        result = _processor._normalize_text(text)
        assert "\r" not in result
        assert_valid_plain_text(result)

    @given(text=text_with_many_blank_lines)
    @settings(max_examples=100)
    def test_normalization_collapses_multiple_blank_lines(self, text):
        """
        Property: For any text with 3+ consecutive newlines, normalization
        collapses them to at most 2 consecutive newlines (one blank line).
        """
        result = _processor._normalize_text(text)
        assert "\n\n\n" not in result
        assert_valid_plain_text(result)

    @given(text=arbitrary_text)
    @settings(max_examples=100)
    def test_normalization_produces_stripped_output(self, text):
        """
        Property: For any text, normalization produces output with no
        leading or trailing whitespace.
        """
        result = _processor._normalize_text(text)
        if result:  # non-empty results should be stripped
            assert result == result.strip()

    def test_normalization_empty_input_returns_empty(self):
        """Edge case: empty string input returns empty string."""
        assert _processor._normalize_text("") == ""

    def test_normalization_only_nulls_returns_empty(self):
        """Edge case: string of only null bytes returns empty."""
        assert _processor._normalize_text("\x00\x00\x00") == ""

    def test_normalization_preserves_tabs(self):
        """Edge case: tabs are preserved in output."""
        result = _processor._normalize_text("col1\tcol2\tcol3")
        assert "\t" in result

    def test_normalization_preserves_newlines(self):
        """Edge case: newlines are preserved in output."""
        result = _processor._normalize_text("line1\nline2\nline3")
        assert "\n" in result
