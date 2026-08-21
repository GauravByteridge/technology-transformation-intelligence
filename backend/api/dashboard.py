"""
Dashboard API endpoint for the Project Intelligence Hub.

Provides project overview statistics including file counts by type and category,
and the most recent file uploads.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.database import get_db
from models.database_models import File, Project
from models.schemas import DashboardStats, FileResponse

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(db: Session = Depends(get_db)):
    """
    Retrieve dashboard statistics for the current project.

    Returns project info, total file count, file distribution by type
    and category, and the 5 most recently uploaded files.

    Returns 404 if no project exists.
    """
    # Get the current project
    project = db.query(Project).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No project exists. Create a project first.",
        )

    # Calculate total file count
    total_files = db.query(func.count(File.id)).filter(File.project_id == project.id).scalar()

    # Calculate file counts grouped by type
    files_by_type_query = (
        db.query(File.file_type, func.count(File.id).label("count"))
        .filter(File.project_id == project.id)
        .group_by(File.file_type)
        .all()
    )
    files_by_type = [{"type": row.file_type, "count": row.count} for row in files_by_type_query]

    # Calculate file counts grouped by category
    files_by_category_query = (
        db.query(File.category, func.count(File.id).label("count"))
        .filter(File.project_id == project.id)
        .group_by(File.category)
        .all()
    )
    files_by_category = [
        {"category": row.category, "count": row.count} for row in files_by_category_query
    ]

    # Get 5 most recent files sorted by upload date descending
    recent_files_query = (
        db.query(File)
        .filter(File.project_id == project.id)
        .order_by(File.uploaded_at.desc())
        .limit(5)
        .all()
    )
    recent_files = [
        FileResponse(
            id=f.id,
            file_name=f.file_name,
            file_type=f.file_type,
            category=f.category,
            uploaded_at=f.uploaded_at,
            chunk_count=f.chunk_count,
        )
        for f in recent_files_query
    ]

    return DashboardStats(
        project_name=project.name,
        project_description=project.description,
        total_files=total_files,
        files_by_type=files_by_type,
        files_by_category=files_by_category,
        recent_files=recent_files,
    )
