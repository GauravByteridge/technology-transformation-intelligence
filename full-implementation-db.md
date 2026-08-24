For the application DB, I would use PostgreSQL as the application/control-plane database, separate from the user's connected enterprise PostgreSQL sources.

The important distinction is:

                    YOUR APPLICATION
                          │
                          ▼
              ┌──────────────────────┐
              │ APPLICATION POSTGRES │
              │                      │
              │ users                │
              │ projects             │
              │ data_sources         │
              │ catalog              │
              │ conversations        │
              │ queries              │
              │ evidence             │
              │ lineage              │
              │ briefs               │
              └──────────────────────┘


       EXTERNAL / CONNECTED DATA SOURCES
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
       PostgreSQL      MongoDB        RAG
       Client DB       Client DB      Files

Do not mix the application tables with the connected customer's PostgreSQL tables.

That separation will make your architecture much cleaner.

1. Application DB — High-Level Design

I would organize the application DB into these logical areas:

APPLICATION POSTGRESQL
│
├── Identity / Access
│   ├── users
│   └── user_sessions (optional)
│
├── Projects
│   ├── projects
│   └── project_members
│
├── Data Sources
│   ├── data_sources
│   ├── data_source_credentials
│   └── data_source_discovery_runs
│
├── Enterprise Data Catalog
│   ├── catalog_entries
│   ├── catalog_fields
│   ├── catalog_relationships
│   ├── catalog_project_mappings
│   └── catalog_versions
│
├── Documents / RAG
│   ├── documents
│   ├── document_versions
│   └── document_processing_runs
│
├── AI / Conversations
│   ├── conversations
│   ├── messages
│   ├── queries
│   └── query_source_usage
│
├── Evidence / Lineage
│   ├── evidence
│   ├── lineage_runs
│   └── lineage_nodes
│
└── Executive Intelligence
    ├── executive_briefs
    └── brief_sources
2. users

Basic application users.

users
────────────────────────────
id                  UUID PK
email               VARCHAR UNIQUE
display_name        VARCHAR
role                VARCHAR
status              VARCHAR
created_at          TIMESTAMP
updated_at          TIMESTAMP
last_login_at       TIMESTAMP

For the POC, don't overbuild RBAC.

You can have:

ADMIN
USER

and expand later.

3. projects

This represents projects inside your application, not projects directly stored in an external DB.

projects
────────────────────────────
id                  UUID PK
project_code        VARCHAR UNIQUE
name                VARCHAR
description         TEXT
status              VARCHAR
start_date          DATE
end_date            DATE
budget              NUMERIC
created_at          TIMESTAMP
updated_at          TIMESTAMP

Example:

P001
Project Alpha
Technology Transformation
At Risk
4. project_members
project_members
────────────────────────────
id                  UUID PK
project_id          UUID FK
user_id             UUID FK
role                VARCHAR
created_at          TIMESTAMP

Relationship:

users
  │
  └──< project_members >──┐
                          │
                       projects
5. data_sources

This is one of the most important tables.

Every connected PostgreSQL/MongoDB/file source gets registered here.

data_sources
────────────────────────────────────
id                  UUID PK
project_id          UUID NULL
name                VARCHAR
source_type         VARCHAR
description         TEXT
status              VARCHAR
environment         VARCHAR
connection_config   JSONB
discovery_status    VARCHAR
last_discovered_at  TIMESTAMP
created_by          UUID FK
created_at          TIMESTAMP
updated_at          TIMESTAMP

source_type:

POSTGRESQL
MONGODB
FILE
RAG

However, I would not put raw passwords/API keys inside connection_config.

For example:

{
  "host": "db.company.com",
  "port": 5432,
  "database": "technology_transformation"
}

Credentials should be handled separately/securely.

6. data_source_credentials

For the POC, you can keep this abstraction even if credentials are initially stored through environment/secret management.

data_source_credentials
────────────────────────────
id                  UUID PK
data_source_id     UUID FK
credential_type     VARCHAR
secret_reference    VARCHAR
created_at          TIMESTAMP
updated_at          TIMESTAMP

For example:

data_source_id = PostgreSQL source
credential_type = DATABASE
secret_reference = vault://...

This means your DB never needs to contain:

password = MySecret123
7. data_source_discovery_runs

Every time you press Discover / Refresh, record a discovery run.

data_source_discovery_runs
────────────────────────────────
id                  UUID PK
data_source_id     UUID FK
status              VARCHAR
started_at          TIMESTAMP
completed_at        TIMESTAMP
objects_discovered  INTEGER
error_message       TEXT
catalog_version     INTEGER
created_at          TIMESTAMP

Example:

PostgreSQL
Discovery #3

Status: SUCCESS
Tables discovered: 42
Columns discovered: 318
Duration: 14 sec

This becomes useful in the UI.

8. Enterprise Data Catalog

This is the heart of Phase 8.

I would NOT create separate tables like:

postgres_tables
mongodb_collections

Instead use a common catalog model.

catalog_entries
catalog_entries
────────────────────────────────────
id                  UUID PK
data_source_id     UUID FK
parent_id           UUID NULL FK
catalog_version_id UUID FK

entry_type          VARCHAR
technical_name      VARCHAR
display_name        VARCHAR
schema_name         VARCHAR NULL
database_name       VARCHAR NULL
domain              VARCHAR NULL
description         TEXT
semantic_metadata   JSONB
project_key_field   VARCHAR NULL
confidence_score    NUMERIC
status              VARCHAR

created_at          TIMESTAMP
updated_at          TIMESTAMP

entry_type could be:

DATABASE
SCHEMA
TABLE
VIEW
COLLECTION
DATASET
DOCUMENT
SHEET

So:

PostgreSQL
   │
   └── public
        │
        └── project_finance

and:

MongoDB
   │
   └── project_risks

can both live in the same catalog model.

9. catalog_fields

Fields/columns discovered from catalog entries.

catalog_fields
────────────────────────────────────
id                  UUID PK
catalog_entry_id    UUID FK
field_name          VARCHAR
display_name        VARCHAR
data_type           VARCHAR
semantic_type       VARCHAR NULL
description         TEXT
nullable            BOOLEAN
is_identifier       BOOLEAN
is_project_key     BOOLEAN
is_sensitive        BOOLEAN
sample_metadata     JSONB
confidence_score    NUMERIC
ordinal_position    INTEGER
created_at          TIMESTAMP
updated_at          TIMESTAMP

Example:

project_finance

project_id
  semantic_type = PROJECT_ID

budget
  semantic_type = CURRENCY

actual_cost
  semantic_type = CURRENCY

variance
  semantic_type = CURRENCY
10. catalog_relationships

This is important for the AI to understand relationships.

catalog_relationships
────────────────────────────────────
id                  UUID PK
source_entry_id     UUID FK
target_entry_id     UUID FK
relationship_type   VARCHAR
source_field_id     UUID NULL
target_field_id     UUID NULL
confidence_score    NUMERIC
discovered_by       VARCHAR
created_at          TIMESTAMP

Example:

project_finance.project_id
             │
             ▼
projects.project_id

or:

project_finance.project_id
             │
             ▼
MongoDB.project_risks.project_id
11. catalog_project_mappings

This addresses the point we discussed earlier:

The catalog belongs to the source, but datasets can be mapped to projects.

catalog_project_mappings
────────────────────────────────
id                  UUID PK
catalog_entry_id    UUID FK
project_id          UUID FK
mapping_type        VARCHAR
mapping_expression  JSONB
confidence_score    NUMERIC
created_at          TIMESTAMP
updated_at          TIMESTAMP

Example:

Project Alpha
   │
   ├── project_finance
   ├── jira_issues
   ├── project_risks
   └── meeting_notes
12. catalog_versions

You want discovery to be versioned.

catalog_versions
────────────────────────────
id                  UUID PK
data_source_id     UUID FK
version_number      INTEGER
status              VARCHAR
discovery_run_id    UUID FK
created_at          TIMESTAMP

So:

PostgreSQL
   │
   ├── Catalog v1
   ├── Catalog v2
   └── Catalog v3 ← current

If discovery fails, don't destroy v3.

13. Documents / RAG
documents
documents
────────────────────────────────
id                  UUID PK
data_source_id     UUID FK
project_id          UUID NULL
file_name            VARCHAR
file_type            VARCHAR
storage_reference    TEXT
file_size            BIGINT
checksum             VARCHAR
status               VARCHAR
page_count           INTEGER NULL
metadata             JSONB
created_by           UUID FK
created_at           TIMESTAMP
updated_at           TIMESTAMP

Example:

Project_Risk_Report.pdf
Audit_Report.pdf
Technology_Transformation.xlsx
Meeting_Notes.docx
14. document_versions
document_versions
────────────────────────────
id                  UUID PK
document_id         UUID FK
version_number      INTEGER
checksum            VARCHAR
storage_reference   TEXT
processing_status   VARCHAR
created_at          TIMESTAMP
15. document_processing_runs
document_processing_runs
────────────────────────────
id                  UUID PK
document_id         UUID FK
status              VARCHAR
parser_type         VARCHAR
started_at          TIMESTAMP
completed_at        TIMESTAMP
chunks_created      INTEGER
datasets_created    INTEGER
error_message       TEXT

This is useful for:

Excel
 ↓
Parsing
 ↓
Structured extraction
 ↓
RAG extraction
 ↓
Catalog
16. Conversations
conversations
conversations
────────────────────────────
id                  UUID PK
project_id          UUID NULL
user_id             UUID FK
title               VARCHAR
mode                VARCHAR
llm_provider        VARCHAR
created_at          TIMESTAMP
updated_at          TIMESTAMP

mode:

DEMO
REAL
17. messages
messages
────────────────────────────
id                  UUID PK
conversation_id     UUID FK
role                VARCHAR
content             TEXT
sequence_number     INTEGER
created_at          TIMESTAMP

Roles:

USER
ASSISTANT
SYSTEM

Don't store chain-of-thought.

18. queries

I would separate a query execution from a conversation message.

queries
────────────────────────────────
id                  UUID PK
conversation_id     UUID FK
project_id          UUID NULL
user_id             UUID FK
question            TEXT
status              VARCHAR
mode                VARCHAR
llm_provider        VARCHAR
is_partial          BOOLEAN
started_at          TIMESTAMP
completed_at        TIMESTAMP
duration_ms         INTEGER
created_at          TIMESTAMP

This is what powers Query History.

19. query_source_usage

This is extremely important for:

"Sources Consulted"

query_source_usage
────────────────────────────────
id                  UUID PK
query_id            UUID FK
data_source_id      UUID FK
catalog_entry_id    UUID NULL
tool_name           VARCHAR
status              VARCHAR
records_retrieved   INTEGER
chunks_retrieved    INTEGER
duration_ms         INTEGER
error_message       TEXT
created_at          TIMESTAMP

Example:

Query: Why is Project Alpha at risk?

PostgreSQL / Finance
  SUCCESS
  3 records

MongoDB / Risks
  SUCCESS
  4 records

RAG / Meeting Notes
  SUCCESS
  5 chunks

This table should drive the UI.

Never manually construct the Sources Consulted list.

20. Evidence
evidence
evidence
────────────────────────────────────
id                  UUID PK
query_id            UUID FK
query_source_usage_id UUID FK
evidence_type       VARCHAR
source_reference    JSONB
content             TEXT
structured_value    JSONB
page_number         INTEGER NULL
sheet_name          VARCHAR NULL
record_reference    VARCHAR NULL
relevance_score     NUMERIC NULL
created_at          TIMESTAMP

This supports all source types.

For PostgreSQL:

table
record
fields
values

MongoDB:

collection
document
fields
values

PDF:

file
page
excerpt

Excel:

file
sheet
region
excerpt/value
21. Lineage

I'd use two tables.

lineage_runs
lineage_runs
────────────────────────────
id                  UUID PK
query_id            UUID FK
created_at          TIMESTAMP
lineage_nodes
lineage_nodes
────────────────────────────────
id                  UUID PK
lineage_run_id      UUID FK
node_type           VARCHAR
node_key            VARCHAR
label               VARCHAR
source_id           UUID NULL
catalog_entry_id    UUID NULL
tool_name           VARCHAR NULL
metadata            JSONB
sequence_number     INTEGER
created_at          TIMESTAMP

Node types:

QUESTION
CATALOG
TOOL
DATA_SOURCE
DATASET
DOCUMENT
EVIDENCE
SYNTHESIS
ANSWER

Then:

QUESTION
   ↓
CATALOG
   ↓
TOOL
   ↓
DATA_SOURCE
   ↓
DATASET
   ↓
EVIDENCE
   ↓
SYNTHESIS
   ↓
ANSWER
22. Executive Briefs
executive_briefs
executive_briefs
────────────────────────────────
id                  UUID PK
project_id          UUID FK
title               VARCHAR
summary             TEXT
content             JSONB
generated_by_query  UUID NULL
status              VARCHAR
created_by          UUID FK
created_at          TIMESTAMP
updated_at          TIMESTAMP
brief_sources
brief_sources
────────────────────────────
id                  UUID PK
brief_id            UUID FK
evidence_id         UUID NULL
query_id            UUID NULL
created_at          TIMESTAMP
23. Complete ER-style view

The whole application DB becomes:

                           USERS
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
          PROJECTS      CONVERSATIONS    DATA SOURCES
              │              │              │
              │              ▼              ▼
              │          MESSAGES      DISCOVERY RUNS
              │                             │
              │                             ▼
              │                      CATALOG VERSIONS
              │                             │
              │                             ▼
              │                       CATALOG ENTRIES
              │                         │       │
              │                         │       ▼
              │                         │  CATALOG FIELDS
              │                         │
              │                         ▼
              │                  CATALOG RELATIONSHIPS
              │
              ▼
       PROJECT MAPPINGS
              │
              └───────────────┐
                              ▼
                         DATA CATALOG


DATA SOURCES
     │
     ├──────────────► DOCUMENTS
     │                    │
     │                    ▼
     │             DOCUMENT VERSIONS
     │                    │
     │                    ▼
     │             PROCESSING RUNS
     │
     ▼
   QUERIES
     │
     ├──────────────► QUERY SOURCE USAGE
     │                       │
     │                       ▼
     │                    EVIDENCE
     │
     └──────────────► LINEAGE RUN
                             │
                             ▼
                       LINEAGE NODES


PROJECTS
    │
    ▼
EXECUTIVE BRIEFS
    │
    ▼
BRIEF SOURCES
24. The most important relationship

The architecture should make this relationship very clear:

                  APPLICATION DB
                       │
                       │ metadata/control
                       ▼
             ┌─────────────────────┐
             │ Enterprise Catalog  │
             └──────────┬──────────┘
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
     PostgreSQL       MongoDB         RAG
     CONNECTED        CONNECTED      DOCUMENTS
     SOURCE           SOURCE
         │              │              │
         └──────────────┼──────────────┘
                        ▼
                     STRANDS
                        │
                        ▼
                     QUERY
                        │
                        ▼
              QUERY SOURCE USAGE
                        │
                        ▼
                    EVIDENCE
                        │
                        ▼
                    LINEAGE

Application PostgreSQL does not contain the customer's actual enterprise data.

It contains:

what sources are connected
how they are configured
what was discovered
what the catalog says
project mappings
conversations
queries
evidence
lineage
application state

The actual data stays in:

Client PostgreSQL
Client MongoDB
Uploaded documents / RAG storage

That separation is very important for the POC architecture.