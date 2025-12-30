"""Export API endpoints - Export data to Google Sheets"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
import logging

from backend.database.connection import get_db
from backend.database.repositories.transaction_repo import TransactionRepository
from backend.database.models import Owner, Institution

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory export job tracker
export_jobs = {}


def export_to_sheets_task(job_id: str, owner_id: Optional[int], institution_id: Optional[int],
                          from_date: Optional[date], to_date: Optional[date]):
    """Background task to export transactions to Google Sheets"""
    try:
        export_jobs[job_id]['status'] = 'processing'
        export_jobs[job_id]['started_at'] = datetime.now().isoformat()

        # Import required modules
        from backend.database.connection import get_db_context
        from src.core.writer import SheetsWriter
        from src.connectors.google_sheets import GoogleSheetsConnector
        from src.models.transaction import Transaction
        import yaml

        # Load settings to get spreadsheet ID
        with open('config/settings.yaml', 'r', encoding='utf-8') as f:
            settings = yaml.safe_load(f)

        spreadsheet_id = settings['google_sheets']['master_sheet_id']

        # Read transactions from database
        with get_db_context() as db:
            repo = TransactionRepository(db)
            transactions, total = repo.get_all(
                skip=0,
                limit=10000,  # Export all transactions
                owner_id=owner_id,
                institution_id=institution_id,
                from_date=from_date,
                to_date=to_date,
                sort_by='date',
                sort_order='asc'
            )

            export_jobs[job_id]['total_transactions'] = total

            # Convert SQLAlchemy models to Transaction objects
            transaction_objects = []
            for txn in transactions:
                # Create Transaction object from database row
                t = Transaction(
                    transaction_id=txn.transaction_id,
                    date=txn.date,
                    amount=txn.amount,
                    currency=txn.currency,
                    amount_czk=txn.amount_czk,
                    exchange_rate=txn.exchange_rate,
                    description=txn.description,
                    counterparty_account=txn.counterparty_account,
                    counterparty_name=txn.counterparty_name,
                    counterparty_bank=txn.counterparty_bank,
                    variable_symbol=txn.variable_symbol,
                    constant_symbol=txn.constant_symbol,
                    specific_symbol=txn.specific_symbol,
                    transaction_type=txn.transaction_type,
                    note=txn.note,
                    category_tier1=txn.category_tier1,
                    category_tier2=txn.category_tier2,
                    category_tier3=txn.category_tier3,
                    is_internal_transfer=txn.is_internal_transfer,
                    categorization_source=txn.categorization_source,
                    ai_confidence=txn.ai_confidence
                )

                # Add metadata fields
                if txn.owner:
                    t.owner = txn.owner.name
                if txn.institution:
                    t.institution = txn.institution.name
                if txn.account:
                    t.account = txn.account.account_number

                t.source_file = txn.source_file
                t.processed_date = txn.processed_date

                transaction_objects.append(t)

        # Get credentials paths from settings
        credentials_path = settings['google_drive']['credentials_path']
        token_path = settings['google_drive']['token_path']
        tab_name = settings['google_sheets'].get('transactions_tab', 'Transactions')

        # Initialize and authenticate Google Sheets connector
        logger.info("Initializing Google Sheets connector...")
        sheets_connector = GoogleSheetsConnector(credentials_path, token_path)
        if not sheets_connector.authenticate():
            raise Exception("Failed to authenticate with Google Sheets")

        # Initialize writer with spreadsheet ID
        writer = SheetsWriter(sheets_connector, spreadsheet_id)

        # Write to Google Sheets (overwrite mode to sync)
        logger.info(f"Exporting {len(transaction_objects)} transactions to Google Sheets (tab: {tab_name})...")
        success = writer.write_transactions(transaction_objects, tab_name=tab_name, mode='overwrite')

        if success:
            export_jobs[job_id]['exported_count'] = len(transaction_objects)
            export_jobs[job_id]['status'] = 'completed'
            export_jobs[job_id]['completed_at'] = datetime.now().isoformat()
            export_jobs[job_id]['message'] = f"Successfully exported {len(transaction_objects)} transactions to Google Sheets"
            logger.info(f"Export job {job_id} completed: {len(transaction_objects)} transactions exported")
        else:
            raise Exception("Failed to write transactions to Google Sheets")

    except Exception as e:
        logger.error(f"Error exporting to Google Sheets: {e}")
        import traceback
        logger.error(traceback.format_exc())

        export_jobs[job_id]['status'] = 'failed'
        export_jobs[job_id]['error'] = str(e)
        export_jobs[job_id]['completed_at'] = datetime.now().isoformat()


@router.post("/export/sheets")
async def export_transactions_to_sheets(
    background_tasks: BackgroundTasks,
    owner: Optional[str] = None,
    institution: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Export transactions from SQLite database to Google Sheets

    Args:
        owner: Filter by owner name (optional)
        institution: Filter by institution name (optional)
        from_date: Filter transactions from this date (optional)
        to_date: Filter transactions to this date (optional)

    Returns:
        Job ID for tracking export status
    """
    try:
        # Convert owner/institution names to IDs
        owner_id = None
        if owner:
            owner_obj = db.query(Owner).filter(Owner.name == owner).first()
            if not owner_obj:
                raise HTTPException(status_code=400, detail=f"Owner '{owner}' not found")
            owner_id = owner_obj.id

        institution_id = None
        if institution:
            inst_obj = db.query(Institution).filter(Institution.name == institution).first()
            if not inst_obj:
                raise HTTPException(status_code=400, detail=f"Institution '{institution}' not found")
            institution_id = inst_obj.id

        # Create export job
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_id = f"export_{timestamp}"

        export_jobs[job_id] = {
            'id': job_id,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'owner': owner,
            'institution': institution,
            'from_date': from_date.isoformat() if from_date else None,
            'to_date': to_date.isoformat() if to_date else None,
            'total_transactions': 0,
            'exported_count': 0
        }

        # Start background export
        background_tasks.add_task(
            export_to_sheets_task,
            job_id,
            owner_id,
            institution_id,
            from_date,
            to_date
        )

        return JSONResponse(
            status_code=202,
            content={
                'job_id': job_id,
                'message': 'Export to Google Sheets started',
                'status': 'pending'
            }
        )

    except Exception as e:
        logger.error(f"Error starting export: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/jobs/{job_id}")
async def get_export_job_status(job_id: str):
    """Get status of an export job"""
    if job_id not in export_jobs:
        raise HTTPException(status_code=404, detail="Export job not found")

    return export_jobs[job_id]


@router.get("/export/jobs")
async def list_export_jobs(limit: int = 20):
    """Get list of recent export jobs"""
    jobs = list(export_jobs.values())
    jobs.sort(key=lambda x: x['created_at'], reverse=True)
    return jobs[:limit]
