from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.etl.ingestor import ingest_fees, ingest_orders, ingest_settlements
from app.etl.transformer import transform_fees, transform_orders, transform_settlements
from app.schemas.ingest import BatchResponse

router = APIRouter()

_ALLOWED_EXTENSIONS = (".xlsx", ".xls", ".csv")


def _check_extension(filename: str) -> None:
    if not any(filename.lower().endswith(ext) for ext in _ALLOWED_EXTENSIONS):
        raise HTTPException(400, "Only .xlsx, .xls, or .csv files are accepted")


@router.post("/orders", response_model=BatchResponse)
async def upload_orders(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    _check_extension(file.filename)
    content = await file.read()
    batch_id, count = await ingest_orders(session, content, file.filename)
    await transform_orders(session, batch_id)
    return BatchResponse(
        batch_id=batch_id,
        file_name=file.filename,
        report_type="orders",
        rows_ingested=count,
        uploaded_at=datetime.now(timezone.utc),
    )


@router.post("/fees", response_model=BatchResponse)
async def upload_fees(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    _check_extension(file.filename)
    content = await file.read()
    batch_id, count = await ingest_fees(session, content, file.filename)
    await transform_fees(session, batch_id)
    return BatchResponse(
        batch_id=batch_id,
        file_name=file.filename,
        report_type="fees",
        rows_ingested=count,
        uploaded_at=datetime.now(timezone.utc),
    )


@router.post("/settlements", response_model=BatchResponse)
async def upload_settlements(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    _check_extension(file.filename)
    content = await file.read()
    batch_id, count = await ingest_settlements(session, content, file.filename)
    await transform_settlements(session, batch_id)
    return BatchResponse(
        batch_id=batch_id,
        file_name=file.filename,
        report_type="settlements",
        rows_ingested=count,
        uploaded_at=datetime.now(timezone.utc),
    )
