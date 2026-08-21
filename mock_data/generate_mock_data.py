"""
Generate mock data files for testing the Project Intelligence Hub.

Creates files in various formats (CSV, JSON, Excel) across all project categories:
- Project Costs
- Burndown
- Audit
- IT Controls
- Remediation
- Business Intelligence
- Internal Data

Run: python generate_mock_data.py
"""

import json
import os
import random
from datetime import datetime, timedelta

# Try to import optional dependencies
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("Warning: pandas not installed. Excel files will not be generated.")
    print("Install with: pip install pandas openpyxl")

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def save_csv(filename, headers, rows):
    """Save data as CSV."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")
        for row in rows:
            f.write(",".join(str(v) for v in row) + "\n")
    print(f"  Created: {filename}")


def save_json(filename, data):
    """Save data as JSON."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  Created: {filename}")


def save_excel(filename, sheets_data):
    """Save data as Excel with multiple sheets."""
    if not HAS_PANDAS:
        return
    filepath = os.path.join(OUTPUT_DIR, filename)
    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        for sheet_name, (headers, rows) in sheets_data.items():
            df = pd.DataFrame(rows, columns=headers)
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    print(f"  Created: {filename}")


# ─── Project Costs ────────────────────────────────────────────────────────────

def generate_project_costs():
    print("\n📊 Project Costs:")

    # CSV - Monthly budget breakdown
    headers = ["Month", "Category", "Planned_Budget", "Actual_Spend", "Variance"]
    rows = []
    categories = ["Infrastructure", "Development", "Testing", "Operations", "Training"]
    months = ["Jan-2026", "Feb-2026", "Mar-2026", "Apr-2026", "May-2026", "Jun-2026"]
    for month in months:
        for cat in categories:
            planned = random.randint(15000, 80000)
            actual = planned + random.randint(-10000, 15000)
            rows.append([month, cat, planned, actual, actual - planned])
    save_csv("project_costs_monthly.csv", headers, rows)

    # JSON - Cost summary
    cost_summary = {
        "project": "Digital Transformation Initiative",
        "fiscal_year": "FY2026",
        "total_budget": 2500000,
        "spent_to_date": 1847500,
        "remaining": 652500,
        "burn_rate_per_month": 307916,
        "categories": [
            {"name": "Infrastructure", "budget": 600000, "spent": 487000, "status": "on_track"},
            {"name": "Development", "budget": 900000, "spent": 723000, "status": "on_track"},
            {"name": "Testing & QA", "budget": 350000, "spent": 298000, "status": "at_risk"},
            {"name": "Operations", "budget": 400000, "spent": 215000, "status": "on_track"},
            {"name": "Training & Change Mgmt", "budget": 250000, "spent": 124500, "status": "behind"},
        ],
        "milestones": [
            {"name": "Phase 1 Complete", "date": "2026-03-15", "cost": 450000, "status": "completed"},
            {"name": "Phase 2 Complete", "date": "2026-06-30", "cost": 780000, "status": "in_progress"},
            {"name": "UAT Sign-off", "date": "2026-09-15", "cost": 350000, "status": "planned"},
            {"name": "Go-Live", "date": "2026-11-01", "cost": 270000, "status": "planned"},
        ],
    }
    save_json("project_costs_summary.json", cost_summary)

    # Excel - Detailed cost tracking
    if HAS_PANDAS:
        sheets = {
            "CapEx": (
                ["Item", "Vendor", "Amount", "Date", "Approved_By", "Status"],
                [
                    ["Cloud Infrastructure", "AWS", 125000, "2026-01-15", "J. Smith", "Paid"],
                    ["Server Hardware", "Dell", 87000, "2026-02-01", "J. Smith", "Paid"],
                    ["Network Equipment", "Cisco", 45000, "2026-02-15", "M. Chen", "Paid"],
                    ["Security Appliances", "Palo Alto", 62000, "2026-03-01", "M. Chen", "Pending"],
                    ["Database Licenses", "Oracle", 98000, "2026-03-15", "J. Smith", "Paid"],
                    ["Dev Tools Licenses", "JetBrains", 15000, "2026-04-01", "R. Patel", "Paid"],
                ],
            ),
            "OpEx": (
                ["Category", "Q1_Actual", "Q2_Actual", "Q3_Forecast", "Q4_Forecast", "Annual_Total"],
                [
                    ["Cloud Hosting", 45000, 52000, 58000, 60000, 215000],
                    ["SaaS Subscriptions", 12000, 12000, 14000, 14000, 52000],
                    ["Contractors", 90000, 85000, 75000, 50000, 300000],
                    ["Support & Maintenance", 8000, 9000, 10000, 10000, 37000],
                    ["Monitoring Tools", 5000, 5000, 6000, 6000, 22000],
                ],
            ),
        }
        save_excel("project_costs_detailed.xlsx", sheets)


# ─── Burndown ─────────────────────────────────────────────────────────────────

def generate_burndown():
    print("\n🔥 Burndown:")

    # CSV - Sprint burndown data
    headers = ["Sprint", "Day", "Planned_Remaining", "Actual_Remaining", "Stories_Completed"]
    rows = []
    for sprint in range(1, 7):
        total_points = random.randint(40, 60)
        planned = total_points
        actual = total_points
        for day in range(1, 11):
            planned_decrement = total_points / 10
            actual_decrement = random.uniform(0, planned_decrement * 2.5)
            planned = max(0, planned - planned_decrement)
            actual = max(0, actual - actual_decrement)
            stories = random.randint(0, 3) if actual_decrement > 2 else 0
            rows.append([f"Sprint {sprint}", day, round(planned, 1), round(actual, 1), stories])
    save_csv("burndown_sprints.csv", headers, rows)

    # JSON - Release burndown
    release_burndown = {
        "release": "v2.0 - Digital Platform",
        "start_date": "2026-01-06",
        "target_date": "2026-09-30",
        "total_story_points": 480,
        "completed_points": 312,
        "velocity_average": 52,
        "sprints": [
            {"id": 1, "name": "Sprint 1", "planned": 48, "completed": 45, "velocity": 45},
            {"id": 2, "name": "Sprint 2", "planned": 50, "completed": 52, "velocity": 52},
            {"id": 3, "name": "Sprint 3", "planned": 52, "completed": 48, "velocity": 48},
            {"id": 4, "name": "Sprint 4", "planned": 52, "completed": 55, "velocity": 55},
            {"id": 5, "name": "Sprint 5", "planned": 54, "completed": 58, "velocity": 58},
            {"id": 6, "name": "Sprint 6", "planned": 54, "completed": 54, "velocity": 54},
        ],
        "risks": [
            {"description": "Key developer on leave in Sprint 8", "impact": "medium", "mitigation": "Cross-train team members"},
            {"description": "Third-party API integration delayed", "impact": "high", "mitigation": "Build mock service layer"},
        ],
    }
    save_json("burndown_release.json", release_burndown)


# ─── Audit ────────────────────────────────────────────────────────────────────

def generate_audit():
    print("\n🔍 Audit:")

    # CSV - Audit findings
    headers = ["Finding_ID", "Category", "Severity", "Description", "Status", "Owner", "Due_Date", "Days_Open"]
    rows = [
        ["AUD-001", "Access Control", "High", "Privileged accounts lack MFA", "Open", "Security Team", "2026-08-15", 45],
        ["AUD-002", "Data Protection", "Critical", "PII data unencrypted in staging DB", "In Progress", "DBA Team", "2026-07-30", 60],
        ["AUD-003", "Change Management", "Medium", "Missing approval records for 12 changes", "Closed", "Release Mgmt", "2026-06-15", 0],
        ["AUD-004", "Logging", "High", "Audit logs not retained for 90 days", "Open", "Platform Team", "2026-09-01", 30],
        ["AUD-005", "Vendor Management", "Medium", "3 vendor contracts expired without renewal", "In Progress", "Procurement", "2026-08-30", 22],
        ["AUD-006", "Business Continuity", "High", "DR test not conducted in 18 months", "Open", "Operations", "2026-09-15", 15],
        ["AUD-007", "Code Quality", "Low", "Static analysis findings not triaged", "Closed", "Dev Lead", "2026-05-30", 0],
        ["AUD-008", "Compliance", "Critical", "SOX controls gap in financial module", "In Progress", "Compliance Team", "2026-08-01", 55],
        ["AUD-009", "Network Security", "Medium", "Firewall rules not reviewed quarterly", "Open", "Network Team", "2026-09-30", 10],
        ["AUD-010", "Identity Management", "High", "Orphaned accounts detected (47 accounts)", "In Progress", "IAM Team", "2026-08-15", 38],
    ]
    save_csv("audit_findings.csv", headers, rows)

    # JSON - Audit report summary
    audit_report = {
        "audit_id": "INT-AUDIT-2026-Q2",
        "audit_type": "Internal Technology Audit",
        "period": "Q2 2026 (Apr - Jun)",
        "auditor": "Deloitte Internal Audit Services",
        "overall_rating": "Needs Improvement",
        "summary": {
            "total_findings": 10,
            "critical": 2,
            "high": 4,
            "medium": 3,
            "low": 1,
            "closed": 2,
            "in_progress": 4,
            "open": 4,
        },
        "recommendations": [
            "Implement MFA for all privileged accounts within 30 days",
            "Encrypt all PII data at rest and in transit",
            "Establish quarterly access review process",
            "Conduct DR test by end of Q3 2026",
            "Remediate SOX control gaps before year-end audit",
        ],
        "next_audit_date": "2026-10-15",
    }
    save_json("audit_report_q2.json", audit_report)


# ─── IT Controls ──────────────────────────────────────────────────────────────

def generate_it_controls():
    print("\n🛡️ IT Controls:")

    # CSV - Control testing results
    headers = ["Control_ID", "Control_Name", "Domain", "Test_Result", "Last_Tested", "Frequency", "Risk_Rating", "Evidence"]
    rows = [
        ["CTRL-001", "Password Complexity", "Access Management", "Pass", "2026-06-15", "Quarterly", "Medium", "AD policy screenshot"],
        ["CTRL-002", "Account Lockout", "Access Management", "Pass", "2026-06-15", "Quarterly", "Medium", "Config export"],
        ["CTRL-003", "Privileged Access Review", "Access Management", "Fail", "2026-06-20", "Monthly", "High", "Review logs incomplete"],
        ["CTRL-004", "Change Approval Workflow", "Change Management", "Pass", "2026-06-01", "Monthly", "High", "ServiceNow tickets"],
        ["CTRL-005", "Segregation of Duties", "Access Management", "Pass", "2026-05-30", "Quarterly", "Critical", "Role matrix"],
        ["CTRL-006", "Backup Verification", "Operations", "Fail", "2026-06-10", "Weekly", "High", "3 backup failures in June"],
        ["CTRL-007", "Patch Management", "Vulnerability Mgmt", "Pass", "2026-06-25", "Monthly", "High", "WSUS report"],
        ["CTRL-008", "Incident Response", "Security Ops", "Pass", "2026-04-15", "Quarterly", "Critical", "Tabletop exercise report"],
        ["CTRL-009", "Data Classification", "Data Protection", "Fail", "2026-05-20", "Annual", "High", "30% assets unclassified"],
        ["CTRL-010", "Encryption Standards", "Data Protection", "Pass", "2026-06-30", "Quarterly", "Critical", "TLS scan results"],
        ["CTRL-011", "Log Monitoring", "Security Ops", "Pass", "2026-06-28", "Continuous", "High", "SIEM dashboard"],
        ["CTRL-012", "Vendor Risk Assessment", "Third Party", "Fail", "2026-03-15", "Annual", "Medium", "5 vendors not assessed"],
    ]
    save_csv("it_controls_testing.csv", headers, rows)

    # Excel - Control framework
    if HAS_PANDAS:
        sheets = {
            "Control Inventory": (
                ["Control_ID", "Domain", "Objective", "Type", "Automation", "Owner"],
                [
                    ["CTRL-001", "Access Mgmt", "Ensure strong passwords", "Preventive", "Automated", "IAM Team"],
                    ["CTRL-002", "Access Mgmt", "Prevent brute force attacks", "Preventive", "Automated", "IAM Team"],
                    ["CTRL-003", "Access Mgmt", "Review privileged access", "Detective", "Manual", "Security Team"],
                    ["CTRL-004", "Change Mgmt", "Ensure authorized changes", "Preventive", "Semi-Auto", "Release Mgmt"],
                    ["CTRL-005", "Access Mgmt", "Prevent conflicts of interest", "Preventive", "Manual", "Compliance"],
                    ["CTRL-006", "Operations", "Verify data recoverability", "Detective", "Automated", "Ops Team"],
                    ["CTRL-007", "Vulnerability", "Reduce attack surface", "Preventive", "Automated", "Infra Team"],
                    ["CTRL-008", "Security", "Effective incident handling", "Corrective", "Manual", "Security Team"],
                ],
            ),
            "Risk Heat Map": (
                ["Domain", "Inherent_Risk", "Control_Effectiveness", "Residual_Risk", "Trend"],
                [
                    ["Access Management", "High", "Moderate", "Medium", "Stable"],
                    ["Change Management", "Medium", "Strong", "Low", "Improving"],
                    ["Data Protection", "Critical", "Weak", "High", "Deteriorating"],
                    ["Security Operations", "High", "Strong", "Medium", "Improving"],
                    ["Third Party", "High", "Weak", "High", "Stable"],
                    ["Business Continuity", "Critical", "Moderate", "High", "Deteriorating"],
                ],
            ),
        }
        save_excel("it_controls_framework.xlsx", sheets)


# ─── Remediation ──────────────────────────────────────────────────────────────

def generate_remediation():
    print("\n🔧 Remediation:")

    # CSV - Remediation tracker
    headers = ["Ticket_ID", "Finding_Source", "Title", "Priority", "Status", "Assigned_To", "Created", "Target_Date", "Percent_Complete"]
    rows = [
        ["REM-001", "AUD-001", "Implement MFA for privileged accounts", "P1", "In Progress", "IAM Team", "2026-05-01", "2026-08-15", 65],
        ["REM-002", "AUD-002", "Encrypt staging database PII fields", "P1", "In Progress", "DBA Team", "2026-05-15", "2026-07-30", 80],
        ["REM-003", "AUD-004", "Configure 90-day log retention", "P2", "Not Started", "Platform Team", "2026-06-01", "2026-09-01", 0],
        ["REM-004", "AUD-006", "Schedule and execute DR test", "P2", "In Progress", "Operations", "2026-06-10", "2026-09-15", 30],
        ["REM-005", "AUD-008", "Close SOX control gaps", "P1", "In Progress", "Compliance", "2026-05-20", "2026-08-01", 45],
        ["REM-006", "CTRL-003", "Automate privileged access reviews", "P2", "Planning", "IAM Team", "2026-06-25", "2026-10-01", 10],
        ["REM-007", "CTRL-006", "Fix backup job failures", "P1", "Completed", "Ops Team", "2026-06-12", "2026-06-30", 100],
        ["REM-008", "CTRL-009", "Complete data classification exercise", "P3", "In Progress", "Data Governance", "2026-04-01", "2026-09-30", 55],
        ["REM-009", "CTRL-012", "Conduct vendor risk assessments", "P3", "Not Started", "Procurement", "2026-07-01", "2026-11-30", 0],
        ["REM-010", "PEN-TEST", "Patch critical vulnerabilities from pen test", "P1", "In Progress", "Infra Team", "2026-06-01", "2026-07-15", 90],
    ]
    save_csv("remediation_tracker.csv", headers, rows)

    # JSON - Remediation dashboard data
    remediation_dashboard = {
        "as_of_date": "2026-07-15",
        "summary": {
            "total_items": 10,
            "completed": 1,
            "in_progress": 6,
            "not_started": 2,
            "planning": 1,
            "overdue": 2,
            "at_risk": 3,
        },
        "by_priority": {
            "P1": {"total": 4, "completed": 0, "in_progress": 4},
            "P2": {"total": 3, "completed": 1, "in_progress": 1, "not_started": 1},
            "P3": {"total": 3, "completed": 0, "in_progress": 1, "not_started": 1, "planning": 1},
        },
        "aging": {
            "0_30_days": 3,
            "31_60_days": 4,
            "61_90_days": 2,
            "over_90_days": 1,
        },
        "trend": [
            {"month": "Mar-2026", "open": 5, "closed": 1},
            {"month": "Apr-2026", "open": 7, "closed": 2},
            {"month": "May-2026", "open": 9, "closed": 3},
            {"month": "Jun-2026", "open": 10, "closed": 4},
            {"month": "Jul-2026", "open": 9, "closed": 5},
        ],
    }
    save_json("remediation_dashboard.json", remediation_dashboard)


# ─── Business Intelligence ────────────────────────────────────────────────────

def generate_business_intelligence():
    print("\n📈 Business Intelligence:")

    # CSV - KPI metrics
    headers = ["Date", "Active_Users", "Transactions", "Revenue", "Avg_Response_Time_ms", "Error_Rate_Percent", "Uptime_Percent"]
    rows = []
    base_date = datetime(2026, 1, 1)
    for i in range(180):  # 6 months of daily data
        date = base_date + timedelta(days=i)
        users = random.randint(1200, 3500) + (i * 5)  # growing trend
        transactions = users * random.randint(3, 8)
        revenue = transactions * random.uniform(12.5, 45.0)
        response_time = random.uniform(120, 450)
        error_rate = random.uniform(0.1, 2.5)
        uptime = random.uniform(99.5, 99.99)
        rows.append([
            date.strftime("%Y-%m-%d"),
            users,
            transactions,
            round(revenue, 2),
            round(response_time, 1),
            round(error_rate, 2),
            round(uptime, 3),
        ])
    save_csv("bi_daily_kpis.csv", headers, rows)

    # JSON - Executive summary
    exec_summary = {
        "report_period": "H1 2026",
        "business_unit": "Digital Banking",
        "highlights": [
            "Active users grew 45% YoY to 3,200 daily average",
            "Transaction volume up 62% driven by mobile adoption",
            "Revenue per user increased 12% through cross-selling",
            "System uptime maintained at 99.95% SLA achievement",
        ],
        "kpi_summary": {
            "customer_satisfaction": {"current": 4.2, "target": 4.5, "previous": 3.9},
            "net_promoter_score": {"current": 42, "target": 50, "previous": 35},
            "digital_adoption_rate": {"current": 0.73, "target": 0.80, "previous": 0.58},
            "cost_per_transaction": {"current": 0.45, "target": 0.40, "previous": 0.62},
            "time_to_market_days": {"current": 28, "target": 21, "previous": 45},
        },
        "top_issues": [
            {"issue": "Mobile app crash rate spike in March", "impact": "Medium", "resolved": True},
            {"issue": "Payment gateway latency during peak hours", "impact": "High", "resolved": False},
            {"issue": "Customer onboarding drop-off at KYC step", "impact": "High", "resolved": False},
        ],
    }
    save_json("bi_executive_summary.json", exec_summary)

    # Excel - Regional performance
    if HAS_PANDAS:
        sheets = {
            "Regional Revenue": (
                ["Region", "Q1_Revenue", "Q2_Revenue", "Growth_Percent", "Market_Share"],
                [
                    ["Tokyo", 12500000, 14200000, 13.6, 0.32],
                    ["Osaka", 8700000, 9100000, 4.6, 0.28],
                    ["Nagoya", 5400000, 6200000, 14.8, 0.21],
                    ["Fukuoka", 3200000, 3800000, 18.7, 0.15],
                    ["Sapporo", 2100000, 2400000, 14.3, 0.12],
                ],
            ),
            "Product Performance": (
                ["Product", "Users", "Revenue", "ARPU", "Churn_Rate", "NPS"],
                [
                    ["Mobile Banking", 45000, 8500000, 188.9, 0.03, 52],
                    ["Online Trading", 12000, 15200000, 1266.7, 0.05, 38],
                    ["Digital Payments", 67000, 4200000, 62.7, 0.02, 61],
                    ["Wealth Management", 3500, 22000000, 6285.7, 0.01, 45],
                    ["Business Banking", 8200, 11800000, 1439.0, 0.04, 41],
                ],
            ),
        }
        save_excel("bi_regional_performance.xlsx", sheets)


# ─── Internal Data ────────────────────────────────────────────────────────────

def generate_internal_data():
    print("\n🏢 Internal Data:")

    # CSV - Team capacity & allocation
    headers = ["Team", "Total_Members", "Available", "Allocated_to_Project", "Utilization_Percent", "Avg_Experience_Years"]
    rows = [
        ["Backend Engineering", 12, 10, 8, 85, 6.5],
        ["Frontend Engineering", 8, 7, 6, 82, 4.2],
        ["QA & Testing", 6, 6, 5, 78, 5.1],
        ["DevOps & SRE", 5, 4, 3, 90, 7.8],
        ["Data Engineering", 4, 4, 3, 88, 5.5],
        ["Security", 3, 3, 2, 75, 8.2],
        ["Architecture", 2, 2, 2, 95, 12.0],
        ["Product Management", 3, 3, 2, 70, 6.0],
        ["UX Design", 4, 3, 3, 80, 4.8],
        ["Project Management", 2, 2, 2, 85, 9.5],
    ]
    save_csv("internal_team_capacity.csv", headers, rows)

    # JSON - Sprint retrospective data
    retro_data = {
        "sprint": "Sprint 6",
        "dates": "2026-06-17 to 2026-06-28",
        "velocity": 54,
        "planned_vs_delivered": {"planned": 56, "delivered": 54, "carried_over": 2},
        "team_satisfaction": 3.8,
        "what_went_well": [
            "CI/CD pipeline improvements reduced deploy time by 40%",
            "Cross-team collaboration on API design was effective",
            "New monitoring dashboards caught 3 issues before production",
        ],
        "what_to_improve": [
            "Sprint planning estimates still 15% over-optimistic",
            "Code review turnaround time averaging 2 days (target: 1 day)",
            "Testing environment instability caused 6 hours of blocked work",
        ],
        "action_items": [
            {"item": "Add buffer factor to planning estimates", "owner": "Scrum Master", "due": "Sprint 7"},
            {"item": "Implement PR size limits and review SLA", "owner": "Tech Lead", "due": "Sprint 7"},
            {"item": "Dedicate time for test env stability fixes", "owner": "DevOps", "due": "Sprint 7-8"},
        ],
    }
    save_json("internal_sprint_retro.json", retro_data)

    # Excel - Resource planning
    if HAS_PANDAS:
        sheets = {
            "Resource Plan": (
                ["Resource", "Role", "Team", "Jul_Allocation", "Aug_Allocation", "Sep_Allocation", "Skills"],
                [
                    ["Tanaka K.", "Senior Dev", "Backend", "100%", "100%", "80%", "Java, Spring, PostgreSQL"],
                    ["Suzuki M.", "Tech Lead", "Backend", "80%", "80%", "60%", "Java, Microservices, AWS"],
                    ["Sato Y.", "Dev", "Frontend", "100%", "100%", "100%", "React, TypeScript, Node.js"],
                    ["Watanabe H.", "Senior Dev", "Frontend", "100%", "80%", "60%", "React, GraphQL, Testing"],
                    ["Yamamoto T.", "QA Lead", "Testing", "100%", "100%", "100%", "Selenium, JMeter, API Testing"],
                    ["Nakamura R.", "DevOps", "SRE", "60%", "80%", "100%", "Kubernetes, Terraform, CI/CD"],
                    ["Kobayashi A.", "Data Eng", "Data", "100%", "100%", "80%", "Python, Spark, Airflow"],
                    ["Ito S.", "Security Eng", "Security", "40%", "60%", "80%", "SAST, DAST, Cloud Security"],
                ],
            ),
            "Leave Calendar": (
                ["Resource", "Leave_Start", "Leave_End", "Type", "Days"],
                [
                    ["Tanaka K.", "2026-08-10", "2026-08-14", "Annual Leave", 5],
                    ["Suzuki M.", "2026-09-01", "2026-09-05", "Annual Leave", 5],
                    ["Sato Y.", "2026-07-28", "2026-07-29", "Personal", 2],
                    ["Nakamura R.", "2026-08-18", "2026-08-22", "Training", 5],
                    ["Kobayashi A.", "2026-09-15", "2026-09-19", "Conference", 5],
                ],
            ),
        }
        save_excel("internal_resource_plan.xlsx", sheets)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Generating Mock Data for Project Intelligence Hub")
    print("=" * 60)

    generate_project_costs()
    generate_burndown()
    generate_audit()
    generate_it_controls()
    generate_remediation()
    generate_business_intelligence()
    generate_internal_data()

    print("\n" + "=" * 60)
    print("  ✅ All mock data files generated!")
    print(f"  📁 Location: {OUTPUT_DIR}")
    print("=" * 60)
    print("\nUpload these files to the Project Intelligence Hub using")
    print("the Data Management screen with the following categories:")
    print("  - project_costs_*     → Project Costs")
    print("  - burndown_*          → Burndown")
    print("  - audit_*             → Audit")
    print("  - it_controls_*       → IT Controls")
    print("  - remediation_*       → Remediation")
    print("  - bi_*                → Business Intelligence")
    print("  - internal_*          → Internal Data")


if __name__ == "__main__":
    main()
