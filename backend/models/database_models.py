"""
SQLAlchemy ORM models for the Project Intelligence Hub.

Defines the Project and Files tables matching the PostgreSQL schema
specified in the design document.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from db.database import Base


class Project(Base):
    """
    Represents a single project in the system.
    Only one project exists at a time (single-project model).
    """

    __tablename__ = "project"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to files
    files = relationship("File", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"


class File(Base):
    """
    Represents an uploaded file associated with a project.
    Stores metadata about the file including its processing status.
    """

    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    category = Column(String(100), nullable=False)
    file_path = Column(String(500), nullable=False)
    chunk_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    project_id = Column(Integer, ForeignKey("project.id", ondelete="CASCADE"), nullable=False)

    # Relationship back to project
    project = relationship("Project", back_populates="files")

    def __repr__(self):
        return f"<File(id={self.id}, file_name='{self.file_name}', type='{self.file_type}')>"
