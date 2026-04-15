import os
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.database import get_db
from backend.models.user import User
from backend.models.weight import Weight
from backend.models.global_model import GlobalModel
from backend.routes.auth import verify_jwt_token
from backend.services.fedavg import federated_average, save_weights
from backend.config import MODELS_DIR

router = APIRouter(prefix="/api", tags=["Aggregation"])


async def get_admin_user(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Verify user is an admin."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")
    payload = verify_jwt_token(token)
    user_id = int(payload["sub"])

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.post("/aggregate")
async def aggregate_weights(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    """
    Perform Federated Averaging on all uploaded weights.
    Admin-only endpoint.
    """
    admin = await get_admin_user(authorization, db)

    # Get latest weight file from each hospital
    # Subquery: latest upload per user
    subquery = (
        select(
            Weight.user_id,
            func.max(Weight.uploaded_at).label("latest_upload"),
        )
        .group_by(Weight.user_id)
        .subquery()
    )

    query = (
        select(Weight)
        .join(
            subquery,
            (Weight.user_id == subquery.c.user_id)
            & (Weight.uploaded_at == subquery.c.latest_upload),
        )
    )

    result = await db.execute(query)
    latest_weights = result.scalars().all()

    if len(latest_weights) < 2:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 2 hospital weights to aggregate. Currently have {len(latest_weights)}.",
        )

    # Collect valid weight file paths
    weight_files = []
    missing_files = []
    for w in latest_weights:
        if os.path.exists(w.file_path):
            weight_files.append(w.file_path)
        else:
            missing_files.append(w.file_path)

    if len(weight_files) < 2:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough valid weight files on disk. Found {len(weight_files)}, need at least 2.",
        )

    # Perform FedAvg
    try:
        avg_weights = federated_average(weight_files)
    except ValueError as e:
        error_msg = str(e)
        # Try to find which hospital this path belongs to for a better error message
        for w in latest_weights:
            if w.file_path in error_msg:
                user_res = await db.execute(select(User).where(User.id == w.user_id))
                user_match = user_res.scalar_one_or_none()
                hospital_info = f"{user_match.name} ({user_match.email})" if user_match else w.user_id
                error_msg = error_msg.replace(w.file_path, f"Hospital: {hospital_info}")
        
        raise HTTPException(
            status_code=400,
            detail=f"Aggregation failed: {error_msg}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during aggregation: {str(e)}",
        )

    # Determine version number
    result = await db.execute(
        select(func.coalesce(func.max(GlobalModel.version), 0))
    )
    current_version = result.scalar()
    new_version = current_version + 1

    # Save global model
    model_filename = f"global_model_v{new_version}.pkl"
    model_path = os.path.join(MODELS_DIR, model_filename)
    save_weights(avg_weights, model_path)

    # Record in database
    global_model = GlobalModel(
        version=new_version,
        file_path=model_path,
        num_participants=len(weight_files),
    )
    db.add(global_model)
    await db.commit()
    await db.refresh(global_model)

    return {
        "message": "Federated averaging completed successfully",
        "global_model": global_model.to_dict(),
        "num_participants": len(weight_files),
        "version": new_version,
        "missing_files": len(missing_files),
    }


@router.get("/global_model")
async def get_global_model(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Get latest global model info."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")
    verify_jwt_token(token)

    result = await db.execute(
        select(GlobalModel).order_by(GlobalModel.version.desc()).limit(1)
    )
    model = result.scalar_one_or_none()

    if not model:
        return {"global_model": None, "message": "No global model available yet"}

    return {"global_model": model.to_dict()}


@router.get("/global_model/download")
async def download_global_model(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Download the latest global model."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")
    verify_jwt_token(token)

    result = await db.execute(
        select(GlobalModel).order_by(GlobalModel.version.desc()).limit(1)
    )
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="No global model available")

    if not os.path.exists(model.file_path):
        raise HTTPException(status_code=404, detail="Global model file not found on disk")

    return FileResponse(
        model.file_path,
        filename=f"global_model_v{model.version}.pkl",
        media_type="application/octet-stream",
    )


@router.get("/global_model/history")
async def get_model_history(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregation history."""
    admin = await get_admin_user(authorization, db)

    result = await db.execute(
        select(GlobalModel).order_by(GlobalModel.version.desc()).limit(20)
    )
    models = result.scalars().all()

    return {
        "history": [m.to_dict() for m in models],
    }


@router.delete("/global_model/{model_id}")
async def delete_global_model(
    model_id: int,
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Delete a global model version (admin only)."""
    admin = await get_admin_user(authorization, db)

    result = await db.execute(select(GlobalModel).where(GlobalModel.id == model_id))
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Global model not found")

    # Delete from disk
    if os.path.exists(model.file_path):
        try:
            os.remove(model.file_path)
        except Exception:
            pass

    # Delete from database
    from sqlalchemy import delete
    await db.execute(delete(GlobalModel).where(GlobalModel.id == model_id))
    await db.commit()

    return {"message": "Global model deleted successfully"}
