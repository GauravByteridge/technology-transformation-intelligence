"""
Property-based test for File Type to Extractor Routing (Property 4).

**Validates: Requirements 4.1**

For any uploaded file with a supported file type, the File Processor SHALL
invoke the correct extraction method:
- PyMuPDF (via _process_pdf) for PDF
- pandas (via _process_excel) for Excel (.xlsx, .xls)
- pandas (via _process_csv) for CSV
- Python json module (via _process_json) for JSON files
"""

from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from services.file_processor import FileProcessor


# ---------------------------------------------------------------------------
# Mapping of file types to the internal extraction method that MUST be
# invoked for that type. This is the source of truth for the routing property.
# ---------------------------------------------------------------------------

# Each supported file type maps to the name of the internal method that
# should handle its extraction.
TYPE_TO_METHOD = {
    "pdf": "_process_pdf",
    "xlsx": "_process_excel",
    "xls": "_process_excel",
    "csv": "_process_csv",
    "json": "_process_json",
}

ALL_EXTRACTION_METHODS = {
    "_process_pdf",
    "_process_excel",
    "_process_csv",
    "_process_json",
}


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Supported file types (the routing input space)
supported_file_types = st.sampled_from(sorted(TYPE_TO_METHOD.keys()))

# Case variations and leading-dot variations that process() should normalize.
# process() lowercases and strips a leading dot, so these must route identically.
def _decorate_type(base: str) -> st.SearchStrategy:
    """Produce case/dot variants of a base file type that must route the same."""
    return st.sampled_from([
        base,
        base.upper(),
        base.capitalize(),
        "." + base,
        "." + base.upper(),
    ])

decorated_supported_types = supported_file_types.flatmap(
    lambda base: st.tuples(st.just(base), _decorate_type(base))
)


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------


class TestFileTypeRoutingProperty:
    """
    Property 4: File Type to Extractor Routing

    **Validates: Requirements 4.1**

    For any supported file type, FileProcessor.process() invokes exactly the
    correct internal extraction method and no other extraction method.
    """

    @given(file_type=supported_file_types)
    @settings(max_examples=50)
    def test_supported_type_routes_to_correct_extractor(self, file_type):
        """
        Property: For any supported file type, process() calls exactly the
        extraction method mapped to that type, and none of the others.
        """
        processor = FileProcessor()
        expected_method = TYPE_TO_METHOD[file_type]

        # Patch os path existence so the routing logic is reached without a
        # real file on disk. process() checks Path.exists() before routing.
        with patch("services.file_processor.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = True
            # Path(...).name is used in error messages; give it a value.
            mock_path_cls.return_value.name = f"test.{file_type}"

            # Patch all four extraction methods so nothing touches real files.
            with patch.object(FileProcessor, "_process_pdf", return_value="pdf") as m_pdf, \
                 patch.object(FileProcessor, "_process_excel", return_value="excel") as m_excel, \
                 patch.object(FileProcessor, "_process_csv", return_value="csv") as m_csv, \
                 patch.object(FileProcessor, "_process_json", return_value="json") as m_json:

                method_mocks = {
                    "_process_pdf": m_pdf,
                    "_process_excel": m_excel,
                    "_process_csv": m_csv,
                    "_process_json": m_json,
                }

                processor.process(f"/fake/path/test.{file_type}", file_type)

                # The expected method must be called exactly once.
                assert method_mocks[expected_method].call_count == 1, (
                    f"Expected {expected_method} to be called once for "
                    f"file_type '{file_type}', but it was called "
                    f"{method_mocks[expected_method].call_count} times."
                )

                # Every other extraction method must NOT be called.
                for method_name, mock in method_mocks.items():
                    if method_name != expected_method:
                        assert mock.call_count == 0, (
                            f"Expected {method_name} NOT to be called for "
                            f"file_type '{file_type}', but it was called "
                            f"{mock.call_count} times."
                        )

    @given(pair=decorated_supported_types)
    @settings(max_examples=50)
    def test_type_normalization_routes_consistently(self, pair):
        """
        Property: Case variations and leading-dot variations of a supported
        file type (e.g. 'PDF', '.pdf', 'Pdf') all route to the same extraction
        method as the canonical lowercase type.
        """
        base_type, decorated_type = pair
        processor = FileProcessor()
        expected_method = TYPE_TO_METHOD[base_type]

        with patch("services.file_processor.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = True
            mock_path_cls.return_value.name = f"test.{base_type}"

            with patch.object(FileProcessor, "_process_pdf", return_value="pdf") as m_pdf, \
                 patch.object(FileProcessor, "_process_excel", return_value="excel") as m_excel, \
                 patch.object(FileProcessor, "_process_csv", return_value="csv") as m_csv, \
                 patch.object(FileProcessor, "_process_json", return_value="json") as m_json:

                method_mocks = {
                    "_process_pdf": m_pdf,
                    "_process_excel": m_excel,
                    "_process_csv": m_csv,
                    "_process_json": m_json,
                }

                processor.process(f"/fake/path/test.{base_type}", decorated_type)

                assert method_mocks[expected_method].call_count == 1, (
                    f"Decorated type '{decorated_type}' should route to "
                    f"{expected_method} (same as base '{base_type}')."
                )

                for method_name, mock in method_mocks.items():
                    if method_name != expected_method:
                        assert mock.call_count == 0, (
                            f"Decorated type '{decorated_type}' should not "
                            f"invoke {method_name}."
                        )

    @given(file_type=supported_file_types)
    @settings(max_examples=25)
    def test_extractor_receives_file_path(self, file_type):
        """
        Property: The routed extraction method receives the provided file path
        as its argument, ensuring routing preserves the input.
        """
        processor = FileProcessor()
        expected_method = TYPE_TO_METHOD[file_type]
        file_path = f"/fake/path/document.{file_type}"

        with patch("services.file_processor.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = True
            mock_path_cls.return_value.name = f"document.{file_type}"

            with patch.object(FileProcessor, expected_method, return_value="text") as mock_method:
                processor.process(file_path, file_type)

                mock_method.assert_called_once_with(file_path)


# ---------------------------------------------------------------------------
# Unit tests: explicit examples for each supported type (complements PBT)
# ---------------------------------------------------------------------------


class TestFileTypeRoutingExamples:
    """Concrete example-based tests for each supported file type."""

    @pytest.mark.parametrize(
        "file_type,expected_method",
        [
            ("pdf", "_process_pdf"),
            ("xlsx", "_process_excel"),
            ("xls", "_process_excel"),
            ("csv", "_process_csv"),
            ("json", "_process_json"),
        ],
    )
    def test_each_type_routes_to_expected_method(self, file_type, expected_method):
        """Each supported type routes to exactly its designated extractor."""
        processor = FileProcessor()

        with patch("services.file_processor.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = True
            mock_path_cls.return_value.name = f"file.{file_type}"

            with patch.object(FileProcessor, "_process_pdf", return_value="pdf") as m_pdf, \
                 patch.object(FileProcessor, "_process_excel", return_value="excel") as m_excel, \
                 patch.object(FileProcessor, "_process_csv", return_value="csv") as m_csv, \
                 patch.object(FileProcessor, "_process_json", return_value="json") as m_json:

                method_mocks = {
                    "_process_pdf": m_pdf,
                    "_process_excel": m_excel,
                    "_process_csv": m_csv,
                    "_process_json": m_json,
                }

                result = processor.process(f"/fake/file.{file_type}", file_type)

                method_mocks[expected_method].assert_called_once()
                for name, mock in method_mocks.items():
                    if name != expected_method:
                        mock.assert_not_called()

                # process() returns normalized text derived from the extractor output.
                assert isinstance(result, str)
