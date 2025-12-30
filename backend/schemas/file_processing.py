"""Pydantic schemas for file processing"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class InstitutionInfo(BaseModel):
    """Information about a configured institution"""
    id: str
    name: str
    filename_patterns: List[str]
    file_format: str  # 'csv' or 'xlsx'


class FileProcessingJob(BaseModel):
    """File processing job status"""
    id: str
    filename: str
    saved_filename: str
    institution: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    override_existing: bool = False

    # Processing metrics
    parsed_rows: int = 0
    normalized_rows: int = 0
    inserted_rows: int = 0
    updated_rows: int = 0

    # Results
    message: Optional[str] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True


class FileProcessingStatus(BaseModel):
    """Current status of file processing"""
    job_id: str
    status: str
    progress_percent: Optional[int] = None
    current_step: Optional[str] = None
    message: Optional[str] = None
