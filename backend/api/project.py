"""
Project API endpoints for the Project Intelligence Hub.

Handles project creation, retrieval, and full reset operations.
"""

import os
import shutil

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.chroma_client import delete_all_embeddings
from db.database import get_db
from models.database_models import Project, File
from models.schemas import ProjectCreate, ProjectResponse

router = APIRouter()

# File storage directory (relative to backend working directory)
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")


@router.post("/project", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project_data: ProjectCreate, db: Session = Depends(get_db)):
    """
    Create a new project.

    - If the project name is empty or whitespace-only, returns 400.
    - If a project already exists, returns 409 with existing project info.
    """
    # Validate project name is not empty or whitespace
    if not project_data.name or not project_data.name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project name cannot be empty or whitespace only.",
        )

    # Check if a project already exists (single-project model)
    existing_project = db.query(Project).first()
    if existing_project:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A project already exists. Use the existing project or reset first.",
        )

    # Create the new project
    new_project = Project(
        name=project_data.name.strip(),
        description=project_data.description,
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return new_project


@router.get("/project", response_model=ProjectResponse)
def get_project(db: Session = Depends(get_db)):
    """
    Retrieve the current project details.

    Returns 404 if no project exists.
    """
    project = db.query(Project).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No project exists. Create a project first.",
        )

    return project


@router.delete("/project/reset", status_code=status.HTTP_200_OK)
def reset_project(db: Session = Depends(get_db)):
    """
    Full project reset: deletes all files from storage, all chunks from
    ChromaDB, all metadata from PostgreSQL, and the project record itself.

    Returns a confirmation message indicating the application is ready
    for a new project.
    """
    project = db.query(Project).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No project exists to reset.",
        )

    # 1. Delete all uploaded files from storage
    if os.path.exists(UPLOAD_DIR):
        shutil.rmtree(UPLOAD_DIR)
        os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 2. Delete all chunks from ChromaDB
    delete_all_embeddings()

    # 3. Delete all file metadata and the project record from PostgreSQL
    # CASCADE on the foreign key will remove associated file records
    db.delete(project)
    db.commit()

    return {"detail": "Project reset successfully. All data has been deleted."}
