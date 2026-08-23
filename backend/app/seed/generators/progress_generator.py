"""Project progress snapshot seed generator.

Generates at least 6 project_progress_snapshots per project at regular
bi-weekly intervals showing planned versus actual progress over time.

Planned progress increases linearly from ~10% to ~85-100% over 6+ snapshots.
Actual progress tracks close to planned for healthy projects.

Project Alpha: the most recent snapshot has actual_progress_percentage
below planned_progress_percentage by >= 10 percentage points, representing
schedule delay.

Both percentages are constrained to 0-100 range.
"""

from datetime import date, timedelta
from uuid import UUID

from app.seed.deterministic import deterministic_uuid

# Number of snapshots per project (bi-weekly intervals).
SNAPSHOT_COUNT = 8

# Interval between snapshots in days (bi-weekly).
SNAPSHOT_INTERVAL_DAYS = 14

# Progress endpoints for linear planned progression.
PLANNED_START_PERCENTAGE = 10
PLANNED_END_PERCENTAGE = 92

# Hero project schedule delay: actual lags planned by this minimum gap
# in the most recent snapshot.
HERO_DELAY_MINIMUM_POINTS = 12


class ProgressSeedGenerator:
    """Generates project progress snapshot seed data.

    Produces at least 6 snapshots per project at bi-weekly intervals.
    Planned progress increases linearly. Actual progress varies based
    on project health profile.
    """

    def generate(self, project_ids_with_names: list[tuple[UUID, str]]) -> list[dict]:
        """Generate progress snapshot records for all projects.

        Args:
            project_ids_with_names: List of (project_id, project_name) tuples.

        Returns:
            List of progress snapshot dictionaries matching the
            ProjectProgressSnapshot model columns.
        """
        snapshots: list[dict] = []

        for project_idx, (project_id, project_name) in enumerate(project_ids_with_names):
            is_hero = project_name == "Project Alpha"
            project_snapshots = self._generate_project_snapshots(
                project_id=project_id,
                project_name=project_name,
                project_idx=project_idx,
                is_hero=is_hero,
            )
            snapshots.extend(project_snapshots)

        return snapshots

    def _generate_project_snapshots(
        self,
        project_id: UUID,
        project_name: str,
        project_idx: int,
        is_hero: bool,
    ) -> list[dict]:
        """Generate bi-weekly progress snapshots for a single project.

        Planned progress increases linearly from ~10% to ~92%.
        Actual progress behavior depends on project type:
        - Hero (Project Alpha): actual lags behind planned, widening gap
        - Healthy projects: actual tracks close to planned (±2 points)
        """
        snapshots: list[dict] = []
        today = date.today()

        # Start date: SNAPSHOT_COUNT intervals before today
        start_date = today - timedelta(days=(SNAPSHOT_COUNT - 1) * SNAPSHOT_INTERVAL_DAYS)

        for i in range(SNAPSHOT_COUNT):
            snapshot_date = start_date + timedelta(days=i * SNAPSHOT_INTERVAL_DAYS)

            planned = self._calculate_planned_progress(i, SNAPSHOT_COUNT)
            actual = self._calculate_actual_progress(
                snapshot_index=i,
                total_snapshots=SNAPSHOT_COUNT,
                planned=planned,
                project_idx=project_idx,
                is_hero=is_hero,
            )

            snapshot_id = deterministic_uuid(
                "progress_snapshot", project_name, str(i)
            )

            snapshots.append({
                "id": snapshot_id,
                "project_id": project_id,
                "snapshot_date": snapshot_date,
                "planned_progress_percentage": planned,
                "actual_progress_percentage": actual,
            })

        return snapshots

    def _calculate_planned_progress(self, snapshot_index: int, total_snapshots: int) -> int:
        """Calculate linearly increasing planned progress percentage.

        Returns a value that increases from PLANNED_START_PERCENTAGE
        to PLANNED_END_PERCENTAGE over the snapshot series.
        """
        if total_snapshots <= 1:
            return PLANNED_START_PERCENTAGE

        # Linear interpolation from start to end
        progress = PLANNED_START_PERCENTAGE + (
            (PLANNED_END_PERCENTAGE - PLANNED_START_PERCENTAGE)
            * snapshot_index
            / (total_snapshots - 1)
        )
        return self._clamp_percentage(int(round(progress)))

    def _calculate_actual_progress(
        self,
        snapshot_index: int,
        total_snapshots: int,
        planned: int,
        project_idx: int,
        is_hero: bool,
    ) -> int:
        """Calculate actual progress based on project profile.

        Hero project (Project Alpha): actual progressively lags behind planned,
        with the final snapshot showing a gap of >= 10 points.

        Healthy projects: actual tracks near planned with small deterministic
        variations (±2 points).
        """
        if is_hero:
            return self._calculate_hero_actual(snapshot_index, total_snapshots, planned)

        return self._calculate_healthy_actual(snapshot_index, planned, project_idx)

    def _calculate_hero_actual(
        self, snapshot_index: int, total_snapshots: int, planned: int
    ) -> int:
        """Calculate actual progress for the hero project (Project Alpha).

        The gap between planned and actual widens over time, ensuring the
        most recent snapshot has actual < planned by >= HERO_DELAY_MINIMUM_POINTS.
        Early snapshots start close to planned, then diverge.
        """
        # Gap grows linearly from 0 to HERO_DELAY_MINIMUM_POINTS over the series
        max_gap = HERO_DELAY_MINIMUM_POINTS + 3  # Slightly exceed minimum for clarity
        gap = int(round(max_gap * snapshot_index / max(total_snapshots - 1, 1)))

        actual = planned - gap
        return self._clamp_percentage(actual)

    def _calculate_healthy_actual(
        self, snapshot_index: int, planned: int, project_idx: int
    ) -> int:
        """Calculate actual progress for healthy/on-track projects.

        Actual tracks close to planned with small deterministic offsets.
        Some projects run slightly ahead, others slightly behind, but never
        more than a few points difference.
        """
        # Deterministic small offset based on project index and snapshot index
        # Creates variety without randomness
        offset_pattern = [0, 1, -1, 2, 0, -1, 1, 0]
        offset = offset_pattern[(project_idx + snapshot_index) % len(offset_pattern)]

        actual = planned + offset
        return self._clamp_percentage(actual)

    def _clamp_percentage(self, value: int) -> int:
        """Ensure percentage value is within 0-100 range."""
        return max(0, min(100, value))
