from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import DEMO_USER, verify_password, create_token
from app.core.deps import get_db_optional, get_current_user

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(req: LoginRequest, db: Session | None = Depends(get_db_optional)):
    if db is not None:
        # DB-backed auth
        from app.db.models import User
        import bcrypt
        user = db.query(User).filter(User.email == req.email, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        pw_match = bcrypt.checkpw(
            req.password.encode("utf-8"),
            user.hashed_password.encode("utf-8"),
        )
        if not pw_match:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_token({"sub": user.email, "id": str(user.id)})
        company = user.companies[0] if user.companies else None
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "company": company.name if company else None,
                "gstin": company.gstin if company else None,
                "city": company.city if company else None,
            },
        }

    # No DB — demo mode
    if req.email != DEMO_USER["email"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(req.password, DEMO_USER["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token({"sub": DEMO_USER["email"], "id": DEMO_USER["id"]})
    user = {k: v for k, v in DEMO_USER.items() if k != "hashed_password"}
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    if isinstance(current_user, dict):
        return {k: v for k, v in current_user.items() if k != "hashed_password"}
    # ORM object
    company = current_user.companies[0] if current_user.companies else None
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "company": company.name if company else None,
        "city": company.city if company else None,
    }
