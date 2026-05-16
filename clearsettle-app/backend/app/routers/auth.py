from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.auth import DEMO_USER, verify_password, create_token

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(req: LoginRequest):
    if req.email != DEMO_USER["email"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(req.password, DEMO_USER["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token({"sub": DEMO_USER["email"], "id": DEMO_USER["id"]})
    user = {k: v for k, v in DEMO_USER.items() if k != "hashed_password"}
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me")
def me():
    return {k: v for k, v in DEMO_USER.items() if k != "hashed_password"}
