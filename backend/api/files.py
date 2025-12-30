"""File Upload and Processing API"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, List
import os
import shutil
from pathlib import Path
from datetime import datetime
import logging

from backend.schemas.file_processing import (
    FileProcessingJob,
    FileProcessingStatus,
    InstitutionInfo
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Storage paths
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# In-memory job tracker (replace with database in production)
processing_jobs = {}


def get_available_institutions() -> List[InstitutionInfo]:
    """Get list of configured institutions from config files"""
    from pathlib import Path
    import yaml

    institutions = []
    inst_dir = Path("config/institutions")

    if inst_dir.exists():
        for config_file in inst_dir.glob("*.yaml"):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)

                institutions.append(InstitutionInfo(
                    id=config_file.stem,
                    name=config.get('institution', {}).get('name', config_file.stem),
                    filename_patterns=config.get('file_detection', {}).get('filename_patterns', []),
                    file_format=config.get('format', {}).get('type', 'csv')
                ))
            except Exception as e:
                logger.error(f"Error loading institution config {config_file}: {e}")
                continue

    return institutions


def process_file_task(job_id: str, file_path: str, institution: str):
    """Background task to process uploaded file"""
    try:
        # Update job status
        processing_jobs[job_id]['status'] = 'processing'
        processing_jobs[job_id]['started_at'] = datetime.now().isoformat()

        # Import processing modules
        from src.core.parser import FileParser
        from src.core.normalizer import DataNormalizer
        from src.utils.categorizer import get_categorizer
        from src.core.database_writer import DatabaseWriter

        # Load institution config
        config_path = f"config/institutions/{institution}.yaml"
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            inst_config = yaml.safe_load(f)

        # Parse file
        parser = FileParser(inst_config)
        original_filename = processing_jobs[job_id]['filename']
        raw_data = parser.parse_file(file_path, original_filename=original_filename)

        processing_jobs[job_id]['parsed_rows'] = len(raw_data)

        # Normalize data
        from src.utils.currency import CurrencyConverter
        currency_converter = CurrencyConverter()
        normalizer = DataNormalizer(currency_converter, inst_config)
        # source_file is just for metadata in the transaction, use the saved file path
        transactions = normalizer.normalize_transactions(raw_data, file_path)

        processing_jobs[job_id]['normalized_rows'] = len(transactions)

        # Categorize transactions
        categorizer = get_categorizer()
        from src.utils.logger import get_logger
        logger = get_logger()

        # Get disable_ai_categorization flag from job
        disable_ai = processing_jobs[job_id].get('disable_ai_categorization', False)
        ai_status = "DISABLED" if disable_ai else "ENABLED"
        logger.info(f"===== Starting categorization of {len(transactions)} transactions (AI: {ai_status}) =====")

        for idx, txn in enumerate(transactions):
            txn_dict = txn.to_dict()
            logger.info(f"[{idx+1}/{len(transactions)}] Processing: desc={txn_dict.get('description')}, type={txn_dict.get('type')}, counterparty={txn_dict.get('counterparty_name')}")
            tier1, tier2, tier3, owner, is_internal, source, confidence = categorizer.categorize(
                txn_dict,
                disable_ai=disable_ai
            )
            logger.info(f"[{idx+1}/{len(transactions)}] Result: Tier1={tier1}, Tier2={tier2}, Tier3={tier3}, internal={is_internal}, source={source}")
            txn.category_tier1 = tier1
            txn.category_tier2 = tier2
            txn.category_tier3 = tier3
            txn.is_internal_transfer = is_internal
            if owner and owner != 'Unknown':
                txn.owner = owner
            txn.categorization_source = source
            if confidence:
                txn.ai_confidence = confidence
        logger.info(f"===== Completed categorization of {len(transactions)} transactions =====")

        # Write to SQLite database as PRIMARY destination
        logger.info("===== Starting write to SQLite database =====")

        override_existing = processing_jobs[job_id]['override_existing']
        mode = "overwrite" if override_existing else "append"
        logger.info(f"Writing {len(transactions)} transactions to database (mode: {mode})")

        # Use DatabaseWriter to write to SQLite
        db_writer = DatabaseWriter()
        result = db_writer.write_transactions(transactions, mode=mode)

        # Extract statistics from result
        inserted = result.get('added', 0)
        updated = result.get('updated', 0)
        skipped = result.get('skipped', 0)
        total = result.get('total', 0)

        logger.info(f"Database write complete: {inserted} added, {updated} updated, {skipped} skipped")

        processing_jobs[job_id]['inserted_rows'] = inserted
        processing_jobs[job_id]['updated_rows'] = updated

        # Build detailed message
        msg_parts = []
        if inserted > 0:
            msg_parts.append(f"{inserted} new")
        if updated > 0:
            msg_parts.append(f"{updated} updated")
        if skipped > 0:
            msg_parts.append(f"{skipped} skipped (duplicates)")

        if msg_parts:
            msg = f"Processed {total} transactions: " + ", ".join(msg_parts)
        else:
            msg = "No transactions to process"

        processing_jobs[job_id]['message'] = msg

        success = True  # Database write always returns True if it doesn't throw exception

        processing_jobs[job_id]['status'] = 'completed'
        processing_jobs[job_id]['completed_at'] = datetime.now().isoformat()

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        import traceback
        logger.error(traceback.format_exc())

        processing_jobs[job_id]['status'] = 'failed'
        processing_jobs[job_id]['error'] = str(e)
        processing_jobs[job_id]['completed_at'] = datetime.now().isoformat()


@router.get("/institutions", response_model=List[InstitutionInfo])
async def list_institutions():
    """Get list of available institutions for file upload"""
    return get_available_institutions()


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    institution: str = Form(...),
    override_existing: bool = Form(False),
    disable_ai_categorization: bool = Form(False)
):
    """
    Upload and process a financial data file

    Args:
        file: The file to upload (CSV or XLSX)
        institution: Institution ID (e.g., 'csob', 'partners_bank', 'wise')
        override_existing: Whether to override existing transactions (default: False)
        disable_ai_categorization: Whether to disable AI categorization fallback (default: False)

    Returns:
        Job ID for tracking processing status
    """
    try:
        # Validate institution
        institutions = get_available_institutions()
        inst_ids = [i.id for i in institutions]
        if institution not in inst_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid institution '{institution}'. Available: {inst_ids}"
            )

        # Create unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = Path(file.filename).suffix
        safe_filename = f"{institution}_{timestamp}{file_ext}"
        file_path = UPLOAD_DIR / safe_filename

        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Create processing job
        job_id = f"job_{timestamp}_{institution}"
        processing_jobs[job_id] = {
            'id': job_id,
            'filename': file.filename,
            'saved_filename': safe_filename,
            'institution': institution,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'override_existing': override_existing,
            'disable_ai_categorization': disable_ai_categorization,
            'parsed_rows': 0,
            'normalized_rows': 0,
            'inserted_rows': 0,
            'updated_rows': 0
        }

        # Start background processing
        background_tasks.add_task(
            process_file_task,
            job_id,
            str(file_path),
            institution
        )

        return JSONResponse(
            status_code=202,
            content={
                'job_id': job_id,
                'message': 'File uploaded successfully, processing started',
                'status': 'pending'
            }
        )

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs", response_model=List[FileProcessingJob])
async def list_jobs(limit: int = 50):
    """Get list of recent processing jobs"""
    jobs = list(processing_jobs.values())
    jobs.sort(key=lambda x: x['created_at'], reverse=True)
    return jobs[:limit]


@router.get("/jobs/{job_id}", response_model=FileProcessingJob)
async def get_job_status(job_id: str):
    """Get status of a specific processing job"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return processing_jobs[job_id]


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a processing job from history"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = processing_jobs[job_id]

    # Delete uploaded file if it exists
    if 'saved_filename' in job:
        file_path = UPLOAD_DIR / job['saved_filename']
        if file_path.exists():
            file_path.unlink()

    del processing_jobs[job_id]

    return {'message': 'Job deleted successfully'}
