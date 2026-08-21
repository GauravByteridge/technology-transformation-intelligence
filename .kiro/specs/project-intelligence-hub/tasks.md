# Implementation Plan: Project Intelligence Hub

## Overview

This implementation plan covers the development of a RAG-based proof-of-concept application with a React + TypeScript frontend and FastAPI Python backend. The application enables users to create a single project, upload files, process them into ChromaDB, and interact through AI chat and visualization features.

The implementation follows a bottom-up approach: backend infrastructure first, then file processing pipeline, followed by RAG pipeline, and finally the React frontend components.

## Tasks

- [x] 1. Set up project structure and core infrastructure
  - [x] 1.1 Initialize backend project structure with FastAPI
    - Create directory structure: `backend/` with `api/`, `services/`, `models/`, `db/`
    - Set up `requirements.txt` with dependencies: fastapi, uvicorn, sqlalchemy, psycopg2-binary, chromadb, pymupdf, pandas, pydantic, python-multipart, httpx
    - Create `main.py` with FastAPI app initialization and CORS configuration
    - _Requirements: 10.1-10.11_
  
  - [x] 1.2 Set up PostgreSQL database connection and models
    - Create `db/database.py` with SQLAlchemy engine and session management
    - Create `models/database_models.py` with Project and Files SQLAlchemy models matching the design schema
    - Create database initialization script
    - _Requirements: 1.2, 4.6_
  
  - [x] 1.3 Set up ChromaDB client and collection
    - Create `db/chroma_client.py` with ChromaDB client initialization
    - Configure "project_knowledge" collection with appropriate settings
    - Create helper functions for adding/querying/deleting embeddings
    - _Requirements: 4.5_
  
  - [x] 1.4 Initialize frontend project structure with React + TypeScript
    - Create React app with TypeScript using Vite
    - Install dependencies: react-router-dom, recharts, axios
    - Set up directory structure: `src/components/`, `src/screens/`, `src/api/`, `src/types/`
    - Create TypeScript interfaces matching the design data models
    - _Requirements: 9.1-9.3_

- [x] 2. Implement backend Pydantic models and API structure
  - [x] 2.1 Create Pydantic request/response models
    - Create `models/schemas.py` with all Pydantic models: ProjectCreate, ProjectResponse, FileResponse, ChatRequest, ChatResponse, VisualizationRequest, ChartConfig, DashboardStats, ErrorResponse
    - Implement FileCategory enum
    - _Requirements: 10.11_
  
  - [x] 2.2 Write property test for API error response format
    - **Property 8: API Error Response Format Consistency**
    - Test that all error responses contain "detail" field and appropriate HTTP status codes
    - **Validates: Requirements 10.11**

- [x] 3. Implement file processing pipeline services
  - [x] 3.1 Implement FileProcessor service
    - Create `services/file_processor.py` with FileProcessor class
    - Implement `_process_pdf()` using PyMuPDF for text extraction
    - Implement `_process_excel()` using pandas for .xlsx and .xls files
    - Implement `_process_csv()` using pandas for CSV files
    - Implement `_process_json()` using Python json module
    - Implement main `process()` method with file type routing
    - _Requirements: 4.1, 4.2_
  
  - [x] 3.2 Write property test for file type routing
    - **Property 4: File Type to Extractor Routing**
    - Test that PDF files route to PyMuPDF, Excel/CSV to pandas, JSON to json module
    - **Validates: Requirements 4.1**
  
  - [x] 3.3 Write property test for text normalization
    - **Property 5: Text Normalization Produces Valid Plain Text**
    - Test that extracted text contains only valid plain text characters
    - **Validates: Requirements 4.2**
  
  - [x] 3.4 Implement Chunker service
    - Create `services/chunker.py` with Chunker class
    - Implement `chunk()` method producing segments of 800-1000 characters
    - Implement character overlap between adjacent chunks
    - Handle edge cases: empty text, text shorter than chunk size
    - _Requirements: 4.3_
  
  - [x] 3.5 Write property test for chunking
    - **Property 6: Chunking Produces Valid Segments**
    - Test chunk size bounds (800-1000 chars), overlap, and content preservation
    - **Validates: Requirements 4.3**
  
  - [x] 3.6 Implement EmbeddingGenerator service
    - Create `services/embeddings.py` with EmbeddingGenerator class
    - Implement `generate()` method using sentence-transformers or ChromaDB's built-in embedding
    - Handle batch embedding generation for efficiency
    - _Requirements: 4.4_

- [x] 4. Checkpoint - Core services complete
  - Ensure all file processing services work correctly
  - Run unit tests for FileProcessor, Chunker, and EmbeddingGenerator
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement RAG pipeline and visualization services
  - [x] 5.1 Implement RAGPipeline service
    - Create `services/rag_pipeline.py` with RAGPipeline class
    - Implement embedding generation for user questions
    - Implement ChromaDB similarity search for top 5 chunks
    - Implement prompt construction combining context and question
    - Implement Groq API integration for inference
    - Return RAGResponse with answer and source file names
    - _Requirements: 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_
  
  - [x] 5.2 Write property test for prompt construction
    - **Property 7: Prompt Construction Completeness**
    - Test that prompts contain complete question, all chunk content, and clear separation
    - **Validates: Requirements 6.4**
  
  - [x] 5.3 Implement VisualizationGenerator service
    - Create `services/visualization.py` with VisualizationGenerator class
    - Implement data retrieval from project files
    - Implement Groq API integration for determining chart type and data mapping
    - Return ChartConfig with type, title, data, and key mappings
    - _Requirements: 7.2, 7.3_

- [x] 6. Implement backend API endpoints
  - [x] 6.1 Implement project API endpoints
    - Create `api/project.py` with router
    - Implement POST /api/project for project creation with validation
    - Implement GET /api/project for retrieving current project
    - Implement DELETE /api/project/reset for full project reset
    - Handle project already exists redirect logic
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 8.3-8.7, 10.1, 10.2, 10.3_
  
  - [x] 6.2 Write property test for project name validation
    - **Property 1: Empty/Whitespace Project Name Rejection**
    - Test that empty or whitespace-only names are rejected with validation error
    - **Validates: Requirements 1.4**
  
  - [x] 6.3 Implement file API endpoints
    - Create `api/files.py` with router
    - Implement POST /api/files/upload with file type validation and category metadata
    - Implement GET /api/files for listing all files
    - Implement GET /api/files/{id} for downloading a file
    - Implement DELETE /api/files/{id} for deleting file, chunks, and metadata
    - _Requirements: 3.1-3.5, 5.2-5.7, 10.4, 10.5, 10.6, 10.7_
  
  - [x] 6.4 Write property test for unsupported file type rejection
    - **Property 3: Unsupported File Type Rejection**
    - Test that files not in {pdf, xlsx, xls, csv, json} are rejected without storage
    - **Validates: Requirements 3.4**
  
  - [x] 6.5 Implement dashboard API endpoint
    - Create `api/dashboard.py` with router
    - Implement GET /api/dashboard returning DashboardStats
    - Calculate file counts by type and category
    - Return 5 most recent files sorted by upload date
    - _Requirements: 2.1-2.6, 10.8_
  
  - [x] 6.6 Write property test for recent files ordering
    - **Property 2: Recent Files Ordering and Limiting**
    - Test that recent files are sorted descending by date and limited to 5
    - **Validates: Requirements 2.5**
  
  - [x] 6.7 Implement chat API endpoint
    - Create `api/chat.py` with router
    - Implement POST /api/chat integrating RAGPipeline
    - Handle no relevant chunks case with appropriate message
    - Handle Groq API failures with service unavailable error
    - _Requirements: 6.1-6.9, 10.9_
  
  - [x] 6.8 Implement visualization API endpoint
    - Create `api/visualize.py` with router
    - Implement POST /api/visualize integrating VisualizationGenerator
    - Handle visualization generation failures
    - _Requirements: 7.1-7.6, 10.10_

- [x] 7. Checkpoint - Backend complete
  - Wire all routers into main FastAPI app
  - Test all API endpoints with sample requests
  - Verify database operations work correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement frontend API client and types
  - [x] 8.1 Create TypeScript interfaces and API client
    - Create `src/types/index.ts` with all TypeScript interfaces from design
    - Create `src/api/client.ts` with axios instance and base configuration
    - Create API functions for all endpoints: createProject, getProject, resetProject, uploadFile, getFiles, downloadFile, deleteFile, getDashboard, sendChatMessage, generateVisualization
    - _Requirements: 10.1-10.11_

- [x] 9. Implement frontend screens and components
  - [x] 9.1 Implement NavigationBar component
    - Create `src/components/NavigationBar.tsx`
    - Display links to Dashboard, Data Management, AI Chat, AI Visualization
    - Conditionally render based on project existence
    - _Requirements: 9.1, 9.2, 9.3_
  
  - [x] 9.2 Implement CreateProjectScreen
    - Create `src/screens/CreateProjectScreen.tsx`
    - Implement form with project name and description inputs
    - Implement client-side validation for empty project name
    - Handle form submission and API call
    - Redirect to Dashboard on success
    - Redirect to Dashboard if project already exists
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [x] 9.3 Implement DashboardScreen
    - Create `src/screens/DashboardScreen.tsx`
    - Display project name and description
    - Display total file count
    - Implement pie chart for file distribution by type using Recharts
    - Implement bar chart for file distribution by category using Recharts
    - Display recent files list
    - Handle empty files state with appropriate message
    - Implement reset button with confirmation dialog
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 8.1, 8.2_
  
  - [x] 9.4 Implement DataManagementScreen
    - Create `src/screens/DataManagementScreen.tsx`
    - Implement file upload control with drag-and-drop
    - Implement category dropdown selector
    - Display file list table with columns: name, type, category, date, actions
    - Implement download action
    - Implement delete action with confirmation prompt
    - Display success/error notifications
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_
  
  - [x] 9.5 Implement AIChatScreen
    - Create `src/screens/AIChatScreen.tsx`
    - Implement chat interface with message history
    - Implement text input field for questions
    - Display user and assistant messages
    - Display source file attributions with responses
    - Handle loading states during API calls
    - Handle error states (no relevant info, API unavailable)
    - _Requirements: 6.1, 6.6, 6.7, 6.8, 6.9_
  
  - [x] 9.6 Implement AIVisualizationScreen
    - Create `src/screens/AIVisualizationScreen.tsx`
    - Implement text input for visualization queries
    - Render bar, line, and pie charts using Recharts based on ChartConfig
    - Handle visualization generation failures with error message
    - _Requirements: 7.1, 7.4, 7.5, 7.6_

- [x] 10. Implement App Router and wire everything together
  - [x] 10.1 Set up React Router and App component
    - Create `src/App.tsx` with React Router configuration
    - Configure routes: `/`, `/dashboard`, `/data`, `/chat`, `/visualize`
    - Implement project existence check and conditional routing
    - Integrate NavigationBar for project-exists state
    - _Requirements: 9.1, 9.2, 9.3_

- [x] 11. Final checkpoint - Full integration
  - Test complete file upload flow: upload → process → verify in database
  - Test chat query flow: submit question → retrieve chunks → display response
  - Test visualization flow: submit query → generate chart → render
  - Test project reset flow: reset → verify deletion → redirect to create
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation throughout development
- Property tests validate universal correctness properties defined in the design
- Unit tests validate specific examples and edge cases
- Backend uses Python with FastAPI, frontend uses React with TypeScript
- ChromaDB collection name is "project_knowledge" as specified in design
- File categories are: Project Costs, Burndown, Audit, IT Controls, Remediation, Business Intelligence, Internal Data, Other

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.4"] },
    { "id": 1, "tasks": ["1.2", "1.3", "2.1"] },
    { "id": 2, "tasks": ["2.2", "3.1"] },
    { "id": 3, "tasks": ["3.2", "3.3", "3.4"] },
    { "id": 4, "tasks": ["3.5", "3.6"] },
    { "id": 5, "tasks": ["5.1", "5.3"] },
    { "id": 6, "tasks": ["5.2", "6.1"] },
    { "id": 7, "tasks": ["6.2", "6.3"] },
    { "id": 8, "tasks": ["6.4", "6.5"] },
    { "id": 9, "tasks": ["6.6", "6.7", "6.8"] },
    { "id": 10, "tasks": ["8.1"] },
    { "id": 11, "tasks": ["9.1"] },
    { "id": 12, "tasks": ["9.2", "9.3", "9.4", "9.5", "9.6"] },
    { "id": 13, "tasks": ["10.1"] }
  ]
}
```
