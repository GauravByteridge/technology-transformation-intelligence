"""Deterministic UUID generation for seed data.

Production models use uuid4() (random) as the default PK generator.
The seed script DOES NOT change production model defaults.

Instead, the seed generators explicitly assign UUIDs using UUID5
with a fixed namespace and deterministic names. This ensures:
- Repeated seed executions produce identical UUIDs
- Identical field values across runs
- Identical relationships (FKs match)
- Identical record counts

UUID5 is deterministic: uuid5(namespace, name) always produces the same UUID
for the same inputs.
"""

from uuid import UUID, uuid5

# Fixed namespace UUID for all seed data generation.
# This is arbitrary but must remain constant across executions.
SEED_NAMESPACE = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def deterministic_uuid(entity_type: str, *identifiers: str) -> UUID:
    """Generate a deterministic UUID for a seed entity.

    Args:
        entity_type: The entity domain (e.g., "project", "budget", "jira_issue")
        identifiers: One or more identifiers that uniquely identify this entity
                     within its type (e.g., project name, issue key)

    Returns:
        A deterministic UUID5 that is identical across repeated executions.

    Examples:
        deterministic_uuid("project", "Project Alpha")
        deterministic_uuid("jira_issue", "ALPHA", "ALPHA-001")
        deterministic_uuid("budget", "Project Alpha", "2025")
    """
    name = f"{entity_type}:{':'.join(identifiers)}"
    return uuid5(SEED_NAMESPACE, name)
