import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.database import get_db
from backend.models.user import User
from backend.models.weight import Weight
from backend.routes.auth import verify_jwt_token
from backend.config import WEIGHTS_DIR

router = APIRouter(prefix="/api", tags=["Weights"])


async def get_authenticated_user(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and verify user from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")
    payload = verify_jwt_token(token)
    user_id = int(payload["sub"])

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/upload_weights")
async def upload_weights(
    file: UploadFile = File(...),
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Upload model weights (.pkl file only)."""
    # Authenticate
    user = await get_authenticated_user(authorization, db)

    # Only hospitals can upload
    if user.role != "hospital":
        raise HTTPException(status_code=403, detail="Only hospitals can upload weights")

    # Validate file type
    if not file.filename or not file.filename.endswith(".pkl"):
        raise HTTPException(
            status_code=400,
            detail="Only .pkl files are allowed. Please upload a pickle file containing model weights.",
        )

    # Create user-specific directory
    user_dir = os.path.join(WEIGHTS_DIR, str(user.id))
    os.makedirs(user_dir, exist_ok=True)

    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"weights_{timestamp}_{unique_id}.pkl"
    file_path = os.path.join(user_dir, filename)

    # Save file
    content = await file.read()
    file_size = len(content)

    with open(file_path, "wb") as f:
        f.write(content)

    # Record in database
    weight = Weight(
        user_id=user.id,
        file_path=file_path,
        original_filename=file.filename,
        file_size=file_size,
    )
    db.add(weight)
    await db.commit()
    await db.refresh(weight)

    return {
        "message": "Weights uploaded successfully",
        "weight": weight.to_dict(),
    }


@router.get("/weights")
async def list_weights(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    """List uploaded weights. Admin sees all, hospitals see their own."""
    user = await get_authenticated_user(authorization, db)

    if user.role == "admin":
        # Admin sees all weights with user emails
        query = (
            select(Weight, User.email, User.name)
            .join(User, Weight.user_id == User.id)
            .order_by(Weight.uploaded_at.desc())
        )
        result = await db.execute(query)
        rows = result.all()
        weights = []
        for weight, email, name in rows:
            w = weight.to_dict()
            w["email"] = email
            w["hospital_name"] = name or email
            weights.append(w)
    else:
        # Hospital sees own weights
        result = await db.execute(
            select(Weight)
            .where(Weight.user_id == user.id)
            .order_by(Weight.uploaded_at.desc())
        )
        weights = [w.to_dict() for w in result.scalars().all()]

    return {"weights": weights}


@router.get("/weights/download/{weight_id}")
async def download_weight(
    weight_id: int,
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Download a specific weight file."""
    user = await get_authenticated_user(authorization, db)

    result = await db.execute(select(Weight).where(Weight.id == weight_id))
    weight = result.scalar_one_or_none()

    if not weight:
        raise HTTPException(status_code=404, detail="Weight not found")

    # Hospitals can only download their own weights
    if user.role != "admin" and weight.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(weight.file_path):
        raise HTTPException(status_code=404, detail="Weight file not found on disk")

    return FileResponse(
        weight.file_path,
        filename=weight.original_filename,
        media_type="application/octet-stream",
    )


@router.get("/stats")
async def get_stats(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Get platform statistics."""
    user = await get_authenticated_user(authorization, db)

    # Count hospitals (users with role 'hospital')
    result = await db.execute(
        select(func.count(User.id)).where(User.role == "hospital")
    )
    hospital_count = result.scalar() or 0

    # Count total uploads
    result = await db.execute(select(func.count(Weight.id)))
    total_uploads = result.scalar() or 0

    # Count unique uploaders
    result = await db.execute(select(func.count(func.distinct(Weight.user_id))))
    participating_hospitals = result.scalar() or 0

    # Uploads per hospital (for chart)
    uploads_per_hospital = []
    if user.role == "admin":
        query = (
            select(User.email, User.name, func.count(Weight.id).label("count"))
            .join(Weight, User.id == Weight.user_id)
            .group_by(User.id, User.email, User.name)
            .order_by(func.count(Weight.id).desc())
        )
        result = await db.execute(query)
        for email, name, count in result.all():
            uploads_per_hospital.append({
                "hospital": name or email,
                "email": email,
                "count": count,
            })

    return {
        "hospital_count": hospital_count,
        "total_uploads": total_uploads,
        "participating_hospitals": participating_hospitals,
        "uploads_per_hospital": uploads_per_hospital,
    }


@router.delete("/weights/{weight_id}")
async def delete_weight(
    weight_id: int,
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific weight record and file (admin only)."""
    user = await get_authenticated_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(select(Weight).where(Weight.id == weight_id))
    weight = result.scalar_one_or_none()

    if not weight:
        raise HTTPException(status_code=404, detail="Weight not found")

    # Delete from disk
    if os.path.exists(weight.file_path):
        try:
            os.remove(weight.file_path)
        except Exception:
            pass

    # Delete from database
    from sqlalchemy import delete
    await db.execute(delete(Weight).where(Weight.id == weight_id))
    await db.commit()

    return {"message": "Weight deleted successfully"}
