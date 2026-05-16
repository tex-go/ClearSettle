import bcrypt
from datetime import datetime, timedelta
from jose import JWTError, jwt

SECRET_KEY = "clearsettle-secret-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

# rounds=4 for fast demo startup
_DEMO_HASH = bcrypt.hashpw(b"demo123", bcrypt.gensalt(rounds=4))

DEMO_USER = {
    "id": 1,
    "email": "demo@clearsettle.in",
    "name": "Ranjith Kumar",
    "company": "Tirupur Exports Pvt. Ltd.",
    "gstin": "33ABCDE1234F1Z5",
    "city": "Tirupur, Tamil Nadu",
    "role": "admin",
    "hashed_password": _DEMO_HASH,
}


def verify_password(plain: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed)


def create_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
