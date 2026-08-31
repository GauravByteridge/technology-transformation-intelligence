"""Seed additional time-series data for PMO charts (budget monthly + sprint velocity)."""
import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, dbname='technology_transformation', user='postgres', password='master')
conn.autocommit = True
cur = conn.cursor()

# Create budget_monthly table
cur.execute("""
    CREATE TABLE IF NOT EXISTS budget_monthly (
        id SERIAL PRIMARY KEY,
        project_id INTEGER REFERENCES projects(id),
        month DATE NOT NULL,
        planned_spend NUMERIC(12,2) NOT NULL,
        actual_spend NUMERIC(12,2) NOT NULL
    )
""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_budget_monthly_project ON budget_monthly(project_id)")
print("Created budget_monthly table")

# Create sprint_velocity table
cur.execute("""
    CREATE TABLE IF NOT EXISTS sprint_velocity (
        id SERIAL PRIMARY KEY,
        project_id INTEGER REFERENCES projects(id),
        sprint_name VARCHAR(50) NOT NULL,
        sprint_end_date DATE NOT NULL,
        committed_points INTEGER NOT NULL,
        completed_points INTEGER NOT NULL
    )
""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_sprint_velocity_project ON sprint_velocity(project_id)")
print("Created sprint_velocity table")

# Seed budget_monthly for GTBPM (project_id=1)
cur.execute("DELETE FROM budget_monthly")
budget_data = [
    # GTBPM (id=1) - $45M total budget, monthly planned ~$2.8M, actuals running higher
    (1, '2025-03-01', 2200000, 2100000),
    (1, '2025-04-01', 2500000, 2400000),
    (1, '2025-05-01', 2800000, 2700000),
    (1, '2025-06-01', 2800000, 2900000),
    (1, '2025-07-01', 2800000, 3100000),
    (1, '2025-08-01', 2800000, 3200000),
    (1, '2025-09-01', 2800000, 3000000),
    (1, '2025-10-01', 2800000, 3100000),
    (1, '2025-11-01', 2800000, 3300000),
    (1, '2025-12-01', 2800000, 3000000),
    (1, '2026-01-01', 2800000, 3200000),
    (1, '2026-02-01', 2800000, 3100000),
    (1, '2026-03-01', 2800000, 3400000),
    (1, '2026-04-01', 2800000, 3500000),
    (1, '2026-05-01', 2800000, 3600000),
    (1, '2026-06-01', 2800000, 3800000),
    (1, '2026-07-01', 2800000, 3900000),
    (1, '2026-08-01', 2800000, 3700000),
    # CMTT (id=2) - $32M total budget
    (2, '2025-05-01', 1800000, 1700000),
    (2, '2025-06-01', 2000000, 1900000),
    (2, '2025-07-01', 2000000, 2000000),
    (2, '2025-08-01', 2000000, 2100000),
    (2, '2025-09-01', 2000000, 2000000),
    (2, '2025-10-01', 2000000, 2200000),
    (2, '2025-11-01', 2000000, 2100000),
    (2, '2025-12-01', 2000000, 2000000),
    (2, '2026-01-01', 2000000, 2100000),
    (2, '2026-02-01', 2000000, 2200000),
    (2, '2026-03-01', 2000000, 2300000),
    (2, '2026-04-01', 2000000, 2100000),
    (2, '2026-05-01', 2000000, 2200000),
    (2, '2026-06-01', 2000000, 2300000),
    (2, '2026-07-01', 2000000, 2100000),
    (2, '2026-08-01', 2000000, 2200000),
    # GDP (id=3) - $18M total budget - on track
    (3, '2025-08-01', 1500000, 1400000),
    (3, '2025-09-01', 1500000, 1500000),
    (3, '2025-10-01', 1500000, 1450000),
    (3, '2025-11-01', 1500000, 1500000),
    (3, '2025-12-01', 1500000, 1480000),
    (3, '2026-01-01', 1500000, 1520000),
    (3, '2026-02-01', 1500000, 1500000),
    (3, '2026-03-01', 1500000, 1550000),
    (3, '2026-04-01', 1500000, 1490000),
    (3, '2026-05-01', 1500000, 1510000),
    (3, '2026-06-01', 1500000, 1500000),
    (3, '2026-07-01', 1500000, 1520000),
    (3, '2026-08-01', 1500000, 1480000),
    # RRRT (id=4) - $25M total budget
    (4, '2025-06-01', 1600000, 1500000),
    (4, '2025-07-01', 1600000, 1550000),
    (4, '2025-08-01', 1600000, 1600000),
    (4, '2025-09-01', 1600000, 1700000),
    (4, '2025-10-01', 1600000, 1650000),
    (4, '2025-11-01', 1600000, 1600000),
    (4, '2025-12-01', 1600000, 1700000),
    (4, '2026-01-01', 1600000, 1750000),
    (4, '2026-02-01', 1600000, 1600000),
    (4, '2026-03-01', 1600000, 1700000),
    (4, '2026-04-01', 1600000, 1800000),
    (4, '2026-05-01', 1600000, 1750000),
    (4, '2026-06-01', 1600000, 1700000),
    (4, '2026-07-01', 1600000, 1800000),
    (4, '2026-08-01', 1600000, 1750000),
]

for row in budget_data:
    cur.execute(
        "INSERT INTO budget_monthly (project_id, month, planned_spend, actual_spend) VALUES (%s, %s, %s, %s)",
        row
    )
print(f"Inserted {len(budget_data)} budget_monthly rows")

# Seed sprint_velocity
cur.execute("DELETE FROM sprint_velocity")
velocity_data = [
    # GTBPM (id=1) - velocity declining
    (1, 'Sprint 1', '2025-04-15', 55, 52),
    (1, 'Sprint 2', '2025-05-13', 55, 50),
    (1, 'Sprint 3', '2025-06-10', 55, 48),
    (1, 'Sprint 4', '2025-07-08', 55, 45),
    (1, 'Sprint 5', '2025-08-05', 50, 42),
    (1, 'Sprint 6', '2025-09-02', 50, 44),
    (1, 'Sprint 7', '2025-09-30', 50, 40),
    (1, 'Sprint 8', '2025-10-28', 50, 38),
    (1, 'Sprint 9', '2025-11-25', 48, 42),
    (1, 'Sprint 10', '2025-12-23', 48, 40),
    (1, 'Sprint 11', '2026-01-20', 48, 38),
    (1, 'Sprint 12', '2026-02-17', 45, 40),
    (1, 'Sprint 13', '2026-03-17', 45, 38),
    (1, 'Sprint 14', '2026-04-14', 45, 35),
    (1, 'Sprint 15', '2026-05-12', 45, 36),
    (1, 'Sprint 16', '2026-06-09', 42, 33),
    (1, 'Sprint 17', '2026-07-07', 42, 30),
    (1, 'Sprint 18', '2026-08-04', 40, 33),
    # CMTT (id=2) - moderate velocity
    (2, 'Sprint 1', '2025-06-15', 40, 38),
    (2, 'Sprint 2', '2025-07-13', 40, 37),
    (2, 'Sprint 3', '2025-08-10', 42, 40),
    (2, 'Sprint 4', '2025-09-07', 42, 38),
    (2, 'Sprint 5', '2025-10-05', 42, 36),
    (2, 'Sprint 6', '2025-11-02', 40, 38),
    (2, 'Sprint 7', '2025-11-30', 40, 35),
    (2, 'Sprint 8', '2025-12-28', 40, 37),
    (2, 'Sprint 9', '2026-01-25', 40, 36),
    (2, 'Sprint 10', '2026-02-22', 40, 34),
    (2, 'Sprint 11', '2026-03-22', 38, 35),
    (2, 'Sprint 12', '2026-04-19', 38, 33),
    (2, 'Sprint 13', '2026-05-17', 38, 34),
    (2, 'Sprint 14', '2026-06-14', 38, 32),
    (2, 'Sprint 15', '2026-07-12', 38, 35),
    (2, 'Sprint 16', '2026-08-09', 38, 33),
    # GDP (id=3) - healthy velocity
    (3, 'Sprint 1', '2025-09-15', 35, 34),
    (3, 'Sprint 2', '2025-10-13', 35, 35),
    (3, 'Sprint 3', '2025-11-10', 38, 37),
    (3, 'Sprint 4', '2025-12-08', 38, 38),
    (3, 'Sprint 5', '2026-01-05', 38, 36),
    (3, 'Sprint 6', '2026-02-02', 40, 39),
    (3, 'Sprint 7', '2026-03-02', 40, 40),
    (3, 'Sprint 8', '2026-03-30', 40, 38),
    (3, 'Sprint 9', '2026-04-27', 40, 41),
    (3, 'Sprint 10', '2026-05-25', 40, 39),
    (3, 'Sprint 11', '2026-06-22', 40, 40),
    (3, 'Sprint 12', '2026-07-20', 40, 38),
    (3, 'Sprint 13', '2026-08-17', 40, 39),
    # RRRT (id=4) - declining slightly
    (4, 'Sprint 1', '2025-07-15', 35, 33),
    (4, 'Sprint 2', '2025-08-12', 35, 32),
    (4, 'Sprint 3', '2025-09-09', 35, 34),
    (4, 'Sprint 4', '2025-10-07', 35, 30),
    (4, 'Sprint 5', '2025-11-04', 35, 32),
    (4, 'Sprint 6', '2025-12-02', 33, 30),
    (4, 'Sprint 7', '2025-12-30', 33, 28),
    (4, 'Sprint 8', '2026-01-27', 33, 30),
    (4, 'Sprint 9', '2026-02-24', 33, 29),
    (4, 'Sprint 10', '2026-03-24', 30, 27),
    (4, 'Sprint 11', '2026-04-21', 30, 28),
    (4, 'Sprint 12', '2026-05-19', 30, 26),
    (4, 'Sprint 13', '2026-06-16', 30, 25),
    (4, 'Sprint 14', '2026-07-14', 30, 27),
    (4, 'Sprint 15', '2026-08-11', 28, 24),
]

for row in velocity_data:
    cur.execute(
        "INSERT INTO sprint_velocity (project_id, sprint_name, sprint_end_date, committed_points, completed_points) VALUES (%s, %s, %s, %s, %s)",
        row
    )
print(f"Inserted {len(velocity_data)} sprint_velocity rows")

cur.close()
conn.close()
print("Done!")
