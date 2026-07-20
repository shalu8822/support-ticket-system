from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import crud
import schemas
import models
from database import get_db
from auth import get_current_user

router = APIRouter(tags=["Users"])


@router.get("/profile", response_model=schemas.UserOut)
def get_profile(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.get("/notifications", response_model=List[schemas.NotificationOut])
def get_notifications(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Notifications fire whenever one of the user's tickets changes status."""
    return crud.list_notifications_for_user(db, current_user.id)


@router.put("/notifications/{notification_id}/read", response_model=schemas.NotificationOut)
def read_notification(
    notification_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not note or note.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    return crud.mark_notification_read(db, note)
