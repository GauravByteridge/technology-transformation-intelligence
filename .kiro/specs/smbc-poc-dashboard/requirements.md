# Requirements Document

## Introduction

This document defines the requirements for the SMBC POC Dashboard — an AI-powered PMO (Project Management Office) dashboard for SMBC's technology transformation projects. The key differentiator is Cross-Source Intelligence: AI brings together Jira, emails/communications, and project documents to identify risks, explain issues, and recommend actions. The POC tracks 4 banking-specific projects across 4 screens, replacing the existing generic project data with realistic SMBC banking-industry scenarios.

## Glossary

- **Dashboard**: The AI PMO Overview web application providing portfolio-level visibility into project health
- **Project**: A technology transformation initiative tracked by the PMO (one of 4 banking-specific projects)
- **Cross_Source_Intelligence_Engine**: The AI component that correlates data from Jira, email/communications, and project documents to produce unified insights
- **AI_Agent**: The Strands AI Agent backed by Groq LLM that generates assessments, summaries, and answers to predefined questions
- **PMO**: Project Management Office — the organizational function responsible for overseeing project delivery
- **Health_Status**: A Red/Amber/Green indicator representing a project's overall condition
- **Risk**: A potential issue that may impact project delivery (schedule, budget, or quality)
- **Action**: A tracked task assigned to an owner with a due date and status
- **Executive_Summary**: An AI-generated narrative covering portfolio health, risks, budget, schedule, and recommended actions
- **Source**: A data origin (Jira, Email, or Document) from which project intelligence is gathered
- **KPI_Card**: A top-level numeric indicator displayed on the overview screen (e.g., Total Projects, Projects at Risk)
- **Project_360**: The detailed single-project view showing health, risks, budget, schedule, and AI assessment

## Requirements

### Requirement 1: Portfolio Overview Display

**User Story:** As a PMO manager, I want to see a high-level overview of all projects with key indicators, so that I can quickly assess portfolio health.

#### Acceptance Criteria

1. WHEN a user navigates to the AI PMO Overview screen, THE Dashboard SHALL display KPI_Cards showing: Total Projects (4), Projects at Risk, High-Severity Risks count, Overdue Actions count, and Projects with Budget Variance count
2. WHEN the AI PMO Overview screen loads, THE Dashboard SHALL display a project health table showing each Project with its name, overall Health_Status, schedule status, budget status, and open risk count
3. WHEN a Project has Health_Status of Red or Amber, THE Dashboard SHALL display that Project in the PMO Attention Required section with a summary of key issues and an AI assessment label

### Requirement 2: Project Data Seeding

**User Story:** As a developer, I want the system seeded with 4 realistic SMBC banking projects, so that the POC demonstrates credible domain-specific scenarios.

#### Acceptance Criteria

1. THE Dashboard SHALL contain exactly 4 projects: Global Transaction Banking Platform Modernization (Red), Capital Markets Technology Transformation (Amber), Global Digital Platform Enhancement (Green), and Regulatory & Risk Reporting Transformation (Amber)
2. WHEN the system initializes, THE Dashboard SHALL seed each project with realistic banking-industry data including risks, issues, actions, budget figures, schedule milestones, and Jira-like issue references
3. WHEN seeding the Global Transaction Banking Platform Modernization project, THE Dashboard SHALL include data representing: UAT delays, critical defects, integration issues, and budget variance of 8% over plan
4. WHEN seeding the Capital Markets Technology Transformation project, THE Dashboard SHALL include data representing: pending requirements, testing delays, and market-data feed dependency
5. WHEN seeding the Global Digital Platform Enhancement project, THE Dashboard SHALL include data representing: minor risks and normal development activities with Green overall status
6. WHEN seeding the Regulatory & Risk Reporting Transformation project, THE Dashboard SHALL include data representing: data-quality gaps, reporting requirement changes, and testing delays

### Requirement 3: Project 360 Detail View

**User Story:** As a PMO manager, I want to drill into a single project's details, so that I can understand its health, risks, and issues in depth.

#### Acceptance Criteria

1. WHEN a user selects a project from the overview, THE Dashboard SHALL navigate to the Project_360 screen showing: overall Health_Status, budget vs actual spend, schedule progress, open risk count, critical issue count, and overdue action count
2. WHEN displaying the Project_360 screen, THE Dashboard SHALL list the top 3-4 Key Risks for the selected project with severity and description
3. WHEN the Project_360 screen loads, THE AI_Agent SHALL generate a project summary assessment explaining the current status, key concerns, and contributing factors

### Requirement 4: Cross-Source Intelligence

**User Story:** As a PMO manager, I want the system to correlate information from Jira, emails, and documents, so that I can see risks that span multiple data sources.

#### Acceptance Criteria

1. WHEN displaying the Cross-Source Intelligence screen for a project, THE Cross_Source_Intelligence_Engine SHALL retrieve and correlate data from Jira (defects, stories, project status), Email/Communications (risks, escalations, action items), and Documents (project reviews, plans, reports)
2. WHEN data from multiple sources indicates a converging risk, THE Cross_Source_Intelligence_Engine SHALL generate an AI insight that explains the correlation and identifies the risk with supporting evidence from each Source
3. WHEN displaying cross-source insights, THE Dashboard SHALL show each insight with clearly labeled contributing sources (Jira, Email, Document) and the specific data point from each source
4. WHEN a cross-source insight is generated, THE AI_Agent SHALL assign a priority level and describe the risk trajectory (emerging, escalating, or stable)

### Requirement 5: Executive Summary Generation

**User Story:** As a PMO executive, I want to generate an AI-written executive summary, so that I can quickly communicate portfolio status to leadership.

#### Acceptance Criteria

1. WHEN a user clicks the Generate Executive Summary button, THE AI_Agent SHALL produce a narrative covering: overall portfolio health, projects requiring attention, top risks, budget concerns, schedule concerns, overdue actions, and recommended PMO actions
2. WHEN generating the Executive_Summary, THE AI_Agent SHALL base the narrative on current data from all projects including cross-source intelligence findings
3. WHEN the Executive_Summary is generated, THE Dashboard SHALL display it in a readable format suitable for leadership communication

### Requirement 6: Unattended Actions Tracking

**User Story:** As a PMO manager, I want to see all overdue and unresolved actions across projects, so that I can intervene on items that need attention.

#### Acceptance Criteria

1. WHEN displaying unattended actions, THE Dashboard SHALL show a list with: action description, owner, due date, status, and source (which project or data source it originated from)
2. WHEN an action has exceeded its due date, THE Dashboard SHALL mark that action as Overdue with visual differentiation
3. WHEN an action has appeared in multiple project updates without resolution, THE AI_Agent SHALL flag it as a recurring unresolved item

### Requirement 7: AI Query Interface

**User Story:** As a PMO manager, I want to ask predefined AI questions about projects, so that I can get instant intelligent answers about project status and risks.

#### Acceptance Criteria

1. WHEN a user selects a predefined question, THE AI_Agent SHALL generate a contextual answer based on the selected project's data from all available sources
2. THE Dashboard SHALL provide the following predefined questions: "Why is this project at risk?", "What are the top unresolved issues?", "What changed this week?", "Which actions are overdue?", "What should the PMO focus on?", "Are there risks mentioned in emails that are not in Jira?", and "Which projects require PMO intervention?"
3. WHEN the AI_Agent generates an answer, THE Dashboard SHALL display it with references to the data sources that informed the response

### Requirement 8: Status Visualization

**User Story:** As a PMO manager, I want clear visual status indicators, so that I can instantly recognize project health without reading detailed text.

#### Acceptance Criteria

1. THE Dashboard SHALL use a three-tier status system: Red (critical issues requiring immediate attention), Amber (concerns that need monitoring), and Green (on track with minor or no issues)
2. WHEN displaying Health_Status, THE Dashboard SHALL use color-coded badges (Red, Amber, Green) consistently across all screens including overview cards, project tables, and detail views
3. WHEN a project's status changes between assessments, THE Dashboard SHALL reflect the updated status on all screens where the project appears
