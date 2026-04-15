from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import jwt

from backend.database import get_db
from backend.models.user import User
from backend.config import GOOGLE_CLIENT_ID, ADMIN_EMAIL, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def create_jwt_token(user_data: dict) -> str:
    """Create a JWT token for session management."""
    payload = {
        "sub": str(user_data["id"]),
        "email": user_data["email"],
        "role": user_data["role"],
        "name": user_data.get("name", ""),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> dict:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    token: str = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to get the current authenticated user."""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_jwt_token(token)
    user_id = int(payload["sub"])

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/google")
async def google_login(request_body: dict, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user with Google ID token.
    Frontend sends the credential (ID token) from Google Sign-In.
    """
    credential = request_body.get("credential")
    if not credential:
        raise HTTPException(status_code=400, detail="No credential provided")

    try:
        # Verify the Google ID token
        idinfo = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )

        email = idinfo.get("email")
        name = idinfo.get("name", "")

        if not email:
            raise HTTPException(status_code=400, detail="Email not found in token")

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")

    # Check if user exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Determine role
    role = "admin" if email.lower() == ADMIN_EMAIL.lower() else "hospital"

    if user:
        # Update name if changed
        if user.name != name:
            user.name = name
        # Update role if admin email changed
        if user.role != role:
            user.role = role
        await db.commit()
        await db.refresh(user)
    else:
        # Create new user
        user = User(email=email, name=name, role=role)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Create JWT session token
    token = create_jwt_token(user.to_dict())

    return JSONResponse(content={
        "token": token,
        "user": user.to_dict(),
    })


@router.get("/me")
async def get_me(authorization: str = Header(default=""), db: AsyncSession = Depends(get_db)):
    """Get current user info from JWT token in Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")
    payload = verify_jwt_token(token)
    user_id = int(payload["sub"])

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {"user": user.to_dict()}


@router.get("/admin/hospitals")
async def list_hospitals(authorization: str = Header(default=""), db: AsyncSession = Depends(get_db)):
    """List all registered hospitals (admin only)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")
    payload = verify_jwt_token(token)
    
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(select(User).where(User.role == "hospital").order_by(User.created_at.desc()))
    hospitals = result.scalars().all()
    
    return {"hospitals": [h.to_dict() for h in hospitals]}


@router.delete("/admin/hospitals/{user_id}")
async def delete_hospital(user_id: int, authorization: str = Header(default=""), db: AsyncSession = Depends(get_db)):
    """Delete a hospital and all their weight files (admin only)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")
    payload = verify_jwt_token(token)
    
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Hospital not found")

    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin user")

    # Delete weight files from disk
    from backend.models.weight import Weight
    import os
    
    result = await db.execute(select(Weight).where(Weight.user_id == user_id))
    weights = result.scalars().all()
    for w in weights:
        if os.path.exists(w.file_path):
            try:
                os.remove(w.file_path)
            except Exception:
                pass

    # Weights will be deleted via cascade or manual if not set up
    # In my case, I'll delete them manually just to be safe if cascade isn't configured
    from sqlalchemy import delete
    await db.execute(delete(Weight).where(Weight.user_id == user_id))
    await db.execute(delete(User).where(User.id == user_id))
    
    await db.commit()
    return {"message": f"Hospital {user.email} and all associated data deleted successfully"}
