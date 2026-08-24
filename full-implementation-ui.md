Based on everything we've defined for Phases 0–8, I would structure the UI as an Enterprise Information Intelligence / Databricks-like application, where the dashboard is the navigation layer and the Data Sources → Catalog → Project 360 → AI Query → Evidence/Lineage flow is the core experience.

The most important principle is:

The UI should make it obvious that the AI understands the connected enterprise information, not just that it has a chatbot.

1. Overall application structure
┌─────────────────────────────────────────────────────────────────────────┐
│                         TOP NAVIGATION                                   │
│                                                                         │
│  Enterprise Intelligence     Environment: REAL     User ▾              │
└─────────────────────────────────────────────────────────────────────────┘

┌───────────────┬─────────────────────────────────────────────────────────┐
│               │                                                         │
│  SIDEBAR      │                    MAIN CONTENT                         │
│               │                                                         │
│  🏠 Overview  │                                                         │
│  📊 Dashboard  │                                                         │
│  📁 Projects  │                                                         │
│  🔌 Data       │                                                         │
│     Sources    │                                                         │
│  🗂 Data       │                                                         │
│     Catalog    │                                                         │
│  🤖 AI Query   │                                                         │
│  🕘 History    │                                                         │
│  📑 Briefs     │                                                         │
│               │                                                         │
│  ⚙ Settings   │                                                         │
│               │                                                         │
└───────────────┴─────────────────────────────────────────────────────────┘

I would keep the sidebar relatively small.

The primary navigation should be:

Overview
Projects
Data Sources
Data Catalog
AI Query
Query History
Executive Briefs

Settings can be lower down.

2. HOME / OVERVIEW

This is the first screen after login.

The purpose is not to overwhelm the user with technical information.

It should answer:

"What is happening across my technology transformation portfolio?"

┌─────────────────────────────────────────────────────────────────┐
│ Technology Transformation Intelligence                         │
│                                                                 │
│ Connected Sources: 8       Projects: 24       Documents: 342    │
│                                                                 │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌───────────────┐ │
│ │ Projects   │ │ At Risk    │ │ Budget     │ │ Open Risks    │ │
│ │    24      │ │     5      │ │  $12.4M    │ │      31       │ │
│ └────────────┘ └────────────┘ └────────────┘ └───────────────┘ │
│                                                                 │
│ Portfolio Health                                               │
│                                                                 │
│  Project Alpha      ███████████░░   At Risk                     │
│  Project Beta       █████████████   On Track                   │
│  Project Gamma      ████████░░░░░   Attention                  │
│                                                                 │
│ Recent Activity                                                 │
│                                                                 │
│ • PostgreSQL source connected                                  │
│ • 12 documents indexed                                         │
│ • Project Alpha risk updated                                    │
│                                                                 │
│                         [ Ask AI ]                              │
└─────────────────────────────────────────────────────────────────┘

The Ask AI button should be prominent.

3. DATA SOURCES — MOST IMPORTANT NEW UI

This is where the user connects PostgreSQL, MongoDB and potentially other sources.

┌─────────────────────────────────────────────────────────────────┐
│ Data Sources                                      [+ Add Source]│
│                                                                 │
│ Connect enterprise data sources and make them AI-queryable.     │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 🐘 Client PostgreSQL                         CONNECTED ✓    │ │
│ │                                                             │ │
│ │ Type: PostgreSQL                                           │ │
│ │ Database: TechnologyTransformation                          │ │
│ │                                                             │ │
│ │ 5 Schemas   42 Tables   318 Columns                        │ │
│ │                                                             │ │
│ │ Last Discovery: 5 min ago                                  │ │
│ │                                                             │ │
│ │ [View Schema] [View Catalog] [Refresh Discovery]            │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 🍃 Client MongoDB                             CONNECTED ✓    │ │
│ │                                                             │ │
│ │ 4 Databases   12 Collections                               │ │
│ │                                                             │ │
│ │ [View Collections] [View Catalog] [Refresh Discovery]       │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 📄 Enterprise Documents                         READY ✓     │ │
│ │                                                             │ │
│ │ 342 Documents   18 Datasets                                │ │
│ │                                                             │ │
│ │ [Browse] [Upload Files]                                     │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
4. ADD DATA SOURCE FLOW

Click:

+ Add Source

Then:

┌──────────────────────────────────────────────┐
│ Add Data Source                              │
│                                              │
│ Select source type                           │
│                                              │
│  🐘 PostgreSQL                               │
│  🍃 MongoDB                                  │
│  📄 Files / Documents                        │
│                                              │
│                         [Continue]            │
└──────────────────────────────────────────────┘
PostgreSQL
┌──────────────────────────────────────────────┐
│ Connect PostgreSQL                           │
│                                              │
│ Connection Name                              │
│ [ Client PostgreSQL                       ]  │
│                                              │
│ Host                                         │
│ [ db.company.com                         ]   │
│                                              │
│ Port                                         │
│ [ 5432 ]                                     │
│                                              │
│ Database                                     │
│ [ TechnologyTransformation               ]   │
│                                              │
│ Username                                     │
│ [ ********                               ]   │
│                                              │
│ Password                                     │
│ [ ********                               ]   │
│                                              │
│ [ Test Connection ]                          │
│                                              │
│                         [Connect & Discover]  │
└──────────────────────────────────────────────┘

Then the important experience:

Connecting...
      ↓
✓ Connection established
      ↓
Discovering schemas...
      ↓
Discovering tables...
      ↓
Discovering columns...
      ↓
Profiling metadata...
      ↓
Understanding datasets...
      ↓
Building semantic catalog...
      ↓
✓ Ready

This is a great demo moment.

You're showing the client:

"We don't need to manually tell the system what is inside the database."

5. SOURCE DISCOVERY RESULT

After discovery:

┌─────────────────────────────────────────────────────────────────┐
│ Client PostgreSQL                                               │
│ Connected ✓                                                     │
│                                                                 │
│ Discovery Complete                                              │
│                                                                 │
│ Schemas          Tables          Columns          Projects       │
│    5               42              318               24          │
│                                                                 │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│ Discovered Data                                                │
│                                                                 │
│ Finance                                                          │
│   └── project_finance                                           │
│       budget                                                    │
│       actual_cost                                               │
│       variance                                                  │
│                                                                 │
│ JIRA                                                            │
│   └── jira_issues                                               │
│       issue_id                                                  │
│       status                                                    │
│       priority                                                  │
│       story_points                                              │
│                                                                 │
│ Resources                                                       │
│   └── project_resources                                         │
│       allocation                                                │
│       utilization                                               │
│                                                                 │
│ [Open Data Catalog]                                             │
└─────────────────────────────────────────────────────────────────┘
6. DATA CATALOG

This is one of the most important screens in the entire POC.

It demonstrates that your system has actually understood the connected data.

┌─────────────────────────────────────────────────────────────────┐
│ Data Catalog                                                    │
│                                                                 │
│ Search datasets, fields, domains and business concepts          │
│ [ Search: finance, project risk, actual cost...              ]  │
│                                                                 │
│ Filters:                                                        │
│ [All Sources] [All Domains] [All Projects]                     │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Project Financials                                          │ │
│ │                                                             │ │
│ │ Source: PostgreSQL                                         │ │
│ │ Domain: Finance                                            │ │
│ │                                                             │ │
│ │ Contains project budget, actual expenditure and variance.   │ │
│ │                                                             │ │
│ │ Fields                                                       │ │
│ │ project_id    Project identifier                            │ │
│ │ budget        Approved project budget                       │ │
│ │ actual_cost   Current actual expenditure                    │ │
│ │ variance      Budget variance                               │ │
│ │                                                             │ │
│ │ Projects: 24                                                │ │
│ │                                                             │ │
│ │ [View Details]                                              │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

A MongoDB entry could look like:

Project Risks

Source: MongoDB
Domain: Risk

Contains current and historical project risk observations.

Fields:
project_id
severity
status
description
created_at

And a document:

Project Alpha Meeting Notes

Source: RAG
Domain: Project Updates

PDF
Pages: 12
Project: Alpha

Contains steering committee discussions,
decisions and project concerns.
7. FILE UPLOAD FLOW

The user clicks:

Upload Files

┌──────────────────────────────────────────────────────────────┐
│ Upload Enterprise Information                                │
│                                                              │
│ Drag & drop files here                                       │
│                                                              │
│ PDF  DOCX  XLSX  XLS  CSV  TXT  JSON                         │
│                                                              │
│ [ Browse Files ]                                             │
└──────────────────────────────────────────────────────────────┘

After upload:

Project_Risk_Report.pdf
      ✓ Uploaded
      ↓
Parsing
      ↓
Content extraction
      ↓
Classification
      ↓
Chunking / Dataset extraction
      ↓
Indexing
      ↓
Catalog registration
      ↓
✓ AI Queryable

For Excel:

Technology_Transformation.xlsx

Sheets discovered:
✓ Project Summary
✓ Financials
✓ Risks
✓ Resource Allocation
✓ Notes

Detected:
3 structured datasets
2 semi-structured regions
4 narrative sections

This reinforces the point we've discussed:

Excel is not automatically treated as a clean table.

8. PROJECTS

Click:

Projects

┌──────────────────────────────────────────────────────────────┐
│ Projects                                      [+ New Project]│
│                                                              │
│ Search projects                                              │
│ [ Project name...                                          ] │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Project Alpha                           🔴 At Risk       │ │
│ │                                                          │ │
│ │ Budget: $1.0M        Actual: $1.14M                      │ │
│ │ Progress: 72%        Schedule: +18 days                  │ │
│ │ Open Risks: 7        Issues: 14                          │ │
│ │                                                          │ │
│ │ [Open Project 360]                                       │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Project Beta                            🟢 On Track      │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
9. PROJECT 360

This should be one of the strongest screens.

┌─────────────────────────────────────────────────────────────────┐
│ ← Projects     Project Alpha                         🔴 At Risk │
│                                                                 │
│ Overview | Financials | Progress | Risks | Audit | Resources | AI│
│                                                                 │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌───────────────┐ │
│ │ Budget     │ │ Actual     │ │ Progress   │ │ Open Risks    │ │
│ │ $1.00M     │ │ $1.14M     │ │ 72%        │ │ 7             │ │
│ └────────────┘ └────────────┘ └────────────┘ └───────────────┘ │
│                                                                 │
│ Financial Overview                                              │
│                                                                 │
│ Budget vs Actual                                               │
│ ███████████████████████████████████                           │
│                                                                 │
│ Progress / Burn Down                                            │
│ [chart]                                                         │
│                                                                 │
│ Risk Summary                                                    │
│ 🔴 UAT Delay                                                   │
│ 🟠 Resource Constraint                                         │
│ 🟠 Budget Variance                                             │
│                                                                 │
│ Recent Documents                                                │
│ Meeting Notes.pdf                                               │
│ Risk_Report.xlsx                                                │
│ Audit_Report.pdf                                                │
│                                                                 │
│                  [ Ask AI about Project Alpha ]                 │
└─────────────────────────────────────────────────────────────────┘
10. AI QUERY — THE CORE EXPERIENCE

Click:

AI Query

┌─────────────────────────────────────────────────────────────────┐
│ AI Enterprise Intelligence                                     │
│                                                                 │
│ Ask questions across your connected enterprise information.     │
│                                                                 │
│ Project Context: [ Project Alpha ▼ ]                            │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                                                             │ │
│ │ What would you like to know?                               │ │
│ │                                                             │ │
│ │ [ Why is Project Alpha at risk?                          ] │ │
│ │                                                             │ │
│ │                                      [Ask AI →]             │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Suggested questions                                             │
│                                                                 │
│ • Why is this project at risk?                                  │
│ • What is causing the budget variance?                          │
│ • What are the biggest unresolved issues?                       │
│ • What should the project manager prioritize?                   │
└─────────────────────────────────────────────────────────────────┘
11. AI EXECUTION EXPERIENCE

When the user submits:

Why is Project Alpha at risk?

Don't just show a spinner.

Show a lightweight status:

Analyzing your question...

✓ Understanding project context
✓ Finding relevant enterprise information
✓ Consulting PostgreSQL — Finance
✓ Consulting MongoDB — Project Risks
✓ Searching Project Documents
✓ Correlating evidence

Generating grounded answer...

This is a huge demo value.

But don't expose chain-of-thought.

You're showing execution status, not reasoning.

12. AI ANSWER
┌─────────────────────────────────────────────────────────────────┐
│ Why is Project Alpha at risk?                                  │
│                                                                 │
│ Project Alpha is currently at risk due to a combination of      │
│ budget pressure, schedule slippage and unresolved project risks.│
│                                                                 │
│ The project is approximately 14% over its current budget, while │
│ UAT completion has slipped and several high-severity risks      │
│ remain unresolved.                                              │
│                                                                 │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│ Sources Consulted (3)                              [Expand ▼]   │
│                                                                 │
│ ✓ PostgreSQL — Project Financials                              │
│ ✓ MongoDB — Project Risks                                     │
│ ✓ Project Alpha Meeting Notes.pdf                             │
│                                                                 │
│ Evidence (3)                                       [Expand ▼]   │
│ Data Lineage                                      [Expand ▼]   │
└─────────────────────────────────────────────────────────────────┘
13. EVIDENCE PANEL

When expanded:

Evidence

┌──────────────────────────────────────────────────────────────┐
│ PostgreSQL — Project Financials                              │
│                                                              │
│ Table: project_finance                                       │
│ Project: Alpha                                               │
│                                                              │
│ Budget:      $1,000,000                                      │
│ Actual Cost: $1,140,000                                      │
│ Variance:    +14%                                            │
│                                                              │
│ [View Source]                                                │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ MongoDB — Project Risks                                      │
│                                                              │
│ Collection: project_risks                                    │
│ Severity: HIGH                                               │
│ Status: OPEN                                                 │
│                                                              │
│ Risk: UAT delay                                               │
│                                                              │
│ [View Source]                                                │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Project Alpha Meeting Notes.pdf                              │
│                                                              │
│ Page 4                                                        │
│                                                              │
│ "UAT completion has slipped..."                              │
│                                                              │
│ [Open Document]                                              │
└──────────────────────────────────────────────────────────────┘
14. DATA LINEAGE PANEL

This is where the demo becomes very compelling.

Data Lineage

Question
   │
   ▼
"Why is Project Alpha at risk?"
   │
   ▼
Strands Agent
   │
   ├───────────────┐
   ▼               ▼
PostgreSQL       MongoDB
Finance          Project Risks
   │               │
   │               │
   └───────┬───────┘
           │
           ▼
     Meeting Notes
           │
           ▼
        Evidence
           │
           ▼
     AI Synthesis
           │
           ▼
        Answer

Clicking a node should show:

Source
Type
Dataset/Table/Collection
Records Retrieved
Execution Time
Status
15. QUERY HISTORY

This should be a first-class feature because we discussed it earlier.

┌──────────────────────────────────────────────────────────────┐
│ Query History                                                 │
│                                                              │
│ Search queries                                               │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Why is Project Alpha at risk?                            │ │
│ │ Project Alpha • Today 10:32 AM                           │ │
│ │ Sources: PostgreSQL, MongoDB, RAG                        │ │
│ │ [Open]                                                   │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ What is Project Beta's budget variance?                  │ │
│ │ Project Beta • Yesterday                                │ │
│ │ Source: PostgreSQL                                      │ │
│ │ [Open]                                                   │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘

Opening a query should restore:

Question
Answer
Sources
Evidence
Lineage
16. EXECUTIVE BRIEFS

This is the presentation layer.

┌──────────────────────────────────────────────────────────────┐
│ Executive Briefs                              [+ Generate]    │
│                                                              │
│ Project Alpha — Weekly Brief                                 │
│ Generated: Aug 24                                            │
│                                                              │
│ Executive Summary                                            │
│ Project remains at risk due to...                            │
│                                                              │
│ Key Metrics                                                  │
│ Budget variance: +14%                                        │
│ Progress: 72%                                                │
│ Open risks: 7                                                │
│                                                              │
│ Key Risks                                                    │
│ 1. UAT delay                                                 │
│ 2. Resource constraint                                       │
│ 3. Budget pressure                                           │
│                                                              │
│ Evidence                                                    │
│ ...                                                          │
│                                                              │
│ [View Sources] [Export]                                      │
└──────────────────────────────────────────────────────────────┘
17. SETTINGS

Keep this relatively simple for the POC.

Settings

General
AI Configuration
Data Sources
LLM Provider
Environment
AI Configuration
Mode

○ Demo
● Real

LLM Provider

○ Azure OpenAI
○ Azure AI Foundry
○ Groq

Model
[ ... ]

[ Test Provider ]

Credentials should never be displayed.

18. COMPLETE USER FLOW

Now the entire client walkthrough can be:

                    LOGIN
                      │
                      ▼
                  OVERVIEW
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
     DATA SOURCES              PROJECTS
          │                       │
          ▼                       ▼
    Add PostgreSQL           Project Alpha
          │                       │
          ▼                       ▼
       Connect               Project 360
          │                       │
          ▼                       │
      Discover                    │
          │                       │
          ▼                       │
    Build Catalog                 │
          │                       │
          ▼                       │
    Add MongoDB                   │
          │                       │
          ▼                       │
      Discover                    │
          │                       │
          ▼                       │
    Build Catalog                 │
          │                       │
          ▼                       │
     Upload Files                 │
          │                       │
          ▼                       │
      RAG/Parse                   │
          │                       │
          ▼                       │
    Update Catalog                │
          │                       │
          └───────────┬───────────┘
                      ▼
                  AI QUERY
                      │
                      ▼
             User asks question
                      │
                      ▼
               Catalog lookup
                      │
                      ▼
                  STRANDS
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
      PostgreSQL   MongoDB       RAG
          │           │           │
          └───────────┼───────────┘
                      ▼
                  Evidence
                      │
                      ▼
                   Answer
                      │
             ┌────────┼────────┐
             ▼        ▼        ▼
          Sources  Evidence  Lineage
                      │
                      ▼
                Query History
                      │
                      ▼
                Executive Brief
19. The actual client "wow" flow

If I were presenting this to the client, I wouldn't start by showing the dashboard.

I'd do this:

Step 1 — Show Data Sources

"We can connect to enterprise data sources."

PostgreSQL ✓
MongoDB ✓
Documents ✓
Step 2 — Connect/discover

Open PostgreSQL and show:

Discovering...
42 tables
318 columns
Finance
JIRA
Resources
Projects

Then MongoDB.

Step 3 — Show Data Catalog

Say:

"The platform doesn't just connect to the database. It discovers and understands what information is available."

Show:

Finance
Risks
JIRA
Resources
Project Updates
Step 4 — Upload an Excel/PDF

Show:

Excel
 ↓
Multiple sheets
 ↓
Structured + semi-structured + narrative
 ↓
Catalog + RAG
Step 5 — Open Project Alpha

Show Project 360.

Step 6 — Ask the killer question

"Why is Project Alpha at risk?"

Then show:

Analyzing...
✓ PostgreSQL
✓ MongoDB
✓ RAG
Step 7 — Answer

Then expand:

Sources → Evidence → Lineage

And say:

"The answer isn't coming from a single database. The AI identified the relevant information across our connected enterprise sources, retrieved the evidence, and shows exactly how the answer was constructed."

That is the core POC story.

One architectural/UI principle I'd keep throughout

Don't make the UI look like:

Database → Chatbot

Make it look like:

                  ENTERPRISE INFORMATION
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
    PostgreSQL           MongoDB            Files
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
                    DATA DISCOVERY
                           ▼
                    DATA CATALOG
                           ▼
                       STRANDS
                           ▼
                  BUSINESS QUESTION
                           ▼
              CROSS-SOURCE INTELLIGENCE
                           ▼
             ANSWER + EVIDENCE + LINEAGE

That is the UI story I would build around. It directly demonstrates the central technical value of the POC rather than making the dashboard itself the product.