"""
Admin router — ClearSettle internal dashboard.

Endpoints (all require admin or superadmin role):
  GET  /admin/stats               — platform-wide summary KPIs
  GET  /admin/sellers             — paginated list of all sellers
  GET  /admin/sellers/{seller_id} — single seller detail + uploads
"""
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db

router = APIRouter()


# ── Auth guard ────────────────────────────────────────────────────────────────

async def require_admin(current_user=Depends(get_current_user)):
    role = (
        current_user.role
        if hasattr(current_user, "role")
        else current_user.get("role", "")
    )
    if role not in ("admin", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ── Helpers ───────────────────────────────────────────────────────────────────

def _company_dict(c) -> dict:
    if c is None:
        return {}
    return {
        "id":                     str(c.id),
        "name":                   c.name,
        "gstin":                  c.gstin,
        "pan":                    c.pan,
        "phone":                  c.phone,
        "state":                  c.state,
        "city":                   c.city,
        "pincode":                c.pincode,
        "address":                c.address,
        "industry":               c.industry,
        "website":                c.website,
        "active_platforms":       c.active_platforms or [],
        "monthly_gmv_range":      c.monthly_gmv_range,
        "bank_name":              c.bank_name,
        "registration_completed": c.registration_completed,
    }


# ── Platform-wide stats ───────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models import User, Company
    from app.db.models.flipkart_report import FlipkartReport, FlipkartSummary, FlipkartReconIssue

    since_30d = datetime.utcnow() - timedelta(days=30)

    # Total sellers
    total_sellers = (await db.execute(
        select(func.count(User.id)).where(
            User.role.in_(["seller", "admin"]),
            User.deleted_at.is_(None),
        )
    )).scalar_one()

    # Sellers active in last 30 days (registered in 30d as proxy)
    active_30d = (await db.execute(
        select(func.count(User.id)).where(
            User.role.in_(["seller", "admin"]),
            User.deleted_at.is_(None),
            User.created_at >= since_30d,
        )
    )).scalar_one()

    # Total Flipkart report uploads
    total_uploads = (await db.execute(
        select(func.count(FlipkartReport.id))
    )).scalar_one()

    # Total GMV processed
    total_gmv = (await db.execute(
        select(func.coalesce(func.sum(FlipkartSummary.gross_sales), 0))
    )).scalar_one()

    # Total money leak detected (absolute value of negative variances)
    total_leak = (await db.execute(
        select(func.coalesce(
            func.sum(func.abs(FlipkartReconIssue.variance)),
            0,
        )).where(FlipkartReconIssue.variance < 0)
    )).scalar_one()

    # Platform distribution
    companies = (await db.execute(
        select(Company.active_platforms).where(Company.active_platforms.isnot(None))
    )).scalars().all()

    platform_count: dict[str, int] = {}
    for platforms in companies:
        for p in (platforms or []):
            platform_count[p] = platform_count.get(p, 0) + 1

    platform_distribution = sorted(
        [{"platform": k, "seller_count": v} for k, v in platform_count.items()],
        key=lambda x: x["seller_count"],
        reverse=True,
    )

    # Recent signups (last 30 days, by day)
    signups_raw = (await db.execute(
        select(
            func.date(User.created_at).label("date"),
            func.count(User.id).label("count"),
        )
        .where(
            User.role.in_(["seller", "admin"]),
            User.deleted_at.is_(None),
            User.created_at >= since_30d,
        )
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    )).all()
    signups_last_30d = [{"date": str(r.date), "count": r.count} for r in signups_raw]

    return {
        "total_sellers":           total_sellers,
        "active_sellers_30d":      active_30d,
        "total_report_uploads":    total_uploads,
        "total_gmv_processed":     float(total_gmv),
        "total_money_leak_detected": float(total_leak),
        "platform_distribution":   platform_distribution,
        "signups_last_30d":        signups_last_30d,
    }


# ── Seller list ───────────────────────────────────────────────────────────────

@router.get("/sellers")
async def list_sellers(
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    platform: str | None = None,
):
    from app.db.models import User, Company
    from app.db.models.flipkart_report import FlipkartReport

    # Build base query
    q = (
        select(User)
        .options(selectinload(User.companies))
        .where(
            User.role.in_(["seller", "admin"]),
            User.deleted_at.is_(None),
        )
        .order_by(User.created_at.desc())
    )
    if search:
        term = f"%{search.lower()}%"
        q = q.where(
            (func.lower(User.name).like(term)) |
            (func.lower(User.email).like(term))
        )

    total = (await db.execute(
        select(func.count()).select_from(q.subquery())
    )).scalar_one()

    users = (await db.execute(q.offset((page - 1) * limit).limit(limit))).scalars().all()

    rows = []
    for u in users:
        company = u.companies[0] if u.companies else None

        # Filter by platform if requested
        if platform:
            platforms = (company.active_platforms or []) if company else []
            if platform not in platforms:
                continue

        upload_count = (await db.execute(
            select(func.count(FlipkartReport.id)).where(
                FlipkartReport.company_id == company.id if company else False
            )
        )).scalar_one() if company else 0

        last_upload = (await db.execute(
            select(func.max(FlipkartReport.uploaded_at)).where(
                FlipkartReport.company_id == company.id if company else False
            )
        )).scalar_one() if company else None

        rows.append({
            "id":           str(u.id),
            "name":         u.name,
            "email":        u.email,
            "phone":        getattr(u, "phone", None),
            "role":         u.role,
            "is_active":    u.is_active,
            "created_at":   u.created_at.isoformat() if u.created_at else None,
            "company":      _company_dict(company),
            "upload_count": upload_count,
            "last_upload_at": last_upload.isoformat() if last_upload else None,
        })

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, (total + limit - 1) // limit),
        "sellers": rows,
    }


# ── Single seller detail ──────────────────────────────────────────────────────

@router.get("/sellers/{seller_id}")
async def get_seller(
    seller_id: str,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models import User
    from app.db.models.flipkart_report import FlipkartReport, FlipkartSummary

    result = await db.execute(
        select(User)
        .options(selectinload(User.companies))
        .where(User.id == seller_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Seller not found")

    company = user.companies[0] if user.companies else None

    # Flipkart uploads
    uploads_raw = (await db.execute(
        select(FlipkartReport)
        .where(FlipkartReport.company_id == company.id)
        .order_by(FlipkartReport.uploaded_at.desc())
        .limit(20)
    )).scalars().all() if company else []

    # Aggregate summary
    agg = (await db.execute(
        select(
            func.coalesce(func.sum(FlipkartSummary.gross_sales), 0).label("total_gmv"),
            func.coalesce(func.sum(FlipkartSummary.net_earnings), 0).label("total_earnings"),
            func.coalesce(func.sum(FlipkartSummary.total_orders), 0).label("total_orders"),
            func.coalesce(func.sum(FlipkartSummary.amount_settled), 0).label("amount_settled"),
            func.coalesce(func.sum(FlipkartSummary.amount_pending), 0).label("amount_pending"),
        ).where(FlipkartSummary.company_id == company.id)
    )).one() if company else None

    return {
        "id":      str(user.id),
        "name":    user.name,
        "email":   user.email,
        "phone":   getattr(user, "phone", None),
        "role":    user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "company": _company_dict(company),
        "aggregates": {
            "total_gmv":      float(agg.total_gmv) if agg else 0,
            "total_earnings": float(agg.total_earnings) if agg else 0,
            "total_orders":   int(agg.total_orders) if agg else 0,
            "amount_settled": float(agg.amount_settled) if agg else 0,
            "amount_pending": float(agg.amount_pending) if agg else 0,
        } if agg else {},
        "flipkart_uploads": [
            {
                "id":            str(r.id),
                "original_name": r.original_name,
                "status":        r.status,
                "report_period": r.report_period,
                "row_count_orders": r.row_count_orders,
                "uploaded_at":   r.uploaded_at.isoformat() if r.uploaded_at else None,
                "processed_at":  r.processed_at.isoformat() if r.processed_at else None,
            }
            for r in uploads_raw
        ],
    }
