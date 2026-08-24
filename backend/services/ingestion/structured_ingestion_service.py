"""
Structured Data Ingestion Service.

Handles the complete ingestion pipeline for structured data:
1. File classification
2. Data extraction with type preservation
3. Storage in relational database
4. Optional semantic text generation for hybrid search
"""

import logging
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session

from .file_classifier import FileClassifier, FileClassification, DataType
from .excel_processor import ExcelProcessor, SheetData, ColumnInfo, RowInfo
from models.structured_data_models import (
    StructuredDataset, StructuredColumn, StructuredRow
)
from models.database_models import File

logger = logging.getLogger(__name__)


class StructuredIngestionService:
    """
    Orchestrates structured data ingestion.
    
    For structured files (Excel, CSV, JSON with tabular data):
    1. Classifies the file and each sheet
    2. Extracts data with proper type handling
    3. Stores in structured_datasets, structured_columns, structured_rows tables
    4. Optionally generates semantic text for hybrid retrieval
    """
    
    def __init__(self):
        self.classifier = FileClassifier()
        self.excel_processor = ExcelProcessor()
    
    def ingest_file(self, db: Session, file_record: File, 
                    file_path: str, file_type: str) -> tuple[int, int]:
        """
        Ingest a structured file into the database.
        
        Args:
            db: Database session
            file_record: The File record from the files table
            file_path: Path to the uploaded file
            file_type: File extension
            
        Returns:
            Tuple of (datasets_created, total_rows)
        """
        # Step 1: Classify the file
        classification = self.classifier.classify(file_path, file_type)
        
        logger.info(
            f"File classification: {classification.file_path} -> "
            f"{classification.primary_data_type.value}, "
            f"sheets: {len(classification.sheet_classifications)}"
        )
        
        # If no structured content, return
        if classification.primary_data_type == DataType.UNSTRUCTURED:
            logger.info(f"File {file_path} is unstructured, skipping structured ingestion")
            return 0, 0
        
        # Step 2: Process based on file type
        if file_type.lower() in ('xlsx', 'xls'):
            return self._ingest_excel(db, file_record, file_path, classification)
        elif file_type.lower() == 'csv':
            return self._ingest_csv(db, file_record, file_path, classification)
        elif file_type.lower() == 'json':
            return self._ingest_json(db, file_record, file_path, classification)
        
        return 0, 0
    
    def _ingest_excel(self, db: Session, file_record: File,
                     file_path: str, classification: FileClassification) -> tuple[int, int]:
        """Ingest an Excel file."""
        # Get structured sheets only
        structured_sheets = [
            sc for sc in classification.sheet_classifications
            if sc.data_type in (DataType.STRUCTURED, DataType.SEMI_STRUCTURED)
        ]
        
        if not structured_sheets:
            return 0, 0
        
        # Extract data
        sheet_data_list = self.excel_processor.process_file(
            file_path, structured_sheets
        )
        
        datasets_created = 0
        total_rows = 0
        
        for sheet_data in sheet_data_list:
            dataset = self._create_dataset(db, file_record, sheet_data)
            
            # Create columns
            for col_info in sheet_data.columns:
                self._create_column(db, dataset, col_info)
            
            # Create data rows
            for row_info in sheet_data.rows:
                self._create_row(db, dataset, row_info)
                total_rows += 1
            
            # Create summary rows
            for summary_info in sheet_data.summary_rows:
                self._create_row(db, dataset, summary_info)
                total_rows += 1
            
            datasets_created += 1
        
        db.commit()
        
        logger.info(
            f"Structured ingestion complete: {datasets_created} datasets, "
            f"{total_rows} rows from {file_record.file_name}"
        )
        
        return datasets_created, total_rows
    
    def _ingest_csv(self, db: Session, file_record: File,
                   file_path: str, classification: FileClassification) -> tuple[int, int]:
        """Ingest a CSV file."""
        import pandas as pd
        
        if not classification.sheet_classifications:
            return 0, 0
        
        sheet_class = classification.sheet_classifications[0]
        
        # Read CSV
        df = pd.read_csv(file_path)
        
        # Create dataset
        dataset = StructuredDataset(
            file_id=file_record.id,
            file_name=file_record.file_name,
            sheet_name=None,
            table_name=file_record.file_name.rsplit('.', 1)[0],
            source_type='csv',
            data_classification=sheet_class.data_type.value,
            header_row_index=0,
            data_start_row=0,
            data_end_row=len(df) - 1,
            row_count=len(df),
            project_id=file_record.project_id,
            ingestion_timestamp=datetime.utcnow()
        )
        db.add(dataset)
        db.flush()
        
        # Create columns
        for idx, col_name in enumerate(df.columns):
            col = StructuredColumn(
                dataset_id=dataset.id,
                column_name=str(col_name),
                column_index=idx,
                data_type=self._infer_pandas_dtype(df[col_name]),
                python_type=str(df[col_name].dtype),
                null_count=int(df[col_name].isna().sum()),
                unique_count=int(df[col_name].nunique())
            )
            db.add(col)
        
        # Create rows
        for idx, row in df.iterrows():
            row_data = {str(k): self._convert_value(v) for k, v in row.items()}
            db_row = StructuredRow(
                dataset_id=dataset.id,
                row_index=idx,
                row_type='data',
                data=row_data
            )
            db.add(db_row)
        
        db.commit()
        return 1, len(df)
    
    def _ingest_json(self, db: Session, file_record: File,
                    file_path: str, classification: FileClassification) -> tuple[int, int]:
        """Ingest a JSON file with array of records."""
        import json
        import pandas as pd
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list) or len(data) == 0:
            return 0, 0
        
        # Convert to DataFrame for easier processing
        df = pd.DataFrame(data)
        
        # Create dataset
        dataset = StructuredDataset(
            file_id=file_record.id,
            file_name=file_record.file_name,
            sheet_name=None,
            table_name=file_record.file_name.rsplit('.', 1)[0],
            source_type='json',
            data_classification='structured',
            row_count=len(df),
            project_id=file_record.project_id,
            ingestion_timestamp=datetime.utcnow()
        )
        db.add(dataset)
        db.flush()
        
        # Create columns
        for idx, col_name in enumerate(df.columns):
            col = StructuredColumn(
                dataset_id=dataset.id,
                column_name=str(col_name),
                column_index=idx,
                data_type=self._infer_pandas_dtype(df[col_name]),
                python_type=str(df[col_name].dtype),
                null_count=int(df[col_name].isna().sum()),
                unique_count=int(df[col_name].nunique())
            )
            db.add(col)
        
        # Create rows
        for idx, row in df.iterrows():
            row_data = {str(k): self._convert_value(v) for k, v in row.items()}
            db_row = StructuredRow(
                dataset_id=dataset.id,
                row_index=idx,
                row_type='data',
                data=row_data
            )
            db.add(db_row)
        
        db.commit()
        return 1, len(df)
    
    def _create_dataset(self, db: Session, file_record: File,
                       sheet_data: SheetData) -> StructuredDataset:
        """Create a StructuredDataset record."""
        dataset = StructuredDataset(
            file_id=file_record.id,
            file_name=file_record.file_name,
            sheet_name=sheet_data.sheet_name,
            table_name=sheet_data.sheet_name,  # Use sheet name as table name
            document_title=sheet_data.document_title,
            document_context=sheet_data.document_context,
            source_type=file_record.file_type,
            data_classification=sheet_data.classification.data_type.value,
            header_row_index=sheet_data.classification.header_row,
            data_start_row=sheet_data.classification.data_start_row,
            data_end_row=sheet_data.classification.data_end_row,
            row_count=len(sheet_data.rows),
            project_id=file_record.project_id,
            ingestion_timestamp=datetime.utcnow()
        )
        db.add(dataset)
        db.flush()  # Get the ID
        return dataset
    
    def _create_column(self, db: Session, dataset: StructuredDataset,
                      col_info: ColumnInfo) -> StructuredColumn:
        """Create a StructuredColumn record."""
        column = StructuredColumn(
            dataset_id=dataset.id,
            column_name=col_info.name,
            column_index=col_info.index,
            data_type=col_info.data_type,
            python_type=col_info.python_type,
            is_currency=col_info.is_currency,
            currency_symbol=col_info.currency_symbol,
            is_percentage=col_info.is_percentage,
            null_count=col_info.null_count,
            unique_count=col_info.unique_count
        )
        db.add(column)
        return column
    
    def _create_row(self, db: Session, dataset: StructuredDataset,
                   row_info: RowInfo) -> StructuredRow:
        """Create a StructuredRow record."""
        row = StructuredRow(
            dataset_id=dataset.id,
            row_index=row_info.row_index,
            row_type=row_info.row_type,
            row_label=row_info.row_label,
            data=row_info.data,
            primary_key_value=row_info.primary_key_value
        )
        db.add(row)
        return row
    
    def _infer_pandas_dtype(self, series) -> str:
        """Infer data type from pandas series."""
        import pandas as pd
        import numpy as np
        
        dtype = series.dtype
        
        if pd.api.types.is_integer_dtype(dtype):
            return 'numeric'
        elif pd.api.types.is_float_dtype(dtype):
            return 'numeric'
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            return 'date'
        elif pd.api.types.is_bool_dtype(dtype):
            return 'boolean'
        else:
            return 'text'
    
    def _convert_value(self, value):
        """Convert pandas value to JSON-serializable format."""
        import pandas as pd
        import numpy as np
        
        if pd.isna(value):
            return None
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return float(value)
        if isinstance(value, (pd.Timestamp, datetime)):
            return value.isoformat()
        return value
    
    def get_unstructured_sheets(self, file_path: str, 
                                file_type: str) -> list[str]:
        """
        Get list of sheet names that should be processed as unstructured.
        
        Returns sheet names that are classified as unstructured.
        """
        classification = self.classifier.classify(file_path, file_type)
        
        if file_type.lower() not in ('xlsx', 'xls'):
            # For non-Excel files, return empty (handled separately)
            return []
        
        unstructured_sheets = [
            sc.sheet_name for sc in classification.sheet_classifications
            if sc.data_type == DataType.UNSTRUCTURED
        ]
        
        return unstructured_sheets
    
    def delete_file_data(self, db: Session, file_id: int) -> int:
        """
        Delete all structured data associated with a file.
        
        Returns:
            Number of datasets deleted
        """
        datasets = db.query(StructuredDataset).filter(
            StructuredDataset.file_id == file_id
        ).all()
        
        count = len(datasets)
        for dataset in datasets:
            db.delete(dataset)
        
        db.commit()
        return count
