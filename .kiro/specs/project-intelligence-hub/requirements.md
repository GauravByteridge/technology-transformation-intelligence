# Requirements Document

## Introduction

The Project Intelligence Hub is a RAG-based proof-of-concept (POC) application that enables users to create a single project, upload various file types (PDF, Excel, CSV, JSON), automatically process and index data into ChromaDB, and interact with the combined information through an AI-powered chatbot. The application prioritizes simplicity and functionality over enterprise features.

**Key Constraints:** No authentication, no user management, no multi-project support, no complex validation, no microservices. This is a lightweight POC designed for rapid prototyping and demonstration.

## Glossary

- **Project**: A single container holding all uploaded files, metadata, and vector embeddings for a POC session
- **RAG_Pipeline**: Retrieval-Augmented Generation system that combines vector search with LLM inference to answer questions
- **ChromaDB**: Vector database storing document embeddings in a single collection called "project_knowledge"
- **Chunk**: A segment of extracted text (800-1000 characters) prepared for embedding and storage
- **Embedding**: A vector representation of text content used for semantic similarity search
- **Groq_API**: External LLM inference service used for generating chat responses
- **File_Category**: Classification label for uploaded files (Project Costs, Burndown, Audit, IT Controls, Remediation, Business Intelligence, Internal Data, Other)
- **Dashboard**: Overview screen displaying project statistics and file distribution charts
- **Reset**: Complete deletion of all project data, files, vectors, and metadata returning the application to initial state

## Requirements

### Requirement 1: Project Creation

**User Story:** As a user, I want to create a single project with a name and description, so that I can begin uploading and analyzing project-related data.

#### Acceptance Criteria

1. THE Create_Project_Screen SHALL display a form with two input fields: project name and project description
2. WHEN the user submits a valid project name, THE System SHALL create a new project record in PostgreSQL with name, description, and created_at timestamp
3. WHEN a project already exists, THE Create_Project_Screen SHALL redirect to the Dashboard_Screen
4. WHEN the user submits an empty project name, THE System SHALL display an inline error message
5. WHEN project creation succeeds, THE System SHALL redirect the user to the Dashboard_Screen

### Requirement 2: Dashboard Display

**User Story:** As a user, I want to view a dashboard with project information and file statistics, so that I can understand the current state of my project data.

#### Acceptance Criteria

1. THE Dashboard_Screen SHALL display the project name and description
2. THE Dashboard_Screen SHALL display the total count of uploaded files
3. THE Dashboard_Screen SHALL display a pie chart showing file distribution by file type (PDF, Excel, CSV, JSON)
4. THE Dashboard_Screen SHALL display a bar chart showing file distribution by category
5. THE Dashboard_Screen SHALL display a list of the five most recently uploaded files with file name and upload date
6. WHEN no files exist, THE Dashboard_Screen SHALL display a message indicating no files have been uploaded

### Requirement 3: File Upload

**User Story:** As a user, I want to upload project-related files with category labels, so that the data can be processed and made searchable.

#### Acceptance Criteria

1. THE Data_Management_Screen SHALL provide a file upload control accepting PDF, Excel (.xlsx, .xls), CSV, and JSON file types
2. THE Data_Management_Screen SHALL provide a dropdown selector for file category with options: Project Costs, Burndown, Audit, IT Controls, Remediation, Business Intelligence, Internal Data, Other
3. WHEN the user uploads a file, THE System SHALL store the original file in the designated file storage directory
4. WHEN the user uploads a file with an unsupported file type, THE System SHALL reject the upload and display an error message
5. WHEN file upload succeeds, THE System SHALL display a success notification to the user

### Requirement 4: File Processing Pipeline

**User Story:** As a user, I want uploaded files to be automatically processed and indexed, so that the content becomes searchable through the AI chatbot.

#### Acceptance Criteria

1. WHEN a file is uploaded, THE File_Processor SHALL detect the file type and apply the appropriate extraction method (PyMuPDF for PDF, pandas for Excel/CSV, Python JSON for JSON)
2. WHEN text extraction completes, THE File_Processor SHALL normalize the content to plain text format
3. WHEN normalization completes, THE Chunker SHALL split the text into segments of 800-1000 characters with appropriate overlap
4. WHEN chunking completes, THE Embedding_Generator SHALL create vector embeddings for each chunk
5. WHEN embeddings are generated, THE System SHALL store the embeddings in the ChromaDB collection named "project_knowledge"
6. WHEN vector storage completes, THE System SHALL save file metadata (file_name, file_type, category, file_path, uploaded_at, chunk_count) to PostgreSQL
7. IF text extraction fails, THEN THE System SHALL log the error and notify the user that processing failed

### Requirement 5: File Management

**User Story:** As a user, I want to view, download, and delete uploaded files, so that I can manage my project data.

#### Acceptance Criteria

1. THE Data_Management_Screen SHALL display a table listing all uploaded files with columns: file name, file type, category, upload date, and actions
2. WHEN the user clicks the download action for a file, THE System SHALL download the original file to the user's device
3. WHEN the user clicks the delete action for a file, THE System SHALL display a confirmation prompt
4. WHEN the user confirms file deletion, THE System SHALL delete the original file from storage
5. WHEN the user confirms file deletion, THE System SHALL delete all associated chunks from ChromaDB
6. WHEN the user confirms file deletion, THE System SHALL delete the file metadata from PostgreSQL
7. WHEN deletion completes, THE Data_Management_Screen SHALL refresh the file list

### Requirement 6: AI Chat Interface

**User Story:** As a user, I want to ask questions about my project data and receive AI-generated answers with source references, so that I can gain insights from the combined information.

#### Acceptance Criteria

1. THE AI_Chat_Screen SHALL display a chat interface with message history and a text input field
2. WHEN the user submits a question, THE RAG_Pipeline SHALL generate an embedding for the question
3. WHEN the question embedding is generated, THE RAG_Pipeline SHALL search ChromaDB for the top 5 most similar chunks
4. WHEN relevant chunks are retrieved, THE RAG_Pipeline SHALL construct a prompt combining the context and the user question
5. WHEN the prompt is constructed, THE RAG_Pipeline SHALL send the prompt to Groq_API for inference
6. WHEN Groq_API returns a response, THE AI_Chat_Screen SHALL display the answer in the chat history
7. WHEN Groq_API returns a response, THE AI_Chat_Screen SHALL display a list of source file names that contributed to the answer
8. IF no relevant chunks are found, THEN THE System SHALL inform the user that no relevant information was found in the project data
9. IF Groq_API request fails, THEN THE System SHALL display an error message indicating the AI service is unavailable

### Requirement 7: AI Visualization Generation (Optional)

**User Story:** As a user, I want to generate data visualizations from natural language queries, so that I can visually explore trends and patterns in my project data.

#### Acceptance Criteria

1. THE AI_Visualization_Screen SHALL display a text input field for entering visualization queries
2. WHEN the user submits a visualization query, THE Visualization_Generator SHALL retrieve relevant data from the project files
3. WHEN relevant data is retrieved, THE Visualization_Generator SHALL use Groq_API to determine the appropriate chart type and data mapping
4. WHEN chart configuration is determined, THE AI_Visualization_Screen SHALL render the chart using Recharts
5. THE AI_Visualization_Screen SHALL support bar charts, line charts, and pie charts
6. IF visualization generation fails, THEN THE System SHALL display a message explaining that the requested visualization could not be generated

### Requirement 8: Project Reset

**User Story:** As a user, I want to completely reset the project and start fresh, so that I can begin a new POC session without residual data.

#### Acceptance Criteria

1. THE Dashboard_Screen SHALL display a reset button clearly labeled
2. WHEN the user clicks the reset button, THE System SHALL display a confirmation dialog warning that all data will be permanently deleted
3. WHEN the user confirms reset, THE System SHALL delete all uploaded files from storage
4. WHEN the user confirms reset, THE System SHALL delete all chunks from the ChromaDB collection
5. WHEN the user confirms reset, THE System SHALL delete all file metadata from PostgreSQL
6. WHEN the user confirms reset, THE System SHALL delete the project record from PostgreSQL
7. WHEN reset completes, THE System SHALL redirect the user to the Create_Project_Screen
8. WHEN reset completes, THE System SHALL clear any in-memory chat history

### Requirement 9: Navigation

**User Story:** As a user, I want to navigate between application screens easily, so that I can access different features without confusion.

#### Acceptance Criteria

1. WHILE a project exists, THE Navigation_Bar SHALL display links to Dashboard, Data Management, AI Chat, and AI Visualization screens
2. WHILE no project exists, THE System SHALL only display the Create_Project_Screen
3. WHEN the user clicks a navigation link, THE System SHALL load the corresponding screen

### Requirement 10: API Endpoints

**User Story:** As a frontend developer, I want well-defined API endpoints, so that I can integrate the React frontend with the FastAPI backend.

#### Acceptance Criteria

1. THE Backend SHALL expose POST /api/project endpoint for creating a project
2. THE Backend SHALL expose GET /api/project endpoint for retrieving current project details
3. THE Backend SHALL expose DELETE /api/project/reset endpoint for resetting all project data
4. THE Backend SHALL expose POST /api/files/upload endpoint for uploading files with category metadata
5. THE Backend SHALL expose GET /api/files endpoint for listing all uploaded files
6. THE Backend SHALL expose GET /api/files/{id} endpoint for downloading a specific file
7. THE Backend SHALL expose DELETE /api/files/{id} endpoint for deleting a specific file
8. THE Backend SHALL expose GET /api/dashboard endpoint for retrieving dashboard statistics
9. THE Backend SHALL expose POST /api/chat endpoint for submitting chat queries and receiving responses
10. THE Backend SHALL expose POST /api/visualize endpoint for submitting visualization queries
11. WHEN any API request fails, THE Backend SHALL return an appropriate HTTP error code and error message in JSON format
