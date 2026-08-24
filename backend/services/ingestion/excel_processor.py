"""
Excel Processor Service.

Processes Excel files with intelligent handling of:
- Multi-sheet workbooks
- Title/metadata rows
- Header detection
- Summary rows (TOTAL, PORTFOLIO TOTAL, etc.)
- Numeric type preservation
- Currency parsing
"""

import re
import logging
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass, field

import pandas as pd
import numpy as np

from .file_classifier import SheetClassification, DataType

logger = logging.getLogger(__name__)


@dataclass
class ColumnInfo:
    """Information about a detected column."""
    name: str
    index: int
    data_type: str  # numeric, currency, percentage, date, text, id
    python_type: str  # int, float, str, datetime
    is_currency: bool = False
    currency_symbol: Optional[str] = None
    is_percentage: bool = False
    null_count: int = 0
    unique_count: int = 0
    sample_values: list = field(default_factory=list)


@dataclass
class RowInfo:
    """Information about a data row."""
    row_index: int
    row_type: str  # data, summary, subtotal
    row_label: Optional[str]
    data: dict  # Column name -> typed value
    primary_key_value: Optional[str] = None


@dataclass
class SheetData:
    """Extracted structured data from a sheet."""
    sheet_name: str
    document_title: Optional[str]
    document_context: Optional[str]
    columns: list[ColumnInfo]
    rows: list[RowInfo]
    summary_rows: list[RowInfo]
    classification: SheetClassification
    raw_headers: list[str]


class ExcelProcessor:
    """
    Processes Excel files to extract structured data with type preservation.
    
    Features:
    - Detects and preserves numeric types (int, float)
    - Parses currency values (e.g., "$2,400,000" -> 2400000.0)
    - Parses percentages (e.g., "85%" -> 0.85)
    - Identifies summary rows
    - Extracts document metadata from title rows
    """
    
    # Patterns for currency detection
    CURRENCY_PATTERN = re.compile(r'^[\$£€¥₹]?\s*[\d,]+\.?\d*\s*[\$£€¥₹]?$')
    CURRENCY_SYMBOLS = {'$', '£', '€', '¥', '₹'}
    
    # Patterns for percentage detection
    PERCENTAGE_PATTERN = re.compile(r'^[\d.]+\s*%$')
    
    # Patterns for ID fields
    ID_PATTERNS = [
        re.compile(r'^[A-Z]{2,5}-\d+', re.IGNORECASE),  # PRJ-001, FIN-002
        re.compile(r'^[A-Z]{2,5}_\d+', re.IGNORECASE),  # PRJ_001
        re.compile(r'^\d{5,}$'),  # Long numbers as IDs
    ]
    
    def process_file(self, file_path: str, 
                     sheet_classifications: list[SheetClassification]) -> list[SheetData]:
        """
        Process an Excel file and extract structured data from all sheets.
        
        Args:
            file_path: Path to the Excel file
            sheet_classifications: Pre-computed classifications for each sheet
            
        Returns:
            List of SheetData objects, one per structured/semi-structured sheet
        """
        excel_file = pd.ExcelFile(file_path)
        results = []
        
        try:
            # Create a lookup by sheet name
            class_lookup = {sc.sheet_name: sc for sc in sheet_classifications}
            
            for sheet_name in excel_file.sheet_names:
                classification = class_lookup.get(sheet_name)
                
                if classification is None:
                    logger.warning(f"No classification for sheet '{sheet_name}', skipping")
                    continue
                
                # Only process structured or semi-structured sheets
                if classification.data_type == DataType.UNSTRUCTURED:
                    logger.info(f"Sheet '{sheet_name}' is unstructured, will use text chunking")
                    continue
                
                # Read the sheet without headers (we'll handle them manually)
                df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
                
                sheet_data = self._process_sheet(df, classification)
                if sheet_data:
                    results.append(sheet_data)
                    
        finally:
            excel_file.close()
        
        return results
    
    def _process_sheet(self, df: pd.DataFrame, 
                       classification: SheetClassification) -> Optional[SheetData]:
        """
        Process a single sheet and extract structured data.
        """
        if df.empty or classification.header_row is None:
            return None
        
        # Extract document title and context from title rows
        doc_title = None
        doc_context = None
        
        for title_row_idx in classification.title_rows:
            if title_row_idx < len(df):
                row = df.iloc[title_row_idx]
                first_val = row.dropna().iloc[0] if row.notna().any() else None
                if first_val:
                    val_str = str(first_val)
                    if "ENTERPRISE REPORT" in val_str.upper() or "PORTFOLIO" in val_str.upper():
                        doc_title = val_str
                    elif "Global" in val_str or "Classification" in val_str:
                        doc_context = val_str
        
        # Extract headers
        header_row = df.iloc[classification.header_row]
        headers = []
        for i, val in enumerate(header_row):
            if pd.notna(val):
                headers.append(str(val).strip())
            else:
                headers.append(f"column_{i}")
        
        # Analyze columns
        columns = self._analyze_columns(
            df, headers, 
            classification.data_start_row, 
            classification.data_end_row
        )
        
        # Extract data rows
        data_rows = []
        summary_rows = []
        
        # Determine primary key column (usually first column with ID-like values)
        pk_column = self._find_primary_key_column(columns)
        
        for idx in range(classification.data_start_row, classification.data_end_row + 1):
            if idx >= len(df):
                break
                
            row = df.iloc[idx]
            row_data = self._extract_row_data(row, columns)
            
            # Get primary key value
            pk_value = None
            if pk_column and pk_column in row_data:
                pk_value = str(row_data[pk_column]) if row_data[pk_column] is not None else None
            
            row_info = RowInfo(
                row_index=idx - classification.data_start_row,
                row_type="data",
                row_label=None,
                data=row_data,
                primary_key_value=pk_value
            )
            data_rows.append(row_info)
        
        # Extract summary row if present
        if classification.has_summary_row and classification.summary_row_index is not None:
            summary_row = df.iloc[classification.summary_row_index]
            summary_data = self._extract_row_data(summary_row, columns)
            
            # Get label from first column
            row_label = str(summary_row.iloc[0]).strip() if pd.notna(summary_row.iloc[0]) else "TOTAL"
            
            summary_info = RowInfo(
                row_index=classification.summary_row_index - classification.data_start_row,
                row_type="summary",
                row_label=row_label,
                data=summary_data,
                primary_key_value=None
            )
            summary_rows.append(summary_info)
        
        return SheetData(
            sheet_name=classification.sheet_name,
            document_title=doc_title,
            document_context=doc_context,
            columns=columns,
            rows=data_rows,
            summary_rows=summary_rows,
            classification=classification,
            raw_headers=headers
        )
    
    def _analyze_columns(self, df: pd.DataFrame, headers: list[str],
                        data_start: int, data_end: int) -> list[ColumnInfo]:
        """Analyze each column to determine its type and properties."""
        columns = []
        
        for idx, header in enumerate(headers):
            if idx >= df.shape[1]:
                break
            
            # Get column data (only data rows, not headers or summary)
            col_data = df.iloc[data_start:data_end + 1, idx]
            
            # Analyze column type
            col_info = self._analyze_column(header, idx, col_data)
            columns.append(col_info)
        
        return columns
    
    def _analyze_column(self, name: str, index: int, 
                       data: pd.Series) -> ColumnInfo:
        """Analyze a single column to determine its type."""
        non_null = data.dropna()
        
        if len(non_null) == 0:
            return ColumnInfo(
                name=name, index=index,
                data_type="text", python_type="str",
                null_count=len(data), unique_count=0
            )
        
        # Sample values for analysis
        sample = non_null.head(10).tolist()
        sample_strs = [str(v).strip() for v in sample]
        
        # Check for ID field FIRST (before numeric check)
        if self._is_id_column(name, sample_strs):
            return ColumnInfo(
                name=name, index=index,
                data_type="id", python_type="str",
                null_count=len(data) - len(non_null),
                unique_count=non_null.nunique(),
                sample_values=sample[:3]
            )
        
        # Check for currency based on column NAME (budget, cost, variance, expense)
        # This is important because values may not have currency symbols
        if self._is_currency_column_by_name(name):
            return ColumnInfo(
                name=name, index=index,
                data_type="currency", python_type="float",
                is_currency=True, currency_symbol="$",
                null_count=len(data) - len(non_null),
                unique_count=non_null.nunique(),
                sample_values=sample[:3]
            )
        
        # Check for currency by values (has $ symbols)
        if self._is_currency_column(sample_strs):
            currency_symbol = self._detect_currency_symbol(sample_strs)
            return ColumnInfo(
                name=name, index=index,
                data_type="currency", python_type="float",
                is_currency=True, currency_symbol=currency_symbol,
                null_count=len(data) - len(non_null),
                unique_count=non_null.nunique(),
                sample_values=sample[:3]
            )
        
        # Check for percentage
        if self._is_percentage_column(sample_strs) or self._is_percentage_column_by_name(name):
            return ColumnInfo(
                name=name, index=index,
                data_type="percentage", python_type="float",
                is_percentage=True,
                null_count=len(data) - len(non_null),
                unique_count=non_null.nunique(),
                sample_values=sample[:3]
            )
        
        # Check for dates
        if self._is_date_column(non_null):
            return ColumnInfo(
                name=name, index=index,
                data_type="date", python_type="datetime",
                null_count=len(data) - len(non_null),
                unique_count=non_null.nunique(),
                sample_values=sample[:3]
            )
        
        # Check for pure numeric
        if self._is_numeric_column(non_null):
            # Determine if int or float
            python_type = "int" if all(isinstance(v, (int, np.integer)) or 
                                       (isinstance(v, float) and v.is_integer()) 
                                       for v in non_null) else "float"
            return ColumnInfo(
                name=name, index=index,
                data_type="numeric", python_type=python_type,
                null_count=len(data) - len(non_null),
                unique_count=non_null.nunique(),
                sample_values=sample[:3]
            )
        
        # Default to text
        return ColumnInfo(
            name=name, index=index,
            data_type="text", python_type="str",
            null_count=len(data) - len(non_null),
            unique_count=non_null.nunique(),
            sample_values=sample[:3]
        )
    
    def _is_currency_column_by_name(self, name: str) -> bool:
        """Check if column name suggests currency values."""
        name_lower = name.lower()
        currency_keywords = [
            'budget', 'cost', 'expense', 'variance', 'spending',
            'amount', 'price', 'revenue', 'profit', 'loss',
            'total_cost', 'actual_cost', 'approved_budget', 'forecast'
        ]
        return any(kw in name_lower for kw in currency_keywords)
    
    def _is_percentage_column_by_name(self, name: str) -> bool:
        """Check if column name suggests percentage values."""
        name_lower = name.lower()
        pct_keywords = ['rate', 'percent', 'pct', 'utilization', 'ratio']
        return any(kw in name_lower for kw in pct_keywords)
    
    def _is_id_column(self, name: str, samples: list[str]) -> bool:
        """Check if column contains ID-like values."""
        name_lower = name.lower()
        
        # Check if name ends with _id or is explicitly an ID column
        # BUT exclude columns that are clearly financial (budget, cost, etc.)
        financial_keywords = ['budget', 'cost', 'expense', 'variance', 'amount', 
                             'price', 'revenue', 'spending', 'forecast', 'actual']
        if any(kw in name_lower for kw in financial_keywords):
            return False
        
        # Check for explicit ID naming patterns
        if name_lower.endswith('_id') or name_lower == 'id' or name_lower.startswith('id_'):
            return True
        if any(id_word in name_lower for id_word in ['_id', 'code', 'key']):
            return True
            return True
        
        # Check sample values against ID patterns
        for sample in samples[:5]:
            for pattern in self.ID_PATTERNS:
                if pattern.match(sample):
                    return True
        
        return False
    
    def _is_currency_column(self, samples: list[str]) -> bool:
        """Check if column contains currency values."""
        matches = 0
        for sample in samples:
            # Check for currency symbols or large formatted numbers
            if any(sym in sample for sym in self.CURRENCY_SYMBOLS):
                matches += 1
            elif self.CURRENCY_PATTERN.match(sample) and ',' in sample:
                matches += 1
        return matches >= len(samples) * 0.5
    
    def _detect_currency_symbol(self, samples: list[str]) -> Optional[str]:
        """Detect the currency symbol used."""
        for sample in samples:
            for sym in self.CURRENCY_SYMBOLS:
                if sym in sample:
                    return sym
        return '$'  # Default to USD
    
    def _is_percentage_column(self, samples: list[str]) -> bool:
        """Check if column contains percentage values."""
        matches = sum(1 for s in samples if self.PERCENTAGE_PATTERN.match(s))
        return matches >= len(samples) * 0.5
    
    def _is_date_column(self, data: pd.Series) -> bool:
        """Check if column contains date values."""
        try:
            # Check if already datetime type
            if pd.api.types.is_datetime64_any_dtype(data):
                return True
            
            # Try to parse as dates
            sample = data.head(5)
            for val in sample:
                if isinstance(val, (datetime, pd.Timestamp)):
                    return True
                try:
                    pd.to_datetime(val)
                except:
                    return False
            return True
        except:
            return False
    
    def _is_numeric_column(self, data: pd.Series) -> bool:
        """Check if column contains numeric values."""
        try:
            # Check if already numeric type
            if pd.api.types.is_numeric_dtype(data):
                return True
            
            # Try to convert
            pd.to_numeric(data, errors='raise')
            return True
        except:
            return False
    
    def _find_primary_key_column(self, columns: list[ColumnInfo]) -> Optional[str]:
        """Find the primary key column (usually the first ID column)."""
        for col in columns:
            if col.data_type == "id":
                return col.name
        return None
    
    def _extract_row_data(self, row: pd.Series, 
                         columns: list[ColumnInfo]) -> dict:
        """Extract typed data from a row."""
        data = {}
        
        for col in columns:
            if col.index >= len(row):
                data[col.name] = None
                continue
            
            raw_value = row.iloc[col.index]
            
            if pd.isna(raw_value):
                data[col.name] = None
                continue
            
            # Convert based on column type
            try:
                if col.data_type == "currency":
                    data[col.name] = self._parse_currency(raw_value)
                elif col.data_type == "percentage":
                    data[col.name] = self._parse_percentage(raw_value)
                elif col.data_type == "numeric":
                    data[col.name] = self._parse_numeric(raw_value, col.python_type)
                elif col.data_type == "date":
                    data[col.name] = self._parse_date(raw_value)
                else:
                    data[col.name] = str(raw_value).strip()
            except Exception as e:
                logger.warning(f"Failed to parse value '{raw_value}' for column '{col.name}': {e}")
                data[col.name] = str(raw_value).strip() if raw_value is not None else None
        
        return data
    
    def _parse_currency(self, value: Any) -> Optional[float]:
        """Parse a currency value to float."""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        # String parsing
        s = str(value).strip()
        # Remove currency symbols and commas
        for sym in self.CURRENCY_SYMBOLS:
            s = s.replace(sym, '')
        s = s.replace(',', '').strip()
        
        try:
            return float(s)
        except ValueError:
            return None
    
    def _parse_percentage(self, value: Any) -> Optional[float]:
        """Parse a percentage value to decimal."""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        
        if isinstance(value, (int, float)):
            # Already a number - might be decimal (0.85) or whole (85)
            v = float(value)
            return v if v <= 1 else v / 100
        
        # String parsing
        s = str(value).strip().replace('%', '').strip()
        try:
            v = float(s)
            return v / 100 if v > 1 else v
        except ValueError:
            return None
    
    def _parse_numeric(self, value: Any, python_type: str) -> Optional[float]:
        """Parse a numeric value."""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        
        if isinstance(value, (int, float)):
            return int(value) if python_type == "int" else float(value)
        
        # String parsing
        s = str(value).strip().replace(',', '')
        try:
            v = float(s)
            return int(v) if python_type == "int" else v
        except ValueError:
            return None
    
    def _parse_date(self, value: Any) -> Optional[str]:
        """Parse a date value to ISO string."""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        
        try:
            if isinstance(value, (datetime, pd.Timestamp)):
                return value.isoformat()
            dt = pd.to_datetime(value)
            return dt.isoformat()
        except:
            return str(value)
