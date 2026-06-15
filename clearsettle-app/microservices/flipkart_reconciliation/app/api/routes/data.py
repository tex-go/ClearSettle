"""
GET /data/orders        — browse orders_etl (latest batch)
GET /data/fees          — browse fees_etl (latest batch)
GET /data/settlements   — browse settlements_etl (latest batch)
GET /data/batches       — list all batches with row counts and upload times
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.etl import FeesEtl, OrdersEtl, SettlementsEtl

router = APIRouter()


def _row(obj, cols) -> dict:
    return {c.key: (str(getattr(obj, c.key)) if getattr(obj, c.key) is not None else None)
            for c in cols}


async def _latest_batch_id(session: AsyncSession, model) -> str | None:
    result = await session.execute(
        select(model.batch_id)
        .where(model.is_valid.is_(True))
        .order_by(model.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return str(row) if row else None


@router.get("/batches")
async def list_batches(session: AsyncSession = Depends(get_session)):
    """Return all batches for all three tables with row counts."""
    out = {}
    for label, model in [("orders", OrdersEtl), ("fees", FeesEtl), ("settlements", SettlementsEtl)]:
        rows = (await session.execute(
            select(
                model.batch_id,
                func.count().label("row_count"),
                func.min(model.created_at).label("uploaded_at"),
            )
            .group_by(model.batch_id)
            .order_by(func.min(model.created_at).desc())
        )).all()
        out[label] = [
            {
                "batch_id": str(r.batch_id),
                "row_count": r.row_count,
                "uploaded_at": str(r.uploaded_at),
            }
            for r in rows
        ]
    return out


@router.get("/orders")
async def browse_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    batch_id: str | None = Query(None, description="Filter by batch_id; defaults to latest"),
    search: str | None = Query(None, description="Search order_item_id, order_id or sku"),
    session: AsyncSession = Depends(get_session),
):
    bid = batch_id or await _latest_batch_id(session, OrdersEtl)
    if not bid:
        return {"batch_id": None, "total": 0, "page": page, "data": []}

    stmt = select(OrdersEtl).where(
        OrdersEtl.batch_id == bid,
        OrdersEtl.is_valid.is_(True),
    )
    if search:
        q = f"%{search.lower()}%"
        stmt = stmt.where(
            (func.lower(OrdersEtl.order_item_id).like(q))
            | (func.lower(OrdersEtl.order_id).like(q))
            | (func.lower(OrdersEtl.sku).like(q))
        )

    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows  = (await session.execute(stmt.order_by(OrdersEtl.id).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    cols  = OrdersEtl.__table__.columns

    return {
        "batch_id": bid,
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [_row(r, cols) for r in rows],
    }


@router.get("/fees")
async def browse_fees(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    batch_id: str | None = Query(None),
    search: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    bid = batch_id or await _latest_batch_id(session, FeesEtl)
    if not bid:
        return {"batch_id": None, "total": 0, "page": page, "data": []}

    stmt = select(FeesEtl).where(FeesEtl.batch_id == bid, FeesEtl.is_valid.is_(True))
    if search:
        q = f"%{search.lower()}%"
        stmt = stmt.where(
            (func.lower(FeesEtl.order_item_id).like(q))
            | (func.lower(FeesEtl.fee_name).like(q))
        )

    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows  = (await session.execute(stmt.order_by(FeesEtl.id).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    cols  = FeesEtl.__table__.columns

    return {"batch_id": bid, "total": total, "page": page, "page_size": page_size, "data": [_row(r, cols) for r in rows]}


@router.get("/settlements")
async def browse_settlements(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    batch_id: str | None = Query(None),
    search: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    bid = batch_id or await _latest_batch_id(session, SettlementsEtl)
    if not bid:
        return {"batch_id": None, "total": 0, "page": page, "data": []}

    stmt = select(SettlementsEtl).where(SettlementsEtl.batch_id == bid, SettlementsEtl.is_valid.is_(True))
    if search:
        q = f"%{search.lower()}%"
        stmt = stmt.where(
            (func.lower(SettlementsEtl.order_item_id).like(q))
            | (func.lower(SettlementsEtl.order_id).like(q))
            | (func.lower(SettlementsEtl.sku).like(q))
        )

    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows  = (await session.execute(stmt.order_by(SettlementsEtl.id).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    cols  = SettlementsEtl.__table__.columns

    return {"batch_id": bid, "total": total, "page": page, "page_size": page_size, "data": [_row(r, cols) for r in rows]}
