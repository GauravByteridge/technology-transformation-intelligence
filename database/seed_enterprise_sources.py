"""
Seed script for external enterprise data sources.

Creates and populates:
1. PostgreSQL database 'technology_transformation' with realistic project data
2. MongoDB database 'technology_transformation' with complementary qualitative data

These are the EXTERNAL sources that the platform discovers and queries.
They are NOT part of the application database (app_db).

Usage:
    python database/seed_enterprise_sources.py

Requirements:
    - PostgreSQL running on localhost:5432 with user 'postgres' password 'master'
    - MongoDB running on localhost:27017 (no auth for local dev)
"""

import asyncio
import sys
import json
from datetime import date, datetime, timedelta
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


# =============================================================================
# PostgreSQL Enterprise Data
# =============================================================================

POSTGRES_SCHEMA = """
-- Enterprise Technology Transformation Database
-- This is the EXTERNAL source that the platform connects to and discovers

DROP TABLE IF EXISTS project_milestones CASCADE;
DROP TABLE IF EXISTS jira_issues CASCADE;
DROP TABLE IF EXISTS resources CASCADE;
DROP TABLE IF EXISTS it_controls CASCADE;
DROP TABLE IF EXISTS remediation_items CASCADE;
DROP TABLE IF EXISTS audit_findings CASCADE;
DROP TABLE IF EXISTS project_risks_ext CASCADE;
DROP TABLE IF EXISTS project_progress CASCADE;
DROP TABLE IF EXISTS project_finance CASCADE;
DROP TABLE IF EXISTS projects CASCADE;

CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    project_code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    health VARCHAR(50) NOT NULL,
    start_date DATE,
    end_date DATE,
    manager VARCHAR(255),
    department VARCHAR(100),
    description TEXT
);

CREATE TABLE project_finance (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    budget NUMERIC(15,2) NOT NULL,
    actual_cost NUMERIC(15,2) NOT NULL,
    forecast_cost NUMERIC(15,2),
    variance NUMERIC(15,2),
    variance_percentage NUMERIC(5,2),
    as_of_date DATE NOT NULL
);

CREATE TABLE project_progress (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    planned_percent NUMERIC(5,2) NOT NULL,
    actual_percent NUMERIC(5,2) NOT NULL,
    status_date DATE NOT NULL
);

CREATE TABLE project_risks_ext (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    risk_id VARCHAR(20) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    category VARCHAR(100),
    description TEXT,
    owner VARCHAR(255),
    identified_date DATE,
    due_date DATE
);

CREATE TABLE audit_findings (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    finding_id VARCHAR(20) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    description TEXT,
    due_date DATE,
    auditor VARCHAR(255)
);

CREATE TABLE remediation_items (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    finding_id VARCHAR(20),
    owner VARCHAR(255),
    status VARCHAR(20) NOT NULL,
    description TEXT,
    due_date DATE
);

CREATE TABLE it_controls (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    control_id VARCHAR(20) NOT NULL,
    control_name VARCHAR(255) NOT NULL,
    compliance_status VARCHAR(50) NOT NULL,
    last_tested DATE
);

CREATE TABLE resources (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    employee_name VARCHAR(255),
    role VARCHAR(100),
    allocation_percent NUMERIC(5,2),
    utilization_percent NUMERIC(5,2)
);

CREATE TABLE jira_issues (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    issue_key VARCHAR(20) NOT NULL,
    summary TEXT NOT NULL,
    status VARCHAR(50) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    assignee VARCHAR(255),
    story_points INTEGER,
    due_date DATE
);

CREATE TABLE project_milestones (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    name VARCHAR(255) NOT NULL,
    planned_date DATE,
    actual_date DATE,
    status VARCHAR(50) NOT NULL
);

-- Indexes for common lookups
CREATE INDEX idx_finance_project ON project_finance(project_id);
CREATE INDEX idx_progress_project ON project_progress(project_id);
CREATE INDEX idx_risks_project ON project_risks_ext(project_id);
CREATE INDEX idx_audit_project ON audit_findings(project_id);
CREATE INDEX idx_resources_project ON resources(project_id);
CREATE INDEX idx_jira_project ON jira_issues(project_id);
CREATE INDEX idx_milestones_project ON project_milestones(project_id);
CREATE INDEX idx_projects_code ON projects(project_code);
"""

POSTGRES_SEED = """
-- Projects
INSERT INTO projects (project_code, name, status, health, start_date, end_date, manager, department, description) VALUES
('ALPHA', 'Project Alpha', 'Active', 'At Risk', '2025-01-15', '2026-06-30', 'Sarah Chen', 'Digital Transformation', 'Core banking platform modernization'),
('BETA', 'Project Beta', 'Active', 'On Track', '2025-03-01', '2026-03-31', 'James Wilson', 'Cloud Infrastructure', 'Cloud migration and infrastructure modernization'),
('GAMMA', 'Project Gamma', 'Active', 'Attention', '2025-06-01', '2026-09-30', 'Maria Rodriguez', 'Data Analytics', 'Enterprise data platform and analytics suite'),
('DELTA', 'Project Delta', 'Active', 'On Track', '2025-04-15', '2026-04-30', 'David Kim', 'Cybersecurity', 'Zero-trust security architecture implementation'),
('EPSILON', 'Project Epsilon', 'Planning', 'On Track', '2026-01-01', '2027-01-31', 'Lisa Park', 'AI/ML', 'AI-powered customer service platform');

-- Finance
INSERT INTO project_finance (project_id, budget, actual_cost, forecast_cost, variance, variance_percentage, as_of_date) VALUES
(1, 1000000, 1140000, 1200000, -140000, -14.0, '2026-08-01'),
(2, 800000, 680000, 790000, 120000, 15.0, '2026-08-01'),
(3, 1200000, 900000, 1250000, 300000, 25.0, '2026-08-01'),
(4, 600000, 450000, 580000, 150000, 25.0, '2026-08-01'),
(5, 500000, 50000, 500000, 450000, 90.0, '2026-08-01');

-- Progress
INSERT INTO project_progress (project_id, planned_percent, actual_percent, status_date) VALUES
(1, 85.0, 72.0, '2026-08-01'),
(2, 65.0, 68.0, '2026-08-01'),
(3, 45.0, 40.0, '2026-08-01'),
(4, 55.0, 58.0, '2026-08-01'),
(5, 5.0, 5.0, '2026-08-01');

-- Risks (in external PostgreSQL for structured risk data)
INSERT INTO project_risks_ext (project_id, risk_id, severity, status, category, description, owner, identified_date, due_date) VALUES
(1, 'R-001', 'HIGH', 'OPEN', 'Schedule', 'UAT delay causing timeline pressure', 'Sarah Chen', '2026-05-15', '2026-09-01'),
(1, 'R-002', 'HIGH', 'OPEN', 'Resource', 'Key developer leaving in Q3', 'HR Team', '2026-06-01', '2026-08-15'),
(1, 'R-003', 'MEDIUM', 'OPEN', 'Budget', 'Infrastructure costs exceeding estimates', 'Finance Team', '2026-04-20', '2026-10-01'),
(1, 'R-004', 'HIGH', 'OPEN', 'Technical', 'Legacy system integration complexity', 'Tech Lead', '2026-03-10', '2026-08-30'),
(2, 'R-005', 'LOW', 'MITIGATED', 'Technical', 'Cloud vendor SLA concerns', 'James Wilson', '2025-08-01', '2026-01-15'),
(3, 'R-006', 'MEDIUM', 'OPEN', 'Data', 'Data quality issues in source systems', 'Data Team', '2026-02-15', '2026-10-30'),
(3, 'R-007', 'HIGH', 'OPEN', 'Resource', 'Data engineer shortage', 'Maria Rodriguez', '2026-07-01', '2026-09-15');

-- Audit Findings
INSERT INTO audit_findings (project_id, finding_id, severity, status, description, due_date, auditor) VALUES
(1, 'AF-001', 'Critical', 'Open', 'Insufficient change management controls', '2026-07-15', 'Internal Audit'),
(1, 'AF-002', 'High', 'Open', 'Inadequate disaster recovery testing', '2026-08-30', 'Internal Audit'),
(1, 'AF-003', 'Medium', 'In Progress', 'Incomplete access control documentation', '2026-09-15', 'External Auditor'),
(2, 'AF-004', 'Low', 'Closed', 'Minor logging gap in CI/CD pipeline', '2026-05-01', 'Internal Audit'),
(3, 'AF-005', 'High', 'Open', 'Data retention policy non-compliance', '2026-08-15', 'Compliance Team');

-- Remediation Items
INSERT INTO remediation_items (project_id, finding_id, owner, status, description, due_date) VALUES
(1, 'AF-001', 'Sarah Chen', 'In Progress', 'Implement change advisory board process', '2026-08-15'),
(1, 'AF-002', 'Ops Team', 'Open', 'Schedule quarterly DR tests', '2026-09-01'),
(1, 'AF-003', 'Security Team', 'In Progress', 'Complete RBAC documentation', '2026-09-15'),
(3, 'AF-005', 'Data Team', 'Open', 'Implement automated data retention enforcement', '2026-09-30');

-- IT Controls
INSERT INTO it_controls (project_id, control_id, control_name, compliance_status, last_tested) VALUES
(1, 'CTRL-001', 'Access Control', 'Partial', '2026-06-15'),
(1, 'CTRL-002', 'Change Management', 'Non-Compliant', '2026-07-01'),
(1, 'CTRL-003', 'Data Encryption', 'Compliant', '2026-07-20'),
(1, 'CTRL-004', 'Backup & Recovery', 'Partial', '2026-06-30'),
(2, 'CTRL-005', 'Access Control', 'Compliant', '2026-07-15'),
(2, 'CTRL-006', 'Network Security', 'Compliant', '2026-07-20'),
(4, 'CTRL-007', 'Zero Trust Controls', 'Compliant', '2026-08-01'),
(4, 'CTRL-008', 'Endpoint Protection', 'Compliant', '2026-08-01');

-- Resources
INSERT INTO resources (project_id, employee_name, role, allocation_percent, utilization_percent) VALUES
(1, 'Sarah Chen', 'Project Manager', 100, 95),
(1, 'Alex Thompson', 'Lead Developer', 100, 110),
(1, 'Priya Patel', 'Senior Developer', 80, 90),
(1, 'Mike Johnson', 'QA Lead', 60, 75),
(1, 'Emma Davis', 'Business Analyst', 50, 85),
(2, 'James Wilson', 'Project Manager', 100, 80),
(2, 'Tom Clark', 'Cloud Architect', 100, 85),
(2, 'Anna Lee', 'DevOps Engineer', 80, 70),
(3, 'Maria Rodriguez', 'Project Manager', 100, 90),
(3, 'Carlos Mendez', 'Data Engineer', 100, 95),
(4, 'David Kim', 'Security Architect', 100, 75);

-- JIRA Issues
INSERT INTO jira_issues (project_id, issue_key, summary, status, priority, assignee, story_points, due_date) VALUES
(1, 'ALPHA-101', 'Complete UAT test cases for payment module', 'In Progress', 'High', 'Mike Johnson', 8, '2026-08-20'),
(1, 'ALPHA-102', 'Fix critical performance regression in API gateway', 'Open', 'Critical', 'Alex Thompson', 13, '2026-08-15'),
(1, 'ALPHA-103', 'Implement retry logic for transaction processing', 'Open', 'High', 'Priya Patel', 5, '2026-08-25'),
(1, 'ALPHA-104', 'Update security certificates for production', 'Blocked', 'High', 'Alex Thompson', 3, '2026-08-10'),
(1, 'ALPHA-105', 'Database migration script for customer accounts', 'Done', 'Medium', 'Priya Patel', 8, '2026-07-30'),
(2, 'BETA-201', 'Provision Kubernetes clusters for staging', 'Done', 'High', 'Tom Clark', 13, '2026-07-15'),
(2, 'BETA-202', 'Configure auto-scaling policies', 'In Progress', 'Medium', 'Anna Lee', 5, '2026-08-30'),
(3, 'GAMMA-301', 'Build ETL pipeline for financial data', 'In Progress', 'High', 'Carlos Mendez', 13, '2026-09-01'),
(3, 'GAMMA-302', 'Implement data quality validation rules', 'Open', 'Medium', 'Carlos Mendez', 8, '2026-09-15');

-- Milestones
INSERT INTO project_milestones (project_id, name, planned_date, actual_date, status) VALUES
(1, 'Requirements Complete', '2025-04-30', '2025-05-15', 'Completed'),
(1, 'Design Approved', '2025-07-31', '2025-08-20', 'Completed'),
(1, 'Development Complete', '2026-03-31', '2026-05-10', 'Completed'),
(1, 'UAT Complete', '2026-06-30', NULL, 'Delayed'),
(1, 'Go Live', '2026-08-31', NULL, 'At Risk'),
(2, 'Architecture Approved', '2025-06-30', '2025-06-28', 'Completed'),
(2, 'Migration Phase 1', '2026-01-31', '2026-01-25', 'Completed'),
(2, 'Migration Phase 2', '2026-06-30', NULL, 'In Progress'),
(3, 'Data Model Finalized', '2025-09-30', '2025-10-15', 'Completed'),
(3, 'MVP Launch', '2026-06-30', NULL, 'In Progress');
"""


# =============================================================================
# MongoDB Enterprise Data
# =============================================================================

MONGODB_DATA = {
    "project_risks": [
        {"project_id": "ALPHA", "severity": "HIGH", "status": "OPEN", "category": "Schedule",
         "description": "UAT completion has slipped by 3 weeks due to environment instability and resource constraints. The testing team reports only 60% of critical test cases have been executed.",
         "identified_date": "2026-05-15", "owner": "Sarah Chen", "impact": "Timeline extension required, potential budget overrun from extended resource allocation"},
        {"project_id": "ALPHA", "severity": "HIGH", "status": "OPEN", "category": "Resource",
         "description": "Lead developer Alex Thompson has accepted an offer elsewhere. Knowledge transfer window is 4 weeks. No identified replacement with equivalent domain expertise.",
         "identified_date": "2026-06-01", "owner": "HR Team", "impact": "Critical path activities may stall, estimated 6-8 week productivity loss during transition"},
        {"project_id": "ALPHA", "severity": "MEDIUM", "status": "OPEN", "category": "Budget",
         "description": "Infrastructure costs for cloud hosting exceeded initial estimates by 23%. The architecture requires more compute resources than modeled.",
         "identified_date": "2026-04-20", "owner": "Finance Team", "impact": "Budget variance now at 14%, forecast indicates potential 20% overrun by project end"},
        {"project_id": "GAMMA", "severity": "HIGH", "status": "OPEN", "category": "Data Quality",
         "description": "Source system data quality is significantly worse than assumed during planning. 34% of financial records have inconsistent formatting requiring manual intervention.",
         "identified_date": "2026-07-01", "owner": "Data Team", "impact": "ETL pipeline development extended by 8 weeks, additional data cleansing resources needed"},
        {"project_id": "BETA", "severity": "LOW", "status": "MITIGATED", "category": "Vendor",
         "description": "Cloud vendor SLA renegotiation completed. New terms include 99.99% uptime guarantee with financial penalties.",
         "identified_date": "2025-08-01", "owner": "James Wilson", "impact": "Minimal - risk fully mitigated through contract terms"},
    ],
    "project_updates": [
        {"project_id": "ALPHA", "date": "2026-08-20", "author": "Sarah Chen", "type": "Weekly Status",
         "summary": "Project remains At Risk. UAT environment stabilized but testing backlog is significant. Budget pressure continues due to infrastructure costs.",
         "concerns": ["UAT timeline", "Budget overrun trajectory", "Key resource departure"],
         "decisions": ["Approved overtime budget for testing team", "Initiated recruitment for replacement developer"],
         "next_steps": ["Complete critical path UAT cases by Aug 30", "Finalize knowledge transfer plan"]},
        {"project_id": "ALPHA", "date": "2026-08-13", "author": "Sarah Chen", "type": "Weekly Status",
         "summary": "Environment issues resolved. Testing resumed but behind schedule. Steering committee raised concerns about go-live date.",
         "concerns": ["Go-live date at risk", "Steering committee confidence"],
         "decisions": ["Escalated to program director", "Requested additional QA resources"],
         "next_steps": ["Present recovery plan to steering committee", "Assess parallel testing options"]},
        {"project_id": "BETA", "date": "2026-08-19", "author": "James Wilson", "type": "Weekly Status",
         "summary": "Migration Phase 2 progressing well. All staging environments operational. Performance testing shows 15% improvement over legacy.",
         "concerns": [],
         "decisions": ["Approved production cutover plan for September"],
         "next_steps": ["Complete load testing", "Schedule production deployment window"]},
        {"project_id": "GAMMA", "date": "2026-08-18", "author": "Maria Rodriguez", "type": "Weekly Status",
         "summary": "Data quality issues continue to impact ETL development. Revised timeline submitted for approval. Additional data engineer hired.",
         "concerns": ["Source data quality", "Timeline extension needed", "Stakeholder expectations"],
         "decisions": ["Approved revised timeline", "Onboarding new data engineer"],
         "next_steps": ["Complete data profiling report", "Present revised milestones to sponsors"]},
    ],
    "project_meeting_observations": [
        {"project_id": "ALPHA", "date": "2026-08-15", "meeting_type": "Steering Committee",
         "attendees": ["CTO", "Program Director", "Sarah Chen", "Finance Director"],
         "key_observations": [
             "CTO expressed concern about go-live date confidence",
             "Finance Director highlighted 14% budget overrun trend",
             "Program Director requested weekly risk escalation reports",
             "Sarah Chen presented mitigation options including parallel testing streams"
         ],
         "action_items": ["Weekly executive risk report starting Aug 22", "Contingency budget request of $150K"],
         "sentiment": "Concerned but supportive"},
        {"project_id": "ALPHA", "date": "2026-08-08", "meeting_type": "Technical Review",
         "attendees": ["Alex Thompson", "Tech Lead", "Architect", "QA Lead"],
         "key_observations": [
             "Performance regression identified in payment API (response time 3x baseline)",
             "Root cause: database connection pooling misconfiguration",
             "Fix estimated at 2 days but requires regression testing",
             "Legacy system integration more complex than documented"
         ],
         "action_items": ["Fix connection pooling by Aug 10", "Update integration documentation"],
         "sentiment": "Technical team confident in fix but timeline tight"},
        {"project_id": "GAMMA", "date": "2026-08-12", "meeting_type": "Data Quality Review",
         "attendees": ["Maria Rodriguez", "Data Engineer", "Source System Owner", "Business Analyst"],
         "key_observations": [
             "34% of financial records have inconsistent date formats",
             "Source system has no data validation at entry point",
             "Historical data correction not feasible - need transformation rules",
             "Business rules for edge cases not documented"
         ],
         "action_items": ["Document transformation rules by Aug 20", "Build validation framework"],
         "sentiment": "Challenging but manageable with revised timeline"},
    ],
    "project_health_signals": [
        {"project_id": "ALPHA", "date": "2026-08-20", "signal_type": "velocity_decline",
         "description": "Sprint velocity dropped 30% over last 3 sprints (from 42 to 29 story points)",
         "severity": "HIGH", "source": "JIRA analytics"},
        {"project_id": "ALPHA", "date": "2026-08-18", "signal_type": "budget_trend",
         "description": "Monthly burn rate exceeds plan by $45K/month for last 3 months",
         "severity": "MEDIUM", "source": "Financial system"},
        {"project_id": "ALPHA", "date": "2026-08-15", "signal_type": "risk_escalation",
         "description": "3 new high-severity risks identified in August alone",
         "severity": "HIGH", "source": "Risk register"},
        {"project_id": "GAMMA", "date": "2026-08-16", "signal_type": "scope_change",
         "description": "Data quality remediation added as new workstream, impacting timeline",
         "severity": "MEDIUM", "source": "Change control board"},
        {"project_id": "BETA", "date": "2026-08-19", "signal_type": "positive_trend",
         "description": "All migration milestones on or ahead of schedule for 6 consecutive sprints",
         "severity": "LOW", "source": "Project tracking"},
    ],
}


async def seed_postgres():
    """Create and populate the external PostgreSQL enterprise database."""
    import asyncpg

    print("=" * 60)
    print("  Seeding External PostgreSQL: technology_transformation")
    print("=" * 60)

    # Connect as superuser to create the database
    conn = await asyncpg.connect(
        host="localhost", port=5432,
        user="postgres", password="master",
        database="postgres"
    )

    # Create database if not exists
    exists = await conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = 'technology_transformation'"
    )
    if not exists:
        await conn.execute("CREATE DATABASE technology_transformation")
        print("  ✓ Database 'technology_transformation' created")
    else:
        print("  • Database 'technology_transformation' already exists")
    await conn.close()

    # Connect to the new database and create schema + seed data
    conn = await asyncpg.connect(
        host="localhost", port=5432,
        user="postgres", password="master",
        database="technology_transformation"
    )

    # Create schema
    await conn.execute(POSTGRES_SCHEMA)
    print("  ✓ Schema created (10 tables)")

    # Seed data
    await conn.execute(POSTGRES_SEED)
    print("  ✓ Seed data inserted")

    # Verify
    count = await conn.fetchval("SELECT count(*) FROM projects")
    print(f"  ✓ Projects: {count}")
    count = await conn.fetchval("SELECT count(*) FROM project_finance")
    print(f"  ✓ Finance records: {count}")
    count = await conn.fetchval("SELECT count(*) FROM jira_issues")
    print(f"  ✓ JIRA issues: {count}")
    count = await conn.fetchval("SELECT count(*) FROM project_risks_ext")
    print(f"  ✓ Risks: {count}")

    await conn.close()
    print("  ✓ PostgreSQL seeding complete\n")


async def seed_mongodb():
    """Create and populate the external MongoDB enterprise database."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except ImportError:
        print("  ⚠ Motor not installed. Skipping MongoDB seeding.")
        print("    Install with: pip install motor")
        return

    print("=" * 60)
    print("  Seeding External MongoDB: technology_transformation")
    print("=" * 60)

    try:
        client = AsyncIOMotorClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
        # Test connection
        await client.admin.command("ping")
    except Exception as e:
        print(f"  ⚠ MongoDB not available: {e}")
        print("    Start MongoDB with: mongod --dbpath /data/db")
        print("    Or: docker run -d -p 27017:27017 mongo:7")
        return

    db = client["technology_transformation"]

    # Drop existing collections
    for collection_name in MONGODB_DATA.keys():
        await db.drop_collection(collection_name)

    # Insert data
    for collection_name, documents in MONGODB_DATA.items():
        if documents:
            result = await db[collection_name].insert_many(documents)
            print(f"  ✓ {collection_name}: {len(result.inserted_ids)} documents")

    # Verify
    collections = await db.list_collection_names()
    print(f"  ✓ Collections created: {len(collections)}")

    client.close()
    print("  ✓ MongoDB seeding complete\n")


async def main():
    """Run all seed operations."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    print("\n" + "=" * 60)
    print("  Enterprise Data Source Initialization")
    print("=" * 60 + "\n")

    await seed_postgres()
    await seed_mongodb()

    print("=" * 60)
    print("  Done! External databases are ready.")
    print("")
    print("  Next steps:")
    print("  1. Start the TTI platform")
    print("  2. Go to Data Sources → Add Source")
    print("  3. Connect PostgreSQL:")
    print("     Host: localhost, Port: 5432")
    print("     Database: technology_transformation")
    print("     User: postgres, Password: master")
    print("  4. Connect MongoDB:")
    print("     Host: localhost, Port: 27017")
    print("     Database: technology_transformation")
    print("  5. Run Discovery on both sources")
    print("  6. Ask AI: 'Why is Project Alpha at risk?'")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
