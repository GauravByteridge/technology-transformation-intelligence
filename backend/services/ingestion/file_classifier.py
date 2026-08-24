"""
File Classifier Service.

Automatically detects file types and determines whether content should be
processed through the structured or unstructured data pipeline.
"""

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)


class FileType(str, Enum):
    """Supported file types."""
    PDF = "pdf"
    XLSX = "xlsx"
    XLS = "xls"
    CSV = "csv"
    JSON = "json"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"


class DataType(str, Enum):
    """Data classification types."""
    STRUCTURED = "structured"
    SEMI_STRUCTURED = "semi_structured"
    UNSTRUCTURED = "unstructured"


@dataclass
class SheetClassification:
    """Classification result for a single Excel sheet."""
    sheet_name: str
    data_type: DataType
    header_row: Optional[int]  # 0-based index
    data_start_row: Optional[int]
    data_end_row: Optional[int]
    has_summary_row: bool
    summary_row_index: Optional[int]
    title_rows: list[int]  # Rows containing titles/metadata
    column_count: int
    row_count: int
    confidence: float
    reason: str


@dataclass
class FileClassification:
    """Classification result for a file."""
    file_path: str
    file_type: FileType
    primary_data_type: DataType
    sheet_classifications: list[SheetClassification]
    is_mixed: bool  # True if file contains both structured and unstructured
    confidence: float


class FileClassifier:
    """
    Classifies files and their contents to determine appropriate processing pipeline.
    
    For Excel files, analyzes each sheet independently to determine if it contains:
    - Structured data (tabular with consistent columns)
    - Semi-structured data (has some structure but irregular)
    - Unstructured data (text, notes, descriptions)
    """
    
    # Keywords indicating summary rows
    SUMMARY_KEYWORDS = [
        "total", "grand total", "portfolio total", "subtotal",
        "total / average", "portfolio total / average", "average",
        "sum", "overall"
    ]
    
    # File types that are always unstructured
    UNSTRUCTURED_FILE_TYPES = {FileType.PDF, FileType.DOCX, FileType.TXT, FileType.MD}
    
    # File types that are potentially structured
    STRUCTURED_FILE_TYPES = {FileType.XLSX, FileType.XLS, FileType.CSV, FileType.JSON}
    
    def classify(self, file_path: str, file_type: str) -> FileClassification:
        """
        Classify a file and determine the appropriate processing pipeline.
        
        Args:
            file_path: Path to the file
            file_type: File extension (without dot)
            
        Returns:
            FileClassification with detailed analysis
        """
        file_type_enum = FileType(file_type.lower())
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # PDF, DOCX, TXT, MD are always unstructured
        if file_type_enum in self.UNSTRUCTURED_FILE_TYPES:
            return FileClassification(
                file_path=file_path,
                file_type=file_type_enum,
                primary_data_type=DataType.UNSTRUCTURED,
                sheet_classifications=[],
                is_mixed=False,
                confidence=1.0
            )
        
        # Analyze structured file types
        if file_type_enum in {FileType.XLSX, FileType.XLS}:
            return self._classify_excel(file_path, file_type_enum)
        elif file_type_enum == FileType.CSV:
            return self._classify_csv(file_path)
        elif file_type_enum == FileType.JSON:
            return self._classify_json(file_path)
        
        # Default to unstructured
        return FileClassification(
            file_path=file_path,
            file_type=file_type_enum,
            primary_data_type=DataType.UNSTRUCTURED,
            sheet_classifications=[],
            is_mixed=False,
            confidence=0.5
        )
    
    def _classify_excel(self, file_path: str, file_type: FileType) -> FileClassification:
        """Classify an Excel file by analyzing each sheet."""
        excel_file = pd.ExcelFile(file_path)
        sheet_classifications = []
        
        try:
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
                classification = self._classify_sheet(sheet_name, df)
                sheet_classifications.append(classification)
        finally:
            excel_file.close()
        
        # Determine primary data type and if mixed
        data_types = {sc.data_type for sc in sheet_classifications}
        is_mixed = len(data_types) > 1
        
        # Primary type is structured if any sheet is structured
        if DataType.STRUCTURED in data_types:
            primary_type = DataType.STRUCTURED
        elif DataType.SEMI_STRUCTURED in data_types:
            primary_type = DataType.SEMI_STRUCTURED
        else:
            primary_type = DataType.UNSTRUCTURED
        
        avg_confidence = sum(sc.confidence for sc in sheet_classifications) / len(sheet_classifications) if sheet_classifications else 0
        
        return FileClassification(
            file_path=file_path,
            file_type=file_type,
            primary_data_type=primary_type,
            sheet_classifications=sheet_classifications,
            is_mixed=is_mixed,
            confidence=avg_confidence
        )
    
    def _classify_sheet(self, sheet_name: str, df: pd.DataFrame) -> SheetClassification:
        """
        Analyze a single Excel sheet to determine its structure.
        
        Detection logic:
        1. Find title/metadata rows (usually first few rows with sparse data)
        2. Find header row (row with most non-null values that looks like headers)
        3. Find data range (consistent rows after header)
        4. Find summary row (row with total/average keywords at the end)
        """
        if df.empty:
            return SheetClassification(
                sheet_name=sheet_name,
                data_type=DataType.UNSTRUCTURED,
                header_row=None,
                data_start_row=None,
                data_end_row=None,
                has_summary_row=False,
                summary_row_index=None,
                title_rows=[],
                column_count=0,
                row_count=0,
                confidence=1.0,
                reason="Empty sheet"
            )
        
        n_rows, n_cols = df.shape
        
        # Step 1: Find title/metadata rows (usually first few rows)
        title_rows = []
        header_row = None
        
        for i in range(min(10, n_rows)):  # Check first 10 rows
            row = df.iloc[i]
            non_null_count = row.notna().sum()
            
            # Title rows typically have very few filled cells (1-2)
            if non_null_count <= 2 and non_null_count > 0:
                first_val = str(row.dropna().iloc[0]) if non_null_count > 0 else ""
                # Check if it looks like a title
                if len(first_val) > 20 or any(kw in first_val.upper() for kw in ["REPORT", "ENTERPRISE", "SUMMARY", "PORTFOLIO"]):
                    title_rows.append(i)
            # Header row has many columns filled with text
            elif non_null_count >= n_cols * 0.5:
                # Check if values look like headers (text, no numbers)
                vals = row.dropna().astype(str).tolist()
                looks_like_header = all(
                    not self._is_numeric_value(v) or v.lower() in ['id', 'status']
                    for v in vals[:min(5, len(vals))]
                )
                if looks_like_header and header_row is None:
                    header_row = i
                    break
        
        if header_row is None:
            # Try to find header by looking for consistent column structure
            for i in range(min(10, n_rows)):
                row = df.iloc[i]
                non_null = row.notna().sum()
                if non_null >= 3:  # At least 3 columns
                    header_row = i
                    break
        
        # Step 2: Determine data range
        data_start_row = header_row + 1 if header_row is not None else 0
        data_end_row = n_rows - 1
        
        # Step 3: Find summary row
        has_summary_row = False
        summary_row_index = None
        
        # Check last few rows for summary keywords
        for i in range(max(0, n_rows - 5), n_rows):
            row = df.iloc[i]
            first_val = str(row.iloc[0]).lower() if pd.notna(row.iloc[0]) else ""
            if any(kw in first_val for kw in self.SUMMARY_KEYWORDS):
                has_summary_row = True
                summary_row_index = i
                data_end_row = i - 1
                break
        
        # Step 4: Determine data type based on structure
        data_row_count = data_end_row - data_start_row + 1 if data_end_row >= data_start_row else 0
        
        if header_row is not None and data_row_count >= 2:
            # Check if data is consistently structured
            if self._is_structured_data(df, header_row, data_start_row, data_end_row):
                data_type = DataType.STRUCTURED
                confidence = 0.9
                reason = f"Structured table with {data_row_count} data rows"
            else:
                data_type = DataType.SEMI_STRUCTURED
                confidence = 0.7
                reason = "Semi-structured with inconsistent data"
        else:
            data_type = DataType.UNSTRUCTURED
            confidence = 0.8
            reason = "No clear tabular structure detected"
        
        return SheetClassification(
            sheet_name=sheet_name,
            data_type=data_type,
            header_row=header_row,
            data_start_row=data_start_row if data_type != DataType.UNSTRUCTURED else None,
            data_end_row=data_end_row if data_type != DataType.UNSTRUCTURED else None,
            has_summary_row=has_summary_row,
            summary_row_index=summary_row_index,
            title_rows=title_rows,
            column_count=n_cols,
            row_count=n_rows,
            confidence=confidence,
            reason=reason
        )
    
    def _is_numeric_value(self, value: str) -> bool:
        """Check if a string value represents a number."""
        if not value:
            return False
        # Remove currency symbols and commas
        cleaned = value.replace("$", "").replace(",", "").replace("%", "").strip()
        try:
            float(cleaned)
            return True
        except (ValueError, TypeError):
            return False
    
    def _is_structured_data(self, df: pd.DataFrame, header_row: int, 
                           data_start: int, data_end: int) -> bool:
        """
        Check if data rows have consistent structure.
        """
        if data_start > data_end:
            return False
        
        # Get header to determine expected columns
        headers = df.iloc[header_row]
        n_expected_cols = headers.notna().sum()
        
        # Check consistency of data rows
        consistent_rows = 0
        for i in range(data_start, min(data_end + 1, data_start + 10)):  # Check up to 10 rows
            row = df.iloc[i]
            non_null = row.notna().sum()
            # Allow some variance
            if non_null >= n_expected_cols * 0.6:
                consistent_rows += 1
        
        # At least 70% of checked rows should be consistent
        total_checked = min(10, data_end - data_start + 1)
        return consistent_rows >= total_checked * 0.7
    
    def _classify_csv(self, file_path: str) -> FileClassification:
        """Classify a CSV file."""
        try:
            df = pd.read_csv(file_path, nrows=100)  # Sample first 100 rows
            
            # CSV is structured if it has consistent columns
            if len(df.columns) >= 2 and len(df) >= 1:
                # Check if columns have meaningful names
                has_headers = not all(str(col).startswith("Unnamed") for col in df.columns)
                
                sheet_class = SheetClassification(
                    sheet_name="data",
                    data_type=DataType.STRUCTURED if has_headers else DataType.SEMI_STRUCTURED,
                    header_row=0,
                    data_start_row=0,
                    data_end_row=len(df) - 1,
                    has_summary_row=False,
                    summary_row_index=None,
                    title_rows=[],
                    column_count=len(df.columns),
                    row_count=len(df),
                    confidence=0.85,
                    reason="CSV with tabular data"
                )
                
                return FileClassification(
                    file_path=file_path,
                    file_type=FileType.CSV,
                    primary_data_type=DataType.STRUCTURED,
                    sheet_classifications=[sheet_class],
                    is_mixed=False,
                    confidence=0.85
                )
        except Exception as e:
            logger.warning(f"Failed to parse CSV: {e}")
        
        return FileClassification(
            file_path=file_path,
            file_type=FileType.CSV,
            primary_data_type=DataType.UNSTRUCTURED,
            sheet_classifications=[],
            is_mixed=False,
            confidence=0.5
        )
    
    def _classify_json(self, file_path: str) -> FileClassification:
        """Classify a JSON file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Check if JSON is a list of records (structured)
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], dict):
                    # List of objects - structured data
                    sheet_class = SheetClassification(
                        sheet_name="data",
                        data_type=DataType.STRUCTURED,
                        header_row=None,
                        data_start_row=0,
                        data_end_row=len(data) - 1,
                        has_summary_row=False,
                        summary_row_index=None,
                        title_rows=[],
                        column_count=len(data[0].keys()) if data else 0,
                        row_count=len(data),
                        confidence=0.9,
                        reason="JSON array of records"
                    )
                    
                    return FileClassification(
                        file_path=file_path,
                        file_type=FileType.JSON,
                        primary_data_type=DataType.STRUCTURED,
                        sheet_classifications=[sheet_class],
                        is_mixed=False,
                        confidence=0.9
                    )
            
            # Single object or nested - semi-structured
            return FileClassification(
                file_path=file_path,
                file_type=FileType.JSON,
                primary_data_type=DataType.SEMI_STRUCTURED,
                sheet_classifications=[],
                is_mixed=False,
                confidence=0.7
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse JSON: {e}")
        
        return FileClassification(
            file_path=file_path,
            file_type=FileType.JSON,
            primary_data_type=DataType.UNSTRUCTURED,
            sheet_classifications=[],
            is_mixed=False,
            confidence=0.5
        )
