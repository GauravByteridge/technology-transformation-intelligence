"""
Seed script for SMBC POC — 4 banking transformation projects.

Replaces existing demo projects with:
1. GTB  — Global Transaction Banking Platform Modernization (🔴 Red)
2. CMTT — Capital Markets Technology Transformation (🟠 Amber)
3. GDP  — Global Digital Platform Enhancement (🟢 Green)
4. RRRT — Regulatory & Risk Reporting Transformation (🟠 Amber)

Seeds data in:
- app_db: projects table (with project_code, status indicators)
- External PostgreSQL: technology_transformation DB (finance, risks, progress, etc.)
- External MongoDB: qualitative data (updates, meetings, health signals)

Usage:
    python database/seed_smbc_projects.py
"""

import asyncio
import sys
import json
from datetime import date, datetime, timezone
from uuid import uuid4
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

# =============================================================================
# Fixed UUIDs for SMBC projects (deterministic)
# =============================================================================

USER_ADMIN_ID = "a1b2c3d4-0001-4000-8000-000000000001"

PROJECT_GTB_ID = "a1b2c3d4-0002-4000-8000-000000000001"   # Reuses slot 1
PROJECT_CMTT_ID = "a1b2c3d4-0002-4000-8000-000000000002"  # Reuses slot 2
PROJECT_GDP_ID = "a1b2c3d4-0002-4000-8000-000000000003"   # Reuses slot 3
PROJECT_RRRT_ID = "a1b2c3d4-0002-4000-8000-000000000004"  # Reuses slot 4


# =============================================================================
# External PostgreSQL — technology_transformation DB
# =============================================================================

POSTGRES_SCHEMA = """
-- SMBC POC Enterprise Database
DROP TABLE IF EXISTS project_milestones CASCADE;
DROP TABLE IF EXISTS jira_issues CASCADE;
DROP TABLE IF EXISTS resources CASCADE;
DROP TABLE IF EXISTS it_controls CASCADE;
DROP TABLE IF EXISTS remediation_items CASCADE;
DROP TABLE IF EXISTS audit_findings CASCADE;
DROP TABLE IF EXISTS project_risks_ext CASCADE;
DROP TABLE IF EXISTS project_progress CASCADE;
DROP TABLE IF EXISTS project_finance CASCADE;
DROP TABLE IF EXISTS unattended_actions CASCADE;
DROP TABLE IF EXISTS projects CASCADE;

CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    project_code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    health VARCHAR(50) NOT NULL,
    schedule_status VARCHAR(50) NOT NULL,
    budget_status VARCHAR(50) NOT NULL,
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
    status_date DATE NOT NULL,
    notes TEXT
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
    due_date DATE,
    impact TEXT
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

CREATE TABLE unattended_actions (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    action TEXT NOT NULL,
    owner VARCHAR(255),
    due_date DATE,
    status VARCHAR(50) NOT NULL,
    source VARCHAR(100),
    first_raised DATE,
    times_repeated INTEGER DEFAULT 1
);

CREATE INDEX idx_finance_project ON project_finance(project_id);
CREATE INDEX idx_progress_project ON project_progress(project_id);
CREATE INDEX idx_risks_project ON project_risks_ext(project_id);
CREATE INDEX idx_audit_project ON audit_findings(project_id);
CREATE INDEX idx_resources_project ON resources(project_id);
CREATE INDEX idx_jira_project ON jira_issues(project_id);
CREATE INDEX idx_milestones_project ON project_milestones(project_id);
CREATE INDEX idx_actions_project ON unattended_actions(project_id);
"""

POSTGRES_SEED = """
-- 4 SMBC POC Projects
INSERT INTO projects (project_code, name, status, health, schedule_status, budget_status, start_date, end_date, manager, department, description) VALUES
('GTB', 'Global Transaction Banking Platform Modernization', 'Active', 'Red', 'Delayed', 'Over Budget', '2025-01-15', '2026-09-30', 'Takeshi Yamamoto', 'Transaction Banking', 'End-to-end modernization of the global transaction banking platform including payments, cash management and trade finance systems'),
('CMTT', 'Capital Markets Technology Transformation', 'Active', 'Amber', 'At Risk', 'On Budget', '2025-03-01', '2026-12-31', 'Rachel Morgan', 'Capital Markets', 'Technology transformation of trading, risk and post-trade systems to support regulatory compliance and market competitiveness'),
('GDP', 'Global Digital Platform Enhancement', 'Active', 'Green', 'On Track', 'On Budget', '2025-06-01', '2026-06-30', 'Kenji Tanaka', 'Digital Banking', 'Enhancement of digital banking platform covering mobile, internet banking and API gateway modernization'),
('RRRT', 'Regulatory & Risk Reporting Transformation', 'Active', 'Amber', 'Delayed', 'On Budget', '2025-04-01', '2026-10-31', 'Sarah Mitchell', 'Risk & Compliance', 'Transformation of regulatory reporting infrastructure to meet Basel IV, FRTB and ESG reporting requirements');

-- Finance Data
INSERT INTO project_finance (project_id, budget, actual_cost, forecast_cost, variance, variance_percentage, as_of_date) VALUES
(1, 45000000, 38700000, 48600000, -3600000, -8.0, '2026-08-20'),
(2, 32000000, 22400000, 33500000, -1500000, -4.7, '2026-08-20'),
(3, 18000000, 12600000, 17800000, 200000, 1.1, '2026-08-20'),
(4, 25000000, 16250000, 25800000, -800000, -3.2, '2026-08-20');

-- Progress Data (multiple snapshots for burndown)
INSERT INTO project_progress (project_id, planned_percent, actual_percent, status_date, notes) VALUES
(1, 40, 35, '2026-03-01', 'Requirements phase extending'),
(1, 55, 47, '2026-05-01', 'Development delays from integration issues'),
(1, 70, 58, '2026-07-01', 'UAT started late'),
(1, 80, 65, '2026-08-01', 'Critical defects blocking UAT'),
(1, 85, 68, '2026-08-20', 'UAT delayed by 2 weeks'),
(2, 30, 28, '2026-03-01', 'Requirements pending from business'),
(2, 45, 40, '2026-05-01', 'Market data dependency causing delays'),
(2, 55, 52, '2026-07-01', 'Testing starting'),
(2, 65, 60, '2026-08-01', 'Testing delays emerging'),
(2, 70, 63, '2026-08-20', 'Requirements gap identified'),
(3, 25, 26, '2026-03-01', 'Ahead of schedule'),
(3, 40, 42, '2026-05-01', 'Good progress'),
(3, 55, 57, '2026-07-01', 'Minor risk but manageable'),
(3, 70, 72, '2026-08-01', 'On track'),
(3, 75, 76, '2026-08-20', 'Tracking well'),
(4, 30, 27, '2026-03-01', 'Data quality gaps emerging'),
(4, 45, 38, '2026-05-01', 'Reporting requirements changing'),
(4, 55, 48, '2026-07-01', 'Testing delays'),
(4, 65, 56, '2026-08-01', 'Regulatory changes impacting scope'),
(4, 70, 59, '2026-08-20', 'Testing delayed');

-- Risks
INSERT INTO project_risks_ext (project_id, risk_id, severity, status, category, description, owner, identified_date, due_date, impact) VALUES
(1, 'GTB-R01', 'Critical', 'Open', 'Schedule', 'UAT delayed by 2 weeks due to critical defects in payment processing module', 'Takeshi Yamamoto', '2026-07-15', '2026-09-01', 'Go-live date at risk'),
(1, 'GTB-R02', 'High', 'Open', 'Quality', '3 critical defects in SWIFT messaging integration remain unresolved', 'Dev Team', '2026-07-20', '2026-08-30', 'Payment processing reliability'),
(1, 'GTB-R03', 'High', 'Open', 'Budget', 'Budget 8% above plan due to extended testing and infrastructure costs', 'Finance', '2026-06-01', '2026-09-30', 'Additional funding required'),
(1, 'GTB-R04', 'Medium', 'Open', 'Integration', 'SWIFT gpi integration complexity higher than estimated', 'Tech Lead', '2026-05-10', '2026-09-15', 'Extended development cycle'),
(1, 'GTB-R05', 'High', 'Open', 'Resource', '2 senior developers leaving — knowledge transfer incomplete', 'HR', '2026-08-01', '2026-09-15', 'Critical path activities impacted'),
(2, 'CMTT-R01', 'High', 'Open', 'Requirements', 'Trading desk requirements still pending sign-off from 3 business units', 'Rachel Morgan', '2026-06-15', '2026-09-01', 'Development cannot proceed on key modules'),
(2, 'CMTT-R02', 'Medium', 'Open', 'Schedule', 'Performance testing delayed by 3 weeks due to market data feed setup', 'Test Manager', '2026-07-01', '2026-09-30', 'Timeline compression needed'),
(2, 'CMTT-R03', 'Medium', 'Open', 'Dependency', 'Market data vendor API changes require code refactoring', 'Tech Lead', '2026-07-20', '2026-10-15', 'Rework estimated at 4 weeks'),
(3, 'GDP-R01', 'Low', 'Mitigated', 'Technical', 'Mobile app performance on older devices', 'Kenji Tanaka', '2026-04-01', '2026-06-30', 'Minimal — workaround deployed'),
(3, 'GDP-R02', 'Low', 'Open', 'Security', 'API gateway rate limiting fine-tuning needed before peak load', 'Security Team', '2026-08-01', '2026-09-15', 'Low — scheduled for next sprint'),
(4, 'RRRT-R01', 'High', 'Open', 'Data', 'Data quality gaps in upstream risk systems affecting report accuracy', 'Data Team', '2026-05-01', '2026-09-30', 'Reporting accuracy below threshold'),
(4, 'RRRT-R02', 'High', 'Open', 'Regulatory', 'Basel IV reporting requirements changed — scope expansion needed', 'Sarah Mitchell', '2026-07-01', '2026-10-31', 'Additional 6 weeks of development'),
(4, 'RRRT-R03', 'Medium', 'Open', 'Schedule', 'Testing delayed due to unavailability of regulatory test scenarios', 'Test Lead', '2026-08-10', '2026-10-15', '3 week delay in test execution');

-- Audit Findings
INSERT INTO audit_findings (project_id, finding_id, severity, status, description, due_date, auditor) VALUES
(1, 'GTB-AF01', 'Critical', 'Open', 'Insufficient disaster recovery testing for payment systems', '2026-09-01', 'Internal Audit'),
(1, 'GTB-AF02', 'High', 'Open', 'Change management process not followed for 4 production deployments', '2026-08-30', 'Internal Audit'),
(1, 'GTB-AF03', 'High', 'In Progress', 'Incomplete access control documentation for SWIFT connectivity', '2026-09-15', 'External Auditor'),
(2, 'CMTT-AF01', 'Medium', 'Open', 'Trading system test coverage below 60% threshold', '2026-10-01', 'Internal Audit'),
(4, 'RRRT-AF01', 'High', 'Open', 'Regulatory data lineage not fully documented', '2026-09-30', 'Compliance'),
(4, 'RRRT-AF02', 'Medium', 'Open', 'Reconciliation gaps between source and reporting systems', '2026-10-15', 'Internal Audit');

-- Unattended Actions (key POC feature)
INSERT INTO unattended_actions (project_id, action, owner, due_date, status, source, first_raised, times_repeated) VALUES
(1, 'Resolve critical SWIFT API defect blocking UAT', 'Technology Team', '2026-08-15', 'Overdue', 'Jira', '2026-07-20', 4),
(1, 'Confirm revised UAT completion plan with business', 'Business Team', '2026-08-20', 'Overdue', 'Steering Committee', '2026-08-01', 3),
(1, 'Review and approve infrastructure cost overrun', 'Infrastructure Team', '2026-08-25', 'Open', 'Finance Review', '2026-08-10', 2),
(1, 'Complete knowledge transfer from departing developers', 'Tech Lead', '2026-09-01', 'Open', 'HR / Project Review', '2026-08-05', 2),
(1, 'Schedule disaster recovery test', 'Operations Team', '2026-08-30', 'Overdue', 'Audit Finding', '2026-07-01', 5),
(2, 'Obtain requirements sign-off from Fixed Income desk', 'Rachel Morgan', '2026-08-25', 'Overdue', 'Weekly Status', '2026-06-15', 8),
(2, 'Setup market data test feed for performance testing', 'Vendor Management', '2026-09-01', 'Open', 'Test Planning', '2026-07-15', 3),
(4, 'Provide updated Basel IV test scenarios', 'Regulatory Affairs', '2026-08-20', 'Overdue', 'Test Manager', '2026-07-20', 4),
(4, 'Fix upstream data quality issues in risk feeds', 'Source System Team', '2026-09-15', 'Open', 'Data Quality Review', '2026-06-01', 6),
(4, 'Document data lineage for all regulatory reports', 'Data Governance', '2026-09-30', 'Open', 'Audit Finding', '2026-07-15', 3);

-- IT Controls
INSERT INTO it_controls (project_id, control_id, control_name, compliance_status, last_tested) VALUES
(1, 'GTB-C01', 'Payment Processing Access Control', 'Partial', '2026-07-15'),
(1, 'GTB-C02', 'Change Management', 'Non-Compliant', '2026-08-01'),
(1, 'GTB-C03', 'SWIFT Message Encryption', 'Compliant', '2026-07-20'),
(1, 'GTB-C04', 'Disaster Recovery', 'Non-Compliant', '2026-06-30'),
(2, 'CMTT-C01', 'Trading System Access', 'Compliant', '2026-08-01'),
(2, 'CMTT-C02', 'Market Data Security', 'Compliant', '2026-07-15'),
(3, 'GDP-C01', 'API Gateway Security', 'Compliant', '2026-08-10'),
(3, 'GDP-C02', 'Customer Data Encryption', 'Compliant', '2026-08-10'),
(4, 'RRRT-C01', 'Regulatory Data Access', 'Partial', '2026-07-25'),
(4, 'RRRT-C02', 'Report Integrity Controls', 'Compliant', '2026-08-01');

-- Resources
INSERT INTO resources (project_id, employee_name, role, allocation_percent, utilization_percent) VALUES
(1, 'Takeshi Yamamoto', 'Program Manager', 100, 110),
(1, 'David Park', 'Lead Developer', 100, 120),
(1, 'Aisha Khan', 'Senior Developer', 100, 95),
(1, 'James Wright', 'QA Lead', 80, 100),
(1, 'Yuki Sato', 'Business Analyst', 60, 85),
(1, 'Chen Wei', 'Integration Specialist', 100, 105),
(2, 'Rachel Morgan', 'Program Manager', 100, 90),
(2, 'Marcus Cole', 'Solutions Architect', 100, 85),
(2, 'Priya Sharma', 'Senior Developer', 80, 75),
(3, 'Kenji Tanaka', 'Project Manager', 100, 80),
(3, 'Lisa Chen', 'Mobile Developer', 100, 85),
(3, 'Tom Anderson', 'API Engineer', 80, 70),
(4, 'Sarah Mitchell', 'Program Manager', 100, 95),
(4, 'Robert Kim', 'Data Engineer', 100, 100),
(4, 'Emma Garcia', 'Regulatory Analyst', 80, 90);

-- JIRA Issues
INSERT INTO jira_issues (project_id, issue_key, summary, status, priority, assignee, story_points, due_date) VALUES
(1, 'GTB-1001', 'Critical: SWIFT gpi message parsing failure in production path', 'Open', 'Critical', 'David Park', 13, '2026-08-25'),
(1, 'GTB-1002', 'UAT blocked: Payment reconciliation mismatch on cross-border txns', 'Open', 'Critical', 'Aisha Khan', 8, '2026-08-22'),
(1, 'GTB-1003', 'Performance degradation on batch payment processing (>3x baseline)', 'In Progress', 'Critical', 'Chen Wei', 8, '2026-08-28'),
(1, 'GTB-1004', 'Implement retry logic for failed SWIFT acknowledgements', 'Open', 'High', 'David Park', 5, '2026-09-01'),
(1, 'GTB-1005', 'Complete UAT test cases for cash management module', 'In Progress', 'High', 'James Wright', 13, '2026-09-05'),
(1, 'GTB-1006', 'Fix timezone handling in multi-currency settlement', 'Open', 'High', 'Aisha Khan', 5, '2026-08-30'),
(1, 'GTB-1007', 'Update DR runbook for new payment infrastructure', 'Blocked', 'High', 'Operations', 3, '2026-08-25'),
(2, 'CMTT-2001', 'Market data feed latency exceeds SLA (>500ms)', 'In Progress', 'High', 'Marcus Cole', 8, '2026-09-10'),
(2, 'CMTT-2002', 'Requirements: FX derivatives pricing model sign-off pending', 'Blocked', 'High', 'Rachel Morgan', 3, '2026-08-25'),
(2, 'CMTT-2003', 'Implement real-time position calculation engine', 'In Progress', 'Medium', 'Priya Sharma', 13, '2026-09-30'),
(2, 'CMTT-2004', 'Setup performance test environment for trading system', 'Open', 'Medium', 'Infra Team', 5, '2026-09-15'),
(3, 'GDP-3001', 'Mobile app: optimize load time for account overview (<2s)', 'Done', 'Medium', 'Lisa Chen', 5, '2026-08-15'),
(3, 'GDP-3002', 'API gateway: implement circuit breaker pattern', 'In Progress', 'Medium', 'Tom Anderson', 8, '2026-08-30'),
(3, 'GDP-3003', 'Push notification service integration', 'In Progress', 'Low', 'Lisa Chen', 5, '2026-09-10'),
(4, 'RRRT-4001', 'Basel IV: Capital adequacy report template incorrect', 'Open', 'High', 'Robert Kim', 8, '2026-09-15'),
(4, 'RRRT-4002', 'Data lineage mapping for FRTB reports incomplete', 'In Progress', 'High', 'Emma Garcia', 13, '2026-09-30'),
(4, 'RRRT-4003', 'Reconciliation between source and reporting aggregation layer', 'Open', 'Medium', 'Robert Kim', 8, '2026-10-01'),
(4, 'RRRT-4004', 'ESG reporting: carbon emissions data integration', 'Open', 'Medium', 'Data Team', 5, '2026-10-15');

-- Milestones
INSERT INTO project_milestones (project_id, name, planned_date, actual_date, status) VALUES
(1, 'Requirements Complete', '2025-05-31', '2025-06-20', 'Completed'),
(1, 'Design Approved', '2025-08-31', '2025-09-15', 'Completed'),
(1, 'Development Complete', '2026-04-30', '2026-06-15', 'Completed'),
(1, 'UAT Complete', '2026-07-31', NULL, 'Delayed'),
(1, 'Go Live', '2026-09-30', NULL, 'At Risk'),
(2, 'Requirements Complete', '2025-07-31', '2025-09-01', 'Completed'),
(2, 'Architecture Approved', '2025-10-31', '2025-11-15', 'Completed'),
(2, 'Development Phase 1', '2026-06-30', NULL, 'In Progress'),
(2, 'UAT Start', '2026-09-01', NULL, 'At Risk'),
(3, 'Design Complete', '2025-09-30', '2025-09-25', 'Completed'),
(3, 'Development Complete', '2026-03-31', '2026-03-28', 'Completed'),
(3, 'UAT Complete', '2026-05-31', '2026-05-29', 'Completed'),
(3, 'Production Release', '2026-06-30', NULL, 'On Track'),
(4, 'Requirements Complete', '2025-07-31', '2025-08-20', 'Completed'),
(4, 'Design Approved', '2025-11-30', '2025-12-10', 'Completed'),
(4, 'Development Phase 1', '2026-06-30', '2026-07-20', 'Completed'),
(4, 'Regulatory Testing', '2026-09-30', NULL, 'Delayed'),
(4, 'Production Deployment', '2026-10-31', NULL, 'At Risk');
"""


# =============================================================================
# MongoDB — Qualitative Data
# =============================================================================

MONGODB_DATA = {
    "project_risks": [
        {"project_id": "GTB", "severity": "Critical", "status": "Open", "category": "Schedule",
         "description": "UAT has been delayed by 2 weeks due to critical defects in SWIFT messaging and payment reconciliation modules. 3 critical defects remain unresolved with no clear resolution timeline. Business users have raised formal concerns about go-live readiness.",
         "identified_date": "2026-07-15", "owner": "Takeshi Yamamoto",
         "impact": "Go-live date at serious risk. Estimated 4-6 week delay unless critical defects are resolved within 10 days."},
        {"project_id": "GTB", "severity": "High", "status": "Open", "category": "Budget",
         "description": "Project budget is currently 8% above plan ($3.6M over). Main drivers: extended testing cycles, additional infrastructure for performance testing, and overtime costs. Trend indicates potential 12% overrun by completion.",
         "identified_date": "2026-06-01", "owner": "Finance",
         "impact": "Additional funding request of $5.4M being prepared for steering committee approval."},
        {"project_id": "GTB", "severity": "High", "status": "Open", "category": "Resource",
         "description": "2 senior developers (David Park, Chen Wei) have submitted resignations. Knowledge transfer window is only 3 weeks. These individuals are sole owners of critical SWIFT integration and batch processing modules.",
         "identified_date": "2026-08-01", "owner": "HR / Takeshi Yamamoto",
         "impact": "Critical path activities will be significantly impacted. No internal replacements identified with equivalent SWIFT expertise."},
        {"project_id": "CMTT", "severity": "High", "status": "Open", "category": "Requirements",
         "description": "Trading desk requirements for FX derivatives and structured products remain unsigned after 10 weeks. Three business units have conflicting requirements for position calculation methodology.",
         "identified_date": "2026-06-15", "owner": "Rachel Morgan",
         "impact": "Development of 3 key modules cannot proceed. Estimated 8-week delay if not resolved by end of August."},
        {"project_id": "CMTT", "severity": "Medium", "status": "Open", "category": "Dependency",
         "description": "Market data vendor (Bloomberg) announced API changes effective Q4 2026. Existing integration code requires significant refactoring. No alternative provider identified.",
         "identified_date": "2026-07-20", "owner": "Tech Lead",
         "impact": "4 weeks of unplanned rework. Budget impact estimated at $800K for vendor migration."},
        {"project_id": "RRRT", "severity": "High", "status": "Open", "category": "Data Quality",
         "description": "Upstream risk data systems have 34% data quality failures on critical fields (counterparty IDs, exposure amounts). Root cause traced to manual entry processes in 3 source systems.",
         "identified_date": "2026-05-01", "owner": "Data Team",
         "impact": "Regulatory report accuracy below 95% threshold. Potential regulatory censure if not resolved before Q4 submission deadline."},
        {"project_id": "RRRT", "severity": "High", "status": "Open", "category": "Regulatory",
         "description": "Basel IV final rules published in July 2026 contain material changes to capital adequacy calculation methodology. 6 additional weeks of development needed for compliance.",
         "identified_date": "2026-07-01", "owner": "Sarah Mitchell",
         "impact": "Scope expansion. Timeline extension request submitted. Regulatory deadline is non-negotiable."},
    ],
    "project_updates": [
        {"project_id": "GTB", "date": "2026-08-20", "author": "Takeshi Yamamoto", "type": "Weekly Status",
         "summary": "Project remains RED. UAT delayed by 2 weeks. 3 critical defects unresolved. Budget 8% over. 2 key developers departing. Steering committee escalation planned for Thursday.",
         "concerns": ["UAT completion date unknown", "Go-live at serious risk", "Budget overrun trajectory worsening", "Key resource departures"],
         "decisions": ["Approved weekend overtime for testing team", "Engaged contractor for SWIFT expertise", "Escalating to Group CTO"],
         "next_steps": ["Present recovery options to steering committee Aug 22", "Finalize contractor onboarding by Aug 25", "Identify DR test date"]},
        {"project_id": "GTB", "date": "2026-08-13", "author": "Takeshi Yamamoto", "type": "Weekly Status",
         "summary": "UAT environment stabilized but critical defects blocking test execution. Payment processing failures in cross-border scenarios. Business users unable to complete acceptance criteria.",
         "concerns": ["3 critical defects with no ETA", "Business confidence declining", "DR test not scheduled"],
         "decisions": ["Requested dedicated defect resolution team", "Daily defect triage calls starting Monday"],
         "next_steps": ["Resolve payment reconciliation defect by Friday", "Schedule business confidence workshop"]},
        {"project_id": "CMTT", "date": "2026-08-20", "author": "Rachel Morgan", "type": "Weekly Status",
         "summary": "Project AMBER. Requirements sign-off remains outstanding from Fixed Income and Structured Products desks. Market data dependency creating timeline pressure. Development team partially idle on blocked modules.",
         "concerns": ["Requirements deadlock entering week 10", "Market data vendor API changes", "Testing timeline compression"],
         "decisions": ["Escalated requirements to Head of Markets", "Initiated vendor alternative assessment"],
         "next_steps": ["Requirements resolution meeting Aug 23", "Market data migration assessment by Sep 1"]},
        {"project_id": "GDP", "date": "2026-08-20", "author": "Kenji Tanaka", "type": "Weekly Status",
         "summary": "Project GREEN. All sprints delivering on plan. Mobile app optimization completed. API gateway circuit breaker in progress. No material risks. Production release on track for June 30.",
         "concerns": ["Minor: API rate limiting needs tuning before peak load"],
         "decisions": ["Approved production release plan"],
         "next_steps": ["Complete API gateway work by Aug 30", "Production readiness review Sep 5"]},
        {"project_id": "RRRT", "date": "2026-08-20", "author": "Sarah Mitchell", "type": "Weekly Status",
         "summary": "Project AMBER. Data quality issues persisting. Basel IV changes require scope expansion (approved). Testing delayed pending regulatory test scenarios. Risk of missing Q4 regulatory deadline.",
         "concerns": ["Data quality gaps", "Basel IV scope expansion", "Testing scenario availability", "Q4 deadline pressure"],
         "decisions": ["Approved 6-week timeline extension", "Additional data engineer approved", "Engaged regulatory affairs for test scenarios"],
         "next_steps": ["Data quality remediation by Sep 15", "Basel IV design update by Sep 1", "Test scenarios from regulator by Sep 5"]},
    ],
    "project_meeting_observations": [
        {"project_id": "GTB", "date": "2026-08-22", "meeting_type": "Steering Committee",
         "attendees": ["Group CTO", "Head of Transaction Banking", "Takeshi Yamamoto", "CFO representative"],
         "key_observations": [
             "Group CTO expressed serious concern about go-live readiness",
             "CFO representative highlighted budget overrun trend and requested cost containment plan",
             "Head of Transaction Banking stressed business impact of further delay",
             "Takeshi Yamamoto presented 3 recovery options with risk/cost trade-offs",
             "Decision: 4-week UAT extension approved but no further delay acceptable"
         ],
         "action_items": ["Weekly CTO update from Takeshi", "Cost containment plan by Aug 28", "Defect resolution daily tracking"],
         "sentiment": "Serious concern — executive patience running thin"},
        {"project_id": "GTB", "date": "2026-08-15", "meeting_type": "Defect Triage",
         "attendees": ["David Park", "QA Lead", "Business Analyst", "Aisha Khan"],
         "key_observations": [
             "SWIFT message parsing failure traced to character encoding in non-Latin currencies",
             "Payment reconciliation mismatch is a data type precision issue (4 vs 6 decimal places)",
             "Performance regression root cause identified: connection pool exhaustion under load",
             "All 3 defects technically solvable but testing validation will take 5+ days each"
         ],
         "action_items": ["Encoding fix by Aug 17", "Precision fix by Aug 18", "Connection pool fix by Aug 20"],
         "sentiment": "Technical team confident in fixes but timeline very tight"},
        {"project_id": "RRRT", "date": "2026-08-18", "meeting_type": "Regulatory Review",
         "attendees": ["Sarah Mitchell", "Head of Compliance", "External Regulator liaison", "Data Governance"],
         "key_observations": [
             "Regulator confirmed Q4 submission deadline is non-negotiable",
             "Basel IV calculation methodology changes are material — cannot use existing templates",
             "Data quality issues in counterparty master data affecting 34% of records",
             "Regulator open to phased approach if critical reports delivered by deadline"
         ],
         "action_items": ["Phased delivery proposal by Sep 1", "Data quality escalation to source system owners", "Basel IV impact assessment complete by Aug 28"],
         "sentiment": "Challenging — regulatory pressure significant but pragmatic approach possible"},
    ],
    "project_health_signals": [
        {"project_id": "GTB", "date": "2026-08-20", "signal_type": "velocity_decline",
         "description": "Sprint velocity dropped 40% over last 4 sprints (from 55 to 33 story points)", "severity": "Critical"},
        {"project_id": "GTB", "date": "2026-08-20", "signal_type": "budget_trend",
         "description": "Monthly burn rate exceeds plan by $300K/month for last 4 months. Total variance: $3.6M (8%)", "severity": "High"},
        {"project_id": "GTB", "date": "2026-08-20", "signal_type": "defect_density",
         "description": "3 critical defects open >2 weeks. Defect discovery rate exceeding resolution rate.", "severity": "Critical"},
        {"project_id": "GTB", "date": "2026-08-20", "signal_type": "resource_attrition",
         "description": "2 senior developers leaving. Utilization >100% for 3 team members.", "severity": "High"},
        {"project_id": "CMTT", "date": "2026-08-20", "signal_type": "requirements_gap",
         "description": "Requirements sign-off pending for 10 weeks. 3 business units in conflict.", "severity": "High"},
        {"project_id": "CMTT", "date": "2026-08-20", "signal_type": "dependency_risk",
         "description": "Market data vendor API change requires unplanned rework. No alternative identified.", "severity": "Medium"},
        {"project_id": "GDP", "date": "2026-08-20", "signal_type": "positive_trend",
         "description": "All milestones on or ahead of schedule for 8 consecutive sprints. Zero critical defects.", "severity": "Low"},
        {"project_id": "RRRT", "date": "2026-08-20", "signal_type": "data_quality",
         "description": "34% of risk data records failing quality checks. Regulatory accuracy threshold at risk.", "severity": "High"},
        {"project_id": "RRRT", "date": "2026-08-20", "signal_type": "scope_change",
         "description": "Basel IV final rules require 6 additional weeks of development. Regulatory deadline unchanged.", "severity": "High"},
    ],
}


# =============================================================================
# App_DB — Update projects table
# =============================================================================

async def seed_app_db_projects():
    """Update the app_db projects table with SMBC project names and codes."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy import text
    from app.config.settings import Settings

    s = Settings()
    engine = create_async_engine(s.app_db_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        # Truncate projects with CASCADE — handles all FK chains automatically
        await session.execute(text("TRUNCATE TABLE projects CASCADE"))

        # Insert the 4 SMBC projects
        projects = [
            (PROJECT_GTB_ID, "GTB", "Global Transaction Banking Platform Modernization",
             "End-to-end modernization of the global transaction banking platform including payments, cash management and trade finance systems. Status: RED — UAT delayed, critical defects, budget overrun.",
             "active"),
            (PROJECT_CMTT_ID, "CMTT", "Capital Markets Technology Transformation",
             "Technology transformation of trading, risk and post-trade systems to support regulatory compliance and market competitiveness. Status: AMBER — requirements pending, testing delays.",
             "active"),
            (PROJECT_GDP_ID, "GDP", "Global Digital Platform Enhancement",
             "Enhancement of digital banking platform covering mobile, internet banking and API gateway modernization. Status: GREEN — on track, minor risks only.",
             "active"),
            (PROJECT_RRRT_ID, "RRRT", "Regulatory & Risk Reporting Transformation",
             "Transformation of regulatory reporting infrastructure to meet Basel IV, FRTB and ESG reporting requirements. Status: AMBER — data quality gaps, testing delays.",
             "active"),
        ]

        for pid, code, name, desc, status in projects:
            await session.execute(
                text("""INSERT INTO projects (id, project_code, name, description, status, created_by, created_at, updated_at)
                        VALUES (:id, :code, :name, :desc, :status, :created_by, now(), now())
                        ON CONFLICT (id) DO UPDATE SET project_code = :code, name = :name, description = :desc"""),
                {"id": pid, "code": code, "name": name, "desc": desc, "status": status, "created_by": USER_ADMIN_ID}
            )

        # Add project members
        await session.execute(
            text("""INSERT INTO project_members (id, project_id, user_id, role, created_at)
                    VALUES (:id, :pid, :uid, 'lead', now())"""),
            {"id": str(uuid4()), "pid": PROJECT_GTB_ID, "uid": USER_ADMIN_ID}
        )

        await session.commit()
        print("  ✓ app_db projects updated (4 SMBC projects)")

    await engine.dispose()


# =============================================================================
# External PostgreSQL
# =============================================================================

async def seed_postgres():
    """Recreate the technology_transformation DB with SMBC data."""
    import asyncpg

    print("\n" + "=" * 60)
    print("  Seeding External PostgreSQL: technology_transformation")
    print("=" * 60)

    conn = await asyncpg.connect(host="localhost", port=5432, user="postgres", password="master", database="postgres")
    exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = 'technology_transformation'")
    if not exists:
        await conn.execute("CREATE DATABASE technology_transformation")
        print("  ✓ Database created")
    await conn.close()

    conn = await asyncpg.connect(host="localhost", port=5432, user="postgres", password="master", database="technology_transformation")
    await conn.execute(POSTGRES_SCHEMA)
    print("  ✓ Schema created (11 tables)")
    await conn.execute(POSTGRES_SEED)
    print("  ✓ Data seeded")

    # Verify
    for table in ["projects", "project_finance", "project_progress", "project_risks_ext", "jira_issues", "unattended_actions"]:
        count = await conn.fetchval(f"SELECT count(*) FROM {table}")
        print(f"    {table}: {count} rows")

    await conn.close()


# =============================================================================
# MongoDB
# =============================================================================

async def seed_mongodb():
    """Seed MongoDB with qualitative SMBC data."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except ImportError:
        print("  ⚠ Motor not installed. Skipping MongoDB.")
        return

    print("\n" + "=" * 60)
    print("  Seeding External MongoDB: technology_transformation")
    print("=" * 60)

    try:
        client = AsyncIOMotorClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
        await client.admin.command("ping")
    except Exception as e:
        print(f"  ⚠ MongoDB not available: {e}")
        return

    db = client["technology_transformation"]
    for collection_name in MONGODB_DATA.keys():
        await db.drop_collection(collection_name)

    for collection_name, documents in MONGODB_DATA.items():
        if documents:
            result = await db[collection_name].insert_many(documents)
            print(f"  ✓ {collection_name}: {len(result.inserted_ids)} documents")

    client.close()


# =============================================================================
# Main
# =============================================================================

async def main():
    print("\n" + "=" * 60)
    print("  SMBC POC — Seeding 4 Banking Projects")
    print("=" * 60)

    await seed_app_db_projects()
    await seed_postgres()
    await seed_mongodb()

    print("\n" + "=" * 60)
    print("  ✅ SMBC POC data seeded successfully!")
    print("")
    print("  Projects:")
    print("    🔴 GTB  — Global Transaction Banking Platform Modernization")
    print("    🟠 CMTT — Capital Markets Technology Transformation")
    print("    🟢 GDP  — Global Digital Platform Enhancement")
    print("    🟠 RRRT — Regulatory & Risk Reporting Transformation")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
